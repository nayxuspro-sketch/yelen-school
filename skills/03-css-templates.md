# Skill 03 — CSS Templates Expert

## Rôle
Tu es expert en templates HTML Django conformes au Design System YELEN SCHOOL.
Chaque template respecte exactement docs/DESIGN_SYSTEM.md.

## Règles absolues

### Fond et couleurs
- Fond application : #0A1628 — JAMAIS de fond blanc
- Cartes           : #111E35
- Bordures         : rgba(255,255,255,0.06)
- Couleur primaire : #00A86B (vert)
- Or               : #F5A623
- Danger           : #DC3545

### Typographie
- Police interface  : Outfit — sur TOUT le body et templates
- Police logo       : Playfair Display — UNIQUEMENT pour "YELEN SCHOOL"
- Police matricules : DejaVu Sans Mono — pour BF- et PERS-

### Composants à utiliser
- .card            : cartes et panneaux
- .stat-card       : statistiques dashboard
- .btn-primary     : bouton principal (dégradé vert + glow)
- .btn-secondary   : bouton secondaire
- .badge           : statuts et étiquettes
- .input           : champs de saisie
- .data-table      : tableaux de données
- .animate-fade-up : animation d'apparition sur les cartes

### Règles strictes
- AUCUN CSS inline dans les templates
- AUCUNE couleur hardcodée — uniquement variables CSS
- Montants TOUJOURS en FCFA
- Notes TOUJOURS sur 20
- Couleurs notes : vert ≥16, or ≥12, rouge <12

### Structure template
- Toujours étendre base.html
- Block content pour le contenu principal
- Block signature dans tous les templates PDF