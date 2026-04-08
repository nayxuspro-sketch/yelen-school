"""
Fixtures partagées pour les tests du module vacations.
"""

import pytest
from model_bakery import baker


@pytest.fixture
def annee(db):
    """Année scolaire courante."""
    return baker.make(
        'parametres.AnneeScolaire',
        libelle='2025-2026',
        est_courante=True,
    )


@pytest.fixture
def personnel(db):
    """MembrePersonnel avec des valeurs courtes (max_length=30)."""
    return baker.make(
        'personnel.MembrePersonnel',
        nom='KABORÉ',
        prenom='Adama',
        matricule='PERS-YSK-2026-0001',
        genre='M',
        nationalite='Burkinabè',
        lieu_naissance='Ouagadougou',
        telephone='0000',
        numero_cni='B00001',
        fonction='Enseignant',
        titre_honorifique='M.',
        situation_matrimoniale='C',
        poste_principal_code='ENS',
    )


@pytest.fixture
def contrat(db, annee, personnel):
    """ContratVacation minimal."""
    return baker.make(
        'vacations.ContratVacation',
        personnel=personnel,
        annee_scolaire=annee,
        actif=True,
    )


@pytest.fixture
def admin_user(db):
    """Utilisateur superadmin."""
    return baker.make('accounts.User', is_superuser=True, is_staff=True)
