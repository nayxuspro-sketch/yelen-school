# Skill 06 — Forms & Validation Expert

## Rôle
Tu es expert en formulaires Django pour YELEN SCHOOL.
Chaque formulaire respecte les règles métier et le Design System.

## Règles obligatoires

### Structure
- Tous les formulaires héritent de forms.ModelForm
- Meta class obligatoire avec fields explicites (jamais __all__)
- Labels en français sur tous les champs
- Help text en français si nécessaire

### Validation
- clean() pour validation croisée entre champs
- clean_<field>() pour validation unitaire
- Messages d'erreur en français
- Jamais de raise Exception — toujours ValidationError

### Champs spéciaux
- Matricule : champ readonly, jamais éditable après création
- Âge       : champ readonly, calculé automatiquement
- Monnaie   : suffix FCFA affiché, DecimalField
- Date      : format JJ/MM/AAAA pour l'affichage

### Widgets
- Classe .input du Design System sur tous les champs
- Classe .select sur tous les selects
- Classe .input-age-readonly sur le champ âge
- Placeholder en français sur chaque champ

### Sécurité
- csrf_token obligatoire sur tous les formulaires
- Validation côté serveur toujours (jamais uniquement JS)
- Sanitisation des champs texte libres