"""Relance de paiement (PDF) : le signataire configuré pour la catégorie Finance doit y figurer."""
from decimal import Decimal
from importlib import import_module
from unittest.mock import patch

import pytest
from django.apps import apps
from django.urls import reverse
from model_bakery import baker

from parametres.models import SignataireDocument, TypeDocument


class EspionPdf:
    documents = []

    def __init__(self, string='', **kwargs):
        EspionPdf.documents.append(string)

    def write_pdf(self, target=None, **kwargs):
        target.write(b'%PDF-1.4 espion')


@pytest.fixture
def contexte(db, client):
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle)
    statut = baker.make('parametres.StatutEleve', etablissement=etab)
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, nom='Scolarité')
    baker.make('parametres.TarifScolarite', etablissement=etab, classe=classe, annee_scolaire=annee, statut_eleve=statut,
               rubrique=rubrique, montant=Decimal('25000'), actif=True)
    eleve = baker.make('inscriptions.Eleve', nom='OUÉDRAOGO', prenom='Awa', matricule='ETAB-2026-07')
    baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut_eleve=statut)
    return {'etab': etab, 'annee': annee, 'cycle': cycle, 'classe': classe, 'rubrique': rubrique}


def _signataire(contexte, code, nom, fonction):
    membre = baker.make('personnel.MembrePersonnel', etablissement=contexte['etab'], nom=nom, prenom='Salimata')
    return baker.make('parametres.SignataireDocument', cycle=contexte['cycle'], annee_scolaire=contexte['annee'],
                      type_document=TypeDocument.objects.get(code=code), membre_personnel_id=membre.id,
                      fonction=fonction, actif=True)


def _relance(client, contexte, classe):
    EspionPdf.documents.clear()
    with patch('finances.views.relances.WeasyHTML', EspionPdf):
        reponse = client.get(reverse('finances:relance_paiement_pdf'), {
            'annee': contexte['annee'].pk, 'classe': classe, 'rubrique': contexte['rubrique'].pk})
    assert reponse.status_code == 200 and len(EspionPdf.documents) == 1
    return EspionPdf.documents[0]


@pytest.mark.django_db
def test_type_de_document_relance_configurable():
    assert TypeDocument.objects.filter(code='RELANCE', categorie='FINANCE', actif=True).exists()


def test_signataire_finance_sur_la_relance(client, contexte):
    _signataire(contexte, 'RELANCE', 'KABORE', "L'Intendante")

    for classe in (contexte['classe'].pk, 'all'):
        html = _relance(client, contexte, classe)
        assert 'OUÉDRAOGO' in html and '25' in html
        assert '<div class="sig-titre">L&#x27;Intendante</div>' in html
        assert '<div class="sig-nom">KABORE Salimata</div>' in html


def test_signataires_configures_avant_la_migration_reportes_sur_la_relance(client, contexte):
    """Établissement configuré avant l'ajout du type « Relance » : le signataire Finance (liste des
    redevables) est repris, pas le signataire pédagogique plus récent."""
    _signataire(contexte, 'LISTE_REDEVABLES', 'KABORE', "L'Intendante")
    _signataire(contexte, 'BULLETIN', 'ZONGO', 'Le Censeur')

    import_module('parametres.migrations.0033_typedocument_relance').ajouter_relance(apps, None)

    assert SignataireDocument.objects.filter(type_document__code='RELANCE', fonction="L'Intendante").count() == 1
    html = _relance(client, contexte, contexte['classe'].pk)
    assert '<div class="sig-nom">KABORE Salimata</div>' in html and 'ZONGO' not in html
