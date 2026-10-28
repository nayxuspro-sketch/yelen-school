"""Sanctions disciplinaires."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.notifications import notifier_sanction
from parametres.models import AnneeScolaire, Classe, TypeSanction
from pedagogie.models import Trimestre
from inscriptions.models import Inscription, StatutInscriptionChoices
from parametres.droits import autorise_url
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

    # Filtrer les classes par établissement de l'utilisateur
    etab = request.user.etablissement
    if etab:
        classes = Classe.objects.filter(etablissement=etab).select_related('cycle').order_by('cycle__ordre', 'nom')
    else:
        classes = Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')

    trimestres = Trimestre.objects.filter(
        annee_scolaire=annee_courante
    ).order_by('numero') if annee_courante else []

    if request.method == 'POST':
        inscription_id = request.POST.get('inscription')
        inscription = get_object_or_404(Inscription, pk=inscription_id)

        # IDOR - Vérifier que l'inscription appartient à l'établissement de l'utilisateur
        if etab and inscription.classe.etablissement != etab:
            messages.error(request, "Vous n'avez pas accès à cet élève.")
            return redirect('viescolaire:sanction_create')

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

        if 'prevenir_parents' in request.POST:
            if notifier_sanction(sanction):
                sanction.parents_notifies_le = timezone.now()
                sanction.save(update_fields=['parents_notifies_le'])
                messages.info(request, "Parent informé (notification du portail et SMS si activé).")
            else:
                messages.warning(request, "Parent non informé : aucun compte parent lié et aucun numéro de téléphone (ou SMS désactivés).")

        # Recalculer la moyenne si des points sont appliqués et le trimestre est défini
        if sanction.a_impact_points:
            from pedagogie.utils import CalculateurMoyenne
            CalculateurMoyenne.calculer_moyenne_generale(inscription, trimestre)
            CalculateurMoyenne.calculer_rangs(inscription.classe, trimestre)
            messages.success(
                request,
                f"Sanction enregistrée — {float(sanction.points):+g} pts appliqués au trimestre {trimestre}.",
            )
        else:
            messages.success(request, "Sanction enregistrée.")

        return redirect('viescolaire:sanction_list')

    classe_id = request.GET.get('classe')
    inscriptions = []
    if classe_id and annee_courante:
        inscriptions = Inscription.objects.filter(
            classe_id=classe_id, annee_scolaire=annee_courante
        ).exclude(statut=StatutInscriptionChoices.ABANDON).select_related('eleve').order_by('eleve__nom')

    import json
    types_qs = TypeSanction.objects.filter(actif=True).order_by('libelle')
    types_sanction_json = json.dumps({
        str(t.pk): str(t.points_defaut) for t in types_qs
    })
    etab = getattr(request.user, 'etablissement', None)
    config_disc = ConfigDiscipline.get_or_default(etab) if etab else None

    return render(request, 'viescolaire/sanction_create.html', {
        'classes': classes,
        'inscriptions': inscriptions,
        'trimestres': trimestres,
        'types_sanction': types_qs,
        'types_sanction_json': types_sanction_json,
        'statut_choices': SanctionDisciplinaire.StatutChoices.choices,
        'classe_id': classe_id,
        'annee_courante': annee_courante,
        'config_disc': config_disc,
    })


@login_required
@require_POST
def sanction_delete(request, sanction_id):
    """Supprime une sanction disciplinaire (POST uniquement)."""
    sanction = get_object_or_404(SanctionDisciplinaire, pk=sanction_id)

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
