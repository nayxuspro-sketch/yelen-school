"""
yelen_school/role_middleware.py — Restriction d'accès par rôle
===============================================================
Bloque les utilisateurs avec le rôle PARENT ou ÉLÈVE sur toutes les URLs
qui ne leur sont pas explicitement destinées, et les redirige vers leur portail.

Rôle PARENT  → accès limité à : /accounts/, /portail/parent/, /notifications/
Rôle ÉLÈVE   → accès limité à : /accounts/, /portail/eleve/, /notifications/
"""

from django.shortcuts import redirect


# Préfixes autorisés communs aux deux rôles restreints
_COMMON_ALLOWED = (
    '/accounts/',     # login, logout, changement de mot de passe
    '/notifications/', # badge et liste des notifications
    '/static/',       # fichiers statiques
    '/media/',        # fichiers médias (photos élèves, logos)
)

_ROLE_CONFIG = {
    'PARENT': {
        'allowed_extra': ('/portail/parent/',),
        'redirect': 'core:portail_parent',
    },
    'ELEVE': {
        'allowed_extra': ('/portail/eleve/',),
        'redirect': 'core:portail_eleve',
    },
}


class RoleAccessMiddleware:
    """
    Empêche les rôles PARENT et ÉLÈVE d'accéder aux modules de gestion
    (finances, inscriptions, bulletins, personnel, etc.).
    Les requêtes non autorisées sont redirigées vers le portail dédié.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            role = getattr(request.user, 'role', None)
            config = _ROLE_CONFIG.get(role)

            if config:
                path = request.path_info
                allowed = _COMMON_ALLOWED + config['allowed_extra']

                # Autoriser la racine "/" (redirigée dans core.views.home)
                if path != '/' and not any(path.startswith(p) for p in allowed):
                    return redirect(config['redirect'])

        return self.get_response(request)
