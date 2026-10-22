"""Montants dus au titre des services annexes (cantine, transport, internat), intégrés à la situation financière."""
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from .models import AbonnementService


@dataclass
class LigneFrais:
    """Ligne de « Rubriques à payer » : même interface que ``TarifScolarite`` (rubrique, montant), plus un libellé."""
    rubrique: object
    montant: Decimal
    libelle: str


def abonnements_actifs(inscription):
    return (
        AbonnementService.objects.filter(inscription=inscription, actif=True, is_active=True)
        .select_related('formule__service__rubrique').order_by('formule__service__type_service', 'date_debut')
    )


def montants_services(inscription_ids):
    """{inscription_id: Σ montant dû des abonnements actifs} pour une liste d'inscriptions."""
    lignes = (
        AbonnementService.objects.filter(inscription_id__in=list(inscription_ids), actif=True, is_active=True)
        .values('inscription_id').annotate(s=Sum('montant_total'))
    )
    return {l['inscription_id']: l['s'] or Decimal('0') for l in lignes}


def montants_par_rubrique(inscription):
    """{rubrique_id: montant dû} des services souscrits : plafond des versements sur ces rubriques."""
    totaux = defaultdict(lambda: Decimal('0'))
    for abonnement in abonnements_actifs(inscription):
        totaux[abonnement.formule.service.rubrique_id] += abonnement.montant_total
    return dict(totaux)


def lignes_services(inscription):
    """Lignes de frais des abonnements actifs, pour la situation financière de l'élève."""
    return [
        LigneFrais(rubrique=a.formule.service.rubrique, montant=a.montant_total,
                   libelle=f"{a.formule.service.nom} — {a.formule.libelle}")
        for a in abonnements_actifs(inscription)
    ]
