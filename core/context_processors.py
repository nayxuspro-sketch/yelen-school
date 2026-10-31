"""Variables de gabarit communes à toutes les pages."""
from django.conf import settings

from core.aide import ancre_pour


def version(request):
    return {'yelen_version': settings.YELEN_VERSION}


def aide(request):
    """Ancre du guide d'utilisation correspondant au module affiché (lien « Aide » du menu)."""
    return {'aide_ancre': ancre_pour(request.path)}


def environnement(request):
    """Bandeau « ENVIRONNEMENT DE TEST » (YELEN_ENVIRONNEMENT=test, copie isolée de la production)."""
    return {'yelen_environnement_test': settings.YELEN_ENVIRONNEMENT_TEST}


def demo(request):
    """Bandeau « DÉMONSTRATION » (DEMO_MODE=true, instance d'essai publique de l'offre hébergée)."""
    from core import mode_demo
    return {'yelen_mode_demo': mode_demo.actif()}
