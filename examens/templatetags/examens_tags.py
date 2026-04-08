"""
Template tags pour les examens
"""
from django import template

register = template.Library()


@register.simple_tag
def capacite_restante(centre):
    """Calcule la capacité restante d'un centre d'examen."""
    total_capacite = sum(salle.capacite for salle in centre.salles.all())
    nb_candidats = centre.candidats.count()
    return max(total_capacite - nb_candidats, 0)


@register.simple_tag
def total_capacite(centre):
    """Calcule la capacité totale d'un centre d'examen."""
    return sum(salle.capacite for salle in centre.salles.all())