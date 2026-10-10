"""Risque de décrochage et prédictions.

Issu du découpage mécanique de ``pedagogie/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from ..models import RisqueDecrochage, PredictionReussiteExamen
from parametres.models import AnneeScolaire, Classe
from inscriptions.models import Inscription
from core.utils import get_etablissement_context
from licences.decorators import requires_licence_feature
from .commun import HTML, _pdf_licence_info


@login_required
@requires_licence_feature('rapports_avances')
def risque_decrochage(request):
    """
    Tableau de bord des élèves à risque de décrochage scolaire.

    Affiche les scores calculés (par `calculer_risques`) avec filtres
    par niveau de risque et par classe. Permet aussi de recalculer
    manuellement le score d'un seul élève via POST.
    """
    from ..utils_ia import calculer_score_risque

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
                    response = render(request, 'pedagogie/partials/risque_row.html', {
                        'r': risque,
                        'annee': annee,
                    })
                    response['HX-Trigger'] = 'risqueUpdated'
                    return response
                
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

    context = {
        'risques': risques_qs,
        'annee': annee,
        'annees': annees,
        'classes': classes,
        'niveau_filtre': niveau_filtre,
        'classe_id': classe_id,
        'stats': stats,
        'niveaux': RisqueDecrochage.NiveauChoices.choices,
    }
    if request.headers.get('HX-Request') and request.GET.get('_partial') == 'stats':
        return render(request, 'pedagogie/partials/risque_stats.html', context)

    return render(request, 'pedagogie/risque_decrochage.html', context)


@login_required
@requires_licence_feature('rapports_avances')
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
        'licence_info': _pdf_licence_info(request, etab),
        'etablissement': etab,
    })

    pdf_file = HTML(string=html_content).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"risque_decrochage_{annee.libelle.replace(' ', '_') if annee else 'actuel'}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
@requires_licence_feature('ia_predictive')
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
@requires_licence_feature('ia_predictive')
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
@requires_licence_feature('ia_predictive')
@require_POST
def prediction_calculer(request, class_id):
    """Lance le calcul (ou recalcul) des prédictions pour toute la classe."""
    from etablissements.models import Etablissement
    from ..predictions import calculer_predictions_classe
    classe = get_object_or_404(Classe, pk=class_id)
    etab = Etablissement.objects.first()
    annee = AnneeScolaire.objects.filter(
        etablissement=etab, est_courante=True
    ).first() if etab else None

    resultats = calculer_predictions_classe(classe, annee)
    messages.success(request, f"{len(resultats)} prédiction(s) calculée(s) pour {classe.nom}.")
    return redirect('pedagogie:prediction_classe', class_id=class_id)


@login_required
@requires_licence_feature('ia_predictive')
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
        'licence_info': _pdf_licence_info(request, etab),
    }, request=request)

    pdf = HTML(string=html_str, base_url=request.build_absolute_uri()).write_pdf()
    filename = f"Predictions_{classe.nom}_{annee.libelle if annee else ''}.pdf".replace(' ', '_')
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="{filename}"'
    return resp
