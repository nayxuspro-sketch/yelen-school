"""Parcours scolaire : transitions calculées et événements annotés."""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Eleve, EvenementParcours, StatutInscriptionChoices
from parametres.models import AnneeScolaire
from licences.decorators import requires_licence_feature


_TRANSITION_META = {
    'PASSAGE':           {'label': 'Passage',            'color': '#16a34a', 'icon': '↑', 'badge_class': 'badge-success'},
    'REDOUBLEMENT':      {'label': 'Redoublement',        'color': '#d97706', 'icon': '↺', 'badge_class': 'badge-warning'},
    'TRANSFERT_ENTRANT': {'label': 'Transfert entrant',   'color': '#2563eb', 'icon': '→', 'badge_class': 'badge-info'},
    'TRANSFERT_SORTANT': {'label': 'Transfert sortant',   'color': '#7c3aed', 'icon': '→', 'badge_class': 'badge-purple'},
    'ABANDON':           {'label': 'Abandon',             'color': '#dc2626', 'icon': '✕', 'badge_class': 'badge-danger'},
    'DIPLOME':           {'label': 'Diplôme',             'color': '#0891b2', 'icon': '✓', 'badge_class': 'badge-info'},
    'AUTRE':             {'label': 'Événement',           'color': '#6b7280', 'icon': '•', 'badge_class': 'badge-neutral'},
}


def _calculer_transition(insc_courante, insc_suivante):
    """
    Déduit automatiquement le type de transition entre deux inscriptions.
    insc_courante = fin d'une année, insc_suivante = début de l'année d'après.
    """
    if insc_courante.statut == StatutInscriptionChoices.ABANDON:
        return 'ABANDON'
    if insc_suivante is None:
        return None  # Dernière inscription connue — pas encore de suite
    if insc_suivante.est_redoublant:
        return 'REDOUBLEMENT'
    # Même classe → redoublement (même si flag non coché)
    if insc_courante.classe_id == insc_suivante.classe_id:
        return 'REDOUBLEMENT'
    return 'PASSAGE'


@login_required
@requires_licence_feature('cursus_scolaire')
def eleve_parcours(request, pk):
    """
    Timeline chronologique du parcours scolaire d'un élève.

    Reconstruit les transitions depuis les Inscription existantes et
    les enrichit avec les EvenementParcours manuels.
    """
    eleve = get_object_or_404(Eleve, pk=pk)

    # Toutes les inscriptions par ordre chronologique
    inscriptions = list(
        eleve.inscriptions
        .select_related('annee_scolaire', 'classe__cycle', 'statut_eleve')
        .order_by('annee_scolaire__date_debut')
    )

    # Événements manuels indexés par annee_scolaire_id
    evenements_qs = (
        EvenementParcours.objects
        .filter(eleve=eleve)
        .select_related('annee_scolaire', 'enregistre_par')
        .order_by('annee_scolaire__date_debut', 'date_evenement')
    )
    evenements_par_annee = {}
    for ev in evenements_qs:
        evenements_par_annee.setdefault(ev.annee_scolaire_id, []).append(ev)

    # Construction de la timeline
    timeline = []
    for i, insc in enumerate(inscriptions):
        insc_suivante = inscriptions[i + 1] if i + 1 < len(inscriptions) else None

        # Transition calculée automatiquement
        type_auto = _calculer_transition(insc, insc_suivante)

        # Événements manuels pour cette année
        ev_annee = evenements_par_annee.get(insc.annee_scolaire_id, [])

        # Événement manuel qui surcharge la transition auto (transfert_sortant, diplome…)
        ev_transition = next(
            (e for e in ev_annee if e.type_evenement in (
                'TRANSFERT_SORTANT', 'DIPLOME', 'ABANDON', 'AUTRE'
            )),
            None
        )

        transition = ev_transition.type_evenement if ev_transition else type_auto
        meta = _TRANSITION_META.get(transition, _TRANSITION_META['AUTRE']) if transition else None

        # Badges de statut de l'inscription
        badges = []
        if insc.est_redoublant:
            badges.append({'label': 'Redoublant', 'badge_class': 'badge-redoublant'})
        if insc.statut == StatutInscriptionChoices.ABANDON:
            badges.append({'label': 'Abandon', 'badge_class': 'badge-danger'})
        if insc.statut == 'BOURSIER':
            badges.append({'label': 'Boursier', 'badge_class': 'badge-boursier'})
        if insc.est_exonere:
            badges.append({'label': 'Exonéré', 'badge_class': 'badge-exonere'})

        timeline.append({
            'inscription': insc,
            'badges': badges,
            'evenements': ev_annee,
            'transition': transition,
            'transition_meta': meta,
            'ev_transition': ev_transition,
            'est_derniere': insc_suivante is None,
        })

    # Formulaire d'ajout d'événement manuel (POST)
    annees = AnneeScolaire.objects.order_by('-libelle')
    if request.method == 'POST':
        type_ev = request.POST.get('type_evenement', '').strip()
        annee_id = request.POST.get('annee_scolaire', '').strip()
        motif = request.POST.get('motif', '').strip()
        etab_transfert = request.POST.get('etablissement_transfert', '').strip()
        date_ev = request.POST.get('date_evenement', '').strip()

        annee_ev = AnneeScolaire.objects.filter(pk=annee_id).first() if annee_id else None
        if type_ev and annee_ev:
            from datetime import date as _date
            EvenementParcours.objects.create(
                eleve=eleve,
                type_evenement=type_ev,
                annee_scolaire=annee_ev,
                motif=motif,
                etablissement_transfert=etab_transfert,
                date_evenement=date_ev or _date.today(),
                enregistre_par=request.user,
            )
            messages.success(request, "Événement enregistré.")
        else:
            messages.error(request, "Type d'événement et année scolaire requis.")
        return redirect('inscriptions:eleve_parcours', pk=eleve.pk)

    return render(request, 'inscriptions/eleve_parcours.html', {
        'eleve': eleve,
        'timeline': timeline,
        'annees': annees,
        'types_evenement': EvenementParcours.TypeEvenement.choices,
        'nb_annees': len(inscriptions),
        'nb_redoublements': sum(1 for e in timeline if e['transition'] == 'REDOUBLEMENT'),
    })


@login_required
@requires_licence_feature('cursus_scolaire')
def evenement_parcours_supprimer(request, pk):
    """Supprime un événement de parcours."""
    ev = get_object_or_404(EvenementParcours, pk=pk)
    eleve_pk = ev.eleve.pk
    if request.method == 'POST':
        ev.delete()
        messages.success(request, "Événement supprimé.")
    return redirect('inscriptions:eleve_parcours', pk=eleve_pk)
