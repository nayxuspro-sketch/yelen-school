"""Variables de gabarit communes à toutes les pages."""
from django.conf import settings


def version(request):
    return {'yelen_version': settings.YELEN_VERSION}
