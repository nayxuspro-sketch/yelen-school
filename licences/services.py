# licences/services.py
# ================================================================
# Services de contrôle des licences — logique métier hors middlewares/vues.
#
# Fournit le calcul des usages réels de l'établissement (élèves,
# enseignants, classes) comparés aux plafonds du niveau de licence.
# Portable PostgreSQL / SQLite (aucune fonctionnalité spécifique moteur).
from __future__ import annotations

from typing import Optional


def _annee_courante(etablissement):
    """Année scolaire courante de l'établissement (ou None)."""
    from parametres.models import AnneeScolaire
    return (
        AnneeScolaire.objects
        .filter(etablissement=etablissement, est_courante=True)
        .first()
    )


def compter_eleves(etablissement) -> int:
    """Nombre d'élèves distincts inscrits dans l'année scolaire courante
    (tous statuts sauf ABANDON)."""
    from inscriptions.models import Inscription

    annee = _annee_courante(etablissement)
    if annee is None:
        return 0
    return (
        Inscription.objects
        .filter(classe__etablissement=etablissement, annee_scolaire=annee)
        .exclude(statut='ABANDON')
        .values('eleve_id')
        .distinct()
        .count()
    )


def compter_enseignants(etablissement) -> int:
    """Nombre d'enseignants distincts actifs dans l'année scolaire courante
    (inscription du personnel validée, poste de catégorie Enseignement)."""
    from personnel.models import InscriptionPersonnel

    annee = _annee_courante(etablissement)
    if annee is None:
        return 0
    return (
        InscriptionPersonnel.objects
        .filter(
            cycle__etablissement=etablissement,
            annee_scolaire=annee,
            est_actif=True,
            is_active=True,
            poste__categorie='ENSEIGNEMENT',
        )
        .values('personnel_id')
        .distinct()
        .count()
    )


def compter_classes(etablissement) -> int:
    """Nombre de classes actives de l'établissement."""
    from parametres.models import Classe
    return Classe.objects.filter(etablissement=etablissement, actif=True).count()


def get_usage_limites(licence) -> dict:
    """
    Compare l'usage réel de l'établissement aux plafonds de sa licence.

    Args:
        licence: instance de licences.Licence

    Returns:
        dict {
            'usage':       {'eleves': int, 'enseignants': int, 'classes': int},
            'limites':     {'max_eleves': int, 'max_enseignants': int,
                            'max_classes': int},
            'depassements': [{'champ': str, 'usage': int, 'max': int,
                              'message': str}, ...],
        }
    """
    from .models import LIMITES_LICENCES

    etab = licence.etablissement
    limites = LIMITES_LICENCES.get(licence.type_licence, {})

    usage = {
        'eleves': compter_eleves(etab),
        'enseignants': compter_enseignants(etab),
        'classes': compter_classes(etab),
    }

    depassements = []
    for champ, max_cle, libelle in (
        ('eleves', 'max_eleves', 'élèves inscrits'),
        ('enseignants', 'max_enseignants', 'enseignants actifs'),
        ('classes', 'max_classes', 'classes actives'),
    ):
        mx = limites.get(max_cle)
        if mx and usage[champ] > mx:
            depassements.append({
                'champ': champ,
                'usage': usage[champ],
                'max': mx,
                'message': (
                    f"Limite de licence dépassée : {usage[champ]} {libelle} "
                    f"pour un maximum de {mx} "
                    f"(licence {licence.get_type_licence_display()})."
                ),
            })

    return {
        'usage': usage,
        'limites': limites,
        'depassements': depassements,
    }
