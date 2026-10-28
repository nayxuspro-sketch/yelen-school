"""Helpers partagés par les vues de paramétrage (établissement courant, suppression générique)."""
import logging

from django.db import DatabaseError
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse


logger = logging.getLogger(__name__)


def _get_etab(request):
    return getattr(request.user, 'etablissement', None)


# ═══════════════════════════════════════════════════════════════════
# VUES DE SUPPRESSION
# ═══════════════════════════════════════════════════════════════════

def _delete_view(request, obj):
    """Helper : supprime l'objet sur POST, renvoie 204 + HX-Trigger."""
    if request.method != 'POST':
        return HttpResponse(status=405)
    try:
        obj.delete()
        return HttpResponse(status=204, headers={'HX-Trigger': 'parametreUpdated'})
    except ProtectedError as e:
        nb = len(e.protected_objects)
        return HttpResponse(
            f"Suppression impossible : {nb} enregistrement(s) lié(s) l'utilisent encore.",
            status=400,
        )
    except DatabaseError as e:
        logger.exception("Suppression impossible")
        return HttpResponse(str(e), status=400)
