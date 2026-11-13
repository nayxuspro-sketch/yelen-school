import uuid

from django.db.utils import IntegrityError
from django.test import TestCase
from model_bakery import baker

from etablissements.models import Etablissement


class TestEtablissementModel(TestCase):
    """Tests unitaires pour le modèle Etablissement."""

    def test_heritage_basemodel(self):
        """Vérifie l'héritage de BaseModel (UUID, is_active, created_at, updated_at)."""
        etab = baker.make(Etablissement)

        assert isinstance(etab.id, uuid.UUID)
        assert etab.is_active is True
        assert etab.created_at is not None
        assert etab.updated_at is not None

    def test_tous_les_champs(self):
        """Vérifie les informations de base de l'établissement."""
        etab = baker.make(
            Etablissement,
            nom="Complexe Scolaire La Joie",
            code="CS-JOIE",
            adresse="Secteur 22, Bobo-Dioulasso",
            telephone="+226 70 10 20 30",
            email="contact@cs-joie.bf",
            ville="Bobo-Dioulasso",
            pays="Burkina Faso",
        )

        assert etab.nom == "Complexe Scolaire La Joie"
        assert etab.code == "CS-JOIE"
        assert etab.adresse == "Secteur 22, Bobo-Dioulasso"
        assert etab.telephone == "+226 70 10 20 30"
        assert etab.email == "contact@cs-joie.bf"
        assert etab.ville == "Bobo-Dioulasso"
        assert etab.pays == "Burkina Faso"
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
        etab = Etablissement.objects.create(
            nom="Ecole Privée",
            code="EP-01",
            ville="Ouahigouya",
        )
        assert etab.pays == "Burkina Faso"

    def test_cycles_configures_par_relation_unique(self):
        """Les cycles appartiennent à l'établissement via la relation paramétrable, pas une liste parallèle."""
        etab = baker.make(Etablissement, code="GRP-SCOL")
        prescolaire = baker.make(
            'parametres.Cycle', etablissement=etab, code='PRES', nom='Préscolaire', ordre=1,
        )
        primaire = baker.make(
            'parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire', ordre=2,
        )

        assert list(etab.cycles_parametres.order_by('ordre')) == [prescolaire, primaire]
        assert 'cycles' not in {field.name for field in Etablissement._meta.get_fields()}
