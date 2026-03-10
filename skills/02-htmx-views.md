# Skill 02 — HTMX Views Expert

## Rôle
Tu es expert en vues Django avec HTMX pour YELEN SCHOOL.
Pas de React, pas de Vue — uniquement HTMX pour toutes les interactions.

## Règles obligatoires

### Vues
- Toutes les vues héritent de LoginRequiredMixin
- Vérification des permissions par rôle (Directeur, AVS, Secrétaire)
- Retourner des partial HTML pour les requêtes HTMX
- Toujours vérifier request.htmx avant de retourner une partial

### Patterns HTMX
- hx-get    : chargement de contenu sans rechargement page
- hx-post   : soumission formulaire sans rechargement
- hx-target : cibler un élément précis du DOM
- hx-swap   : innerHTML par défaut, outerHTML si remplacement total
- hx-confirm: toujours sur les actions de suppression

### Sécurité
- csrf_token obligatoire sur tous les formulaires
- @login_required ou LoginRequiredMixin sur toutes les vues
- Vérification du rôle utilisateur avant chaque action

### URLs
- Namespace par app : app_name = 'nom_app'
- Nommage : nom_app:action_objet (ex: eleves:liste, eleves:detail)