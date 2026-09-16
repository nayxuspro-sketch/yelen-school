"""Barrière RBAC commune au module financier."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from core.models import RoleChoices


FINANCE_VIEW_ROLES = frozenset({
    RoleChoices.SUPER_ADMIN,
    RoleChoices.DIRECTEUR,
    RoleChoices.CENSEUR,
    RoleChoices.COMPTABLE,
})
FINANCE_WRITE_ROLES = frozenset({
    RoleChoices.SUPER_ADMIN,
    RoleChoices.DIRECTEUR,
    RoleChoices.COMPTABLE,
})
FINANCE_APPROVER_ROLES = frozenset({
    RoleChoices.SUPER_ADMIN,
    RoleChoices.DIRECTEUR,
})


class FinanceAccessMiddleware:
    """Refuse le module financier aux rôles non financiers.

    Le lien public Mobile Money ``/finances/payer/<token>/`` reste accessible
    sans session : il n'expose que la confirmation destinée au parent.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if (
            path.startswith('/finances/')
            and not path.startswith('/finances/payer/')
            and request.user.is_authenticated
            and getattr(request.user, 'role', None) not in FINANCE_VIEW_ROLES
        ):
            raise PermissionDenied("Accès au module financier non autorisé pour ce rôle.")
        return self.get_response(request)
