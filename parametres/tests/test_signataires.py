"""Résolution du signataire d'un document : repli par catégorie et reprise des configurations existantes
sur les types ajoutés au catalogue (migration 0036)."""
import datetime
from importlib import import_module

import pytest
from django.apps import apps
from model_bakery import baker

from parametres.models import SignataireDocument, TypeDocument

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexte():
    etab = baker.make('etablissements.Etablissement', code='SIG', nom='Ets Signataires')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=datetime.date(2026, 10, 1), date_fin=datetime.date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire', ordre=1, actif=True)
    return {'etab': etab, 'annee': annee, 'cycle': cycle}


def _signataire(contexte, code, nom, fonction):
    membre = baker.make('personnel.MembrePersonnel', etablissement=contexte['etab'], nom=nom, prenom='Salimata')
    return baker.make('parametres.SignataireDocument', cycle=contexte['cycle'], annee_scolaire=contexte['annee'],
                      type_document=TypeDocument.objects.get(code=code), membre_personnel_id=membre.id,
                      fonction=fonction, actif=True)


def test_repli_sur_le_signataire_de_la_meme_categorie(contexte):
    """Type jamais configuré (ex. contrat de travail) : son document reprend le signataire de sa catégorie
    (Personnel), pas le signataire Finance pourtant plus récent."""
    _signataire(contexte, 'LISTE_PERSONNEL', 'KABORE', 'Le Directeur')
    _signataire(contexte, 'LISTE_REDEVABLES', 'ZONGO', "L'Intendante")

    sig = SignataireDocument.objects.get_signataire(
        cycle=contexte['cycle'], type_document=TypeDocument.objects.get(code='CONTRAT_TRAVAIL'),
        annee_scolaire=contexte['annee'],
    )
    assert sig.fonction == 'Le Directeur' and sig.get_membre_personnel().nom == 'KABORE'


def test_migration_0036_reprend_les_signataires_configures_par_categorie(contexte):
    """Établissement configuré avant 5.5.14 : chaque type ajouté reçoit, par cycle et année, le signataire
    déjà choisi pour sa catégorie — sans action de l'utilisateur."""
    _signataire(contexte, 'LISTE_PERSONNEL', 'KABORE', 'Le Directeur')
    _signataire(contexte, 'LISTE_REDEVABLES', 'ZONGO', "L'Intendante")

    import_module('parametres.migrations.0036_typedocument_documents_signes_2').ajouter_types(apps, None)

    def fonction(code):
        return SignataireDocument.objects.get(type_document__code=code, cycle=contexte['cycle'],
                                              annee_scolaire=contexte['annee']).fonction

    assert fonction('CONTRAT_TRAVAIL') == fonction('BULLETIN_SALAIRE') == fonction('BULLETIN_VACATION') == 'Le Directeur'
    assert fonction('LISTE_BOURSIERS') == "L'Intendante"
    # Catégories jamais configurées (Scolarité, Pédagogie) : rien n'est inventé
    assert not SignataireDocument.objects.filter(type_document__code__in=('PV_CONSEIL', 'DOSSIER_TRANSFERT')).exists()
    # Rejouable sans doublon
    import_module('parametres.migrations.0036_typedocument_documents_signes_2').ajouter_types(apps, None)
    assert SignataireDocument.objects.filter(type_document__code='CONTRAT_TRAVAIL').count() == 1
