from django import template

register = template.Library()


@register.filter
def dict_get(d, key):
    """Return d[key] if d is a dict, otherwise None."""
    if isinstance(d, dict):
        return d.get(key)
    return None
