"""Compteur d'usage anonyme par module applicatif (audit P1-10, livré en 5.48.0).

Mesure quels modules sont réellement consultés sans collecter aucune donnée personnelle
(ni identifiant utilisateur, ni adresse IP, ni paramètres d'URL) et sans pénaliser SQLite
sous forte concurrence : les appels sont cumulés en mémoire dans chaque processus et reversés
en base par lot au plus une fois par minute (ou immédiatement à l'ouverture d'*Exploitation*).
"""
from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from datetime import timedelta

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

INTERVALLE_VIDAGE_SECONDES = 60.0

LIBELLES_MODULES: dict[str, str] = {
    'accounts': 'Comptes & Portail',
    'api': 'API & Intégrations',
    'bulletins': 'Bulletins scolaires',
    'communication': 'Communication & Messagerie',
    'core': 'Tableau de bord & Administration',
    'documents': 'Documents administratifs',
    'etablissements': 'Établissements',
    'examens': 'Examens & Concours',
    'finances': 'Finances & Scolarité',
    'inscriptions': 'Élèves & Inscriptions',
    'licences': 'Licences',
    'manuels': 'Manuels scolaires',
    'parametres': 'Paramètres',
    'pedagogie': 'Pédagogie & Notes',
    'personnel': 'Personnel & RH',
    'presences': 'Présences & Appels',
    'vacations': 'Vacations',
    'viescolaire': 'Vie scolaire & Emplois du temps',
}

# Routes techniques ou de rafraîchissement automatique exclues pour ne mesurer que l'usage humain.
URLS_EXCLUES = frozenset({
    'aide_capture',
    'app_manifest',
    'certificat_autorite',
    'favicon',
    'health_check',
    'mise_a_jour_etat',
    'notifications_badge',
    'offline_page',
    'pwa_icon',
    'pwa_manifest',
    'pwa_manifest_eleve',
    'saisies_contexte',
})

MODULES_EXCLUS = frozenset({'admin', 'django'})

_verrou = threading.Lock()
_tampon: Counter[tuple] = Counter()
_dernier_vidage: float | None = None


def reinitialiser_tampon_usage() -> None:
    """Réinitialise le tampon mémoire sans accès base (isolation des tests)."""
    global _dernier_vidage
    with _verrou:
        _tampon.clear()
        _dernier_vidage = None


def _extraire_module(request) -> str | None:
    match = getattr(request, 'resolver_match', None)
    if match is None or match.url_name in URLS_EXCLUES:
        return None
    module = (
        match.app_name
        or (match.namespaces[0] if match.namespaces else '')
        or getattr(match.func, '__module__', '').split('.')[0]
    ).strip().lower()
    if not module or module in MODULES_EXCLUS:
        return None
    return module[:40]


def enregistrer_appel_module(module: str, jour=None) -> None:
    """Incrémente le compteur mémoire pour ``(jour, module)`` et déclenche un vidage périodique."""
    global _dernier_vidage
    if not module:
        return
    jour_effectif = jour or timezone.localdate()
    maintenant = time.monotonic()
    a_vider: dict[tuple, int] | None = None

    with _verrou:
        if _dernier_vidage is None:
            _dernier_vidage = maintenant
        _tampon[(jour_effectif, module)] += 1
        if (maintenant - _dernier_vidage) >= INTERVALLE_VIDAGE_SECONDES:
            a_vider = dict(_tampon)
            _tampon.clear()
            _dernier_vidage = maintenant

    if a_vider:
        _persister_lot(a_vider)


def vider_tampon_usage() -> int:
    """Force l'écriture en base de tous les appels accumulés en mémoire ; retourne le nombre de clés écrites."""
    global _dernier_vidage
    with _verrou:
        if not _tampon:
            return 0
        a_vider = dict(_tampon)
        _tampon.clear()
        _dernier_vidage = time.monotonic()
    return _persister_lot(a_vider)


def _persister_lot(lot: dict[tuple, int]) -> int:
    from core.models import UsageModuleQuotidien

    ecrits = 0
    for (jour, module), nb in lot.items():
        if nb <= 0:
            continue
        try:
            mis_a_jour = UsageModuleQuotidien.objects.filter(date=jour, module=module).update(
                appels=F('appels') + nb
            )
            if not mis_a_jour:
                try:
                    with transaction.atomic():
                        UsageModuleQuotidien.objects.create(date=jour, module=module, appels=nb)
                except IntegrityError:
                    UsageModuleQuotidien.objects.filter(date=jour, module=module).update(
                        appels=F('appels') + nb
                    )
            ecrits += 1
        except DatabaseError as exc:
            logger.debug("Compteur d'usage non persisté (%s, %s) : %s", jour, module, exc)
    return ecrits


def usage_modules(jours_courts: int = 7, jours_longs: int = 30) -> dict:
    """Agrège l'usage anonyme des modules sur ``jours_courts`` et ``jours_longs`` jours glissants."""
    from core.models import UsageModuleQuotidien

    vider_tampon_usage()
    aujourd_hui = timezone.localdate()
    debut_long = aujourd_hui - timedelta(days=max(jours_longs - 1, 0))
    debut_court = aujourd_hui - timedelta(days=max(jours_courts - 1, 0))

    try:
        lignes_30 = {
            r['module']: r['total'] or 0
            for r in UsageModuleQuotidien.objects.filter(date__gte=debut_long)
            .values('module')
            .annotate(total=Sum('appels'))
        }
        lignes_7 = {
            r['module']: r['total'] or 0
            for r in UsageModuleQuotidien.objects.filter(date__gte=debut_court)
            .values('module')
            .annotate(total=Sum('appels'))
        }
    except DatabaseError as exc:
        logger.debug("Lecture du compteur d'usage indisponible : %s", exc)
        lignes_30, lignes_7 = {}, {}

    total_30j = sum(lignes_30.values())
    total_7j = sum(lignes_7.values())
    par_module = []
    for module, appels_30 in lignes_30.items():
        if appels_30 <= 0:
            continue
        appels_7 = lignes_7.get(module, 0)
        libelle = LIBELLES_MODULES.get(module, module.replace('_', ' ').capitalize())
        part = round((appels_30 * 100.0) / total_30j, 1) if total_30j else 0.0
        par_module.append({
            'module': module,
            'libelle': libelle,
            'appels_7j': appels_7,
            'appels_30j': appels_30,
            'part_30j': part,
        })
    par_module.sort(key=lambda x: (-x['appels_30j'], -x['appels_7j'], x['libelle']))

    return {
        'jours_courts': jours_courts,
        'jours_longs': jours_longs,
        'total_7j': total_7j,
        'total_30j': total_30j,
        'par_module': par_module,
    }


class UsageModuleMiddleware:
    """Comptabilise de façon anonyme les pages servies aux utilisateurs authentifiés."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        utilisateur = getattr(request, 'user', None)
        if (
            utilisateur is not None
            and getattr(utilisateur, 'is_authenticated', False)
            and 200 <= getattr(response, 'status_code', 0) < 400
        ):
            module = _extraire_module(request)
            if module:
                enregistrer_appel_module(module)
        return response
