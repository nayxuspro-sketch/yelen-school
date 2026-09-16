"""Force l'enrôlement 2FA des rôles privilégiés."""

from __future__ import annotations

from django.conf import settings
from django.shortcuts import redirect

from core.models import RoleChoices


REQUIRED_2FA_ROLES = frozenset({
    RoleChoices.SUPER_ADMIN,
    RoleChoices.DIRECTEUR_RESEAU,
    RoleChoices.DIRECTEUR,
    RoleChoices.CENSEUR,
    RoleChoices.COMPTABLE,
})


class TwoFactorRequiredMiddleware:
    """Limite un compte privilégié non enrôlé aux pages d'enrôlement."""

    ALLOWED_PREFIXES = (
        "/accounts/profile/",
        "/accounts/login/",
        "/accounts/logout/",
        "/static/",
        "/media/",
        "/health/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and getattr(user, "role", None) in REQUIRED_2FA_ROLES
            and not getattr(user, "totp_enabled", False)
            and not request.path_info.startswith(self.ALLOWED_PREFIXES)
        ):
            return redirect("accounts:totp_setup")
        return self.get_response(request)
