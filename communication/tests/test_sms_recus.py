"""Réception des SMS des parents par relève de la boîte du téléphone passerelle (communication/sms_recus.py) :
empreinte commune webhook / boîte, première relève silencieuse, traitement et réponse, dédoublonnage entre les deux
chemins, erreurs de passerelle, commande ``sms_recus`` et diagnostic de la page Configuration SMS."""
import json
import urllib.error
from io import BytesIO, StringIO

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from model_bakery import baker

from communication import sms_recus
from communication.models import IncomingSMSLog
from core import sms
from core.models import SmsSortant

pytestmark = pytest.mark.django_db

PASSERELLE = 'http://192.168.1.45:8080'


class FausseReponseHttp:
    def __init__(self, status, body=b''):
        self.status, self._body = status, body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def message_boite(hash_signe, texte, quand, expediteur='+22670112233'):
    return {'id': f'text:{hash_signe}', 'type': 'SMS', 'sender': expediteur, 'recipient': '+22600000000',
            'simNumber': 1, 'contentPreview': texte, 'createdAt': quand}


@pytest.fixture(autouse=True)
def passerelle_wifi(settings):
    cache.clear()
    settings.SMS_ENABLED = True
    settings.SMS_BACKEND = 'http'
    settings.SMS_HTTP_URL = f'{PASSERELLE}/message'
    settings.SMS_HTTP_USER = 'admin'
    settings.SMS_HTTP_PASSWORD = 'secret'
    settings.SMS_WEBHOOK_TOKEN = 'jeton-test'
    yield
    cache.clear()


@pytest.fixture
def boite(mocker):
    """Boîte de réception simulée : ``boite.messages`` est renvoyé (plus récents d'abord, comme l'app) à chaque GET /inbox."""
    class Boite:
        messages = []
        appels = []

    def urlopen(req, timeout=10):
        Boite.appels.append((req.get_method(), req.full_url, req.get_header('Authorization')))
        return FausseReponseHttp(200, json.dumps(sorted(Boite.messages, key=lambda m: m['createdAt'], reverse=True)).encode())

    mocker.patch('urllib.request.urlopen', side_effect=urlopen)
    return Boite


@pytest.mark.parametrize('brut, attendu', [
    ('text:-1215651052', 'b78aa314'),      # id de la boîte (hashCode signé) → messageId du webhook (non signé, hexa)
    ('text:123', '7b'),
    ('B78AA314', 'b78aa314'),              # messageId du webhook tel quel
    ('', ''), (None, ''),
])
def test_identifiant_message_commun_aux_deux_chemins(brut, attendu):
    assert sms_recus.identifiant_message(brut) == attendu


def test_premiere_releve_pose_le_repere_sans_repondre_aux_anciens_sms(boite):
    boite.messages = [message_boite(11, 'AIDE', '2026-10-28T10:00:00.000+00:00'),
                      message_boite(12, 'SOLDE 01-2026-9999', '2026-10-28T10:05:00.000+00:00')]

    bilan = sms_recus.relever_boite_reception()

    assert bilan['ok'] is True and (bilan['nouveaux'], bilan['ignores']) == (0, 2)
    assert IncomingSMSLog.objects.count() == 0 and SmsSortant.objects.count() == 0
    assert cache.get(sms_recus.CLE_REPERE_RELEVE) == '2026-10-28T10:05:00.000+00:00'
    methode, url, autorisation = boite.appels[0]
    assert (methode, url, autorisation) == ('GET', f'{PASSERELLE}/inbox?type=SMS&limit=30', 'Basic YWRtaW46c2VjcmV0')
    assert sms_recus.etat_releve()['ok'] is True


def test_releve_traite_les_nouveaux_sms_une_seule_fois(boite, django_capture_on_commit_callbacks, mocker):
    mocker.patch('core.tasks.threading.Thread')
    boite.messages = [message_boite(11, 'AIDE', '2026-10-28T10:00:00.000+00:00')]
    sms_recus.relever_boite_reception()                      # repère posé
    boite.messages.append(message_boite(-1215651052, 'aide', '2026-10-28T10:07:00.000+00:00'))

    with django_capture_on_commit_callbacks(execute=True):
        bilan = sms_recus.relever_boite_reception()

    assert (bilan['nouveaux'], bilan['ignores']) == (1, 0)
    journal = IncomingSMSLog.objects.get()
    assert (journal.message_id, journal.command_type, journal.sender_number) == ('b78aa314', 'HELP', '+22670112233')
    reponse = SmsSortant.objects.get()
    assert reponse.numero == '+22670112233' and reponse.message.startswith('Yelen -')

    # Relève suivante : rien de nouveau, rien de retraité.
    assert sms_recus.relever_boite_reception()['nouveaux'] == 0
    assert IncomingSMSLog.objects.count() == 1 and SmsSortant.objects.count() == 1


def test_un_sms_arrive_par_le_webhook_puis_par_la_releve_n_est_traite_qu_une_fois(boite, client, django_capture_on_commit_callbacks, mocker):
    mocker.patch('core.tasks.threading.Thread')
    sms_recus.relever_boite_reception()                      # repère posé (boîte vide)
    enveloppe = {'event': 'sms:received', 'payload': {'messageId': 'b78aa314', 'message': 'AIDE', 'sender': '+22670112233',
                                                      'receivedAt': '2026-10-28T10:07:00.000+00:00'}}
    with django_capture_on_commit_callbacks(execute=True):
        reponse = client.post(reverse('communication:webhook_incoming_sms') + '?token=jeton-test',
                              data=json.dumps(enveloppe), content_type='application/json')
    assert reponse.json()['status'] == 'success'

    boite.messages = [message_boite(-1215651052, 'AIDE', '2026-10-28T10:07:00.000+00:00')]
    bilan = sms_recus.relever_boite_reception()
    assert (bilan['nouveaux'], bilan['ignores']) == (0, 1)

    # … et réciproquement : le webhook rejoué (14 tentatives côté téléphone) ne répond pas deux fois.
    rejoue = client.post(reverse('communication:webhook_incoming_sms') + '?token=jeton-test',
                         data=json.dumps(enveloppe), content_type='application/json')
    assert rejoue.json()['status'] == 'duplicate'
    assert IncomingSMSLog.objects.count() == 1 and SmsSortant.objects.count() == 1


def test_releve_refusee_ou_impossible(mocker, settings):
    settings.SMS_ENABLED = False
    assert sms_recus.relever_boite_reception()['motif'].startswith('SMS désactivés')

    settings.SMS_ENABLED = True
    sms.set_sms_config_runtime(SMS_BACKEND='serial')
    assert 'passerelle WiFi' in sms_recus.relever_boite_reception()['motif']

    sms.set_sms_config_runtime(SMS_BACKEND='http')
    mocker.patch('urllib.request.urlopen', side_effect=urllib.error.URLError('connexion refusée'))
    bilan = sms_recus.relever_boite_reception()
    assert bilan['ok'] is False and f'Impossible de joindre la passerelle SMS ({PASSERELLE})' in bilan['motif']

    ancienne_app = urllib.error.HTTPError(f'{PASSERELLE}/inbox', 404, 'Not Found', {}, BytesIO(b''))
    mocker.patch('urllib.request.urlopen', side_effect=ancienne_app)
    assert 'version 1.59' in sms_recus.relever_boite_reception()['motif']
    assert sms_recus.etat_releve()['ok'] is False


def test_commande_sms_recus_releve_et_vide_la_file(boite, mocker):
    boite.messages = [message_boite(11, 'AIDE', '2026-10-28T10:00:00.000+00:00')]
    file_sms = mocker.patch('core.tasks.traiter_file_sms', return_value={'envoyes': 2, 'echecs': 0, 'en_attente': 1})
    sortie = StringIO()

    call_command('sms_recus', stdout=sortie)

    assert 'Relève : 0 nouveau(x) SMS, 1 ignoré(s) ; file SMS : 2 envoyé(s), 0 échec(s), 1 en attente.' in sortie.getvalue()
    file_sms.assert_called_once_with(limite=20)

    dormir = mocker.patch('communication.management.commands.sms_recus.time.sleep')
    call_command('sms_recus', '--boucle', '--intervalle', '7', '--iterations', '3', stdout=sortie)
    assert dormir.call_count == 2 and dormir.call_args.args == (7,)


def test_page_configuration_affiche_la_reception_et_releve_a_la_demande(client, mocker):
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', must_change_password=False,
                                  etablissement=baker.make('etablissements.Etablissement')))
    url = reverse('core:sms_configuration')

    page = client.get(url, secure=True).content.decode()
    assert 'jamais exécutée' in page and 'Relever maintenant' in page

    relever = mocker.patch('communication.sms_recus.relever_boite_reception',
                           return_value={'ok': True, 'motif': '', 'nouveaux': 1, 'ignores': 0})
    page = client.post(url, {'relever_maintenant': '1'}, secure=True, follow=True).content.decode()
    assert relever.called and 'Boîte de réception relevée : 1 nouveau(x) SMS traité(s)' in page

    journal = IncomingSMSLog.objects.create(sender_number='+22670112233', message_text='AIDE', command_type='HELP',
                                            response_text='Yelen - Commandes…', processed_successfully=True)
    SmsSortant.objects.create(numero='+22670112233', message='Yelen - Commandes…', statut='ECHEC',
                              derniere_erreur='Impossible de joindre la passerelle')
    cache.set(sms_recus.CLE_ETAT_RELEVE, {'ok': True, 'motif': '', 'nouveaux': 0, 'ignores': 0,
                                          'quand': '2026-10-28T10:07:00+00:00'})
    page = client.get(url, secure=True).content.decode()
    assert journal.sender_number in page and 'Impossible de joindre la passerelle' in page
    assert 'semble arrêté' in page        # relève datée de plus de 2 minutes
