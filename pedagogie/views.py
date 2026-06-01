import json
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)
from .models import Matiere, MatiereCycle, Enseignement, Evaluation, Note, Resultat, MoyenneGenerale, Trimestre, RisqueDecrochage, CahierTextes, PredictionReussiteExamen, Competence, EvaluationCompetence
from .forms import MatiereForm, MatiereCycleForm, EnseignementForm, EvaluationForm
from .utils import CalculateurMoyenne
from parametres.models import AnneeScolaire, Classe, Cycle
from inscriptions.models import Inscription
from core.utils import get_etablissement_context

try:
    from weasyprint import HTML
except ImportError:
    HTML = None

@login_required
def classe_result_list(request):
    """Liste des classes pour accéder aux résultats."""
    from django.db.models import Count, OuterRef, Subquery
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    classes = (
        Classe.objects
        .select_related('cycle')
        .order_by('cycle__ordre', 'nom')
    )
    if annee_courante:
        nb_sub = (
            Inscription.objects
            .filter(classe=OuterRef('pk'), annee_scolaire=annee_courante)
            .exclude(statut='ABANDON')
            .values('classe')
            .annotate(n=Count('pk'))
            .values('n')
        )
        classes = classes.annotate(nb_eleves=Subquery(nb_sub))

    return render(request, 'pedagogie/classe_result_list.html', {
        'classes': classes,
        'annee_courante': annee_courante,
    })


@login_required
def bilan_periodes(request):
    """
    Bilan par période (trimestre) × classe × année scolaire.
    Affiche : effectif, moyenne classe, plus haute/faible moyenne,
    nb admis, taux de réussite.
    """
    from django.db.models import Avg, Max, Min, Count, Q as _Q

    annees = AnneeScolaire.objects.order_by('-date_debut')
    annee_id = request.GET.get('annee')
    annee = annees.filter(pk=annee_id).first() if annee_id else None
    if not annee:
        annee = annees.filter(est_courante=True).first() or annees.first()

    trimestres = list(
        Trimestre.objects.filter(annee_scolaire=annee).order_by('numero')
    ) if annee else []

    classes = list(
        Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')
    )

    # Une seule requête pour toutes les stats (classe × trimestre)
    mg_stats = (
        MoyenneGenerale.objects
        .filter(trimestre__in=trimestres, inscription__annee_scolaire=annee)
        .values('trimestre_id', 'inscription__classe_id')
        .annotate(
            nb_eleves=Count('id'),
            moy_classe=Avg('moyenne'),
            moy_max=Max('moyenne'),
            moy_min=Min('moyenne'),
            nb_admis=Count('id', filter=_Q(moyenne__gte=10)),
        )
    )

    index = {}
    for row in mg_stats:
        key = (str(row['inscription__classe_id']), str(row['trimestre_id']))
        nb = row['nb_eleves'] or 0
        nb_admis = row['nb_admis'] or 0
        index[key] = {
            'nb_eleves': nb,
            'moy_classe': round(float(row['moy_classe']), 2) if row['moy_classe'] else None,
            'moy_max':    round(float(row['moy_max']),    2) if row['moy_max']    else None,
            'moy_min':    round(float(row['moy_min']),    2) if row['moy_min']    else None,
            'nb_admis':   nb_admis,
            'taux':       round(nb_admis / nb * 100, 1) if nb else None,
        }

    # Construire la hiérarchie : période → liste de classes avec stats
    periodes_data = []
    stats_ia = []  # liste plate pour l'appel IA (JSON sérialisé côté vue)
    for trimestre in trimestres:
        lignes = []
        for classe in classes:
            stats = index.get((str(classe.pk), str(trimestre.pk)))
            if stats:
                lignes.append({'classe': classe, 'stats': stats})
                stats_ia.append({
                    'cle':         f"{classe.pk}_{trimestre.pk}",
                    'classe_nom':  classe.nom,
                    'cycle_nom':   classe.cycle.nom,
                    'periode_nom': trimestre.nom,
                    'nb_eleves':   stats['nb_eleves'],
                    'moy_classe':  stats['moy_classe'],
                    'moy_max':     stats['moy_max'],
                    'moy_min':     stats['moy_min'],
                    'taux':        stats['taux'],
                    'nb_admis':    stats['nb_admis'],
                })
        if lignes:
            periodes_data.append({'trimestre': trimestre, 'lignes': lignes})

    import json as _json
    return render(request, 'pedagogie/bilan_periodes.html', {
        'annee':         annee,
        'annees':        annees,
        'periodes_data': periodes_data,
        'stats_ia_json': _json.dumps(stats_ia, ensure_ascii=False),
    })


@login_required
@require_POST
def generer_commentaires_bilan(request):
    """
    Génère des commentaires pour le bilan pédagogique (mode hors ligne).
    Reçoit un JSON body : {"stats": [{cle, classe_nom, cycle_nom, ...}, ...]}
    Retourne : {"commentaires": {cle: {commentaire, recommandations}, ...}}
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'erreur': 'Corps de requête JSON invalide.'}, status=400)

    stats = data.get('stats', [])
    if not stats:
        return JsonResponse({'erreur': 'Aucune donnée de statistiques fournie.'}, status=400)

    try:
        from .utils_ia import generer_analyse_bilan
        commentaires = generer_analyse_bilan(stats)
        return JsonResponse({'commentaires': commentaires})
    except ImportError as e:
        return JsonResponse({'erreur': str(e)}, status=503)
    except ValueError as e:
        return JsonResponse({'erreur': str(e)}, status=503)
    except RuntimeError as e:
        return JsonResponse({'erreur': str(e)}, status=503)
    except Exception as e:
        logger.exception("Erreur inattendue lors de la génération des commentaires IA")
        return JsonResponse({'erreur': f"Erreur inattendue : {e}"}, status=500)


@login_required
def bilan_pdf(request):
    """
    Génère le bilan des périodes en PDF (offline).
    Paramètres GET/POST :
      - annee (uuid) : année scolaire (défaut : courante)
      - classe (uuid, optionnel) : filtre sur une seule classe
      - trimestre (uuid, optionnel) : filtre sur une seule période
    Paramètre POST optionnel :
      - commentaires (JSON str) : résultats de l'analyse IA
    """
    from django.db.models import Avg, Max, Min, Count, Q as _Q

    def _get(key):
        return request.POST.get(key) or request.GET.get(key)

    annees = AnneeScolaire.objects.order_by('-date_debut')
    annee = annees.filter(pk=_get('annee')).first() if _get('annee') else None
    if not annee:
        annee = annees.filter(est_courante=True).first() or annees.first()

    classe_id    = _get('classe')
    trimestre_id = _get('trimestre')

    # Commentaires IA (optionnel, online uniquement)
    try:
        commentaires = json.loads(request.POST.get('commentaires', '{}'))
    except (json.JSONDecodeError, ValueError):
        commentaires = {}

    # Périodes
    trimestres_qs = Trimestre.objects.filter(annee_scolaire=annee).order_by('numero')
    if trimestre_id:
        trimestres_qs = trimestres_qs.filter(pk=trimestre_id)
    trimestres = list(trimestres_qs)

    # Classes
    classes_qs = Classe.objects.select_related('cycle').order_by('cycle__ordre', 'nom')
    if classe_id:
        classes_qs = classes_qs.filter(pk=classe_id)
    classes = list(classes_qs)

    # Agrégation SQL
    mg_stats = (
        MoyenneGenerale.objects
        .filter(trimestre__in=trimestres, inscription__annee_scolaire=annee)
        .values('trimestre_id', 'inscription__classe_id')
        .annotate(
            nb_eleves=Count('id'),
            moy_classe=Avg('moyenne'),
            moy_max=Max('moyenne'),
            moy_min=Min('moyenne'),
            nb_admis=Count('id', filter=_Q(moyenne__gte=10)),
        )
    )

    index = {}
    for row in mg_stats:
        key = (str(row['inscription__classe_id']), str(row['trimestre_id']))
        nb = row['nb_eleves'] or 0
        nb_admis = row['nb_admis'] or 0
        index[key] = {
            'nb_eleves': nb,
            'moy_classe': round(float(row['moy_classe']), 2) if row['moy_classe'] else None,
            'moy_max':    round(float(row['moy_max']),    2) if row['moy_max']    else None,
            'moy_min':    round(float(row['moy_min']),    2) if row['moy_min']    else None,
            'nb_admis':   nb_admis,
            'taux':       round(nb_admis / nb * 100, 1) if nb else None,
        }

    periodes_data = []
    for trimestre in trimestres:
        lignes = []
        for classe in classes:
            stats = index.get((str(classe.pk), str(trimestre.pk)))
            if stats:
                cle = f"{classe.pk}_{trimestre.pk}"
                lignes.append({
                    'classe': classe,
                    'stats': stats,
                    'cle': cle,
                    'analyse_ia': commentaires.get(cle),
                })
        if lignes:
            periodes_data.append({'trimestre': trimestre, 'lignes': lignes})

    if HTML is None:
        return HttpResponse("WeasyPrint non disponible sur ce serveur.", status=500)

    from etablissements.models import Etablissement
    etab = Etablissement.objects.first()
    etab_ctx = get_etablissement_context(etab, request) if etab else {}
    html_string = render_to_string('pedagogie/pdf/bilan.html', {
        **etab_ctx,
        'annee':             annee,
        'periodes_data':     periodes_data,
        'avec_commentaires': bool(commentaires),
    }, request=request)

    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    label = annee.libelle.replace(' ', '_').replace('/', '-') if annee else 'bilan'
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="bilan_{label}.pdf"'
    return response


@login_required
def releve_moyenne_classe_pdf(request):
    """
    Relevé de moyenne d'une classe pour un trimestre donné, classé par ordre de mérite.
    Paramètres GET : classe (uuid), trimestre (uuid)
    """
    classe_id    = request.GET.get('classe')
    trimestre_id = request.GET.get('trimestre')

    classe    = get_object_or_404(Classe, pk=classe_id)
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id)

    # Récupérer toutes les moyennes générales de la classe pour ce trimestre
    moyennes = (
        MoyenneGenerale.objects
        .filter(
            trimestre=trimestre,
            inscription__classe=classe,
            inscription__annee_scolaire=trimestre.annee_scolaire,
        )
        .select_related('inscription__eleve')
        .order_by('-moyenne', 'inscription__eleve__nom', 'inscription__eleve__prenom')
    )

    # Attribution du rang (ex aequo = même rang)
    eleves = []
    rang = 0
    rang_affiche = 0
    prev_moy = None
    for mg in moyennes:
        rang += 1
        if mg.moyenne != prev_moy:
            rang_affiche = rang
            prev_moy = mg.moyenne
        eleves.append({
            'rang':   rang_affiche,
            'eleve':  mg.inscription.eleve,
            'moyenne': mg.moyenne,
            'appreciation': mg.appreciation,
            'admis':  bool(mg.moyenne is not None and mg.moyenne >= 10),
        })

    # Statistiques récapitulatives
    moyennes_vals = [e['moyenne'] for e in eleves if e['moyenne'] is not None]
    nb_admis = sum(1 for e in eleves if e['admis'])
    stats = {
        'nb_eleves':  len(eleves),
        'nb_admis':   nb_admis,
        'taux':       round(nb_admis / len(eleves) * 100, 1) if eleves else None,
        'moy_classe': round(sum(float(m) for m in moyennes_vals) / len(moyennes_vals), 2) if moyennes_vals else None,
        'moy_max':    round(float(max(moyennes_vals)), 2) if moyennes_vals else None,
        'moy_min':    round(float(min(moyennes_vals)), 2) if moyennes_vals else None,
    }

    if HTML is None:
        return HttpResponse("WeasyPrint non disponible sur ce serveur.", status=500)

    from etablissements.models import Etablissement
    etab = Etablissement.objects.first()
    etab_ctx = get_etablissement_context(etab, request) if etab else {}

    html_string = render_to_string('pedagogie/pdf/releve_moyenne_classe.html', {
        **etab_ctx,
        'classe':    classe,
        'trimestre': trimestre,
        'annee':     trimestre.annee_scolaire,
        'eleves':    eleves,
        'stats':     stats,
    }, request=request)

    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    nom_fichier = (
        f"releve_{classe.nom}_{trimestre.nom}"
        .replace(' ', '_').replace('/', '-')
    )
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom_fichier}.pdf"'
    return response


@login_required
def matiere_list(request):
    """Liste des matières avec filtrage HTMX."""
    query = request.GET.get('q', '')
    matieres = Matiere.objects.all()
    
    if query:
        matieres = matieres.filter(
            Q(nom__icontains=query) | 
            Q(code__icontains=query) |
            Q(nom_complet__icontains=query)
        )
    
    context = {
        'matiere_list': matieres,
        'query': query,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'pedagogie/partials/matiere_table.html', context)
        
    return render(request, 'pedagogie/matiere_list.html', context)

def _build_cycles_config(matiere):
    """Construit la liste des cycles avec leur config MatiereCycle (ou None)."""
    cycles = Cycle.objects.filter(actif=True).order_by('ordre', 'nom')
    configs = {c.cycle_id: c for c in matiere.configurations_cycle.all()} if matiere else {}
    return [
        {'cycle': cycle, 'config': configs.get(cycle.pk), 'form': MatiereCycleForm(instance=configs.get(cycle.pk))}
        for cycle in cycles
    ]


@login_required
def matiere_create(request):
    """Ajout d'une nouvelle matière."""
    if request.method == 'POST':
        form = MatiereForm(request.POST)
        if form.is_valid():
            matiere = form.save()
            messages.success(request, f"Matière {matiere.nom} créée. Configurez les coefficients par cycle.")
            return redirect('pedagogie:matiere_update', pk=matiere.pk)
    else:
        form = MatiereForm()

    return render(request, 'pedagogie/matiere_form.html', {
        'form': form,
        'title': "Ajouter une matière",
        'cycles_config': [],
    })


@login_required
def matiere_update(request, pk):
    """Modification d'une matière et de ses configurations par cycle."""
    matiere = get_object_or_404(Matiere, pk=pk)

    if request.method == 'POST':
        form = MatiereForm(request.POST, instance=matiere)
        if form.is_valid():
            form.save()
            messages.success(request, f"Matière {matiere.nom} mise à jour.")
            return redirect('pedagogie:matiere_list')
    else:
        form = MatiereForm(instance=matiere)

    return render(request, 'pedagogie/matiere_form.html', {
        'form': form,
        'title': "Modifier la matière",
        'matiere': matiere,
        'cycles_config': _build_cycles_config(matiere),
    })


@login_required
def matiere_cycle_save(request, matiere_pk, cycle_pk):
    """Sauvegarde HTMX de la configuration d'une matière pour un cycle."""
    matiere = get_object_or_404(Matiere, pk=matiere_pk)
    cycle = get_object_or_404(Cycle, pk=cycle_pk)
    instance = MatiereCycle.objects.filter(matiere=matiere, cycle=cycle).first()

    if request.method == 'POST':
        # Supprimer la config si le coefficient est vide
        if not request.POST.get('coefficient', '').strip():
            if instance:
                instance.delete()
            instance = None
            form = MatiereCycleForm()
            return render(request, 'pedagogie/partials/cycle_config_row.html', {
                'cycle': cycle, 'config': None, 'form': form, 'matiere': matiere,
            })

        form = MatiereCycleForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.matiere = matiere
            obj.cycle = cycle
            obj.save()
            form = MatiereCycleForm(instance=obj)
            return render(request, 'pedagogie/partials/cycle_config_row.html', {
                'cycle': cycle, 'config': obj, 'form': form, 'matiere': matiere,
            })

        return render(request, 'pedagogie/partials/cycle_config_row.html', {
            'cycle': cycle, 'config': instance, 'form': form, 'matiere': matiere,
        })

    # GET — renvoie la ligne en mode édition
    form = MatiereCycleForm(instance=instance)
    return render(request, 'pedagogie/partials/cycle_config_row.html', {
        'cycle': cycle, 'config': instance, 'form': form, 'matiere': matiere,
    })

@login_required
def enseignement_list(request):
    """Liste des enseignements (affectations profs-matières-classes), groupés par classe."""
    from itertools import groupby
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    qs = Enseignement.objects.filter(annee_scolaire=annee_courante).select_related(
        'classe__cycle', 'matiere', 'personnel'
    ).order_by('classe__cycle__ordre', 'classe__nom', 'matiere__nom')

    classes_groupes = [
        {'classe': classe, 'enseignements': list(items)}
        for classe, items in groupby(qs, key=lambda e: e.classe)
    ]

    context = {
        'classes_groupes': classes_groupes,
        'annee_courante': annee_courante,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'pedagogie/partials/enseignement_table.html', context)

    return render(request, 'pedagogie/enseignement_list.html', context)

@login_required
def enseignement_create(request):
    """Nouvelle affectation d'enseignement."""
    if request.method == 'POST':
        form = EnseignementForm(request.POST)
        if form.is_valid():
            enseignement = form.save()
            messages.success(request, f"Affectation {enseignement} réussie.")
            return redirect('pedagogie:enseignement_list')
    else:
        annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
        form = EnseignementForm(initial={'annee_scolaire': annee_courante})
    
    return render(request, 'pedagogie/enseignement_form.html', {
        'form': form,
        'title': "Nouvelle Affectation"
    })

@login_required
def enseignement_update(request, pk):
    """Modification d'une affectation."""
    enseignement = get_object_or_404(Enseignement, pk=pk)
    if request.method == 'POST':
        form = EnseignementForm(request.POST, instance=enseignement)
        if form.is_valid():
            form.save()
            messages.success(request, f"Affectation {enseignement} mise à jour.")
            return redirect('pedagogie:enseignement_list')
    else:
        form = EnseignementForm(instance=enseignement)
    
    return render(request, 'pedagogie/enseignement_form.html', {
        'form': form,
        'title': "Modifier l'affectation",
        'enseignement': enseignement
    })

# ═══════════════════════════════════════════════════════════════════
# ÉVALUATIONS & NOTES
# ═══════════════════════════════════════════════════════════════════

@login_required
def evaluation_list(request):
    """Liste des évaluations planifiées."""
    from django.db.models import Count, Subquery, OuterRef
    from inscriptions.models import Inscription

    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()
    query = request.GET.get('q', '')

    evaluations = (
        Evaluation.objects
        .filter(enseignement__annee_scolaire=annee_courante)
        .select_related('enseignement__classe', 'enseignement__matiere', 'type_evaluation', 'trimestre')
        .annotate(nb_notes=Count('notes'))
    )

    if query:
        evaluations = evaluations.filter(
            Q(titre__icontains=query) |
            Q(enseignement__matiere__nom__icontains=query) |
            Q(enseignement__classe__nom__icontains=query)
        )

    # Nombre d'élèves actifs par classe (pour la progression)
    if annee_courante:
        nb_eleves_map = {
            row['classe_id']: row['total']
            for row in Inscription.objects.filter(
                annee_scolaire=annee_courante,
            ).exclude(statut='ABANDON').values('classe_id').annotate(total=Count('id'))
        }
    else:
        nb_eleves_map = {}

    # Attacher nb_eleves à chaque évaluation
    evaluations = list(evaluations.order_by(
        'enseignement__classe__nom',
        'enseignement__matiere__nom',
        'date_planifiee',
    ))
    for ev in evaluations:
        ev.nb_eleves = nb_eleves_map.get(ev.enseignement.classe_id, 0)

    # Groupement : classe → matière → [évaluations]
    groupes = {}
    for ev in evaluations:
        classe = ev.enseignement.classe
        matiere = ev.enseignement.matiere
        groupes.setdefault(classe, {}).setdefault(matiere, []).append(ev)

    # Convertir en liste ordonnée pour le template
    groupes_liste = [
        {
            'classe': classe,
            'matieres': [
                {'matiere': mat, 'evaluations': evs}
                for mat, evs in matieres.items()
            ],
            'total': sum(len(evs) for evs in matieres.values()),
        }
        for classe, matieres in groupes.items()
    ]

    context = {
        'evaluation_list': evaluations,
        'groupes': groupes_liste,
        'query': query,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'pedagogie/partials/evaluation_table.html', context)

    return render(request, 'pedagogie/evaluation_list.html', context)

def _resolve_trimestre(periode):
    """
    À partir d'une PeriodeEvaluation, trouve ou crée le pedagogie.Trimestre
    correspondant (même annee_scolaire + même numero).
    """
    trimestre, _ = Trimestre.objects.get_or_create(
        annee_scolaire=periode.annee_scolaire,
        numero=periode.numero,
        defaults={
            'nom': periode.nom,
            'type_periode': 'TRIMESTRE' if periode.type_periode == 'TRIMESTRE' else 'SEMESTRE',
            'date_debut': periode.date_debut,
            'date_fin': periode.date_fin,
        },
    )
    # Mettre à jour le nom si la PeriodeEvaluation a changé
    if trimestre.nom != periode.nom:
        trimestre.nom = periode.nom
        trimestre.save(update_fields=['nom'])
    return trimestre


@login_required
def evaluation_create(request):
    """Création d'une nouvelle évaluation."""
    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.trimestre = _resolve_trimestre(form.cleaned_data['periode'])
            evaluation.save()
            messages.success(request, f"Évaluation '{evaluation.titre}' planifiée.")
            return redirect('pedagogie:evaluation_list')
    else:
        form = EvaluationForm()

    return render(request, 'pedagogie/evaluation_form.html', {
        'form': form,
        'title': "Planifier une évaluation"
    })


@login_required
def evaluation_update(request, pk):
    """Modification d'une évaluation."""
    evaluation = get_object_or_404(
        Evaluation.objects.select_related('enseignement__classe'), pk=pk
    )
    etab = getattr(request.user, 'etablissement', None)

    if etab and evaluation.enseignement.classe.etablissement_id != etab.pk:
        messages.error(request, "Accès refusé. Cette évaluation n'appartient pas à votre établissement.")
        return redirect('pedagogie:evaluation_list')
    
    if request.method == 'POST':
        form = EvaluationForm(request.POST, instance=evaluation)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.trimestre = _resolve_trimestre(form.cleaned_data['periode'])
            evaluation.save()
            messages.success(request, f"Évaluation mise à jour.")
            return redirect('pedagogie:evaluation_list')
    else:
        form = EvaluationForm(instance=evaluation)

    return render(request, 'pedagogie/evaluation_form.html', {
        'form': form,
        'title': "Modifier l'évaluation",
        'evaluation': evaluation
    })

@login_required
def evaluation_saisie(request, pk):
    """Saisie groupée des notes pour une évaluation."""
    import decimal
    from inscriptions.models import Inscription

    evaluation = get_object_or_404(
        Evaluation.objects.select_related(
            'enseignement__classe__cycle',
            'enseignement__matiere',
            'enseignement__annee_scolaire',
            'type_evaluation',
            'trimestre',
        ),
        pk=pk,
    )
    classe = evaluation.enseignement.classe
    enseignement = evaluation.enseignement
    trimestre = evaluation.trimestre

    # Vérification de sécurité - vérifier que l'enseignant enseigne cette matière
    if request.user.role == 'ENSEIGNANT':
        from pedagogie.models import Enseignement
        authorized = Enseignement.objects.filter(
            id=enseignement.pk,
            personnel=request.user
        ).exists()
        if not authorized and classe.professeur_principal_id != request.user.id:
            messages.error(request, "Vous n'êtes pas autorisé à saisir les notes de cette évaluation.")
            return redirect('pedagogie:evaluation_list')

    inscriptions = Inscription.objects.filter(
        classe=classe,
        annee_scolaire=enseignement.annee_scolaire,
    ).exclude(statut='ABANDON').select_related('eleve').order_by('eleve__nom', 'eleve__prenom')

    if request.method == 'POST':
        updated_count = 0
        errors = []

        for ins in inscriptions:
            dispense_vals = request.POST.getlist(f'disp_{ins.id}')
            est_dispense = 'on' in dispense_vals

            if est_dispense:
                Resultat.objects.update_or_create(
                    inscription=ins,
                    enseignement=enseignement,
                    trimestre=trimestre,
                    defaults={'dispense': True, 'moyenne': None, 'nb_notes': 0,
                              'coefficient_utilise': enseignement.get_coefficient()},
                )
                Note.objects.filter(inscription=ins, evaluation=evaluation).delete()
                continue

            # Désactive le dispense si la case est décochée
            Resultat.objects.filter(
                inscription=ins, enseignement=enseignement, trimestre=trimestre,
            ).update(dispense=False)

            # Gestion "Absent" : note = 0, observation = ABS
            absent_vals = request.POST.getlist(f'abs_{ins.id}')
            est_absent = 'on' in absent_vals
            
            note_vals = request.POST.getlist(f'note_{ins.id}')
            note_val = next((v.strip() for v in note_vals if v.strip() != ''), '')
            
            obs_vals = request.POST.getlist(f'obs_{ins.id}')
            obs_val = next((v.strip() for v in obs_vals if v.strip() != ''), '')

            if est_absent:
                valeur = decimal.Decimal('0.00')
                obs_val = obs_val or 'ABS'
            elif note_val:
                try:
                    valeur = decimal.Decimal(note_val.replace(',', '.'))
                except (decimal.InvalidOperation, ValueError):
                    errors.append(f"Valeur invalide pour {ins.eleve.nom}")
                    continue
                if valeur < 0:
                    errors.append(f"{ins.eleve.nom} : la note ne peut pas être négative.")
                    continue
                if valeur > evaluation.bareme:
                    errors.append(
                        f"{ins.eleve.nom} : note {valeur} dépasse le barème {evaluation.bareme}. "
                        f"Corrigez et re-soumettez."
                    )
                    continue
            else:
                continue  # Champ vide → on ne touche pas la note

            note, created = Note.objects.get_or_create(
                inscription=ins,
                evaluation=evaluation,
                defaults={'valeur': valeur, 'observation': obs_val},
            )
            if not created:
                note.valeur = valeur
                note.observation = obs_val
                note.save()
            updated_count += 1

        if errors:
            for e in errors:
                messages.warning(request, e)

        if updated_count > 0:
            evaluation.statut = 'TERMINEE'
            evaluation.save(update_fields=['statut'])
            messages.success(request, f"{updated_count} note(s) enregistrée(s).")

        return redirect('pedagogie:evaluation_saisie', pk=pk)

    # GET — préparer les données
    notes_dict = {
        n.inscription_id: n
        for n in Note.objects.filter(evaluation=evaluation)
    }

    dispenses_ids = set(
        Resultat.objects.filter(
            enseignement=enseignement,
            trimestre=trimestre,
            dispense=True,
        ).values_list('inscription_id', flat=True)
    )

    eleves_data = []
    for ins in inscriptions:
        note = notes_dict.get(ins.id)
        eleves_data.append({
            'inscription': ins,
            'note': note,
            'est_absent': note is not None and note.observation == 'ABS' and note.valeur == 0,
            'est_dispense': ins.id in dispenses_ids,
        })

    nb_total = len(eleves_data)
    nb_saisies = sum(1 for d in eleves_data if d['note'] is not None and not d['est_dispense'])

    return render(request, 'pedagogie/note_saisie.html', {
        'evaluation': evaluation,
        'eleves_data': eleves_data,
        'nb_total': nb_total,
        'nb_saisies': nb_saisies,
    })


@login_required
def saisie_rapide_classe(request, class_id):
    """Page de saisie rapide : sélection évaluation depuis une classe."""
    from inscriptions.models import Inscription
    from django.db.models import Count

    classe = get_object_or_404(Classe, pk=class_id)
    annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    nb_eleves = Inscription.objects.filter(
        classe=classe, annee_scolaire=annee_courante,
    ).exclude(statut='ABANDON').count() if annee_courante else 0

    # Évaluations de la classe, annotées avec le nb de notes saisies
    evaluations = (
        Evaluation.objects
        .filter(enseignement__classe=classe, enseignement__annee_scolaire=annee_courante)
        .select_related('enseignement__matiere', 'type_evaluation', 'trimestre')
        .annotate(nb_notes=Count('notes'))
        .order_by('trimestre__numero', 'enseignement__matiere__nom', '-date_planifiee')
    )

    # Grouper par matière
    from collections import defaultdict
    par_matiere = defaultdict(list)
    for ev in evaluations:
        par_matiere[ev.enseignement.matiere].append(ev)

    return render(request, 'pedagogie/saisie_rapide_classe.html', {
        'classe': classe,
        'annee_courante': annee_courante,
        'nb_eleves': nb_eleves,
        'par_matiere': dict(par_matiere),
    })

@login_required
def saisie_classe_select(request):
    """Sélection de la classe pour la saisie des notes."""
    classes = Classe.objects.all().order_by('cycle__ordre', 'nom')
    return render(request, 'pedagogie/saisie_classe_select.html', {'classes': classes})


# ═══════════════════════════════════════════════════════════════════
# TABLEAU DES RÉSULTATS / MOYENNES
# ═══════════════════════════════════════════════════════════════════

@login_required
def resultat_classe(request, class_id):
    """Tableau de bord des résultats pour une classe."""
    from inscriptions.models import Inscription
    classe = get_object_or_404(Classe, pk=class_id)
    annees = AnneeScolaire.objects.all().order_by('-libelle')

    # Année sélectionnée (param GET ou année courante par défaut)
    selected_annee_id = request.GET.get('annee')
    if selected_annee_id:
        annee_courante = get_object_or_404(AnneeScolaire, pk=selected_annee_id)
    else:
        annee_courante = AnneeScolaire.objects.filter(est_courante=True).first()

    if not annee_courante:
        return render(request, 'pedagogie/resultat_classe.html', {
            'classe': classe,
            'annees': annees,
            'annee_courante': None,
            'trimestre': None,
            'trimestres': [],
            'inscriptions': [],
            'moyennes_gen': {},
            'error': 'Aucune année scolaire trouvée.'
        })

    trimestre = None
    selected_trimestre_id = request.GET.get('trimestre')
    if selected_trimestre_id:
        trimestre = get_object_or_404(Trimestre, pk=selected_trimestre_id)
    else:
        trimestre = Trimestre.objects.filter(annee_scolaire=annee_courante).first()

    inscriptions = Inscription.objects.filter(
        classe=classe,
        annee_scolaire=annee_courante,
    ).exclude(statut='ABANDON').select_related('eleve')

    # Récupérer les moyennes générales existantes
    moyennes_gen = {}
    if trimestre:
        moyennes_gen = {mg.inscription_id: mg for mg in MoyenneGenerale.objects.filter(trimestre=trimestre)}

    # Récupérer les trimestres dispos pour le filtre
    trimestres = Trimestre.objects.filter(annee_scolaire=annee_courante)

    return render(request, 'pedagogie/resultat_classe.html', {
        'classe': classe,
        'annees': annees,
        'annee_courante': annee_courante,
        'trimestre': trimestre,
        'trimestres': trimestres,
        'inscriptions': inscriptions,
        'moyennes_gen': moyennes_gen,
    })

@login_required
def calculer_moyennes_classe(request, class_id):
    """Action HTMX pour lancer le calcul des moyennes d'une classe."""
    if request.method != 'POST':
        return redirect('pedagogie:resultat_classe', class_id=class_id)
        
    classe = get_object_or_404(Classe, pk=class_id)
    trimestre_id = request.POST.get('trimestre_id')
    
    if not trimestre_id:
        messages.error(request, "Aucun trimestre sélectionné.")
        return redirect('pedagogie:resultat_classe', class_id=class_id)
    
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id)
    
    inscriptions = Inscription.objects.filter(classe=classe, annee_scolaire=trimestre.annee_scolaire).exclude(statut='ABANDON')
    enseignements = Enseignement.objects.filter(classe=classe, annee_scolaire=trimestre.annee_scolaire)
    
    # 1. Calculer les moyennes par matière
    for ins in inscriptions:
        for ens in enseignements:
            CalculateurMoyenne.calculer_resultat_matiere(ins, ens, trimestre)
            
    # 2. Calculer les moyennes générales
    for ins in inscriptions:
        CalculateurMoyenne.calculer_moyenne_generale(ins, trimestre)
        
    # 3. Calculer les rangs
    CalculateurMoyenne.calculer_rangs(classe, trimestre)
    
    messages.success(request, f"Calcul des moyennes terminé pour la classe {classe.nom}.")

    from django.urls import reverse
    url = reverse('pedagogie:resultat_classe', kwargs={'class_id': class_id})
    annee_id = request.POST.get('annee_id', str(trimestre.annee_scolaire_id))
    return redirect(f"{url}?annee={annee_id}&trimestre={trimestre_id}")

# ═══════════════════════════════════════════════════════════════════
# EXPORTS PDF (BULLETINS)
# ═══════════════════════════════════════════════════════════════════

def _get_appreciation_generale(inscription, mg, etab):
    """
    Retourne l'appréciation générale selon le cycle de l'élève.
    - Cycles POST et SEC → AppreciationMoyenneSecondaire
    - Autres cycles     → None
    Cherche d'abord par établissement, puis sans filtre etablissement en fallback.
    """
    from parametres.models import AppreciationMoyenneSecondaire
    if not mg or mg.moyenne is None:
        return None
    cycle_code = inscription.classe.cycle.code if inscription.classe.cycle_id else None
    if cycle_code not in ('POST', 'SEC'):
        return None
    base_qs = AppreciationMoyenneSecondaire.objects.filter(actif=True)
    if etab:
        base_qs = base_qs.filter(etablissement=etab)

    # 1. Correspondance exacte (moy_min <= moyenne <= moy_max)
    appreciation = base_qs.filter(
        moy_min__lte=mg.moyenne,
        moy_max__gte=mg.moyenne,
    ).first()
    if appreciation:
        return appreciation

    # 2. Fallback : appréciation dont la borne supérieure est la plus proche
    #    en dessous de la moyenne (couvre les trous de configuration)
    appreciation = base_qs.filter(
        moy_max__lt=mg.moyenne
    ).order_by('-moy_max').first()
    if appreciation:
        return appreciation

    # 3. Dernière chance : appréciation avec la borne inférieure la plus basse
    return base_qs.order_by('moy_min').first()

def _load_appreciations(etab):
    """Charge toutes les appréciations actives pour un établissement."""
    from parametres.models import AppreciationMoyenneSecondaire
    qs = AppreciationMoyenneSecondaire.objects.filter(actif=True)
    if etab:
        qs = qs.filter(etablissement=etab)
    return list(qs.order_by('moy_min'))


def _match_appreciation(moyenne, apprs):
    """Trouve l'appréciation correspondant à une moyenne depuis une liste pré-chargée."""
    if moyenne is None or not apprs:
        return None
    # Correspondance exacte
    for a in apprs:
        if a.moy_min <= moyenne <= a.moy_max:
            return a
    # Fallback : borne supérieure la plus proche en dessous
    below = [a for a in apprs if a.moy_max < moyenne]
    if below:
        return max(below, key=lambda a: a.moy_max)
    return apprs[0]


def _annotate_resultats(resultats, apprs, cycle_code):
    """
    Annote chaque Resultat avec un attribut .appreciation et retourne la liste.
    """
    for r in resultats:
        if cycle_code in ('POST', 'SEC') and not r.dispense and r.moyenne is not None:
            r.appreciation = _match_appreciation(r.moyenne, apprs)
        else:
            r.appreciation = None
    return resultats


@login_required
def _build_bulletin_context(request, inscription, trimestre):
    """Construit le contexte commun utilisé par l'aperçu HTML et le PDF."""
    from django.db.models import Max, Min, Avg
    from datetime import date as _date
    from parametres.models import TypeDocument, SignataireDocument
    from viescolaire.models import SanctionDisciplinaire
    from .utils_ia import generer_commentaire_eleve

    mg = get_object_or_404(MoyenneGenerale, inscription=inscription, trimestre=trimestre)
    resultats = Resultat.objects.filter(
        inscription=inscription, trimestre=trimestre
    ).select_related('enseignement__matiere', 'enseignement__personnel')

    nb_eleves = (
        Inscription.objects
        .filter(classe=inscription.classe, annee_scolaire=trimestre.annee_scolaire)
        .exclude(statut='ABANDON').count()
    )

    stats_classe = MoyenneGenerale.objects.filter(
        inscription__classe=inscription.classe, trimestre=trimestre,
    ).aggregate(max_moy=Max('moyenne'), min_moy=Min('moyenne'), avg_moy=Avg('moyenne'))

    etab = inscription.classe.etablissement
    etab_context = get_etablissement_context(etab, request)

    cycle_code = inscription.classe.cycle.code if inscription.classe.cycle_id else None
    apprs = _load_appreciations(etab)
    appreciation_generale = _get_appreciation_generale(inscription, mg, etab=etab)
    resultats_annotes = _annotate_resultats(list(resultats), apprs, cycle_code)

    cycle = inscription.classe.cycle
    annee = trimestre.annee_scolaire
    type_doc_bulletin = (
        TypeDocument.objects.filter(code__icontains='bulletin', cycle=cycle, actif=True).first()
        or TypeDocument.objects.filter(code__icontains='bulletin', actif=True).first()
    )
    signataire = SignataireDocument.objects.get_signataire(
        cycle=cycle, type_document=type_doc_bulletin, annee_scolaire=annee,
    ) if type_doc_bulletin else None
    signataire_membre = signataire.get_membre_personnel() if signataire else None

    today = _date.today()
    mois_fr = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
    lieu = (etab.ville + ', le ') if etab.ville else 'Le '
    date_lieu = f"{lieu}{today.day} {mois_fr[today.month - 1]} {today.year}"

    sanctions_conduite = list(
        SanctionDisciplinaire.objects.filter(
            inscription=inscription,
            trimestre=trimestre,
            statut=SanctionDisciplinaire.StatutChoices.CONFIRME,
            is_active=True,
        ).select_related('type_sanction').order_by('date_sanction')
    )

    commentaire_eleve = generer_commentaire_eleve(
        mg, nb_eleves, stats_classe['avg_moy'], resultats_annotes, sanctions_conduite
    )

    # Compétences APC (Préscolaire / Primaire uniquement)
    competences_data = None
    if cycle and cycle.code in ('PRES', 'PRIM'):
        competences_qs = (
            Competence.objects.filter(cycle=cycle, actif=True)
            .select_related('matiere')
            .order_by('matiere__code', 'categorie', 'ordre')
        )
        evals_qs = EvaluationCompetence.objects.filter(
            inscription=inscription,
            competence__in=competences_qs,
            trimestre=trimestre,
        )
        evals_map = {str(ev.competence_id): ev for ev in evals_qs}

        from collections import defaultdict
        groupes = defaultdict(list)
        for comp in competences_qs:
            ev = evals_map.get(str(comp.pk))
            groupes[comp.get_categorie_display()].append({'competence': comp, 'evaluation': ev})
        competences_data = {
            'groupes': [(cat, items) for cat, items in groupes.items()],
            'total': competences_qs.count(),
            'acquis': sum(1 for ev in evals_map.values() if ev.niveau == 'ACQUIS'),
            'en_cours': sum(1 for ev in evals_map.values() if ev.niveau == 'EN_COURS'),
            'non_acquis': sum(1 for ev in evals_map.values() if ev.niveau == 'NON_ACQUIS'),
        }

    return {
        'inscription': inscription,
        'trimestre': trimestre,
        'mg': mg,
        'total_points_max': mg.total_coefficients * 20,
        'resultats_annotes': resultats_annotes,
        'nb_eleves': nb_eleves,
        'moy_max_classe': stats_classe['max_moy'],
        'moy_min_classe': stats_classe['min_moy'],
        'moy_avg_classe': stats_classe['avg_moy'],
        'appreciation_generale': appreciation_generale,
        'sanctions_conduite': sanctions_conduite,
        'commentaire_eleve': commentaire_eleve,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'signataire': signataire,
        'signataire_membre': signataire_membre,
        'date_lieu': date_lieu,
        'competences_data': competences_data,
    }


@login_required
def bulletin_apercu(request, inscription_id, trimestre_id):
    """Aperçu HTML du bulletin dans le navigateur (sans génération PDF)."""
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe__cycle', 'annee_scolaire'),
        pk=inscription_id,
    )
    trimestre = get_object_or_404(Trimestre.objects.select_related('annee_scolaire'), pk=trimestre_id)
    ctx = _build_bulletin_context(request, inscription, trimestre)
    ctx['pdf_url'] = request.build_absolute_uri(
        f"/pedagogie/bulletins/{inscription_id}/{trimestre_id}/pdf/"
    )
    return render(request, 'pedagogie/bulletin_apercu.html', ctx)


@login_required
def bulletin_pdf(request, inscription_id, trimestre_id):
    """Génère le bulletin PDF d'un élève pour un trimestre."""
    if HTML is None:
        messages.error(request, "L'extension WeasyPrint n'est pas installée sur le serveur.")
        return redirect('pedagogie:resultat_classe', class_id=Inscription.objects.get(pk=inscription_id).classe_id)

    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe__cycle', 'annee_scolaire'),
        pk=inscription_id,
    )
    trimestre = get_object_or_404(Trimestre.objects.select_related('annee_scolaire'), pk=trimestre_id)

    ctx = _build_bulletin_context(request, inscription, trimestre)
    html_string = render_to_string('pedagogie/pdf/bulletin_trimestriel.html', ctx)

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Bulletin_{inscription.eleve.nom}_{trimestre.nom}.pdf".replace(" ", "_")
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

@login_required
def bulletin_classe_batch_pdf(request, class_id, trimestre_id):
    """Génère un seul PDF contenant tous les bulletins d'une classe."""
    if HTML is None:
        messages.error(request, "L'extension WeasyPrint n'est pas installée sur le serveur.")
        return redirect('pedagogie:resultat_classe', class_id=class_id)

    classe = get_object_or_404(Classe, pk=class_id)
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id)
    
    inscriptions = Inscription.objects.select_related(
        'eleve', 'classe__cycle'
    ).filter(classe=classe, annee_scolaire=trimestre.annee_scolaire).exclude(statut='ABANDON')
    nb_eleves = inscriptions.count()

    etab = classe.etablissement
    cycle_code = classe.cycle.code if classe.cycle_id else None
    apprs = _load_appreciations(etab)

    # Récupérer toutes les données nécessaires
    from viescolaire.models import SanctionDisciplinaire
    # Précharger toutes les sanctions confirmées de la classe pour ce trimestre
    sanctions_par_ins = {}
    for s in SanctionDisciplinaire.objects.filter(
        inscription__classe=classe,
        trimestre=trimestre,
        statut=SanctionDisciplinaire.StatutChoices.CONFIRME,
        is_active=True,
    ).select_related('type_sanction').order_by('date_sanction'):
        sanctions_par_ins.setdefault(s.inscription_id, []).append(s)

    # Compétences APC (batch: précharger pour tous les élèves du cycle PRES/PRIM)
    cycle = classe.cycle
    competences_par_ins = {}
    if cycle and cycle.code in ('PRES', 'PRIM'):
        competences_qs = list(
            Competence.objects.filter(cycle=cycle, actif=True)
            .select_related('matiere')
            .order_by('matiere__code', 'categorie', 'ordre')
        )
        all_evals = EvaluationCompetence.objects.filter(
            inscription__in=inscriptions,
            competence__in=competences_qs,
            trimestre=trimestre,
        )
        for ins_pk in inscriptions.values_list('pk', flat=True):
            competences_par_ins[ins_pk] = {'competences': competences_qs, 'evals_map': {}}
        for ev in all_evals:
            competences_par_ins.setdefault(ev.inscription_id, {'competences': competences_qs, 'evals_map': {}})
            competences_par_ins[ev.inscription_id]['evals_map'][str(ev.competence_id)] = ev

    students_data = []
    for ins in inscriptions:
        try:
            mg = MoyenneGenerale.objects.get(inscription=ins, trimestre=trimestre)
            resultats = list(Resultat.objects.filter(inscription=ins, trimestre=trimestre).select_related('enseignement__matiere', 'enseignement__personnel'))
            resultats_annotes = _annotate_resultats(resultats, apprs, cycle_code)
            sanctions = sanctions_par_ins.get(ins.pk, [])

            # Compétences APC pour cet élève
            competences_data = None
            if cycle and cycle.code in ('PRES', 'PRIM') and ins.pk in competences_par_ins:
                cdata = competences_par_ins[ins.pk]
                from collections import defaultdict
                groupes = defaultdict(list)
                for comp in cdata['competences']:
                    ev = cdata['evals_map'].get(str(comp.pk))
                    groupes[comp.get_categorie_display()].append({'competence': comp, 'evaluation': ev})
                competences_data = {
                    'groupes': [(cat, items) for cat, items in groupes.items()],
                    'total': len(cdata['competences']),
                    'acquis': sum(1 for ev in cdata['evals_map'].values() if ev.niveau == 'ACQUIS'),
                    'en_cours': sum(1 for ev in cdata['evals_map'].values() if ev.niveau == 'EN_COURS'),
                    'non_acquis': sum(1 for ev in cdata['evals_map'].values() if ev.niveau == 'NON_ACQUIS'),
                }

            students_data.append({
                'inscription': ins,
                'mg': mg,
                'resultats_annotes': resultats_annotes,
                'appreciation_generale': _get_appreciation_generale(ins, mg, etab),
                'sanctions_conduite': sanctions,
                'commentaire_eleve': None,
                'competences_data': competences_data,
            })
        except MoyenneGenerale.DoesNotExist:
            continue

    if not students_data:
        messages.warning(request, "Aucune moyenne calculée pour cette classe.")
        return redirect('pedagogie:resultat_classe', class_id=class_id)

    # Meilleures / plus faible moyenne de la classe (calculées depuis les données déjà chargées)
    toutes_moyennes = [d['mg'].moyenne for d in students_data if d['mg'].moyenne is not None]
    moy_max_classe = max(toutes_moyennes) if toutes_moyennes else None
    moy_min_classe = min(toutes_moyennes) if toutes_moyennes else None
    moy_avg_classe = round(sum(toutes_moyennes) / len(toutes_moyennes), 2) if toutes_moyennes else None

    # Commentaires individuels (nécessitent moy_avg_classe, calculé ci-dessus)
    from .utils_ia import generer_commentaire_eleve
    for d in students_data:
        d['commentaire_eleve'] = generer_commentaire_eleve(
            d['mg'], nb_eleves, moy_avg_classe, d['resultats_annotes'], d['sanctions_conduite']
        )

    # Contexte établissement
    etab_context = get_etablissement_context(etab, request)
    
    # 2. Rendre le template HTML (on utilisera un template qui boucle sur les élèves)
    html_string = render_to_string('pedagogie/pdf/bulletin_batch.html', {
        'trimestre': trimestre,
        'classe': classe,
        'students_data': students_data,
        'nb_eleves': nb_eleves,
        'moy_max_classe': moy_max_classe,
        'moy_min_classe': moy_min_classe,
        'moy_avg_classe': moy_avg_classe,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
    })
    
    # 3. Générer le PDF
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Bulletins_{classe.nom}_{trimestre.nom}.pdf".replace(" ", "_")
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response


# ═══════════════════════════════════════════════════════════════════
# MOYENNES PAR DISCIPLINE
# ═══════════════════════════════════════════════════════════════════

@login_required
def moyennes_disciplines(request):
    """
    Tableau des moyennes par discipline pour chaque élève d'une classe.
    Paramètres : année scolaire, période d'évaluation (trimestre), classe.
    """
    etab = request.user.etablissement

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut') if etab else AnneeScolaire.objects.none()
    classes = Classe.objects.filter(etablissement=etab, actif=True).select_related('cycle').order_by('cycle__ordre', 'nom') if etab else Classe.objects.none()

    annee_id    = request.GET.get('annee')
    trimestre_id = request.GET.get('trimestre')
    classe_id   = request.GET.get('classe')

    annee     = annees.filter(pk=annee_id).first() if annee_id else (annees.filter(est_courante=True).first() or annees.first())
    trimestres = Trimestre.objects.filter(annee_scolaire=annee).order_by('numero') if annee else Trimestre.objects.none()
    trimestre  = trimestres.filter(pk=trimestre_id).first() if trimestre_id else None
    classe     = classes.filter(pk=classe_id).first() if classe_id else None

    # Réponse HTMX : recharger la liste des trimestres
    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'trimestres':
        from django.template.loader import render_to_string
        html = render_to_string('pedagogie/partials/trimestre_options.html', {'trimestres': trimestres, 'trimestre': trimestre})
        return HttpResponse(html)

    enseignements = []
    lignes        = []

    if annee and trimestre and classe:
        enseignements = list(
            Enseignement.objects.filter(
                classe=classe,
                annee_scolaire=annee,
                est_actif=True,
            ).select_related('matiere').order_by('matiere__nom')
        )

        inscriptions = list(
            Inscription.objects.filter(
                classe=classe,
                annee_scolaire=annee,
            ).exclude(statut='ABANDON').select_related('eleve').order_by('eleve__nom', 'eleve__prenom')
        )

        # Chargement groupé : tous les Resultat d'un coup
        resultats_qs = Resultat.objects.filter(
            enseignement__in=enseignements,
            trimestre=trimestre,
            inscription__in=inscriptions,
        )
        # {inscription_id: {enseignement_id: resultat}}
        res_map: dict = {}
        for r in resultats_qs:
            res_map.setdefault(r.inscription_id, {})[r.enseignement_id] = r

        # Chargement groupé : toutes les MoyenneGenerale
        mg_map: dict = {
            mg.inscription_id: mg
            for mg in MoyenneGenerale.objects.filter(
                trimestre=trimestre,
                inscription__in=inscriptions,
            )
        }

        for inscr in inscriptions:
            resultats_row = []
            for ens in enseignements:
                r = res_map.get(inscr.pk, {}).get(ens.pk)
                resultats_row.append(r)
            lignes.append({
                'inscription': inscr,
                'eleve':       inscr.eleve,
                'resultats':   resultats_row,
                'mg':          mg_map.get(inscr.pk),
            })

    return render(request, 'pedagogie/moyennes_disciplines.html', {
        'annees':        annees,
        'classes':       classes,
        'trimestres':    trimestres,
        'annee':         annee,
        'trimestre':     trimestre,
        'classe':        classe,
        'enseignements': enseignements,
        'lignes':        lignes,
    })


@login_required
def moyennes_disciplines_pdf(request):
    """Génère le PDF du tableau des moyennes par discipline."""
    etab = request.user.etablissement

    annee_id     = request.GET.get('annee')
    trimestre_id = request.GET.get('trimestre')
    classe_id    = request.GET.get('classe')

    if not (annee_id and trimestre_id and classe_id):
        return redirect('pedagogie:moyennes_disciplines')

    annee     = get_object_or_404(AnneeScolaire, pk=annee_id)
    trimestre = get_object_or_404(Trimestre, pk=trimestre_id, annee_scolaire=annee)
    classe    = get_object_or_404(Classe, pk=classe_id)

    etab_context = get_etablissement_context(etab, request)

    enseignements = list(
        Enseignement.objects.filter(
            classe=classe, annee_scolaire=annee, est_actif=True,
        ).select_related('matiere').order_by('matiere__nom')
    )
    inscriptions = list(
        Inscription.objects.filter(
            classe=classe, annee_scolaire=annee,
        ).exclude(statut='ABANDON').select_related('eleve').order_by('eleve__nom', 'eleve__prenom')
    )

    res_map: dict = {}
    for r in Resultat.objects.filter(
        enseignement__in=enseignements,
        trimestre=trimestre,
        inscription__in=inscriptions,
    ):
        res_map.setdefault(r.inscription_id, {})[r.enseignement_id] = r

    mg_map: dict = {
        mg.inscription_id: mg
        for mg in MoyenneGenerale.objects.filter(
            trimestre=trimestre, inscription__in=inscriptions,
        )
    }

    lignes = []
    for inscr in inscriptions:
        resultats_row = [res_map.get(inscr.pk, {}).get(ens.pk) for ens in enseignements]
        lignes.append({
            'inscription': inscr,
            'eleve':       inscr.eleve,
            'resultats':   resultats_row,
            'mg':          mg_map.get(inscr.pk),
        })

    from django.utils import timezone as tz
    html_str = render_to_string('pedagogie/pdf/moyennes_disciplines.html', {
        'annee':         annee,
        'trimestre':     trimestre,
        'classe':        classe,
        'enseignements': enseignements,
        'lignes':        lignes,
        'identite':      etab_context.get('identite'),
        'logo_url':      etab_context.get('logo_url'),
        'date_impression': tz.now().strftime('%d/%m/%Y'),
    }, request=request)

    if HTML is None:
        return HttpResponse("WeasyPrint non disponible.", status=500)

    buffer = __import__('io').BytesIO()
    HTML(string=html_str).write_pdf(buffer)
    nom = f"Moyennes_{classe.nom}_{trimestre.nom}_{annee.libelle}.pdf".replace(' ', '_')
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


# ═══════════════════════════════════════════════════════════════════
# RELEVÉ DE NOTES
# ═══════════════════════════════════════════════════════════════════

@login_required
def releve_notes(request):
    """
    Relevé de notes : tableau croisé élèves × évaluations.
    Filtres : année scolaire, classe, discipline (matière/enseignement), période.
    """
    from parametres.models import PeriodeEvaluation

    etab = request.user.etablissement

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut') if etab else AnneeScolaire.objects.none()
    classes = Classe.objects.filter(etablissement=etab, actif=True).select_related('cycle').order_by('cycle__ordre', 'nom') if etab else Classe.objects.none()

    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    enseignement_id = request.GET.get('enseignement') or request.GET.get('ENSEIGNEMENT')
    periode_id = request.GET.get('periode')

    annee = annees.filter(pk=annee_id).first() if annee_id else (annees.filter(est_courante=True).first() or annees.first())
    classe = classes.filter(pk=classe_id).first() if classe_id else None

    # Si annee_id est fourni mais annee non trouvé dans le filtre etab → chercher sans filtre
    if annee_id and not annee:
        annee = AnneeScolaire.objects.filter(pk=annee_id).first()

    enseignements = Enseignement.objects.none()
    if classe:
        qs_classe = Enseignement.objects.filter(classe=classe, est_actif=True).select_related('matiere')
        if annee:
            qs_filtered = qs_classe.filter(annee_scolaire=annee)
            enseignements = qs_filtered if qs_filtered.exists() else qs_classe
        else:
            enseignements = qs_classe
        enseignements = enseignements.order_by('matiere__nom')

    periodes = PeriodeEvaluation.objects.none()
    if annee and etab:
        periodes = PeriodeEvaluation.objects.filter(
            annee_scolaire=annee, etablissement=etab,
        ).order_by('numero')

    # Délègue la construction du tableau à _build_releve_context
    # On passe str(annee.pk) plutôt que annee_id brut pour couvrir le cas
    # où annee est auto-sélectionnée (annee_id=None en premier chargement).
    releve_ctx = {}
    if enseignement_id:
        effective_annee_id = str(annee.pk) if annee else annee_id
        releve_ctx = _build_releve_context(effective_annee_id, enseignement_id, periode_id) or {}

    # Resolve periode pour l'affichage des selects même sans releve_ctx
    periode = releve_ctx.get('periode')
    if not periode and periode_id:
        periode = PeriodeEvaluation.objects.filter(pk=periode_id).first()

    context = {
        'annees': annees,
        'annee': annee,
        'classes': classes,
        'classe': classe,
        'enseignements': enseignements,
        'enseignement': releve_ctx.get('enseignement'),
        'periodes': periodes,
        'periode': periode,
        'evaluations_cols': releve_ctx.get('evaluations_cols', []),
        'table': releve_ctx.get('table'),
        'ev_stats': releve_ctx.get('ev_stats', []),
        'moy_classe': releve_ctx.get('moy_classe'),
        'moy_max': releve_ctx.get('moy_max'),
        'moy_min': releve_ctx.get('moy_min'),
        'nb_saisies': releve_ctx.get('nb_saisies', 0),
        'nb_max_saisies': releve_ctx.get('nb_max_saisies', 0),
    }
    return render(request, 'pedagogie/releve_notes.html', context)


def _build_releve_context(annee_id, enseignement_id, periode_id):
    """Construit le contexte commun pour releve_notes et releve_notes_pdf."""
    from collections import defaultdict
    from parametres.models import PeriodeEvaluation

    annee = AnneeScolaire.objects.filter(pk=annee_id).first() if annee_id else None
    enseignement = (
        Enseignement.objects.filter(pk=enseignement_id)
        .select_related('matiere', 'classe__cycle', 'annee_scolaire')
        .first()
    ) if enseignement_id else None
    periode = PeriodeEvaluation.objects.filter(pk=periode_id).first() if periode_id else None

    if not enseignement:
        return None

    ev_qs = (
        Evaluation.objects
        .filter(enseignement=enseignement)
        .select_related('type_evaluation', 'trimestre')
        .order_by('trimestre__numero', 'type_evaluation__ordre', 'date_planifiee', 'titre')
    )
    if periode and annee:
        ev_qs = ev_qs.filter(
            trimestre__annee_scolaire=annee,
            trimestre__numero=periode.numero,
        )
    evaluations_cols = list(ev_qs)

    inscriptions = (
        Inscription.objects
        .filter(classe=enseignement.classe, annee_scolaire=annee)
        .exclude(statut='ABANDON')
        .select_related('eleve')
        .order_by('eleve__nom', 'eleve__prenom')
    )

    notes_qs = Note.objects.filter(
        evaluation__in=evaluations_cols,
        inscription__in=inscriptions,
    ).values('inscription_id', 'evaluation_id', 'valeur', 'observation')

    notes_index = defaultdict(dict)
    for n in notes_qs:
        notes_index[n['inscription_id']][n['evaluation_id']] = n

    resultats_index = {}
    if periode and annee:
        for res in Resultat.objects.filter(
            inscription__in=inscriptions,
            enseignement=enseignement,
            trimestre__annee_scolaire=annee,
            trimestre__numero=periode.numero,
        ):
            resultats_index[res.inscription_id] = res

    table = []
    for ins in inscriptions:
        row_notes = []
        valeurs_sur_20 = []
        for ev in evaluations_cols:
            note_data = notes_index[ins.pk].get(ev.pk)
            if note_data and note_data.get('observation') != 'ABS':
                try:
                    v = float(note_data['valeur'])
                    b = float(ev.bareme) if ev.bareme else 20.0
                    sur_20 = round((v / b) * 20, 2)
                    note_data = dict(note_data, sur_20=sur_20)
                    valeurs_sur_20.append(sur_20)
                except (TypeError, ValueError):
                    note_data = dict(note_data)
            row_notes.append(note_data)
        resultat = resultats_index.get(ins.pk)
        table.append({
            'inscription': ins,
            'notes': row_notes,
            'resultat': resultat,
            'nb_notes': len(valeurs_sur_20),
            'moyenne_locale': round(sum(valeurs_sur_20) / len(valeurs_sur_20), 2) if valeurs_sur_20 else None,
        })

    # Stats colonnes unifiées (ev, avg_sur_20, count)
    nb_rows = len(table)
    ev_stats = []
    for c_idx, ev in enumerate(evaluations_cols):
        vals, count = [], 0
        for row in table:
            nd = row['notes'][c_idx] if c_idx < len(row['notes']) else None
            if nd:
                count += 1
                if nd.get('sur_20') is not None:
                    vals.append(nd['sur_20'])
        ev_stats.append({
            'ev': ev,
            'avg': round(sum(vals) / len(vals), 2) if vals else None,
            'count': count,
        })

    # Meilleures / plus faibles moyennes par élève
    moyennes = []
    for row in table:
        moy = None
        if row['resultat'] and row['resultat'].moyenne_sur_20 is not None:
            moy = float(row['resultat'].moyenne_sur_20)
        elif row['moyenne_locale'] is not None:
            moy = float(row['moyenne_locale'])
        if moy is not None:
            moyennes.append({'inscription': row['inscription'], 'moy': moy})

    moy_max = max(moyennes, key=lambda x: x['moy']) if moyennes else None
    moy_min = min(moyennes, key=lambda x: x['moy']) if moyennes else None
    moy_classe = round(sum(m['moy'] for m in moyennes) / len(moyennes), 2) if moyennes else None

    # Rang dans la classe (par moyenne décroissante, ex aequo inclus)
    moyennes_indexed = [
        (i, float(row['resultat'].moyenne_sur_20) if row['resultat'] and row['resultat'].moyenne_sur_20 is not None
         else float(row['moyenne_locale']) if row['moyenne_locale'] is not None else None)
        for i, row in enumerate(table)
    ]
    sorted_moy = sorted(
        [(i, m) for i, m in moyennes_indexed if m is not None],
        key=lambda x: x[1], reverse=True,
    )
    rank_map = {}
    for pos, (i, moy) in enumerate(sorted_moy):
        if pos > 0 and moy == sorted_moy[pos - 1][1]:
            rank_map[i] = rank_map[sorted_moy[pos - 1][0]]
        else:
            rank_map[i] = pos + 1
    for i, row in enumerate(table):
        row['rang'] = rank_map.get(i)

    # Totaux saisies
    nb_saisies = sum(s['count'] for s in ev_stats)
    nb_max_saisies = nb_rows * len(evaluations_cols)

    # Signataire
    from parametres.models import TypeDocument, SignataireDocument
    type_doc_releve = TypeDocument.objects.filter(code='RELEVE_NOTES').first()
    cycle = enseignement.classe.cycle if hasattr(enseignement.classe, 'cycle') else None
    signataire = SignataireDocument.objects.get_signataire(
        cycle=cycle,
        type_document=type_doc_releve,
        annee_scolaire=annee,
    ) if type_doc_releve else None
    signataire_membre = signataire.get_membre_personnel() if signataire else None

    return {
        'annee': annee,
        'enseignement': enseignement,
        'periode': periode,
        'evaluations_cols': evaluations_cols,
        'table': table,
        'ev_stats': ev_stats,
        'nb_rows': nb_rows,
        'moy_max': moy_max,
        'moy_min': moy_min,
        'moy_classe': moy_classe,
        'nb_saisies': nb_saisies,
        'nb_max_saisies': nb_max_saisies,
        'signataire': signataire,
        'signataire_membre': signataire_membre,
    }


@login_required
def releve_notes_pdf(request):
    """Génère le relevé de notes en PDF (mêmes paramètres GET que releve_notes)."""
    if HTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur le serveur.")
        return redirect('pedagogie:releve_notes')

    ctx = _build_releve_context(
        annee_id=request.GET.get('annee'),
        enseignement_id=request.GET.get('enseignement'),
        periode_id=request.GET.get('periode'),
    )
    if not ctx or not ctx['table']:
        messages.warning(request, "Aucune donnée à imprimer. Vérifiez les filtres.")
        return redirect(request.META.get('HTTP_REFERER', 'pedagogie:releve_notes'))

    enseignement = ctx['enseignement']
    etab = enseignement.classe.etablissement if hasattr(enseignement.classe, 'etablissement') else None
    etab_context = get_etablissement_context(etab, request) if etab else {}

    html_string = render_to_string('pedagogie/pdf/releve_notes.html', {
        **ctx,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
    })

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    periode_label = ctx['periode'].nom.replace(' ', '_') if ctx['periode'] else 'toutes_periodes'
    filename = f"Releve_{enseignement.matiere.code}_{enseignement.classe.nom}_{periode_label}.pdf".replace(' ', '_')
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def fiche_discipline_pdf(request):
    """
    Fiche officielle de relevé de notes par discipline et par évaluation,
    signée par l'enseignant de la classe pour cette discipline.
    Mêmes paramètres GET que releve_notes : annee, enseignement, periode.
    """
    if HTML is None:
        messages.error(request, "WeasyPrint n'est pas installé sur le serveur.")
        return redirect('pedagogie:releve_notes')

    ctx = _build_releve_context(
        annee_id=request.GET.get('annee'),
        enseignement_id=request.GET.get('enseignement'),
        periode_id=request.GET.get('periode'),
    )
    if not ctx or not ctx['table']:
        messages.warning(request, "Aucune donnée à imprimer. Vérifiez les filtres sélectionnés.")
        return redirect(request.META.get('HTTP_REFERER', 'pedagogie:releve_notes'))

    enseignement = ctx['enseignement']
    professeur = enseignement.personnel  # FK vers MembrePersonnel (peut être None)

    etab = getattr(enseignement.classe, 'etablissement', None)
    etab_context = get_etablissement_context(etab, request) if etab else {}

    from datetime import date as _date
    html_string = render_to_string('pedagogie/pdf/fiche_discipline.html', {
        **ctx,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'today': _date.today(),
        'professeur': professeur,
    })

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    periode_label = ctx['periode'].nom.replace(' ', '_') if ctx['periode'] else 'annee'
    filename = (
        f"Fiche_{enseignement.matiere.code}_{enseignement.classe.nom}_{periode_label}.pdf"
        .replace(' ', '_')
    )
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# ─── RISQUE DE DÉCROCHAGE ────────────────────────────────────────────

@login_required
def risque_decrochage(request):
    """
    Tableau de bord des élèves à risque de décrochage scolaire.

    Affiche les scores calculés (par `calculer_risques`) avec filtres
    par niveau de risque et par classe. Permet aussi de recalculer
    manuellement le score d'un seul élève via POST.
    """
    from .utils_ia import calculer_score_risque

    etab = getattr(request.user, 'etablissement', None)
    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else AnneeScolaire.objects.filter(est_courante=True).first()

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut') if etab else AnneeScolaire.objects.none()
    annee_id = request.GET.get('annee')
    if annee_id:
        annee = annees.filter(pk=annee_id).first() or annee

    # Recalcul manuel (POST depuis la liste)
    if request.method == 'POST':
        inscription_id = request.POST.get('inscription_id')
        recalculer_tout = request.POST.get('recalculer_tout')

        if recalculer_tout and annee:
            # Recalcul pour tous les élèves de l'établissement pour l'année en cours
            inscriptions = Inscription.objects.filter(
                annee_scolaire=annee,
                classe__etablissement=etab
            ).exclude(statut='ABANDON').select_related('eleve', 'classe')

            count = 0
            for ins in inscriptions:
                score, facteurs = calculer_score_risque(ins, annee)
                niveau = RisqueDecrochage.niveau_pour_score(score)
                RisqueDecrochage.objects.update_or_create(
                    inscription=ins,
                    defaults={'score': score, 'niveau': niveau, 'facteurs': facteurs},
                )
                count += 1
            
            messages.success(request, f"Analyse terminée : {count} élève(s) traité(s).")
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Refresh'] = 'true'
                return response
            return redirect('pedagogie:risque_decrochage')

        if inscription_id and annee:
            try:
                inscription = Inscription.objects.select_related('eleve', 'classe').get(
                    pk=inscription_id, annee_scolaire=annee
                )
                score, facteurs = calculer_score_risque(inscription, annee)
                niveau = RisqueDecrochage.niveau_pour_score(score)
                risque, _ = RisqueDecrochage.objects.update_or_create(
                    inscription=inscription,
                    defaults={'score': score, 'niveau': niveau, 'facteurs': facteurs},
                )
                
                if request.headers.get('HX-Request'):
                    return render(request, 'pedagogie/partials/risque_row.html', {'r': risque})
                
                messages.success(request, f"Score recalculé : {niveau} ({score}/100)")
            except Inscription.DoesNotExist:
                if request.headers.get('HX-Request'):
                    return HttpResponse("Erreur", status=404)
                messages.error(request, "Inscription introuvable.")
        
        if request.headers.get('HX-Request'):
             return HttpResponse("Ok")
             
        return redirect('pedagogie:risque_decrochage')

    niveau_filtre = request.GET.get('niveau', '')
    classe_id = request.GET.get('classe', '')

    classes = Classe.objects.filter(
        etablissement=etab, actif=True
    ).order_by('cycle__ordre', 'nom') if etab else Classe.objects.none()

    risques_qs = (
        RisqueDecrochage.objects
        .filter(inscription__annee_scolaire=annee, inscription__classe__etablissement=etab)
        .exclude(inscription__statut='ABANDON')
        .select_related('inscription__eleve', 'inscription__classe')
        .order_by('-score')
    )
    if niveau_filtre:
        risques_qs = risques_qs.filter(niveau=niveau_filtre)
    if classe_id:
        risques_qs = risques_qs.filter(inscription__classe_id=classe_id)

    tous = RisqueDecrochage.objects.filter(
        inscription__annee_scolaire=annee,
        inscription__classe__etablissement=etab,
    ).exclude(inscription__statut='ABANDON')

    stats = {n: tous.filter(niveau=n).count() for n in RisqueDecrochage.NiveauChoices.values}
    stats['total'] = tous.count()

    return render(request, 'pedagogie/risque_decrochage.html', {
        'risques': risques_qs,
        'annee': annee,
        'annees': annees,
        'classes': classes,
        'niveau_filtre': niveau_filtre,
        'classe_id': classe_id,
        'stats': stats,
        'niveaux': RisqueDecrochage.NiveauChoices.choices,
    })


# ─── PDF RISQUE DE DÉCROCHAGE ───────────────────────────────────────────

def risque_decrochage_pdf(request):
    """Génère un PDF de la liste des élèves à risque de décrochage."""
    try:
        from weasyprint import HTML
    except ImportError:
        messages.error(request, "WeasyPrint n'est pas installé sur le serveur.")
        return redirect('pedagogie:risque_decrochage')

    etab = getattr(request.user, 'etablissement', None)
    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else AnneeScolaire.objects.filter(est_courante=True).first()

    niveau_filtre = request.GET.get('niveau')
    classe_id = request.GET.get('classe')

    risques_qs = RisqueDecrochage.objects.filter(
        inscription__annee_scolaire=annee,
        inscription__classe__etablissement=etab,
    ).exclude(inscription__statut='ABANDON').select_related(
        'inscription__eleve', 'inscription__classe'
    ).order_by('-score')

    if niveau_filtre:
        risques_qs = risques_qs.filter(niveau=niveau_filtre)
    if classe_id:
        risques_qs = risques_qs.filter(inscription__classe_id=classe_id)

    tous = RisqueDecrochage.objects.filter(
        inscription__annee_scolaire=annee,
        inscription__classe__etablissement=etab,
    ).exclude(inscription__statut='ABANDON')

    stats = {n: tous.filter(niveau=n).count() for n in RisqueDecrochage.NiveauChoices.values}
    stats['total'] = tous.count()

    risques = []
    for r in risques_qs:
        risque_dict = {
            'eleve': r.inscription.eleve,
            'classe': r.inscription.classe,
            'score': r.score,
            'niveau': r.get_niveau_display(),
            'couleur_css': r.couleur_css,
            'facteurs': r.facteurs or [],
            'date_calcul': r.date_calcul,
        }
        risques.append(risque_dict)

    html_content = render_to_string('pedagogie/pdf/risque_decrochage.html', {
        'risques': risques,
        'annee': annee,
        'stats': stats,
        'niveau_filtre': niveau_filtre,
        'classe_id': classe_id,
    })

    pdf_file = HTML(string=html_content).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"risque_decrochage_{annee.libelle.replace(' ', '_') if annee else 'actuel'}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# ═══════════════════════════════════════════════════════════════════
# BULLETIN ANNUEL
# ═══════════════════════════════════════════════════════════════════

def _build_bulletin_annuel_context(request, inscription, annee_scolaire):
    """Construit le contexte pour le bulletin annuel."""
    from django.db.models import Max, Min, Avg
    from datetime import date as _date
    from parametres.models import TypeDocument, SignataireDocument
    from decimal import Decimal

    etab = inscription.classe.etablissement
    etab_context = get_etablissement_context(etab, request)
    cycle = inscription.classe.cycle

    nb_eleves = Inscription.objects.filter(
        classe=inscription.classe,
        annee_scolaire=annee_scolaire
    ).exclude(statut='ABANDON').count()

    # Moyennes par trimestre (pour le récapitulatif) + agrégation annuelle
    trimestres = list(Trimestre.objects.filter(annee_scolaire=annee_scolaire).order_by('numero'))
    mg_map = {
        mg.trimestre_id: mg
        for mg in MoyenneGenerale.objects.filter(inscription=inscription, trimestre__in=trimestres)
    }
    periodes = []
    total_points_annuel = Decimal('0')
    total_coefficients_annuel = Decimal('0')
    for t in trimestres:
        mg = mg_map.get(t.pk)
        if mg:
            if mg.total_points:
                total_points_annuel += mg.total_points
            if mg.total_coefficients:
                total_coefficients_annuel += mg.total_coefficients
        periodes.append({'nom': t.nom, 'moyenne': mg.moyenne if mg else None})

    moyenne_annuelle = None
    if total_coefficients_annuel > 0:
        moyenne_annuelle = (total_points_annuel / total_coefficients_annuel).quantize(Decimal('0.01'))

    from django.db.models import Sum as _Sum

    # Moyenne annuelle de chaque élève actif de la classe (une entrée par élève)
    all_annuals = list(MoyenneGenerale.objects.filter(
        inscription__classe=inscription.classe,
        inscription__annee_scolaire=annee_scolaire,
        trimestre__in=trimestres,
    ).exclude(
        inscription__statut='ABANDON'
    ).values('inscription_id').annotate(
        pts=_Sum('total_points'),
        coef=_Sum('total_coefficients'),
    ))

    avgs_by_ins = {
        row['inscription_id']: Decimal(str(row['pts'])) / Decimal(str(row['coef']))
        for row in all_annuals
        if row['coef']
    }

    all_avgs = list(avgs_by_ins.values())
    moy_max_classe = max(all_avgs) if all_avgs else None
    moy_min_classe = min(all_avgs) if all_avgs else None
    moy_avg_classe = (sum(all_avgs) / len(all_avgs)).quantize(Decimal('0.01')) if all_avgs else None

    nb_admis = sum(1 for m in all_avgs if m >= Decimal('10'))
    taux_reussite = (nb_admis / nb_eleves * 100) if nb_eleves > 0 else 0

    rang_annuel = None
    if moyenne_annuelle:
        rang_annuel = 1 + sum(
            1 for ins_id, moy in avgs_by_ins.items()
            if ins_id != inscription.pk and moy > moyenne_annuelle
        )

    mention = _get_mention(moyenne_annuelle) if moyenne_annuelle else None
    admis = moyenne_annuelle >= Decimal('10') if moyenne_annuelle else False

    type_doc_bulletin = (
        TypeDocument.objects.filter(code__icontains='bulletin', cycle=cycle, actif=True).first()
        or TypeDocument.objects.filter(code__icontains='bulletin', actif=True).first()
    )
    signataire = SignataireDocument.objects.get_signataire(
        cycle=cycle, type_document=type_doc_bulletin, annee_scolaire=annee_scolaire,
    ) if type_doc_bulletin else None
    signataire_membre = signataire.get_membre_personnel() if signataire else None

    today = _date.today()
    mois_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
    lieu = (etab.ville + ', le ') if etab.ville else 'Le '
    date_lieu = f"{lieu}{today.day} {mois_fr[today.month - 1]} {today.year}"

    return {
        'inscription': inscription,
        'annee_scolaire': annee_scolaire,
        'periodes': periodes,
        'moyenne_annuelle': {
            'moyenne_annuelle': moyenne_annuelle,
            'total_points': total_points_annuel,
            'total_points_max': total_coefficients_annuel * 20,
            'total_coefficients': total_coefficients_annuel,
            'rang': rang_annuel,
            'mention': mention,
            'admis': admis,
        },
        'nb_eleves': nb_eleves,
        'moy_max_classe': moy_max_classe,
        'moy_min_classe': moy_min_classe,
        'moy_avg_classe': moy_avg_classe,
        'taux_reussite': taux_reussite,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'signataire': signataire,
        'signataire_membre': signataire_membre,
        'date_lieu': date_lieu,
    }


def _get_mention(moyenne):
    """Retourne la mention selon la moyenne sur 20."""
    if moyenne is None:
        return None
    if moyenne >= 16:
        return "Très Bien"
    elif moyenne >= 14:
        return "Bien"
    elif moyenne >= 12:
        return "Assez Bien"
    elif moyenne >= 10:
        return "Passable"
    else:
        return "Insuffisant"


@login_required
def bulletin_duplicata_pdf(request, inscription_id, trimestre_id):
    """Génère le duplicata PDF du bulletin trimestriel d'un élève."""
    if HTML is None:
        messages.error(request, "L'extension WeasyPrint n'est pas installée sur le serveur.")
        return redirect('pedagogie:classe_result_list')

    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe__cycle', 'annee_scolaire'),
        pk=inscription_id,
    )
    trimestre = get_object_or_404(Trimestre.objects.select_related('annee_scolaire'), pk=trimestre_id)

    from datetime import date as _date
    ctx = _build_bulletin_context(request, inscription, trimestre)
    ctx['is_duplicata'] = True
    ctx['today'] = _date.today()

    html_string = render_to_string('pedagogie/pdf/bulletin_duplicata.html', ctx)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"DUPLICATA_Bulletin_{inscription.eleve.nom}_{trimestre.nom}.pdf".replace(" ", "_")
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def bulletin_annuel_apercu(request, inscription_id):
    """Aperçu HTML du bulletin annuel."""
    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe__cycle', 'annee_scolaire'),
        pk=inscription_id,
    )
    annee_id = request.GET.get('annee')
    if annee_id:
        annee_scolaire = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee_scolaire = inscription.annee_scolaire

    if not annee_scolaire:
        messages.error(request, "Aucune année scolaire trouvée.")
        return redirect('pedagogie:resultat_classe', class_id=inscription.classe_id)

    ctx = _build_bulletin_annuel_context(request, inscription, annee_scolaire)
    ctx['pdf_url'] = request.build_absolute_uri(
        f"/pedagogie/bulletins/{inscription_id}/annuel/pdf/?annee={annee_scolaire.pk}"
    )
    return render(request, 'pedagogie/bulletin_apercu.html', ctx)


@login_required
def bulletin_annuel_pdf(request, inscription_id):
    """Génère le bulletin PDF annuel d'un élève."""
    if HTML is None:
        messages.error(request, "L'extension WeasyPrint n'est pas installée sur le serveur.")
        return redirect('pedagogie:classe_result_list')

    inscription = get_object_or_404(
        Inscription.objects.select_related('eleve', 'classe__cycle', 'annee_scolaire'),
        pk=inscription_id,
    )
    annee_id = request.GET.get('annee')
    if annee_id:
        annee_scolaire = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee_scolaire = inscription.annee_scolaire

    if not annee_scolaire:
        messages.error(request, "Aucune année scolaire trouvée.")
        return redirect('pedagogie:classe_result_list')

    ctx = _build_bulletin_annuel_context(request, inscription, annee_scolaire)
    html_string = render_to_string('pedagogie/pdf/bulletin_annuel.html', ctx)

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Bulletin_Annuel_{inscription.eleve.nom}_{annee_scolaire.libelle.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def bulletin_annuel_classe_batch_pdf(request, class_id):
    """Génère un PDF contenant tous les bulletins annuels d'une classe."""
    if HTML is None:
        messages.error(request, "L'extension WeasyPrint n'est pas installée sur le serveur.")
        return redirect('pedagogie:resultat_classe', class_id=class_id)

    classe = get_object_or_404(Classe, pk=class_id)
    annee_id = request.GET.get('annee')
    if annee_id:
        annee_scolaire = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee_scolaire = AnneeScolaire.objects.filter(est_courante=True).first()

    if not annee_scolaire:
        messages.error(request, "Aucune année scolaire trouvée.")
        return redirect('pedagogie:resultat_classe', class_id=class_id)

    inscriptions = Inscription.objects.select_related(
        'eleve', 'classe__cycle'
    ).filter(classe=classe, annee_scolaire=annee_scolaire).exclude(statut='ABANDON')

    etab = classe.etablissement
    etab_context = get_etablissement_context(etab, request)

    students_data = []
    for ins in inscriptions:
        ctx = _build_bulletin_annuel_context(request, ins, annee_scolaire)
        students_data.append(ctx)

    html_string = render_to_string('pedagogie/pdf/bulletin_annuel_batch.html', {
        'classe': classe,
        'annee_scolaire': annee_scolaire,
        'students_data': students_data,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
    })

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Bulletins_Annuels_{classe.nom}_{annee_scolaire.libelle.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# ── Palmarès annuel ──────────────────────────────────────────────────────────

def _compute_palmares_annuel(classe, annee_scolaire):
    """Calcule le palmarès annuel d'une classe : moyenne, rang et décision du conseil."""
    from decimal import Decimal
    from django.db.models import Sum

    trimestres = list(Trimestre.objects.filter(annee_scolaire=annee_scolaire).order_by('numero'))

    rows = list(
        MoyenneGenerale.objects.filter(
            inscription__classe=classe,
            inscription__annee_scolaire=annee_scolaire,
            trimestre__in=trimestres,
        ).exclude(
            inscription__statut='ABANDON'
        ).values('inscription_id').annotate(
            pts=Sum('total_points'),
            coef=Sum('total_coefficients'),
        )
    )

    avgs_by_ins = {
        row['inscription_id']: Decimal(str(row['pts'])) / Decimal(str(row['coef']))
        for row in rows
        if row['coef']
    }

    # Classement avec ex-aequo
    sorted_avgs = sorted(avgs_by_ins.items(), key=lambda x: x[1], reverse=True)
    rang_by_ins = {}
    current_rank = 0
    current_avg = None
    for i, (ins_id, avg) in enumerate(sorted_avgs, start=1):
        if avg != current_avg:
            current_rank = i
            current_avg = avg
        rang_by_ins[ins_id] = current_rank

    inscriptions = list(
        Inscription.objects.select_related('eleve')
        .filter(classe=classe, annee_scolaire=annee_scolaire)
        .exclude(statut='ABANDON')
        .order_by('eleve__nom', 'eleve__prenom')
    )

    palmares = []
    for ins in inscriptions:
        moyenne = avgs_by_ins.get(ins.pk)
        rang = rang_by_ins.get(ins.pk)
        if moyenne is not None:
            moyenne_q = moyenne.quantize(Decimal('0.01'))
            admis = moyenne_q >= Decimal('10')
            decision = "Admis(e) en classe supérieure" if admis else "Redouble la classe"
        else:
            moyenne_q = None
            admis = None
            decision = "—"
        palmares.append({
            'inscription': ins,
            'eleve': ins.eleve,
            'moyenne': moyenne_q,
            'rang': rang,
            'admis': admis,
            'decision': decision,
        })

    palmares.sort(key=lambda x: (x['rang'] or 9999, x['eleve'].nom))

    nb_eleves = len(inscriptions)
    all_avgs = list(avgs_by_ins.values())
    nb_admis = sum(1 for m in all_avgs if m >= Decimal('10'))
    taux_reussite = round(nb_admis / nb_eleves * 100, 1) if nb_eleves > 0 else 0
    moy_max = max(all_avgs).quantize(Decimal('0.01')) if all_avgs else None
    moy_min = min(all_avgs).quantize(Decimal('0.01')) if all_avgs else None
    moy_avg = (sum(all_avgs) / len(all_avgs)).quantize(Decimal('0.01')) if all_avgs else None

    return {
        'palmares': palmares,
        'nb_eleves': nb_eleves,
        'nb_admis': nb_admis,
        'nb_redoublants': nb_eleves - nb_admis,
        'taux_reussite': taux_reussite,
        'moy_max': moy_max,
        'moy_min': moy_min,
        'moy_avg': moy_avg,
    }


@login_required
def palmares_annuel(request, class_id):
    """Aperçu HTML du palmarès annuel d'une classe."""
    classe = get_object_or_404(
        Classe.objects.select_related('cycle', 'etablissement'), pk=class_id
    )
    annees = AnneeScolaire.objects.order_by('-date_debut')
    annee_id = request.GET.get('annee')
    if annee_id:
        annee_scolaire = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee_scolaire = AnneeScolaire.objects.filter(est_courante=True).first()

    if not annee_scolaire:
        messages.error(request, "Aucune année scolaire trouvée.")
        return redirect('pedagogie:resultat_classe', class_id=class_id)

    data = _compute_palmares_annuel(classe, annee_scolaire)

    from parametres.models import TypeDocument, SignataireDocument
    cycle = classe.cycle
    type_doc = (
        TypeDocument.objects.filter(code__icontains='bulletin', cycle=cycle, actif=True).first()
        or TypeDocument.objects.filter(code__icontains='bulletin', actif=True).first()
    )
    signataire = SignataireDocument.objects.get_signataire(
        cycle=cycle, type_document=type_doc, annee_scolaire=annee_scolaire,
    ) if type_doc else None
    signataire_membre = signataire.get_membre_personnel() if signataire else None

    return render(request, 'pedagogie/palmares_annuel.html', {
        'classe': classe,
        'annee_scolaire': annee_scolaire,
        'annees': annees,
        'signataire': signataire,
        'signataire_membre': signataire_membre,
        **data,
    })


@login_required
def palmares_annuel_pdf(request, class_id):
    """Génère le palmarès annuel d'une classe en PDF via WeasyPrint."""
    if HTML is None:
        messages.error(request, "L'extension WeasyPrint n'est pas installée sur le serveur.")
        return redirect('pedagogie:resultat_classe', class_id=class_id)

    classe = get_object_or_404(
        Classe.objects.select_related('cycle', 'etablissement'), pk=class_id
    )
    annee_id = request.GET.get('annee')
    if annee_id:
        annee_scolaire = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee_scolaire = AnneeScolaire.objects.filter(est_courante=True).first()

    if not annee_scolaire:
        messages.error(request, "Aucune année scolaire trouvée.")
        return redirect('pedagogie:resultat_classe', class_id=class_id)

    from datetime import date as _date
    from parametres.models import TypeDocument, SignataireDocument
    etab = classe.etablissement
    etab_context = get_etablissement_context(etab, request)
    data = _compute_palmares_annuel(classe, annee_scolaire)

    cycle = classe.cycle
    type_doc = (
        TypeDocument.objects.filter(code__icontains='bulletin', cycle=cycle, actif=True).first()
        or TypeDocument.objects.filter(code__icontains='bulletin', actif=True).first()
    )
    signataire = SignataireDocument.objects.get_signataire(
        cycle=cycle, type_document=type_doc, annee_scolaire=annee_scolaire,
    ) if type_doc else None
    signataire_membre = signataire.get_membre_personnel() if signataire else None

    today = _date.today()
    mois_fr = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
               'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
    lieu = (etab.ville + ', le ') if etab.ville else 'Le '
    date_lieu = f"{lieu}{today.day} {mois_fr[today.month - 1]} {today.year}"

    ctx = {
        'classe': classe,
        'annee_scolaire': annee_scolaire,
        'identite': etab_context.get('identite'),
        'logo_url': etab_context.get('logo_url'),
        'etab_logo_url': etab_context.get('etab_logo_url'),
        'etablissement': etab,
        'date_lieu': date_lieu,
        'signataire': signataire,
        'signataire_membre': signataire_membre,
        **data,
    }

    html_string = render_to_string('pedagogie/pdf/palmares_annuel.html', ctx)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Palmares_{classe.nom}_{annee_scolaire.libelle.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


# ─── Cahier de textes ─────────────────────────────────────────────────────────

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
                personnel=request.user,
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
        enseignements = enseignements.filter(personnel=request.user)

    entrees = CahierTextes.objects.filter(
        enseignement__classe=classe,
        enseignement__annee_scolaire=annee,
    ).select_related(
        'enseignement__matiere', 'enseignement__personnel', 'redige_par'
    ).order_by('-date', '-created_at') if annee else CahierTextes.objects.none()

    if enseignement_id:
        entrees = entrees.filter(enseignement_id=enseignement_id)

    if request.user.role == 'ENSEIGNANT':
        entrees = entrees.filter(enseignement__personnel=request.user)

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
        enseignements = enseignements.filter(personnel=request.user)

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
        enseignements = enseignements.filter(personnel=request.user)

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


# ─────────────────────────────────────────────────────────────────────────────
# Prédiction de réussite aux examens officiels
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def prediction_index(request):
    """Sélecteur de classe pour la prédiction de réussite."""
    from etablissements.models import Etablissement
    etab = Etablissement.objects.first()
    annee_courante = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None
    classes = (
        Classe.objects.filter(etablissement=etab, actif=True)
        .select_related('cycle')
        .order_by('cycle__ordre', 'nom')
    ) if etab else Classe.objects.none()

    cycles_examens = ['Post-primaire', 'Secondaire', 'Primaire']
    classes_avec_examen = [
        c for c in classes
        if any(x.lower() in (getattr(c.cycle, 'nom', '') or '').lower() for x in cycles_examens)
    ]

    return render(request, 'pedagogie/prediction_index.html', {
        'classes': classes_avec_examen,
        'annee': annee_courante,
        'toutes_classes': classes,
    })


@login_required
def prediction_classe(request, class_id):
    """Vue des prédictions de réussite pour toute une classe."""
    from etablissements.models import Etablissement
    classe = get_object_or_404(Classe, pk=class_id)
    etab = Etablissement.objects.first()
    annee_courante = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    predictions = (
        PredictionReussiteExamen.objects
        .filter(
            inscription__classe=classe,
            inscription__annee_scolaire=annee_courante,
        )
        .select_related('inscription__eleve')
        .order_by('-score')
    )

    return render(request, 'pedagogie/prediction_classe.html', {
        'classe': classe,
        'annee': annee_courante,
        'predictions': predictions,
        'nb_bon':      predictions.filter(pronostic='BON').count(),
        'nb_moyen':    predictions.filter(pronostic='MOYEN').count(),
        'nb_risque':   predictions.filter(pronostic='RISQUE').count(),
        'nb_critique': predictions.filter(pronostic='CRITIQUE').count(),
        'nb_total':    predictions.count(),
    })


@login_required
@require_POST
def prediction_calculer(request, class_id):
    """Lance le calcul (ou recalcul) des prédictions pour toute la classe."""
    from etablissements.models import Etablissement
    from .predictions import calculer_predictions_classe
    classe = get_object_or_404(Classe, pk=class_id)
    etab = Etablissement.objects.first()
    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    resultats = calculer_predictions_classe(classe, annee)
    messages.success(request, f"{len(resultats)} prédiction(s) calculée(s) pour {classe.nom}.")
    return redirect('pedagogie:prediction_classe', class_id=class_id)


@login_required
def prediction_classe_pdf(request, class_id):
    """Rapport PDF de prédiction pour le conseil de classe."""
    if HTML is None:
        messages.error(request, "WeasyPrint n'est pas disponible.")
        return redirect('pedagogie:prediction_classe', class_id=class_id)

    from etablissements.models import Etablissement
    classe = get_object_or_404(Classe, pk=class_id)
    etab = Etablissement.objects.first()
    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None
    etab_ctx = get_etablissement_context(etab, request) if etab else {}

    predictions = (
        PredictionReussiteExamen.objects
        .filter(inscription__classe=classe, inscription__annee_scolaire=annee)
        .select_related('inscription__eleve')
        .order_by('-score')
    )

    html_str = render_to_string('pedagogie/prediction_classe_pdf.html', {
        'classe': classe,
        'annee': annee,
        'predictions': predictions,
        'etablissement': etab,
        'identite': etab_ctx.get('identite'),
    }, request=request)

    pdf = HTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()
    filename = f"Predictions_{classe.nom}_{annee.libelle if annee else ''}.pdf".replace(' ', '_')
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{filename}"'
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Bulletins de compétences (Préscolaire / Primaire)
# ─────────────────────────────────────────────────────────────────────────────

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
    }, request=request)

    pdf = HTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()
    eleve = inscription.eleve
    nom = f"Bulletin_{eleve.nom}_{eleve.prenom}_{trimestre.numero}.pdf".replace(' ', '_')
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{nom}"'
    return resp
