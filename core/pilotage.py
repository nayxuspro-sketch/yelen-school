"""Tableau de bord direction : indicateurs de pilotage d'un établissement pour une année scolaire."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Max, Q

ROLES_PILOTAGE = ('SUPER_ADMIN', 'DIRECTEUR_RESEAU', 'DIRECTEUR', 'CENSEUR')
NIVEAUX_RISQUE = ('CRITIQUE', 'ELEVE', 'MODERE', 'FAIBLE')


def _taux(part, total):
    """Pourcentage arrondi à une décimale (0 si le total est nul)."""
    return round(float(part) * 100 / float(total), 1) if total else 0.0


def tableau_de_bord(etab, annee, aujourdhui=None):
    """Recouvrement, impayés par classe, effectifs, absences et élèves à risque de ``etab`` pour ``annee``."""
    from finances.views.commun import _situations_financieres_en_lot
    from inscriptions.models import Inscription
    from pedagogie.models import RisqueDecrochage
    from presences.models import Justification, Presence

    aujourdhui = aujourdhui or date.today()
    inscriptions = list(
        Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=etab)
        .select_related('eleve', 'classe__cycle', 'statut_eleve')
    )
    actives = [i for i in inscriptions if i.statut != 'ABANDON']
    situations = _situations_financieres_en_lot(actives)

    # ── Recouvrement et impayés par classe ──
    attendu = encaisse = reste = Decimal('0')
    par_classe = {}
    for ins in actives:
        sit = situations[ins.pk]
        ligne = par_classe.setdefault(ins.classe_id, {
            'classe': ins.classe, 'effectif': 0, 'redevables': 0,
            'attendu': Decimal('0'), 'reste': Decimal('0'),
        })
        ligne['effectif'] += 1
        ligne['attendu'] += sit['total_du']
        ligne['reste'] += sit['reste_a_payer']
        if sit['reste_a_payer'] > 0:
            ligne['redevables'] += 1
        attendu += sit['total_du']
        encaisse += sit['total_paye']
        reste += sit['reste_a_payer']
    for ligne in par_classe.values():
        ligne['taux'] = _taux(ligne['attendu'] - ligne['reste'], ligne['attendu'])
    impayes = sorted(par_classe.values(), key=lambda l: (-l['reste'], l['classe'].nom))
    recouvrement = {
        'attendu': attendu, 'encaisse': encaisse, 'reste': reste,
        'taux': _taux(attendu - reste, attendu),
        'redevables': sum(l['redevables'] for l in impayes),
        'sans_tarif': sum(1 for i in actives if situations[i.pk]['total_du'] == 0),
    }

    # ── Effectifs ──
    cycles = {}
    for ins in actives:
        cycle = ins.classe.cycle
        ligne = cycles.setdefault(cycle.pk, {'cycle': cycle, 'garcons': 0, 'filles': 0, 'total': 0, 'classes': set()})
        ligne['total'] += 1
        ligne['garcons' if ins.eleve.genre == 'M' else 'filles'] += 1
        ligne['classes'].add(ins.classe_id)
    for ligne in cycles.values():
        ligne['classes'] = len(ligne['classes'])
    classes_actives = {i.classe for i in actives}
    capacite = sum(c.capacite_max or 0 for c in classes_actives)
    effectifs = {
        'total': len(actives),
        'garcons': sum(1 for i in actives if i.eleve.genre == 'M'),
        'filles': sum(1 for i in actives if i.eleve.genre == 'F'),
        'redoublants': sum(1 for i in actives if i.est_redoublant),
        'abandons': len(inscriptions) - len(actives),
        'classes': len(classes_actives),
        'capacite': capacite,
        'taux_remplissage': _taux(len(actives), capacite),
        'cycles': sorted(cycles.values(), key=lambda l: l['cycle'].ordre),
    }

    # ── Absences ──
    absences = Presence.objects.filter(
        statut=Presence.StatutChoices.ABSENT, appel__annee_scolaire=annee, appel__classe__etablissement=etab,
    )
    depuis_30j = aujourdhui - timedelta(days=29)
    absences_30j = absences.filter(appel__date__gte=depuis_30j, appel__date__lte=aujourdhui)
    pointages_30j = Presence.objects.filter(
        appel__annee_scolaire=annee, appel__classe__etablissement=etab,
        appel__date__gte=depuis_30j, appel__date__lte=aujourdhui,
    ).count()
    classes_30j = (
        absences_30j.values('appel__classe__nom')
        .annotate(nb=Count('id'), eleves=Count('inscription', distinct=True))
        .order_by('-nb', 'appel__classe__nom')[:5]
    )
    eleves_annee = (
        absences.values('inscription__eleve__nom', 'inscription__eleve__prenom', 'inscription__classe__nom')
        .annotate(nb=Count('id')).order_by('-nb', 'inscription__eleve__nom')[:5]
    )
    absences_resume = {
        'aujourdhui': absences.filter(appel__date=aujourdhui).count(),
        'sept_jours': absences.filter(appel__date__gte=aujourdhui - timedelta(days=6), appel__date__lte=aujourdhui).count(),
        'trente_jours': absences_30j.count(),
        'taux_30j': _taux(absences_30j.count(), pointages_30j),
        'justifications_attente': Justification.objects.filter(
            statut='EN_ATTENTE', inscription__annee_scolaire=annee, inscription__classe__etablissement=etab,
        ).count(),
        'classes': list(classes_30j),
        'eleves': list(eleves_annee),
    }

    # ── Élèves à risque ──
    risques = RisqueDecrochage.objects.filter(
        inscription__annee_scolaire=annee, inscription__classe__etablissement=etab,
    ).exclude(inscription__statut='ABANDON')
    compteurs = defaultdict(int, {
        r['niveau']: r['nb'] for r in risques.values('niveau').annotate(nb=Count('id'))
    })
    risque = {
        'niveaux': [
            {'code': niveau, 'libelle': RisqueDecrochage.NiveauChoices(niveau).label, 'nb': compteurs[niveau]}
            for niveau in NIVEAUX_RISQUE
        ],
        'prioritaires_nb': compteurs['CRITIQUE'] + compteurs['ELEVE'],
        'prioritaires': list(
            risques.filter(Q(niveau='CRITIQUE') | Q(niveau='ELEVE'))
            .select_related('inscription__eleve', 'inscription__classe').order_by('-score')[:10]
        ),
        'date_calcul': risques.aggregate(d=Max('date_calcul'))['d'],
    }

    return {
        'recouvrement': recouvrement, 'impayes': impayes, 'effectifs': effectifs,
        'absences': absences_resume, 'risque': risque,
    }
