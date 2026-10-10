"""Compétences : référentiel, saisie, bulletin.

Issu du découpage mécanique de ``pedagogie/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from ..models import Matiere, Trimestre, Competence, EvaluationCompetence
from parametres.models import AnneeScolaire, Classe, Cycle
from inscriptions.models import Inscription
from core.utils import get_etablissement_context
from .commun import HTML, _pdf_licence_info


@login_required
def competences_index(request):
    """Sélecteur de cycle pour les bulletins de compétences."""
    from etablissements.models import Etablissement
    etab = Etablissement.objects.first()
    # Seuls les cycles Préscolaire et Primaire utilisent les compétences
    cycles_cibles = ['PRES', 'PRIM']
    cycles = (
        Cycle.objects.filter(etablissement=etab, code__in=cycles_cibles)
        .order_by('ordre')
    ) if etab else Cycle.objects.none()
    return render(request, 'pedagogie/competences_index.html', {
        'cycles': cycles,
        'etablissement': etab,
    })


@login_required
def competences_referentiel(request, cycle_id):
    """Référentiel de compétences pour un cycle donné (lecture + ajout HTMX)."""
    from etablissements.models import Etablissement
    etab = Etablissement.objects.first()
    cycle = get_object_or_404(Cycle, pk=cycle_id)
    competences = (
        Competence.objects.filter(cycle=cycle, actif=True)
        .select_related('matiere')
        .order_by('matiere__code', 'ordre', 'libelle')
    )
    matieres = Matiere.objects.filter(
        configurations_cycle__cycle=cycle
    ).order_by('code').distinct()

    categories = {
        k: str(v) for k, v in Competence.CategorieChoices.choices
    }

    if request.method == 'POST':
        libelle = request.POST.get('libelle', '').strip()
        matiere_id = request.POST.get('matiere') or None
        ordre = int(request.POST.get('ordre', 0) or 0)
        categorie = request.POST.get('categorie', Competence.CategorieChoices.SAVOIRS_ACAD)
        if libelle:
            matiere = Matiere.objects.filter(pk=matiere_id).first() if matiere_id else None
            Competence.objects.create(
                cycle=cycle,
                matiere=matiere,
                libelle=libelle,
                ordre=ordre,
                categorie=categorie,
            )
            messages.success(request, "Compétence ajoutée.")
        return redirect('pedagogie:competences_referentiel', cycle_id=cycle_id)

    return render(request, 'pedagogie/competences_referentiel.html', {
        'cycle': cycle,
        'competences': competences,
        'matieres': matieres,
        'categories': categories,
        'etablissement': etab,
    })


@login_required
@require_POST
def competence_supprimer(request, pk):
    """Supprime (désactive) une compétence."""
    comp = get_object_or_404(Competence, pk=pk)
    comp.actif = False
    comp.save(update_fields=['actif'])
    messages.success(request, f"Compétence supprimée : {comp.libelle}")
    return redirect('pedagogie:competences_referentiel', cycle_id=comp.cycle_id)


@login_required
def competences_saisie(request, classe_id):
    """Saisie des niveaux de compétences pour une classe et un trimestre."""
    from etablissements.models import Etablissement
    etab = Etablissement.objects.first()
    classe = get_object_or_404(Classe, pk=classe_id)
    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    trimestres = Trimestre.objects.filter(annee_scolaire=annee).order_by('numero') if annee else Trimestre.objects.none()
    trimestre_id = request.GET.get('trimestre') or request.POST.get('trimestre')
    trimestre = Trimestre.objects.filter(pk=trimestre_id).first() if trimestre_id else trimestres.first()

    inscriptions = (
        Inscription.objects.filter(classe=classe, annee_scolaire=annee)
        .select_related('eleve')
        .exclude(statut='ABANDON')
        .order_by('eleve__nom', 'eleve__prenom')
    ) if annee else Inscription.objects.none()

    competences = (
        Competence.objects.filter(cycle=classe.cycle, actif=True)
        .select_related('matiere')
        .order_by('matiere__code', 'ordre')
    ) if classe.cycle_id else Competence.objects.none()

    if request.method == 'POST' and trimestre:
        niveaux_choices = EvaluationCompetence.NiveauChoices.values
        for ins in inscriptions:
            for comp in competences:
                key = f"niveau_{ins.pk}_{comp.pk}"
                niveau = request.POST.get(key, EvaluationCompetence.NiveauChoices.NON_EVALUE)
                if niveau not in niveaux_choices:
                    niveau = EvaluationCompetence.NiveauChoices.NON_EVALUE
                obs_key = f"obs_{ins.pk}_{comp.pk}"
                obs = request.POST.get(obs_key, '').strip()[:200]
                EvaluationCompetence.objects.update_or_create(
                    inscription=ins,
                    competence=comp,
                    trimestre=trimestre,
                    defaults={'niveau': niveau, 'observation': obs},
                )
        messages.success(request, "Évaluations enregistrées.")
        return redirect(f"{request.path}?trimestre={trimestre.pk}")

    # Construire grille : {inscription_id: {competence_id: EvaluationCompetence}}
    evals_qs = EvaluationCompetence.objects.filter(
        inscription__in=inscriptions,
        competence__in=competences,
        trimestre=trimestre,
    ) if trimestre else EvaluationCompetence.objects.none()
    grille = {}
    for ev in evals_qs:
        grille.setdefault(str(ev.inscription_id), {})[str(ev.competence_id)] = ev

    # Grille JSON pour le JS de pré-sélection : {ins_id: {comp_id: niveau}}
    import json as _json
    grille_json = _json.dumps({
        ins_id: {comp_id: ev.niveau for comp_id, ev in comps.items()}
        for ins_id, comps in grille.items()
    })

    return render(request, 'pedagogie/competences_saisie.html', {
        'classe': classe,
        'annee': annee,
        'trimestre': trimestre,
        'trimestres': trimestres,
        'inscriptions': inscriptions,
        'competences': competences,
        'grille': grille,
        'grille_json': grille_json,
        'niveaux': EvaluationCompetence.NiveauChoices,
        'etablissement': etab,
    })


@login_required
@require_POST
def competence_sauvegarder(request):
    """Sauvegarde HTMX individuelle d'une évaluation de compétence."""
    ins_id = request.POST.get('inscription')
    comp_id = request.POST.get('competence')
    trim_id = request.POST.get('trimestre')
    niveau = request.POST.get('niveau', EvaluationCompetence.NiveauChoices.NON_EVALUE)

    niveaux_vals = [v for v, _ in EvaluationCompetence.NiveauChoices.choices]
    if niveau not in niveaux_vals:
        niveau = EvaluationCompetence.NiveauChoices.NON_EVALUE

    ins = get_object_or_404(Inscription, pk=ins_id)
    comp = get_object_or_404(Competence, pk=comp_id)
    trim = get_object_or_404(Trimestre, pk=trim_id)

    EvaluationCompetence.objects.update_or_create(
        inscription=ins,
        competence=comp,
        trimestre=trim,
        defaults={'niveau': niveau},
    )

    competences = (
        Competence.objects.filter(cycle=ins.classe.cycle, actif=True)
        .select_related('matiere')
        .order_by('matiere__code', 'categorie', 'ordre')
    )
    evals_qs = EvaluationCompetence.objects.filter(
        inscription=ins, competence__in=competences, trimestre=trim
    )
    grille = {}
    for ev in evals_qs:
        grille.setdefault(str(ev.inscription_id), {})[str(ev.competence_id)] = ev

    return render(request, 'pedagogie/partials/competence_eleve_card.html', {
        'ins': ins,
        'competences': competences,
        'grille': grille,
        'trimestre': trim,
    })


@login_required
def competences_bulletin_pdf(request, inscription_id, trimestre_id):
    """Bulletin de compétences PDF pour un élève à un trimestre."""
    if HTML is None:
        messages.error(request, "WeasyPrint n'est pas disponible.")
        return redirect('pedagogie:competences_index')

    from etablissements.models import Etablissement
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe__cycle'),
        pk=inscription_id,
    )
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id)
    etab = Etablissement.objects.first()
    etab_ctx = get_etablissement_context(etab, request) if etab else {}

    competences = (
        Competence.objects.filter(cycle=inscription.classe.cycle, actif=True)
        .select_related('matiere')
        .order_by('matiere__code', 'ordre')
    )
    evals_qs = EvaluationCompetence.objects.filter(
        inscription=inscription,
        competence__in=competences,
        trimestre=trimestre,
    ).select_related('competence__matiere')
    evals_map = {str(ev.competence_id): ev for ev in evals_qs}

    # Regrouper par matière
    from collections import defaultdict
    groupes = defaultdict(list)
    for comp in competences:
        ev = evals_map.get(str(comp.pk))
        groupes[comp.matiere].append({'competence': comp, 'evaluation': ev})
    groupes_list = [(mat, items) for mat, items in groupes.items()]

    html_str = render_to_string('pedagogie/competences_bulletin_pdf.html', {
        'inscription': inscription,
        'trimestre': trimestre,
        'groupes': groupes_list,
        'etablissement': etab,
        'identite': etab_ctx.get('identite'),
        'licence_info': _pdf_licence_info(request, etab),
    }, request=request)

    pdf = HTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()
    eleve = inscription.eleve
    nom = f"Bulletin_{eleve.nom}_{eleve.prenom}_{trimestre.numero}.pdf".replace(' ', '_')
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{nom}"'
    return resp
