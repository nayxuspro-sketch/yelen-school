"""Vues de synthèse périodique et d'analyse des résultats scolaires."""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from licences.decorators import requires_licence_feature
from parametres.models import AnneeScolaire, Classe
from inscriptions.models import Inscription, StatutInscriptionChoices
from ..models import MoyenneGenerale, Trimestre
from ..notes_access import filtrer_inscriptions_autorisees_notes
from yelen_school.cycle_filter import filtrer_classe_par_cycle

logger = logging.getLogger(__name__)


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
            .exclude(statut=StatutInscriptionChoices.ABANDON)
            .values('classe')
            .annotate(n=Count('pk'))
            .values('n')
        )
        classes = classes.annotate(nb_eleves=Subquery(nb_sub))

    classes = filtrer_classe_par_cycle(classes, request)

    return render(request, 'pedagogie/classe_result_list.html', {
        'classes': classes,
        'annee_courante': annee_courante,
    })


@login_required
@requires_licence_feature('rapports_avances')
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
    classes_qs = filtrer_classe_par_cycle(Classe.objects.filter(pk__in=[c.pk for c in classes]), request)
    classes = list(classes_qs)

    inscriptions_autorisees = filtrer_inscriptions_autorisees_notes(
        Inscription.objects.filter(
            annee_scolaire=annee, classe__in=classes_qs,
        ).exclude(statut=StatutInscriptionChoices.ABANDON).select_related('classe')
    ) if annee else []

    # Une seule requête pour toutes les stats (classe × trimestre), après exclusion des inscriptions bloquées.
    mg_stats = (
        MoyenneGenerale.objects
        .filter(trimestre__in=trimestres, inscription__in=inscriptions_autorisees)
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
@requires_licence_feature('ia_predictive')
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
        from ..utils_ia import generer_analyse_bilan
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
