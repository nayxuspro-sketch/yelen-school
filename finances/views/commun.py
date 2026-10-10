"""Helpers partagés des vues finances (droits, situation financière, validations).

Issu du découpage mécanique de ``finances/views.py`` (octobre 2026) : code inchangé.
"""
from django.db.models import Sum
from django.core.exceptions import PermissionDenied
from decimal import Decimal

try:
    from core.pdf import HTML as WeasyHTML
except Exception:  # ImportError ou OSError (libpango/cairo absents)
    # Les vues PDF vérifient cette valeur avant de générer un document.
    WeasyHTML = None
from ..models import Paiement, Remboursement, BourseEleve
from parametres.models import TarifScolarite
from core.models import RoleChoices
import re as _re


def _numero_valide(numero):
    """Vérifie qu'un numéro ressemble à un numéro mobile valide (BF ou international)."""
    n = _re.sub(r'[\s\-\.]', '', numero or '')
    # +226XXXXXXXX ou 00226XXXXXXXX ou 8 chiffres commençant par 0,5,6,7
    return bool(_re.fullmatch(r'(\+226|00226)?\d{8}', n) and
                _re.search(r'\d{8}$', n))


def _situations_financieres_en_lot(inscriptions):
    """
    Version « en lot » de _calcul_situation_financiere : calcule
    {inscription_id: {'total_du', 'total_paye', 'reste_a_payer'}} pour toutes
    les inscriptions fournies en 4 requêtes agrégées au lieu de 4 par élève.

    Reproduit strictement les mêmes règles :
    - total payé  = Σ paiements − Σ remboursements
    - total dû    = Σ tarifs actifs (niveau × statut_eleve × année), dédoublonnés
                    par rubrique, − Σ bourses actives ; 0 si pas de statut_eleve
    - reste       = max(total dû net − total payé, 0)
    Utilisée par les listes (redevables, PDF) sur des milliers d'inscriptions.
    """
    inscriptions = list(inscriptions)
    ids = [i.pk for i in inscriptions]
    if not ids:
        return {}

    verses = {
        r['inscription_id']: r['s'] or Decimal('0')
        for r in Paiement.objects.filter(inscription_id__in=ids).values('inscription_id').annotate(s=Sum('montant'))
    }
    rembourses = {
        r['paiement__inscription_id']: r['s'] or Decimal('0')
        for r in Remboursement.objects.filter(paiement__inscription_id__in=ids)
        .values('paiement__inscription_id').annotate(s=Sum('montant'))
    }
    bourses = {
        r['inscription_id']: r['s'] or Decimal('0')
        for r in BourseEleve.objects.filter(inscription_id__in=ids, actif=True)
        .values('inscription_id').annotate(s=Sum('montant_accorde'))
    }

    # Tarifs : une seule requête pour toutes les combinaisons (etab, niveau, année, statut)
    combos = {
        (i.classe.etablissement_id, i.classe.niveau, i.annee_scolaire_id, i.statut_eleve_id)
        for i in inscriptions if i.statut_eleve_id
    }
    tarifs_par_combo = {}
    if combos:
        etab_ids = {c[0] for c in combos}
        annee_ids = {c[2] for c in combos}
        statut_ids = {c[3] for c in combos}
        tarifs = (
            TarifScolarite.objects
            .filter(etablissement_id__in=etab_ids, annee_scolaire_id__in=annee_ids,
                    statut_eleve_id__in=statut_ids, actif=True)
            .values_list('etablissement_id', 'classe__niveau', 'annee_scolaire_id',
                         'statut_eleve_id', 'rubrique_id', 'montant')
        )
        for etab_id, niveau, annee_id, statut_id, rubrique_id, montant in tarifs:
            # dédoublonnage par rubrique (comme la version unitaire)
            tarifs_par_combo.setdefault((etab_id, niveau, annee_id, statut_id), {}).setdefault(rubrique_id, montant)

    result = {}
    for i in inscriptions:
        total_paye = verses.get(i.pk, Decimal('0')) - rembourses.get(i.pk, Decimal('0'))
        if not i.statut_eleve_id:
            result[i.pk] = {'total_du': Decimal('0'), 'total_paye': total_paye, 'reste_a_payer': Decimal('0')}
            continue
        combo = (i.classe.etablissement_id, i.classe.niveau, i.annee_scolaire_id, i.statut_eleve_id)
        total_du = sum(tarifs_par_combo.get(combo, {}).values(), Decimal('0'))
        total_du_net = max(total_du - bourses.get(i.pk, Decimal('0')), Decimal('0'))
        result[i.pk] = {
            'total_du': total_du_net,
            'total_paye': total_paye,
            'reste_a_payer': max(total_du_net - total_paye, Decimal('0')),
        }
    return result


def _require_finance_role(request, roles):
    if getattr(request.user, 'role', None) not in roles:
        raise PermissionDenied("Action financière non autorisée pour ce rôle.")


def _require_same_establishment(request, inscription):
    """Refuse tout objet hors établissement, sauf au Super Admin global."""
    if getattr(request.user, 'role', None) == RoleChoices.SUPER_ADMIN:
        return

    user_etab = getattr(request.user, 'etablissement_id', None)
    if user_etab is None or inscription.classe.etablissement_id != user_etab:
        raise PermissionDenied("Cette opération concerne un autre établissement.")


def _calcul_situation_financiere(inscription):
    """
    Calcule Total DÛ, Total payé, Reste à payer pour une inscription.

    - Total DÛ  : somme des tarifs actifs niveau × statut_eleve × annee,
                  dédoublonnés par rubrique. 0 si statut_eleve non configuré.
                  Les bourses/aides actives sont déduites du total dû.
    - Total payé: somme de tous les paiements enregistrés pour l'inscription.
    - Reste     : Total DÛ net – Total payé (jamais négatif pour le reste affiché).
    """
    etablissement = inscription.classe.etablissement
    paiements = Paiement.objects.filter(inscription=inscription).select_related('rubrique')
    total_verse = paiements.aggregate(s=Sum('montant'))['s'] or Decimal('0')
    total_rembourse = (
        Remboursement.objects
        .filter(paiement__inscription=inscription, is_active=True)
        .aggregate(s=Sum('montant'))['s'] or Decimal('0')
    )
    total_paye = total_verse - total_rembourse

    # Bourses actives pour cette inscription
    bourses = BourseEleve.objects.filter(
        inscription=inscription, actif=True, is_active=True,
    ).select_related('type_bourse', 'rubrique')

    # Sans statut_eleve, impossible de déterminer les frais — total_du = 0
    if not inscription.statut_eleve_id:
        total_reduction = bourses.aggregate(s=Sum('montant_accorde'))['s'] or Decimal('0')
        return {
            'total_du': Decimal('0'),
            'total_paye': total_paye,
            'total_rembourse': total_rembourse,
            'total_reduction': total_reduction,
            'reste_a_payer': Decimal('0'),
            'frais_details': [],
            'use_tarifs': False,
            'paiements': paiements,
            'bourses': bourses,
        }

    tarifs_qs = TarifScolarite.objects.filter(
        etablissement=etablissement,
        classe__niveau=inscription.classe.niveau,
        annee_scolaire=inscription.annee_scolaire,
        statut_eleve=inscription.statut_eleve,
        actif=True,
    ).select_related('rubrique').order_by('rubrique__ordre', 'rubrique__nom')

    # Dédoublonner par rubrique (plusieurs classes peuvent partager le même niveau)
    seen = set()
    frais_details = []
    total_du = Decimal('0')
    for t in tarifs_qs:
        if t.rubrique_id not in seen:
            seen.add(t.rubrique_id)
            frais_details.append(t)
            total_du += t.montant

    # Déduire les bourses/aides scolaires
    total_reduction = bourses.aggregate(s=Sum('montant_accorde'))['s'] or Decimal('0')
    total_du_net = max(total_du - total_reduction, Decimal('0'))

    reste_a_payer = max(total_du_net - total_paye, Decimal('0'))

    return {
        'total_du': total_du_net,
        'total_du_brut': total_du,
        'total_paye': total_paye,
        'total_rembourse': total_rembourse,
        'total_reduction': total_reduction,
        'reste_a_payer': reste_a_payer,
        'frais_details': frais_details,
        'use_tarifs': bool(frais_details),
        'paiements': paiements,
        'bourses': bourses,
    }


def _payment_overage_errors(inscription, lignes):
    """Recalcule les plafonds sous verrou logique de l'inscription."""
    etablissement = inscription.classe.etablissement
    errors = []
    seen = set()
    for rubrique, montant, _echeance in lignes:
        if rubrique.etablissement_id != etablissement.pk:
            errors.append(f"La rubrique « {rubrique} » appartient à un autre établissement.")
            continue
        if rubrique.pk in seen:
            errors.append(f"La rubrique « {rubrique.nom} » est répétée dans le paiement.")
            continue
        seen.add(rubrique.pk)
        deja_verse = (
            Paiement.objects.filter(inscription=inscription, rubrique=rubrique)
            .aggregate(Sum('montant'))['montant__sum'] or Decimal('0')
        )
        tarif_qs = TarifScolarite.objects.filter(
            etablissement=etablissement,
            classe__niveau=inscription.classe.niveau,
            annee_scolaire=inscription.annee_scolaire,
            actif=True,
            rubrique=rubrique,
        )
        if inscription.statut_eleve_id:
            tarif_qs = tarif_qs.filter(statut_eleve=inscription.statut_eleve)
        tarif = tarif_qs.first()
        if tarif:
            reste = Decimal(str(tarif.montant)) - deja_verse
            if montant > reste:
                errors.append(
                    f"« {rubrique.nom} » : montant versé {montant:,.0f} FCFA "
                    f"dépasse le reste à payer {max(reste, Decimal('0')):,.0f} FCFA."
                )
    return errors
