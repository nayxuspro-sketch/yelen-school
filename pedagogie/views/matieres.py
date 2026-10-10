"""Matières, configuration par cycle et enseignements.

Issu du découpage mécanique de ``pedagogie/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from ..models import Matiere, MatiereCycle, Enseignement
from ..forms import MatiereForm, MatiereCycleForm, EnseignementForm
from ..selectors import configurations_matiere, ligne_configuration
from parametres.models import AnneeScolaire, Cycle


@login_required
def matiere_list(request):
    """Liste des matières avec filtrage HTMX."""
    query = request.GET.get('q', '')
    matieres = Matiere.objects.all()
    
    if query:
        matieres = matieres.filter(
            Q(nom__icontains=query) | 
            Q(code__icontains=query) |
            Q(nom_complet__icontains=query)
        )
    
    context = {
        'matiere_list': matieres,
        'query': query,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'pedagogie/partials/matiere_table.html', context)
        
    return render(request, 'pedagogie/matiere_list.html', context)


@login_required
def matiere_create(request):
    """Ajout d'une nouvelle matière."""
    if request.method == 'POST':
        form = MatiereForm(request.POST)
        if form.is_valid():
            matiere = form.save()
            messages.success(request, f"Matière {matiere.nom} créée. Configurez les coefficients par cycle.")
            return redirect('pedagogie:matiere_update', pk=matiere.pk)
    else:
        form = MatiereForm()

    return render(request, 'pedagogie/matiere_form.html', {
        'form': form,
        'title': "Ajouter une matière",
        'cycles_config': [],
    })


@login_required
def matiere_update(request, pk):
    """Modification d'une matière et de ses configurations par cycle."""
    matiere = get_object_or_404(Matiere, pk=pk)

    if request.method == 'POST':
        form = MatiereForm(request.POST, instance=matiere)
        if form.is_valid():
            form.save()
            messages.success(request, f"Matière {matiere.nom} mise à jour.")
            return redirect('pedagogie:matiere_list')
    else:
        form = MatiereForm(instance=matiere)

    return render(request, 'pedagogie/matiere_form.html', {
        'form': form,
        'title': "Modifier la matière",
        'matiere': matiere,
        'cycles_config': configurations_matiere(matiere),
    })


@login_required
def matiere_cycle_save(request, matiere_pk, cycle_pk):
    """Sauvegarde HTMX de la configuration d'une matière pour une portée d'un cycle.

    La portée est transmise par les champs ``niveau`` et ``serie`` (vides = tout le cycle).
    Un coefficient vide ou le champ ``supprimer`` retire la configuration : la valeur héritée s'applique.
    """
    matiere = get_object_or_404(Matiere, pk=matiere_pk)
    cycle = get_object_or_404(Cycle, pk=cycle_pk)
    donnees = request.POST if request.method == 'POST' else request.GET
    niveau = donnees.get('niveau', '').strip()[:50]
    serie = donnees.get('serie', '').strip()[:10]
    instance = MatiereCycle.objects.filter(matiere=matiere, cycle=cycle, niveau=niveau, serie=serie).first()
    form = None

    if request.method == 'POST':
        if donnees.get('supprimer') or not donnees.get('coefficient', '').strip():
            if instance:
                instance.delete()
        else:
            form = MatiereCycleForm(request.POST, instance=instance)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.matiere, obj.cycle, obj.niveau, obj.serie = matiere, cycle, niveau, serie
                obj.save()
                form = None  # ligne réaffichée depuis la base

    return render(request, 'pedagogie/partials/cycle_config_row.html', {
        'matiere': matiere, 'cycle': cycle,
        'ligne': ligne_configuration(matiere, cycle, niveau, serie, form=form),
    })


@login_required
def enseignement_list(request):
    """Liste des enseignements (affectations profs-matières-classes), groupés par classe."""
    from itertools import groupby
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    qs = Enseignement.objects.filter(annee_scolaire=annee_courante).select_related(
        'classe__cycle', 'matiere', 'personnel'
    ).order_by('classe__cycle__ordre', 'classe__nom', 'matiere__nom')

    classes_groupes = [
        {'classe': classe, 'enseignements': list(items)}
        for classe, items in groupby(qs, key=lambda e: e.classe)
    ]

    context = {
        'classes_groupes': classes_groupes,
        'annee_courante': annee_courante,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'pedagogie/partials/enseignement_table.html', context)

    return render(request, 'pedagogie/enseignement_list.html', context)


@login_required
def enseignement_create(request):
    """Nouvelle affectation d'enseignement."""
    if request.method == 'POST':
        form = EnseignementForm(request.POST)
        if form.is_valid():
            enseignement = form.save()
            messages.success(request, f"Affectation {enseignement} réussie.")
            return redirect('pedagogie:enseignement_list')
    else:
        annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
        form = EnseignementForm(initial={'annee_scolaire': annee_courante})
    
    return render(request, 'pedagogie/enseignement_form.html', {
        'form': form,
        'title': "Nouvelle Affectation"
    })


@login_required
def enseignement_update(request, pk):
    """Modification d'une affectation."""
    enseignement = get_object_or_404(Enseignement, pk=pk)
    if request.method == 'POST':
        form = EnseignementForm(request.POST, instance=enseignement)
        if form.is_valid():
            form.save()
            messages.success(request, f"Affectation {enseignement} mise à jour.")
            return redirect('pedagogie:enseignement_list')
    else:
        form = EnseignementForm(instance=enseignement)
    
    return render(request, 'pedagogie/enseignement_form.html', {
        'form': form,
        'title': "Modifier l'affectation",
        'enseignement': enseignement
    })
