"""
Module Pédagogie - Tests Unitaires
==================================
Tests pour les modèles pédagogiques
"""

import pytest
from decimal import Decimal

from pedagogie.models import (
    Matiere,
    TypeEvaluation,
)


@pytest.mark.django_db
class TestMatiere:
    """Tests pour le modèle Matiere."""
    
    def test_creation_matiere(self):
        """Test de création d'une matière."""
        matiere = Matiere.objects.create(
            code='MATH',
            nom='Mathématiques',
            categorie=Matiere.CategorieChoices.SCIENTIFIQUE,
            coefficient=Decimal('4.00'),
            est_obligatoire=True
        )
        
        assert matiere.code == 'MATH'
        assert matiere.nom == 'Mathématiques'
        assert matiere.categorie == 'SCIENTIFIQUE'
        assert matiere.coefficient == Decimal('4.00')
    
    def test_matiere_str(self):
        """Test de la représentation string."""
        matiere = Matiere.objects.create(code='PHY', nom='Physique')
        assert str(matiere) == 'PHY - Physique'
    
    def test_matiere_est_obligatoire_par_defaut(self):
        """Test que est_obligatoire est True par défaut."""
        matiere = Matiere.objects.create(code='TEST', nom='Test')
        assert matiere.est_obligatoire is True
    
    def test_matiere_est_discipline_par_defaut(self):
        """Test que est_discipline est False par défaut."""
        matiere = Matiere.objects.create(code='TEST', nom='Test')
        assert matiere.est_discipline is False
    
    def test_categories_matieres(self):
        """Test que toutes les catégories de matières sont présentes."""
        categories = [choice.value for choice in Matiere.CategorieChoices]
        
        assert 'LANGUE' in categories
        assert 'SCIENTIFIQUE' in categories
        assert 'SOCIAL' in categories
        assert 'ART' in categories
        assert 'TECHNIQUE' in categories
        assert 'AUTRE' in categories


@pytest.mark.django_db
class TestTypeEvaluation:
    """Tests pour le modèle TypeEvaluation."""
    
    def test_creation_type_evaluation(self):
        """Test de création d'un type d'évaluation."""
        type_eval = TypeEvaluation.objects.create(
            code='DEV',
            nom='Devoir',
            coefficient=Decimal('1.00'),
            ponderation=Decimal('1.00'),
            est_visible=True,
            ordre=1
        )
        
        assert type_eval.code == 'DEV'
        assert type_eval.nom == 'Devoir'
        assert type_eval.ordre == 1
    
    def test_type_evaluation_str(self):
        """Test de la représentation string."""
        type_eval = TypeEvaluation.objects.create(code='COMP', nom='Composition')
        assert str(type_eval) == 'COMP - Composition'
    
    def test_type_evaluation_est_visible_par_defaut(self):
        """Test que est_visible est True par défaut."""
        type_eval = TypeEvaluation.objects.create(code='TEST', nom='Test')
        assert type_eval.est_visible is True


@pytest.mark.django_db
class TestChoices:
    """Tests pour les choix (choices) des modèles."""
    
    def test_categories_matieres_choices(self):
        """Test que toutes les catégories de matières sont présentes."""
        categories = [choice.value for choice in Matiere.CategorieChoices]
        
        assert 'LANGUE' in categories
        assert 'SCIENTIFIQUE' in categories
        assert 'SOCIAL' in categories
        assert 'ART' in categories
        assert 'TECHNIQUE' in categories
        assert 'AUTRE' in categories
    
    def test_types_periode_choices(self):
        """Test que tous les types de période sont présents."""
        from pedagogie.models import Trimestre
        types = [choice.value for choice in Trimestre.TypePeriodeChoices]
        
        assert 'TRIMESTRE' in types
        assert 'SEMESTRE' in types
    
    def test_statuts_evaluation_choices(self):
        """Test que tous les statuts d'évaluation sont présents."""
        from pedagogie.models import Evaluation
        statuts = [choice.value for choice in Evaluation.StatutChoices]
        
        assert 'PLANIFIEE' in statuts
        assert 'EN_COURS' in statuts
        assert 'TERMINEE' in statuts
        assert 'ANNULEE' in statuts
    
    def test_statuts_note_choices(self):
        """Test que tous les statuts de note sont présents."""
        from pedagogie.models import Note
        statuts = [choice.value for choice in Note.StatutNoteChoices]
        
        assert 'ENREGISTREE' in statuts
        assert 'VALIDEE' in statuts
        assert 'MODIFIEE' in statuts
        assert 'ANNULEE' in statuts


@pytest.mark.django_db
class TestModelFields:
    """Tests pour les champs des modèles."""
    
    def test_matiere_champs_obligatoires(self):
        """Test que les champs obligatoires sont présents."""
        # Code et nom sont obligatoires
        matiere = Matiere.objects.create(
            code='CODE',
            nom='Nom'
        )
        
        assert matiere.code == 'CODE'
        assert matiere.nom == 'Nom'
    
    def test_type_evaluation_champs_obligatoires(self):
        """Test que les champs obligatoires sont présents."""
        type_eval = TypeEvaluation.objects.create(
            code='CODE',
            nom='Nom'
        )
        
        assert type_eval.code == 'CODE'
        assert type_eval.nom == 'Nom'
    
    def test_matiere_coefficient_par_defaut(self):
        """Test que le coefficient est à 1.00 par défaut."""
        matiere = Matiere.objects.create(code='TEST', nom='Test')
        assert matiere.coefficient == Decimal('1.00')
    
    def test_matiere_moy_max_par_defaut(self):
        """Test que la moyenne maximale est à 20 par défaut."""
        matiere = Matiere.objects.create(code='TEST', nom='Test')
        assert matiere.moy_max == Decimal('20')
