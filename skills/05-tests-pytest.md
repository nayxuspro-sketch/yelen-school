# Skill 05 — Tests Pytest Expert

## Rôle
Tu es expert en tests automatisés pour YELEN SCHOOL.
Coverage minimum obligatoire : 80% sur chaque app.

## Stack de test
- pytest + pytest-django
- model_bakery pour les fixtures
- coverage pour le rapport

## Règles obligatoires

### Structure
- Un fichier tests/ par app
- Nommage : test_models.py, test_views.py, test_forms.py
- Chaque test commence par test_
- Docstring obligatoire sur chaque fonction de test

### Fixtures
- Utiliser model_bakery.baker.make() pour créer les objets
- Jamais de données hardcodées dans les tests
- Fixtures pytest pour les objets réutilisables

### Marqueurs
- @pytest.mark.slow        : tests lents (PDF, etc.)
- @pytest.mark.integration : tests multi-modules
- @pytest.mark.matricule   : tests génération BF- et PERS-
- @pytest.mark.age_calcule : tests calcul automatique âge
- @pytest.mark.signataire  : tests SignataireDocument

### Cas à tester obligatoirement
- Génération matricule unique BF-AAAA-NNNNN
- Calcul automatique de l'âge depuis date_naissance
- Unicité contrainte (cycle × type_document × annee_scolaire)
- Feature Flags selon niveau de licence
- Fallback signataire sur IdentiteEtablissement

### Commandes
- pytest --cov=. --cov-report=html --cov-fail-under=80