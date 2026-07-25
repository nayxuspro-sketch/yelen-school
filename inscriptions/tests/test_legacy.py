"""
Module Inscriptions - Tests
===========================
YELEN SCHOOL v3.4 - Tests unitaires

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError

from inscriptions.models import Eleve, Inscription, GenreChoices, StatutInscriptionChoices


class EleveModelTest(TestCase):
    """Tests pour le modèle Eleve."""
    
    def setUp(self):
        """Configuration des tests."""
        self.eleve_data = {
            'nom': 'KABORE',
            'prenom': 'Abdel',
            'genre': GenreChoices.MASCULIN,
            'date_naissance': date(2015, 3, 15),
            'lieu_naissance': 'Ouagadougou',
            'nationalite': 'Burkinabè',
            'pays_residence': 'Burkina Faso',
            'province': 'Kadiogo',
            'commune': 'Ouagadougou',
            'telephone_parent': '+226 70 00 00 00',
        }
    
    def test_create_eleve(self):
        """Test de création d'un élève."""
        eleve = Eleve.objects.create(**self.eleve_data)
        
        self.assertIsNotNone(eleve.id)
        self.assertEqual(eleve.nom, 'KABORE')
        self.assertEqual(eleve.prenom, 'Abdel')
        self.assertEqual(eleve.genre, GenreChoices.MASCULIN)
    
    def test_matricule_auto_generated(self):
        """Test de génération automatique du matricule."""
        eleve = Eleve.objects.create(**self.eleve_data)
        
        # Le matricule doit être généré automatiquement
        self.assertIsNotNone(eleve.matricule)
        self.assertTrue('-' in eleve.matricule)
        self.assertIn(str(date.today().year), eleve.matricule)
    
    def test_age_calculation(self):
        """Test du calcul de l'âge."""
        eleve = Eleve.objects.create(**self.eleve_data)
        
        # L'âge doit être calculé dynamiquement
        self.assertIsNotNone(eleve.age)
        expected_age = (date.today() - date(2015, 3, 15)).days // 365
        self.assertEqual(eleve.age, expected_age)
    
    def test_nom_complet(self):
        """Test du nom complet."""
        eleve = Eleve.objects.create(**self.eleve_data)
        
        self.assertEqual(eleve.get_nom_complet(), 'KABORE ABDEL')
    
    def test_str_method(self):
        """Test de la méthode __str__."""
        eleve = Eleve.objects.create(**self.eleve_data)
        
        self.assertIn('KABORE', str(eleve))
        self.assertIn('Abdel', str(eleve))
        self.assertIn(eleve.matricule, str(eleve))


class InscriptionModelTest(TestCase):
    """Tests pour le modèle Inscription."""
    
    def setUp(self):
        """Configuration des tests."""
        # Créer un élève
        self.eleve = Eleve.objects.create(
            nom='TRAORE',
            prenom='Fatou',
            genre=GenreChoices.FEMININ,
            date_naissance=date(2014, 5, 20),
            lieu_naissance='Bobo-Dioulasso',
            nationalite='Burkinabè',
            pays_residence='Burkina Faso',
        )
        
        # Créer une année scolaire et une classe (si disponibles)
        # Note: Ces tests nécessitent que les modèles AnneeScolaire et Classe existent
    
    def test_create_inscription(self):
        """Test de création d'une inscription."""
        # Skip si les modèles liés n'existent pas
        from parametres.models import AnneeScolaire
        from etablissements.models import Etablissement
        from parametres.models import Cycle, Classe
        
        # Créer les données nécessaires
        etab, _ = Etablissement.objects.get_or_create(
            code='TEST',
            defaults={
                'nom': 'École Test',
                'ville': 'Ouagadougou'
            }
        )
        
        annee, _ = AnneeScolaire.objects.get_or_create(
            libelle='2025-2026',
            etablissement=etab,
            defaults={
                'date_debut': date(2025, 10, 1),
                'date_fin': date(2026, 7, 15),
                'est_courante': True
            }
        )
        
        cycle, _ = Cycle.objects.get_or_create(
            code='PRIM',
            etablissement=etab,
            defaults={
                'nom': 'Primaire',
                'ordre': 2,
                'actif': True
            }
        )
        
        classe, _ = Classe.objects.get_or_create(
            nom='CI',
            cycle=cycle,
            etablissement=etab,
            defaults={
                'nom': 'Cours Initiation',
                'niveau': 'CI'
            }
        )
        
        inscription = Inscription.objects.create(
            eleve=self.eleve,
            annee_scolaire=annee,
            classe=classe,
            statut=StatutInscriptionChoices.AFFECTE,
            est_redoublant=False
        )
        
        self.assertIsNotNone(inscription.id)
        self.assertEqual(inscription.eleve, self.eleve)
        self.assertEqual(inscription.statut, StatutInscriptionChoices.AFFECTE)
    
    def test_unique_inscription_per_year(self):
        """Test d'unicité d'inscription par année scolaire."""
        from parametres.models import AnneeScolaire
        from etablissements.models import Etablissement
        from parametres.models import Cycle, Classe
        
        # Créer les données nécessaires
        etab, _ = Etablissement.objects.get_or_create(
            code='TEST2',
            defaults={
                'nom': 'École Test 2',
                'ville': 'Ouagadougou'
            }
        )
        
        annee, _ = AnneeScolaire.objects.get_or_create(
            libelle='2026-2027',
            etablissement=etab,
            defaults={
                'date_debut': date(2026, 10, 1),
                'date_fin': date(2027, 7, 15),
                'est_courante': True
            }
        )
        
        cycle, _ = Cycle.objects.get_or_create(
            code='POST',
            etablissement=etab,
            defaults={
                'nom': 'Post-primaire',
                'ordre': 3,
                'actif': True
            }
        )
        
        classe, _ = Classe.objects.get_or_create(
            nom='CP',
            cycle=cycle,
            etablissement=etab,
            defaults={
                'nom': 'Cours Préparatoire',
                'niveau': 'CP'
            }
        )
        
        # Créer une première inscription
        Inscription.objects.create(
            eleve=self.eleve,
            annee_scolaire=annee,
            classe=classe,
            statut=StatutInscriptionChoices.AFFECTE
        )
        
        # Tenter de créer une deuxième inscription pour la même année
        with self.assertRaises(Exception):
            Inscription.objects.create(
                eleve=self.eleve,
                annee_scolaire=annee,
                classe=classe,
                statut=StatutInscriptionChoices.BOURSIER
            )
    
    def test_numero_recu_generation(self):
        """Test de génération du numéro de reçu."""
        from parametres.models import AnneeScolaire
        from etablissements.models import Etablissement
        from parametres.models import Cycle, Classe
        
        # Créer les données nécessaires
        etab, _ = Etablissement.objects.get_or_create(
            code='TEST3',
            defaults={
                'nom': 'École Test 3',
                'ville': 'Bobo-Dioulasso'
            }
        )
        
        annee, _ = AnneeScolaire.objects.get_or_create(
            libelle='2027-2028',
            etablissement=etab,
            defaults={
                'date_debut': date(2027, 10, 1),
                'date_fin': date(2028, 7, 15),
                'est_courante': True
            }
        )
        
        cycle, _ = Cycle.objects.get_or_create(
            code='SEC',
            etablissement=etab,
            defaults={
                'nom': 'Secondaire',
                'ordre': 4,
                'actif': True
            }
        )
        
        classe, _ = Classe.objects.get_or_create(
            nom='6e',
            cycle=cycle,
            etablissement=etab,
            defaults={
                'nom': 'Sixième',
                'niveau': '6e'
            }
        )
        
        inscription = Inscription.objects.create(
            eleve=self.eleve,
            annee_scolaire=annee,
            classe=classe,
            statut=StatutInscriptionChoices.AFFECTE
        )
        
        # Le numéro de reçu n'est plus auto-généré
        self.assertEqual(inscription.numero_recu, '')
