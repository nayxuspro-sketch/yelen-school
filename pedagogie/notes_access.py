"""Règles d'accès aux notes et bulletins selon les paiements de scolarité."""

from collections import defaultdict
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal

from django.db.models import Sum
from django.http import Http404

from inscriptions.models import Inscription, StatutInscriptionChoices
from parametres.models import IdentiteEtablissement


ZERO = Decimal('0')
_CONTROLE_PREALABLE = ContextVar('notes_controle_prealable', default=False)


@contextmanager
def saisies_notes_deja_controlees():
    """Évite de recalculer l'accès ligne par ligne après un contrôle par lot réussi."""
    jeton = _CONTROLE_PREALABLE.set(True)
    try:
        yield
    finally:
        _CONTROLE_PREALABLE.reset(jeton)


def controle_note_requis() -> bool:
    """Indique si le modèle doit vérifier lui-même l'accès à la note."""
    return not _CONTROLE_PREALABLE.get()


def filtrer_inscriptions_autorisees_notes(inscriptions: Iterable[Inscription]) -> list[Inscription]:
    """Retourne uniquement les inscriptions autorisées à afficher des notes ou un bulletin."""
    autorisees, _ = separer_inscriptions_saisie_notes(inscriptions)
    return autorisees


def inscription_autorisee_notes(inscription: Inscription) -> bool:
    """Indique si une inscription peut accéder à ses notes et bulletins."""
    return not separer_inscriptions_saisie_notes([inscription])[1]


def exiger_inscription_autorisee_notes(inscription: Inscription) -> Inscription:
    """Masque les fiches individuelles des inscriptions non autorisées (404)."""
    if not inscription_autorisee_notes(inscription):
        raise Http404("Fiche de résultats indisponible.")
    return inscription


def separer_inscriptions_saisie_notes(
    inscriptions: Iterable[Inscription],
) -> tuple[list[Inscription], list[Inscription]]:
    """Sépare les inscriptions autorisées et bloquées pour afficher/saisir des notes ou bulletins.

    Dans un établissement configuré comme non public, un élève non exonéré est
    bloqué si le montant net payé pour les rubriques comptées dans les frais de
    scolarité de son inscription annuelle est exactement nul. La règle s'applique
    même sans tarif actif configuré. Les inscriptions de plusieurs établissements
    peuvent être fournies ensemble ; chacune est évaluée selon son établissement.
    """
    inscriptions = list(inscriptions)
    if not inscriptions:
        return [], []

    par_etablissement = defaultdict(list)
    for inscription in inscriptions:
        par_etablissement[inscription.classe.etablissement_id].append(inscription)

    autorisees_ids = set()
    bloquees_ids = set()
    for groupe in par_etablissement.values():
        autorisees, bloquees = _separer_inscriptions_meme_etablissement(groupe)
        autorisees_ids.update(inscription.pk for inscription in autorisees)
        bloquees_ids.update(inscription.pk for inscription in bloquees)

    # Préserve l'ordre initial, y compris pour une sélection portant sur plusieurs établissements.
    return (
        [inscription for inscription in inscriptions if inscription.pk in autorisees_ids],
        [inscription for inscription in inscriptions if inscription.pk in bloquees_ids],
    )


def _separer_inscriptions_meme_etablissement(
    inscriptions: list[Inscription],
) -> tuple[list[Inscription], list[Inscription]]:
    """Applique le seuil de paiement aux inscriptions d'un même établissement."""
    if not inscriptions:
        return [], []

    etablissement_id = inscriptions[0].classe.etablissement_id
    type_etablissement = IdentiteEtablissement.objects.filter(
        etablissement_id=etablissement_id,
    ).values_list('type_etablissement', flat=True).first()
    if type_etablissement is None or type_etablissement == 'PUBLIC':
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
