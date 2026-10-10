"""Sélecteurs du module personnel : requêtes partagées par la liste et ses exports."""
import uuid

from django.db.models import Prefetch, Q

from parametres.models import AnneeScolaire

from .models import InscriptionPersonnel, MembrePersonnel


def identifiants_valides(ids):
    """UUID valides d'une chaîne « id1,id2,… » (sélection d'export) ; les autres sont ignorés."""
    valides = []
    for brut in (ids or '').split(','):
        brut = brut.strip()
        if not brut:
            continue
        try:
            valides.append(uuid.UUID(brut))
        except ValueError:
            continue
    return valides


def personnel_filtre(etablissement, query='', inclure_inactifs=False, ids=''):
    """Membres du personnel selon les filtres de la liste (CSV, Excel et PDF partagent cette requête).

    - ``ids`` (sélection par cases à cocher) remplace les autres filtres ;
    - sinon seuls les membres actifs sont renvoyés, sauf ``inclure_inactifs`` (paramètre ``tous=1``) ;
    - ``query`` filtre sur le nom, le prénom ou le matricule.

    Tri alphabétique (nom, prénom), cycles préchargés.
    """
    personnel = MembrePersonnel.objects.prefetch_related('cycles').order_by('nom', 'prenom')
    if etablissement:
        personnel = personnel.filter(etablissement=etablissement)

    selection = identifiants_valides(ids)
    if selection:
        return personnel.filter(pk__in=selection)

    if not inclure_inactifs:
        personnel = personnel.filter(is_active=True)
    if query:
        personnel = personnel.filter(
            Q(nom__icontains=query) |
            Q(prenom__icontains=query) |
            Q(matricule__icontains=query)
        )
    return personnel


def annee_courante(etablissement):
    """Année scolaire courante de l'établissement (None si aucune n'est marquée courante)."""
    if not etablissement:
        return None
    return AnneeScolaire.objects.filter(etablissement=etablissement, est_courante=True).first()


def avec_inscriptions_annee(personnel, annee):
    """Précharge dans ``membre.inscriptions_annee`` les inscriptions actives de ``annee`` (cycle, poste).

    Une seule requête supplémentaire par liste évaluée, quel que soit le nombre de membres ;
    liste vide pour chaque membre si ``annee`` est None.
    """
    inscriptions = InscriptionPersonnel.objects.none()
    if annee is not None:
        inscriptions = (
            InscriptionPersonnel.objects
            .filter(annee_scolaire=annee, est_actif=True)
            .select_related('cycle', 'poste')
            .order_by('cycle__ordre', 'cycle__nom')
        )
    return personnel.prefetch_related(Prefetch('inscriptions', queryset=inscriptions, to_attr='inscriptions_annee'))
