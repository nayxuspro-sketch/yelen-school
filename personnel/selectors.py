"""Sélecteurs du module personnel : requêtes partagées par la liste et ses exports."""
import uuid

from django.db.models import Q

from .models import MembrePersonnel


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
