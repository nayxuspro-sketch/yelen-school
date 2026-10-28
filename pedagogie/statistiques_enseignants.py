"""Statistiques par enseignant (pilotage) : charge (classes, disciplines, heures hebdomadaires), évaluations créées,
taux de saisie des notes, moyenne et taux de réussite des élèves, cahier de textes, appréciations — pour l'année ou
une période."""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from django.db.models import Count, Q, Sum

from inscriptions.models import Inscription, StatutInscriptionChoices
from viescolaire.models import SeanceCours

from .models import CahierTextes, Enseignement, Evaluation, Note, Resultat

STATUTS_EVALUATION_COMPTES = ('PLANIFIEE', 'EN_COURS', 'TERMINEE')


def _taux(part, total):
    return round(float(part) * 100 / float(total), 1) if total else 0.0


def _minutes(debut, fin):
    return max((datetime.combine(date.min, fin) - datetime.combine(date.min, debut)).total_seconds() / 60, 0)


def _par_enseignement(qs, cle, **annotations):
    return {ligne[cle]: ligne for ligne in qs.order_by().values(cle).annotate(**annotations)}


def statistiques_enseignants(etab, annee, trimestre=None):
    """Lignes par enseignant (puis par enseignement) pour l'année ``annee`` ; ``trimestre`` restreint évaluations,
    notes, résultats et cahier de textes à la période. Les enseignements sans enseignant forment la ligne
    « Non attribué »."""
    enseignements = list(
        Enseignement.objects.filter(annee_scolaire=annee, est_actif=True, classe__etablissement=etab)
        .select_related('classe', 'matiere', 'personnel').order_by('personnel__nom', 'personnel__prenom', 'classe__nom')
    )
    if not enseignements:
        return []
    ids = [e.pk for e in enseignements]
    periode = {'trimestre': trimestre} if trimestre else {}

    effectifs = {
        ligne['classe_id']: ligne['n']
        for ligne in Inscription.objects.filter(classe__in={e.classe_id for e in enseignements}, annee_scolaire=annee)
        .exclude(statut=StatutInscriptionChoices.ABANDON).order_by().values('classe_id').annotate(n=Count('pk'))
    }
    heures = defaultdict(float)
    for seance in SeanceCours.objects.filter(enseignement_id__in=ids).only('enseignement_id', 'heure_debut', 'heure_fin'):
        heures[seance.enseignement_id] += _minutes(seance.heure_debut, seance.heure_fin) / 60
    evaluations = _par_enseignement(
        Evaluation.objects.filter(enseignement_id__in=ids, statut__in=STATUTS_EVALUATION_COMPTES, **periode),
        'enseignement_id', total=Count('pk'), terminees=Count('pk', filter=Q(statut='TERMINEE')),
    )
    notes = _par_enseignement(
        Note.objects.filter(evaluation__enseignement_id__in=ids, evaluation__statut__in=STATUTS_EVALUATION_COMPTES,
                            **{f'evaluation__{k}': v for k, v in periode.items()}),
        'evaluation__enseignement_id', n=Count('pk'),
    )
    resultats = _par_enseignement(
        Resultat.objects.filter(enseignement_id__in=ids, dispense=False, moyenne__isnull=False, **periode),
        'enseignement_id', n=Count('pk'), somme=Sum('moyenne'), reussite=Count('pk', filter=Q(moyenne__gte=10)),
    )
    appreciations = _par_enseignement(
        Resultat.objects.filter(enseignement_id__in=ids, **periode).exclude(appreciation=''),
        'enseignement_id', n=Count('pk'),
    )
    cahier_qs = CahierTextes.objects.filter(enseignement_id__in=ids)
    if trimestre:
        cahier_qs = cahier_qs.filter(date__gte=trimestre.date_debut, date__lte=trimestre.date_fin)
    cahier = _par_enseignement(cahier_qs, 'enseignement_id', n=Count('pk'))

    par_enseignant = {}
    for e in enseignements:
        effectif = effectifs.get(e.classe_id, 0)
        ev = evaluations.get(e.pk, {'total': 0, 'terminees': 0})
        res = resultats.get(e.pk, {'n': 0, 'somme': None, 'reussite': 0})
        detail = {
            'enseignement': e, 'classe': e.classe.nom, 'matiere': e.matiere.nom, 'effectif': effectif,
            'heures': round(heures.get(e.pk, 0.0), 1),
            'evaluations': ev['total'], 'evaluations_terminees': ev['terminees'],
            'notes_saisies': notes.get(e.pk, {'n': 0})['n'], 'notes_attendues': ev['total'] * effectif,
            'resultats': res['n'], 'somme_moyennes': res['somme'] or Decimal('0'), 'reussite': res['reussite'],
            'cahier': cahier.get(e.pk, {'n': 0})['n'], 'appreciations': appreciations.get(e.pk, {'n': 0})['n'],
        }
        detail['taux_saisie'] = _taux(detail['notes_saisies'], detail['notes_attendues'])
        detail['moyenne'] = (detail['somme_moyennes'] / res['n']).quantize(Decimal('0.01')) if res['n'] else None
        detail['taux_reussite'] = _taux(res['reussite'], res['n'])
        cle = e.personnel_id or 'non_attribue'
        ligne = par_enseignant.get(cle)
        if ligne is None:
            ligne = par_enseignant[cle] = {
                'personnel': e.personnel, 'nom': e.personnel.get_nom_complet() if e.personnel else 'Non attribué',
                'fonction': e.personnel.fonction if e.personnel else '', 'classes': {}, 'disciplines': set(),
                'details': [], 'heures': 0.0, 'evaluations': 0, 'evaluations_terminees': 0, 'notes_saisies': 0,
                'notes_attendues': 0, 'resultats': 0, 'somme_moyennes': Decimal('0'), 'reussite': 0, 'cahier': 0,
                'appreciations': 0,
            }
        ligne['classes'][e.classe_id] = (e.classe.nom, effectif)
        ligne['disciplines'].add(e.matiere.nom)
        ligne['details'].append(detail)
        for champ in ('heures', 'evaluations', 'evaluations_terminees', 'notes_saisies', 'notes_attendues', 'resultats',
                      'somme_moyennes', 'reussite', 'cahier', 'appreciations'):
            ligne[champ] += detail[champ]

    lignes = []
    for ligne in par_enseignant.values():
        ligne['nb_classes'] = len(ligne['classes'])
        ligne['eleves'] = sum(n for _, n in ligne['classes'].values())
        ligne['libelle_classes'] = ', '.join(sorted(nom for nom, _ in ligne['classes'].values()))
        ligne['libelle_disciplines'] = ', '.join(sorted(ligne['disciplines']))
        ligne['heures'] = round(ligne['heures'], 1)
        ligne['taux_saisie'] = _taux(ligne['notes_saisies'], ligne['notes_attendues'])
        ligne['moyenne'] = (ligne['somme_moyennes'] / ligne['resultats']).quantize(Decimal('0.01')) if ligne['resultats'] else None
        ligne['taux_reussite'] = _taux(ligne['reussite'], ligne['resultats'])
        lignes.append(ligne)
    lignes.sort(key=lambda l: (l['personnel'] is None, l['nom']))
    return lignes
