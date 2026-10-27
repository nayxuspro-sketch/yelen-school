"""Créances individuelles (manuel non rendu, …) : montants dus par un élève hors tarifs, intégrés à sa situation
financière au même titre que les services annexes."""
from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from .abonnements import LigneFrais, montants_par_rubrique
from .models import Creance


def creances_actives(inscription):
    return Creance.objects.filter(inscription=inscription, actif=True, is_active=True).select_related('rubrique')


def montants_creances(inscription_ids):
    """{inscription_id: Σ créances actives} pour une liste d'inscriptions."""
    lignes = (
        Creance.objects.filter(inscription_id__in=list(inscription_ids), actif=True, is_active=True)
        .values('inscription_id').annotate(s=Sum('montant'))
    )
    return {l['inscription_id']: l['s'] or Decimal('0') for l in lignes}


def lignes_creances(inscription):
    """Lignes de frais des créances actives, pour la situation financière de l'élève."""
    return [LigneFrais(rubrique=c.rubrique, montant=c.montant, libelle=c.libelle) for c in creances_actives(inscription)]


def montants_hors_tarifs_par_rubrique(inscription):
    """{rubrique_id: montant dû} des services souscrits et des créances actives : rubriques encaissables en plus
    des tarifs de la classe, et plafond des versements sur chacune."""
    totaux = defaultdict(lambda: Decimal('0'), montants_par_rubrique(inscription))
    for creance in creances_actives(inscription):
        totaux[creance.rubrique_id] += creance.montant
    return dict(totaux)
