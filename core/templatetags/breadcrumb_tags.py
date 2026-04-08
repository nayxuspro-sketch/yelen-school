"""
Template tag pour générer le fil d'Ariane (breadcrumb)
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def breadcrumb(current_label, **kwargs):
    """Generate breadcrumb with custom items."""
    items = []
    for label, url in kwargs.items():
        if url:
            items.append(f'<a href="{url}" class="breadcrumb-link">{label}</a>')
        else:
            items.append(f'<span class="breadcrumb-current">{label}</span>')
    
    return mark_safe('<span class="breadcrumb-sep">/</span>'.join(items))


@register.simple_tag
def breadcrumb_link(label, url):
    """Generate a breadcrumb link item."""
    return mark_safe(f'<a href="{url}" class="breadcrumb-link">{label}</a>')


@register.simple_tag
def breadcrumb_current(label):
    """Generate current breadcrumb item (not clickable)."""
    return mark_safe(f'<span class="breadcrumb-current">{label}</span>')