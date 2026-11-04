"""Pointage du personnel (journée, feuille mensuelle) et entretien annuel d'évaluation."""
import logging
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.utils import get_etablissement_context
from licences.decorators import requires_licence_feature
from parametres.models import AnneeScolaire

from ..models import EvaluationAnnuelle, MembrePersonnel, PointagePersonnel, ProfilPointage, ReglagePointage

logger = logging.getLogger(__name__)


def _etab(request):
    return getattr(request.user, 'etablissement', None)


def _membres_actifs(etab):
    """Agents actifs de l'établissement, dans l'ordre alphabétique."""
    return MembrePersonnel.objects.filter(etablissement=etab, is_active=True).order_by('nom', 'prenom')


def _heure(valeur):
    """Heure « HH:MM » du formulaire → ``time`` (None si vide ou illisible)."""
    try:
        return datetime.strptime((valeur or '').strip(), '%H:%M').time()
    except ValueError:
        return None


def _date(valeur, defaut=None):
    try:
        return date.fromisoformat((valeur or '').strip())
    except ValueError:
        return defaut


# ═══════════════════════════════════════════════════════════════════
# POINTAGE
# ═══════════════════════════════════════════════════════════════════

@login_required
@requires_licence_feature('gestion_personnel')
def pointage_jour(request):
    """Pointage d'une journée en deux plages (matin, après-midi) et horaires de référence par profil et par agent ;
    statut déduit de l'heure limite propre à l'agent, sur sa première arrivée de la journée (5.54.0)."""
    etab = _etab(request)
    reglage = ReglagePointage.pour(etab)
    jour = _date(request.GET.get('date') or request.POST.get('date'), timezone.localdate())
    membres = list(_membres_actifs(etab))
    pointages = {p.personnel_id: p for p in PointagePersonnel.objects.filter(personnel__in=membres, date=jour)}

    if request.method == 'POST':
        action = request.POST.get('action') or ''

        if action in ('horaires', 'limite'):      # « limite » : ancien bouton, conservé
            _enregistrer_horaires_etablissement(request, reglage)
            return redirect(f"{request.path}?date={jour.isoformat()}")

        if action == 'horaires_agents':
            modifies = 0
            for membre in membres:
                champ_limite = request.POST.get(f'limite_{membre.pk}')
                champ_depart = request.POST.get(f'depart_prevu_{membre.pk}')
                if champ_limite is None and champ_depart is None:
                    continue
                change = False
                limite = _heure(champ_limite)
                if limite != membre.heure_arrivee_limite:
                    membre.heure_arrivee_limite = limite
                    change = True
                depart = _heure(champ_depart)
                if depart != membre.heure_depart_normale:
                    membre.heure_depart_normale = depart
                    change = True
                if change:
                    membre.save(update_fields=['heure_arrivee_limite', 'heure_depart_normale', 'updated_at'])
                    modifies += 1
            messages.success(request, f"Horaires de {modifies} agent{'s' if modifies > 1 else ''} enregistré"
                                      f"{'s' if modifies > 1 else ''}.")
            return redirect(f"{request.path}?date={jour.isoformat()}")

        enregistres = 0
        for membre in membres:
            arrivee = _heure(request.POST.get(f'arrivee_{membre.pk}'))
            depart = _heure(request.POST.get(f'depart_{membre.pk}'))
            arrivee_pm = _heure(request.POST.get(f'arrivee_pm_{membre.pk}'))
            depart_pm = _heure(request.POST.get(f'depart_pm_{membre.pk}'))
            statut = request.POST.get(f'statut_{membre.pk}') or ''
            if not (arrivee or depart or arrivee_pm or depart_pm or statut):
                continue                      # ligne laissée vide : rien n'est enregistré
            statut = statut if statut in PointagePersonnel.StatutChoices.values else \
                PointagePersonnel.statut_depuis(arrivee or arrivee_pm, membre.heure_limite_pointage(reglage))
            PointagePersonnel.objects.update_or_create(
                personnel=membre, date=jour,
                defaults={'heure_arrivee': arrivee, 'heure_depart': depart,
                          'heure_arrivee_apres_midi': arrivee_pm, 'heure_depart_apres_midi': depart_pm,
                          'statut': statut,
                          'observation': (request.POST.get(f'observation_{membre.pk}') or '')[:200]},
            )
            enregistres += 1
        messages.success(request, f"{enregistres} pointage{'s' if enregistres > 1 else ''} enregistré"
                                  f"{'s' if enregistres > 1 else ''} pour le {jour:%d/%m/%Y}.")
        return redirect(f"{request.path}?date={jour.isoformat()}")

    lignes = []
    for membre in membres:
        pointage = pointages.get(membre.pk)
        depart_normal = membre.heure_depart_pointage(reglage)
        lignes.append({
            'membre': membre,
            'pointage': pointage,
            'limite': membre.heure_limite_pointage(reglage),
            'depart_normal': depart_normal,
            'en_retard': pointage is not None and pointage.statut == PointagePersonnel.StatutChoices.RETARD,
            'depart_anticipe': pointage is not None and pointage.est_depart_anticipe(depart_normal),
            'heures': pointage.heures_travaillees if pointage else 0.0,
        })

    return render(request, 'personnel/pointage_jour.html', {
        'lignes': lignes,
        'jour': jour,
        'veille': jour - timedelta(days=1),
        'lendemain': jour + timedelta(days=1),
        'reglage': reglage,
        'statuts': PointagePersonnel.StatutChoices.choices,
        'profils': ProfilPointage.choices,
        'today': timezone.localdate(),
    })


def _enregistrer_horaires_etablissement(request, reglage):
    """Enregistre les heures de référence de l'établissement et celles de chaque profil (vides = héritage)."""
    champs = {
        'heure_arrivee_limite': request.POST.get('heure_arrivee_limite'),
        'heure_arrivee_limite_enseignant': request.POST.get('heure_arrivee_limite_enseignant'),
        'heure_arrivee_limite_administration': request.POST.get('heure_arrivee_limite_administration'),
        'heure_depart_normale': request.POST.get('heure_depart_normale'),
        'heure_depart_normale_enseignant': request.POST.get('heure_depart_normale_enseignant'),
        'heure_depart_normale_administration': request.POST.get('heure_depart_normale_administration'),
    }
    if champs['heure_arrivee_limite'] is None:
        champs.pop('heure_arrivee_limite')                 # formulaire partiel : on ne touche pas au défaut
    modifiees = []
    for champ, valeur in champs.items():
        if valeur is None:
            continue
        heure = _heure(valeur)
        if champ == 'heure_arrivee_limite' and heure is None:
            messages.error(request, "Heure d'arrivée limite de l'établissement invalide.")
            continue
        if getattr(reglage, champ) != heure:
            setattr(reglage, champ, heure)
            modifiees.append(champ)
    if modifiees:
        reglage.save(update_fields=modifiees + ['updated_at'])
        messages.success(request, "Horaires de référence de l'établissement enregistrés.")
    elif not messages.get_messages(request):
        messages.info(request, "Aucune modification d'horaire à enregistrer.")


@login_required
@requires_licence_feature('gestion_personnel')
def pointage_mois(request):
    """Feuille de pointage du mois : jours pointés, retards, absences et heures par agent, et PDF signé."""
    etab = _etab(request)
    reglage = ReglagePointage.pour(etab)
    today = timezone.localdate()
    try:
        mois = int(request.GET.get('mois') or today.month)
        annee = int(request.GET.get('annee') or today.year)
        debut = date(annee, mois, 1)
    except (TypeError, ValueError):
        debut = date(today.year, today.month, 1)
    fin = (debut.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    membres = list(_membres_actifs(etab))
    pointages = (PointagePersonnel.objects
                 .filter(personnel__in=membres, date__gte=debut, date__lte=fin)
                 .select_related('personnel'))
    par_membre = {}
    for pointage in pointages:
        ligne = par_membre.setdefault(pointage.personnel_id, {'jours': 0, 'retards': 0, 'absences': 0,
                                                              'conges': 0, 'heures': 0.0,
                                                              'departs_anticipes': 0})
        ligne['jours'] += 1
        ligne['heures'] += pointage.heures_travaillees
        if pointage.est_depart_anticipe(pointage.personnel.heure_depart_pointage(reglage)):
            ligne['departs_anticipes'] += 1
        if pointage.statut == PointagePersonnel.StatutChoices.RETARD:
            ligne['retards'] += 1
        elif pointage.statut == PointagePersonnel.StatutChoices.ABSENT:
            ligne['absences'] += 1
        elif pointage.statut == PointagePersonnel.StatutChoices.CONGE:
            ligne['conges'] += 1

    lignes = [{'membre': membre, **par_membre.get(membre.pk, {'jours': 0, 'retards': 0, 'absences': 0,
                                                             'conges': 0, 'heures': 0.0,
                                                             'departs_anticipes': 0})}
              for membre in membres]
    totaux = {cle: sum(ligne[cle] for ligne in lignes)
              for cle in ('jours', 'retards', 'absences', 'conges', 'heures', 'departs_anticipes')}

    return render(request, 'personnel/pointage_mois.html', {
        'lignes': lignes,
        'totaux': totaux,
        'debut': debut,
        'fin': fin,
        'mois': mois,
        'annee': annee,
        'mois_precedent': (debut - timedelta(days=1)).replace(day=1),
        'mois_suivant': fin + timedelta(days=1),
    })


@login_required
@requires_licence_feature('gestion_personnel')
def pointage_mois_pdf(request):
    """Feuille de pointage mensuelle du personnel (A4 portrait, signée)."""
    from core.pdf import HTML as WeasyPrint

    etab = _etab(request)
    reglage = ReglagePointage.pour(etab)
    today = timezone.localdate()
    try:
        mois = int(request.GET.get('mois') or today.month)
        annee = int(request.GET.get('annee') or today.year)
        debut = date(annee, mois, 1)
    except (TypeError, ValueError):
        debut = date(today.year, today.month, 1)
    fin = (debut.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    membres = list(_membres_actifs(etab))
    pointages = (PointagePersonnel.objects
                 .filter(personnel__in=membres, date__gte=debut, date__lte=fin)
                 .select_related('personnel'))
    par_membre = {}
    for pointage in pointages:
        ligne = par_membre.setdefault(pointage.personnel_id, {'jours': 0, 'retards': 0, 'absences': 0,
                                                              'conges': 0, 'heures': 0.0,
                                                              'departs_anticipes': 0})
        ligne['jours'] += 1
        ligne['heures'] += pointage.heures_travaillees
        if pointage.est_depart_anticipe(pointage.personnel.heure_depart_pointage(reglage)):
            ligne['departs_anticipes'] += 1
        if pointage.statut == PointagePersonnel.StatutChoices.RETARD:
            ligne['retards'] += 1
        elif pointage.statut == PointagePersonnel.StatutChoices.ABSENT:
            ligne['absences'] += 1
        elif pointage.statut == PointagePersonnel.StatutChoices.CONGE:
            ligne['conges'] += 1
    lignes = [{'membre': membre, **par_membre.get(membre.pk, {'jours': 0, 'retards': 0, 'absences': 0,
                                                             'conges': 0, 'heures': 0.0,
                                                             'departs_anticipes': 0})}
              for membre in membres]
    totaux = {cle: sum(ligne[cle] for ligne in lignes)
              for cle in ('jours', 'retards', 'absences', 'conges', 'heures', 'departs_anticipes')}

    etab_ctx = get_etablissement_context(etab, request)
    html = render_to_string('personnel/pdf/feuille_pointage.html', {
        'lignes': lignes, 'totaux': totaux, 'debut': debut, 'fin': fin, 'today': today, 'etab': etab,
        'identite': etab_ctx.get('identite'),
        'logo_url': etab_ctx.get('logo_url') or etab_ctx.get('etab_logo_url'),
    }, request=request)
    pdf = WeasyPrint(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="pointage_{debut:%Y-%m}.pdf"'
    return response


# ═══════════════════════════════════════════════════════════════════
# ÉVALUATION ANNUELLE
# ═══════════════════════════════════════════════════════════════════

@login_required
@requires_licence_feature('gestion_personnel')
def evaluation_list(request):
    """Évaluations annuelles de l'établissement pour l'année scolaire choisie, et agents restant à évaluer."""
    etab = _etab(request)
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_sel = (annees.filter(pk=request.GET.get('annee')).first() if request.GET.get('annee')
                 else annees.filter(est_courante=True).first() or annees.first())

    evaluations = (EvaluationAnnuelle.objects
                   .filter(personnel__etablissement=etab,
                           **({'annee_scolaire': annee_sel} if annee_sel else {}))
                   .select_related('personnel', 'annee_scolaire', 'evaluateur')
                   .order_by('-date_entretien'))
    evalues = {e.personnel_id for e in evaluations}
    a_evaluer = [m for m in _membres_actifs(etab) if m.pk not in evalues]

    return render(request, 'personnel/evaluation_list.html', {
        'evaluations': evaluations,
        'a_evaluer': a_evaluer,
        'annees': annees,
        'annee_sel': annee_sel,
    })


@login_required
@requires_licence_feature('gestion_personnel')
def evaluation_form(request, pk=None):
    """Saisie (ou reprise) de l'entretien annuel d'évaluation d'un agent."""
    etab = _etab(request)
    evaluation = (get_object_or_404(EvaluationAnnuelle.objects.select_related('personnel', 'annee_scolaire'),
                                    pk=pk, personnel__etablissement=etab) if pk else None)
    membres = _membres_actifs(etab)
    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first() or annees.first()
    erreur = None

    if request.method == 'POST':
        personnel = get_object_or_404(MembrePersonnel, pk=request.POST.get('personnel'), etablissement=etab)
        annee = get_object_or_404(AnneeScolaire, pk=request.POST.get('annee_scolaire'), etablissement=etab)
        date_entretien = _date(request.POST.get('date_entretien'), timezone.localdate())
        evaluateur = MembrePersonnel.objects.filter(pk=request.POST.get('evaluateur') or None,
                                                    etablissement=etab).first()
        notes = {}
        for champ, libelle in EvaluationAnnuelle.CRITERES:
            try:
                note = int(request.POST.get(champ) or 0)
            except ValueError:
                note = -1
            if not 0 <= note <= 5:
                erreur = f"La note « {libelle} » doit être comprise entre 0 et 5."
                break
            notes[champ] = note
        if erreur is None and EvaluationAnnuelle.objects.filter(
                personnel=personnel, annee_scolaire=annee).exclude(pk=pk).exists():
            erreur = f"{personnel.get_nom_complet()} a déjà une évaluation pour {annee.libelle}."
        if erreur is None:
            evaluation = evaluation or EvaluationAnnuelle(personnel=personnel, annee_scolaire=annee)
            evaluation.personnel = personnel
            evaluation.annee_scolaire = annee
            evaluation.date_entretien = date_entretien
            evaluation.evaluateur = evaluateur
            for champ, note in notes.items():
                setattr(evaluation, champ, note)
            evaluation.bilan = (request.POST.get('bilan') or '').strip()
            evaluation.objectifs = (request.POST.get('objectifs') or '').strip()
            evaluation.avis = (request.POST.get('avis') if request.POST.get('avis') in
                               EvaluationAnnuelle.AvisChoices.values else EvaluationAnnuelle.AvisChoices.FAVORABLE)
            evaluation.save()
            messages.success(request, f"Évaluation de {personnel.get_nom_complet()} enregistrée "
                                      f"({evaluation.moyenne_sur_20:.2f}/20).")
            return redirect('personnel:evaluation_list')

    return render(request, 'personnel/evaluation_form.html', {
        'evaluation': evaluation,
        'membres': membres,
        'annees': annees,
        'annee_courante': annee_courante,
        'criteres': EvaluationAnnuelle.CRITERES,
        'criteres_notes': [(champ, libelle, getattr(evaluation, champ) if evaluation else 3)
                           for champ, libelle in EvaluationAnnuelle.CRITERES],
        'avis_choices': EvaluationAnnuelle.AvisChoices.choices,
        'notes_possibles': range(0, 6),
        'today': timezone.localdate(),
        'erreur': erreur,
    })


@login_required
@requires_licence_feature('gestion_personnel')
def evaluation_pdf(request, pk):
    """Compte rendu d'entretien annuel (A4 portrait, signé) remis à l'agent."""
    from core.pdf import HTML as WeasyPrint

    etab = _etab(request)
    evaluation = get_object_or_404(
        EvaluationAnnuelle.objects.select_related('personnel', 'annee_scolaire', 'evaluateur'),
        pk=pk, personnel__etablissement=etab,
    )
    etab_ctx = get_etablissement_context(etab, request)
    html = render_to_string('personnel/pdf/evaluation_annuelle.html', {
        'evaluation': evaluation,
        'membre': evaluation.personnel,
        'annee_scolaire': evaluation.annee_scolaire,
        'today': timezone.localdate(),
        'etab': etab,
        'identite': etab_ctx.get('identite'),
        'logo_url': etab_ctx.get('logo_url') or etab_ctx.get('etab_logo_url'),
    }, request=request)
    pdf = WeasyPrint(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="evaluation_{evaluation.personnel.nom}_{evaluation.annee_scolaire.libelle}.pdf"'
        .replace(' ', '_'))
    return response


@login_required
@require_POST
@requires_licence_feature('gestion_personnel')
def evaluation_delete(request, pk):
    """Supprime une évaluation saisie par erreur (la direction seule, action tracée dans l'audit)."""
    etab = _etab(request)
    evaluation = get_object_or_404(EvaluationAnnuelle, pk=pk, personnel__etablissement=etab)
    nom = evaluation.personnel.get_nom_complet()
    evaluation.delete()
    messages.success(request, f"Évaluation de {nom} supprimée.")
    return redirect('personnel:evaluation_list')
