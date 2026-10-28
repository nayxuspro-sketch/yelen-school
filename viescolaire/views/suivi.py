"""Fiche de suivi individuelle, capital points et configuration discipline."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from django.contrib import messages

from parametres.models import AnneeScolaire, Classe
from pedagogie.models import Trimestre, MoyenneGenerale
from inscriptions.models import Inscription, StatutInscriptionChoices
from ..models import (
    DecisionConseil, SanctionDisciplinaire,
    ParticipationActivite,
    ConfigDiscipline,
)
from .commun import _get_etab


# ─── Fiche de suivi individuelle ──────────────────────────────────────────────

@login_required
def fiche_suivi_eleve(request, inscription_id):
    """
    Vue unifiee : presences + notes + sanctions + retards + activites
    pour un eleve donne (scope : une inscription = annee + eleve + classe).
    """
    from presences.models import Presence
    from pedagogie.models import Resultat

    inscription = get_object_or_404(
        Inscription.objects.select_related(
            'eleve', 'classe', 'annee_scolaire', 'statut_eleve'
        ),
        pk=inscription_id,
        classe__etablissement=_get_etab(request),
    )

    # ── 1. Presences ──────────────────────────────────────────────────────────
    presences_qs = (
        Presence.objects
        .filter(inscription=inscription)
        .select_related('appel__matiere')
        .order_by('-appel__date')
    )
    nb_absences     = presences_qs.filter(statut='ABSENT').count()
    nb_retards      = presences_qs.filter(statut='RETARD').count()
    nb_excuses      = presences_qs.filter(statut='EXCUSE').count()
    nb_presents     = presences_qs.filter(statut='PRESENT').count()
    nb_total_appels = presences_qs.count()

    absences  = presences_qs.filter(statut__in=['ABSENT', 'EXCUSE'])
    retards   = presences_qs.filter(statut='RETARD')

    # ── 2. Notes / Resultats ──────────────────────────────────────────────────
    trimestres = (
        Trimestre.objects
        .filter(annee_scolaire=inscription.annee_scolaire)
        .order_by('numero')
    )

    # Moyennes generales par trimestre
    moyennes = (
        MoyenneGenerale.objects
        .filter(inscription=inscription)
        .select_related('trimestre')
        .order_by('trimestre__numero')
    )
    moyennes_par_tri = {mg.trimestre_id: mg for mg in moyennes}

    # Resultats par trimestre
    resultats_qs = (
        Resultat.objects
        .filter(inscription=inscription)
        .select_related('enseignement__matiere', 'trimestre')
        .order_by('trimestre__numero', 'enseignement__matiere__nom')
    )

    resultats_par_tri = {}
    for r in resultats_qs:
        tid = r.trimestre_id
        resultats_par_tri.setdefault(tid, []).append(r)

    periodes = []
    for tri in trimestres:
        periodes.append({
            'trimestre': tri,
            'moyenne': moyennes_par_tri.get(tri.pk),
            'resultats': resultats_par_tri.get(tri.pk, []),
        })

    # ── 3. Sanctions ──────────────────────────────────────────────────────────
    sanctions = (
        SanctionDisciplinaire.objects
        .filter(inscription=inscription)
        .select_related('type_sanction', 'prononcee_par', 'trimestre')
        .order_by('-date_sanction')
    )
    nb_sanctions_actives = sanctions.exclude(statut='ANNULE').count()

    # ── 4. Decisions de conseil ───────────────────────────────────────────────
    decisions = (
        DecisionConseil.objects
        .filter(inscription=inscription)
        .select_related('conseil__trimestre', 'conseil__classe')
        .order_by('-conseil__trimestre__numero')
    )

    # ── 5. Activites parascolaires ────────────────────────────────────────────
    participations = (
        ParticipationActivite.objects
        .filter(inscription=inscription, is_active=True)
        .select_related('activite')
        .order_by('activite__type_activite', 'activite__nom')
    )
    nb_activites = participations.count()

    # ── Onglets (label + badge count) ────────────────────────────────────────
    tabs_def = [
        ('presences',  'Présences & Retards',      nb_absences + nb_retards if (nb_absences + nb_retards) else None),
        ('notes',      'Notes & Résultats',         None),
        ('sanctions',  'Sanctions',                  nb_sanctions_actives if nb_sanctions_actives else None),
        ('conseil',    'Conseil de classe',          decisions.count() or None),
        ('activites',  'Activités parascolaires',   nb_activites if nb_activites else None),
    ]

    # ── 6. Capital points discipline ─────────────────────────────────────────
    etab = getattr(request.user, 'etablissement', None)
    config_disc = ConfigDiscipline.get_or_default(etab) if etab else None
    capital = _calcul_capital_points(inscription, config_disc) if config_disc else None

    return render(request, 'viescolaire/fiche_suivi_eleve.html', {
        'inscription':          inscription,
        'nb_absences':          nb_absences,
        'nb_retards':           nb_retards,
        'nb_excuses':           nb_excuses,
        'nb_presents':          nb_presents,
        'nb_total_appels':      nb_total_appels,
        'absences':             absences,
        'retards':              retards,
        'periodes':             periodes,
        'sanctions':            sanctions,
        'nb_sanctions_actives': nb_sanctions_actives,
        'decisions':            decisions,
        'participations':       participations,
        'tabs_def':             tabs_def,
        'capital':              capital,
        'config_disc':          config_disc,
    })


# ─── Liste / recherche des fiches de suivi ────────────────────────────────────

@login_required
def fiches_suivi_list(request):
    """
    Page de recherche permettant d'acceder a la fiche de suivi
    de n'importe quel eleve de l'etablissement.
    """
    etab = request.user.etablissement
    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    q = request.GET.get('q', '').strip()

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classes = Classe.objects.filter(etablissement=etab, actif=True).order_by('nom')

    inscriptions = (
        Inscription.objects
        .filter(annee_scolaire=annee_sel, classe__etablissement=etab)
        .exclude(statut=StatutInscriptionChoices.ABANDON)
        .select_related('eleve', 'classe', 'statut_eleve')
        .order_by('classe__nom', 'eleve__nom', 'eleve__prenom')
    )

    if classe_id:
        inscriptions = inscriptions.filter(classe_id=classe_id)

    if q:
        from django.db.models import Q
        inscriptions = inscriptions.filter(
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__matricule__icontains=q)
        )

    return render(request, 'viescolaire/fiches_suivi_list.html', {
        'inscriptions': inscriptions,
        'annees': annees,
        'annee_sel': annee_sel,
        'classes': classes,
        'classe_id': classe_id or '',
        'q': q,
    })


# ─── Discipline — helper capital points ───────────────────────────────────────

def _calcul_capital_points(inscription, config):
    """
    Retourne le solde de points de discipline pour une inscription.

    solde = points_depart  +  SUM(sanctions confirmees avec impact)
    Les sanctions avec points < 0 retirent, points > 0 ajoutent.
    """
    from decimal import Decimal
    from django.db.models import Sum

    agg = (
        SanctionDisciplinaire.objects
        .filter(
            inscription=inscription,
            statut=SanctionDisciplinaire.StatutChoices.CONFIRME,
        )
        .exclude(points=0)
        .aggregate(total=Sum('points'))
    )
    total_sanctions = agg['total'] or Decimal('0')
    solde = Decimal(str(config.points_depart)) + total_sanctions
    return {
        'solde': solde,
        'statut': config.statut_solde(solde),
        'points_depart': config.points_depart,
        'total_sanctions': total_sanctions,
    }


# ─── Discipline — configuration ───────────────────────────────────────────────

@login_required
def config_discipline(request):
    """Paramétrer les seuils du système de points de discipline."""
    etab = getattr(request.user, 'etablissement', None)
    if not etab:
        messages.error(request, "Aucun établissement associé à votre compte.")
        return redirect('core:home')

    config = ConfigDiscipline.get_or_default(etab)

    if request.method == 'POST':
        config.points_depart = int(request.POST.get('points_depart', 20))
        config.seuil_alerte = int(request.POST.get('seuil_alerte', 5))
        config.seuil_conseil = int(request.POST.get('seuil_conseil', 2))
        config.seuil_exclusion = int(request.POST.get('seuil_exclusion', 0))
        config.message_alerte = request.POST.get('message_alerte', '').strip()
        config.save()
        messages.success(request, "Configuration de discipline enregistrée.")
        return redirect('viescolaire:config_discipline')

    return render(request, 'viescolaire/config_discipline.html', {'config': config})


# ─── Discipline — tableau de bord capital points ──────────────────────────────

@login_required
def capital_points_list(request):
    """
    Tableau de bord : liste des élèves avec leur solde de points de discipline,
    triés par statut (EXCLUSION → CONSEIL → ALERTE → NORMAL).
    """
    etab = getattr(request.user, 'etablissement', None)
    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')

    annees = AnneeScolaire.objects.filter(etablissement=etab).order_by('-date_debut')
    annee_courante = annees.filter(est_courante=True).first()
    annee_sel = annees.filter(pk=annee_id).first() if annee_id else annee_courante

    classes = Classe.objects.filter(etablissement=etab, actif=True).order_by('nom')

    config = ConfigDiscipline.get_or_default(etab) if etab else None

    inscriptions_qs = (
        Inscription.objects
        .filter(annee_scolaire=annee_sel, classe__etablissement=etab)
        .exclude(statut=StatutInscriptionChoices.ABANDON)
        .select_related('eleve', 'classe')
        .order_by('classe__nom', 'eleve__nom')
    )
    if classe_id:
        inscriptions_qs = inscriptions_qs.filter(classe_id=classe_id)

    # Calcul du solde pour chaque élève
    ORDER = {'EXCLUSION': 0, 'CONSEIL': 1, 'ALERTE': 2, 'NORMAL': 3}
    lignes = []
    for inscr in inscriptions_qs:
        if config:
            cap = _calcul_capital_points(inscr, config)
        else:
            cap = {'solde': 20, 'statut': 'NORMAL', 'points_depart': 20, 'total_sanctions': 0}
        lignes.append({
            'inscription': inscr,
            'solde': cap['solde'],
            'statut': cap['statut'],
            'total_sanctions': cap['total_sanctions'],
        })

    lignes.sort(key=lambda x: ORDER.get(x['statut'], 9))

    nb_exclusion = sum(1 for l in lignes if l['statut'] == 'EXCLUSION')
    nb_conseil   = sum(1 for l in lignes if l['statut'] == 'CONSEIL')
    nb_alerte    = sum(1 for l in lignes if l['statut'] == 'ALERTE')

    return render(request, 'viescolaire/capital_points_list.html', {
        'lignes': lignes,
        'config': config,
        'annees': annees,
        'annee_sel': annee_sel,
        'classes': classes,
        'classe_id': classe_id or '',
        'nb_exclusion': nb_exclusion,
        'nb_conseil': nb_conseil,
        'nb_alerte': nb_alerte,
    })
