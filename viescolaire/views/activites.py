"""Activités parascolaires."""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Exists, OuterRef, Q
from django.shortcuts import render, get_object_or_404, redirect

from django.contrib import messages

from inscriptions.models import Inscription, StatutInscriptionChoices
from .commun import _get_etab, annees_accessibles, classes_accessibles
from yelen_school.cycle_filter import get_cycle_ids
from ..models import (
    ActiviteParascolaire, ParticipationActivite,
    JourSemaine,
)


def _activites_accessibles(request, etablissement=None):
    """Activités de l'établissement sans inscription active hors du périmètre."""
    etablissement = etablissement or _get_etab(request)
    activites = ActiviteParascolaire.objects.filter(
        annee_scolaire__in=annees_accessibles(request, etablissement),
    )

    classes = classes_accessibles(request, etablissement)
    inscriptions_hors_perimetre = ParticipationActivite.objects.filter(
        activite_id=OuterRef('pk'),
    ).exclude(
        inscription__classe__in=classes,
        inscription__annee_scolaire_id=OuterRef('annee_scolaire_id'),
    )
    activites = activites.annotate(
        _a_des_inscriptions_hors_perimetre=Exists(inscriptions_hors_perimetre),
    ).filter(_a_des_inscriptions_hors_perimetre=False)
    cycle_ids = get_cycle_ids(request)
    if cycle_ids is not None:
        if not cycle_ids:
            return activites.none()
        responsables = _responsables_accessibles(request, etablissement)
        activites = activites.filter(
            Q(responsable__isnull=True) | Q(responsable__in=responsables),
        )
    return activites


def _responsables_accessibles(request, etablissement):
    """Comptes responsables dans l'établissement et les cycles autorisés."""
    responsables = get_user_model().objects.filter(
        is_active=True,
        etablissement=etablissement,
    )
    cycle_ids = get_cycle_ids(request)
    if cycle_ids is not None:
        if not cycle_ids:
            return responsables.none()
        responsables = responsables.filter(
            Q(cycles__in=cycle_ids) | Q(est_tous_cycles=True)
            | Q(role__in=('SUPER_ADMIN', 'DIRECTEUR_RESEAU')),
        ).distinct()
    return responsables.order_by('last_name', 'first_name')


# ─── Activités parascolaires ──────────────────────────────────────────────────

@login_required
def activite_list(request):
    """Liste les activités accessibles de l'année scolaire courante."""
    etab = _get_etab(request)
    annees_courantes = annees_accessibles(request, etab).filter(est_courante=True)
    annee_courante = annees_courantes.first()

    activites = _activites_accessibles(request, etab).select_related(
        'annee_scolaire', 'responsable'
    ).annotate(
        nb_participants_accessibles=Count(
            'participations',
            filter=Q(participations__is_active=True),
            distinct=True,
        ),
    ).order_by('type_activite', 'nom')
    if annees_courantes.exists():
        activites = activites.filter(annee_scolaire__in=annees_courantes)

    return render(request, 'viescolaire/activite_list.html', {
        'activites': activites,
        'annee_courante': annee_courante,
        'type_choices': ActiviteParascolaire.TypeActiviteChoices.choices,
    })


@login_required
def activite_detail(request, activite_id):
    """Détail d'une activité et des participants accessibles."""
    activite = get_object_or_404(
        _activites_accessibles(request).select_related('annee_scolaire', 'responsable'),
        pk=activite_id,
    )
    classes = classes_accessibles(request, activite.annee_scolaire.etablissement)
    participations = activite.participations.filter(
        is_active=True,
        inscription__classe__in=classes,
        inscription__annee_scolaire=activite.annee_scolaire,
    ).select_related(
        'inscription__eleve', 'inscription__classe'
    ).order_by('inscription__eleve__nom')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'inscrire':
            inscription = get_object_or_404(
                Inscription.objects.filter(
                    classe__in=classes,
                    annee_scolaire=activite.annee_scolaire,
                    is_active=True,
                ).exclude(statut=StatutInscriptionChoices.ABANDON),
                pk=request.POST.get('inscription'),
            )
            _, created = ParticipationActivite.objects.get_or_create(
                activite=activite, inscription=inscription,
            )
            if created:
                messages.success(request, f"{inscription.eleve} inscrit(e) à {activite.nom}.")
            else:
                messages.info(request, "Cet élève est déjà inscrit.")
        elif action == 'retirer':
            participation = get_object_or_404(
                participations,
                pk=request.POST.get('participation_id'),
            )
            participation.is_active = False
            participation.save(update_fields=['is_active', 'updated_at'])
            messages.success(request, "Élève retiré de l'activité.")
        return redirect('viescolaire:activite_detail', activite_id=activite.pk)

    inscrits_ids = participations.values_list('inscription_id', flat=True)
    inscriptions_dispo = Inscription.objects.filter(
        annee_scolaire=activite.annee_scolaire,
        classe__in=classes,
        is_active=True,
    ).exclude(
        pk__in=inscrits_ids,
    ).exclude(
        statut=StatutInscriptionChoices.ABANDON,
    ).select_related('eleve', 'classe').order_by('eleve__nom')

    return render(request, 'viescolaire/activite_detail.html', {
        'activite': activite,
        'participations': participations,
        'inscriptions_dispo': inscriptions_dispo,
    })


@login_required
def activite_create(request):
    """Créer une activité parascolaire dans l'établissement accessible."""
    etab = _get_etab(request)
    annees_courantes = annees_accessibles(request, etab).filter(est_courante=True)
    annee_courante = annees_courantes.first()
    responsable_etab = etab or getattr(annee_courante, 'etablissement', None)
    responsables = _responsables_accessibles(request, responsable_etab)

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom de l'activité est obligatoire.")
        elif not annee_courante:
            messages.error(request, "Aucune année scolaire courante définie.")
        else:
            try:
                responsable_id = request.POST.get('responsable') or None
                responsable = responsables.get(pk=responsable_id) if responsable_id else None
                ActiviteParascolaire.objects.create(
                    annee_scolaire=annee_courante,
                    nom=nom,
                    type_activite=request.POST.get('type_activite', ActiviteParascolaire.TypeActiviteChoices.CLUB),
                    description=request.POST.get('description', '').strip(),
                    responsable=responsable,
                    capacite_max=int(request.POST.get('capacite_max') or 30),
                    jour_reunion=request.POST.get('jour_reunion') or None,
                    heure_debut=request.POST.get('heure_debut') or None,
                )
                messages.success(request, f"Activité « {nom} » créée.")
                return redirect('viescolaire:activite_list')
            except (ValueError, ObjectDoesNotExist) as e:
                messages.error(request, str(e))

    return render(request, 'viescolaire/activite_form.html', {
        'titre': 'Nouvelle activité parascolaire',
        'submit_label': 'Créer l\'activité',
        'type_choices': ActiviteParascolaire.TypeActiviteChoices.choices,
        'jour_choices': JourSemaine.choices,
        'responsables': responsables,
        'annee_courante': annee_courante,
    })


@login_required
def activite_edit(request, activite_id):
    """Modifier une activité accessible."""
    activite = get_object_or_404(
        _activites_accessibles(request).select_related('annee_scolaire', 'responsable'),
        pk=activite_id,
    )
    responsables = _responsables_accessibles(
        request, activite.annee_scolaire.etablissement,
    )

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom est obligatoire.")
        else:
            try:
                responsable_id = request.POST.get('responsable') or None
                responsable = responsables.get(pk=responsable_id) if responsable_id else None
                activite.nom = nom
                activite.type_activite = request.POST.get('type_activite', activite.type_activite)
                activite.description = request.POST.get('description', '').strip()
                activite.responsable = responsable
                activite.capacite_max = int(request.POST.get('capacite_max') or 30)
                activite.jour_reunion = request.POST.get('jour_reunion') or None
                activite.heure_debut = request.POST.get('heure_debut') or None
                activite.save(update_fields=[
                    'nom', 'type_activite', 'description', 'responsable',
                    'capacite_max', 'jour_reunion', 'heure_debut', 'updated_at',
                ])
                messages.success(request, f"Activité « {activite.nom} » mise à jour.")
                return redirect('viescolaire:activite_detail', activite_id=activite.pk)
            except (ValueError, ObjectDoesNotExist) as e:
                messages.error(request, str(e))

    return render(request, 'viescolaire/activite_form.html', {
        'activite': activite,
        'titre': f'Modifier — {activite.nom}',
        'submit_label': 'Enregistrer',
        'type_choices': ActiviteParascolaire.TypeActiviteChoices.choices,
        'jour_choices': JourSemaine.choices,
        'responsables': responsables,
    })


@login_required
def activite_delete(request, activite_id):
    """Supprimer une activité sans inscription hors du périmètre accessible."""
    activite = get_object_or_404(_activites_accessibles(request), pk=activite_id)
    if request.method == 'POST':
        nb = activite.participations.filter(is_active=True).count()
        nom = activite.nom
        activite.delete()
        messages.success(request, f"Activité « {nom} » supprimée ({nb} participant(s) retiré(s)).")
        return redirect('viescolaire:activite_list')
    return render(request, 'viescolaire/activite_confirm_delete.html', {'activite': activite})
