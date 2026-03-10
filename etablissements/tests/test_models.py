import uuid
from django.db.utils import IntegrityError
from django.test import TestCase
from model_bakery import baker

from core.models import CycleChoices
from etablissements.models import Etablissement


class TestEtablissementModel(TestCase):
    """Tests unitaires pour le modèle Etablissement."""

    def test_heritage_basemodel(self):
        """Vérifie l'héritage de BaseModel (UUID, is_active, created_at, updated_at)."""
        etab = baker.make(Etablissement)
        
        # Vérification des champs hérités de BaseModel
        assert isinstance(etab.id, uuid.UUID)
        assert etab.is_active is True
        assert etab.created_at is not None
        assert etab.updated_at is not None

    def test_tous_les_champs(self):
        """Vérifie tous les champs spécifiques au modèle Etablissement."""
        cycles_str = f"{CycleChoices.PRIMAIRE},{CycleChoices.POST_PRIMAIRE},{CycleChoices.SECONDAIRE}"
        
        etab = baker.make(
            Etablissement,
            nom="Complexe Scolaire La Joie",
            code="CS-JOIE",
            adresse="Secteur 22, Bobo-Dioulasso",
            telephone="+226 70 10 20 30",
            email="contact@cs-joie.bf",
            cycles=cycles_str,
            ville="Bobo-Dioulasso",
            pays="Burkina Faso"
        )
        
        # Vérification des valeurs assignées
        assert etab.nom == "Complexe Scolaire La Joie"
        assert etab.code == "CS-JOIE"
        assert etab.adresse == "Secteur 22, Bobo-Dioulasso"
        assert etab.telephone == "+226 70 10 20 30"
        assert etab.email == "contact@cs-joie.bf"
        assert etab.ville == "Bobo-Dioulasso"
        assert etab.pays == "Burkina Faso"
        assert etab.cycles == "PRIMAIRE,POST_PRIMAIRE,SECONDAIRE"
        # Validation d'un champ vide par défaut pour le logo (non fourni via baker)
        assert not etab.logo

    def test_code_unique(self):
        """Vérifie que le code de l'établissement est unique."""
        baker.make(Etablissement, code="UNIK-123")
        
        with self.assertRaises(IntegrityError):
            baker.make(Etablissement, code="UNIK-123")

    def test_str_representation(self):
        """Vérifie que __str__ retourne 'nom (code)'."""
        etab = baker.make(Etablissement, nom="Lycée d'Excellence", code="LYC-EXC")
        assert str(etab) == "Lycée d'Excellence (LYC-EXC)"

    def test_pays_default_value(self):
        """Vérifie que le pays par défaut est bien le Burkina Faso."""
        # On ne passe pas la valeur pays lors de la création
        etab = baker.make(Etablissement, pays="")
        
        # Puisque baker.make peut forcer des champs, testons à la création classique ou 
        # forçons None pour voir. En général baker.make remplit intelligemment,
        # donc on vérifie via object.create() pour les valeurs par défaut au niveau BDD.
        etab_default = Etablissement.objects.create(
            nom="Ecole Privée",
            code="EP-01",
            ville="Ouahigouya"
        )
        assert etab_default.pays == "Burkina Faso"

    def test_cycle_peut_contenir_plusieurs_choix(self):
        """Vérifie que le champ cycles peut contenir plusieurs CycleChoices séparés par des virgules."""
        etab = Etablissement.objects.create(
            nom="Groupe Scolaire",
            code="GRP-SCOL",
            ville="Koudougou",
            cycles=f"{CycleChoices.PRESCOLAIRE},{CycleChoices.PRIMAIRE},{CycleChoices.POST_PRIMAIRE}"
        )
        
        # Rechargement depuis la base
        etab.refresh_from_db()
        
        assert isinstance(etab.cycles, str)
        assert "PRESCOLAIRE" in etab.cycles
        assert "PRIMAIRE" in etab.cycles
        assert "POST_PRIMAIRE" in etab.cycles
