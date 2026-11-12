"""Statistiques officielles : tableaux du questionnaire statistique du ministère (DGESS), par niveau et par sexe.

Rentrée : élèves et redoublants par niveau, nouveaux entrants, répartition par âge.
Fin d'année : abandons, décisions des conseils de classe, résultats aux examens officiels.
Toutes les fonctions reçoivent une ``AnneeScolaire`` et renvoient des structures prêtes à afficher ou exporter.
"""
from collections import Counter

from examens.models import InscriptionExamen, SessionExamen
from inscriptions.models import Inscription, StatutInscriptionChoices
from parametres.niveaux import rang_niveau
from viescolaire.models import DecisionConseil


def _compteur():
    return {'M': 0, 'F': 0, 'T': 0}


def _ajouter(compteur, genre):
    compteur['T'] += 1
    if genre in ('M', 'F'):
        compteur[genre] += 1


def _total(compteurs):
    total = _compteur()
    for compteur in compteurs:
        for cle in total:
            total[cle] += compteur[cle]
    return total


def _ordonner(lignes):
    lignes = sorted(lignes.values(), key=lambda l: (l['cycle_ordre'], rang_niveau(l['niveau'])))
    for ligne in lignes:
        ligne['divisions'] = len(ligne.pop('classes'))
    return lignes


def _inscriptions(annee, cycle_ids=None):
    inscriptions = Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=annee.etablissement)
    if cycle_ids is not None:
        inscriptions = inscriptions.filter(classe__cycle_id__in=cycle_ids)
    return inscriptions.values(
        'id', 'classe_id', 'classe__niveau', 'classe__cycle__nom', 'classe__cycle__ordre',
        'eleve_id', 'eleve__genre', 'eleve__date_naissance', 'est_redoublant', 'statut',
    )


def _cle_ligne(ligne):
    """Identité d'une ligne de niveau : un même libellé de niveau peut exister dans plusieurs cycles."""
    return (ligne['cycle_ordre'], ligne['cycle'], ligne['niveau'])


def _libelles_colonnes(lignes):
    """Libellé de colonne par niveau, précisé du cycle lorsque le niveau existe dans plusieurs cycles."""
    doublons = {niveau for niveau, n in Counter(ligne['niveau'] for ligne in lignes).items() if n > 1}
    return [f"{ligne['niveau']} ({ligne['cycle']})" if ligne['niveau'] in doublons else ligne['niveau'] for ligne in lignes]


def _ligne(lignes, valeur, cles):
    cle = (valeur['classe__cycle__ordre'] or 0, valeur['classe__cycle__nom'] or '', valeur['classe__niveau'])
    ligne = lignes.get(cle)
    if ligne is None:
        ligne = lignes[cle] = {'cycle_ordre': cle[0], 'cycle': cle[1], 'niveau': cle[2], 'classes': set(),
                               **{k: _compteur() for k in cles}}
    ligne['classes'].add(valeur['classe_id'])
    return ligne


def statistiques_rentree(annee, cycle_ids=None):
    """Élèves inscrits à la rentrée (abandons ultérieurs compris) : effectif, redoublants, nouveaux entrants par niveau ;
    répartition par âge (année de la rentrée − année de naissance) et par sexe.

    ``cycle_ids=None`` conserve la vue établissement ; une liste limite les indicateurs au périmètre autorisé.
    """
    anciens_qs = Inscription.objects.filter(
        classe__etablissement=annee.etablissement, annee_scolaire__date_debut__lt=annee.date_debut,
    )
    if cycle_ids is not None:
        anciens_qs = anciens_qs.filter(classe__cycle_id__in=cycle_ids)
    anciens = set(anciens_qs.values_list('eleve_id', flat=True))
    cles = ('effectif', 'redoublants', 'nouveaux')
    lignes, ages = {}, {}
    for valeur in _inscriptions(annee, cycle_ids):
        ligne = _ligne(lignes, valeur, cles)
        genre = valeur['eleve__genre']
        _ajouter(ligne['effectif'], genre)
        if valeur['est_redoublant']:
            _ajouter(ligne['redoublants'], genre)
        if valeur['eleve_id'] not in anciens:
            _ajouter(ligne['nouveaux'], genre)
        age = annee.date_debut.year - valeur['eleve__date_naissance'].year
        _ajouter(ages.setdefault(age, {}).setdefault(_cle_ligne(ligne), _compteur()), genre)

    lignes = _ordonner(lignes)
    cles_lignes = [_cle_ligne(ligne) for ligne in lignes]
    tableau_ages = []
    for age in sorted(ages):
        colonnes = [ages[age].get(cle, _compteur()) for cle in cles_lignes]
        tableau_ages.append({'age': f'{age} ans', 'colonnes': colonnes, 'total': _total(colonnes)})
    total = {cle: _total(ligne[cle] for ligne in lignes) for cle in cles}
    return {
        'lignes': lignes,
        'total': total,
        'niveaux': _libelles_colonnes(lignes),
        'ages': tableau_ages,
        # Pied du tableau des âges : effectif par niveau et total général (= somme des lignes d'âge)
        'ages_total': {'colonnes': [ligne['effectif'] for ligne in lignes], 'total': total['effectif']},
    }


DECISIONS = (('passage', 'Passage'), ('redoublement', 'Redoublement'), ('orientation', 'Réorientation'),
             ('exclusion', 'Exclusion'), ('sans_decision', 'Sans décision'))
_CLE_DECISION = {'PASSAGE': 'passage', 'RACHAT': 'passage', 'REDOUBLEMENT': 'redoublement',
                 'ORIENTATION': 'orientation', 'EXCLUSION': 'exclusion'}


def statistiques_fin_annee(annee, cycle_ids=None):
    """Par niveau : inscrits, abandons, effectif de fin d'année, dernière décision de conseil de classe ;
    par session d'examen officiel : inscrits, présents, admis et taux de réussite par sexe.

    ``cycle_ids=None`` conserve la vue établissement ; une liste limite les indicateurs au périmètre autorisé.
    """
    decisions_qs = DecisionConseil.objects.filter(
        inscription__annee_scolaire=annee, conseil__classe__etablissement=annee.etablissement,
    )
    if cycle_ids is not None:
        decisions_qs = decisions_qs.filter(conseil__classe__cycle_id__in=cycle_ids)
    decisions = dict(decisions_qs.order_by('conseil__date_conseil', 'created_at')
                     .values_list('inscription_id', 'decision'))
    cles = ('inscrits', 'abandons', 'fin_annee') + tuple(cle for cle, _ in DECISIONS)
    lignes = {}
    for valeur in _inscriptions(annee, cycle_ids):
        ligne = _ligne(lignes, valeur, cles)
        genre = valeur['eleve__genre']
        _ajouter(ligne['inscrits'], genre)
        if valeur['statut'] == StatutInscriptionChoices.ABANDON:
            _ajouter(ligne['abandons'], genre)
            continue
        _ajouter(ligne['fin_annee'], genre)
        _ajouter(ligne[_CLE_DECISION.get(decisions.get(valeur['id']), 'sans_decision')], genre)
    lignes = _ordonner(lignes)

    examens = []
    sessions = SessionExamen.objects.filter(annee_scolaire=annee)
    if cycle_ids is not None:
        sessions = sessions.filter(inscriptions_examen__inscription__classe__cycle_id__in=cycle_ids).distinct()
    for session in sessions.order_by('type_examen', 'libelle'):
        compteurs = {cle: _compteur() for cle in ('inscrits', 'presents', 'admis')}
        inscriptions_examen = InscriptionExamen.objects.filter(session=session)
        if cycle_ids is not None:
            inscriptions_examen = inscriptions_examen.filter(inscription__classe__cycle_id__in=cycle_ids)
        for statut, genre in inscriptions_examen.values_list('statut', 'inscription__eleve__genre'):
            _ajouter(compteurs['inscrits'], genre)
            if statut != 'ABSENT':
                _ajouter(compteurs['presents'], genre)
            if statut == 'ADMIS':
                _ajouter(compteurs['admis'], genre)
        taux = {cle: round(100 * compteurs['admis'][cle] / compteurs['presents'][cle], 1) if compteurs['presents'][cle] else None
                for cle in ('M', 'F', 'T')}
        examens.append({'session': session, **compteurs, 'taux': taux})
    return {
        'lignes': lignes,
        'total': {cle: _total(ligne[cle] for ligne in lignes) for cle in cles},
        'decisions': DECISIONS,
        'examens': examens,
    }
