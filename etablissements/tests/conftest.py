# tests/conftest.py — Configuration globale pytest YELEN SCHOOL v2.0
import pytest
from django.test import Client
from model_bakery import baker
from datetime import date

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def directeur_proviseur(db):
    """Crée un utilisateur Directeur/Proviseur pour les tests."""
    user = baker.make('accounts.User', role='directeur_proviseur')
    baker.make('licences.Licence', etablissement__directeur=user,
               type_licence='premium', statut='active')
    return user

@pytest.fixture
def annee_scolaire(db):
    from parametres.models import AnneeScolaire
    return baker.make(AnneeScolaire, libelle='2025-2026', est_courante=True)

@pytest.fixture
def eleve_actif(db):
    """Crée un élève actif avec dossier complet."""
    eleve = baker.make('inscriptions.Eleve',
                       actif=True,
                       exonere=False,
                       date_naissance=date(2013, 5, 15))
    # Vérifie que le matricule BF- a bien été généré
    assert eleve.matricule.startswith('BF-')
 # Vérifie que l'âge est calculé (non stocké)
    assert eleve.age is not None
    assert isinstance(eleve.age, int)
    return eleve

@pytest.fixture
def membre_personnel(db, annee_scolaire):
    """Crée un membre du personnel avec matricule PERS-."""
    membre = baker.make('personnel.MembrePersonnel',
                        actif=True, sexe='M')
    # Vérifie que le matricule PERS- a été généré
    assert membre.matricule_personnel.startswith('PERS-')
    # Crée l'inscription annuelle
    baker.make('personnel.InscriptionPersonnel',
               membre=membre, annee_scolaire=annee_scolaire,
               statut='validee')
    return membre

@pytest.fixture
def eleve_sans_dettes(db, eleve_actif):
    """Élève sans dettes financières."""
    baker.make('finances.Paiement', eleve=eleve_actif, montant_solde=0)
    return eleve_actif
