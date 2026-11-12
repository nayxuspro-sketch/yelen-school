"""Règles d'accès à la saisie des notes selon les paiements de scolarité."""

from collections.abc import Iterable

from inscriptions.models import Inscription, StatutInscriptionChoices
from parametres.models import IdentiteEtablissement, TarifScolarite


def separer_inscriptions_saisie_notes(
    inscriptions: Iterable[Inscription],
) -> tuple[list[Inscription], list[Inscription]]:
    """Sépare les inscriptions autorisées et bloquées pour une même classe et une même année.

    Dans un établissement privé, si des tarifs sont configurés pour l'année,
    un élève non exonéré ne peut saisir de notes que si un paiement net positif
    est enregistré pour son inscription annuelle. Les autres établissements,
    les années sans tarif configuré et les élèves exonérés ne sont pas bloqués.
    """
    inscriptions = list(inscriptions)
    if not inscriptions:
        return [], []

    premiere = inscriptions[0]
    etablissement_id = premiere.classe.etablissement_id
    annee_scolaire_id = premiere.annee_scolaire_id
    est_prive = IdentiteEtablissement.objects.filter(
        etablissement_id=etablissement_id,
        type_etablissement='PRIVE',
    ).exists()
    frais_configures = est_prive and TarifScolarite.objects.filter(
        etablissement_id=etablissement_id,
        annee_scolaire_id=annee_scolaire_id,
        actif=True,
    ).exists()
    if not frais_configures:
        return inscriptions, []

    non_exonerees = [
        inscription for inscription in inscriptions
        if not inscription.est_exonere and inscription.statut != StatutInscriptionChoices.EXONERE
    ]
    if not non_exonerees:
        return inscriptions, []

    from finances.views.commun import _situations_financieres_en_lot

    situations = _situations_financieres_en_lot(non_exonerees)
    bloquees = [
        inscription for inscription in non_exonerees
        if situations.get(inscription.pk, {}).get('total_paye', 0) <= 0
    ]
    bloquees_ids = {inscription.pk for inscription in bloquees}
    autorisees = [inscription for inscription in inscriptions if inscription.pk not in bloquees_ids]
    return autorisees, bloquees
