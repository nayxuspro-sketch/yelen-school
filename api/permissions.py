"""
api/permissions.py — Permissions RBAC de l'API YELEN SCHOOL
============================================================

Cloisonnement des données par rôle (RBAC) :

- SUPER_ADMIN / DIRECTEUR_RESEAU  → tous les établissements
- Staff (DIRECTEUR, CENSEUR, AVS, ENSEIGNANT, COMPTABLE, SECRETAIRE)
                                   → leur établissement uniquement
- PARENT                           → uniquement ses enfants (eleves_lies)
- ELEVE                            → uniquement lui-même (eleves_lies)

Aucun rôle ne peut lire les données d'un élève hors de son périmètre :
en cas de dépassement, les vues répondent 404 (pas de fuite
d'existence de l'élève).
"""

from rest_framework.permissions import BasePermission

from core.models import RoleChoices

# Rôles « staff » : personnel de l'établissement (tout sauf PARENT/ELEVE)
STAFF_ROLES = frozenset({
    RoleChoices.SUPER_ADMIN,
    RoleChoices.DIRECTEUR_RESEAU,
    RoleChoices.DIRECTEUR,
    RoleChoices.CENSEUR,
    RoleChoices.AVS,
    RoleChoices.ENSEIGNANT,
    RoleChoices.COMPTABLE,
    RoleChoices.SECRETAIRE,
})

# Rôles pouvant accéder aux données « élèves » (avec périmètre restreint)
ELEVE_DATA_ROLES = frozenset(STAFF_ROLES | {RoleChoices.PARENT, RoleChoices.ELEVE})


def role_utilisateur(user) -> str:
    """Rôle de l'utilisateur (vide si champ absent)."""
    return getattr(user, 'role', '') or ''


class IsStaffRole(BasePermission):
    """Autorise les rôles staff (personnel), refuse PARENT/ELEVE/anonyme."""

    message = "Accès réservé au personnel de l'établissement."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return role_utilisateur(user) in STAFF_ROLES


class EleveScopeAccess(BasePermission):
    """Autorise l'accès aux endpoints « données élève ».

    Le contrôle FINE du périmètre (quels élèves précisément) est fait
    dans les vues via api.views.eleves_visibles / get_eleve_scope :
    ici on s'assure que le rôle est autorisé à consulter des données
    élève et que l'utilisateur a un périmètre non vide.
    """

    message = "Accès non autorisé aux données des élèves."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        role = role_utilisateur(user)
        if role not in ELEVE_DATA_ROLES:
            return False
        if role in (RoleChoices.PARENT, RoleChoices.ELEVE):
            # Un parent/élève sans élève lié n'a pas de périmètre :
            # on refuse d'entrée (leurs listes seraient vides de toute
            # façon — le refus explicite documente mieux l'API).
            return user.eleves_lies.exists()
        return True
