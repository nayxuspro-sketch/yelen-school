"""Activités parascolaires."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from django.contrib import messages

from parametres.models import AnneeScolaire
from inscriptions.models import Inscription, StatutInscriptionChoices
from ..models import (
    ActiviteParascolaire, ParticipationActivite,
    JourSemaine,
)


# ─── Activités parascolaires ──────────────────────────────────────────────────

@login_required
def activite_list(request):
    """Liste des activités parascolaires filtrées par établissement."""
    etab = getattr(request.user, 'etablissement', None)

    annee_qs = AnneeScolaire.objects.filter(est_courante=True)
    if etab:
        annee_qs = annee_qs.filter(etablissement=etab)
    annee_courante = annee_qs.first()

    activites = ActiviteParascolaire.objects.select_related(
        'annee_scolaire', 'responsable'
    ).prefetch_related('participations').order_by('type_activite', 'nom')

    if etab:
        activites = activites.filter(annee_scolaire__etablissement=etab)
    if annee_courante:
        activites = activites.filter(annee_scolaire=annee_courante)

    return render(request, 'viescolaire/activite_list.html', {
        'activites': activites,
        'annee_courante': annee_courante,
        'type_choices': ActiviteParascolaire.TypeActiviteChoices.choices,
    })


@login_required
def activite_detail(request, activite_id):
    """Détail d'une activité + liste des participants."""
    activite = get_object_or_404(
        ActiviteParascolaire.objects.select_related('annee_scolaire', 'responsable'),
        pk=activite_id
    )
    participations = activite.participations.select_related(
        'inscription__eleve', 'inscription__classe'
    ).filter(is_active=True).order_by('inscription__eleve__nom')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'inscrire':
            inscription_id = request.POST.get('inscription')
            inscription = get_object_or_404(Inscription, pk=inscription_id)
            _, created = ParticipationActivite.objects.get_or_create(
                activite=activite, inscription=inscription
            )
            if created:
                messages.success(request, f"{inscription.eleve} inscrit(e) à {activite.nom}.")
            else:
                messages.info(request, "Cet élève est déjà inscrit.")
        elif action == 'retirer':
            part_id = request.POST.get('participation_id')
            ParticipationActivite.objects.filter(pk=part_id).update(is_active=False)
            messages.success(request, "Élève retiré de l'activité.")
        return redirect('viescolaire:activite_detail', activite_id=activite.pk)

    # Élèves disponibles pour inscription (année scolaire de l'activité)
    inscrits_ids = participations.values_list('inscription_id', flat=True)
    inscriptions_dispo = Inscription.objects.filter(
        annee_scolaire=activite.annee_scolaire, is_active=True
    ).exclude(pk__in=inscrits_ids).exclude(statut=StatutInscriptionChoices.ABANDON).select_related('eleve', 'classe').order_by('eleve__nom')

    return render(request, 'viescolaire/activite_detail.html', {
        'activite': activite,
        'participations': participations,
        'inscriptions_dispo': inscriptions_dispo,
    })


@login_required
def activite_create(request):
    """Créer une activité parascolaire."""
    etab = getattr(request.user, 'etablissement', None)
    annee_qs = AnneeScolaire.objects.filter(est_courante=True)
    if etab:
        annee_qs = annee_qs.filter(etablissement=etab)
    annee_courante = annee_qs.first()

    from django.contrib.auth import get_user_model
    User = get_user_model()
    responsables = User.objects.filter(is_active=True).order_by('last_name', 'first_name')

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom de l'activité est obligatoire.")
        elif not annee_courante:
            messages.error(request, "Aucune année scolaire courante définie.")
        else:
            try:
                ActiviteParascolaire.objects.create(
                    annee_scolaire=annee_courante,
                    nom=nom,
                    type_activite=request.POST.get('type_activite', ActiviteParascolaire.TypeActiviteChoices.CLUB),
                    description=request.POST.get('description', '').strip(),
                    responsable_id=request.POST.get('responsable') or None,
                    capacite_max=int(request.POST.get('capacite_max') or 30),
                    jour_reunion=request.POST.get('jour_reunion') or None,
                    heure_debut=request.POST.get('heure_debut') or None,
                )
                messages.success(request, f"Activité « {nom} » créée.")
                return redirect('viescolaire:activite_list')
            except ValueError as e:
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
    """Modifier une activité parascolaire."""
    activite = get_object_or_404(ActiviteParascolaire, pk=activite_id)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    responsables = User.objects.filter(is_active=True).order_by('last_name', 'first_name')

    if request.method == 'POST':
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom est obligatoire.")
        else:
            try:
                activite.nom = nom
                activite.type_activite = request.POST.get('type_activite', activite.type_activite)
                activite.description = request.POST.get('description', '').strip()
                activite.responsable_id = request.POST.get('responsable') or None
                activite.capacite_max = int(request.POST.get('capacite_max') or 30)
                activite.jour_reunion = request.POST.get('jour_reunion') or None
                activite.heure_debut = request.POST.get('heure_debut') or None
                activite.save(update_fields=[
                    'nom', 'type_activite', 'description', 'responsable',
                    'capacite_max', 'jour_reunion', 'heure_debut', 'updated_at',
                ])
                messages.success(request, f"Activité « {activite.nom} » mise à jour.")
                return redirect('viescolaire:activite_detail', activite_id=activite.pk)
            except ValueError as e:
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
    """Supprimer une activité parascolaire."""
    activite = get_object_or_404(ActiviteParascolaire, pk=activite_id)
    if request.method == 'POST':
        nb = activite.participations.filter(is_active=True).count()
        nom = activite.nom
        activite.delete()
        messages.success(request, f"Activité « {nom} » supprimée ({nb} participant(s) retiré(s)).")
        return redirect('viescolaire:activite_list')
    return render(request, 'viescolaire/activite_confirm_delete.html', {'activite': activite})
