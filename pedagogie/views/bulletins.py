"""Bulletins trimestriels et annuels, palmarès.

Issu du découpage mécanique de ``pedagogie/views.py`` (octobre 2026) : code inchangé.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from ..models import Resultat, MoyenneGenerale, Trimestre, Competence, EvaluationCompetence
from parametres.models import AnneeScolaire, Classe
from inscriptions.models import Inscription
from core.utils import get_etablissement_context
from licences.decorators import requires_licence_feature
from .commun import HTML, _pdf_licence_info


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
    from ..utils_ia import generer_commentaire_eleve

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

    ctx_base = {
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
    # P2 — filigrane licence
    ctx_base['licence_info'] = _pdf_licence_info(request, etab)
    return ctx_base


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
    from ..utils_ia import generer_commentaire_eleve
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
        'licence_info': _pdf_licence_info(request, etab),
    })
    
    # 3. Générer le PDF
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Bulletins_{classe.nom}_{trimestre.nom}.pdf".replace(" ", "_")
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response


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

    ctx_annuel = {
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
    ctx_annuel['licence_info'] = _pdf_licence_info(request, etab)
    return ctx_annuel


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
        'licence_info': _pdf_licence_info(request, etab),
    })

    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Bulletins_Annuels_{classe.nom}_{annee_scolaire.libelle.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


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
@requires_licence_feature('rapports_avances')
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
@requires_licence_feature('rapports_avances')
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
        'licence_info': _pdf_licence_info(request, etab),
        **data,
    }

    html_string = render_to_string('pedagogie/pdf/palmares_annuel.html', ctx)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Palmares_{classe.nom}_{annee_scolaire.libelle.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
