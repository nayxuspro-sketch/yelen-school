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
