"""Règles d'accès à la saisie des notes selon les paiements de scolarité."""

from collections.abc import Iterable
from decimal import Decimal

from django.db.models import Sum

from inscriptions.models import Inscription, StatutInscriptionChoices
from parametres.models import IdentiteEtablissement


ZERO = Decimal('0')


def separer_inscriptions_saisie_notes(
    inscriptions: Iterable[Inscription],
) -> tuple[list[Inscription], list[Inscription]]:
    """Sépare les inscriptions autorisées et bloquées pour une même classe et une même année.

    Dans un établissement privé, un élève non exonéré est bloqué si le montant
    net payé pour les rubriques comptées dans les frais de scolarité de son
    inscription annuelle est exactement nul. La règle s'applique même sans tarif
    actif configuré.
    """
    inscriptions = list(inscriptions)
    if not inscriptions:
        return [], []

    etablissement_id = inscriptions[0].classe.etablissement_id
    est_prive = IdentiteEtablissement.objects.filter(
        etablissement_id=etablissement_id,
        type_etablissement='PRIVE',
    ).exists()
    if not est_prive:
        return inscriptions, []

    non_exonerees = [
        inscription for inscription in inscriptions
        if not inscription.est_exonere and inscription.statut != StatutInscriptionChoices.EXONERE
    ]
    if not non_exonerees:
        return inscriptions, []

    from finances.models import Paiement, Remboursement

    ids = [inscription.pk for inscription in non_exonerees]
    verses = {
        ligne['inscription_id']: ligne['total'] or ZERO
        for ligne in Paiement.objects.filter(
            inscription_id__in=ids,
            is_active=True,
            rubrique__etablissement_id=etablissement_id,
            rubrique__soumise_plafond=True,
        ).values('inscription_id').annotate(total=Sum('montant'))
    }
    rembourses = {
        ligne['paiement__inscription_id']: ligne['total'] or ZERO
        for ligne in Remboursement.objects.filter(
            paiement__inscription_id__in=ids,
            paiement__is_active=True,
            paiement__rubrique__etablissement_id=etablissement_id,
            paiement__rubrique__soumise_plafond=True,
            is_active=True,
        ).values('paiement__inscription_id').annotate(total=Sum('montant'))
    }
    bloquees = [
        inscription for inscription in non_exonerees
        if verses.get(inscription.pk, ZERO) - rembourses.get(inscription.pk, ZERO) == ZERO
    ]
    bloquees_ids = {inscription.pk for inscription in bloquees}
    autorisees = [inscription for inscription in inscriptions if inscription.pk not in bloquees_ids]
    return autorisees, bloquees
