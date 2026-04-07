"""
Module Vie Scolaire - Views
============================
YELEN SCHOOL v3.5
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from parametres.models import AnneeScolaire, Classe, TypeSanction
from pedagogie.models import Trimestre
from inscriptions.models import Inscription
from .models import (
    ConseilClasse, DecisionConseil,
    SanctionDisciplinaire,
    ActiviteParascolaire, ParticipationActivite,
)


# ─── Conseils de classe ───────────────────────────────────────────────────────

@login_required
def conseil_list(request):
    """Liste des conseils de classe (tous trimestres)."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    trimestres = Trimestre.objects.filter(annee_scolaire=annee_courante).order_by('numero') if annee_courante else []

    trimestre_id = request.GET.get('trimestre')
    trimestre_selectionne = None
    if trimestre_id:
        trimestre_selectionne = Trimestre.objects.filter(pk=trimestre_id).first()

    conseils = ConseilClasse.objects.select_related(
        'classe', 'trimestre', 'president'
    ).order_by('date_conseil')
    if trimestre_selectionne:
        conseils = conseils.filter(trimestre=trimestre_selectionne)
    elif annee_courante:
        conseils = conseils.filter(trimestre__annee_scolaire=annee_courante)

    return render(request, 'viescolaire/conseil_list.html', {
        'conseils': conseils,
        'trimestres': trimestres,
        'trimestre_selectionne': trimestre_selectionne,
        'annee_courante': annee_courante,
    })


@login_required
def conseil_detail(request, conseil_id):
    """Détail d'un conseil + décisions individuelles."""
    conseil = get_object_or_404(
        ConseilClasse.objects.select_related('classe', 'trimestre', 'president'),
        pk=conseil_id
    )
    decisions = conseil.decisions.select_related(
        'inscription__eleve'
    ).order_by('inscription__eleve__nom')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'mark_tenu':
            conseil.tenu = True
            conseil.save(update_fields=['tenu'])
            messages.success(request, "Conseil marqué comme tenu.")

        elif action == 'save_decisions':
            for decision in decisions:
                key_decision = f'decision_{decision.pk}'
                key_appreciation = f'appreciation_{decision.pk}'
                key_mention = f'mention_{decision.pk}'
                key_encouragements = f'encouragements_{decision.pk}'
                key_felicitations = f'felicitations_{decision.pk}'
                if key_decision in request.POST:
                    decision.decision = request.POST[key_decision]
                    decision.appreciation = request.POST.get(key_appreciation, '')
                    decision.mention_honneur = key_mention in request.POST
                    decision.encouragements = key_encouragements in request.POST
                    decision.felicitations = key_felicitations in request.POST
                    decision.save(update_fields=[
                        'decision', 'appreciation',
                        'mention_honneur', 'encouragements', 'felicitations'
                    ])
            messages.success(request, "Décisions enregistrées.")

        return redirect('viescolaire:conseil_detail', conseil_id=conseil.pk)

    return render(request, 'viescolaire/conseil_detail.html', {
        'conseil': conseil,
        'decisions': decisions,
        'decision_choices': DecisionConseil.DecisionChoices.choices,
    })


@login_required
def conseil_create(request):
    """Créer un conseil de classe pour une classe/trimestre."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    classes = Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')
    trimestres = Trimestre.objects.filter(annee_scolaire=annee_courante).order_by('numero') if annee_courante else []

    if request.method == 'POST':
        classe_id = request.POST.get('classe')
        trimestre_id = request.POST.get('trimestre')
        date_conseil = request.POST.get('date_conseil')
        president_id = request.POST.get('president') or None

        classe = get_object_or_404(Classe, pk=classe_id)
        trimestre = get_object_or_404(Trimestre, pk=trimestre_id)

        conseil, created = ConseilClasse.objects.get_or_create(
            classe=classe,
            trimestre=trimestre,
            defaults={
                'date_conseil': date_conseil,
                'president_id': president_id,
            }
        )
        if not created:
            messages.warning(request, "Un conseil existe déjà pour cette classe et ce trimestre.")
            return redirect('viescolaire:conseil_detail', conseil_id=conseil.pk)

        # Créer les décisions pour tous les élèves de la classe
        inscriptions = Inscription.objects.filter(
            classe=classe, annee_scolaire=trimestre.annee_scolaire
        ).exclude(statut='ABANDON').select_related('eleve')
        DecisionConseil.objects.bulk_create([
            DecisionConseil(conseil=conseil, inscription=ins)
            for ins in inscriptions
        ], ignore_conflicts=True)

        messages.success(request, f"Conseil créé pour {classe} — {trimestre} ({inscriptions.count()} élèves).")
        return redirect('viescolaire:conseil_detail', conseil_id=conseil.pk)

    return render(request, 'viescolaire/conseil_create.html', {
        'classes': classes,
        'trimestres': trimestres,
    })


# ─── Sanctions disciplinaires ─────────────────────────────────────────────────

@login_required
def sanction_list(request):
    """Liste des sanctions disciplinaires, regroupées par classe."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    qs = SanctionDisciplinaire.objects.select_related(
        'inscription__eleve', 'inscription__classe__cycle', 'prononcee_par', 'trimestre', 'type_sanction'
    ).order_by('inscription__classe__cycle__ordre', 'inscription__classe__nom', '-date_sanction')
    if annee_courante:
        qs = qs.filter(inscription__annee_scolaire=annee_courante)

    type_filtre = request.GET.get('type')
    if type_filtre:
        qs = qs.filter(type_sanction_id=type_filtre)

    # Regroupement par classe
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
        'annee_courante': annee_courante,
        'types_sanction': types_sanction,
        'type_filtre': type_filtre,
    })


@login_required
def sanction_create(request):
    """Enregistrer une nouvelle sanction disciplinaire."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    classes = Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')
    trimestres = Trimestre.objects.filter(
        annee_scolaire=annee_courante
    ).order_by('numero') if annee_courante else []

    if request.method == 'POST':
        inscription_id = request.POST.get('inscription')
        inscription = get_object_or_404(Inscription, pk=inscription_id)
        trimestre_id = request.POST.get('trimestre') or None
        trimestre = Trimestre.objects.filter(pk=trimestre_id).first() if trimestre_id else None
        points_raw = request.POST.get('points', '0').strip() or '0'

        type_sanction = get_object_or_404(TypeSanction, pk=request.POST['type_sanction'])

        sanction = SanctionDisciplinaire.objects.create(
            inscription=inscription,
            type_sanction=type_sanction,
            date_sanction=request.POST['date_sanction'],
            motif=request.POST['motif'],
            duree_jours=request.POST.get('duree_jours') or 0,
            date_retour=request.POST.get('date_retour') or None,
            prononcee_par=request.user,
            statut=request.POST.get('statut', SanctionDisciplinaire.StatutChoices.EN_COURS),
            observations=request.POST.get('observations', ''),
            parents_convoques='parents_convoques' in request.POST,
            date_convocation=request.POST.get('date_convocation') or None,
            trimestre=trimestre,
            points=points_raw,
            appreciation_conduite=request.POST.get('appreciation_conduite', ''),
        )

        # Recalculer la moyenne si des points sont appliqués et le trimestre est défini
        if sanction.a_impact_points:
            from pedagogie.utils import CalculateurMoyenne
            CalculateurMoyenne.calculer_moyenne_generale(inscription, trimestre)
            CalculateurMoyenne.calculer_rangs(inscription.classe, trimestre)
            messages.success(request, f"Sanction enregistrée — {float(sanction.points):+g} pts appliqués au trimestre {trimestre}.")
        else:
            messages.success(request, "Sanction enregistrée.")

        return redirect('viescolaire:sanction_list')

    classe_id = request.GET.get('classe')
    inscriptions = []
    if classe_id and annee_courante:
        inscriptions = Inscription.objects.filter(
            classe_id=classe_id, annee_scolaire=annee_courante
        ).exclude(statut='ABANDON').select_related('eleve').order_by('eleve__nom')

    return render(request, 'viescolaire/sanction_create.html', {
        'classes': classes,
        'inscriptions': inscriptions,
        'trimestres': trimestres,
        'types_sanction': TypeSanction.objects.filter(actif=True).order_by('libelle'),
        'statut_choices': SanctionDisciplinaire.StatutChoices.choices,
        'classe_id': classe_id,
        'annee_courante': annee_courante,
    })


@login_required
def sanction_delete(request, sanction_id):
    """Supprime une sanction disciplinaire (POST uniquement)."""
    sanction = get_object_or_404(SanctionDisciplinaire, pk=sanction_id)

    if request.method != 'POST':
        return redirect('viescolaire:sanction_list')

    # Si la sanction avait un impact sur la moyenne, recalculer après suppression
    avait_impact = sanction.a_impact_points
    inscription = sanction.inscription
    trimestre = sanction.trimestre

    sanction.delete()

    if avait_impact:
        from pedagogie.utils import CalculateurMoyenne
        CalculateurMoyenne.calculer_moyenne_generale(inscription, trimestre)
        CalculateurMoyenne.calculer_rangs(inscription.classe, trimestre)

    messages.success(request, "Sanction supprimée.")
    return redirect('viescolaire:sanction_list')


# ─── Activités parascolaires ──────────────────────────────────────────────────

@login_required
def activite_list(request):
    """Liste des activités parascolaires."""
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    activites = ActiviteParascolaire.objects.select_related(
        'annee_scolaire', 'responsable'
    ).prefetch_related('participations').order_by('type_activite', 'nom')
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
    ).exclude(pk__in=inscrits_ids).exclude(statut='ABANDON').select_related('eleve', 'classe').order_by('eleve__nom')

    return render(request, 'viescolaire/activite_detail.html', {
        'activite': activite,
        'participations': participations,
        'inscriptions_dispo': inscriptions_dispo,
    })
