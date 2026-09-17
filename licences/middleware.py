"""
Module Licences - Middleware
=============================
YELEN SCHOOL v3.4 - Middleware de vérification automatique des licences

Vérifie à chaque requête :
- La validité de la licence (expiration, signature HMAC)
- Le respect des limites (nombre d'élèves, enseignants)
- Génère les alertes d'expiration automatiques

Auteur: YELEN SCHOOL Team  
Date: Mars 2026
"""

from datetime import timedelta
from typing import Callable

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Licence, LicenceAlert, LicenceAuditLog, StatutLicence


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

class LicenceCheckMiddleware:
    """
    Middleware de vérification des licences.
    
    S'exécute à chaque requête pour :
    1. Vérifier la validité de la licence
    2. Mettre à jour le statut si expirée
    3. Créer les alertes d'expiration
    4. Bloquer l'accès si licence invalide
    
    Configuration dans settings.py:
        MIDDLEWARE = [
            ...
            'licences.middleware.LicenceCheckMiddleware',
        ]
    """
    
    # URLs exemptées de vérification (toujours accessibles)
    # - /licences/ : l'ensemble du module licences doit rester atteignable
    #   pour permettre la création / activation / renouvellement d'une
    #   licence (onboarding) et la résolution d'un blocage. Les actions
    #   sensibles restent protégées au niveau des vues (superuser requis).
    # - /admin/ n'est PAS exempté : l'admin est soumis au contrôle
    #   (un superuser avec licence expirée/absente n'y a pas accès).
    EXEMPTED_URLS = [
        '/accounts/login/',
        '/accounts/logout/',
        '/licences/',
        '/static/',
        '/media/',
        '/__debug__/',
    ]
    
    # Fréquence de vérification (éviter de surcharger la DB)
    CACHE_TIMEOUT = 300  # 5 minutes
    
    def __init__(self, get_response: Callable):
        """Initialise le middleware."""
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Traite chaque requête.
        
        Args:
            request: Requête HTTP Django
            
        Returns:
            HttpResponse
        """
        # Vérifier si l'URL est exemptée
        if self._is_exempted_url(request.path):
            return self.get_response(request)
        
        # Vérifier uniquement pour les utilisateurs authentifiés
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # NOTE : plus de bypass superuser — le compte superuser d'un
        # déploiement école est soumis au contrôle de licence comme tout
        # autre utilisateur (il reste libre de gérer les licences via
        # /licences/, exempté ci-dessus).
        
        # Vérifier que l'utilisateur a un établissement
        if not hasattr(request.user, 'etablissement') or request.user.etablissement is None:
            # Pas d'établissement : rediriger vers configuration du profil
            if request.path != reverse('accounts:profile'):
                messages.warning(
                    request,
                    _("Veuillez compléter votre profil et associer un établissement.")
                )
                return redirect('accounts:profile')
            return self.get_response(request)
        
        # Récupérer la licence de l'établissement
        etablissement = request.user.etablissement
        
        try:
            licence = etablissement.licence
        except Licence.DoesNotExist:
            # Pas de licence : rediriger vers activation
            if request.path != reverse('licences:activer'):
                messages.error(
                    request,
                    _("Votre établissement n'a pas de licence. "
                      "Veuillez activer une licence pour accéder à l'application.")
                )
                return redirect('licences:activer')
            return self.get_response(request)
        
        # Vérifier la licence avec cache
        cache_key = f'licence_check_{licence.id}'
        cached_status = cache.get(cache_key)
        
        if cached_status is None:
            # Cache expiré : vérifier la licence
            is_valid, redirect_response = self._check_licence(request, licence)
            
            if not is_valid:
                return redirect_response
            
            # Mettre en cache le résultat positif
            cache.set(cache_key, 'valid', self.CACHE_TIMEOUT)
        
        # Licence valide : continuer
        return self.get_response(request)
    
    def _is_exempted_url(self, path: str) -> bool:
        """
        Vérifie si l'URL est exemptée de vérification.
        
        Args:
            path: Chemin de l'URL
            
        Returns:
            bool: True si exemptée
        """
        for exempted in self.EXEMPTED_URLS:
            if path.startswith(exempted):
                return True
        return False
    
    def _check_licence(self, request: HttpRequest, licence: Licence) -> tuple:
        """
        Vérifie la validité complète de la licence — P1 avec bail offline + binding.

        Args:
            request: Requête HTTP
            licence: Instance de Licence

        Returns:
            tuple: (is_valid: bool, redirect_response: HttpResponse or None)
        """
        # 1. Vérifier la signature (Ed25519 prioritaire, HMAC fallback) — P1
        if not licence.verifier_signature():
            self._log_audit(
                licence,
                'TENTATIVE_FRAUDE',
                "Signature invalide (Ed25519/HMAC) détectée",
                request
            )

            messages.error(
                request,
                _("⚠️ La signature de votre licence est invalide. "
                  "Contactez le support immédiatement.")
            )
            return False, redirect('licences:support')

        # 1b. Vérifier bail offline (phone-home) — P1 fenêtre décroissante
        try:
            if licence.bail_offline_expire_le and licence.is_bail_offline_expired():
                self._log_audit(
                    licence,
                    'EXPIRATION',
                    f"Bail offline expiré — dernier heartbeat {licence.dernier_heartbeat}, bail jusqu'à {licence.bail_offline_expire_le}",
                    request
                )
                messages.error(
                    request,
                    _("🔴 Bail offline expiré — votre licence n'a pas contacté le serveur éditeur depuis trop longtemps. "
                      "Vérifiez votre connexion internet ou contactez le support. Dernier heartbeat : {date}.").format(
                        date=licence.dernier_heartbeat.strftime('%d/%m/%Y %H:%M') if licence.dernier_heartbeat else "jamais"
                    )
                )
                return False, redirect('licences:support')
        except Exception:
            pass

        # 1c. Vérifier binding machine si activé — P1
        try:
            from django.conf import settings as _s
            if getattr(_s, 'LICENCE_BINDING_ENABLED', False):
                from .models import LicenceActivation
                activations = LicenceActivation.objects.filter(licence=licence, est_active=True)
                for act in activations:
                    if not act.verify_fingerprint():
                        self._log_audit(
                            licence,
                            'TENTATIVE_FRAUDE',
                            f"Binding machine invalide — activation {act.id} empreinte {act.machine_fingerprint}",
                            request
                        )
                        messages.error(
                            request,
                            _("🚫 Empreinte machine invalide — activation suspecte détectée. Contactez le support.")
                        )
                        return False, redirect('licences:support')
        except Exception:
            pass

        # 2. Vérifier l'expiration
        if licence.date_expiration < timezone.now().date():
            # Licence expirée : mettre à jour le statut
            if licence.statut != StatutLicence.EXPIREE:
                licence.statut = StatutLicence.EXPIREE
                licence.save()

                self._log_audit(
                    licence,
                    'EXPIRATION',
                    f"Licence expirée le {licence.date_expiration}",
                    request
                )

                # Créer une alerte
                self._creer_alerte_expiration(licence, 'EXPIREE')

            messages.error(
                request,
                _("🔴 Votre licence a expiré le {date}. "
                  "Veuillez la renouveler pour continuer à utiliser l'application.").format(
                    date=licence.date_expiration.strftime('%d/%m/%Y')
                )
            )
            return False, redirect('licences:renouveler')

        # 3. Vérifier si la licence est révoquée
        if licence.statut == StatutLicence.REVOQUEE:
            messages.error(
                request,
                _("🚫 Votre licence a été révoquée. Contactez le support.")
            )
            return False, redirect('licences:support')

        # 4. Générer les alertes d'expiration si nécessaire
        self._generer_alertes_expiration(licence)

        # 5. Mettre à jour la date de dernière vérification
        try:
            licence.derniere_verification = timezone.now()
            # Utiliser update_fields pour éviter de regénérer signature inutilement si date_activation inchangée
            # mais on doit quand même passer par save() qui regénère signature v2 (qui inclut date_activation, pas derniere_verification)
            # Donc on fait un update direct
            Licence.objects.filter(pk=licence.pk).update(derniere_verification=licence.derniere_verification)
        except Exception:
            pass

        # 6. Heartbeat opportuniste : si dû et URL configurée, on tente en arrière-plan (non bloquant)
        try:
            from django.conf import settings as _s
            if getattr(_s, 'LICENCE_HEARTBEAT_URL', '') and licence.is_heartbeat_required():
                # On ne bloque pas la requête, on lance heartbeat en thread ou on le marque pour cron
                # Ici, simple : on log, le vrai envoi se fait via management command cron
                pass
        except Exception:
            pass

        # Licence valide
        return True, None
    
    def _generer_alertes_expiration(self, licence: Licence) -> None:
        """
        Génère les alertes d'expiration automatiques.
        
        Crée des alertes à J-30, J-15, J-7, J-1 si elles n'existent pas.
        
        Args:
            licence: Instance de Licence
        """
        jours_restants = licence.jours_restants()
        
        # Définir les seuils d'alerte
        seuils = {
            30: 'J-30',
            15: 'J-15',
            7: 'J-7',
            1: 'J-1',
        }
        
        for seuil, type_alerte in seuils.items():
            if jours_restants <= seuil:
                # Vérifier si l'alerte existe déjà
                alerte_existe = LicenceAlert.objects.filter(
                    licence=licence,
                    type_alerte=type_alerte
                ).exists()
                
                if not alerte_existe:
                    # Créer l'alerte
                    LicenceAlert.objects.create(
                        licence=licence,
                        type_alerte=type_alerte
                    )
                    
                    # Logger dans l'audit
                    self._log_audit(
                        licence,
                        'VERIFICATION',
                        f"Alerte {type_alerte} créée ({jours_restants} jours restants)",
                        None
                    )
    
    def _creer_alerte_expiration(self, licence: Licence, type_alerte: str) -> None:
        """
        Crée une alerte d'expiration.
        
        Args:
            licence: Instance de Licence
            type_alerte: Type d'alerte
        """
        LicenceAlert.objects.create(
            licence=licence,
            type_alerte=type_alerte
        )
    
    def _log_audit(
            self,
            licence: Licence,
            action: str,
            description: str,
            request: HttpRequest | None = None,
    ) -> None:
        """
        Enregistre une entrée d'audit.
        
        Args:
            licence: Licence concernée
            action: Type d'action
            description: Description de l'action
            request: Requête HTTP (optionnel)
        """
        try:
            LicenceAuditLog.objects.create(
                licence=licence,
                action=action,
                description=description,
                acteur_user=request.user if request and request.user.is_authenticated else None,
                acteur_systeme=True if request is None else False,
                ip_address=self._get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            )
        except Exception:
            pass
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Récupère l'adresse IP réelle du client.
        
        Args:
            request: Requête HTTP
            
        Returns:
            str: Adresse IP
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE : VÉRIFICATION DES LIMITES
# ═══════════════════════════════════════════════════════════════════

class LicenceLimitsMiddleware:
    """
    Middleware de vérification des limites de licence.
    
    Vérifie que l'établissement ne dépasse pas les limites
    de sa licence (nombre d'élèves, enseignants, classes).
    
    S'exécute moins fréquemment que LicenceCheckMiddleware.
    
    Configuration:
        MIDDLEWARE = [
            ...
            'licences.middleware.LicenceCheckMiddleware',
            'licences.middleware.LicenceLimitsMiddleware',  # Après LicenceCheck
        ]
    """
    
    CACHE_TIMEOUT = 3600  # 1 heure
    
    def __init__(self, get_response: Callable):
        """Initialise le middleware."""
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Traite chaque requête.
        
        Args:
            request: Requête HTTP
            
        Returns:
            HttpResponse
        """
        # Vérifier uniquement pour les utilisateurs authentifiés avec établissement
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        if not hasattr(request.user, 'etablissement') or request.user.etablissement is None:
            return self.get_response(request)
        
        # Vérifier les limites avec cache
        etablissement = request.user.etablissement
        
        try:
            licence = etablissement.licence
        except Licence.DoesNotExist:
            return self.get_response(request)
        
        cache_key = f'licence_limits_{licence.id}'
        cached_check = cache.get(cache_key)
        
        if cached_check is None:
            # Vérifier les limites
            self._check_limits(request, licence)
            
            # Mettre en cache
            cache.set(cache_key, 'checked', self.CACHE_TIMEOUT)
        
        return self.get_response(request)
    
    def _check_limits(self, request: HttpRequest, licence: Licence) -> None:
        """
        Vérifie les limites de la licence et avertit si elles sont dépassées.

        La logique métier (comptage des usages, comparaison aux plafonds)
        vit dans licences/services.py — le middleware n'émet que les
        avertissements utilisateurs.

        Args:
            request: Requête HTTP
            licence: Instance de Licence
        """
        from .services import get_usage_limites

        try:
            resultat = get_usage_limites(licence)
        except Exception:
            # Tables absentes (migration partielle) ou erreur de comptage :
            # le contrôle de limites ne doit jamais bloquer l'application.
            return

        for depassement in resultat['depassements']:
            messages.warning(request, depassement['message'])


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE : INJECTION CONTEXTE LICENCE
# ═══════════════════════════════════════════════════════════════════

class LicenceContextMiddleware:
    """
    Middleware qui injecte les informations de licence dans le contexte.
    
    Ajoute automatiquement les variables suivantes à chaque template :
    - licence_info : dict avec toutes les infos de licence
    - features_disponibles : list des features accessibles
    - jours_restants : int nombre de jours avant expiration
    
    Usage dans un template:
        {% if 'cursus_scolaire' in features_disponibles %}
            <a href="...">Cursus</a>
        {% endif %}
        
        <div class="badge">{{ licence_info.type_display }}</div>
    
    Configuration:
        MIDDLEWARE = [
            ...
            'licences.middleware.LicenceContextMiddleware',
        ]
    """
    
    def __init__(self, get_response: Callable):
        """Initialise le middleware."""
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Traite la requête et injecte le contexte.
        
        Args:
            request: Requête HTTP
            
        Returns:
            HttpResponse
        """
        # Initialiser les variables de contexte
        request.licence_info = None
        request.features_disponibles = []
        request.jours_restants = None
        
        # Vérifier si l'utilisateur a une licence
        if (
            request.user.is_authenticated
            and hasattr(request.user, 'etablissement')
            and request.user.etablissement is not None
        ):
            try:
                licence = request.user.etablissement.licence
                
                if licence.est_active():
                    request.licence_info = {
                        'type': licence.type_licence,
                        'type_display': licence.get_type_licence_display(),
                        'cle_licence': licence.cle_licence,
                        'date_expiration': licence.date_expiration,
                        'est_active': True,
                    }
                    
                    request.features_disponibles = licence.get_features_disponibles()
                    request.jours_restants = licence.jours_restants()
                    
            except Licence.DoesNotExist:
                pass
        
        return self.get_response(request)


# ═══════════════════════════════════════════════════════════════════
# CONTEXT PROCESSOR (Alternative au middleware pour les templates)
# ═══════════════════════════════════════════════════════════════════

def licence_context_processor(request: HttpRequest) -> dict:
    """
    Context processor pour injecter les infos de licence dans tous les templates.
    
    À ajouter dans settings.py:
        TEMPLATES = [{
            'OPTIONS': {
                'context_processors': [
                    ...
                    'licences.middleware.licence_context_processor',
                ],
            },
        }]
    
    Returns:
        dict: Contexte avec infos de licence
    """
    context = {
        'licence_info': None,
        'features_disponibles': [],
        'jours_restants': None,
    }
    
    if (
        request.user.is_authenticated
        and hasattr(request.user, 'etablissement')
        and request.user.etablissement is not None
    ):
        try:
            licence = request.user.etablissement.licence
            
            if licence.est_active():
                context['licence_info'] = {
                    'type': licence.type_licence,
                    'type_display': licence.get_type_licence_display(),
                    'cle_licence': licence.cle_licence,
                    'date_expiration': licence.date_expiration,
                    'est_active': True,
                }
                
                context['features_disponibles'] = licence.get_features_disponibles()
                context['jours_restants'] = licence.jours_restants()
                
        except Licence.DoesNotExist:
            pass
    
    return context
