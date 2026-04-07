import pytest
from decimal import Decimal
from model_bakery import baker
from pedagogie.utils import CalculateurMoyenne
from pedagogie.models import Resultat, MoyenneGenerale, Note, Evaluation, TypeEvaluation

@pytest.mark.django_db
class TestCalculateurMoyenne:
    def test_arrondir(self):
        assert CalculateurMoyenne.arrondir('10.555') == Decimal('10.56')
        assert CalculateurMoyenne.arrondir('10.554') == Decimal('10.55')

    def test_calculer_resultat_matiere_base(self):
        """Vérifie le calcul simple d'une moyenne de matière."""
        inscription = baker.make('inscriptions.Inscription')
        enseignement = baker.make('pedagogie.Enseignement')
        trimestre = baker.make('pedagogie.Trimestre')
        
        type_eval = baker.make('pedagogie.TypeEvaluation', coefficient=Decimal('1.0'))
        eval1 = baker.make('pedagogie.Evaluation', 
                          enseignement=enseignement, 
                          trimestre=trimestre, 
                          type_evaluation=type_eval,
                          statut='TERMINEE')
        
        baker.make('pedagogie.Note', inscription=inscription, evaluation=eval1, valeur=15)
        
        resultat = CalculateurMoyenne.calculer_resultat_matiere(inscription, enseignement, trimestre)
        
        assert resultat is not None
        assert resultat.moyenne == Decimal('15.00')

    def test_calculer_moyenne_generale(self):
        """Vérifie le calcul de la moyenne générale de l'élève."""
        inscription = baker.make('inscriptions.Inscription')
        trimestre = baker.make('pedagogie.Trimestre')
        
        # Deux matières avec des coefficients différents
        baker.make('pedagogie.Resultat', inscription=inscription, trimestre=trimestre, moyenne=Decimal('12.00'), coefficient_utilise=Decimal('2.00'))
        baker.make('pedagogie.Resultat', inscription=inscription, trimestre=trimestre, moyenne=Decimal('15.00'), coefficient_utilise=Decimal('3.00'))
        
        # (12*2 + 15*3) / 5 = (24 + 45) / 5 = 69 / 5 = 13.8
        mg = CalculateurMoyenne.calculer_moyenne_generale(inscription, trimestre)
        
        assert mg.moyenne == Decimal('13.80')
        assert mg.total_coefficients == Decimal('5.00')

    def test_calculer_rangs(self):
        """Vérifie l'attribution correcte des rangs."""
        classe = baker.make('parametres.Classe')
        trimestre = baker.make('pedagogie.Trimestre')
        
        # 3 élèves avec des moyennes différentes
        ins1 = baker.make('inscriptions.Inscription', classe=classe, statut='ACTIF')
        ins2 = baker.make('inscriptions.Inscription', classe=classe, statut='ACTIF')
        ins3 = baker.make('inscriptions.Inscription', classe=classe, statut='ACTIF')
        
        baker.make('pedagogie.MoyenneGenerale', inscription=ins1, trimestre=trimestre, moyenne=Decimal('16.00'))
        baker.make('pedagogie.MoyenneGenerale', inscription=ins2, trimestre=trimestre, moyenne=Decimal('12.00'))
        baker.make('pedagogie.MoyenneGenerale', inscription=ins3, trimestre=trimestre, moyenne=Decimal('14.00'))
        
        CalculateurMoyenne.calculer_rangs(classe, trimestre)
        
        assert MoyenneGenerale.objects.get(inscription=ins1).rang == 1
        assert MoyenneGenerale.objects.get(inscription=ins3).rang == 2
        assert MoyenneGenerale.objects.get(inscription=ins2).rang == 3
