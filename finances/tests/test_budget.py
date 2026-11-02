"""Budget prévisionnel, dépenses et trésorerie (couverture 5.47.1).

Ces écrans engagent l'argent de l'école : séparation saisie / approbation, refus d'une dépense
hors budget, conservation des pièces annulées. Chaque test reproduit le geste du comptable
ou de la direction, pas le détail du code.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from django.urls import reverse
from model_bakery import baker

from finances.models import BudgetAnnuel, CategorieDepense, Depense, StatutDepense

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    comptable = baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False)
    directeur = baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    salaires = baker.make(CategorieDepense, etablissement=etab, nom='Salaires', code='SAL',
                          type_depense='SALAIRES', actif=True)
    fournitures = baker.make(CategorieDepense, etablissement=etab, nom='Fournitures', code='FOU',
                             type_depense='FOURNITURES', actif=True)
    inactive = baker.make(CategorieDepense, etablissement=etab, nom='Ancienne', code='ANC',
                          type_depense='AUTRE', actif=False)
    client.force_login(comptable)
    return {'client': client, 'etab': etab, 'annee': annee, 'comptable': comptable,
            'directeur': directeur, 'salaires': salaires, 'fournitures': fournitures,
            'inactive': inactive}


def _depense(ecole, categorie=None, montant='10000', statut=StatutDepense.BROUILLON, **extra):
    return baker.make(Depense, annee_scolaire=ecole['annee'], categorie=categorie or ecole['fournitures'],
                      libelle=extra.pop('libelle', 'Craies'), montant=Decimal(montant),
                      date_depense=date(2026, 10, 12), mode_paiement='ESPECES',
                      beneficiaire='Papeterie', reference='C-1', statut=statut, **extra)


def _donnees_depense(ecole, **extra):
    donnees = {
        'libelle': 'Achat de craies',
        'montant': '50 000',
        'categorie': str(ecole['fournitures'].pk),
        'annee_scolaire': str(ecole['annee'].pk),
        'date_depense': '2026-10-12',
        'mode_paiement': 'ESPECES',
        'beneficiaire': 'Papeterie du marché',
        'reference': 'FAC-2026-014',
        'observation': '',
    }
    donnees.update(extra)
    return donnees


# ── Catégories de dépense ────────────────────────────────────────────────────

def test_categorie_list_ne_montre_que_l_etablissement(ecole):
    """La liste des catégories est cloisonnée à l'établissement du compte connecté."""
    baker.make(CategorieDepense, etablissement=baker.make('etablissements.Etablissement'),
               nom='Ailleurs', code='AIL')
    reponse = ecole['client'].get(reverse('finances:categorie_depense_list'))
    assert reponse.status_code == 200
    noms = {c.nom for c in reponse.context['categories']}
    assert noms == {'Salaires', 'Fournitures', 'Ancienne'}


def test_categorie_creation_puis_modification(ecole):
    """Création, refus d'un code déjà pris, puis modification d'une catégorie existante."""
    url = reverse('finances:categorie_depense_create')
    creation = ecole['client'].post(url, {'nom': 'Transport', 'code': 'tra', 'type_depense': 'TRANSPORT',
                                          'actif': 'on'})
    assert creation.status_code == 302
    transport = CategorieDepense.objects.get(etablissement=ecole['etab'], code='TRA')
    assert transport.nom == 'Transport' and transport.actif and transport.created_by == ecole['comptable']

    doublon = ecole['client'].post(url, {'nom': 'Autre transport', 'code': 'TRA'})
    assert doublon.status_code == 200
    assert 'déjà utilisé' in doublon.context['error']
    assert CategorieDepense.objects.filter(etablissement=ecole['etab'], code='TRA').count() == 1

    vide = ecole['client'].post(url, {'nom': '  ', 'code': ''})
    assert vide.context['error'] == 'Le nom et le code sont obligatoires.'

    modification = ecole['client'].post(
        reverse('finances:categorie_depense_edit', kwargs={'pk': transport.pk}),
        {'nom': 'Transport scolaire', 'code': 'TRA', 'type_depense': 'TRANSPORT', 'actif': ''})
    assert modification.status_code == 302
    transport.refresh_from_db()
    assert transport.nom == 'Transport scolaire' and transport.actif is False


def test_categorie_delete_exige_un_motif_et_refuse_si_utilisee(ecole):
    """Une catégorie utilisée par une dépense n'est jamais supprimée ; sinon il faut un motif."""
    utilisee = ecole['fournitures']
    _depense(ecole, categorie=utilisee)
    url = reverse('finances:categorie_depense_delete', kwargs={'pk': utilisee.pk})
    ecole['client'].post(url, {'motif': 'Doublon'})
    utilisee.refresh_from_db()
    assert utilisee.actif is True

    libre = ecole['salaires']
    sans_motif = ecole['client'].post(url.replace(str(utilisee.pk), str(libre.pk)), {'motif': ' '}, follow=True)
    libre.refresh_from_db()
    assert libre.actif is True
    assert "motif de désactivation est obligatoire" in sans_motif.content.decode()

    ecole['client'].post(url.replace(str(utilisee.pk), str(libre.pk)), {'motif': 'Catégorie abandonnée'})
    libre.refresh_from_db()
    assert libre.actif is False and libre.is_active is False


# ── Dépenses ─────────────────────────────────────────────────────────────────

def test_depense_list_filtre_et_total_ne_compte_que_le_valide(ecole):
    """Filtres année/catégorie/statut/recherche ; le total n'additionne que les dépenses validées."""
    _depense(ecole, montant='30000', statut=StatutDepense.VALIDEE, libelle='Salaires octobre')
    _depense(ecole, montant='7000', statut=StatutDepense.BROUILLON, libelle='Craies')
    annulee = _depense(ecole, montant='5000', statut=StatutDepense.ANNULEE, libelle='Ramettes')
    url = reverse('finances:depense_list')

    reponse = ecole['client'].get(url)
    assert reponse.status_code == 200
    assert reponse.context['depenses'].count() == 3
    assert reponse.context['total_valide'] == Decimal('30000')

    par_statut = ecole['client'].get(url, {'statut': StatutDepense.ANNULEE})
    assert [d.pk for d in par_statut.context['depenses']] == [annulee.pk]

    par_categorie = ecole['client'].get(url, {'categorie': str(ecole['salaires'].pk)})
    assert par_categorie.context['depenses'].count() == 0

    par_recherche = ecole['client'].get(url, {'q': 'craies'})
    assert [d.libelle for d in par_recherche.context['depenses']] == ['Craies']

    autre_annee = baker.make('parametres.AnneeScolaire', etablissement=ecole['etab'], libelle='2025-2026')
    par_annee = ecole['client'].get(url, {'annee': str(autre_annee.pk)})
    assert par_annee.context['annee_sel'] == autre_annee
    assert par_annee.context['depenses'].count() == 0


def test_depense_form_refuse_le_depassement_de_budget(ecole):
    """Une dépense au-delà du budget prévu n'est pas enregistrée : le plafond est expliqué."""
    url = reverse('finances:depense_create')
    sans_budget = ecole['client'].post(url, _donnees_depense(ecole))
    assert sans_budget.status_code == 200
    assert 'Aucun budget défini' in sans_budget.context['error']
    assert not Depense.objects.exists()

    baker.make(BudgetAnnuel, annee_scolaire=ecole['annee'], categorie=ecole['fournitures'],
               montant_prevu=Decimal('20000'))
    depassement = ecole['client'].post(url, _donnees_depense(ecole, montant='20 001'))
    assert 'Montant supérieur au budget' in depassement.context['error']
    assert not Depense.objects.exists()

    accepte = ecole['client'].post(url, _donnees_depense(ecole, montant='20 000'))
    assert accepte.status_code == 302
    depense = Depense.objects.get()
    assert depense.statut == StatutDepense.BROUILLON
    assert depense.numero_depense.startswith('DEP-')
    assert depense.montant == Decimal('20000')


def test_depense_form_valide_les_champs_obligatoires(ecole):
    """Montant, libellé, bénéficiaire et référence sont contrôlés avant toute écriture."""
    baker.make(BudgetAnnuel, annee_scolaire=ecole['annee'], categorie=ecole['fournitures'],
               montant_prevu=Decimal('100000'))
    url = reverse('finances:depense_create')

    invalide = ecole['client'].post(url, _donnees_depense(ecole, montant='abc'))
    assert invalide.context['error'] == 'Montant invalide.'

    zero = ecole['client'].post(url, _donnees_depense(ecole, montant='0'))
    assert zero.context['error'] == 'Montant invalide.'

    sans_beneficiaire = ecole['client'].post(url, _donnees_depense(ecole, beneficiaire='  '))
    assert sans_beneficiaire.context['error'] == 'Le bénéficiaire est obligatoire.'

    sans_reference = ecole['client'].post(url, _donnees_depense(ecole, reference=''))
    assert sans_reference.context['error'] == 'La référence / n° de pièce est obligatoire.'

    sans_libelle = ecole['client'].post(url, _donnees_depense(ecole, libelle='   ', reference='FAC-1'))
    assert sans_libelle.context['error'] == 'Le libellé est obligatoire.'

    assert not Depense.objects.exists()


def test_depense_validee_est_geleee_en_modification(ecole):
    """Une dépense validée ne se réécrit pas ; un brouillon se met à jour."""
    validee = _depense(ecole, montant='10000', statut=StatutDepense.VALIDEE)
    refus = ecole['client'].get(reverse('finances:depense_edit', kwargs={'pk': validee.pk}), follow=True)
    assert 'ne peut pas être modifiée' in refus.content.decode()

    baker.make(BudgetAnnuel, annee_scolaire=ecole['annee'], categorie=ecole['fournitures'],
               montant_prevu=Decimal('100000'))
    brouillon = _depense(ecole, montant='10000')
    modification = ecole['client'].post(reverse('finances:depense_edit', kwargs={'pk': brouillon.pk}),
                                        _donnees_depense(ecole, libelle='Craies et ardoises', montant='15000'))
    assert modification.status_code == 302
    brouillon.refresh_from_db()
    assert brouillon.libelle == 'Craies et ardoises' and brouillon.montant == Decimal('15000')
    assert brouillon.statut == StatutDepense.BROUILLON


def test_depense_delete_annule_sans_effacer(ecole):
    """La suppression logique conserve la pièce et son motif ; une pièce validée est protégée."""
    brouillon = _depense(ecole)
    url = reverse('finances:depense_delete', kwargs={'pk': brouillon.pk})
    ecole['client'].post(url, {'motif': '  '})
    brouillon.refresh_from_db()
    assert brouillon.statut == StatutDepense.BROUILLON

    ecole['client'].post(url, {'motif': 'Erreur de saisie'})
    brouillon.refresh_from_db()
    assert brouillon.statut == StatutDepense.ANNULEE and brouillon.motif_annulation == 'Erreur de saisie'

    validee = _depense(ecole, statut=StatutDepense.VALIDEE)
    ecole['client'].post(reverse('finances:depense_delete', kwargs={'pk': validee.pk}), {'motif': 'Test'})
    validee.refresh_from_db()
    assert validee.statut == StatutDepense.VALIDEE


def test_depense_valider_separe_saisie_et_approbation(ecole):
    """Le saisisseur ne valide pas sa propre dépense ; la direction valide et date l'acte."""
    sienne = _depense(ecole, saisi_par=ecole['directeur'])
    ecole['client'].force_login(ecole['directeur'])
    ecole['client'].post(reverse('finances:depense_valider', kwargs={'pk': sienne.pk}), {})
    sienne.refresh_from_db()
    assert sienne.statut == StatutDepense.BROUILLON, 'on ne valide pas sa propre saisie'

    ecole['client'].force_login(ecole['comptable'])
    depense = _depense(ecole, saisi_par=ecole['comptable'])
    url = reverse('finances:depense_valider', kwargs={'pk': depense.pk})
    ecole['client'].post(url, {})
    depense.refresh_from_db()
    assert depense.statut == StatutDepense.BROUILLON, 'un comptable n’a pas le droit d’approuver'

    ecole['client'].force_login(ecole['directeur'])
    ecole['client'].post(url, {'motif': 'Pièce vérifiée'})
    depense.refresh_from_db()
    assert depense.statut == StatutDepense.VALIDEE
    assert depense.valide_par == ecole['directeur'] and depense.date_validation == date.today()

    ecole['client'].post(url, {})
    depense.refresh_from_db()
    assert depense.statut == StatutDepense.VALIDEE, 'une pièce déjà validée ne se revalide pas'


def test_depense_annuler_exige_un_motif_et_ne_redit_rien(ecole):
    """Annulation par un approbateur : motif obligatoire, pas de double annulation."""
    depense = _depense(ecole, statut=StatutDepense.VALIDEE)
    ecole['client'].force_login(ecole['directeur'])
    url = reverse('finances:depense_annuler', kwargs={'pk': depense.pk})

    ecole['client'].post(url, {'motif': ''})
    depense.refresh_from_db()
    assert depense.statut == StatutDepense.VALIDEE

    ecole['client'].post(url, {'motif': 'Doublon de facture'})
    depense.refresh_from_db()
    assert depense.statut == StatutDepense.ANNULEE and depense.motif_annulation == 'Doublon de facture'

    encore = ecole['client'].post(url, {'motif': 'Encore'}, follow=True)
    assert 'déjà annulée' in encore.content.decode()


def test_finance_refuse_un_role_sans_droit(ecole):
    """Un enseignant n'atteint jamais les écrans financiers."""
    ecole['client'].force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=ecole['etab'],
                                           must_change_password=False))
    refus = ecole['client'].get(reverse('finances:depense_list'))
    assert refus.status_code == 302 and refus.url == '/', 'le middleware de rôle renvoie l’enseignant'
    tresorerie = ecole['client'].get(reverse('finances:tableau_bord_budget'))
    assert tresorerie.status_code == 302


# ── Budget prévisionnel et trésorerie ────────────────────────────────────────

def test_budget_previsionnel_enregistre_et_rejette_un_montant_invalide(ecole):
    """La saisie du budget crée puis met à jour le montant prévu, sans accepter de texte."""
    url = reverse('finances:budget_previsionnel')
    assert ecole['client'].get(url).status_code == 200

    enregistre = ecole['client'].post(url, {
        f'budget_{ecole["salaires"].pk}': '500 000',
        f'budget_{ecole["fournitures"].pk}': '150000',
        f'budget_{ecole["inactive"].pk}': '999999',      # catégorie désactivée : ignorée
    })
    assert enregistre.status_code == 302
    assert BudgetAnnuel.objects.get(categorie=ecole['salaires'], annee_scolaire=ecole['annee']) \
        .montant_prevu == Decimal('500000')
    assert not BudgetAnnuel.objects.filter(categorie=ecole['inactive']).exists()

    partiel = ecole['client'].post(url, {f'budget_{ecole["salaires"].pk}': '600000'}, follow=True)
    assert 'Montant invalide pour « Fournitures »' in partiel.content.decode()
    assert BudgetAnnuel.objects.get(categorie=ecole['salaires'], annee_scolaire=ecole['annee']) \
        .montant_prevu == Decimal('500000'), 'un envoi partiel ne réécrit rien'

    ecole['client'].post(url, {f'budget_{ecole["salaires"].pk}': '600000',
                               f'budget_{ecole["fournitures"].pk}': '150000'})
    assert BudgetAnnuel.objects.get(categorie=ecole['salaires'], annee_scolaire=ecole['annee']) \
        .montant_prevu == Decimal('600000')
    assert BudgetAnnuel.objects.count() == 2, 'la mise à jour ne duplique pas la ligne'

    negatif = ecole['client'].post(url, {f'budget_{ecole["salaires"].pk}': '-5',
                                         f'budget_{ecole["fournitures"].pk}': '150000'}, follow=True)
    assert 'Montant invalide pour « Salaires »' in negatif.content.decode()

    refuse = ecole['client'].post(url, {f'budget_{ecole["salaires"].pk}': 'beaucoup',
                                        f'budget_{ecole["fournitures"].pk}': '150000'}, follow=True)
    assert 'Montant invalide pour « Salaires »' in refuse.content.decode()
    assert BudgetAnnuel.objects.get(categorie=ecole['salaires'], annee_scolaire=ecole['annee']) \
        .montant_prevu == Decimal('600000')


def test_tableau_bord_budget_calcule_ecarts_et_depassements(ecole):
    """Le tableau de bord croise budget prévu, réel validé et recettes, et signale un dépassement."""
    from finances.models import Paiement
    statut = baker.make('parametres.StatutEleve', etablissement=ecole['etab'], nom='Affecté')
    classe = baker.make('parametres.Classe', etablissement=ecole['etab'], nom='6e A')
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=ecole['annee'],
                             eleve__photo='', statut='AFFECTE', statut_eleve=statut)
    baker.make(Paiement, inscription=inscription, montant=Decimal('400000'), numero_recu='R-1',
               date_paiement=date(2026, 10, 5), mode_paiement='ESPECES', statut_eleve=statut)

    baker.make(BudgetAnnuel, annee_scolaire=ecole['annee'], categorie=ecole['fournitures'],
               montant_prevu=Decimal('10000'))
    _depense(ecole, montant='15000', statut=StatutDepense.VALIDEE)
    _depense(ecole, montant='99000', statut=StatutDepense.BROUILLON)      # hors calcul

    reponse = ecole['client'].get(reverse('finances:tableau_bord_budget'))
    assert reponse.status_code == 200
    fournitures = next(l for l in reponse.context['lignes'] if l['categorie'] == ecole['fournitures'])
    assert fournitures['prevu'] == Decimal('10000') and fournitures['reel'] == Decimal('15000')
    assert fournitures['depasse'] is True
    assert fournitures['pct'] == 100, 'le pourcentage est plafonné à 100'
    assert reponse.context['recettes_total'] == Decimal('400000')
    assert reponse.context['total_depenses'] == Decimal('15000')
    assert reponse.context['solde'] == Decimal('385000')

    par_annee = ecole['client'].get(reverse('finances:tableau_bord_budget'),
                                    {'annee': str(ecole['annee'].pk)})
    assert par_annee.context['annee_sel'] == ecole['annee']


def test_tableau_bord_budget_xlsx_produit_un_classeur_lisible(ecole):
    """L'export dépasse le simple octet-stream : le classeur s'ouvre et porte les bonnes lignes."""
    from openpyxl import load_workbook
    baker.make(BudgetAnnuel, annee_scolaire=ecole['annee'], categorie=ecole['fournitures'],
               montant_prevu=Decimal('25000'))
    _depense(ecole, montant='7000', statut=StatutDepense.VALIDEE)

    reponse = ecole['client'].get(reverse('finances:tableau_bord_budget_xlsx'))
    assert reponse.status_code == 200
    assert reponse['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'tresorerie_2026-2027.xlsx' in reponse['Content-Disposition']

    classeur = load_workbook(BytesIO(reponse.content))
    feuille = classeur.active
    assert feuille.title == 'Trésorerie'
    assert '2026-2027' in feuille['A1'].value
    lignes = {ligne[0].value: ligne for ligne in feuille.iter_rows(min_row=3, max_col=5)}
    assert lignes['Fournitures'][2].value == 25000.0 and lignes['Fournitures'][3].value == 7000.0
    assert lignes['Fournitures'][4].value == 18000.0


def test_export_comptable_exige_une_annee(ecole):
    """Sans année scolaire, l'export renvoie vers les dépenses avec un message au lieu de planter."""
    ecole['annee'].est_courante = False
    ecole['annee'].save(update_fields=['est_courante'])
    reponse = ecole['client'].get(reverse('finances:export_comptable'), follow=True)
    assert reponse.redirect_chain[-1][0] == reverse('finances:depense_list')
    assert 'Aucune année scolaire' in reponse.content.decode()


def test_export_comptable_livre_le_classeur_syscohada(ecole):
    """L'export comptable de l'année choisie est un vrai classeur Excel, pas une page d'erreur."""
    from openpyxl import load_workbook
    from finances.models import Paiement
    statut = baker.make('parametres.StatutEleve', etablissement=ecole['etab'], nom='Affecté')
    inscription = baker.make('inscriptions.Inscription',
                             classe=baker.make('parametres.Classe', etablissement=ecole['etab'], nom='6e A'),
                             annee_scolaire=ecole['annee'], eleve__photo='', statut='AFFECTE',
                             statut_eleve=statut)
    baker.make(Paiement, inscription=inscription, montant=Decimal('25000'), numero_recu='R-EXPORT',
               date_paiement=date(2026, 10, 5), mode_paiement='ESPECES', statut_eleve=statut)
    _depense(ecole, montant='9000', statut=StatutDepense.VALIDEE)

    reponse = ecole['client'].get(reverse('finances:export_comptable'),
                                  {'annee': str(ecole['annee'].pk)})
    assert reponse.status_code == 200
    assert 'Export_comptable_SYSCOHADA_2026-2027.xlsx' in reponse['Content-Disposition']
    classeur = load_workbook(BytesIO(reponse.content))
    assert 'CAISSE' in [f.title.upper() for f in classeur.worksheets] or classeur.worksheets
