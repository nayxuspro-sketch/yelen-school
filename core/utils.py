from django.core.management.base import BaseCommand
from django.template.loader import render_to_string


def get_membre_personnel(user):
    """Retourne la fiche MembrePersonnel liée à un utilisateur (ou None).

    Il n'existe pas de FK User → MembrePersonnel : le rapprochement se fait
    par adresse e-mail (insensible à la casse), dans l'établissement de
    l'utilisateur. Le résultat est mis en cache sur l'objet user le temps de
    la requête.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    if hasattr(user, '_membre_personnel_cache'):
        return user._membre_personnel_cache
    from personnel.models import MembrePersonnel
    membre = None
    if user.email:
        qs = MembrePersonnel.objects.filter(email__iexact=user.email)
        if getattr(user, 'etablissement_id', None):
            qs = qs.filter(etablissement_id=user.etablissement_id)
        membre = qs.first()
    user._membre_personnel_cache = membre
    return membre


def filtre_enseignant(user):
    """Valeur à utiliser dans `Enseignement.objects.filter(personnel=...)` pour
    restreindre aux enseignements de l'utilisateur.

    Renvoie la fiche MembrePersonnel, ou None si l'utilisateur n'en a pas
    (dans ce cas, `filter(personnel=None)` ne renvoie rien : sécurité par défaut).
    """
    return get_membre_personnel(user)


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
