from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


def get_etablissement_context(etablissement, request=None):
    """
    Retourne le contexte nécessaire pour l'en-tête d'établissement dans les PDF.
    Inclut l'identité de l'établissement et les URLs absolues des logos.
    """
    from parametres.models import IdentiteEtablissement
    
    identite = IdentiteEtablissement.objects.filter(etablissement=etablissement).first()
    
    def get_logo_url(logo_field):
        if logo_field and hasattr(logo_field, 'url'):
            if request:
                return request.build_absolute_uri(logo_field.url)
            return logo_field.url
        return None
    
    logo_url = None
    etab_logo_url = None
    
    if identite and identite.logo:
        logo_url = get_logo_url(identite.logo)
    if etablissement.logo:
        etab_logo_url = get_logo_url(etablissement.logo)
    
    return {
        'identite': identite,
        'etablissement': etablissement,
        'logo_url': logo_url,
        'etab_logo_url': etab_logo_url,
    }
