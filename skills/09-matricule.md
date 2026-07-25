# Skill 09 — Matricule System Expert

## Rôle
Tu es expert en génération et validation des matricules pour YELEN SCHOOL.
Les matricules sont l'identifiant unique et permanent de chaque personne.

## Formats

### Élève
- Format   : {CODE_ETAB}-AAAA-NN
- Exemple  : 01-2026-5
- CODE_ETAB : code de l'établissement
- AAAA     : année d'enregistrement
- NN       : numéro d'enregistrement

### Personnel
- Format   : {CODE_ETAB}-P-AAAA-NN
- Exemple  : 01-P-2026-2
- CODE_ETAB : code de l'établissement
- P        : Personnel
- AAAA     : année d'enregistrement
- NN       : numéro d'enregistrement

## Règles obligatoires

### Génération
- Généré automatiquement dans la méthode save() du modèle
- Jamais généré dans une vue ou un formulaire
- Utiliser transaction.atomic() pour garantir l'unicité
- select_for_update() pour éviter les doublons en concurrence

### Immutabilité
- Jamais modifiable après création
- Champ readonly dans tous les formulaires
- Pas de migration permettant de modifier un matricule existant

### Unicité
- Contrainte unique en base de données
- Vérification applicative ET contrainte SQL
- Index sur le champ matricule pour les performances

### Affichage
- Toujours en police DejaVu Sans Mono
- Toujours en majuscules
- Copie dans le presse-papier au clic