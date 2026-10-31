"""Dossier documentaire par élève (5.37.0) : dépôt d'une pièce, téléchargement, suppression, isolation par
établissement, export et anonymisation."""
from datetime import date
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from model_bakery import baker

from inscriptions.models import PieceDossier

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, nom='4e A')
    eleve = baker.make('inscriptions.Eleve', nom='SAWADOGO', prenom='Awa', date_naissance=date(2012, 3, 4), photo='')
    baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=annee, classe=classe)
    return {'etab': etab, 'annee': annee, 'classe': classe, 'eleve': eleve}


def _pdf(nom='acte.pdf', contenu=b'%PDF-1.4 acte'):
    return SimpleUploadedFile(nom, contenu, content_type='application/pdf')


def test_depot_telechargement_et_suppression(client, ecole):
    url = reverse('inscriptions:eleve_dossier', args=[ecole['eleve'].pk])
    assert client.get(url).status_code == 200
    reponse = client.post(url, {'type_piece': 'ACTE_NAISSANCE', 'libelle': 'copie 2026', 'fichier': _pdf()})
    assert reponse.status_code == 302
    piece = PieceDossier.objects.get(eleve=ecole['eleve'])
    assert piece.get_type_piece_display() == 'Acte de naissance' and piece.libelle == 'copie 2026'
    assert piece.inscription is not None and piece.created_by is not None
    html = client.get(url).content.decode()
    assert 'Acte de naissance' in html and 'copie 2026' in html
    reponse = client.get(reverse('inscriptions:piece_dossier_telecharger', args=[piece.pk]))
    assert reponse.status_code == 200 and b''.join(reponse.streaming_content) == b'%PDF-1.4 acte'
    assert client.post(reverse('inscriptions:piece_dossier_supprimer', args=[piece.pk])).status_code == 302
    assert not PieceDossier.objects.exists()


def test_piece_refusee_si_pas_un_pdf_ou_image(client, ecole):
    url = reverse('inscriptions:eleve_dossier', args=[ecole['eleve'].pk])
    faux = SimpleUploadedFile('note.pdf', b'ceci est un texte', content_type='application/pdf')
    reponse = client.post(url, {'type_piece': 'AUTRE', 'fichier': faux})
    assert reponse.status_code == 200 and not PieceDossier.objects.exists()
    reponse = client.post(url, {'type_piece': 'AUTRE', 'fichier': SimpleUploadedFile('gros.pdf', b'x' * (6 * 1024 * 1024))})
    assert reponse.status_code == 200 and not PieceDossier.objects.exists()


def test_isolation_par_etablissement(client, ecole):
    autre = baker.make('etablissements.Etablissement')
    eleve_autre = baker.make('inscriptions.Eleve', nom='AUTRE', prenom='Issa', date_naissance=date(2012, 1, 1), photo='')
    baker.make('inscriptions.Inscription', eleve=eleve_autre, annee_scolaire=ecole['annee'],
               classe=baker.make('parametres.Classe', etablissement=autre))
    piece = baker.make(PieceDossier, eleve=eleve_autre, fichier=_pdf('x.pdf'))
    assert client.get(reverse('inscriptions:eleve_dossier', args=[eleve_autre.pk])).status_code == 302
    assert client.get(reverse('inscriptions:piece_dossier_telecharger', args=[piece.pk])).status_code == 404
    assert client.post(reverse('inscriptions:piece_dossier_supprimer', args=[piece.pk])).status_code == 404


def test_pieces_dans_l_export_et_effacees_a_l_anonymisation(ecole):
    from core import donnees_personnelles as dp
    piece = baker.make(PieceDossier, eleve=ecole['eleve'], type_piece='AUTRE', fichier=_pdf())
    chemin = piece.fichier.path
    dossier = dp.exporter_dossier(ecole['eleve'])
    (piece_exportee,) = dossier['pieces_dossier']
    assert piece_exportee['type_piece'] == 'AUTRE' and piece_exportee['fichier'].endswith('.pdf')
    bilan = dp.anonymiser(ecole['etab'], annees=1)      # année en cours (2026-2027) non terminée : rien à faire
    assert bilan['eleves'] == 0 and PieceDossier.objects.exists()
    ecole['annee'].date_fin = date(2000, 1, 1)
    ecole['annee'].save(update_fields=['date_fin'])
    bilan = dp.anonymiser(ecole['etab'], annees=1)
    assert bilan['eleves'] == 1 and not PieceDossier.objects.exists()
    import os
    assert not os.path.exists(chemin)
