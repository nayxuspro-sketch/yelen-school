"""Paramètres financiers de l'établissement et application des pénalités de retard."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .. import penalites as services
from ..forms import ParametresFinancesForm
from ..models import ParametresFinances
from ..permissions import FINANCE_APPROVER_ROLES
from ..selectors import annee_choisie
from .commun import _require_finance_role
from core.utils import fcfa


@login_required
def parametres_finances(request):
    """Pénalités de retard, blocage des bulletins, remise fratrie (direction)."""
    _require_finance_role(request, FINANCE_APPROVER_ROLES)
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')
    params = ParametresFinances.pour(etab)
    form = ParametresFinancesForm(request.POST or None, instance=params, etablissement=etab)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Paramètres financiers enregistrés.")
        return redirect('finances:parametres_finances')
    return render(request, 'finances/parametres_finances.html', {'form': form, 'params': params})


@login_required
@require_POST
def penalites_appliquer(request):
    """Crée les créances « Pénalité de retard » des échéances dépassées et non couvertes (direction)."""
    _require_finance_role(request, FINANCE_APPROVER_ROLES)
    etab = request.user.etablissement
    annee = annee_choisie(etab, request.POST.get('annee'))
    retour = reverse('finances:echeancier_global') + (f'?annee={annee.pk}&statut=retard' if annee else '')
    if annee is None:
        messages.error(request, "Aucune année scolaire.")
        return redirect(retour)
    try:
        creees = services.appliquer_penalites(etab, annee, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(retour)
    if creees:
        total = sum((c.montant for c in creees), 0)
        messages.success(request, f"{len(creees)} pénalité(s) de retard appliquée(s) — {fcfa(total)} au total "
                                  "(visibles dans la situation de chaque élève, annulables).".replace(',', ' '))
    else:
        messages.info(request, "Aucune nouvelle pénalité : pas d'échéance dépassée non couverte sans pénalité.")
    return redirect(retour)
