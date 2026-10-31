"""Inscriptions et changements de statut (abandon, transfert de classe)."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .. import services
from ..models import Eleve, Inscription, StatutInscriptionChoices
from ..forms import InscriptionForm, TransfertClasseForm
from parametres.models import AnneeScolaire


@login_required
def inscription_create(request, pk):
    """Réinscription ou nouvelle inscription annuelle d'un élève."""
    eleve = get_object_or_404(Eleve, pk=pk)
    etab = getattr(request.user, 'etablissement', None)

    if etab and eleve.inscriptions.exists() and not eleve.inscriptions.filter(classe__etablissement=etab).exists():
        messages.error(request, "Accès refusé. Cet élève n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')

    if request.method == 'POST':
        form = InscriptionForm(request.POST, etablissement=etab)
        if form.is_valid():
            inscription = form.save(commit=False)
            inscription.eleve = eleve
            inscription.save()
            eleve.last_classe = inscription.classe.nom
            eleve.last_annee = inscription.annee_scolaire.libelle
            eleve.save(update_fields=['last_classe', 'last_annee'])
            messages.success(request, f"Inscription confirmée pour {eleve.get_nom_complet()}.")
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        annee_courante = AnneeScolaire.objects.filter(etablissement=etab, est_courante=True).first()
        form = InscriptionForm(
            initial={'eleve': eleve, 'annee_scolaire': annee_courante, 'statut_eleve': 'AFFECTE'},
            etablissement=etab,
        )

    return render(request, 'inscriptions/inscription_form.html', {
        'form': form,
        'eleve': eleve
    })


@login_required
def inscription_update(request, pk):
    """Modifier une inscription existante."""
    inscription = get_object_or_404(Inscription, pk=pk)
    eleve = inscription.eleve
    etab = getattr(request.user, 'etablissement', None)

    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')

    if request.method == 'POST':
        form = InscriptionForm(request.POST, instance=inscription, etablissement=etab)
        if form.is_valid():
            form.save()
            eleve.last_classe = inscription.classe.nom
            eleve.last_annee = inscription.annee_scolaire.libelle
            eleve.save(update_fields=['last_classe', 'last_annee'])
            messages.success(request, f"Inscription de {eleve.get_nom_complet()} mise à jour.")
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        form = InscriptionForm(instance=inscription, etablissement=etab)

    return render(request, 'inscriptions/inscription_form.html', {
        'form': form,
        'eleve': eleve,
        'inscription': inscription,
        'is_update': True
    })


@login_required
def get_classe_niveau(request, pk):
    """API endpoint to get the niveau of a class."""
    from django.http import JsonResponse
    from parametres.models import Classe

    try:
        classe = Classe.objects.get(pk=pk)
        return JsonResponse({'niveau': classe.niveau})
    except Classe.DoesNotExist:
        return JsonResponse({'niveau': ''})


@login_required
def get_classe_cycle(request, pk):
    """API endpoint to get the cycle of a class."""
    from django.http import JsonResponse
    from parametres.models import Classe

    try:
        classe = Classe.objects.select_related('cycle').get(pk=pk)
        return JsonResponse({
            'cycle': classe.cycle.nom if classe.cycle else '',
            'cycle_id': str(classe.cycle.pk) if classe.cycle else ''
        })
    except Classe.DoesNotExist:
        return JsonResponse({'cycle': '', 'cycle_id': ''})


@login_required
def get_statut_code(request, pk):
    """API endpoint to get the code and nom of a statut eleve."""
    from django.http import JsonResponse
    from parametres.models import StatutEleve

    try:
        statut = StatutEleve.objects.get(pk=pk)
        return JsonResponse({'code': statut.code, 'nom': statut.nom})
    except StatutEleve.DoesNotExist:
        return JsonResponse({'code': '', 'nom': ''})


def _get_inscription_courante(eleve):
    """Retourne l'inscription de l'année courante, sinon la plus récente."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    if annee_courante:
        ins = Inscription.objects.filter(
            eleve=eleve, annee_scolaire=annee_courante
        ).select_related('classe__cycle', 'classe__etablissement', 'annee_scolaire', 'statut_eleve').first()
        if ins:
            return ins
    return Inscription.objects.filter(eleve=eleve).select_related(
        'classe__cycle', 'classe__etablissement', 'annee_scolaire', 'statut_eleve'
    ).order_by('-annee_scolaire__date_debut').first()


@login_required
def marquer_abandon(request, pk):
    """Marque une inscription comme Abandon (ou annule l'abandon)."""
    inscription = get_object_or_404(Inscription, pk=pk)
    etab = getattr(request.user, 'etablissement', None)

    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')

    if request.method == 'POST':
        if services.message_annee_cloturee(inscription.annee_scolaire):
            messages.error(request, services.message_annee_cloturee(inscription.annee_scolaire))
            return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)
        if inscription.statut == StatutInscriptionChoices.ABANDON:
            inscription.statut = 'AFFECTE'
            messages.success(request, f"{inscription.eleve.get_nom_complet()} — Abandon annulé, statut remis à Affecté.")
        else:
            inscription.statut = StatutInscriptionChoices.ABANDON
            messages.warning(request, f"{inscription.eleve.get_nom_complet()} — Marqué(e) Abandon pour {inscription.annee_scolaire.libelle}.")
        inscription.save(update_fields=['statut'])
    return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)


@login_required
def transfert_classe(request, pk):
    """Transfert d'un élève vers une autre classe pour la même année scolaire."""
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe', 'annee_scolaire'),
        pk=pk,
    )
    etab = getattr(request.user, 'etablissement', None)

    if etab and inscription.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette inscription n'appartient pas à votre établissement.")
        return redirect('inscriptions:eleve_list')

    if inscription.statut == StatutInscriptionChoices.ABANDON:
        messages.error(request, "Impossible de transférer une inscription marquée Abandon.")
        return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)
    if services.message_annee_cloturee(inscription.annee_scolaire):
        messages.error(request, services.message_annee_cloturee(inscription.annee_scolaire))
        return redirect('inscriptions:eleve_detail', pk=inscription.eleve.pk)

    if request.method == 'POST':
        form = TransfertClasseForm(request.POST, inscription=inscription, etablissement=etab)
        if form.is_valid():
            ancienne_classe = inscription.classe
            inscription.classe = form.cleaned_data['classe']
            inscription.save(update_fields=['classe'])
            eleve = inscription.eleve
            eleve.last_classe = inscription.classe.nom
            eleve.last_annee = inscription.annee_scolaire.libelle
            eleve.save(update_fields=['last_classe', 'last_annee'])
            messages.success(
                request,
                f"{eleve.get_nom_complet()} transféré(e) de "
                f"{ancienne_classe.nom} vers {inscription.classe.nom}."
            )
            return redirect('inscriptions:eleve_detail', pk=eleve.pk)
    else:
        form = TransfertClasseForm(inscription=inscription, etablissement=etab)

    return render(request, 'inscriptions/transfert_classe.html', {
        'form': form,
        'inscription': inscription,
        'eleve': inscription.eleve,
    })
