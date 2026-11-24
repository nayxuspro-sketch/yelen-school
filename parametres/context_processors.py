"""Expose au gabarit de base les modules et fonctionnalités accessibles à l'utilisateur connecté."""
from .droits import MODULES, SECTION_ADMINISTRATION, SECTION_SCOLARITE, droits_requete


def droits_acces(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    modules, fonctionnalites, _ = droits_requete(request)
    # « Bulletins compétences » (API / APC) ne concerne que le Préscolaire et le Primaire : l'entrée de
    # menu disparaît d'un établissement du secondaire, et pour un enseignant qui n'y a aucune classe.
    from pedagogie.selectors import cycles_competences
    if '/pedagogie/competences/' in fonctionnalites and not cycles_competences(request).exists():
        fonctionnalites = fonctionnalites - {'/pedagogie/competences/'}
    return {
        'droits_modules': modules,
        'droits_fonctionnalites': fonctionnalites,
        'droits_scolarite': any(m.code in modules for m in MODULES if m.section == SECTION_SCOLARITE),
        'droits_administration': any(m.code in modules for m in MODULES if m.section == SECTION_ADMINISTRATION),
    }
