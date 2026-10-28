"""Familles (fratries) : regroupement des élèves d'une année par responsable, situation consolidée et remise
fratrie automatique (type de bourse appliqué à partir du n-ième enfant)."""
import re
from decimal import Decimal

from django.db.models import Prefetch

from inscriptions.models import Inscription, StatutInscriptionChoices
from .models import BourseEleve, ParametresFinances, TypeReduction


def _telephone(valeur):
    chiffres = re.sub(r'\D', '', valeur or '')
    return chiffres[-8:] if len(chiffres) >= 8 else ''


def cle_famille(eleve):
    """Clé de regroupement : compte parent lié, sinon téléphone du parent ou du tuteur ; '' si inconnu."""
    parent = next(iter(eleve.utilisateurs_lies.all()), None)
    if parent is not None:
        return f"U:{parent.pk}"
    telephone = _telephone(eleve.telephone_parent) or _telephone(eleve.tuteur_telephone)
    return f"T:{telephone}" if telephone else ''


def _responsable(eleve):
    parent = next(iter(eleve.utilisateurs_lies.all()), None)
    if parent is not None:
        return parent.get_full_name() or parent.email
    return eleve.tuteur_nom or eleve.nom_pere or eleve.nom_mere or ''


def familles(etab, annee, minimum=2):
    """Fratries de l'année (au moins ``minimum`` enfants inscrits, hors abandon) avec la situation financière
    de chaque enfant et les totaux de la famille, triées par reste à payer décroissant."""
    from accounts.models import User
    from .views.commun import _situations_financieres_en_lot
    inscriptions = list(
        Inscription.objects.filter(annee_scolaire=annee, classe__etablissement=etab)
        .exclude(statut=StatutInscriptionChoices.ABANDON)
        .select_related('eleve', 'classe', 'statut_eleve')
        .prefetch_related(Prefetch('eleve__utilisateurs_lies', queryset=User.objects.order_by('pk')))
    )
    groupes = {}
    for ins in inscriptions:
        cle = cle_famille(ins.eleve)
        if cle:
            groupes.setdefault(cle, []).append(ins)
    groupes = {cle: membres for cle, membres in groupes.items() if len(membres) >= minimum}
    situations = _situations_financieres_en_lot([i for membres in groupes.values() for i in membres])
    resultat = []
    for cle, membres in groupes.items():
        membres.sort(key=lambda i: (i.eleve.date_naissance, i.eleve.nom, i.eleve.prenom))
        enfants = [{'inscription': i, **situations[i.pk]} for i in membres]
        premier = membres[0].eleve
        resultat.append({
            'cle': cle,
            'responsable': _responsable(premier),
            'telephone': premier.telephone_parent or premier.tuteur_telephone or '',
            'enfants': enfants,
            'total_du': sum((e['total_du'] for e in enfants), Decimal('0')),
            'total_paye': sum((e['total_paye'] for e in enfants), Decimal('0')),
            'reste_a_payer': sum((e['reste_a_payer'] for e in enfants), Decimal('0')),
        })
    resultat.sort(key=lambda f: (-f['reste_a_payer'], f['responsable']))
    return resultat


def fratrie(inscription):
    """Autres enfants de la même famille inscrits la même année (hors abandon), avec leur situation."""
    cle = cle_famille(inscription.eleve)
    if not cle:
        return []
    for famille in familles(inscription.classe.etablissement, inscription.annee_scolaire, minimum=2):
        if famille['cle'] == cle:
            return [e for e in famille['enfants'] if e['inscription'].pk != inscription.pk]
    return []


def montant_remise(type_bourse, total_du_brut):
    if type_bourse.type_reduction == TypeReduction.POURCENTAGE:
        return (total_du_brut * type_bourse.valeur_reduction / 100).quantize(Decimal('1'))
    return min(type_bourse.valeur_reduction, total_du_brut)


def appliquer_remise_fratrie(etab, annee, par):
    """Attribue la remise fratrie paramétrée aux enfants de rang ≥ n de chaque fratrie (aîné d'abord) qui ne
    l'ont pas encore ; renvoie les bourses créées. Lève ValueError si la remise n'est pas paramétrée."""
    params = ParametresFinances.pour(etab)
    type_bourse = params.remise_fratrie
    if type_bourse is None or not type_bourse.actif:
        raise ValueError("Aucune remise fratrie paramétrée : choisissez le type de bourse dans Finances → "
                         "Paramètres financiers.")
    rang_min = max(params.remise_fratrie_a_partir, 2)
    creees = []
    for famille in familles(etab, annee, minimum=rang_min):
        for enfant in famille['enfants'][rang_min - 1:]:
            ins = enfant['inscription']
            if BourseEleve.objects.filter(inscription=ins, type_bourse=type_bourse, actif=True, is_active=True).exists():
                continue
            montant = montant_remise(type_bourse, enfant['total_du_brut'])
            if montant <= 0:
                continue
            creees.append(BourseEleve.objects.create(
                inscription=ins, type_bourse=type_bourse, montant_accorde=montant, rubrique=type_bourse.rubrique,
                attribue_par=par, observation=f"Remise fratrie appliquée automatiquement ({famille['responsable'] or famille['telephone']})",
            ))
    return creees
