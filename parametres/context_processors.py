"""Expose au gabarit de base les modules et fonctionnalités accessibles à l'utilisateur connecté."""
from .droits import MODULES, SECTION_ADMINISTRATION, SECTION_SCOLARITE, droits_requete


def droits_acces(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    modules, fonctionnalites = droits_requete(request)
    return {
        'droits_modules': modules,
        'droits_fonctionnalites': fonctionnalites,
        'droits_scolarite': any(m.code in modules for m in MODULES if m.section == SECTION_SCOLARITE),
        'droits_administration': any(m.code in modules for m in MODULES if m.section == SECTION_ADMINISTRATION),
    }
