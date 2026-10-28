"""Pénalités de retard : une créance « Pénalité de retard » par échéance dépassée et non couverte, selon les
paramètres financiers de l'établissement (mode, valeur, délai de grâce, rubrique)."""
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

from inscriptions.models import StatutInscriptionChoices
from .models import Creance, Echeancier, ModePenalite, OrigineCreance, ParametresFinances


def montant_penalite(params, echeance):
    if params.penalite_mode == ModePenalite.FIXE:
        return params.penalite_valeur.quantize(Decimal('1'))
    if params.penalite_mode == ModePenalite.POURCENT:
        return (echeance.montant_du * params.penalite_valeur / 100).quantize(Decimal('1'))
    return Decimal('0')


def echeances_en_retard(etab, annee, params, aujourdhui=None):
    """Échéances non marquées payées, dépassées du délai de grâce, non couvertes par les versements (cumul des
    échéances dues jusqu'à cette date > total payé) et sans pénalité active."""
    from .views.commun import _situations_financieres_en_lot
    aujourdhui = aujourdhui or timezone.localdate()
    limite = aujourdhui - timezone.timedelta(days=params.penalite_delai_jours)
    echeances = list(
        Echeancier.objects.filter(inscription__annee_scolaire=annee, inscription__classe__etablissement=etab,
                                  is_active=True, paye=False, date_limite__lt=limite)
        .exclude(inscription__statut=StatutInscriptionChoices.ABANDON)
        .exclude(penalites__actif=True, penalites__is_active=True)
        .select_related('inscription__eleve', 'inscription__classe', 'inscription__statut_eleve')
        .order_by('inscription_id', 'date_limite')
    )
    if not echeances:
        return []
    inscriptions = {e.inscription_id: e.inscription for e in echeances}
    situations = _situations_financieres_en_lot(inscriptions.values())
    dues = defaultdict(list)
    for ins_id, date_limite, montant in (Echeancier.objects.filter(inscription_id__in=inscriptions, is_active=True)
                                         .values_list('inscription_id', 'date_limite', 'montant_du')):
        dues[ins_id].append((date_limite, montant))
    retards = []
    for e in echeances:
        du_a_date = sum((m for d, m in dues[e.inscription_id] if d <= e.date_limite), Decimal('0'))
        if situations[e.inscription_id]['total_paye'] < du_a_date:
            retards.append(e)
    return retards


def appliquer_penalites(etab, annee, par, aujourdhui=None):
    """Crée les créances de pénalité manquantes ; renvoie la liste créée. Lève ValueError si non paramétré."""
    params = ParametresFinances.pour(etab)
    if params.penalite_mode == ModePenalite.AUCUNE or params.penalite_valeur <= 0:
        raise ValueError("Les pénalités de retard ne sont pas activées (Finances → Paramètres financiers).")
    if params.penalite_rubrique is None:
        raise ValueError("Choisissez la rubrique d'encaissement des pénalités (Finances → Paramètres financiers).")
    creees = []
    for echeance in echeances_en_retard(etab, annee, params, aujourdhui):
        montant = montant_penalite(params, echeance)
        if montant <= 0:
            continue
        creees.append(Creance.objects.create(
            inscription=echeance.inscription, rubrique=params.penalite_rubrique, origine=OrigineCreance.PENALITE,
            libelle=f"Pénalité de retard — {echeance.libelle} (échéance du {echeance.date_limite:%d/%m/%Y})",
            montant=montant, emise_par=par, echeance=echeance,
        ))
    return creees
