"""Résultats de classe : bilans périodiques, moyennes, relevés, fiches discipline.

Issu du découpage mécanique de ``pedagogie/views.py`` (octobre 2026) : code inchangé.
"""
import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
logger = logging.getLogger(__name__)
from ..models import Enseignement, Evaluation, Note, Resultat, MoyenneGenerale, Trimestre
from ..utils import CalculateurMoyenne
from parametres.models import AnneeScolaire, Classe
from inscriptions.models import Inscription
from core.utils import get_etablissement_context
from licences.decorators import requires_licence_feature
from .commun import HTML, _pdf_licence_info


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


@login_required
@requires_licence_feature('rapports_avances')
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
        'licence_info':      _pdf_licence_info(request, etab),
        'etablissement':     etab,
    }, request=request)

    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    label = annee.libelle.replace(' ', '_').replace('/', '-') if annee else 'bilan'
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="bilan_{label}.pdf"'
    return response


@login_required
@requires_licence_feature('rapports_avances')
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
        'licence_info': _pdf_licence_info(request, etab),
        'etablissement': etab,
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
        'licence_info':  _pdf_licence_info(request, etab),
        'etablissement': etab,
    }, request=request)

    if HTML is None:
        return HttpResponse("WeasyPrint non disponible.", status=500)

    buffer = __import__('io').BytesIO()
    HTML(string=html_str).write_pdf(buffer)
    nom = f"Moyennes_{classe.nom}_{trimestre.nom}_{annee.libelle}.pdf".replace(' ', '_')
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{nom}"'
    return response


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
        'licence_info': _pdf_licence_info(request, etab),
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
        'licence_info': _pdf_licence_info(request, etab),
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
