"""Conseils de classe, procès-verbaux et appels de décision."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string

from django.contrib import messages

from parametres.models import AnneeScolaire, Classe
from pedagogie.models import Trimestre, MoyenneGenerale
from inscriptions.models import Inscription, StatutInscriptionChoices
from core.utils import get_etablissement_context
from ..models import (
    ConseilClasse, DecisionConseil, AppelDecision,
)
from .commun import WeasyHTML


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
        ).exclude(statut=StatutInscriptionChoices.ABANDON).select_related('eleve')
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


@login_required
def conseil_pv_pdf(request, conseil_id):
    """Génère le PV du conseil de classe en PDF."""
    if WeasyHTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur ce serveur.")
        return redirect('viescolaire:conseil_detail', conseil_id=conseil_id)
    conseil = get_object_or_404(
        ConseilClasse.objects.select_related('classe', 'trimestre', 'president'),
        pk=conseil_id
    )
    decisions = conseil.decisions.select_related(
        'inscription__eleve'
    ).order_by('inscription__eleve__nom', 'inscription__eleve__prenom')

    # Moyennes générales pour affichage dans le PV
    mg_par_ins = {
        mg.inscription_id: mg
        for mg in MoyenneGenerale.objects.filter(
            trimestre=conseil.trimestre,
            inscription__in=[d.inscription for d in decisions]
        )
    }

    # Enrichir chaque décision avec la moyenne
    lignes = []
    for d in decisions:
        lignes.append({
            'decision': d,
            'mg': mg_par_ins.get(d.inscription_id),
        })

    # Statistiques récapitulatives
    stats_decisions = {}
    for val, label in DecisionConseil.DecisionChoices.choices:
        stats_decisions[val] = {
            'label': label,
            'count': sum(1 for d in decisions if d.decision == val),
        }
    nb_felicitations = sum(1 for d in decisions if d.felicitations)
    nb_encouragements = sum(1 for d in decisions if d.encouragements)
    nb_mentions = sum(1 for d in decisions if d.mention_honneur)

    etab = getattr(request.user, 'etablissement', None)
    etab_ctx = get_etablissement_context(etab, request=request)

    html_string = render_to_string('viescolaire/pdf/conseil_pv.html', {
        'conseil': conseil,
        'classe': conseil.classe,
        'lignes': lignes,
        'stats_decisions': stats_decisions,
        'nb_felicitations': nb_felicitations,
        'nb_encouragements': nb_encouragements,
        'nb_mentions': nb_mentions,
        'nb_total': len(lignes),
        **etab_ctx,
    })

    pdf = WeasyHTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    nom_fichier = (
        f"PV_conseil_{conseil.classe.nom}_{conseil.trimestre.nom}"
        .replace(' ', '_').replace('/', '-') + '.pdf'
    )
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom_fichier}"'
    return response


# ─── Appels de décision ────────────────────────────────────────────────────────

@login_required
def appel_decision_list(request):
    """Liste de tous les appels de décision de l'établissement."""
    etab = request.user.etablissement
    if not etab:
        return redirect('viescolaire:conseil_list')

    qs = (
        AppelDecision.objects
        .filter(decision_conseil__conseil__classe__etablissement=etab)
        .select_related(
            'decision_conseil__inscription__eleve',
            'decision_conseil__conseil__classe',
            'decision_conseil__conseil__trimestre',
            'depose_par',
            'traite_par',
        )
        .order_by('-date_depot')
    )

    statut_filter = request.GET.get('statut', '')
    if statut_filter:
        qs = qs.filter(statut=statut_filter)

    return render(request, 'viescolaire/appel_decision_list.html', {
        'appels': qs,
        'statut_filter': statut_filter,
        'statut_choices': AppelDecision.StatutChoices.choices,
        'nb_en_attente': qs.filter(statut=AppelDecision.StatutChoices.EN_ATTENTE).count(),
    })


@login_required
def appel_decision_create(request, decision_id):
    """Déposer un appel contre une décision de conseil de classe."""
    etab = request.user.etablissement
    decision = get_object_or_404(
        DecisionConseil,
        pk=decision_id,
        conseil__classe__etablissement=etab,
    )

    # Une décision ne peut être contestée qu'une seule fois
    if hasattr(decision, 'appel'):
        messages.warning(request, "Cette décision a déjà fait l'objet d'un appel.")
        return redirect('viescolaire:conseil_detail', conseil_id=decision.conseil_id)

    # Seules certaines décisions sont contestables
    contestables = [
        DecisionConseil.DecisionChoices.REDOUBLEMENT,
        DecisionConseil.DecisionChoices.ORIENTATION,
        DecisionConseil.DecisionChoices.EXCLUSION,
    ]
    if decision.decision not in contestables:
        messages.error(request, "Cette décision ne peut pas être contestée.")
        return redirect('viescolaire:conseil_detail', conseil_id=decision.conseil_id)

    if request.method == 'POST':
        motif      = request.POST.get('motif', '').strip()
        date_depot = request.POST.get('date_depot', '')
        if not motif:
            messages.error(request, "Le motif de contestation est obligatoire.")
        else:
            import datetime
            try:
                date_obj = datetime.date.fromisoformat(date_depot) if date_depot else datetime.date.today()
            except ValueError:
                date_obj = datetime.date.today()

            AppelDecision.objects.create(
                decision_conseil=decision,
                motif=motif,
                date_depot=date_obj,
                depose_par=request.user,
                statut=AppelDecision.StatutChoices.EN_ATTENTE,
            )
            messages.success(request, "Appel enregistré — la commission sera saisie.")
            return redirect('viescolaire:conseil_detail', conseil_id=decision.conseil_id)

    import datetime
    return render(request, 'viescolaire/appel_decision_form.html', {
        'decision': decision,
        'today': datetime.date.today().isoformat(),
    })


@login_required
def appel_decision_traiter(request, appel_id):
    """Instruire et clôturer un appel de décision."""
    etab = request.user.etablissement
    appel = get_object_or_404(
        AppelDecision,
        pk=appel_id,
        decision_conseil__conseil__classe__etablissement=etab,
    )

    if appel.est_traite:
        messages.info(request, "Cet appel est déjà traité.")
        return redirect('viescolaire:appel_decision_list')

    if request.method == 'POST':
        issue                  = request.POST.get('issue', '')
        nouvelle_decision      = request.POST.get('nouvelle_decision', '') or None
        observations           = request.POST.get('observations_commission', '').strip()
        statut_form            = request.POST.get('statut', AppelDecision.StatutChoices.EN_INSTRUCTION)

        if not issue and statut_form == AppelDecision.StatutChoices.TRAITE:
            messages.error(request, "L'issue est obligatoire pour clôturer l'appel.")
        else:
            import datetime
            appel.statut                 = statut_form
            appel.observations_commission = observations
            if issue:
                appel.issue = issue
            if issue == AppelDecision.IssueChoices.MODIFIE and nouvelle_decision:
                appel.nouvelle_decision = nouvelle_decision
                # Mettre à jour la décision effective si modifiée
                appel.decision_conseil.decision = nouvelle_decision
                appel.decision_conseil.save(update_fields=['decision'])
            if statut_form == AppelDecision.StatutChoices.TRAITE:
                appel.traite_par      = request.user
                appel.date_traitement = datetime.date.today()
            appel.save()
            messages.success(request, "Appel mis à jour.")
            return redirect('viescolaire:appel_decision_list')

    return render(request, 'viescolaire/appel_decision_traiter.html', {
        'appel': appel,
        'issue_choices': AppelDecision.IssueChoices.choices,
        'decision_choices': DecisionConseil.DecisionChoices.choices,
        'statut_choices': AppelDecision.StatutChoices.choices,
    })
