from django import template

register = template.Library()

@register.filter(name='dict_get')
def dict_get(dictionary, key):
    """Récupère une valeur d'un dictionnaire par sa clé."""
    if not dictionary:
        return None
    return dictionary.get(key)
