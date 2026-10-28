"""Redevables d'une rubrique : un seul calcul pour le compteur, le PDF et les SMS de relance.

Même règle que le formulaire de paiement et la situation financière de l'élève :
  dû    = tarif actif de la rubrique (niveau × année × statut de l'élève ; 0 sans statut)
          + services souscrits et créances actives portant sur la rubrique
          − bourses actives ciblant la rubrique
  versé = Σ paiements − Σ remboursements de la rubrique
  reste = max(dû − versé, 0), plafonné au reste global de l'élève (bourses globales comprises).
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Max, Sum

from inscriptions.models import Inscription, StatutInscriptionChoices
from parametres.models import TarifScolarite

from .models import AbonnementService, BourseEleve, Creance, Paiement, Remboursement

ZERO = Decimal('0')


@dataclass(frozen=True)
class Redevable:
    inscription: Inscription
    montant_du: Decimal
    verse: Decimal
    reste: Decimal
    echeance: date | None  # dernière échéance saisie sur un versement de la rubrique

    @property
    def eleve(self):
        return self.inscription.eleve


def inscriptions_relancables(etab, annee, classe=None):
    """Inscriptions de l'année (hors abandons) d'une classe — ou de tout l'établissement —, par classe puis élève."""
    qs = Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=etab)
    if classe is not None:
        qs = qs.filter(classe=classe)
    return (
        qs.exclude(statut=StatutInscriptionChoices.ABANDON)
        .select_related('eleve', 'classe', 'classe__cycle', 'statut_eleve')
        .order_by('classe__nom', 'eleve__nom', 'eleve__prenom')
    )


def _sommes(queryset, cle, champ):
    return {ligne[cle]: ligne['s'] or ZERO for ligne in queryset.values(cle).annotate(s=Sum(champ))}


def redevables_rubrique(inscriptions, rubrique):
    """[Redevable] des inscriptions dont le reste à payer de ``rubrique`` est positif, dans l'ordre fourni
    (nombre de requêtes constant, quel que soit le nombre d'élèves)."""
    from .views.commun import _situations_financieres_en_lot  # même règle globale que les listes de redevables

    inscriptions = list(inscriptions)
    ids = [i.pk for i in inscriptions]
    if not ids:
        return []

    tarifs = {}
    lignes = (
        TarifScolarite.objects
        .filter(rubrique=rubrique, actif=True, annee_scolaire_id__in={i.annee_scolaire_id for i in inscriptions})
        .order_by('classe__nom')
        .values_list('classe__niveau', 'annee_scolaire_id', 'statut_eleve_id', 'montant')
    )
    for niveau, annee_id, statut_id, montant in lignes:
        tarifs.setdefault((niveau, annee_id, statut_id), montant)  # plusieurs classes partagent un niveau

    versements = _sommes(Paiement.objects.filter(inscription_id__in=ids, rubrique=rubrique), 'inscription_id', 'montant')
    rembourses = _sommes(Remboursement.objects.filter(paiement__inscription_id__in=ids, paiement__rubrique=rubrique),
                         'paiement__inscription_id', 'montant')
    services = _sommes(AbonnementService.objects.filter(inscription_id__in=ids, actif=True, is_active=True,
                                                        formule__service__rubrique=rubrique),
                       'inscription_id', 'montant_total')
    creances = _sommes(Creance.objects.filter(inscription_id__in=ids, actif=True, is_active=True, rubrique=rubrique),
                       'inscription_id', 'montant')
    bourses = _sommes(BourseEleve.objects.filter(inscription_id__in=ids, actif=True, rubrique=rubrique),
                      'inscription_id', 'montant_accorde')
    echeances = {
        ligne['inscription_id']: ligne['d']
        for ligne in Paiement.objects.filter(inscription_id__in=ids, rubrique=rubrique, echeance__isnull=False)
        .values('inscription_id').annotate(d=Max('echeance'))
    }
    situations = _situations_financieres_en_lot(inscriptions)

    redevables = []
    for inscr in inscriptions:
        tarif = ZERO
        if inscr.statut_eleve_id:
            tarif = tarifs.get((inscr.classe.niveau, inscr.annee_scolaire_id, inscr.statut_eleve_id), ZERO)
        montant_du = max(
            tarif + services.get(inscr.pk, ZERO) + creances.get(inscr.pk, ZERO) - bourses.get(inscr.pk, ZERO), ZERO)
        verse = versements.get(inscr.pk, ZERO) - rembourses.get(inscr.pk, ZERO)
        reste = min(max(montant_du - verse, ZERO), situations[inscr.pk]['reste_a_payer'])
        if reste > 0:
            redevables.append(Redevable(inscr, montant_du, verse, reste, echeances.get(inscr.pk)))
    return redevables
