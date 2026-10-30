"""Créances individuelles (manuel non rendu, …) : annulation depuis la situation financière de l'élève."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Creance
from ..permissions import FINANCE_APPROVER_ROLES
from .commun import _require_finance_role, _require_same_establishment
from core.utils import fcfa


@login_required
@require_POST
def creance_annuler(request, pk):
    """Annule une créance (plus rien n'est dû) ; conservée pour l'historique. Un montant déjà encaissé dessus
    se traite, le cas échéant, par un remboursement."""
    _require_finance_role(request, FINANCE_APPROVER_ROLES)
    creance = get_object_or_404(Creance.objects.select_related('inscription__classe'), pk=pk, actif=True)
    _require_same_establishment(request, creance.inscription)
    creance.annuler(f"Annulée le {timezone.localdate():%d/%m/%Y} par {request.user.get_full_name() or request.user.email}")
    messages.success(request, f"Créance « {creance.libelle} » annulée : {fcfa(creance.montant)} ne sont plus dus.")
    return redirect('finances:situation_eleve', inscription_id=creance.inscription_id)
