"""Cycle de vie des données personnelles (5.35.0) : éligibilité, anonymisation, comptes, audit, export, page, commande."""
import json
from datetime import date
from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from model_bakery import baker

from core import donnees_personnelles as dp
from inscriptions.models import Eleve

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement')
    user = baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False)
    client.force_login(user)
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6e A', niveau='6e')
    ancienne = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2012-2013',
                          date_debut=date(2012, 10, 1), date_fin=date(2013, 6, 30))
    courante = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027',
                          date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30), est_courante=True)

    def eleve(nom, annees, photo=''):
        e = baker.make(Eleve, nom=nom, prenom='Awa', date_naissance=date(2000, 1, 1), photo=photo,
                       telephone_parent='70000000', allergies='arachide')
        for a in annees:
            baker.make('inscriptions.Inscription', eleve=e, annee_scolaire=a, classe=classe)
        return e

    sorti = eleve('SORTI', [ancienne], photo=SimpleUploadedFile('p.jpg', b'x', content_type='image/jpeg'))
    present = eleve('PRESENT', [ancienne, courante])
    return {'etab': etab, 'user': user, 'classe': classe, 'ancienne': ancienne, 'courante': courante,
            'sorti': sorti, 'present': present, 'tmp': tmp_path}


def test_eligibilite_selon_la_derniere_annee(ctx):
    assert list(dp.eleves_a_anonymiser(ctx['etab'], 10)) == [ctx['sorti']]
    assert dp.eleves_a_anonymiser(ctx['etab'], 20).count() == 0
    autre = baker.make('etablissements.Etablissement')
    assert dp.eleves_a_anonymiser(autre, 10).count() == 0


def test_anonymisation_efface_identite_photo_fichiers_et_comptes(ctx):
    sorti, present = ctx['sorti'], ctx['present']
    chemin_photo = sorti.photo.path
    insc = sorti.inscriptions.first()
    doc = baker.make('documents.Document', inscription=insc, annee_scolaire=ctx['ancienne'],
                     fichier=SimpleUploadedFile('c.pdf', b'%PDF', content_type='application/pdf'))
    parent_seul = baker.make('accounts.User', role='PARENT', username='70000000', telephone='70000000',
                             first_name='Moussa', eleves_lies=[sorti])
    parent_mixte = baker.make('accounts.User', role='PARENT', username='71000000', eleves_lies=[sorti, present])
    preinsc = baker.make('inscriptions.PreInscription', etablissement=ctx['etab'], annee_scolaire=ctx['ancienne'])

    bilan = dp.anonymiser(ctx['etab'], user=ctx['user'])

    assert bilan == {'eleves': 1, 'comptes': 1, 'fichiers': 2, 'preinscriptions': 1}
    sorti.refresh_from_db()
    assert (sorti.nom, sorti.prenom, sorti.telephone_parent, sorti.allergies, sorti.photo.name) == ('ANONYMISÉ', '—', '', '', '')
    assert sorti.anonymise_le and not sorti.is_active
    assert not (ctx['tmp'] / chemin_photo.split(str(ctx['tmp']))[-1].lstrip('/')).exists()
    doc.refresh_from_db()
    assert doc.fichier.name == '' and sorti.inscriptions.count() == 1
    parent_seul.refresh_from_db()
    assert not parent_seul.is_active and parent_seul.telephone == '' and parent_seul.username.startswith('anonyme-')
    parent_mixte.refresh_from_db()
    assert parent_mixte.is_active and parent_mixte.username == '71000000'
    present.refresh_from_db()
    assert present.nom == 'PRESENT' and present.anonymise_le is None
    assert not type(preinsc).objects.filter(pk=preinsc.pk).exists()
    assert dp.eleves_a_anonymiser(ctx['etab'], 10).count() == 0
    politique = dp.politique_de(ctx['etab'])
    assert politique.derniere_anonymisation is not None
    from core.models import AuditLog
    assert AuditLog.objects.filter(action='DELETE', object_id=str(politique.pk), reason__startswith='Anonymisation').exists()


def test_export_dossier_json(ctx, client):
    baker.make('finances.Paiement', inscription=ctx['present'].inscriptions.first(), montant=15000)
    r = client.get(reverse('inscriptions:eleve_export_donnees', args=[ctx['present'].pk]))
    assert r.status_code == 200 and r['Content-Type'].startswith('application/json')
    from core.models import AuditLog
    assert AuditLog.objects.filter(action='EXPORT', object_id=str(ctx['present'].pk)).exists()
    data = json.loads(r.content)
    assert data['eleve']['nom'] == 'PRESENT' and len(data['inscriptions']) == 2 and data['paiements'][0]['montant'] == 15000.0
    assert 'id' not in data['eleve']
    # Isolation : un élève d'un autre établissement n'est pas exportable
    autre = baker.make('etablissements.Etablissement')
    classe = baker.make('parametres.Classe', etablissement=autre)
    e = baker.make(Eleve, nom='AUTRE', date_naissance=date(2000, 1, 1), photo='')
    baker.make('inscriptions.Inscription', eleve=e, classe=classe, annee_scolaire=ctx['courante'])
    assert client.get(reverse('inscriptions:eleve_export_donnees', args=[e.pk])).status_code == 302


def test_page_et_formulaire(ctx, client):
    url = reverse('parametres:donnees_personnelles')
    html = client.get(url).content.decode()
    assert 'SORTI' in html and 'PRESENT' not in html and 'Registre des traitements' in html and 'Anonymiser 1 élève' in html
    r = client.post(url, {'duree_conservation_annees': 15, 'responsable_traitement': 'Le Directeur', 'contact_responsable': ''})
    assert r.status_code == 302 and dp.politique_de(ctx['etab']).duree_conservation_annees == 15
    assert 'Aucun élève à anonymiser' in client.get(url).content.decode()
    r = client.post(url, {'duree_conservation_annees': 1, 'responsable_traitement': '', 'contact_responsable': ''})
    assert r.status_code == 200 and 'entre 2 et 50 ans' in r.content.decode()
    r = client.post(reverse('parametres:anonymiser_donnees'))
    assert r.status_code == 302 and dp.politique_de(ctx['etab']).derniere_anonymisation is not None


def test_commande_dry_run_puis_execution(ctx):
    out = StringIO()
    call_command('anonymiser_donnees', '--dry-run', stdout=out)
    assert '1 élève(s) à anonymiser' in out.getvalue()
    ctx['sorti'].refresh_from_db()
    assert ctx['sorti'].nom == 'SORTI'
    out = StringIO()
    call_command('anonymiser_donnees', stdout=out)
    assert '1 élève(s) anonymisé(s)' in out.getvalue()
    ctx['sorti'].refresh_from_db()
    assert ctx['sorti'].nom == 'ANONYMISÉ'
