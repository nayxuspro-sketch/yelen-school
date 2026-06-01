from django import template
from django.templatetags.static import static
from django.conf import settings
import os
import hashlib

register = template.Library()

_cache: dict[str, str] = {}


@register.simple_tag
def static_v(path: str) -> str:
    """Retourne l'URL d'un fichier statique avec un hash de contenu en query string.

    Exemple : {% static_v 'css/yelen.css' %}
    → /static/css/yelen.css?v=a3f2c1

    Le hash est mis en cache en mémoire jusqu'au redémarrage du serveur.
    En DEBUG, le hash est recalculé à chaque requête pour refléter les
    modifications immédiates.
    """
    if not settings.DEBUG and path in _cache:
        return _cache[path]

    full_path = os.path.join(settings.BASE_DIR, "static", path)
    try:
        with open(full_path, "rb") as fh:
            digest = hashlib.md5(fh.read(), usedforsecurity=False).hexdigest()[:8]
    except OSError:
        digest = "0"

    url = f"{static(path)}?v={digest}"
    if not settings.DEBUG:
        _cache[path] = url
    return url
