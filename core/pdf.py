"""Rendu PDF WeasyPrint avec résolution locale des fichiers ``/static/`` et ``/media/``.

Les gabarits PDF référencent photos, logos et feuilles de style par des URL absolues
(``request.build_absolute_uri(...)``). Par défaut WeasyPrint les télécharge en HTTP
auprès du serveur lui-même, ce qui échoue en production :

- en conteneur, le port publié (ex. ``localhost:8001``) n'est pas joignable de l'intérieur ;
- ``/media/`` est réservé aux utilisateurs connectés (``core.media.media_protege``) et la
  requête de WeasyPrint n'a pas de session.

``core.pdf.HTML`` remplace ``weasyprint.HTML`` : les URL dont l'hôte est autorisé
(``ALLOWED_HOSTS``) et le chemin sous ``MEDIA_URL`` ou ``STATIC_URL`` sont lues
directement sur le disque ; toute autre URL suit le comportement standard.
"""
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urlsplit

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http.request import validate_host

import weasyprint
from weasyprint.urls import URLFetcher, URLFetcherResponse

_HOTES_DEBUG = ['.localhost', '127.0.0.1', '[::1]']


def _prefixe(url):
    return '/' + (url or '').lstrip('/')


def _sous_racine(racine, relatif):
    """Fichier ``relatif`` sous ``racine`` (résolution des liens, ``..`` interdit), sinon None."""
    if not racine or not relatif:
        return None
    base = Path(racine).resolve()
    fichier = (base / relatif).resolve()
    if base in fichier.parents and fichier.is_file():
        return fichier
    return None


def fichier_local(url):
    """Chemin local correspondant à une URL ``/media/…`` ou ``/static/…`` de l'application."""
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname:
        return None
    hotes = settings.ALLOWED_HOSTS or (_HOTES_DEBUG if settings.DEBUG else [])
    if not validate_host(parts.hostname, hotes):
        return None
    chemin = unquote(parts.path)
    media = _prefixe(settings.MEDIA_URL)
    static = _prefixe(settings.STATIC_URL)
    if chemin.startswith(media):
        return _sous_racine(settings.MEDIA_ROOT, chemin[len(media):])
    if chemin.startswith(static):
        relatif = chemin[len(static):]
        fichier = _sous_racine(getattr(settings, 'STATIC_ROOT', None), relatif)
        if fichier is None:
            trouve = finders.find(relatif)
            fichier = Path(trouve) if trouve and Path(trouve).is_file() else None
        return fichier
    return None


class FetcherLocal(URLFetcher):
    """``URLFetcher`` WeasyPrint : disque pour les fichiers de l'application, HTTP sinon."""

    def fetch(self, url, headers=None):
        fichier = fichier_local(url)
        if fichier is not None:
            mime_type, _ = mimetypes.guess_type(fichier.name)
            return URLFetcherResponse(
                url, fichier.open('rb'),
                {'Content-Type': mime_type or 'application/octet-stream'},
            )
        return super().fetch(url, headers)


class HTML(weasyprint.HTML):
    """``weasyprint.HTML`` dont le fetcher par défaut lit static/media sur le disque."""

    def __init__(self, *args, url_fetcher=None, **kwargs):
        super().__init__(*args, url_fetcher=url_fetcher or FetcherLocal(), **kwargs)
