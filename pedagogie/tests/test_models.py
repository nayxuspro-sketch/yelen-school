import pytest
from django.core.exceptions import ValidationError
from model_bakery import baker

@pytest.mark.django_db
class TestPedagogieModels:
    def test_note_range_validation(self):
        """Vérifie que les notes sont compromises entre 0 et 20."""
        # Note valide
        note_valide = baker.make('pedagogie.Note', valeur=15.5)
        assert note_valide.valeur == 15.5
        
        # Test de validation (full_clean)
        note_invalide_trop_haute = baker.prepare('pedagogie.Note', valeur=21)
        with pytest.raises(ValidationError):
            note_invalide_trop_haute.full_clean()
            
        note_invalide_negative = baker.prepare('pedagogie.Note', valeur=-1)
        with pytest.raises(ValidationError):
            note_invalide_negative.full_clean()

    def test_trimestre_period(self):
        """Vérifie que la date de fin est après la date de début."""
        from datetime import date
        trimestre = baker.make(
            'pedagogie.Trimestre', 
            date_debut=date(2026, 9, 15), 
            date_fin=date(2026, 12, 20)
        )
        assert trimestre.date_fin > trimestre.date_debut

    def test_matiere_str(self):
        """Vérifie la représentation textuelle d'une matière."""
        matiere = baker.make('pedagogie.Matiere', nom="Mathématiques", code="MATH")
        assert "Mathématiques" in str(matiere)
        assert "MATH" in str(matiere)

    def test_evaluation_weight(self):
        """Vérifie que le coefficient d'une évaluation est positif."""
        evaluation = baker.make('pedagogie.Evaluation', coefficient=2)
        assert evaluation.coefficient > 0

    def test_note_str(self):
        """Vérifie la représentation textuelle d'une note."""
        note = baker.make('pedagogie.Note', valeur=18)
        assert "18" in str(note)


@pytest.mark.django_db
class TestSigleCompetences:
    """Sigle de l'évaluation par compétences selon le cycle.

    Au Burkina Faso, le primaire relève de l'**Approche Pédagogique Intégratrice (API)** ; le préscolaire,
    le post-primaire et le secondaire de l'**Approche Par Compétences (APC)**. Le sigle était jusqu'ici
    écrit « APC » partout, y compris sur les bulletins du primaire.
    """

    @pytest.mark.parametrize('code, sigle, libelle', [
        ('PRIM', 'API', 'Approche Pédagogique Intégratrice (API)'),
        ('PRES', 'APC', 'Approche Par Compétences (APC)'),
        ('POST', 'APC', 'Approche Par Compétences (APC)'),
        ('SEC', 'APC', 'Approche Par Compétences (APC)'),
    ])
    def test_sigle_et_libelle_par_cycle(self, code, sigle, libelle):
        cycle = baker.make('parametres.Cycle', code=code, nom=f'Cycle {code}')
        assert cycle.sigle_competences == sigle
        assert cycle.libelle_competences == libelle
