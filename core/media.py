"""Diffusion des fichiers téléversés (``MEDIA_URL``) réservée aux utilisateurs connectés.

Les photos (élèves, personnel), logos, cachets et signatures sont stockés sous
``MEDIA_ROOT``. Django ne les servait qu'en ``DEBUG=True`` : en production (Docker
sans reverse proxy pour ``/media/``, mode autonome Waitress) toute image renvoyait 404,
donc n'apparaissait ni dans les pages ni dans les PDF. Cette vue les sert dans tous
les modes, après authentification (données personnelles).
"""
import posixpath

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.views.decorators.cache import cache_control
from django.views.static import serve


@login_required
@cache_control(private=True, max_age=3600)
def media_protege(request, path):
    """Renvoie un fichier privé ; les PDF archivés passent par leur vue de contrôle de cycle."""
    chemin = posixpath.normpath((path or '').replace(chr(92), '/')).lstrip('/')
    if chemin == 'documents' or chemin.startswith('documents/'):
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)
