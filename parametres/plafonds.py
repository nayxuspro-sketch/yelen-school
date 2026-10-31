"""Plafonds réglementaires des frais de scolarité des structures privées d'enseignement au Burkina Faso
(décret n° 2026-0761 et arrêté n° 2026-101 du 10 juillet 2026, en vigueur à la rentrée 2026-2027).

Le plafond s'applique au total annuel des frais de scolarité d'un apprenant (dossier, inscription, formation,
examens…), selon le cycle, la catégorie de l'établissement (1 à 3) et sa zone d'implantation (1 à 3).
Les rubriques non soumises (services annexes, frais autorisés par la tutelle) en sont exclues."""
from decimal import Decimal

from .models import IdentiteEtablissement, TarifScolarite

REFERENCE = "décret n° 2026-0761 et arrêté n° 2026-101 du 10/07/2026"

# code du cycle → catégorie → (zone 1, zone 2, zone 3), en FCFA
PLAFONDS = {
    'PRES': {1: (50000, 40000, 30000), 2: (100000, 80000, 50000), 3: (150000, 125000, 75000)},
    'PRIM': {1: (40000, 30000, 25000), 2: (80000, 60000, 40000), 3: (150000, 125000, 60000)},
    'POST': {1: (90000, 80000, 60000), 2: (120000, 100000, 80000), 3: (130000, 110000, 90000)},
    'SEC': {1: (130000, 110000, 90000), 2: (170000, 130000, 110000), 3: (200000, 170000, 140000)},
}


def identite_de(etablissement):
    return IdentiteEtablissement.objects.filter(etablissement=etablissement).first()


def plafond(identite, code_cycle):
    """Plafond annuel (Decimal) ou None si l'établissement n'est pas classé ou le cycle inconnu."""
    if not identite or not identite.categorie_reglementaire or not identite.zone_implantation:
        return None
    grille = PLAFONDS.get(code_cycle or '')
    if not grille:
        return None
    return Decimal(grille[identite.categorie_reglementaire][identite.zone_implantation - 1])


def conformite(etablissement, annee):
    """Lignes (classe × statut) : total des rubriques plafonnées, rubriques hors plafond, plafond, écart."""
    identite = identite_de(etablissement)
    tarifs = (
        TarifScolarite.objects.filter(etablissement=etablissement, annee_scolaire=annee, actif=True)
        .select_related('classe__cycle', 'statut_eleve', 'rubrique')
        .order_by('classe__cycle__ordre', 'classe__niveau', 'classe__nom', 'statut_eleve__ordre', 'rubrique__ordre')
    )
    lignes = {}
    for t in tarifs:
        cle = (t.classe_id, t.statut_eleve_id)
        if cle not in lignes:
            lignes[cle] = {
                'classe': t.classe, 'statut': t.statut_eleve, 'plafonne': Decimal(0), 'hors_plafond': Decimal(0),
                'rubriques': [], 'plafond': plafond(identite, t.classe.cycle.code if t.classe.cycle else None),
            }
        ligne = lignes[cle]
        ligne['plafonne' if t.rubrique.soumise_plafond else 'hors_plafond'] += t.montant
        ligne['rubriques'].append(t)
    for ligne in lignes.values():
        p = ligne['plafond']
        ligne['ecart'] = (p - ligne['plafonne']) if p is not None else None
        ligne['conforme'] = (p is None) or ligne['plafonne'] <= p
    resultat = list(lignes.values())
    return {
        'identite': identite, 'lignes': resultat,
        'classe_connue': bool(identite and identite.categorie_reglementaire and identite.zone_implantation),
        'nb_non_conformes': sum(1 for l in resultat if not l['conforme']),
        'tout_conforme': bool(resultat) and all(l['conforme'] for l in resultat),
    }


def verifier_tarif(etablissement, annee, classe, statut, rubrique, montant, exclure_pk=None):
    """Refuse (ValueError) un tarif qui porterait le total plafonné de la classe/du statut au-delà du plafond."""
    if not rubrique.soumise_plafond:
        return
    p = plafond(identite_de(etablissement), classe.cycle.code if classe.cycle else None)
    if p is None:
        return
    autres = TarifScolarite.objects.filter(
        etablissement=etablissement, annee_scolaire=annee, classe=classe, statut_eleve=statut, actif=True,
        rubrique__soumise_plafond=True,
    ).exclude(rubrique=rubrique)
    if exclure_pk:
        autres = autres.exclude(pk=exclure_pk)
    total = sum((t.montant for t in autres), Decimal(0)) + Decimal(montant)
    if total > p:
        raise ValueError(
            f"Plafond réglementaire dépassé pour {classe.nom} / {statut.nom} : {total:,.0f} F de frais de scolarité "
            f"pour un plafond de {p:,.0f} F ({REFERENCE}). Réduisez le montant ou, s'il s'agit d'un service annexe "
            f"ou d'un frais autorisé par la tutelle, décochez « comptée dans les frais plafonnés » sur la rubrique."
            .replace(',', ' ')
        )
