"""Lot F — caisse et familles : journal / arrêté de caisse par caissier, familles et remise fratrie, pénalités de
retard, blocage des bulletins des élèves non à jour, portail parent (reste à payer)."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from finances import caisse, familles, penalites
from finances.blocage import motif_blocage_bulletin
from finances.models import (BourseEleve, ClotureCaisse, Creance, ModePenalite, OrigineCreance, Paiement,
                             ParametresFinances)

pytestmark = pytest.mark.django_db

JOUR = date(2026, 11, 3)


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6e A', niveau='6e', actif=True)
    statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Affecté', actif=True)
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Scolarité', code='SCO', actif=True)
    penalite = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Pénalités', code='PEN', actif=True)
    baker.make('parametres.TarifScolarite', etablissement=etab, annee_scolaire=annee, classe=classe,
               statut_eleve=statut, rubrique=rubrique, montant=Decimal('100000'), actif=True)
    comptable = baker.make('accounts.User', etablissement=etab, role='COMPTABLE', must_change_password=False,
                           first_name='Awa', last_name='SAWADOGO')
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False,
                           first_name='Issa', last_name='KABORE')

    def inscrire(nom, naissance, telephone='70 12 34 56'):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom='Test', date_naissance=naissance,
                           telephone_parent=telephone)
        return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee,
                          statut='AFFECTE', statut_eleve=statut)

    aine = inscrire('OUEDRAOGO', date(2012, 1, 1))
    cadet = inscrire('OUEDRAOGO', date(2014, 6, 1))
    seul = inscrire('ZONGO', date(2013, 3, 3), telephone='76 00 00 00')
    client.force_login(comptable)
    return {'etab': etab, 'annee': annee, 'classe': classe, 'statut': statut, 'rubrique': rubrique, 'penalite': penalite,
            'comptable': comptable, 'directeur': directeur, 'aine': aine, 'cadet': cadet, 'seul': seul}


def _payer(ins, montant, par, jour=JOUR, mode='ESPECES'):
    return baker.make('finances.Paiement', inscription=ins, montant=Decimal(montant), mode_paiement=mode,
                      date_paiement=jour, encaisse_par=par, rubrique=None)


# ── F1 : journal et arrêté de caisse ──────────────────────────────────────────

def test_journal_de_caisse_totaux_par_caissier(client, ecole):
    _payer(ecole['aine'], '30000', ecole['comptable'])
    _payer(ecole['cadet'], '20000', ecole['comptable'], mode='MOBILE_MONEY')
    _payer(ecole['seul'], '15000', ecole['directeur'])
    p = _payer(ecole['seul'], '10000', ecole['comptable'])
    baker.make('finances.Remboursement', paiement=p, montant=Decimal('4000'), motif='Trop-perçu',
               date_remboursement=JOUR, rembourse_par=ecole['comptable'])

    totaux = caisse.totaux_journee(caisse.paiements_du_jour(ecole['etab'], JOUR, ecole['comptable']),
                                   caisse.remboursements_du_jour(ecole['etab'], JOUR, ecole['comptable']))
    assert (totaux['especes'], totaux['mobile_money'], totaux['total_rembourse']) == (40000, 20000, 4000)
    assert totaux['especes_theoriques'] == 36000 and totaux['nb_operations'] == 4

    # Sans paramètre, la page affiche la caisse de l'utilisateur connecté ; « caissier= » vide → toutes.
    reponse = client.get(reverse('finances:journal_caisse') + f'?date={JOUR.isoformat()}')
    assert reponse.context['caissier'] == ecole['comptable'] and reponse.context['totaux']['total'] == 60000
    assert len(caisse.caissiers_du_jour(ecole['etab'], JOUR)) == 2
    toutes = client.get(reverse('finances:journal_caisse') + f'?date={JOUR.isoformat()}&caissier=')
    assert toutes.context['caissier'] is None and toutes.context['totaux']['total'] == 75000


def test_arrete_de_caisse_fige_ecart_et_verrouille_la_journee(client, ecole):
    _payer(ecole['aine'], '30000', ecole['comptable'])
    reponse = client.post(reverse('finances:caisse_arreter'), {'date': JOUR.isoformat(), 'montant_compte': '29000',
                                                                 'observation': 'Billet de 1 000 manquant'})
    assert reponse.status_code == 302
    cloture = ClotureCaisse.objects.get(etablissement=ecole['etab'], caissier=ecole['comptable'], date=JOUR)
    assert (cloture.total_especes, cloture.montant_compte, cloture.ecart) == (30000, 29000, -1000)
    assert cloture.cloture_par == ecole['comptable'] and cloture.nb_operations == 1

    # Deuxième arrêté refusé ; saisie antidatée refusée pour ce caissier, libre pour un autre et le lendemain.
    doublon = client.post(reverse('finances:caisse_arreter'), {'date': JOUR.isoformat(), 'montant_compte': '0'})
    assert doublon.status_code == 302 and ClotureCaisse.objects.count() == 1
    assert 'arrêtée jusqu' in caisse.message_caisse_arretee(ecole['etab'], ecole['comptable'], JOUR)
    assert 'arrêtée jusqu' in caisse.message_caisse_arretee(ecole['etab'], ecole['comptable'], JOUR - timedelta(days=1))
    assert caisse.message_caisse_arretee(ecole['etab'], ecole['comptable'], JOUR + timedelta(days=1)) is None
    assert caisse.message_caisse_arretee(ecole['etab'], ecole['directeur'], JOUR) is None

    avant = Paiement.objects.count()
    refus = client.post(reverse('finances:paiement_create'), {
        'inscription': str(ecole['cadet'].pk), 'date_paiement': JOUR.isoformat(), 'mode_paiement': 'ESPECES',
        'rubrique_ids[]': [str(ecole['rubrique'].pk)], 'montants[]': ['5000'], 'echeances[]': [''],
    })
    assert refus.status_code == 200 and Paiement.objects.count() == avant
    assert any('Votre caisse est arrêtée' in e for e in refus.context['errors'])

    # Réouverture : direction seulement.
    assert client.post(reverse('finances:caisse_rouvrir', kwargs={'pk': cloture.pk})).status_code in (302, 403)
    assert ClotureCaisse.objects.filter(pk=cloture.pk).exists()
    client.force_login(ecole['directeur'])
    client.post(reverse('finances:caisse_rouvrir', kwargs={'pk': cloture.pk}))
    assert not ClotureCaisse.objects.filter(pk=cloture.pk).exists()


def test_journal_de_caisse_pdf(client, ecole):
    pytest.importorskip('weasyprint')
    _payer(ecole['aine'], '30000', ecole['comptable'])
    reponse = client.get(reverse('finances:journal_caisse_pdf') + f'?date={JOUR.isoformat()}')
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'


# ── F2 : familles et remise fratrie ───────────────────────────────────────────

def test_familles_regroupe_par_telephone_et_consolide(client, ecole):
    _payer(ecole['aine'], '60000', ecole['comptable'])
    liste = familles.familles(ecole['etab'], ecole['annee'])
    assert len(liste) == 1
    famille = liste[0]
    assert [e['inscription'] for e in famille['enfants']] == [ecole['aine'], ecole['cadet']]   # aîné d'abord
    assert (famille['total_du'], famille['total_paye'], famille['reste_a_payer']) == (200000, 60000, 140000)
    assert famille['telephone'] == '70 12 34 56'
    assert [e['inscription'] for e in familles.fratrie(ecole['cadet'])] == [ecole['aine']]
    assert familles.fratrie(ecole['seul']) == []

    html = client.get(reverse('finances:familles_list')).content.decode()
    assert 'OUEDRAOGO TEST' in html and 'ZONGO' not in html
    assert client.get(reverse('finances:familles_list') + '?q=zongo').context['familles'] == []
    situation = client.get(reverse('finances:situation_eleve', kwargs={'inscription_id': ecole['cadet'].pk}))
    assert 'Fratrie — autres enfants inscrits' in situation.content.decode()


def test_compte_parent_prime_sur_le_telephone(ecole):
    parent = baker.make('accounts.User', etablissement=ecole['etab'], role='PARENT', must_change_password=False)
    parent.eleves_lies.add(ecole['aine'].eleve, ecole['seul'].eleve)
    liste = {f['cle']: f for f in familles.familles(ecole['etab'], ecole['annee'])}
    assert set(liste) == {f'U:{parent.pk}'}   # le cadet, seul sur son téléphone, ne forme pas une fratrie
    assert [e['inscription'] for e in liste[f'U:{parent.pk}']['enfants']] == [ecole['aine'], ecole['seul']]
    assert liste[f'U:{parent.pk}']['responsable'] == parent.email   # sans nom renseigné, l'e-mail du compte


def test_remise_fratrie_appliquee_a_partir_du_deuxieme_enfant(client, ecole):
    type_bourse = baker.make('finances.TypeBourse', etablissement=ecole['etab'], nom='Remise fratrie', code='FRAT',
                             type_reduction='POURCENTAGE', valeur_reduction=Decimal('10'), actif=True)
    refus = client.post(reverse('finances:remise_fratrie_appliquer'), {'annee': str(ecole['annee'].pk)})
    assert refus.status_code == 302 and not BourseEleve.objects.exists()

    params = ParametresFinances.pour(ecole['etab'])
    params.remise_fratrie = type_bourse
    params.save()
    client.post(reverse('finances:remise_fratrie_appliquer'), {'annee': str(ecole['annee'].pk)})
    bourse = BourseEleve.objects.get()
    assert bourse.inscription == ecole['cadet'] and bourse.montant_accorde == 10000 and bourse.attribue_par == ecole['comptable']

    # Idempotent ; la remise réduit le dû du cadet.
    client.post(reverse('finances:remise_fratrie_appliquer'), {'annee': str(ecole['annee'].pk)})
    assert BourseEleve.objects.count() == 1
    famille = familles.familles(ecole['etab'], ecole['annee'])[0]
    assert famille['total_du'] == 190000 and famille['enfants'][1]['total_reduction'] == 10000


# ── F3 : pénalités de retard et blocage des bulletins ─────────────────────────

def test_penalites_de_retard_sur_echeances_non_couvertes(client, ecole):
    aujourdhui = date(2026, 12, 20)
    for ins in (ecole['aine'], ecole['seul']):
        baker.make('finances.Echeancier', inscription=ins, libelle='1re tranche', date_limite=date(2026, 11, 15),
                   montant_du=Decimal('50000'), paye=False)
        baker.make('finances.Echeancier', inscription=ins, libelle='2e tranche', date_limite=date(2027, 2, 15),
                   montant_du=Decimal('50000'), paye=False)
    _payer(ecole['seul'], '50000', ecole['comptable'])   # 1re tranche couverte sans être cochée « payée »
    baker.make('finances.Echeancier', inscription=ecole['cadet'], libelle='1re tranche', date_limite=date(2026, 12, 16),
               montant_du=Decimal('50000'), paye=False)   # 4 jours de retard < délai de grâce

    params = ParametresFinances.pour(ecole['etab'])
    with pytest.raises(ValueError, match='ne sont pas activées'):
        penalites.appliquer_penalites(ecole['etab'], ecole['annee'], ecole['directeur'], aujourdhui)
    params.penalite_mode, params.penalite_valeur, params.penalite_delai_jours = ModePenalite.POURCENT, Decimal('5'), 7
    params.penalite_rubrique = ecole['penalite']
    params.save()

    creees = penalites.appliquer_penalites(ecole['etab'], ecole['annee'], ecole['directeur'], aujourdhui)
    assert [(c.inscription, c.montant, c.origine) for c in creees] == [(ecole['aine'], 2500, OrigineCreance.PENALITE)]
    assert creees[0].libelle == 'Pénalité de retard — 1re tranche (échéance du 15/11/2026)'
    assert creees[0].rubrique == ecole['penalite'] and creees[0].echeance.libelle == '1re tranche'
    assert penalites.appliquer_penalites(ecole['etab'], ecole['annee'], ecole['directeur'], aujourdhui) == []
    from finances.views.commun import _calcul_situation_financiere
    assert _calcul_situation_financiere(ecole['aine'])['total_du'] == 102500

    # Annulée, la pénalité peut être ré-émise ; la vue réservée à la direction.
    creees[0].annuler('Geste commercial')
    assert len(penalites.appliquer_penalites(ecole['etab'], ecole['annee'], ecole['directeur'], aujourdhui)) == 1
    assert client.post(reverse('finances:penalites_appliquer'), {'annee': str(ecole['annee'].pk)}).status_code in (302, 403)
    client.force_login(ecole['directeur'])
    assert client.get(reverse('finances:echeancier_global')).context['penalites_actives'] is True
    assert client.post(reverse('finances:penalites_appliquer'), {'annee': str(ecole['annee'].pk)}).status_code == 302
    assert Creance.objects.filter(origine=OrigineCreance.PENALITE, actif=True, inscription=ecole['aine'],
                                  echeance__libelle='1re tranche').count() == 1


def test_parametres_financiers_formulaire(client, ecole):
    client.force_login(ecole['directeur'])
    url = reverse('finances:parametres_finances')
    assert client.get(url).status_code == 200
    invalide = client.post(url, {'penalite_mode': 'FIXE', 'penalite_valeur': '0', 'penalite_delai_jours': '7',
                                 'seuil_blocage_pct': '100', 'remise_fratrie_a_partir': '2'})
    assert invalide.status_code == 200 and 'penalite_rubrique' in invalide.context['form'].errors
    valide = client.post(url, {'penalite_mode': 'FIXE', 'penalite_valeur': '2000', 'penalite_delai_jours': '10',
                               'penalite_rubrique': str(ecole['penalite'].pk), 'bloquer_bulletins_impayes': 'on',
                               'seuil_blocage_pct': '50', 'remise_fratrie_a_partir': '3'})
    assert valide.status_code == 302
    params = ParametresFinances.objects.get(etablissement=ecole['etab'])
    assert (params.penalite_mode, params.penalite_valeur, params.bloquer_bulletins_impayes, params.seuil_blocage_pct,
            params.remise_fratrie_a_partir) == ('FIXE', 2000, True, 50, 3)


def test_blocage_des_bulletins_des_eleves_non_a_jour(client, ecole):
    ins = ecole['aine']
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=ecole['annee'], numero=1, nom='T1',
                           date_debut=date(2026, 10, 1), date_fin=date(2026, 12, 20))
    bulletin = baker.make('bulletins.Bulletin', inscription=ins, trimestre=trimestre, est_publie=True,
                          token_signature='tok-aine-0001', token_expire_le=timezone.now() + timedelta(days=30))
    parent = baker.make('accounts.User', etablissement=ecole['etab'], role='PARENT', must_change_password=False)
    parent.eleves_lies.add(ins.eleve)
    assert motif_blocage_bulletin(ins) is None   # blocage inactif

    params = ParametresFinances.pour(ecole['etab'])
    params.bloquer_bulletins_impayes, params.seuil_blocage_pct = True, 50
    params.save()
    _payer(ins, '40000', ecole['comptable'])
    motif = motif_blocage_bulletin(ins)
    assert motif.startswith('Bulletin consultable après régularisation des frais de scolarité : reste à payer 60 000 FCFA')

    client.force_login(parent)
    portail = client.get(reverse('core:portail_parent_bulletins'))
    assert portail.context['enfants'][0]['bulletins'] == [] and 'reste à payer 60 000 FCFA' in portail.content.decode()
    public = Client().get(reverse('bulletins:bulletin_parent_consulter', kwargs={'token': bulletin.token_signature}))
    assert public.status_code == 200 and 'reste à payer 60 000 FCFA' in public.content.decode()
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=parent)
    api = Client().get(reverse('api:eleve_bulletins', kwargs={'pk': ins.eleve.pk}), HTTP_AUTHORIZATION=f'Token {token.key}')
    assert api.status_code == 200 and api.json() == []

    _payer(ins, '10000', ecole['comptable'])   # 50 % atteints
    assert motif_blocage_bulletin(ins) is None
    assert len(client.get(reverse('core:portail_parent_bulletins')).context['enfants'][0]['bulletins']) == 1


# ── F4 : portail parent ───────────────────────────────────────────────────────

def test_portail_parent_affiche_le_reste_a_payer(client, ecole):
    ins = ecole['aine']
    parent = baker.make('accounts.User', etablissement=ecole['etab'], role='PARENT', must_change_password=False)
    parent.eleves_lies.add(ins.eleve)
    p = _payer(ins, '40000', ecole['comptable'])
    baker.make('finances.Remboursement', paiement=p, montant=Decimal('5000'), motif='Trop-perçu', date_remboursement=JOUR)
    baker.make('finances.Echeancier', inscription=ins, libelle='2e tranche', date_limite=date.today() + timedelta(days=30),
               montant_du=Decimal('30000'), paye=False)
    client.force_login(parent)
    reponse = client.get(reverse('core:portail_parent'))
    enfant = reponse.context['enfants'][0]
    assert (enfant['situation']['total_du'], enfant['situation']['total_paye'], enfant['situation']['reste_a_payer']) == (100000, 35000, 65000)
    assert enfant['prochaine_echeance'].libelle == '2e tranche' and enfant['derniers_paiements'] == [p]
    html = reponse.content.decode()
    assert 'Reste à payer' in html and '65000' in html and p.numero_recu in html
