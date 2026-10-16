"""Statistiques d'effectif : répartition des élèves par genre et par tranche d'âge.

Partagé par la liste alphabétique de classe (documents) et la liste des élèves (inscriptions).
L'âge suit la même approximation que ``Eleve.age`` (jours écoulés // 365) pour rester cohérent
avec la colonne « Âge » affichée dans l'application.
"""
import datetime

TRANCHES_AGE = (
    (0, 5, "≤ 5 ans"),
    (6, 8, "6 – 8 ans"),
    (9, 11, "9 – 11 ans"),
    (12, 14, "12 – 14 ans"),
    (15, 17, "15 – 17 ans"),
    (18, 20, "18 – 20 ans"),
    (21, None, "> 20 ans"),
)
SANS_DATE = "Sans date de naissance"


def age_en_annees(date_naissance, aujourd_hui=None):
    """Âge approché (comme ``Eleve.age``) ; None sans date de naissance."""
    if not date_naissance:
        return None
    return ((aujourd_hui or datetime.date.today()) - date_naissance).days // 365


def statistiques_eleves(couples, aujourd_hui=None):
    """``couples`` : itérable de (genre, date_naissance).

    Retourne ``{'effectif': {'garcons', 'filles', 'total'}, 'tranches': [...]}`` où chaque tranche
    non vide est ``{'label', 'garcons', 'filles', 'total'}`` (tranches d'âge dans l'ordre, puis
    « Sans date de naissance » le cas échéant).
    """
    effectif = {'garcons': 0, 'filles': 0, 'total': 0}
    compteurs = {label: {'garcons': 0, 'filles': 0, 'total': 0} for _, _, label in TRANCHES_AGE}
    compteurs[SANS_DATE] = {'garcons': 0, 'filles': 0, 'total': 0}

    for genre, date_naissance in couples:
        age = age_en_annees(date_naissance, aujourd_hui)
        label = SANS_DATE
        if age is not None:
            for minimum, maximum, libelle in TRANCHES_AGE:
                if age >= minimum and (maximum is None or age <= maximum):
                    label = libelle
                    break
        for cible in (effectif, compteurs[label]):
            cible['total'] += 1
            if genre == 'M':
                cible['garcons'] += 1
            elif genre == 'F':
                cible['filles'] += 1

    tranches = [{'label': label, **valeurs} for label, valeurs in compteurs.items() if valeurs['total']]
    return {'effectif': effectif, 'tranches': tranches}
