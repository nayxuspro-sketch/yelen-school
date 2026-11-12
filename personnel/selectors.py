"""Sélecteurs du module personnel : requêtes partagées par les vues et leurs exports."""
import uuid

from django.db.models import Prefetch, Q

from parametres.models import AnneeScolaire, Cycle
from yelen_school.cycle_filter import get_cycle_ids

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


def cycles_accessibles(request, etablissement=None):
    """Cycles que le compte peut consulter, éventuellement limités à un établissement."""
    cycles = Cycle.objects.all()
    if etablissement is not None:
        cycles = cycles.filter(etablissement=etablissement)
    if request is not None:
        cycle_ids = get_cycle_ids(request)
        if cycle_ids is not None:
            cycles = cycles.filter(pk__in=cycle_ids)
    return cycles


def filtrer_membres_par_cycle_ids(queryset, cycle_ids):
    """Conserve les membres affectés à au moins un cycle de ``cycle_ids``.

    Une affectation peut être portée par la fiche (cycles), l'inscription annuelle
    (inscriptions.cycle) ou la classe de rattachement de l'enseignant.
    ``None`` signifie que le compte voit tous les cycles ; une liste vide n'en donne aucun.
    """
    if cycle_ids is None:
        return queryset
    if not cycle_ids:
        return queryset.none()
    return queryset.filter(
        Q(cycles__in=cycle_ids)
        | Q(inscriptions__cycle_id__in=cycle_ids)
        | Q(classe_affectation__cycle_id__in=cycle_ids)
    ).distinct()


def membres_visibles(request, queryset=None):
    """Queryset de membres limité à l'établissement et aux cycles accessibles du compte."""
    if queryset is None:
        queryset = MembrePersonnel.objects.all()
        etablissement = getattr(getattr(request, 'user', None), 'etablissement', None)
        if etablissement is not None:
            queryset = queryset.filter(etablissement=etablissement)
    if request is None:
        return queryset
    return filtrer_membres_par_cycle_ids(queryset, get_cycle_ids(request))


def membres_dans_cycle(queryset, cycle):
    """Membres affectés à ``cycle`` par leur fiche, leur inscription ou leur classe."""
    return queryset.filter(
        Q(cycles=cycle)
        | Q(inscriptions__cycle=cycle)
        | Q(classe_affectation__cycle=cycle)
    ).distinct()


def inscriptions_visibles(queryset, request):
    """Inscriptions annuelles limitées aux cycles autorisés du compte."""
    if request is None:
        return queryset
    cycle_ids = get_cycle_ids(request)
    if cycle_ids is None:
        return queryset
    if not cycle_ids:
        return queryset.none()
    return queryset.filter(cycle_id__in=cycle_ids)


def filtrer_par_membres_visibles(queryset, request, personnel_field='personnel'):
    """Filtre un queryset lié à un membre (paie, congé, pointage, évaluation…) par cycle."""
    if request is None:
        return queryset
    membres = membres_visibles(request)
    return queryset.filter(**{f'{personnel_field}__in': membres}).distinct()


def absences_visibles(queryset, request):
    """Absences d'agents accessibles, avec restriction supplémentaire sur le cycle de la classe."""
    queryset = filtrer_par_membres_visibles(queryset, request)
    if request is None:
        return queryset
    cycle_ids = get_cycle_ids(request)
    if cycle_ids is not None:
        queryset = queryset.filter(Q(classe__isnull=True) | Q(classe__cycle_id__in=cycle_ids))
    return queryset


def personnel_filtre(etablissement, query='', inclure_inactifs=False, ids='', request=None):
    """Membres du personnel selon les filtres de la liste (CSV, Excel et PDF partagent cette requête).

    - ``ids`` (sélection par cases à cocher) remplace les filtres métier, jamais le périmètre d'accès ;
    - sinon seuls les membres actifs sont renvoyés, sauf ``inclure_inactifs`` (paramètre ``tous=1``) ;
    - ``query`` filtre sur le nom, le prénom ou le matricule ;
    - ``request`` applique le périmètre de cycles du compte (et filtre aussi les cycles préchargés).

    Tri alphabétique (nom, prénom), cycles préchargés.
    """
    cycles = Cycle.objects.all()
    if etablissement is not None:
        cycles = cycles.filter(etablissement=etablissement)
    if request is not None:
        cycle_ids = get_cycle_ids(request)
        if cycle_ids is not None:
            cycles = cycles.filter(pk__in=cycle_ids)
    personnel = MembrePersonnel.objects.prefetch_related(
        Prefetch('cycles', queryset=cycles)
    ).order_by('nom', 'prenom')
    if etablissement is not None:
        personnel = personnel.filter(etablissement=etablissement)
    personnel = membres_visibles(request, personnel)

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


def avec_inscriptions_annee(personnel, annee, request=None):
    """Précharge les inscriptions actives et accessibles de ``annee`` (cycle, poste).

    Une seule requête supplémentaire par liste évaluée, quel que soit le nombre de membres ;
    liste vide pour chaque membre si ``annee`` est None ou si aucun cycle n'est accessible.
    """
    inscriptions = InscriptionPersonnel.objects.none()
    if annee is not None:
        inscriptions = InscriptionPersonnel.objects.filter(annee_scolaire=annee, est_actif=True)
        inscriptions = inscriptions_visibles(inscriptions, request)
        inscriptions = inscriptions.select_related('cycle', 'poste').order_by('cycle__ordre', 'cycle__nom')
    return personnel.prefetch_related(
        Prefetch('inscriptions', queryset=inscriptions, to_attr='inscriptions_annee')
    )
