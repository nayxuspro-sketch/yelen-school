import pytest
from model_bakery import baker
from django.core.exceptions import ValidationError
from finances.models import Paiement, TypeFrais

@pytest.mark.django_db
class TestFinancesModels:
    def test_paiement_montant_positif(self):
        """Vérifie que le montant d'un paiement est positif."""
        paiement = baker.make('finances.Paiement', montant=25000)
        assert paiement.montant > 0

    def test_frais_scolarite_str(self):
        """Vérifie la représentation textuelle d'un frais de scolarité."""
        classe = baker.make('parametres.Classe', nom="6ème A")
        frais = baker.make('finances.FraisScolarite', classe=classe, montant=50000)
        assert "6ème A" in str(frais)
        assert "50000" in str(frais)

    def test_paiement_str(self):
        """Vérifie la représentation textuelle d'un paiement."""
        inscription = baker.make('inscriptions.Inscription')
        paiement = baker.make('finances.Paiement', inscription=inscription, montant=10000)
        assert "10000" in str(paiement)
        assert str(inscription.eleve.nom) in str(paiement)
