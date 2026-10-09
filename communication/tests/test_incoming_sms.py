import hashlib
import hmac
import json
import pytest
from unittest.mock import patch
from django.urls import reverse
from model_bakery import baker
from communication.models import IncomingSMSLog
from inscriptions.models import Eleve, Inscription
from pedagogie.models import MoyenneGenerale, Trimestre
from presences.models import Presence
from finances.models import FraisScolarite, Echeancier, Paiement

@pytest.mark.django_db
class TestIncomingSMSWebhook:

    @pytest.fixture(autouse=True)
    def setup_data(self, client, settings):
        # Les tests utilisent le même mécanisme d'authentification que la
        # passerelle réelle, sans laisser le webhook ouvert par défaut.
        settings.SMS_WEBHOOK_TOKEN = 'test-webhook-token'
        client.defaults['HTTP_X_SMS_TOKEN'] = 'test-webhook-token'

        # Create common setup objects
        self.etab = baker.make('etablissements.Etablissement')
        self.annee = baker.make('parametres.AnneeScolaire', etablissement=self.etab, est_courante=True)
        self.cycle = baker.make('parametres.Cycle')
        self.classe = baker.make('parametres.Classe', etablissement=self.etab, cycle=self.cycle)
        
        # Student and Inscription
        self.eleve = baker.make(
            'inscriptions.Eleve',
            matricule='01-2026-9999',
            nom='OUEDRAOGO',
            prenom='Adama',
            telephone_parent='+22670112233'
        )
        self.statut_eleve = baker.make('parametres.StatutEleve', code='INTERNE')
        self.inscription = baker.make(
            'inscriptions.Inscription',
            eleve=self.eleve,
            classe=self.classe,
            annee_scolaire=self.annee,
            statut_eleve=self.statut_eleve
        )

        # Trimester and average
        self.trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=self.annee, numero=1, nom='1er Trimestre')
        self.mg = baker.make(
            'pedagogie.MoyenneGenerale',
            inscription=self.inscription,
            trimestre=self.trimestre,
            moyenne=14.50,
            rang=3
        )

        self.url = reverse('communication:webhook_incoming_sms')

    @patch('core.tasks.envoyer_sms_async')
    def test_help_command(self, mock_envoyer, client):
        """Verifie la reponse de la commande HELP."""
        response = client.post(self.url, {
            'phoneNumber': '+22670000000',
            'message': 'HELP'
        }, secure=True)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'Yelen - Commandes:' in data['response']
        mock_envoyer.assert_called_once_with('+22670000000', data['response'])
        
        # Check audit log
        log = IncomingSMSLog.objects.first()
        assert log is not None
        assert log.command_type == 'HELP'
        assert log.processed_successfully is True

    @patch('core.tasks.envoyer_sms_async')
    def test_note_command_unauthorized(self, mock_envoyer, client):
        """Verifie le rejet d'un numero non autorise."""
        response = client.post(self.url, {
            'phoneNumber': '+22670999999',  # Pas le parent
            'message': 'NOTE 01-2026-9999 T1'
        }, secure=True)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'error'
        assert 'pas autorise' in data['response']
        
        log = IncomingSMSLog.objects.first()
        assert log.is_authorized is False
        assert log.processed_successfully is False

    @patch('core.tasks.envoyer_sms_async')
    def test_note_command_success(self, mock_envoyer, client):
        """Verifie le retour correct des notes pour un parent autorise."""
        response = client.post(self.url, {
            'phoneNumber': '+22670112233',  # Parent
            'message': 'NOTE 01-2026-9999 T1'
        }, secure=True)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'Adama OUEDRAOGO' in data['response']
        assert '14.50/20' in data['response']
        assert '3/' in data['response']
        
        log = IncomingSMSLog.objects.first()
        assert log.is_authorized is True
        assert log.processed_successfully is True
        assert log.eleve == self.eleve

    @patch('core.tasks.envoyer_sms_async')
    def test_abs_command_success(self, mock_envoyer, client):
        """Verifie le retour correct du nombre d'absences."""
        # Create some presences
        appel1 = baker.make('presences.Appel', classe=self.classe, annee_scolaire=self.annee, date='2026-06-01')
        appel2 = baker.make('presences.Appel', classe=self.classe, annee_scolaire=self.annee, date='2026-06-02')
        baker.make('presences.Presence', appel=appel1, inscription=self.inscription, statut='ABSENT')
        baker.make('presences.Presence', appel=appel2, inscription=self.inscription, statut='EXCUSE')

        response = client.post(self.url, {
            'phoneNumber': '+22670112233',  # Parent
            'message': 'ABS 01-2026-9999'
        }, secure=True)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert '1 absence(s) non justifiee(s)' in data['response']
        assert '1 excusee(s)' in data['response']

        log = IncomingSMSLog.objects.first()
        assert log.command_type == 'ABS'
        assert log.processed_successfully is True

    @patch('core.tasks.envoyer_sms_async')
    def test_solde_command_success(self, mock_envoyer, client):
        """Verifie le retour correct de la situation financiere."""
        # Pour _calcul_situation_financiere: on cree un tarif
        rubrique = baker.make('parametres.RubriquePaiement', etablissement=self.etab, code='SCOL')
        baker.make(
            'parametres.TarifScolarite',
            etablissement=self.etab,
            classe=self.classe,
            annee_scolaire=self.annee,
            statut_eleve=self.statut_eleve,
            rubrique=rubrique,
            montant=150000.00,
            actif=True
        )
        # Create a payment
        baker.make('finances.Paiement', inscription=self.inscription, rubrique=rubrique, montant=50000.00)

        response = client.post(self.url, {
            'phoneNumber': '+22670112233',  # Parent
            'message': 'SOLDE 01-2026-9999'
        }, secure=True)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert 'Du 150000' in data['response']
        assert 'Paye 50000' in data['response']
        assert 'Reste 100000' in data['response']

        log = IncomingSMSLog.objects.first()
        assert log.command_type == 'SOLDE'
        assert log.processed_successfully is True

    @patch('core.tasks.envoyer_sms_async')
    def test_json_payload_compatibility(self, mock_envoyer, client):
        """Verifie le support du format JSON."""
        payload = {
            'phoneNumber': '+22670112233',
            'message': 'HELP'
        }
        response = client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
            secure=True
        )
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'

    def test_invalid_webhook_token_is_rejected(self, client):
        response = client.post(
            self.url,
            {'phoneNumber': '+22670000000', 'message': 'HELP'},
            HTTP_X_SMS_TOKEN='wrong-token',
            secure=True,
        )
        assert response.status_code == 403

    @patch('django.core.cache.cache')
    @patch('core.tasks.envoyer_sms_async')
    def test_rate_limit_rejects_excess_requests(self, mock_envoyer, mock_cache, client, settings):
        settings.SMS_WEBHOOK_RATE_LIMIT = 1
        mock_cache.incr.side_effect = [1, 2]

        first = client.post(
            self.url,
            {'phoneNumber': '+22670000000', 'message': 'HELP'},
            secure=True,
        )
        second = client.post(
            self.url,
            {'phoneNumber': '+22670000000', 'message': 'HELP'},
            secure=True,
        )

        assert first.status_code == 200
        assert second.status_code == 429
        mock_envoyer.assert_called_once()

    @patch('core.tasks.envoyer_sms_async')
    def test_hmac_signature_is_accepted(self, mock_envoyer, client, settings):
        settings.SMS_WEBHOOK_TOKEN = ''
        settings.SMS_WEBHOOK_HMAC_SECRET = 'test-hmac-secret'
        client.defaults.pop('HTTP_X_SMS_TOKEN', None)
        body = json.dumps({
            'phoneNumber': '+22670000000',
            'message': 'HELP',
        }).encode('utf-8')
        signature = hmac.new(
            settings.SMS_WEBHOOK_HMAC_SECRET.encode('utf-8'),
            body,
            hashlib.sha256,
        ).hexdigest()

        response = client.post(
            self.url,
            body,
            content_type='application/json',
            HTTP_X_SMS_SIGNATURE=signature,
            secure=True,
        )
        assert response.status_code == 200
        mock_envoyer.assert_called_once()

    def test_missing_webhook_secret_is_rejected_outside_debug(self, client, settings):
        settings.SMS_WEBHOOK_TOKEN = ''
        settings.SMS_WEBHOOK_HMAC_SECRET = ''
        settings.DEBUG = False
        client.defaults.pop('HTTP_X_SMS_TOKEN', None)

        response = client.post(
            self.url,
            {'phoneNumber': '+22670000000', 'message': 'HELP'},
            secure=True,
        )
        assert response.status_code == 503
