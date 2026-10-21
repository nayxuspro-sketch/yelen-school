"""Statistiques officielles : tableaux du questionnaire statistique du ministère (DGESS), par niveau et par sexe.

Rentrée : élèves et redoublants par niveau, nouveaux entrants, répartition par âge.
Fin d'année : abandons, décisions des conseils de classe, résultats aux examens officiels.
Toutes les fonctions reçoivent une ``AnneeScolaire`` et renvoient des structures prêtes à afficher ou exporter.
"""
import re
import unicodedata

from examens.models import InscriptionExamen, SessionExamen
from inscriptions.models import Inscription
from viescolaire.models import DecisionConseil

_NIVEAUX = ['PS', 'MS', 'GS', 'CP1', 'CP2', 'CE1', 'CE2', 'CM1', 'CM2', '6', '5', '4', '3', '2', '1', 'T']


def rang_niveau(niveau):
    """Ordre officiel des niveaux (maternelle → terminale) ; les libellés inconnus suivent, par ordre alphabétique."""
    cle = unicodedata.normalize('NFKD', niveau or '').encode('ascii', 'ignore').decode().upper().strip()
    if cle.startswith('TERM') or cle.startswith('TLE'):
        cle = 'T'
    else:
        chiffre = re.match(r'(\d+)', cle)
        if chiffre and not re.match(r'(CP|CE|CM)\d', cle):
            cle = chiffre.group(1)
    return (_NIVEAUX.index(cle), '') if cle in _NIVEAUX else (len(_NIVEAUX), cle)


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


def _inscriptions(annee):
    return Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=annee.etablissement).values(
        'id', 'classe_id', 'classe__niveau', 'classe__cycle__nom', 'classe__cycle__ordre',
        'eleve_id', 'eleve__genre', 'eleve__date_naissance', 'est_redoublant', 'statut',
    )


def _ligne(lignes, valeur, cles):
    cle = (valeur['classe__cycle__ordre'] or 0, valeur['classe__cycle__nom'] or '', valeur['classe__niveau'])
    ligne = lignes.get(cle)
    if ligne is None:
        ligne = lignes[cle] = {'cycle_ordre': cle[0], 'cycle': cle[1], 'niveau': cle[2], 'classes': set(),
                               **{k: _compteur() for k in cles}}
    ligne['classes'].add(valeur['classe_id'])
    return ligne


def statistiques_rentree(annee):
    """Élèves inscrits à la rentrée (abandons ultérieurs compris) : effectif, redoublants, nouveaux entrants par niveau ;
    répartition par âge (année de la rentrée − année de naissance) et par sexe."""
    anciens = set(Inscription.objects.filter(
        classe__etablissement=annee.etablissement, annee_scolaire__date_debut__lt=annee.date_debut,
    ).values_list('eleve_id', flat=True))
    cles = ('effectif', 'redoublants', 'nouveaux')
    lignes, ages = {}, {}
    for valeur in _inscriptions(annee):
        ligne = _ligne(lignes, valeur, cles)
        genre = valeur['eleve__genre']
        _ajouter(ligne['effectif'], genre)
        if valeur['est_redoublant']:
            _ajouter(ligne['redoublants'], genre)
        if valeur['eleve_id'] not in anciens:
            _ajouter(ligne['nouveaux'], genre)
        age = annee.date_debut.year - valeur['eleve__date_naissance'].year
        _ajouter(ages.setdefault(age, {}).setdefault(ligne['niveau'], _compteur()), genre)

    lignes = _ordonner(lignes)
    niveaux = [ligne['niveau'] for ligne in lignes]
    tableau_ages = []
    for age in sorted(ages):
        colonnes = [ages[age].get(niveau, _compteur()) for niveau in niveaux]
        tableau_ages.append({'age': f'{age} ans', 'colonnes': colonnes, 'total': _total(colonnes)})
    return {
        'lignes': lignes,
        'total': {cle: _total(ligne[cle] for ligne in lignes) for cle in cles},
        'niveaux': niveaux,
        'ages': tableau_ages,
    }


DECISIONS = (('passage', 'Passage'), ('redoublement', 'Redoublement'), ('orientation', 'Réorientation'),
             ('exclusion', 'Exclusion'), ('sans_decision', 'Sans décision'))
_CLE_DECISION = {'PASSAGE': 'passage', 'RACHAT': 'passage', 'REDOUBLEMENT': 'redoublement',
                 'ORIENTATION': 'orientation', 'EXCLUSION': 'exclusion'}


def statistiques_fin_annee(annee):
    """Par niveau : inscrits, abandons, effectif de fin d'année, dernière décision de conseil de classe ;
    par session d'examen officiel : inscrits, présents, admis et taux de réussite par sexe."""
    decisions = dict(DecisionConseil.objects.filter(
        inscription__annee_scolaire=annee, conseil__classe__etablissement=annee.etablissement,
    ).order_by('conseil__date_conseil', 'created_at').values_list('inscription_id', 'decision'))
    cles = ('inscrits', 'abandons', 'fin_annee') + tuple(cle for cle, _ in DECISIONS)
    lignes = {}
    for valeur in _inscriptions(annee):
        ligne = _ligne(lignes, valeur, cles)
        genre = valeur['eleve__genre']
        _ajouter(ligne['inscrits'], genre)
        if valeur['statut'] == 'ABANDON':
            _ajouter(ligne['abandons'], genre)
            continue
        _ajouter(ligne['fin_annee'], genre)
        _ajouter(ligne[_CLE_DECISION.get(decisions.get(valeur['id']), 'sans_decision')], genre)
    lignes = _ordonner(lignes)

    examens = []
    for session in SessionExamen.objects.filter(annee_scolaire=annee).order_by('type_examen', 'libelle'):
        compteurs = {cle: _compteur() for cle in ('inscrits', 'presents', 'admis')}
        for statut, genre in InscriptionExamen.objects.filter(session=session).values_list('statut', 'inscription__eleve__genre'):
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
