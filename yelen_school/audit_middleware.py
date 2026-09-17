"""Contexte de requête pour l'audit métier."""

import threading
import uuid

from django.conf import settings


_request_local = threading.local()


def get_request():
    """Récupère la requête actuelle depuis le thread local."""
    return getattr(_request_local, 'request', None)


def get_user_from_request():
    request = get_request()
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


def get_client_ip(request):
    """Retourne l'IP réseau réelle, sans faire confiance au client par défaut."""
    if request is None:
        return None
    remote_addr = request.META.get('REMOTE_ADDR')
    trusted_proxies = set(getattr(settings, 'TRUSTED_PROXY_IPS', []))
    if (
        getattr(settings, 'TRUST_PROXY_HEADERS', False)
        and remote_addr in trusted_proxies
    ):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
    return remote_addr


class AuditRequestMiddleware:
    """Stocke la requête et un identifiant corrélable pendant son traitement."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.audit_request_id = str(uuid.uuid4())
        _request_local.request = request
        try:
            return self.get_response(request)
        finally:
            # Ne jamais réutiliser le contexte d'un utilisateur sur une requête
            # suivante du même thread.
            try:
                del _request_local.request
            except AttributeError:
                pass
