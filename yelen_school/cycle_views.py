"""
yelen_school/cycle_views.py — Mixins de filtrage par cycle pour les vues

Fournit :
- CycleFilterMixin : pour les vues CBV (ListView, etc.) — filtre automatiquement
  le queryset selon request.cycles_autorises / request.est_tous_cycles
- cycle_queryset() : helper pour les vues FBV
"""

from __future__ import annotations

from django.db.models.query import QuerySet

from yelen_school.cycle_filter import (
    filtrer_par_cycle,
    filtrer_eleve_par_cycle,
    filtrer_classe_par_cycle,
    get_cycle_ids,
)


class CycleFilterMixin:
    """
    Mixin pour les vues CBV qui applique le filtrage par cycle sur le queryset.

    Attributs optionnels :
    - cycle_field : nom du champ FK vers Cycle sur le modèle (défaut: 'cycle')
    - cycle_filter_func : fonction de filtrage personnalisée (défaut: None →
      utilise filtrer_par_cycle avec cycle_field)

    Exemple :
        class EleveListView(CycleFilterMixin, ListView):
            model = Eleve
            cycle_filter_func = filtrer_eleve_par_cycle
    """

    cycle_field: str = 'cycle'
    cycle_filter_func = None  # Si None, utilise filtrer_par_cycle avec cycle_field

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()
        request = self.request

        if self.cycle_filter_func is not None:
            return self.cycle_filter_func(queryset, request)

        return filtrer_par_cycle(queryset, request, cycle_field=self.cycle_field)


def cycle_queryset(queryset: QuerySet, request, cycle_field: str = 'cycle') -> QuerySet:
    """
    Helper pour les vues FBV : filtre un queryset selon les cycles autorisés.

    Exemple :
        def ma_vue(request):
            queryset = cycle_queryset(Eleve.objects.all(), request)
    """
    return filtrer_par_cycle(queryset, request, cycle_field=cycle_field)


def cycle_ids(request) -> list:
    """
    Retourne la liste des IDs de cycles autorisés pour l'utilisateur de la request.
    None = tous les cycles (pas de filtrage).
    [] = aucun cycle autorisé (données vides).
    """
    return get_cycle_ids(request)
