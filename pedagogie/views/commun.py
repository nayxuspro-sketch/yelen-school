"""Imports et helpers partagés des vues pédagogie (PDF, filigrane licence).

Issu du découpage mécanique de ``pedagogie/views.py`` (octobre 2026) : code inchangé.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from core.pdf import HTML
except (ImportError, OSError) as exc:  # libpango/cairo absents
    logger.error("WeasyPrint indisponible, génération PDF désactivée : %s", exc)
    HTML = None

# P2 — filigrane licence PDF : helper central licences/pdf_utils.py
try:
    from licences.pdf_utils import inject_licence_filigrane_context, get_licence_info_for_pdf
    def _pdf_licence_info(request, etab=None):
        try:
            return get_licence_info_for_pdf(request.user, etab)
        except Exception:
            logger.warning("Filigrane licence indisponible pour le PDF", exc_info=True)
            return None
except ImportError:
    def inject_licence_filigrane_context(ctx, user, etab=None):  # type: ignore
        return ctx
    def get_licence_info_for_pdf(user, etab=None):  # type: ignore
        return None
    def _pdf_licence_info(request, etab=None):
        return None
