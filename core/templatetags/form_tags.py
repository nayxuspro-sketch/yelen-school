"""
Template tags pour les formulaires - Ajoute indicateur champs obligatoires
"""
from django import template

register = template.Library()


@register.filter
def field_label(label):
    """Ajoute une astérisque aux labels des champs obligatoires."""
    if not label:
        return label
    # Si le label contient déjà (optionnel) ou Optionnel, ne pas ajouter *
    if 'optionnel' in label.lower() or 'optionnel' in label.lower() or '(optionnel)' in label.lower():
        return label
    return label


@register.simple_tag
def required_indicator():
    """Retourne l'astérisque pour champ obligatoire."""
    return ' *'