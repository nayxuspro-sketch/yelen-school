"""Sanctions disciplinaires."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.notifications import notifier_sanction
from parametres.models import AnneeScolaire, Classe, TypeSanction
from parametres.droits import autorise_url
from yelen_school.cycle_filter import get_cycle_ids, filtrer_classe_par_cycle
from pedagogie.models import Trimestre
from inscriptions.models import Inscription, StatutInscriptionChoices
from ..models import (
    SanctionDisciplinaire,
    ConfigDiscipline,
)


# ─── Sanctions disciplinaires ─────────────────────────────────────────────────

@login_required
def sanction_list(request):
    """Liste des sanctions disciplinaires, regroupées par classe."""
    from django.db.models import Q

    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    qs = SanctionDisciplinaire.objects.select_related(
        'inscription__eleve', 'inscription__classe__cycle', 'prononcee_par', 'trimestre', 'type_sanction'
    ).order_by('inscription__classe__cycle__ordre', 'inscription__classe__nom', '-date_sanction')

    if annee_courante:
        qs = qs.filter(inscription__annee_scolaire=annee_courante)

    # Filtrage par cycle pour les non-réseau
    cycle_ids = get_cycle_ids(request)
    if cycle_ids is not None and not cycle_ids:
        qs = qs.none()
    elif cycle_ids:
        qs = qs.filter(inscription__classe__cycle_id__in=cycle_ids)

    type_filtre = request.GET.get('type')
    if type_filtre:
        qs = qs.filter(type_sanction_id=type_filtre)

    statut_filtre = request.GET.get('statut')
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)

    classe_filtre = request.GET.get('classe')
    if classe_filtre:
        qs = qs.filter(inscription__classe_id=classe_filtre)

    date_min = request.GET.get('date_min')
    if date_min:
        qs = qs.filter(date_sanction__gte=date_min)

    eleve_q = request.GET.get('eleve')
    if eleve_q:
        qs = qs.filter(
            Q(inscription__eleve__nom__icontains=eleve_q) |
            Q(inscription__eleve__prenom__icontains=eleve_q) |
            Q(inscription__eleve__matricule__icontains=eleve_q)
        )

    etab = getattr(request.user, 'etablissement', None)
    if etab:
        classes = Classe.objects.filter(etablissement=etab).select_related('cycle').order_by('cycle__ordre', 'nom')
    else:
        classes = Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')
    classes = filtrer_classe_par_cycle(classes, request)

    groupes = {}
    for s in qs:
        classe = s.inscription.classe
        if classe.pk not in groupes:
            groupes[classe.pk] = {'classe': classe, 'sanctions': []}
        groupes[classe.pk]['sanctions'].append(s)

    types_sanction = TypeSanction.objects.filter(actif=True).order_by('libelle')

    return render(request, 'viescolaire/sanction_list.html', {
        'groupes': list(groupes.values()),
        'total': qs.count(),
        'nb_confirmees': qs.filter(statut='CONFIRME').count(),
        'nb_en_cours': qs.filter(statut='EN_COURS').count(),
        'nb_levees': qs.filter(statut='LEVEE').count(),
        'nb_avec_points': qs.exclude(points=0).count(),
        'annee_courante': annee_courante,
        'types_sanction': types_sanction,
        'type_filtre': type_filtre,
        'statut_filtre': statut_filtre,
        'classe_filtre': classe_filtre,
        'date_min_filtre': date_min,
        'eleve_filtre': eleve_q,
        'classes': classes,
    })


@login_required
def sanction_create(request):
    """Enregistrer une nouvelle sanction disciplinaire."""
    if not autorise_url(request, 'viescolaire:sanction_create'):
        messages.error(request, "Vous n'êtes pas autorisé à enregistrer des sanctions.")
        return redirect('viescolaire:sanction_list')

    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    cycle_ids = get_cycle_ids(request)
    classes_qs = Classe.objects.all()
    if cycle_ids is not None:
        if cycle_ids:
            classes_qs = classes_qs.filter(cycle_id__in=cycle_ids)
        else:
            classes_qs = classes_qs.none()
    classes = classes_qs.select_related('cycle').order_by('cycle__ordre', 'nom')

    context = {
        'annee_courante': annee_courante,
        'classes': classes,
        'types_sanction': TypeSanction.objects.filter(actif=True).order_by('libelle'),
        'trimestres': Trimestre.objects.filter(annee_scolaire=annee_courante).order_by('numero') if annee_courante else [],
    }

    if request.method == 'POST':
        inscription_id = request.POST.get('inscription')
        type_sanction_id = request.POST.get('type_sanction')
        date_sanction = request.POST.get('date_sanction')
        motif = request.POST.get('motif')
        points = request.POST.get('points', 0)
        statut = request.POST.get('statut', 'EN_COURS')

        try:
            inscription = Inscription.objects.get(pk=inscription_id)
            type_sanction = TypeSanction.objects.get(pk=type_sanction_id)
            trimestre_id = request.POST.get('trimestre')
            trimestre = Trimestre.objects.get(pk=trimestre_id) if trimestre_id else None

            SanctionDisciplinaire.objects.create(
                inscription=inscription,
                type_sanction=type_sanction,
                trimestre=trimestre,
                date_sanction=date_sanction,
                motif=motif,
                points=int(points) if points else 0,
                statut=statut,
                prononcee_par=request.user,
            )
            messages.success(request, "Sanction enregistrée avec succès.")
            return redirect('viescolaire:sanction_list')
        except (Inscription.DoesNotExist, TypeSanction.DoesNotExist, ValueError, Trimestre.DoesNotExist) as e:
            messages.error(request, f"Erreur lors de l'enregistrement : {e}")

    return render(request, 'viescolaire/sanction_form.html', context)


@login_required
def sanction_delete(request, sanction_id):
    """Supprimer une sanction disciplinaire."""
    sanction = get_object_or_404(SanctionDisciplinaire, pk=sanction_id)

    if request.method == 'POST':
        sanction.delete()
        messages.success(request, "Sanction supprimée avec succès.")
        return redirect('viescolaire:sanction_list')

    return render(request, 'viescolaire/sanction_confirm_delete.html', {
        'sanction': sanction,
    })
