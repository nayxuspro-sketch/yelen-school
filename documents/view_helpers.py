"""Sélecteurs et contrôles de périmètre partagés par les vues Documents."""

import uuid

from django.db.models import Q
from core.models import RoleChoices
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire, Classe, TypeDocument
from personnel.selectors import cycles_accessibles
from yelen_school.cycle_filter import get_cycle_ids


def _can_generate_document(user):
    """Vérifie si l'utilisateur peut générer des documents officiels."""
    return user.role in (
        RoleChoices.SUPER_ADMIN,
        RoleChoices.DIRECTEUR,
        RoleChoices.CENSEUR,
        RoleChoices.SECRETAIRE,
        RoleChoices.COMPTABLE,
    )


def _annees_accessibles(request, etab=None):
    """Années scolaires de l'établissement et des cycles accessibles au compte."""
    annees = AnneeScolaire.objects.all()
    cycles = cycles_accessibles(request, etab)
    if etab is not None:
        return annees.filter(etablissement=etab)
    return annees.filter(etablissement_id__in=cycles.values('etablissement_id'))


def _classes_accessibles(request, etab=None):
    """Classes rattachées aux cycles accessibles, dans l'établissement le cas échéant."""
    return Classe.objects.filter(cycle__in=cycles_accessibles(request, etab))


def _inscriptions_accessibles(request, etab=None):
    """Inscriptions d'élèves dont la classe appartient à un cycle accessible."""
    inscriptions = Inscription.objects.filter(classe__cycle__in=cycles_accessibles(request, etab))
    if etab is not None:
        inscriptions = inscriptions.filter(classe__etablissement=etab, annee_scolaire__etablissement=etab)
    return inscriptions


def _documents_accessibles(request, queryset):
    """Documents du bon périmètre de cycle.

    Les documents sans classe ni inscription (par exemple une circulaire générale) restent visibles aux comptes
    autorisés à tous les cycles ; ils ne sont pas attribuables à un cycle pour les autres comptes.
    """
    cycle_ids = get_cycle_ids(request)
    if cycle_ids is None:
        return queryset
    if not cycle_ids:
        return queryset.none()
    return queryset.filter(
        Q(classe__cycle_id__in=cycle_ids) | Q(inscription__classe__cycle_id__in=cycle_ids)
    )


def _types_documents_accessibles(request, etab=None):
    """Types actifs du bon établissement et des cycles consultables."""
    types = TypeDocument.objects.filter(actif=True)
    if etab is not None:
        types = types.filter(Q(cycle__isnull=True) | Q(cycle__etablissement=etab))
    if get_cycle_ids(request) is not None:
        types = types.filter(Q(cycle__isnull=True) | Q(cycle__in=cycles_accessibles(request, etab)))
    return types


def _identifiants_uuid(valeurs):
    """Normalise une liste d'identifiants UUID ; None signale une valeur mal formée."""
    try:
        return list(dict.fromkeys(str(uuid.UUID(valeur)) for valeur in valeurs))
    except (AttributeError, TypeError, ValueError):
        return None
