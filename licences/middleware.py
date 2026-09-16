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

import hashlib
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
    """Bloque toute utilisation client sans licence Ed25519 valide."""

    # Ces pages doivent rester visibles pour expliquer une absence, une
    # expiration ou une procédure de renouvellement. L'administration Django
    # n'est pas exemptée : un superutilisateur client ne doit pas contourner la
    # licence en passant par /admin/.
    EXEMPTED_URLS = (
        '/accounts/login/',
        '/accounts/logout/',
        '/licences/activer/',
        '/licences/renouveler/',
        '/licences/support/',
        '/licences/guide/',
        '/licences/mon-abonnement/',
        '/static/',
        '/media/',
        '/__debug__/',
    )
    CACHE_TIMEOUT = 60

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not getattr(settings, 'LICENSE_ENFORCEMENT_ENABLED', True):
            return self.get_response(request)
        if self._is_exempted_url(request.path):
            return self.get_response(request)
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Le bypass est réservé à un environnement fournisseur explicitement
        # configuré. Un simple is_superuser chez le client ne suffit pas.
        if (
            request.user.is_superuser
            and getattr(settings, 'LICENSE_ALLOW_SUPERUSER_BYPASS', False)
        ):
            return self.get_response(request)

        etablissement = getattr(request.user, 'etablissement', None)
        if etablissement is None:
            if request.path != reverse('accounts:profile'):
                messages.warning(
                    request,
                    _("Veuillez compléter votre profil et associer un établissement."),
                )
                return redirect('accounts:profile')
            return self.get_response(request)

        try:
            licence = etablissement.licence
        except Licence.DoesNotExist:
            if request.path != reverse('licences:activer'):
                messages.error(
                    request,
                    _("Votre établissement n'a pas de licence. Importez le fichier signé fourni par YELEN SCHOOL."),
                )
                return redirect('licences:activer')
            return self.get_response(request)

        from .fingerprint import get_server_fingerprint
        cache_key = self._cache_key(licence, get_server_fingerprint())
        if cache.get(cache_key) is None:
            is_valid, response = self._check_licence(request, licence)
            if not is_valid:
                return response
            cache.set(cache_key, 'valid', self.CACHE_TIMEOUT)

        return self.get_response(request)

    @staticmethod
    def _cache_key(licence: Licence, fingerprint: str) -> str:
        # Le statut, l'expiration, la signature et l'empreinte font partie de
        # la clé : une modification DB ne réutilise pas un cache positif ancien.
        signature = licence.signature_ed25519 or licence.signature_hmac
        material = ':'.join((
            str(licence.pk),
            signature,
            licence.statut,
            licence.date_expiration.isoformat(),
            fingerprint,
        ))
        return 'licence_check_' + hashlib.sha256(material.encode('utf-8')).hexdigest()

    def _is_exempted_url(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.EXEMPTED_URLS)

    def _check_licence(self, request: HttpRequest, licence: Licence) -> tuple:
        # Une licence historique HMAC est refusée en mode commercial, même si
        # son HMAC correspond à SECRET_KEY.
        if not licence.utilise_signature_forte:
            self._log_audit(
                licence,
                'TENTATIVE_FRAUDE',
                'Licence historique HMAC refusée : migration Ed25519 nécessaire',
                request,
            )
            messages.error(
                request,
                _("Cette installation utilise une licence historique non certifiée. Importez une licence Ed25519."),
            )
            return False, redirect('licences:support')

        if not licence.verifier_signature():
            self._log_audit(
                licence,
                'TENTATIVE_FRAUDE',
                'Signature Ed25519 ou payload de licence invalide',
                request,
            )
            messages.error(
                request,
                _("La licence est invalide ou a été modifiée. Contactez le support."),
            )
            return False, redirect('licences:support')

        if licence.statut == StatutLicence.REVOQUEE:
            messages.error(request, _("La licence a été révoquée. Contactez le support."))
            return False, redirect('licences:support')

        if licence.date_expiration < timezone.now().date():
            if licence.statut != StatutLicence.EXPIREE:
                Licence.objects.filter(pk=licence.pk).update(statut=StatutLicence.EXPIREE)
                self._log_audit(
                    licence,
                    'EXPIRATION',
                    f'Licence expirée le {licence.date_expiration}',
                    request,
                )
                self._creer_alerte_expiration(licence, 'EXPIREE')
            messages.error(
                request,
                _("Votre licence a expiré le {date}. Importez un renouvellement signé.").format(
                    date=licence.date_expiration.strftime('%d/%m/%Y'),
                ),
            )
            return False, redirect('licences:renouveler')

        if licence.statut != StatutLicence.ACTIVE:
            messages.error(
                request,
                _("La licence n'est pas activée. Importez puis activez le fichier fourni par YELEN SCHOOL."),
            )
            return False, redirect('licences:activer')

        if not licence.est_liee_au_serveur():
            self._log_audit(
                licence,
                'TENTATIVE_FRAUDE',
                'Empreinte serveur différente de celle du payload signé',
                request,
            )
            messages.error(
                request,
                _("Cette licence est liée à un autre serveur. Contactez le support pour un remplacement autorisé."),
            )
            return False, redirect('licences:support')

        self._generer_alertes_expiration(licence)
        Licence.objects.filter(pk=licence.pk).update(derniere_verification=timezone.now())
        return True, None

    def _generer_alertes_expiration(self, licence: Licence) -> None:
        jours_restants = licence.jours_restants()
        for seuil, type_alerte in {30: 'J-30', 15: 'J-15', 7: 'J-7', 1: 'J-1'}.items():
            if jours_restants <= seuil and not LicenceAlert.objects.filter(
                licence=licence,
                type_alerte=type_alerte,
            ).exists():
                LicenceAlert.objects.create(licence=licence, type_alerte=type_alerte)
                self._log_audit(
                    licence,
                    'VERIFICATION',
                    f'Alerte {type_alerte} créée ({jours_restants} jours restants)',
                    None,
                )

    def _creer_alerte_expiration(self, licence: Licence, type_alerte: str) -> None:
        LicenceAlert.objects.get_or_create(licence=licence, type_alerte=type_alerte)

    def _log_audit(
        self,
        licence: Licence,
        action: str,
        description: str,
        request: HttpRequest | None = None,
    ) -> None:
        try:
            LicenceAuditLog.objects.create(
                licence=licence,
                action=action,
                description=description,
                acteur_user=request.user if request and request.user.is_authenticated else None,
                acteur_systeme=request is None,
                ip_address=self._get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            )
        except Exception:
            # Une alerte de licence ne doit pas rendre l'application inutilisable
            # si le journal historique est temporairement indisponible.
            pass

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR', '')


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARE : VÉRIFICATION DES LIMITES
# ═══════════════════════════════════════════════════════════════════

class LicenceLimitsMiddleware:
    """Bloque les écritures lorsque les compteurs dépassent une licence."""

    CACHE_TIMEOUT = 30

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not getattr(settings, 'LICENSE_ENFORCEMENT_ENABLED', True):
            return self.get_response(request)
        if not request.user.is_authenticated:
            return self.get_response(request)
        if (
            request.user.is_superuser
            and getattr(settings, 'LICENSE_ALLOW_SUPERUSER_BYPASS', False)
        ):
            return self.get_response(request)

        etab = getattr(request.user, 'etablissement', None)
        if etab is None:
            return self.get_response(request)
        try:
            licence = etab.licence
        except Licence.DoesNotExist:
            return self.get_response(request)

        # Les écritures ne réutilisent jamais un résultat de comptage ancien.
        cache_key = self._cache_key(licence)
        violations = None if request.method not in {'GET', 'HEAD', 'OPTIONS'} else cache.get(cache_key)
        if violations is None:
            violations = self._check_limits(request, licence)
            if request.method in {'GET', 'HEAD', 'OPTIONS'}:
                cache.set(cache_key, violations, self.CACHE_TIMEOUT)

        if violations and request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            message = _(
                "Opération refusée : la limite de licence est dépassée pour %(items)s."
            ) % {'items': ', '.join(violations)}
            messages.error(request, message)
            if request.path.startswith('/api/'):
                from django.http import JsonResponse
                return JsonResponse(
                    {'error': 'licence_limit_exceeded', 'details': violations},
                    status=403,
                )
            return HttpResponse(message, status=403, content_type='text/plain; charset=utf-8')

        return self.get_response(request)

    @staticmethod
    def _cache_key(licence: Licence) -> str:
        material = ':'.join((
            str(licence.pk),
            licence.signature_ed25519 or licence.signature_hmac,
            licence.statut,
            licence.date_expiration.isoformat(),
        ))
        return 'licence_limits_' + hashlib.sha256(material.encode('utf-8')).hexdigest()

    def _check_limits(self, request: HttpRequest, licence: Licence) -> dict:
        """Retourne les limites dépassées ; ne se contente plus d'avertir."""
        limites = licence.limites_effectives()
        etab = licence.etablissement
        violations = {}

        try:
            from inscriptions.models import Inscription
            nb_eleves = (
                Inscription.objects
                .filter(
                    classe__etablissement=etab,
                    annee_scolaire__est_courante=True,
                    statut__in=('AFFECTE', 'BOURSIER', 'EXONERE'),
                )
                .values('eleve_id').distinct().count()
            )
            maximum = limites.get('max_eleves', 0)
            if maximum < 0 or nb_eleves > maximum:
                violations['eleves'] = {'current': nb_eleves, 'max': maximum}
        except ImportError:
            pass

        try:
            from personnel.models import InscriptionPersonnel
            nb_enseignants = (
                InscriptionPersonnel.objects
                .filter(
                    cycle__etablissement=etab,
                    est_actif=True,
                    poste__categorie='ENSEIGNEMENT',
                )
                .values('personnel_id').distinct().count()
            )
            maximum = limites.get('max_enseignants', 0)
            if maximum < 0 or nb_enseignants > maximum:
                violations['enseignants'] = {'current': nb_enseignants, 'max': maximum}
        except ImportError:
            pass

        try:
            from parametres.models import Classe
            nb_classes = Classe.objects.filter(etablissement=etab, actif=True).count()
            maximum = limites.get('max_classes', 0)
            if maximum < 0 or nb_classes > maximum:
                violations['classes'] = {'current': nb_classes, 'max': maximum}
        except ImportError:
            pass

        return violations


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
