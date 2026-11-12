"""Sélecteurs du module vacations, limités au périmètre établissement / cycle."""
from django.db.models import Exists, OuterRef, Q

from parametres.models import Classe, Cycle
from personnel.models import MembrePersonnel
from personnel.selectors import membres_visibles
from yelen_school.cycle_filter import filtrer_classe_par_cycle, get_cycle_ids

from .models import BulletinVacation, ContratVacation


def _etablissement(request):
    return getattr(getattr(request, 'user', None), 'etablissement', None)


def classes_vacation_visibles(request, etablissement=None):
    """Classes de l'établissement et des cycles autorisés (toutes si request est absente)."""
    classes = Classe.objects.all()
    if etablissement is None:
        etablissement = _etablissement(request)
    if etablissement is not None:
        classes = classes.filter(etablissement=etablissement)
    if request is not None:
        classes = filtrer_classe_par_cycle(classes, request)
    return classes


def personnel_vacation_visible(request, etablissement=None, inclure_inactifs=False):
    """Personnel du périmètre, y compris les enseignants de classes accessibles."""
    personnel = MembrePersonnel.objects.all()
    if etablissement is None:
        etablissement = _etablissement(request)
    if etablissement is not None:
        personnel = personnel.filter(etablissement=etablissement)
    if not inclure_inactifs:
        personnel = personnel.filter(is_active=True)
    if request is None:
        return personnel

    cycle_ids = get_cycle_ids(request)
    if cycle_ids is None:
        return personnel
    if not cycle_ids:
        return personnel.none()

    membres = membres_visibles(request, personnel)
    classes = classes_vacation_visibles(request, etablissement)
    return personnel.filter(
        Q(pk__in=membres.values('pk')) | Q(enseignements__classe__in=classes)
    ).distinct()


def contrats_vacation_visibles(request, queryset=None):
    """Contrats du périmètre : cycle de l'enseignement, ou cycle du membre sans enseignement."""
    contrats = queryset if queryset is not None else ContratVacation.objects.all()
    etablissement = _etablissement(request)
    if etablissement is not None:
        contrats = contrats.filter(annee_scolaire__etablissement=etablissement)
    if request is None:
        return contrats

    cycle_ids = get_cycle_ids(request)
    if cycle_ids is None:
        return contrats
    if not cycle_ids:
        return contrats.none()

    classes = classes_vacation_visibles(request, etablissement)
    personnel = personnel_vacation_visible(request, etablissement, inclure_inactifs=True)
    return contrats.filter(
        Q(enseignement__classe__in=classes)
        | Q(enseignement__isnull=True, personnel__in=personnel)
    ).distinct()


def _affectation_hors_cycles(personnel_id, cycle_ids):
    """Indique si la fiche du membre porte aussi une affectation hors du périmètre."""
    cycles_hors_perimetre = Cycle.objects.exclude(pk__in=cycle_ids)
    return MembrePersonnel.objects.filter(pk=personnel_id).filter(
        Q(cycles__in=cycles_hors_perimetre)
        | Q(inscriptions__cycle__in=cycles_hors_perimetre)
        | Q(classe_affectation__cycle__in=cycles_hors_perimetre)
    ).exists()


def bulletin_vacation_synthese_visible(request, personnel_id, annee_scolaire_id):
    """Les totaux mensuels sont par membre, pas par cycle : refuse une synthèse mêlant des cycles cachés."""
    if request is None:
        return True
    cycle_ids = get_cycle_ids(request)
    if cycle_ids is None:
        return True
    if not cycle_ids:
        return False

    contrats = ContratVacation.objects.filter(
        personnel_id=personnel_id, annee_scolaire_id=annee_scolaire_id,
    )
    contrat_hors_perimetre = contrats.filter(enseignement__isnull=False).filter(
        Q(enseignement__classe__cycle_id__isnull=True)
        | ~Q(enseignement__classe__cycle_id__in=cycle_ids)
    ).exists()
    if contrat_hors_perimetre:
        return False

    # Un contrat sans enseignement n'a pas de cycle propre ; si le membre est aussi affecté
    # hors périmètre, ses heures ne peuvent pas être séparées de façon sûre dans le bulletin.
    contrat_sans_cycle = contrats.filter(enseignement__isnull=True).exists()
    return not (contrat_sans_cycle and _affectation_hors_cycles(personnel_id, cycle_ids))


def bulletins_vacation_visibles(request, queryset=None):
    """Bulletins limités au périmètre ; une synthèse multi-cycle est masquée si elle inclut un cycle caché."""
    bulletins = queryset if queryset is not None else BulletinVacation.objects.all()
    etablissement = _etablissement(request)
    if etablissement is not None:
        bulletins = bulletins.filter(annee_scolaire__etablissement=etablissement)
    if request is None:
        return bulletins

    cycle_ids = get_cycle_ids(request)
    if cycle_ids is None:
        return bulletins
    if not cycle_ids:
        return bulletins.none()

    personnel = personnel_vacation_visible(request, etablissement, inclure_inactifs=True)
    contrats_hors_perimetre = ContratVacation.objects.filter(
        personnel_id=OuterRef('personnel_id'),
        annee_scolaire_id=OuterRef('annee_scolaire_id'),
        enseignement__isnull=False,
    ).filter(
        Q(enseignement__classe__cycle_id__isnull=True)
        | ~Q(enseignement__classe__cycle_id__in=cycle_ids)
    )
    contrats_sans_cycle = ContratVacation.objects.filter(
        personnel_id=OuterRef('personnel_id'),
        annee_scolaire_id=OuterRef('annee_scolaire_id'),
        enseignement__isnull=True,
    )
    affectations_hors_perimetre = MembrePersonnel.objects.filter(
        pk=OuterRef('personnel_id'),
    ).filter(
        Q(cycles__in=Cycle.objects.exclude(pk__in=cycle_ids))
        | Q(inscriptions__cycle_id__in=Cycle.objects.exclude(pk__in=cycle_ids).values('pk'))
        | Q(classe_affectation__cycle_id__in=Cycle.objects.exclude(pk__in=cycle_ids).values('pk'))
    )
    return bulletins.filter(personnel__in=personnel).annotate(
        _contrat_vacation_hors_perimetre=Exists(contrats_hors_perimetre),
        _contrat_vacation_sans_cycle=Exists(contrats_sans_cycle),
        _affectation_vacation_hors_perimetre=Exists(affectations_hors_perimetre),
    ).filter(
        _contrat_vacation_hors_perimetre=False,
    ).exclude(
        _contrat_vacation_sans_cycle=True,
        _affectation_vacation_hors_perimetre=True,
    ).distinct()
