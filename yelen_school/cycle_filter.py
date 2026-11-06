"""
yelen_school/cycle_filter.py — Utilitaires de filtrage des querysets par cycle

Fournit des fonctions pour filtrer les querysets selon les cycles autorisés
de l'utilisateur connecté, stockés sur request par CycleAccessMiddleware.
"""

from __future__ import annotations

from django.db.models import QuerySet, Q


def get_cycle_ids(request) -> list:
    """
    Retourne la liste des IDs de cycles autorisés pour l'utilisateur de la request.
    Retourne une liste vide si aucun cycle n'est autorisé.
    Retourne None si l'utilisateur voit tous les cycles (pas de filtrage).
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return []

    if getattr(request, 'est_tous_cycles', False):
        return None  # Aucun filtrage

    cycles = getattr(request, 'cycles_autorises', None)
    if cycles is None:
        return []

    return list(cycles.values_list('id', flat=True))


def filtrer_par_cycle(
    queryset: QuerySet,
    request,
    cycle_field: str = 'cycle',
) -> QuerySet:
    """
    Filtre un queryset selon les cycles autorisés de l'utilisateur.

    Args:
        queryset: Le queryset à filtrer.
        request: La requête HTTP (doit avoir été passée par CycleAccessMiddleware).
        cycle_field: Nom du champ FK vers Cycle sur le modèle (par défaut 'cycle').
                     Si le modèle n'a pas de champ cycle direct, utiliser une expression
                     de liaison (ex: 'inscription__classe__cycle').

    Returns:
        Le queryset filtré. Si l'utilisateur voit tous les cycles, retourne le queryset
        inchangé. Si aucun cycle n'est autorisé, retourne un queryset vide.
    """
    cycle_ids = get_cycle_ids(request)

    # Aucun filtrage (tous les cycles)
    if cycle_ids is None:
        return queryset

    # Aucun cycle autorisé → queryset vide
    if not cycle_ids:
        return queryset.none()

    return queryset.filter(**{f'{cycle_field}__in': cycle_ids})


def cycle_queryset(
    queryset: QuerySet,
    request,
    cycle_field: str = 'cycle',
) -> QuerySet:
    """
    Alias de filtrer_par_cycle pour compatibilité avec les vues existantes.
    """
    return filtrer_par_cycle(queryset, request, cycle_field=cycle_field)


def filtrer_eleve_par_cycle(
    queryset: QuerySet,
    request,
) -> QuerySet:
    """
    Filtre un queryset d'élèves selon les cycles autorisés.

    Un élève est lié à un cycle via : Inscription → Classe → Cycle.
    Seules les inscriptions de l'année scolaire courante sont prises en compte.
    """
    from inscriptions.models import Inscription
    from parametres.models import AnneeScolaire

    cycle_ids = get_cycle_ids(request)

    if cycle_ids is None:
        return queryset

    if not cycle_ids:
        return queryset.none()

    # Récupérer les classes autorisées pour les cycles de l'utilisateur
    from parametres.models import Classe
    classes_autorisees = Classe.objects.filter(cycle_id__in=cycle_ids)

    # Récupérer les élèves inscrits dans ces classes (année courante)
    annee_courante = AnneeScolaire.objects.filter(
        est_courante=True
    ).first()

    if annee_courante:
        eleves_ids = Inscription.objects.filter(
            classe__in=classes_autorisees,
            annee_scolaire=annee_courante,
        ).values_list('eleve_id', flat=True)
    else:
        eleves_ids = Inscription.objects.filter(
            classe__in=classes_autorisees,
        ).values_list('eleve_id', flat=True)

    return queryset.filter(id__in=eleves_ids)


def filtrer_classe_par_cycle(
    queryset: QuerySet,
    request,
) -> QuerySet:
    """
    Filtre un queryset de classes selon les cycles autorisés.
    """
    cycle_ids = get_cycle_ids(request)

    if cycle_ids is None:
        return queryset

    if not cycle_ids:
        return queryset.none()

    return queryset.filter(cycle_id__in=cycle_ids)
