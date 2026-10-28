"""Tests du module d'envoi SMS (core/sms.py) : normalisation, dispatch, passerelle HTTP et modem série simulés."""
import json
import urllib.error
from io import BytesIO

import pytest
from django.core.cache import cache

from core import sms

pytestmark = pytest.mark.django_db


class FauxModem:
    """Port série simulé : une réponse scriptée par écriture, dans l'ordre."""

    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.ecrit = []
        self.ferme = False
        self._tampon = b''

    @property
    def in_waiting(self):
        return len(self._tampon)

    def write(self, data):
        self.ecrit.append(data.decode('utf-8'))
        self._tampon = (self.reponses.pop(0) if self.reponses else '').encode('utf-8')

    def read(self, n):
        tampon, self._tampon = self._tampon, b''
        return tampon

    def close(self):
        self.ferme = True


class FausseReponseHttp:
    def __init__(self, status, body=b''):
        self.status, self._body = status, body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture(autouse=True)
def sms_http_actif(settings):
    cache.delete(sms.SMS_CACHE_KEY)
    settings.SMS_ENABLED = True
    settings.SMS_BACKEND = 'http'
    settings.SMS_HTTP_URL = 'http://192.168.1.45:8080/message'
    settings.SMS_HTTP_USER = 'admin'
    settings.SMS_HTTP_PASSWORD = 'secret'
    settings.SMS_HTTP_TIMEOUT = 3
    yield
    cache.delete(sms.SMS_CACHE_KEY)


@pytest.fixture
def modem(mocker):
    def _brancher(reponses):
        faux = FauxModem(reponses)
        mocker.patch('core.sms._get_serial', return_value=faux)
        mocker.patch('core.sms.time.sleep')
        return faux
    return _brancher


# ── Configuration ─────────────────────────────────────────────────────────────

def test_config_runtime_prime_sur_les_settings(settings):
    assert sms.get_sms_config()['SMS_HTTP_USER'] == 'admin'
    sms.set_sms_config_runtime(SMS_HTTP_USER='gateway', SMS_BACKEND='serial')
    config = sms.get_sms_config()
    assert config['SMS_HTTP_USER'] == 'gateway' and config['SMS_BACKEND'] == 'serial'
    assert config['SMS_HTTP_URL'] == settings.SMS_HTTP_URL
    assert sms.get_sms_val('SMS_MODEM_PORT') == sms.SMS_DEFAULTS['SMS_MODEM_PORT']


@pytest.mark.parametrize('valeur, attendu', [
    (True, True), ('True', True), (' on ', True), ('1', True),
    (False, False), ('False', False), ('', False), (None, False), ('non', False),
])
def test_sms_actifs_interprete_les_chaines_du_env(settings, valeur, attendu):
    settings.SMS_ENABLED = valeur
    assert sms.sms_actifs() is attendu


# ── Numéros ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('numero, attendu', [
    ('70 12 34 56', '+22670123456'),
    ('0022670123456', '+22670123456'),
    ('+226-70-12-34-56', '+22670123456'),
    ('+33612345678', '+33612345678'),
])
def test_normaliser_numero(numero, attendu):
    assert sms._normaliser_numero(numero) == attendu


@pytest.mark.parametrize('numero, valide', [
    ('70123456', True), ('+226 70 12 34 56', True), ('00226-70.12.34.56', True),
    ('7012345', False), ('701234567', False), ('abcdefgh', False), ('', False), (None, False),
])
def test_numero_valide(numero, valide):
    assert sms._numero_valide(numero) is valide


# ── Point d'entrée ────────────────────────────────────────────────────────────

def test_envoyer_sms_refuse_si_desactive(settings, mocker):
    settings.SMS_ENABLED = 'False'
    http = mocker.patch('core.sms._envoyer_http')
    ok, motif = sms.envoyer_sms('70123456', 'Bonjour')
    assert ok is False and 'SMS_ENABLED' in motif
    http.assert_not_called()


def test_envoyer_sms_refuse_un_numero_invalide(mocker):
    http = mocker.patch('core.sms._envoyer_http')
    ok, motif = sms.envoyer_sms('12345', 'Bonjour')
    assert ok is False and 'Numéro invalide' in motif
    http.assert_not_called()


def test_envoyer_sms_normalise_tronque_et_delegue(mocker):
    http = mocker.patch('core.sms._envoyer_http', return_value=(True, ''))
    assert sms.envoyer_sms('70 12 34 56', 'Message beaucoup trop long', limite=12) == (True, '')
    http.assert_called_once_with('+22670123456', 'Message b...')


def test_envoyer_sms_dispatch_serial_et_backend_inconnu(mocker):
    serie = mocker.patch('core.sms._envoyer_serial', return_value=(True, ''))
    sms.set_sms_config_runtime(SMS_BACKEND='Serial')
    assert sms.envoyer_sms('70123456', 'Test') == (True, '')
    serie.assert_called_once_with('+22670123456', 'Test')
    sms.set_sms_config_runtime(SMS_BACKEND='pigeon')
    ok, motif = sms.envoyer_sms('70123456', 'Test')
    assert ok is False and "SMS_BACKEND inconnu : 'pigeon'" in motif


# ── Passerelle HTTP ───────────────────────────────────────────────────────────

def test_http_envoi_reussi_avec_authentification_basic(mocker):
    urlopen = mocker.patch('urllib.request.urlopen', return_value=FausseReponseHttp(202))
    assert sms._envoyer_http('+22670123456', 'Bonjour') == (True, '')
    requete = urlopen.call_args.args[0]
    assert requete.full_url == 'http://192.168.1.45:8080/message' and requete.get_method() == 'POST'
    assert json.loads(requete.data) == {'message': 'Bonjour', 'phoneNumbers': ['+22670123456']}
    assert requete.get_header('Authorization') == 'Basic YWRtaW46c2VjcmV0'
    assert urlopen.call_args.kwargs['timeout'] == 3


def test_http_statut_inattendu(mocker):
    mocker.patch('urllib.request.urlopen', return_value=FausseReponseHttp(204, b'vide'))
    ok, motif = sms._envoyer_http('+22670123456', 'Bonjour')
    assert ok is False and motif == 'HTTP 204 : vide'


def test_http_erreur_authentification(mocker):
    erreur = urllib.error.HTTPError('http://x', 401, 'Unauthorized', {}, BytesIO(b'{"message":"bad credentials"}'))
    mocker.patch('urllib.request.urlopen', side_effect=erreur)
    ok, motif = sms._envoyer_http('+22670123456', 'Bonjour')
    assert ok is False and motif.startswith('HTTP 401 : ') and 'bad credentials' in motif


def test_http_passerelle_injoignable(mocker):
    mocker.patch('urllib.request.urlopen', side_effect=urllib.error.URLError('connexion refusée'))
    ok, motif = sms._envoyer_http('+22670123456', 'Bonjour')
    assert ok is False
    assert 'Impossible de joindre la passerelle SMS (http://192.168.1.45:8080/message)' in motif
    assert 'connexion refusée' in motif


def test_http_exception_inattendue(mocker):
    mocker.patch('urllib.request.urlopen', side_effect=TimeoutError('timed out'))
    assert sms._envoyer_http('+22670123456', 'Bonjour') == (False, 'timed out')


# ── Modem série ───────────────────────────────────────────────────────────────

def test_serial_envoi_reussi(modem):
    faux = modem(['OK', 'OK', 'OK', '> ', '+CMGS: 12\r\nOK'])
    assert sms._envoyer_serial('+22670123456', 'Bonjour') == (True, '')
    assert faux.ecrit == ['AT\r', 'AT+CMGF=1\r', 'AT+CSCS="GSM"\r', 'AT+CMGS="+22670123456"\r', 'Bonjour\x1a']
    assert faux.ferme is True


def test_serial_modem_muet(modem):
    faux = modem([''])
    ok, motif = sms._envoyer_serial('+22670123456', 'Bonjour')
    assert ok is False and 'ne répond pas à la commande AT' in motif and faux.ferme is True


def test_serial_mode_texte_refuse(modem):
    modem(['OK', 'ERROR'])
    ok, motif = sms._envoyer_serial('+22670123456', 'Bonjour')
    assert ok is False and 'AT+CMGF=1' in motif


def test_serial_sans_prompt_puis_refus_reseau(modem):
    modem(['OK', 'OK', 'OK', 'ERROR'])
    ok, motif = sms._envoyer_serial('+22670123456', 'Bonjour')
    assert ok is False and "n'a pas renvoyé le prompt" in motif
    modem(['OK', 'OK', 'OK', '> ', '+CMS ERROR: 500'])
    ok, motif = sms._envoyer_serial('+22670123456', 'Bonjour')
    assert ok is False and 'Le réseau a refusé' in motif and '+CMS ERROR: 500' in motif


def test_serial_pyserial_absent_ou_port_introuvable(mocker):
    mocker.patch('core.sms._get_serial', side_effect=RuntimeError('pyserial non installé.'))
    assert sms._envoyer_serial('+22670123456', 'Bonjour') == (False, 'pyserial non installé.')
    mocker.patch('core.sms._get_serial', side_effect=OSError('could not open port COM3'))
    assert sms._envoyer_serial('+22670123456', 'Bonjour') == (False, 'could not open port COM3')


# ── Diagnostic ────────────────────────────────────────────────────────────────

def test_tester_modem_desactive(settings):
    settings.SMS_ENABLED = 'False'
    resultat = sms.tester_modem()
    assert resultat['ok'] is False and 'SMS_ENABLED=False' in resultat['message'] and resultat['backend'] == 'http'


def test_tester_modem_http(mocker):
    urlopen = mocker.patch('urllib.request.urlopen')
    assert sms.tester_modem() == {'ok': True, 'message': 'Passerelle HTTP joignable', 'operateur': None, 'backend': 'http'}
    assert urlopen.call_args.args[0].full_url == 'http://192.168.1.45:8080/health'
    urlopen.side_effect = urllib.error.URLError('hors ligne')
    resultat = sms.tester_modem()
    assert resultat['ok'] is False and 'hors ligne' in resultat['message']


def test_tester_modem_serial(modem, mocker):
    sms.set_sms_config_runtime(SMS_BACKEND='serial')
    faux = modem(['OK', '+COPS: 0,0,"Orange BF",7'])
    assert sms.tester_modem() == {'ok': True, 'message': 'Modem connecté', 'operateur': 'Orange BF', 'backend': 'serial'}
    assert faux.ferme is True
    modem(['ERROR'])
    assert sms.tester_modem()['ok'] is False
    mocker.patch('core.sms._get_serial', side_effect=RuntimeError('port COM3 introuvable'))
    assert sms.tester_modem()['message'] == 'port COM3 introuvable'


def test_tester_modem_backend_inconnu():
    sms.set_sms_config_runtime(SMS_BACKEND='pigeon')
    assert sms.tester_modem() == {'ok': False, 'message': "Backend inconnu : 'pigeon'", 'operateur': None, 'backend': 'pigeon'}
