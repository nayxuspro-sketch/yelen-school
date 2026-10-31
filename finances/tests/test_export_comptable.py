"""Export comptable SYSCOHADA (5.40.0) : comptes par nature de flux, périmètre, fichier Excel et récapitulatif."""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from django.urls import reverse
from model_bakery import baker

from finances.export_comptable import ecritures

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='Collège Yelen')
    client.force_login(baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6e A')
    statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Affecté')
    eleve = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Awa', date_naissance=date(2012, 1, 1), photo='')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=annee, classe=classe,
                             statut='AFFECTE', statut_eleve=statut)
    scol = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Scolarité', code='SCOL', actif=True)
    cant = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Cantine', code='CANT', actif=True)
    baker.make('finances.Paiement', inscription=inscription, montant=Decimal('50000'), rubrique=scol, statut_eleve=statut,
               date_paiement=date(2026, 10, 5), mode_paiement='ESPECES', numero_recu='R-001')
    baker.make('finances.Paiement', inscription=inscription, montant=Decimal('10000'), rubrique=cant, statut_eleve=statut,
               date_paiement=date(2026, 10, 6), mode_paiement='MOBILE_MONEY', numero_recu='R-002')
    salaires = baker.make('finances.CategorieDepense', etablissement=etab, nom='Salaires', code='SAL',
                          type_depense='SALAIRES', actif=True)
    fournitures = baker.make('finances.CategorieDepense', etablissement=etab, nom='Fournitures', code='FOU',
                             type_depense='FOURNITURES', actif=True)
    baker.make('finances.Depense', annee_scolaire=annee, categorie=salaires, numero_depense='D-001',
               libelle='Salaires enseignants', montant=Decimal('80000'), date_depense=date(2026, 10, 31),
               mode_paiement='VIREMENT', beneficiaire='Personnel', reference='VIR-1', statut='VALIDEE')
    baker.make('finances.Depense', annee_scolaire=annee, categorie=fournitures, numero_depense='D-002',
               libelle='Craies', montant=Decimal('5000'), date_depense=date(2026, 10, 12), mode_paiement='ESPECES',
               beneficiaire='Papeterie', reference='C-1', statut='BROUILLON')      # brouillon : exclu
    return {'etab': etab, 'annee': annee}


def test_comptes_par_nature_de_flux(ecole):
    lignes, totaux = ecritures(ecole['etab'], ecole['annee'])
    recettes = {l['piece']: l for l in lignes if l['journal'] == 'CAISSE'}
    assert (recettes['R-001']['compte_debit'], recettes['R-001']['compte_credit']) == ('571', '706')
    assert (recettes['R-002']['compte_debit'], recettes['R-002']['compte_credit']) == ('521', '707')
    (depense,) = [l for l in lignes if l['journal'] == 'DEPENSES']
    assert (depense['piece'], depense['compte_debit'], depense['compte_credit']) == ('D-001', '661', '521')
    assert totaux['571'] == {'debit': Decimal('50000'), 'credit': Decimal('0')}
    assert totaux['521'] == {'debit': Decimal('10000'), 'credit': Decimal('80000')}
    assert totaux['706']['credit'] == Decimal('50000') and totaux['707']['credit'] == Decimal('10000')
    assert totaux['661']['debit'] == Decimal('80000')


def test_fichier_excel(client, ecole):
    from openpyxl import load_workbook
    reponse = client.get(reverse('finances:export_comptable'), {'annee': ecole['annee'].pk})
    assert reponse.status_code == 200
    assert reponse['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'Export_comptable_SYSCOHADA_2026-2027.xlsx' in reponse['Content-Disposition']
    feuille = load_workbook(BytesIO(reponse.content)).active
    valeurs = [[c.value for c in ligne] for ligne in feuille.iter_rows()]
    plat = '\n'.join(' | '.join(str(v) for v in ligne if v is not None) for ligne in valeurs)
    assert 'Journal de caisse' in plat and 'R-001' in plat and '706' in plat
    assert 'D-001' in plat and '661' in plat and 'Craies' not in plat
    assert 'Récapitulatif par compte' in plat
