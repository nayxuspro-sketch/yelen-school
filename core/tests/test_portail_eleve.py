"""Portail élève aligné sur le portail parent (5.36.0) : PWA propre (manifeste, service worker), pages partagées,
bulletin en lecture seule, documents délivrés isolés par élève, notification de bulletin au compte élève."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement')
    aujourdhui = timezone.localdate()
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=aujourdhui - timedelta(days=30), date_fin=aujourdhui + timedelta(days=240))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='3e A', actif=True)

    def dossier(nom):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='Issa', date_naissance=date(2011, 5, 6), photo='')
        inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut='AFFECTE')
        compte = baker.make('accounts.User', etablissement=etab, role='ELEVE', must_change_password=False)
        compte.eleves_lies.add(eleve)
        type_doc = baker.make('parametres.TypeDocument', code=f'CERT_{nom[:10]}', libelle='Certificat de scolarité')
        document = baker.make('documents.Document', inscription=inscription, annee_scolaire=annee, type_document=type_doc,
                              fichier=SimpleUploadedFile(f'{nom}.pdf', b'%PDF-1.4 test', content_type='application/pdf'))
        return {'eleve': eleve, 'inscription': inscription, 'compte': compte, 'document': document}

    return {'etab': etab, 'annee': annee, 'classe': classe, 'a': dossier('TRAORE'), 'b': dossier('KABORE')}


def test_manifeste_et_service_worker_de_l_eleve(client, ecole):
    client.force_login(ecole['a']['compte'])
    manifest = client.get('/manifest-eleve.json').json()
    assert (manifest['name'], manifest['start_url'], manifest['scope']) == ('YELEN SCHOOL — Portail Élève', '/portail/eleve/', '/portail/eleve/')
    sw = client.get('/sw-eleve.js')
    assert sw.status_code == 200 and sw['Content-Type'].startswith('application/javascript')
    assert "yelen-eleve-v1" in sw.content.decode() and "/portail/parent/" not in sw.content.decode()
    parent = client.get('/sw.js').content.decode()
    assert "yelen-parent-v4" in parent and "/portail/eleve/" not in parent


def test_pages_du_portail_eleve_et_isolation_des_roles(client, ecole):
    client.force_login(ecole['a']['compte'])
    for nom in ('portail_eleve', 'portail_eleve_vie_scolaire', 'portail_eleve_bulletins', 'portail_eleve_cahier',
                'portail_eleve_notifications'):
        reponse = client.get(reverse(f'core:{nom}'))
        assert reponse.status_code == 200, nom
        assert '/portail/parent/' not in reponse.content.decode(), nom
    # L'élève est renvoyé vers son portail s'il tente les URL parent ; le personnel n'accède à aucun portail
    assert client.get(reverse('core:portail_parent')).status_code == 302
    client.force_login(baker.make('accounts.User', etablissement=ecole['etab'], role='DIRECTEUR', must_change_password=False))
    assert client.get(reverse('core:portail_eleve')).status_code == 403


def test_documents_delivres_telechargeables_par_leur_seul_eleve(client, ecole):
    client.force_login(ecole['a']['compte'])
    html = client.get(reverse('core:portail_eleve_bulletins')).content.decode()
    assert 'Documents délivrés' in html and 'Certificat de scolarité' in html
    mien = client.get(reverse('core:portail_eleve_document', args=[ecole['a']['document'].pk]))
    assert mien.status_code == 200 and mien['Content-Disposition'].startswith('attachment')
    assert b''.join(mien.streaming_content) == b'%PDF-1.4 test'
    assert client.get(reverse('core:portail_eleve_document', args=[ecole['b']['document'].pk])).status_code == 404


def test_bulletin_publie_en_lecture_seule_et_notification_du_compte_eleve(client, ecole, settings):
    from core.models import Notification
    from core.notifications import notifier_bulletin_publie
    t1 = baker.make('pedagogie.Trimestre', annee_scolaire=ecole['annee'], numero=1, nom='Trimestre 1',
                    date_debut=ecole['annee'].date_debut, date_fin=ecole['annee'].date_debut + timedelta(days=90))
    bulletin = baker.make('bulletins.Bulletin', inscription=ecole['a']['inscription'], trimestre=t1, est_publie=True)
    baker.make('pedagogie.MoyenneGenerale', inscription=ecole['a']['inscription'], trimestre=t1, moyenne=Decimal('13.25'))
    settings.SMS_ENABLED = False
    notifier_bulletin_publie(bulletin)
    assert Notification.objects.filter(destinataire=ecole['a']['compte'], type='BULLETIN', lien='/portail/eleve/bulletins/').exists()

    client.force_login(ecole['a']['compte'])
    liste = client.get(reverse('core:portail_eleve_bulletins')).content.decode()
    assert reverse('core:portail_eleve_bulletin', args=[bulletin.pk]) in liste and 'Signer' not in liste
    page = client.get(reverse('core:portail_eleve_bulletin', args=[bulletin.pk]))
    assert page.status_code == 200
    html = page.content.decode()
    assert '13,25' in html and 'Lu et signé' not in html
    # Le bulletin d'un autre élève n'est pas consultable
    autre = baker.make('bulletins.Bulletin', inscription=ecole['b']['inscription'], trimestre=t1, est_publie=True)
    assert client.get(reverse('core:portail_eleve_bulletin', args=[autre.pk])).status_code == 404


def test_carte_scolaire_telechargeable_depuis_le_portail(client, ecole, mocker):
    """L'élève télécharge sa carte scolaire (pièce d'entrée portant son matricule) ; celle d'un autre élève est refusée,
    et le parent retrouve celle de ses enfants."""
    from inscriptions.views import documents as vues_documents

    class _PDF:
        def __init__(self, string, base_url=''):
            self.string = string

        def write_pdf(self):
            return b'%PDF-1.4 carte'

    mocker.patch.object(vues_documents, '_WeasyHTML', _PDF)
    client.force_login(ecole['a']['compte'])
    reponse = client.get(reverse('core:portail_eleve_carte', args=[ecole['a']['eleve'].pk]))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert b''.join(reponse.streaming_content) == b'%PDF-1.4 carte'
    accueil = client.get(reverse('core:portail_eleve')).content.decode()
    assert reverse('core:portail_eleve_carte', args=[ecole['a']['eleve'].pk]) in accueil
    assert ecole['a']['eleve'].matricule in accueil, 'matricule rappelé : identifiant de connexion'
    assert client.get(reverse('core:portail_eleve_carte', args=[ecole['b']['eleve'].pk])).status_code == 404

    parent = baker.make('accounts.User', etablissement=ecole['etab'], role='PARENT', must_change_password=False)
    parent.eleves_lies.add(ecole['a']['eleve'])
    client.force_login(parent)
    assert client.get(reverse('core:portail_parent_carte', args=[ecole['a']['eleve'].pk])).status_code == 200
    assert client.get(reverse('core:portail_parent_carte', args=[ecole['b']['eleve'].pk])).status_code == 404


def test_notifications_d_absence_de_sanction_et_de_document_recues_par_l_eleve(ecole, settings):
    """Les avis qui ne concernaient que les parents arrivent aussi au compte élève, avec le lien de son portail."""
    from core.models import Notification
    from core.notifications import notifier_absence, notifier_document_delivre, notifier_sanction
    from presences.models import Presence

    settings.SMS_ENABLED = False
    parent = baker.make('accounts.User', etablissement=ecole['etab'], role='PARENT', must_change_password=False)
    parent.eleves_lies.add(ecole['a']['eleve'])
    inscription = ecole['a']['inscription']

    appel = baker.make('presences.Appel', classe=ecole['classe'], annee_scolaire=ecole['annee'],
                       date=timezone.localdate(), est_clos=True)
    presence = baker.make('presences.Presence', appel=appel, inscription=inscription,
                          statut=Presence.StatutChoices.ABSENT)
    notifier_absence(presence)
    avis = Notification.objects.get(destinataire=ecole['a']['compte'], type='ABSENCE')
    assert avis.lien == '/portail/eleve/vie-scolaire/'
    assert Notification.objects.get(destinataire=parent, type='ABSENCE').lien == '/portail/parent/vie-scolaire/'

    type_sanction = baker.make('parametres.TypeSanction', libelle='Avertissement')
    sanction = baker.make('viescolaire.SanctionDisciplinaire', inscription=inscription, type_sanction=type_sanction,
                          date_sanction=timezone.localdate(), motif='Bavardages')
    notifier_sanction(sanction)
    assert Notification.objects.get(destinataire=ecole['a']['compte'], type='SANCTION').lien == \
        '/portail/eleve/vie-scolaire/'

    notifier_document_delivre(ecole['a']['document'])
    avis = Notification.objects.get(destinataire=ecole['a']['compte'], type='DOCUMENT')
    assert avis.titre == 'Document disponible — Certificat de scolarité'
    assert avis.lien == '/portail/eleve/bulletins/'
    assert Notification.objects.filter(destinataire=parent, type='DOCUMENT', lien='/portail/parent/bulletins/').exists()
