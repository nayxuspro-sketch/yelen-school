from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Permet d'accéder à une valeur de dict par clé dynamique dans un template."""
    if not dictionary:
        return None
    return dictionary.get(str(key))
