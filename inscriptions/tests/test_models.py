import pytest
from datetime import date, timedelta
from model_bakery import baker
from inscriptions.models import Eleve, Inscription, StatutInscriptionChoices

@pytest.mark.django_db
class TestEleveModel:
    def test_matricule_generation(self):
        """Vérifie que le matricule est généré automatiquement."""
        eleve = baker.make('inscriptions.Eleve', matricule='')
        assert eleve.matricule.startswith('XX-')
        assert len(eleve.matricule) == 10  # XX-2026-01 (10 chars)

    def test_age_calculation(self):
        """Vérifie le calcul dynamique de l'âge."""
        fifteen_years_ago = date.today() - timedelta(days=365 * 15 + 4) # +4 pour compenser les années bissextiles
        eleve = baker.make('inscriptions.Eleve', date_naissance=fifteen_years_ago)
        assert eleve.age == 15
        assert "15 ans" in eleve.age_formatted

    def test_str_representation(self):
        """Vérifie la représentation textuelle de l'élève."""
        eleve = baker.make('inscriptions.Eleve', nom="Traore", prenom="Paul", matricule="01-2026-01")
        assert "Paul Traore" in str(eleve)
        assert "01-2026-01" in str(eleve)

@pytest.mark.django_db
class TestInscriptionModel:
    def test_inscription_uniqueness(self):
        """Vérifie qu'un élève ne peut pas être inscrit deux fois la même année."""
        annee = baker.make('parametres.AnneeScolaire')
        eleve = baker.make('inscriptions.Eleve')
        baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=annee)
        
        with pytest.raises(Exception): # Django integrity error or ValidationError depending on save/clean
            # Utilisation de baker.make qui appelle save()
            baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=annee)

    def test_numero_recu_vide_par_defaut(self):
        """Vérifie que le numéro de reçu est vide par défaut (n'est plus auto-généré)."""
        inscription = baker.make('inscriptions.Inscription')
        assert inscription.numero_recu == ''

    def test_str_representation(self):
        """Vérifie la représentation textuelle de l'inscription."""
        inscription = baker.make('inscriptions.Inscription')
        assert str(inscription.eleve.nom) in str(inscription)
        assert str(inscription.classe.nom) in str(inscription)
