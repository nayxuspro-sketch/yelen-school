"""Réception filtrée (5.52.0) : la plateforme n'accepte que les SMS venant de numéros enregistrés — familles
(père/mère, tuteur, urgence), personnel et comptes —, les autres sont journalisés sans réponse."""
from datetime import date

import pytest
from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from communication import sms_recus
from communication.models import IncomingSMSLog
from core import sms
from core.models import SmsSortant

pytestmark = pytest.mark.django_db

PARENT = '+22670112233'
INCONNU = '+22679999999'


@pytest.fixture(autouse=True)
def sms_prets(settings):
    cache.clear()
    settings.SMS_ENABLED = True
    settings.SMS_BACKEND = 'http'
    settings.SMS_HTTP_URL = 'http://192.168.1.45:8080/message'
    settings.SMS_WEBHOOK_TOKEN = 'jeton-test'
    settings.MASTER_SMS_NUMBERS = []
    yield
    cache.clear()


@pytest.fixture
def ecole():
    baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Awa', matricule='01-2026-0001',
               date_naissance=date(2013, 1, 1), telephone_parent='70 11 22 33', tuteur_telephone='',
               telephone_urgence='76543210')
    baker.make('personnel.MembrePersonnel', nom='KABORE', prenom='Salif', telephone='+226 70 55 44 33',
               is_active=True, photo='', signature='')
    baker.make('accounts.User', username='secretaire', email='s@yelen.local', telephone='70445566',
               must_change_password=False)


def _filtrer():
    sms.set_sms_config_runtime(SMS_RECEPTION_FILTREE='True')


def _accepter_tout():
    sms.set_sms_config_runtime(SMS_RECEPTION_FILTREE='False')


# ── Reconnaissance des numéros enregistrés ───────────────────────────────────

def test_un_numero_est_reconnu_quel_que_soit_son_format(ecole):
    assert sms_recus.numero_enregistre('70 11 22 33')          # parent, saisie locale
    assert sms_recus.numero_enregistre('+22670112233')         # parent, format international
    assert sms_recus.numero_enregistre('0022676543210')        # numéro d'urgence
    assert sms_recus.numero_enregistre('+22670554433')         # personnel
    assert sms_recus.numero_enregistre('70445566')             # compte de la plateforme
    assert not sms_recus.numero_enregistre(INCONNU)
    assert not sms_recus.numero_enregistre('') and not sms_recus.numero_enregistre('144')


def test_les_numeros_sont_memorises_puis_relus_apres_expiration(ecole):
    assert sms_recus.numeros_enregistres()
    assert cache.get(sms_recus.CLE_NUMEROS_ENREGISTRES) is not None
    baker.make('inscriptions.Eleve', nom='ZONGO', prenom='Paul', telephone_parent='76111111',
               date_naissance=date(2013, 1, 1))
    assert not sms_recus.numero_enregistre('76111111')          # pas encore relu : mémorisation
    cache.delete(sms_recus.CLE_NUMEROS_ENREGISTRES)
    assert sms_recus.numero_enregistre('76111111')              # relu après expiration


# ── Traitement des SMS reçus ─────────────────────────────────────────────────

def test_filtre_desactive_le_comportement_ne_change_pas(ecole):
    _accepter_tout()
    journal, _ = sms_recus.traiter_sms_recu(INCONNU, 'Bonjour, mon fils est malade')
    assert journal.command_type == IncomingSMSLog.LIBRE
    assert journal.response_text == sms_recus.ACCUSE_MESSAGE_LIBRE


def test_filtre_actif_un_numero_inconnu_est_ignore_sans_reponse(ecole):
    _filtrer()
    journal, cree = sms_recus.traiter_sms_recu(INCONNU, 'Bonjour, mon fils est malade')
    assert cree and journal.command_type == 'REFUSE'
    assert journal.response_text == '' and journal.is_authorized is False
    assert 'Numéro non enregistré' in journal.error_message
    assert not SmsSortant.objects.exists()                      # aucun SMS facturé


def test_filtre_actif_un_numero_inconnu_ne_recoit_pas_aide_non_plus(ecole):
    _filtrer()
    journal, _ = sms_recus.traiter_sms_recu(INCONNU, 'AIDE')
    assert journal.command_type == 'REFUSE' and journal.response_text == ''


def test_filtre_actif_les_numeros_enregistres_restent_traites(ecole):
    _filtrer()
    aide, _ = sms_recus.traiter_sms_recu(PARENT, 'AIDE')
    assert aide.command_type == 'HELP' and aide.response_text and aide.is_authorized
    personnel, _ = sms_recus.traiter_sms_recu('+22670554433', 'AIDE')
    assert personnel.command_type == 'HELP'
    secretariat, _ = sms_recus.traiter_sms_recu('70445566', 'AIDE')
    assert secretariat.command_type == 'HELP'


def test_le_message_refuse_reste_consulte_par_la_direction(ecole, client):
    _filtrer()
    sms_recus.traiter_sms_recu(INCONNU, 'Annonce commerciale')
    sms_recus.traiter_sms_recu(PARENT, 'Je serai absent demain')
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', must_change_password=False,
                                  etablissement=baker.make('etablissements.Etablissement')))
    url = reverse('communication:messages_recus')

    ignores = client.get(url, {'type': 'ignores'}).content.decode()
    assert INCONNU in ignores and 'Numéro non enregistré' in ignores and PARENT not in ignores

    libres = client.get(url, {'type': 'libres'}).content.decode()
    assert PARENT in libres and INCONNU not in libres

    commandes = client.get(url, {'type': 'commandes'}).content.decode()
    assert INCONNU not in commandes


def test_le_webhook_acquitte_un_message_refuse_sans_erreur(ecole, client):
    """Le téléphone passerelle rejoue jusqu'à 14 fois un webhook en erreur : un refus est un succès technique."""
    _filtrer()
    url = reverse('communication:webhook_incoming_sms') + '?token=jeton-test'
    reponse = client.post(url, {'phoneNumber': INCONNU, 'message': 'Publicité', 'messageId': 'abc123'},
                          secure=True)
    assert reponse.status_code == 200
    assert reponse.json()['status'] == 'ignored'
    assert IncomingSMSLog.objects.get(message_id='abc123').command_type == 'REFUSE'


def test_le_reglage_est_propose_dans_la_configuration_sms(ecole, client):
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', must_change_password=False,
                                  etablissement=baker.make('etablissements.Etablissement')))
    url = reverse('core:sms_configuration')
    page = client.get(url, secure=True).content.decode()
    assert 'SMS_RECEPTION_FILTREE' in page and "N'accepter que les SMS des numéros enregistrés" in page
    assert 'name="SMS_RECEPTION_FILTREE" value="True" checked' not in page   # désactivé par défaut

    client.post(url, {'sauvegarder': '1', 'SMS_ENABLED': 'True', 'SMS_BACKEND': 'http',
                      'SMS_RECEPTION_FILTREE': 'True'}, secure=True)
    assert sms.reception_filtree() is True
    assert 'name="SMS_RECEPTION_FILTREE" value="True" checked' in client.get(url, secure=True).content.decode()
