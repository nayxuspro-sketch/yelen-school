"""Force le remplacement du mot de passe initial avant l'accès à l'application."""


class ForcePasswordChangeMiddleware:
    """Redirige un compte marqué vers son profil jusqu'au changement de secret."""

    _ALLOWED_PREFIXES = (
        '/accounts/profile/',
        '/accounts/logout/',
        '/static/',
        '/media/',
        '/health/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path_info
        if (
            user is not None
            and user.is_authenticated
            and getattr(user, 'must_change_password', False)
            and not path.startswith(self._ALLOWED_PREFIXES)
        ):
            from django.shortcuts import redirect
            return redirect('accounts:profile')
        return self.get_response(request)
