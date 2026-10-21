"""Paiement Mobile Money en ligne (CinetPay) : lien de paiement, vérification active, droits."""
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from model_bakery import baker

from finances.models import DemandePaiementMobile, Paiement
from finances.paiements_mobiles import ErreurPasserelle, verifier_paiement
from finances.releves import importer_releve

CONFIG = dict(CINETPAY_API_KEY='cle', CINETPAY_SITE_ID='123', CINETPAY_URL_PUBLIQUE='https://ecole.bf/')
LIEN = 'https://checkout.cinetpay.com/payment/jeton-abc'
REPONSE_LIEN = {'code': '201', 'message': 'CREATED', 'data': {'payment_token': 'jeton-abc', 'payment_url': LIEN}}


def _acceptee(montant='25000', operateur='OM260503.1234.A1'):
    return {'code': '00', 'message': 'SUCCES', 'data': {
        'amount': montant, 'currency': 'XOF', 'status': 'ACCEPTED', 'payment_method': 'OMBF',
        'operator_id': operateur, 'payment_date': '2026-10-21 10:00:00'}}


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement')


@pytest.fixture
def comptable(etab):
    return baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False)


@pytest.fixture
def comptable_client(client, comptable):
    client.force_login(comptable)
    return client


@pytest.fixture
def inscription(etab):
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle', etablissement=etab))
    eleve = baker.make('inscriptions.Eleve', nom='OUÉDRAOGO', prenom='Awa', matricule='ETAB-2026-07')
    return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee,
                      statut='AFFECTE', est_exonere=False)


@pytest.fixture
def demande(inscription, comptable):
    return DemandePaiementMobile.objects.create(inscription=inscription, montant=Decimal('25000'),
                                                telephone='70123456', cree_par=comptable)


@pytest.fixture
def demande_avec_lien(demande):
    demande.lien_paiement, demande.jeton_paiement = LIEN, 'jeton-abc'
    demande.save(update_fields=['lien_paiement', 'jeton_paiement'])
    return demande


@pytest.mark.django_db
class TestCreationDuLien:
    def test_creation_envoie_le_lien_par_sms(self, settings, comptable_client, inscription):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        with patch('finances.paiements_mobiles._appeler', return_value=REPONSE_LIEN) as appel, \
                patch('core.sms.envoyer_sms', return_value=(True, '')) as sms:
            reponse = comptable_client.post(reverse('finances:mobile_money_create'), {
                'inscription': str(inscription.pk), 'montant': '25000', 'telephone': '70123456'}, follow=True)
        demande = DemandePaiementMobile.objects.get()
        assert (demande.lien_paiement, demande.jeton_paiement, demande.sms_envoye) == (LIEN, 'jeton-abc', True)

        chemin, donnees = appel.call_args.args
        assert chemin == '/payment'
        assert (donnees['transaction_id'], donnees['amount'], donnees['currency'], donnees['channels']) == (
            demande.reference, 25000, 'XOF', 'MOBILE_MONEY')
        assert donnees['notify_url'] == donnees['return_url'] == 'https://ecole.bf/'
        assert donnees['invoice_data'] == {'Eleve': 'OUEDRAOGO Awa', 'Matricule': 'ETAB-2026-07', 'Rubrique': 'Scolarite'}
        assert '#' not in donnees['description'] and 'OUEDRAOGO' in donnees['description']

        numero, message = sms.call_args.args
        assert numero == '70123456' and LIEN in message and '*144#' not in message
        assert sms.call_args.kwargs == {'limite': 320}
        assert 'Lien de paiement en ligne inclus.' in reponse.content.decode()

    def test_passerelle_injoignable_bascule_sur_les_instructions_ussd(self, settings, comptable_client, inscription):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        with patch('finances.paiements_mobiles._appeler', side_effect=ErreurPasserelle('passerelle injoignable')), \
                patch('core.sms.envoyer_sms', return_value=(True, '')) as sms:
            reponse = comptable_client.post(reverse('finances:mobile_money_create'), {
                'inscription': str(inscription.pk), 'montant': '25000', 'telephone': '70123456'}, follow=True)
        demande = DemandePaiementMobile.objects.get()
        assert demande.lien_paiement == '' and demande.statut == 'EN_ATTENTE'
        assert '*144#' in sms.call_args.args[1]
        html = reponse.content.decode()
        assert 'Lien de paiement en ligne indisponible' in html and f'Demande {demande.reference} créée' in html

    def test_sans_configuration_aucun_appel(self, comptable_client, inscription):
        with patch('finances.paiements_mobiles._appeler') as appel, patch('core.sms.envoyer_sms', return_value=(False, '')):
            comptable_client.post(reverse('finances:mobile_money_create'), {
                'inscription': str(inscription.pk), 'montant': '25000', 'telephone': '70123456'})
        assert not appel.called and DemandePaiementMobile.objects.get().lien_paiement == ''
        html = comptable_client.get(reverse('finances:mobile_money_list')).content.decode()
        assert 'Vérifier les paiements en ligne' not in html

    def test_montant_non_multiple_de_cinq_refuse_avant_appel(self, settings, inscription, comptable):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        from finances.paiements_mobiles import creer_lien
        demande = DemandePaiementMobile.objects.create(inscription=inscription, montant=Decimal('1002'), telephone='70123456')
        with patch('finances.paiements_mobiles._appeler') as appel, pytest.raises(ErreurPasserelle, match='multiple de 5'):
            creer_lien(demande)
        assert not appel.called


@pytest.mark.django_db
class TestVerification:
    def test_paiement_accepte_confirme_la_demande_avec_recu_et_sms(self, settings, demande_avec_lien, comptable):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        with patch('finances.paiements_mobiles._appeler', return_value=_acceptee()) as appel, \
                patch('core.sms.envoyer_sms', return_value=(True, '')) as sms:
            etat, message = verifier_paiement(demande_avec_lien, comptable)
        assert etat == 'CONFIRME' and 'reçu REC-' in message
        assert appel.call_args.args == ('/payment/check', {'transaction_id': demande_avec_lien.reference})
        demande_avec_lien.refresh_from_db()
        paiement = demande_avec_lien.paiement
        assert (demande_avec_lien.statut, demande_avec_lien.confirme_par, demande_avec_lien.verifie_le is not None) == ('CONFIRME', comptable, True)
        assert (paiement.montant, paiement.mode_paiement, paiement.reference, paiement.encaisse_par) == (
            Decimal('25000'), 'MOBILE_MONEY', 'OM260503.1234.A1', comptable)
        assert 'Paiement accepté (OMBF' in demande_avec_lien.message_passerelle
        assert 'Recu ' + paiement.numero_recu in sms.call_args.args[1]

        # Le relevé marchand importé ensuite retrouve ce paiement par son n° d'opérateur.
        releve = importer_releve(demande_avec_lien.inscription.classe.etablissement, 'ORANGE', SimpleUploadedFile(
            'releve.csv', 'Date;Transaction;Montant\n21/10/2026 10:00;OM260503.1234.A1;25 000\n'.encode()), comptable)
        ligne = releve.lignes.get()
        assert (ligne.statut, ligne.methode, ligne.paiement) == ('RAPPROCHE', 'TRANSACTION', paiement)

    def test_montant_different_non_confirme(self, settings, demande_avec_lien, comptable):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        with patch('finances.paiements_mobiles._appeler', return_value=_acceptee(montant='20000')):
            etat, message = verifier_paiement(demande_avec_lien, comptable)
        demande_avec_lien.refresh_from_db()
        assert etat == 'ERREUR' and 'différent' in message
        assert demande_avec_lien.statut == 'EN_ATTENTE' and not Paiement.objects.exists()

    @pytest.mark.parametrize('reponse, etat, statut', [
        ({'code': '600', 'message': 'PAYMENT_FAILED', 'data': {'status': 'REFUSED'}}, 'REFUSE', 'ANNULE'),
        ({'code': '627', 'message': 'TRANSACTION_CANCEL', 'data': {}}, 'REFUSE', 'ANNULE'),
        ({'code': '662', 'message': 'WAITING_CUSTOMER_PAYMENT', 'data': {'status': 'PENDING'}}, 'EN_ATTENTE', 'EN_ATTENTE'),
    ])
    def test_refus_et_attente(self, settings, demande_avec_lien, comptable, reponse, etat, statut):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        with patch('finances.paiements_mobiles._appeler', return_value=reponse):
            assert verifier_paiement(demande_avec_lien, comptable)[0] == etat
        demande_avec_lien.refresh_from_db()
        assert demande_avec_lien.statut == statut and demande_avec_lien.verifie_le is not None
        assert reponse['message'] in demande_avec_lien.message_passerelle
        if statut == 'ANNULE':
            assert 'refusé ou annulé' in demande_avec_lien.observations
        assert not Paiement.objects.exists()

    def test_passerelle_injoignable_ne_change_rien(self, settings, demande_avec_lien, comptable):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        with patch('finances.paiements_mobiles._appeler', side_effect=ErreurPasserelle('passerelle injoignable (timeout)')):
            etat, message = verifier_paiement(demande_avec_lien, comptable)
        demande_avec_lien.refresh_from_db()
        assert (etat, demande_avec_lien.statut, demande_avec_lien.verifie_le) == ('ERREUR', 'EN_ATTENTE', None)
        assert 'injoignable' in message

    def test_commande_verifie_les_demandes_en_attente_avec_lien(self, settings, demande_avec_lien, inscription):
        DemandePaiementMobile.objects.create(inscription=inscription, montant=Decimal('5000'), telephone='70000000')  # sans lien
        sortie = StringIO()
        call_command('verifier_paiements_mobiles', stdout=sortie)
        assert 'non configuré' in sortie.getvalue()

        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        sortie = StringIO()
        with patch('finances.paiements_mobiles._appeler', return_value=_acceptee()) as appel, \
                patch('core.sms.envoyer_sms', return_value=(False, '')):
            call_command('verifier_paiements_mobiles', stdout=sortie)
        assert appel.call_count == 1 and '1 confirmé(s)' in sortie.getvalue()
        demande_avec_lien.refresh_from_db()
        assert demande_avec_lien.statut == 'CONFIRME' and demande_avec_lien.paiement.encaisse_par is None


@pytest.mark.django_db
class TestVueVerifier:
    def test_boutons_et_verification_par_la_vue(self, settings, comptable_client, demande_avec_lien):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        html = comptable_client.get(reverse('finances:mobile_money_list')).content.decode()
        assert 'Vérifier les paiements en ligne (1)' in html and 'Lien en ligne' in html

        with patch('finances.paiements_mobiles._appeler', return_value={'code': '662', 'message': 'WAITING_CUSTOMER_PAYMENT'}):
            reponse = comptable_client.post(reverse('finances:mobile_money_verifier', args=[demande_avec_lien.pk]), follow=True)
        assert 'toujours en attente' in reponse.content.decode()

        with patch('finances.paiements_mobiles._appeler', return_value=_acceptee()), \
                patch('core.sms.envoyer_sms', return_value=(False, '')):
            reponse = comptable_client.post(reverse('finances:mobile_money_verifier'), follow=True)
        assert '1 confirmé(s)' in reponse.content.decode()
        demande_avec_lien.refresh_from_db()
        assert demande_avec_lien.statut == 'CONFIRME'

    def test_page_parent_affiche_le_lien(self, client, demande_avec_lien):
        html = client.get(reverse('finances:mobile_money_confirmation_parent', args=[demande_avec_lien.token])).content.decode()
        assert LIEN in html and 'Payer 25' in html and 'FCFA maintenant' in html

    def test_droits_et_isolation(self, settings, client, etab, demande_avec_lien):
        for cle, valeur in CONFIG.items():
            setattr(settings, cle, valeur)
        url = reverse('finances:mobile_money_verifier', args=[demande_avec_lien.pk])
        client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, must_change_password=False))
        with patch('finances.paiements_mobiles._appeler') as appel:
            assert client.post(url).status_code in (302, 403)
            client.force_login(baker.make('accounts.User', role='COMPTABLE', must_change_password=False,
                                          etablissement=baker.make('etablissements.Etablissement')))
            assert client.post(url).status_code == 403
        assert not appel.called

    def test_non_configure(self, comptable_client, demande_avec_lien):
        reponse = comptable_client.post(reverse('finances:mobile_money_verifier', args=[demande_avec_lien.pk]), follow=True)
        assert 'non configuré' in reponse.content.decode()
