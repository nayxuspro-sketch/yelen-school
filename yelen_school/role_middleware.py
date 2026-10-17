"""
yelen_school/role_middleware.py — Restriction d'accès par rôle
===============================================================
Bloque les utilisateurs avec le rôle PARENT ou ÉLÈVE sur toutes les URLs
qui ne leur sont pas explicitement destinées, et les redirige vers leur portail.

Rôle PARENT  → accès limité à : /accounts/, /portail/parent/, /notifications/
Rôle ÉLÈVE   → accès limité à : /accounts/, /portail/eleve/, /notifications/

Pour les autres rôles, l'accès aux modules (espace de noms d'URL) et à leurs
fonctionnalités (préfixes d'URL du menu) suit la matrice des droits d'accès
administrée par le Super Admin (``parametres.droits``).
"""

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from core.models import RoleChoices
from parametres.droits import CODES_MODULES, acces_autorise, libelle_module


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

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Applique la matrice des droits d'accès aux modules du personnel."""
        user = request.user
        if not user.is_authenticated or getattr(user, 'role', None) in (
            RoleChoices.SUPER_ADMIN, RoleChoices.PARENT, RoleChoices.ELEVE,
        ):
            return None
        module = request.resolver_match.app_name if request.resolver_match else None
        if module not in CODES_MODULES or acces_autorise(request, module, request.path_info):
            return None
        if request.headers.get('HX-Request'):
            return HttpResponseForbidden("Module non autorisé pour votre rôle.")
        messages.error(request, f"Accès au module « {libelle_module(module)} » non autorisé pour votre rôle.")
        return redirect('/')
