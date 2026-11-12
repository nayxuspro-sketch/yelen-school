"""Helpers partagés par les vues Vie scolaire (périmètre, établissement, moteur PDF)."""
import logging

from parametres.models import AnneeScolaire, Classe
from personnel.selectors import cycles_accessibles
from yelen_school.cycle_filter import filtrer_classe_par_cycle, get_cycle_ids

logger = logging.getLogger(__name__)
try:
    from core.pdf import HTML as WeasyHTML
except (ImportError, OSError) as exc:  # libpango/cairo absents
    logger.error("WeasyPrint indisponible, génération PDF désactivée : %s", exc)
    WeasyHTML = None


# ─── Emploi du temps ──────────────────────────────────────────────────────────

def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


def classes_accessibles(request, etablissement=None):
    """Classes du périmètre d'établissement et des cycles autorisés du compte."""
    etablissement = etablissement or _get_etab(request)
    classes = Classe.objects.all()
    if etablissement is not None:
        classes = classes.filter(etablissement=etablissement)
    return filtrer_classe_par_cycle(classes, request)


def annees_accessibles(request, etablissement=None):
    """Années des établissements et cycles accessibles, sans révéler les autres écoles."""
    etablissement = etablissement or _get_etab(request)
    annees = AnneeScolaire.objects.all()
    if etablissement is not None:
        return annees.filter(etablissement=etablissement)
    if get_cycle_ids(request) is None:
        return annees
    return annees.filter(etablissement_id__in=cycles_accessibles(request).values('etablissement_id'))
