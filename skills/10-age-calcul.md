# Skill 10 — Age Calcul Expert

## Rôle
Tu es expert en calcul automatique de l'âge pour YELEN SCHOOL.
L'âge n'est jamais saisi manuellement — toujours calculé depuis date_naissance.

## Règles obligatoires

### Modèle
- date_naissance : DateField obligatoire sur ElèveEnregistre et MembrePersonnel
- age            : Property calculé dynamiquement, jamais stocké en base
- Affichage      : "X ans" à la date du jour

### Calcul
- Utiliser relativedelta (dateutil) pour un calcul précis
- Tenir compte du jour et mois d'anniversaire
- Recalculé automatiquement à chaque accès

### Exemple de code
```python
from dateutil.relativedelta import relativedelta
from datetime import date

@property
def age(self):
    if self.date_naissance:
        delta = relativedelta(date.today(), self.date_naissance)
        return delta.years
    return None

@property
def age_display(self):
    age = self.age
    if age is not None:
        return f"{age} ans"
    return "Non renseigné"
```

### Formulaires
- Champ âge      : toujours readonly (.input-age-readonly)
- Mis à jour     : via HTMX au changement de date_naissance
- Jamais éditable par l'utilisateur

### Affichage
- Format         : "X ans"
- Classe CSS     : .input-age-readonly sur le champ
- Couleur        : var(--color-text-muted) pour indiquer lecture seule