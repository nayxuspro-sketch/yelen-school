import pytest
from django.core.exceptions import ValidationError
from model_bakery import baker

from finances.forms import FraisScolariteForm
from finances.models import FraisScolarite

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

    def test_frais_scolarite_cycle_relationnel_et_limite_a_l_etablissement(self):
        etab = baker.make('etablissements.Etablissement')
        autre = baker.make('etablissements.Etablissement')
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab)
        cycle = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire')
        cycle_autre = baker.make('parametres.Cycle', etablissement=autre, code='PRIM', nom='Primaire étranger')
        frais = baker.make(
            FraisScolarite, annee_scolaire=annee, classe=None, cycle=cycle, montant=50000,
        )

        assert 'Primaire' in str(frais)
        assert list(FraisScolariteForm(etablissement=etab).fields['cycle'].queryset) == [cycle]

        frais_incoherent = FraisScolarite(
            annee_scolaire=annee, cycle=cycle_autre, montant=50000,
        )
        with pytest.raises(ValidationError, match="cycle doit appartenir à l'établissement"):
            frais_incoherent.full_clean()

    def test_paiement_str(self):
        """Vérifie la représentation textuelle d'un paiement."""
        inscription = baker.make('inscriptions.Inscription')
        paiement = baker.make('finances.Paiement', inscription=inscription, montant=10000)
        assert "10000" in str(paiement)
        assert str(inscription.eleve.nom) in str(paiement)
