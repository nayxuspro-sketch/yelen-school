"""Contrôles atomiques des limites de licence.

Les limites ne sont pas des avertissements d'interface. Chaque création métier
verrouille la ligne de licence PostgreSQL, recompte la ressource puis effectue
la sauvegarde dans la même transaction. Cela évite que deux requêtes
concurrentes passent ensemble sous la limite.
"""

from __future__ import annotations

from contextlib import contextmanager

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Licence


class LicenceLimitExceeded(ValidationError):
    """La création ferait dépasser une limite commerciale."""

    def __init__(self, resource: str, current: int, maximum: int):
        self.resource = resource
        self.current = current
        self.maximum = maximum
        super().__init__(
            f"Limite de licence dépassée pour {resource}: "
            f"{current}/{maximum}."
        )


def _enforcement_enabled() -> bool:
    return bool(getattr(settings, "LICENSE_ENFORCEMENT_ENABLED", True))


def _current_count(etablissement, resource: str) -> int:
    if resource == "eleves":
        from inscriptions.models import Inscription

        return (
            Inscription.objects.filter(
                classe__etablissement=etablissement,
                annee_scolaire__est_courante=True,
                statut__in=("AFFECTE", "BOURSIER", "EXONERE"),
            )
            .values("eleve_id")
            .distinct()
            .count()
        )

    if resource == "enseignants":
        from personnel.models import InscriptionPersonnel

        return (
            InscriptionPersonnel.objects.filter(
                cycle__etablissement=etablissement,
                est_actif=True,
                poste__categorie="ENSEIGNEMENT",
            )
            .values("personnel_id")
            .distinct()
            .count()
        )

    if resource == "classes":
        from parametres.models import Classe

        return Classe.objects.filter(etablissement=etablissement, actif=True).count()

    raise ValueError(f"Ressource de licence inconnue: {resource}")


def _maximum(licence: Licence, resource: str) -> int:
    key = {
        "eleves": "max_eleves",
        "enseignants": "max_enseignants",
        "classes": "max_classes",
    }.get(resource)
    if key is None:
        raise ValueError(f"Ressource de licence inconnue: {resource}")
    return int(licence.limites_effectives().get(key, 0))


@contextmanager
def reserve_limit(etablissement, resource: str, *, increment: int = 1):
    """Réserve une capacité dans une transaction PostgreSQL verrouillée.

    La transaction englobe le ``yield`` : l'appelant doit effectuer sa création
    métier dans le bloc ``with``. En cas d'exception, la réservation est
    annulée avec la transaction.

    En développement/test sans enforcement, le bloc reste transparent pour ne
    pas fabriquer une licence de test implicite.
    """
    if not _enforcement_enabled():
        yield None
        return

    if increment < 0:
        raise ValueError("increment doit être positif")

    with transaction.atomic():
        licence = (
            Licence.objects.select_for_update()
            .select_related("etablissement")
            .get(etablissement=etablissement)
        )
        if not licence.est_active():
            raise ValidationError("Aucune licence active et liée à ce serveur.")

        maximum = _maximum(licence, resource)
        current = _current_count(etablissement, resource)
        # Zéro est une limite explicite (aucune ressource autorisée), pas
        # l'absence de plafond. Les limites « illimitées » sont représentées
        # par une grande valeur dans les profils officiels.
        if maximum < 0 or current + increment > maximum:
            raise LicenceLimitExceeded(resource, current, maximum)

        yield licence
