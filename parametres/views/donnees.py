"""Données personnelles : durée de conservation, anonymisation des élèves sortis, registre des traitements."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core import donnees_personnelles as dp
from ..forms import PolitiqueDonneesForm
from .commun import _get_etab


@login_required
def donnees_personnelles(request):
    etab = _get_etab(request)
    if not etab:
        return redirect('parametres:index')
    politique = dp.politique_de(etab)
    if request.method == 'POST':
        form = PolitiqueDonneesForm(request.POST, instance=politique)
        if form.is_valid():
            form.save()
            messages.success(request, "Politique de conservation enregistrée.")
            return redirect('parametres:donnees_personnelles')
    else:
        form = PolitiqueDonneesForm(instance=politique)
    candidats = dp.eleves_a_anonymiser(etab, politique.duree_conservation_annees)
    return render(request, 'parametres/donnees_personnelles.html', {
        'form': form, 'politique': politique, 'nb_candidats': candidats.count(), 'candidats': candidats[:20],
        'date_limite': dp.date_limite(politique.duree_conservation_annees), 'registre': dp.REGISTRE,
    })


@login_required
@require_POST
def anonymiser(request):
    etab = _get_etab(request)
    if not etab:
        return redirect('parametres:index')
    bilan = dp.anonymiser(etab, user=request.user, request=request)
    messages.success(request, (
        f"Anonymisation terminée : {bilan['eleves']} élève(s), {bilan['comptes']} compte(s) fermé(s), "
        f"{bilan['fichiers']} fichier(s) supprimé(s), {bilan['preinscriptions']} pré-inscription(s) effacée(s)."
    ))
    return redirect('parametres:donnees_personnelles')
