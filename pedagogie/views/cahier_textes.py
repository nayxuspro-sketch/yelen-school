"""Cahier de textes.

Issu du découpage mécanique de ``pedagogie/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from ..models import Enseignement, CahierTextes
from parametres.models import AnneeScolaire, Classe
from core.utils import filtre_enseignant


@login_required
def cahier_textes_index(request):
    """Sélecteur de classe pour accéder au cahier de textes."""
    etab = getattr(request.user, 'etablissement', None)
    classes = (
        Classe.objects.filter(etablissement=etab, actif=True)
        .select_related('cycle')
        .order_by('cycle__ordre', 'cycle__nom', 'nom')
    ) if etab else Classe.objects.none()

    # Si enseignant : restreindre aux classes où il enseigne
    if request.user.role == 'ENSEIGNANT':
        annee = AnneeScolaire.objects.filter(
            etablissement=etab, est_courante=True
        ).first() if etab else None
        if annee:
            classe_ids = Enseignement.objects.filter(
                annee_scolaire=annee,
                personnel=filtre_enseignant(request.user),
                est_actif=True,
            ).values_list('classe_id', flat=True)
            classes = classes.filter(pk__in=classe_ids)

    cycles = {}
    for c in classes:
        key = c.cycle_id
        if key not in cycles:
            cycles[key] = {'cycle': c.cycle, 'classes': []}
        cycles[key]['classes'].append(c)

    return render(request, 'pedagogie/cahier_textes_index.html', {
        'cycles': sorted(cycles.values(), key=lambda x: getattr(x['cycle'], 'ordre', 0)),
    })


@login_required
def cahier_textes_classe(request, classe_id):
    """Liste des entrées du cahier de textes d'une classe, avec filtres."""
    etab = getattr(request.user, 'etablissement', None)
    classe = get_object_or_404(Classe, pk=classe_id)

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut') if etab else AnneeScolaire.objects.none()
    annee_id = request.GET.get('annee')
    annee = annees.filter(pk=annee_id).first() if annee_id else annees.filter(est_courante=True).first()

    enseignement_id = request.GET.get('enseignement')
    enseignements = Enseignement.objects.filter(
        classe=classe, annee_scolaire=annee, est_actif=True
    ).select_related('matiere', 'personnel') if annee else Enseignement.objects.none()

    # Enseignant ne voit que ses propres matières
    if request.user.role == 'ENSEIGNANT':
        enseignements = enseignements.filter(personnel=filtre_enseignant(request.user))

    entrees = CahierTextes.objects.filter(
        enseignement__classe=classe,
        enseignement__annee_scolaire=annee,
    ).select_related(
        'enseignement__matiere', 'enseignement__personnel', 'redige_par'
    ).order_by('-date', '-created_at') if annee else CahierTextes.objects.none()

    if enseignement_id:
        entrees = entrees.filter(enseignement_id=enseignement_id)

    if request.user.role == 'ENSEIGNANT':
        entrees = entrees.filter(enseignement__personnel=filtre_enseignant(request.user))

    is_htmx = request.headers.get('HX-Request')
    template = 'pedagogie/partials/cahier_textes_liste.html' if is_htmx else 'pedagogie/cahier_textes_classe.html'

    return render(request, template, {
        'classe': classe,
        'annees': annees,
        'annee': annee,
        'enseignements': enseignements,
        'enseignement_selectionne': enseignement_id,
        'entrees': entrees,
    })


@login_required
def cahier_textes_create(request):
    """Créer une entrée du cahier de textes (formulaire HTMX)."""
    etab = getattr(request.user, 'etablissement', None)
    classe_id = request.GET.get('classe') or request.POST.get('classe')
    classe = get_object_or_404(Classe, pk=classe_id) if classe_id else None

    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    enseignements = Enseignement.objects.filter(
        classe=classe, annee_scolaire=annee, est_actif=True
    ).select_related('matiere') if (classe and annee) else Enseignement.objects.none()

    if request.user.role == 'ENSEIGNANT':
        enseignements = enseignements.filter(personnel=filtre_enseignant(request.user))

    if request.method == 'POST':
        enseignement_id = request.POST.get('enseignement')
        date = request.POST.get('date')
        heure_debut = request.POST.get('heure_debut') or None
        heure_fin = request.POST.get('heure_fin') or None
        contenu = request.POST.get('contenu', '').strip()
        devoirs = request.POST.get('devoirs', '').strip()
        date_remise = request.POST.get('date_remise_devoirs') or None

        if not enseignement_id or not date or not contenu:
            messages.error(request, "L'enseignement, la date et le contenu sont obligatoires.")
        else:
            enseignement = get_object_or_404(Enseignement, pk=enseignement_id)
            CahierTextes.objects.create(
                enseignement=enseignement,
                date=date,
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                contenu=contenu,
                devoirs=devoirs,
                date_remise_devoirs=date_remise,
                redige_par=request.user,
            )
            messages.success(request, "Entrée ajoutée au cahier de textes.")
            return redirect('pedagogie:cahier_textes_classe', classe_id=classe.pk)

    return render(request, 'pedagogie/cahier_textes_form.html', {
        'classe': classe,
        'annee': annee,
        'enseignements': enseignements,
        'action': 'create',
    })


@login_required
def cahier_textes_update(request, pk):
    """Modifier une entrée du cahier de textes."""
    entree = get_object_or_404(CahierTextes, pk=pk)
    classe = entree.enseignement.classe
    annee = entree.enseignement.annee_scolaire

    enseignements = Enseignement.objects.filter(
        classe=classe, annee_scolaire=annee, est_actif=True
    ).select_related('matiere')

    if request.user.role == 'ENSEIGNANT':
        enseignements = enseignements.filter(personnel=filtre_enseignant(request.user))

    if request.method == 'POST':
        heure_debut = request.POST.get('heure_debut') or None
        heure_fin = request.POST.get('heure_fin') or None
        contenu = request.POST.get('contenu', '').strip()
        devoirs = request.POST.get('devoirs', '').strip()
        date_remise = request.POST.get('date_remise_devoirs') or None

        if not contenu:
            messages.error(request, "Le contenu du cours est obligatoire.")
        else:
            entree.heure_debut = heure_debut
            entree.heure_fin = heure_fin
            entree.contenu = contenu
            entree.devoirs = devoirs
            entree.date_remise_devoirs = date_remise
            entree.save()
            messages.success(request, "Entrée mise à jour.")
            return redirect('pedagogie:cahier_textes_classe', classe_id=classe.pk)

    return render(request, 'pedagogie/cahier_textes_form.html', {
        'classe': classe,
        'annee': annee,
        'enseignements': enseignements,
        'entree': entree,
        'action': 'update',
    })


@login_required
@require_POST
def cahier_textes_delete(request, pk):
    """Supprimer une entrée du cahier de textes."""
    entree = get_object_or_404(CahierTextes, pk=pk)
    classe_id = entree.enseignement.classe_id
    entree.delete()
    messages.success(request, "Entrée supprimée.")
    return redirect('pedagogie:cahier_textes_classe', classe_id=classe_id)
