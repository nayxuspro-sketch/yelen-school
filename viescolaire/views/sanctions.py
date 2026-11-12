"""Sanctions disciplinaires."""

import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from core.notifications import notifier_sanction
from parametres.models import TypeSanction
from parametres.droits import autorise_url
from .commun import _get_etab, annees_accessibles, classes_accessibles
from pedagogie.models import Trimestre
from inscriptions.models import Inscription, StatutInscriptionChoices
from ..models import (
    SanctionDisciplinaire,
    ConfigDiscipline,
)


# ─── Sanctions disciplinaires ─────────────────────────────────────────────────

@login_required
def sanction_list(request):
    """Liste les sanctions des classes accessibles, regroupées par classe."""
    etab = _get_etab(request)
    annees_courantes = annees_accessibles(request, etab).filter(est_courante=True)
    annee_courante = annees_courantes.first()
    classes = classes_accessibles(request, etab).select_related('cycle').order_by('cycle__ordre', 'nom')

    qs = SanctionDisciplinaire.objects.filter(
        inscription__classe__in=classes,
    ).select_related(
        'inscription__eleve', 'inscription__classe__cycle', 'prononcee_par', 'trimestre', 'type_sanction'
    ).order_by('inscription__classe__cycle__ordre', 'inscription__classe__nom', '-date_sanction')

    if annees_courantes.exists():
        qs = qs.filter(inscription__annee_scolaire__in=annees_courantes)

    type_filtre = request.GET.get('type')
    if type_filtre:
        qs = qs.filter(type_sanction_id=type_filtre)

    statut_filtre = request.GET.get('statut')
    if statut_filtre:
        qs = qs.filter(statut=statut_filtre)

    classe_filtre = request.GET.get('classe')
    if classe_filtre:
        qs = qs.filter(inscription__classe__in=classes, inscription__classe_id=classe_filtre)

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

    etab = _get_etab(request)
    annees_courantes = annees_accessibles(request, etab).filter(est_courante=True)
    annee_courante = annees_courantes.first()
    classes = classes_accessibles(request, etab).select_related('cycle').order_by('cycle__ordre', 'nom')
    trimestres = Trimestre.objects.filter(
        annee_scolaire__in=annees_courantes,
    ).order_by('annee_scolaire__date_debut', 'numero')
    types_sanction = TypeSanction.objects.filter(actif=True).order_by('libelle')
    classe_id = request.GET.get('classe', '')
    classes_selectionnees = classes.filter(pk=classe_id) if classe_id else classes.none()
    inscriptions = Inscription.objects.filter(
        classe__in=classes_selectionnees,
        annee_scolaire__in=annees_courantes,
    ).exclude(
        statut=StatutInscriptionChoices.ABANDON,
    ).select_related('eleve', 'classe').order_by('eleve__nom', 'eleve__prenom')
    config_disc = ConfigDiscipline.get_or_default(etab) if etab else None

    context = {
        'annee_courante': annee_courante,
        'classes': classes,
        'classe_id': classe_id,
        'inscriptions': inscriptions,
        'types_sanction': types_sanction,
        'types_sanction_json': json.dumps({str(t.pk): float(t.points_defaut) for t in types_sanction}),
        'statut_choices': SanctionDisciplinaire.StatutChoices.choices,
        'trimestres': trimestres,
        'config_disc': config_disc,
    }

    if request.method == 'POST':
        inscription_id = request.POST.get('inscription')
        type_sanction_id = request.POST.get('type_sanction')
        date_sanction = request.POST.get('date_sanction')
        motif = request.POST.get('motif')
        points = request.POST.get('points', 0)
        statut = request.POST.get('statut', 'EN_COURS')

        try:
            inscriptions_accessibles = Inscription.objects.filter(
                classe__in=classes,
                annee_scolaire__in=annees_courantes,
            ).exclude(statut=StatutInscriptionChoices.ABANDON)
            inscription = inscriptions_accessibles.get(pk=inscription_id)
            type_sanction = types_sanction.get(pk=type_sanction_id)
            trimestre_id = request.POST.get('trimestre')
            trimestre = trimestres.get(pk=trimestre_id) if trimestre_id else None
            if trimestre and trimestre.annee_scolaire_id != inscription.annee_scolaire_id:
                raise ValueError("Le trimestre ne correspond pas à l'année de l'inscription.")
            if statut not in SanctionDisciplinaire.StatutChoices.values:
                raise ValueError("Statut de sanction invalide.")

            sanction = SanctionDisciplinaire.objects.create(
                inscription=inscription,
                type_sanction=type_sanction,
                trimestre=trimestre,
                date_sanction=date_sanction,
                motif=motif,
                points=Decimal(str(points or '0')),
                statut=statut,
                prononcee_par=request.user,
            )
            messages.success(request, "Sanction enregistrée avec succès.")
            if request.POST.get('prevenir_parents') == 'on':
                if notifier_sanction(sanction):
                    sanction.parents_notifies_le = timezone.now()
                    sanction.save(update_fields=['parents_notifies_le'])
                    messages.success(request, "Parent informé (portail / SMS).")
                else:
                    messages.warning(request, "Parent non informé : aucun compte parent ni numéro de téléphone disponible.")
            return redirect('viescolaire:sanction_list')
        except (
            Inscription.DoesNotExist, TypeSanction.DoesNotExist, Trimestre.DoesNotExist,
            ValueError, InvalidOperation,
        ) as e:
            messages.error(request, f"Erreur lors de l'enregistrement : {e}")

    return render(request, 'viescolaire/sanction_create.html', context)


@login_required
def sanction_delete(request, sanction_id):
    """Supprimer une sanction d'une classe accessible."""
    sanction = get_object_or_404(
        SanctionDisciplinaire.objects.filter(
            inscription__classe__in=classes_accessibles(request),
        ),
        pk=sanction_id,
    )

    if request.method == 'POST':
        sanction.delete()
        messages.success(request, "Sanction supprimée avec succès.")
        return redirect('viescolaire:sanction_list')

    return render(request, 'viescolaire/sanction_confirm_delete.html', {
        'sanction': sanction,
    })
