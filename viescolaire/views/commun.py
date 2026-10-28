"""Helpers partagés par les vues de vie scolaire (établissement courant, moteur PDF)."""
import logging


logger = logging.getLogger(__name__)
try:
    from core.pdf import HTML as WeasyHTML
except (ImportError, OSError) as exc:  # libpango/cairo absents
    logger.error("WeasyPrint indisponible, génération PDF désactivée : %s", exc)
    WeasyHTML = None


# ─── Emploi du temps ──────────────────────────────────────────────────────────

def _get_etab(request):
    return getattr(request.user, 'etablissement', None)
