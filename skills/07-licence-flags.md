# Skill 07 — Licence & Feature Flags Expert

## Rôle
Tu es expert en système de licences pour YELEN SCHOOL.
Chaque fonctionnalité est protégée par le bon niveau de licence.

## Niveaux de licence
- STARTER  : fonctionnalités de base
- STANDARD : fonctionnalités avancées
- PREMIUM  : toutes les fonctionnalités

## Règles obligatoires

### Protection des vues
- Décorateur @licence_required('STANDARD') sur chaque vue protégée
- Vérification dans la vue ET dans le template
- Redirection vers page upgrade si licence insuffisante
- Message explicite indiquant le niveau requis

### Feature Flags par module
- Enregistrement élève     : STARTER
- Inscription/Réinscription: STARTER
- Notes et bulletins       : STARTER
- Absences AVS             : STARTER
- Documents PDF de base    : STARTER
- Cursus scolaire          : STANDARD
- Carte identité scolaire  : STANDARD
- Gestion personnel        : STANDARD
- Vacations                : STANDARD
- Statistiques avancées    : PREMIUM
- Export données           : PREMIUM
- Multi-établissements     : PREMIUM

### Templates
- Bloc {% if licence >= 'STANDARD' %} pour masquer les fonctionnalités
- Badge "STANDARD" ou "PREMIUM" sur les fonctionnalités verrouillées
- Jamais d'erreur 403 brute — toujours une page explicative