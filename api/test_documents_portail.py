"""API — documents délivrés d'un élève (portail élève et parent), cloisonnés par le périmètre RBAC."""
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from model_bakery import baker
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='3e A', actif=True)
    type_doc = baker.make('parametres.TypeDocument', code='CERT', libelle='Certificat de scolarité')
    eleves = {}
    for nom in ('TRAORE', 'KABORE'):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='Issa', photo='', date_naissance=date(2011, 5, 6))
        inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
        document = baker.make('documents.Document', inscription=inscription, annee_scolaire=annee,
                              type_document=type_doc,
                              fichier=SimpleUploadedFile(f'{nom}.pdf', b'%PDF-1.4', content_type='application/pdf'))
        eleves[nom] = {'eleve': eleve, 'document': document}
    return {'etab': etab, 'eleves': eleves}


def test_documents_delivres_du_perimetre(ecole):
    client = APIClient()
    parent = baker.make('accounts.User', etablissement=ecole['etab'], role='PARENT', must_change_password=False)
    parent.eleves_lies.add(ecole['eleves']['TRAORE']['eleve'])
    client.force_authenticate(user=parent)

    reponse = client.get(f"/api/eleves/{ecole['eleves']['TRAORE']['eleve'].pk}/documents/")
    assert reponse.status_code == 200
    document, = reponse.json()
    assert document['libelle'] == 'Certificat de scolarité' and document['annee'] == '2026-2027'
    assert document['telechargement'] == reverse('core:portail_eleve_document',
                                                 kwargs={'pk': ecole['eleves']['TRAORE']['document'].pk})
    # L'élève d'une autre famille reste hors périmètre : 404, sans révéler son existence
    assert client.get(f"/api/eleves/{ecole['eleves']['KABORE']['eleve'].pk}/documents/").status_code == 404
