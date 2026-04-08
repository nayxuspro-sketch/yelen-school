import threading

_request_local = threading.local()


def get_request():
    """Récupère la requête actuelle depuis le thread local."""
    return getattr(_request_local, 'request', None)


def get_user_from_request():
    """Récupère l'utilisateur depuis la requête actuelle."""
    request = get_request()
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return request.user
    return None


def get_client_ip(request):
    """Récupère l'IP cliente depuis la requête."""
    if request is None:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class AuditRequestMiddleware:
    """Middleware pour stocker la requête dans le thread local pour les signaux d'audit."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _request_local.request = request
        response = self.get_response(request)
        return response
