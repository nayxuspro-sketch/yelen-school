"""Garde-fous anti-brute-force pour la connexion web."""

from __future__ import annotations

import hashlib

from django.core.cache import cache


class LoginRateLimiter:
    """Limite simultanément une adresse IP et un identifiant de compte.

    L'adresse IP provient uniquement de REMOTE_ADDR : les en-têtes transmis par
    le client ne sont pas fiables sans proxy de confiance explicitement géré.
    Le verrouillage en base du modèle User reste la seconde ligne de défense.
    """

    WINDOW_SECONDS = 60
    MAX_ATTEMPTS = 5
    PREFIX = "yelen:login:v1"

    @classmethod
    def client_ip(cls, request) -> str:
        return (request.META.get("REMOTE_ADDR") or "unknown").strip()[:64]

    @classmethod
    def _digest(cls, value: str) -> str:
        return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()

    @classmethod
    def _keys(cls, request, email: str) -> tuple[str, str]:
        ip_key = f"{cls.PREFIX}:ip:{cls._digest(cls.client_ip(request))}"
        account_key = f"{cls.PREFIX}:account:{cls._digest(email)}"
        return ip_key, account_key

    @classmethod
    def is_blocked(cls, request, email: str) -> bool:
        try:
            return any(
                (cache.get(key) or 0) >= cls.MAX_ATTEMPTS
                for key in cls._keys(request, email)
            )
        except Exception:
            # Le compteur DB (5 échecs / 15 minutes) reste actif si Redis est
            # momentanément indisponible.
            return False

    @classmethod
    def register_failure(cls, request, email: str) -> None:
        try:
            for key in cls._keys(request, email):
                if not cache.add(key, 1, cls.WINDOW_SECONDS):
                    cache.incr(key)
        except Exception:
            # Ne pas révéler la disponibilité de Redis et laisser le verrou DB
            # prendre le relais.
            return

    @classmethod
    def clear_account(cls, request, email: str) -> None:
        try:
            # On ne supprime pas le compteur IP après une connexion valide :
            # sinon un attaquant pourrait faire tourner des comptes valides pour
            # contourner la limite par adresse.
            _, account_key = cls._keys(request, email)
            cache.delete(account_key)
        except Exception:
            return
