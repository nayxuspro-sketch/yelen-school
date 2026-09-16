"""Expiration d'inactivité des sessions authentifiées."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone


class SessionSecurityMiddleware:
    """Déconnecte une session inactive au-delà du délai configuré."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            now = int(timezone.now().timestamp())
            last_activity = request.session.get("_yelen_last_activity")
            timeout = int(getattr(settings, "SESSION_IDLE_TIMEOUT", 1800))
            try:
                last_activity_value = int(last_activity) if last_activity is not None else None
            except (TypeError, ValueError):
                last_activity_value = None
            if last_activity is not None and last_activity_value is None:
                logout(request)
                return redirect("accounts:login")
            if last_activity_value is not None and now - last_activity_value > timeout:
                logout(request)
                if request.path_info.startswith("/api/"):
                    from django.http import JsonResponse
                    return JsonResponse(
                        {"detail": "Session expirée pour inactivité."},
                        status=401,
                    )
                return redirect("accounts:login")
            request.session["_yelen_last_activity"] = now
            request.session.modified = True
        return self.get_response(request)
