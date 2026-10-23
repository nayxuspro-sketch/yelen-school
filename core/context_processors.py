"""Variables de gabarit communes à toutes les pages."""
from django.conf import settings

from core.aide import ancre_pour


def version(request):
    return {'yelen_version': settings.YELEN_VERSION}


def aide(request):
    """Ancre du guide d'utilisation correspondant au module affiché (lien « Aide » du menu)."""
    return {'aide_ancre': ancre_pour(request.path)}
