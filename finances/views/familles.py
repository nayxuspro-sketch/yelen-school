"""Familles (fratries) : situation consolidée par responsable et remise fratrie automatique."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from parametres.models import AnneeScolaire
from .. import familles as services
from ..models import ParametresFinances
from ..permissions import FINANCE_VIEW_ROLES, FINANCE_WRITE_ROLES
from ..selectors import annee_choisie
from .commun import _require_finance_role


def _annee(request, etab):
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    return annees, annee_choisie(etab, request.GET.get('annee'))


@login_required
def familles_list(request):
    """Fratries de l'année (≥ 2 enfants inscrits) : enfants, total dû, payé, reste à payer de la famille."""
    _require_finance_role(request, FINANCE_VIEW_ROLES)
    etab = request.user.etablissement
    if not etab:
        messages.error(request, "Votre compte n'est pas associé à un établissement.")
        return redirect('finances:paiement_list')
    annees, annee = _annee(request, etab)
    q = request.GET.get('q', '').strip().lower()
    familles = services.familles(etab, annee) if annee else []
    if q:
        familles = [f for f in familles if q in f['responsable'].lower() or q in f['telephone']
                    or any(q in e['inscription'].eleve.get_nom_complet().lower() for e in f['enfants'])]
    params = ParametresFinances.objects.filter(etablissement=etab).first()
    return render(request, 'finances/familles_list.html', {
        'annees': annees,
        'annee': annee,
        'familles': familles,
        'q': q,
        'nb_enfants': sum(len(f['enfants']) for f in familles),
        'total_reste': sum((f['reste_a_payer'] for f in familles), 0),
        'remise': params.remise_fratrie if params else None,
        'remise_a_partir': params.remise_fratrie_a_partir if params else 2,
    })


@login_required
@require_POST
def remise_fratrie_appliquer(request):
    """Attribue la remise fratrie paramétrée aux enfants de rang ≥ n de chaque fratrie de l'année."""
    _require_finance_role(request, FINANCE_WRITE_ROLES)
    etab = request.user.etablissement
    annee = annee_choisie(etab, request.POST.get('annee'))
    retour = reverse('finances:familles_list') + (f'?annee={annee.pk}' if annee else '')
    if annee is None:
        messages.error(request, "Aucune année scolaire.")
        return redirect(retour)
    try:
        creees = services.appliquer_remise_fratrie(etab, annee, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect(retour)
    if creees:
        total = sum((b.montant_accorde for b in creees), 0)
        messages.success(request, f"Remise fratrie attribuée à {len(creees)} enfant(s) — {total:,.0f} FCFA au total."
                         .replace(',', ' '))
    else:
        messages.info(request, "Aucune nouvelle remise à attribuer : toutes les fratries en bénéficient déjà.")
    return redirect(retour)
