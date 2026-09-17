"""
Module Licences - Decorators
=============================
YELEN SCHOOL v3.4 - Décorateurs pour contrôle d'accès par Feature Flags

Fournit les décorateurs et fonctions utilitaires pour vérifier
les permissions basées sur le niveau de licence de l'établissement.

Usage:
    @requires_licence_feature('cursus_scolaire')
    def ma_vue(request):
        # Cette vue nécessite au minimum une licence Standard
        ...

Auteur: YELEN SCHOOL Team
Date: Mars 2026
"""

from functools import wraps
from typing import Callable, Optional

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page

from .models import Licence, FEATURE_FLAGS


# ═══════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════

def _enforcement_actif() -> bool:
    """Le contrôle des licences est-il actif (settings.LICENSE_ENFORCEMENT) ?

    Quand le contrôle est inactif (développement / démo / tests), tous les
    garde-fous de ce module deviennent transparents : aucun blocage, toutes
    les features sont considérées disponibles — comportement identique à
    l'application avant l'activation du contrôle.
    """
    return bool(getattr(settings, 'LICENSE_ENFORCEMENT', False))


def get_licence_active(etablissement) -> Optional[Licence]:
    """
    Récupère la licence active d'un établissement.
    
    Args:
        etablissement: Instance d'Etablissement
        
    Returns:
        Licence active ou None
    """
    try:
        licence = etablissement.licence
        if licence.est_active():
            return licence
        return None
    except Licence.DoesNotExist:
        return None


def has_feature(user, feature_name: str) -> bool:
    """
    Vérifie si un utilisateur a accès à une fonctionnalité.
    
    Args:
        user: Instance User Django
        feature_name: Nom de la feature (ex: 'cursus_scolaire')
        
    Returns:
        bool: True si l'utilisateur peut utiliser cette feature
    """
    # Contrôle inactif : toutes les features sont disponibles
    if not _enforcement_actif():
        return True

    # Vérifier que l'utilisateur a un établissement
    if not hasattr(user, 'etablissement') or user.etablissement is None:
        return False

    # Récupérer la licence active
    licence = get_licence_active(user.etablissement)

    if not licence:
        return False

    # Vérifier si la feature est disponible pour ce niveau de licence
    return licence.peut_utiliser_feature(feature_name)


def get_features_disponibles(user) -> list:
    """
    Retourne toutes les features disponibles pour un utilisateur.
    
    Args:
        user: Instance User Django
        
    Returns:
        list: Liste des noms de features accessibles
    """
    # Contrôle inactif : toutes les features sont disponibles
    if not _enforcement_actif():
        return list(FEATURE_FLAGS.keys())

    if not hasattr(user, 'etablissement') or user.etablissement is None:
        return []

    licence = get_licence_active(user.etablissement)

    if not licence:
        return []

    return licence.get_features_disponibles()


def get_niveau_licence(user) -> Optional[str]:
    """
    Récupère le niveau de licence d'un utilisateur.
    
    Args:
        user: Instance User Django
        
    Returns:
        str: Type de licence (STARTER, STANDARD, PREMIUM, RESEAU) ou None
    """
    if not hasattr(user, 'etablissement') or user.etablissement is None:
        return None
    
    licence = get_licence_active(user.etablissement)
    
    if not licence:
        return None
    
    return licence.type_licence


# ═══════════════════════════════════════════════════════════════════
# DÉCORATEUR PRINCIPAL : @requires_licence_feature
# ═══════════════════════════════════════════════════════════════════

def requires_licence_feature(
    feature_name: str,
    redirect_url: str = '/licences/mon-abonnement/',
    raise_exception: bool = False,
    api_mode: bool = False
):
    """
    Décorateur pour protéger une vue avec un Feature Flag.
    
    Vérifie que l'utilisateur connecté possède une licence active
    avec accès à la fonctionnalité demandée.
    
    Args:
        feature_name: Nom de la feature requise
        redirect_url: URL de redirection si accès refusé (mode web)
        raise_exception: Si True, lève PermissionDenied au lieu de rediriger
        api_mode: Si True, retourne JSON 403 au lieu de rediriger
        
    Usage:
        @requires_licence_feature('cursus_scolaire')
        def vue_cursus(request):
            # Accessible uniquement avec licence Standard ou supérieure
            ...
        
        @requires_licence_feature('ia_predictive', api_mode=True)
        def api_predictions(request):
            # API accessible uniquement avec licence Premium ou Réseau
            ...
    
    Returns:
        Decorated function
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        @login_required
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Contrôle inactif (développement / démo) : vue non restreinte
            if not _enforcement_actif():
                return view_func(request, *args, **kwargs)

            user = request.user

            # Vérifier que l'utilisateur a un établissement
            if not hasattr(user, 'etablissement') or user.etablissement is None:
                return _handle_access_denied(
                    request,
                    "Aucun établissement associé à votre compte.",
                    redirect_url,
                    raise_exception,
                    api_mode
                )
            
            # Récupérer la licence active
            licence = get_licence_active(user.etablissement)
            
            if not licence:
                return _handle_access_denied(
                    request,
                    "Aucune licence active trouvée pour votre établissement.",
                    redirect_url,
                    raise_exception,
                    api_mode,
                    show_upgrade=True
                )
            
            # Vérifier l'accès à la feature
            if not licence.peut_utiliser_feature(feature_name):
                # Récupérer les niveaux requis pour cette feature
                niveaux_requis = FEATURE_FLAGS.get(feature_name, [])
                
                message = (
                    f"Cette fonctionnalité nécessite une licence "
                    f"{', '.join(niveaux_requis)}. "
                    f"Votre licence actuelle : {licence.get_type_licence_display()}."
                )
                
                return _handle_access_denied(
                    request,
                    message,
                    redirect_url,
                    raise_exception,
                    api_mode,
                    show_upgrade=True,
                    current_licence=licence.type_licence,
                    required_levels=niveaux_requis
                )
            
            # Accès autorisé
            return view_func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


def _handle_access_denied(
    request: HttpRequest,
    message: str,
    redirect_url: str,
    raise_exception: bool,
    api_mode: bool,
    show_upgrade: bool = False,
    current_licence: str = None,
    required_levels: list = None
) -> HttpResponse:
    """
    Gère le refus d'accès à une fonctionnalité.
    
    Args:
        request: Requête HTTP
        message: Message d'erreur
        redirect_url: URL de redirection
        raise_exception: Lever une exception
        api_mode: Mode API (JSON)
        show_upgrade: Afficher le bouton d'upgrade
        current_licence: Niveau de licence actuel
        required_levels: Niveaux requis
        
    Returns:
        HttpResponse appropriée
    """
    # Mode exception
    if raise_exception:
        raise PermissionDenied(message)
    
    # Mode API
    if api_mode:
        response_data = {
            'error': 'licence_insuffisante',
            'message': message,
            'upgrade_required': show_upgrade
        }
        
        if current_licence:
            response_data['current_licence'] = current_licence
        
        if required_levels:
            response_data['required_levels'] = required_levels
        
        return JsonResponse(response_data, status=403)
    
    # Mode web classique
    messages.error(request, message)
    
    if show_upgrade:
        messages.info(
            request,
            _("Contactez-nous pour upgrader votre licence et débloquer cette fonctionnalité.")
        )
    
    return redirect(redirect_url)


# ═══════════════════════════════════════════════════════════════════
# DÉCORATEUR : @check_licence_validity (vérification générale)
# ═══════════════════════════════════════════════════════════════════

def check_licence_validity(view_func: Callable) -> Callable:
    """
    Décorateur pour vérifier uniquement la validité de la licence.
    
    Plus permissif que @requires_licence_feature : vérifie juste
    que l'établissement a UNE licence active, peu importe le niveau.
    
    Usage:
        @check_licence_validity
        def tableau_bord(request):
            # Accessible avec n'importe quelle licence active
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        # Contrôle inactif (développement / démo) : vue non restreinte
        if not _enforcement_actif():
            return view_func(request, *args, **kwargs)

        user = request.user

        # Vérifier l'établissement
        if not hasattr(user, 'etablissement') or user.etablissement is None:
            messages.error(request, _("Aucun établissement associé à votre compte."))
            return redirect('accounts:profile')
        
        # Vérifier la licence
        licence = get_licence_active(user.etablissement)
        
        if not licence:
            messages.error(
                request,
                _("Votre établissement n'a pas de licence active. "
                  "Veuillez contacter l'administrateur.")
            )
            return redirect('licences:activer')
        
        # Licence active : accès autorisé
        return view_func(request, *args, **kwargs)
    
    return wrapper


# ═══════════════════════════════════════════════════════════════════
# DÉCORATEUR : @licence_feature_required (pour les vues basées sur classe)
# ═══════════════════════════════════════════════════════════════════

class LicenceFeatureMixin:
    """
    Mixin pour les vues basées sur classe (CBV).
    
    Usage:
        class CursusView(LicenceFeatureMixin, TemplateView):
            required_feature = 'cursus_scolaire'
            template_name = 'cursus.html'
    """
    
    required_feature: str = None
    redirect_url: str = '/licences/mon-abonnement/'
    raise_exception: bool = False
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch pour vérifier la licence."""
        if not self.required_feature:
            raise ValueError(
                "LicenceFeatureMixin nécessite l'attribut 'required_feature'"
            )
        
        # Contrôle inactif (développement / démo) : vue non restreinte
        if not _enforcement_actif():
            return super().dispatch(request, *args, **kwargs)

        user = request.user

        # Vérifier l'authentification
        if not user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())

        # Vérifier l'établissement
        if not hasattr(user, 'etablissement') or user.etablissement is None:
            messages.error(request, _("Aucun établissement associé."))
            return redirect('accounts:profile')
        
        # Vérifier la licence et la feature
        licence = get_licence_active(user.etablissement)
        
        if not licence:
            messages.error(request, _("Aucune licence active."))
            return redirect('licences:activer')
        
        if not licence.peut_utiliser_feature(self.required_feature):
            niveaux_requis = FEATURE_FLAGS.get(self.required_feature, [])
            message = (
                f"Cette fonctionnalité nécessite une licence "
                f"{', '.join(niveaux_requis)}."
            )
            
            if self.raise_exception:
                raise PermissionDenied(message)
            
            messages.error(request, message)
            return redirect(self.redirect_url)
        
        # Accès autorisé
        return super().dispatch(request, *args, **kwargs)


# ═══════════════════════════════════════════════════════════════════
# DÉCORATEUR SPÉCIAL : @cache_by_licence (cache par niveau de licence)
# ═══════════════════════════════════════════════════════════════════

def cache_by_licence(timeout: int = 300):
    """
    Cache une vue en fonction du niveau de licence.
    
    Permet d'avoir des caches différents pour chaque niveau de licence,
    évitant ainsi les fuites de données entre niveaux.
    
    Args:
        timeout: Durée du cache en secondes (défaut 5 min)
        
    Usage:
        @cache_by_licence(timeout=600)
        @requires_licence_feature('rapports_avances')
        def rapports_dashboard(request):
            # Cache séparé pour Premium vs Réseau
            ...
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            # Déterminer la clé de cache basée sur le niveau de licence
            niveau = get_niveau_licence(request.user)
            cache_key = f"view_{view_func.__name__}_{niveau}"
            
            # Utiliser le cache Django standard avec clé personnalisée
            from django.core.cache import cache
            
            result = cache.get(cache_key)
            
            if result is not None:
                return result
            
            # Exécuter la vue et mettre en cache
            result = view_func(request, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        
        return wrapper
    
    return decorator


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE TAG HELPER (pour utilisation dans les templates)
# ═══════════════════════════════════════════════════════════════════

def user_has_feature(user, feature_name: str) -> bool:
    """
    Alias de has_feature pour utilisation dans les template tags.
    
    Usage dans un template tag:
        {% if user|has_feature:'cursus_scolaire' %}
            <a href="{% url 'cursus' %}">Cursus scolaire</a>
        {% endif %}
    """
    return has_feature(user, feature_name)


def get_licence_info(user) -> dict:
    """
    Retourne les informations complètes de licence pour un utilisateur.
    
    Utile pour afficher le badge de licence, les limites, etc.
    
    Returns:
        dict: {
            'type': 'PREMIUM',
            'type_display': '🥇 Premium - Licence Intégrale',
            'jours_restants': 45,
            'est_active': True,
            'features': ['inscriptions', 'notes_bulletins', ...]
        }
    """
    if not hasattr(user, 'etablissement') or user.etablissement is None:
        return None
    
    licence = get_licence_active(user.etablissement)
    
    if not licence:
        return None
    
    return {
        'type': licence.type_licence,
        'type_display': licence.get_type_licence_display(),
        'jours_restants': licence.jours_restants(),
        'est_active': licence.est_active(),
        'date_expiration': licence.date_expiration,
        'features': licence.get_features_disponibles(),
        'cle_licence': licence.cle_licence,
    }
