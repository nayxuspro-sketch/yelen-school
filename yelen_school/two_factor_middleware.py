"""Impose la double authentification aux rôles sensibles avant tout accès à l'application."""
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse


class ForceTwoFactorMiddleware:
    """Redirige un Super Admin ou un Directeur sans 2FA vers l'activation TOTP.

    Le changement de mot de passe initial (ForcePasswordChangeMiddleware) reste
    prioritaire. Les écrans de licence sont exemptés pour ne pas entrer en boucle
    avec le contrôle de licence.
    """

    _ALLOWED_PREFIXES = (
        '/accounts/profile/2fa/',
        '/accounts/logout/',
        '/licences/',
        '/static/',
        '/media/',
        '/health/',
    )
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            settings.TWO_FACTOR_REQUIRED
            and user is not None
            and user.is_authenticated
            and getattr(user, 'two_factor_obligatoire', False)
            and not user.totp_enabled
            and not getattr(user, 'must_change_password', False)
            and not request.path_info.startswith(self._ALLOWED_PREFIXES)
        ):
            url = reverse('accounts:totp_setup')
            if request.headers.get('HX-Request') == 'true':
                return HttpResponse(status=204, headers={'HX-Redirect': url})
            return redirect(url)
        return self.get_response(request)
