"""Export comptable SYSCOHADA (5.40.0) : journal de caisse des recettes, journal des dépenses et récapitulatif par
compte, en Excel — pour le comptable externe tenu à une comptabilité en partie double.

Comptes utilisés (plan comptable SYSCOHADA révisé, version simplifiée du système normal) :

| Flux | Débit | Crédit |
|---|---|---|
| Frais de scolarité, inscription, examen | 571 Caisse / 521 Banque | **706** Prestations de services |
| Services annexes (cantine, transport, internat) | 571 / 521 | **707** Produits accessoires |
| Dépenses de personnel | **661** Charges de personnel | 571 / 521 |
| Fournitures et matériel | **604** Achats stockés de matières et fournitures | 571 / 521 |
| Maintenance, eau-électricité, communication | **624/628** Entretien, fournitures non stockables, divers | 571 / 521 |
| Transport | **625** Déplacements, missions et réceptions | 571 / 521 |
| Formation | **633** Formation du personnel | 571 / 521 |
| Autres dépenses | **658** Charges diverses | 571 / 521 |

Les numéros de compte sont modifiables dans ``COMPTES_DEPENSES`` sans toucher aux vues."""
from collections import defaultdict
from decimal import Decimal

from core.excel import ExcelExport

CAISSE = '571'
BANQUE = '521'
SCOLARITE = '706'
ACCESSOIRES = '707'

COMPTES_DEPENSES = {
    'SALAIRES': ('661', 'Charges de personnel'),
    'FOURNITURES': ('604', 'Achats stockés de matières et fournitures'),
    'MAINTENANCE': ('624', 'Entretien et réparations'),
    'UTILITIES': ('605', 'Achats de fournitures non stockables (eau, énergie)'),
    'COMMUNICATION': ('628', 'Frais de télécommunication et divers'),
    'TRANSPORT': ('625', 'Déplacements, missions et réceptions'),
    'FORMATION': ('633', 'Formation du personnel'),
    'AUTRE': ('658', 'Charges diverses'),
}
# Rubriques dont le code fait d'elles un service annexe (produit accessoire 707)
CODES_ACCESSOIRES = ('CANT', 'TRANS', 'INT', 'INTERNAT', 'CANTINE', 'TRANSPORT')


def _compte_tresorerie(mode):
    return BANQUE if mode in ('VIREMENT', 'CHEQUE', 'MOBILE_MONEY') else CAISSE


def _compte_recette(rubrique):
    code = (rubrique.code or '').upper() if rubrique else ''
    return ACCESSOIRES if any(code.startswith(prefixe) for prefixe in CODES_ACCESSOIRES) else SCOLARITE


def ecritures(etablissement, annee):
    """Écritures du journal (recettes puis dépenses) et totaux par compte, pour l'année scolaire ``annee``."""
    from finances.models import Depense, Paiement, StatutDepense

    lignes = []
    for p in (Paiement.objects.filter(inscription__annee_scolaire=annee, inscription__classe__etablissement=etablissement)
              .select_related('inscription__eleve', 'inscription__classe', 'rubrique').order_by('date_paiement', 'created_at')):
        ligne = {
            'journal': 'CAISSE', 'date': p.date_paiement,
            'piece': p.numero_recu or f'PAI-{p.pk.hex[:8].upper()}',
            'libelle': f"{p.rubrique.nom if p.rubrique else 'Frais'} — "
                       f"{p.inscription.eleve.get_nom_complet()} ({p.inscription.classe.nom})",
            'compte_debit': _compte_tresorerie(p.mode_paiement), 'compte_credit': _compte_recette(p.rubrique),
            'montant': p.montant, 'mode': p.get_mode_paiement_display(), 'reference': p.reference or '',
        }
        ligne['libelle_compte'] = ('Caisse' if ligne['compte_debit'] == CAISSE else 'Banque') + ' / ' + (
            'Prestations de services (706)' if ligne['compte_credit'] == SCOLARITE else 'Produits accessoires (707)')
        lignes.append(ligne)
    for d in (Depense.objects.filter(annee_scolaire=annee, statut=StatutDepense.VALIDEE)
              .select_related('categorie').order_by('date_depense', 'numero_depense')):
        numero, libelle = COMPTES_DEPENSES.get((d.categorie.type_depense if d.categorie else 'AUTRE'), COMPTES_DEPENSES['AUTRE'])
        lignes.append({
            'journal': 'DEPENSES', 'date': d.date_depense, 'piece': d.numero_depense,
            'libelle': d.libelle, 'compte_debit': numero, 'compte_credit': _compte_tresorerie(d.mode_paiement),
            'montant': d.montant, 'mode': d.get_mode_paiement_display(), 'reference': d.reference or '',
            'libelle_compte': libelle,
        })
    totaux = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0')})
    for ligne in lignes:
        totaux[ligne['compte_debit']]['debit'] += ligne['montant']
        totaux[ligne['compte_credit']]['credit'] += ligne['montant']
    return lignes, dict(sorted(totaux.items()))


def classe_comptes():
    """Libellé de chaque compte utilisé (pour le récapitulatif)."""
    libelles = {CAISSE: 'Caisse', BANQUE: 'Banques', SCOLARITE: 'Prestations de services',
                ACCESSOIRES: 'Produits accessoires'}
    libelles.update({numero: libelle for numero, libelle in COMPTES_DEPENSES.values()})
    return libelles


def classeur(etablissement, annee):
    """Classeur Excel : Journal de caisse, Journal des dépenses, Récapitulatif par compte."""
    lignes, totaux = ecritures(etablissement, annee)
    libelles = classe_comptes()
    wb = ExcelExport('Export comptable SYSCOHADA')
    wb.add_title(f"Journal comptable — {etablissement.nom}",
                 f"Année scolaire {annee.libelle} · plan comptable SYSCOHADA · édité le "
                 f"{__import__('datetime').date.today().strftime('%d/%m/%Y')}")
    entete = ['Date', 'Pièce', 'Libellé', 'Compte débit', 'Compte crédit', 'Débit (FCFA)', 'Crédit (FCFA)',
              'Mode', 'Référence']
    for journal, titre in (('CAISSE', 'Journal de caisse — recettes (journaux AC)'),
                           ('DEPENSES', 'Journal des dépenses (journal DE)')):
        selection = [ligne for ligne in lignes if ligne['journal'] == journal]
        wb.add_header([titre])
        wb.add_header(entete)
        for ligne in selection:
            wb.add_row([ligne['date'].strftime('%d/%m/%Y'), ligne['piece'], ligne['libelle'],
                        f"{ligne['compte_debit']} {libelles.get(ligne['compte_debit'], '')}",
                        f"{ligne['compte_credit']} {libelles.get(ligne['compte_credit'], '')}",
                        float(ligne['montant']), float(ligne['montant']), ligne['mode'], ligne['reference']])
        total = sum((ligne['montant'] for ligne in selection), Decimal('0'))
        wb.add_row(['', '', f"TOTAL {titre.split(' —')[0]}", '', '', float(total), float(total), '', ''])
        wb.add_separator()
    wb.add_header(['Récapitulatif par compte', 'Libellé du compte', 'Total débit', 'Total crédit', 'Solde'])
    for numero, valeurs in totaux.items():
        wb.add_row([numero, libelles.get(numero, ''), float(valeurs['debit']), float(valeurs['credit']),
                    float(valeurs['debit'] - valeurs['credit'])])
    return wb
