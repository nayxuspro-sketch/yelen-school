import uuid
from decimal import Decimal

from django.db.models import Count


def fcfa(valeur):
    """Montant lisible pour messages et libellés : milliers séparés par une espace insécable, sans décimales
    (« 150 000 FCFA ») — même rendu que ``floatformat:"0g"`` dans les gabarits."""
    return f"{Decimal(valeur or 0):,.0f}".replace(',', '\xa0') + ' FCFA'
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
        # Rien n'interdit deux fiches portant la même adresse (doublon de saisie) : prendre la
        # première au hasard rendait l'enseignant invisible s'il était affecté sur l'autre.
        # On retient la fiche active qui porte réellement des enseignements, à défaut la première.
        membre = (qs.filter(is_active=True)
                  .annotate(_nb_enseignements=Count('enseignements'))
                  .order_by('-_nb_enseignements', 'matricule')
                  .first()) or qs.first()
    user._membre_personnel_cache = membre
    return membre


AUCUNE_FICHE = uuid.UUID(int=0)  # identifiant qui ne correspond à aucune fiche du personnel


def filtre_enseignant(user):
    """Valeur à utiliser dans `Enseignement.objects.filter(personnel=...)` pour
    restreindre aux enseignements de l'utilisateur.

    Renvoie la fiche MembrePersonnel, ou ``AUCUNE_FICHE`` si l'utilisateur n'en
    a pas : le filtre ne renvoie alors rien (sécurité par défaut — avec ``None``
    il renverrait les enseignements sans enseignant, le champ étant nullable).
    """
    return get_membre_personnel(user) or AUCUNE_FICHE


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
