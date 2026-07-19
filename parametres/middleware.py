"""
Module Paramètres — Middleware
================================
YELEN SCHOOL — Déclenchement automatique de la nouvelle année scolaire.

Vérifie à chaque requête authentifiée si la génération automatique
de l'année scolaire doit être déclenchée (à partir du 5 juillet).

La vérification est limitée à 1 fois par jour par établissement
grâce au cache Redis.
"""

import logging
from typing import Callable

from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


class AnneeScolaireAutoMiddleware:
    """
    Middleware qui déclenche automatiquement la création de la nouvelle
    année scolaire à partir du 5 juillet.

    Fonctionnement :
        1. Vérifie que l'utilisateur est authentifié avec un établissement
        2. Vérifie le cache (1x/jour maximum par établissement)
        3. Appelle ``auto_generer_annee_scolaire(etablissement=etab)``
        4. En cas de création, un log est émis

    Configuration dans settings.py ::

        MIDDLEWARE = [
            ...
            'parametres.middleware.AnneeScolaireAutoMiddleware',
        ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            etab = getattr(request.user, 'etablissement', None)
            if etab is not None:
                today = timezone.now().date()
                cache_key = f'auto_annee_scolaire_{etab.id}_{today.isoformat()}'

                if cache.get(cache_key) is None:
                    from parametres.services import auto_generer_annee_scolaire

                    created = auto_generer_annee_scolaire(etablissement=etab)
                    if created:
                        logger.info(
                            "Nouvelle année scolaire générée automatiquement : "
                            "%s pour %s",
                            created[0].libelle,
                            etab.nom,
                        )
                    # Marquer comme vérifié pour les prochaines 24h
                    cache.set(cache_key, True, 86400)

        return self.get_response(request)
