"""Filtre ``autorise_url`` : masque un lien vers une action non autorisée (voir parametres.droits)."""
from django import template

from parametres import droits

register = template.Library()


@register.filter
def autorise_url(request, nom_complet):
    """``{% if request|autorise_url:'pedagogie:evaluation_saisie' %}`` — vrai hors catalogue d'actions."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return False
    return droits.autorise_url(request, nom_complet)
