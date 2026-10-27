"""File persistante des SMS : mise en file, envoi immédiat, nouvelles tentatives, abandons, commande."""
from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock

import pytest
from django.core.management import call_command
from django.utils import timezone
from model_bakery import baker

from core import tasks
from core.models import SmsSortant

pytestmark = pytest.mark.django_db


@pytest.fixture
def sms_actifs(settings):
    settings.SMS_ENABLED = True


@pytest.fixture
def passerelle(mocker):
    """Remplace l'envoi réel ; ``passerelle.return_value`` pilote le résultat."""
    return mocker.patch('core.sms.envoyer_sms', return_value=(True, ''))


def test_desactive_rien_en_file(settings, passerelle):
    settings.SMS_ENABLED = False
    assert tasks.envoyer_sms_async('70000000', 'Bonjour') is None
    assert SmsSortant.objects.count() == 0 and not passerelle.called


def test_envoi_immediat_marque_la_notification(sms_actifs, passerelle, mocker, django_capture_on_commit_callbacks):
    notification = baker.make('core.Notification', destinataire=baker.make('accounts.User', must_change_password=False))
    thread = mocker.patch('core.tasks.threading.Thread')
    mocker.patch('core.tasks.connection', MagicMock())
    with django_capture_on_commit_callbacks(execute=True):
        sms = tasks.envoyer_sms_async(' 70000000 ', 'Bonjour', notification_id=notification.pk)
    assert sms.numero == '70000000' and sms.statut == 'EN_ATTENTE'
    thread.assert_called_once()
    tasks._envoyer_puis_rattraper(sms.pk)                       # corps du thread
    sms.refresh_from_db()
    notification.refresh_from_db()
    assert (sms.statut, sms.tentatives, sms.derniere_erreur) == ('ENVOYE', 1, '') and sms.date_envoi and notification.sms_envoye
    passerelle.assert_called_once_with('70000000', 'Bonjour')


def test_echec_passager_retente_plus_tard(sms_actifs, passerelle):
    passerelle.return_value = (False, 'HTTP 503 Service Unavailable')
    sms = tasks.envoyer_sms_async('70000000', 'Bonjour')
    assert tasks.envoyer_sms_en_file(sms) is False
    sms.refresh_from_db()
    assert (sms.statut, sms.tentatives, sms.derniere_erreur) == ('EN_ATTENTE', 1, 'HTTP 503 Service Unavailable')
    assert timedelta(minutes=1, seconds=50) < sms.prochaine_tentative - timezone.now() <= timedelta(minutes=2)
    assert tasks.traiter_file_sms() == {'envoyes': 0, 'echecs': 0, 'en_attente': 1}, 'pas encore due'

    SmsSortant.objects.filter(pk=sms.pk).update(prochaine_tentative=timezone.now() - timedelta(seconds=1))
    passerelle.return_value = (True, '')
    assert tasks.traiter_file_sms() == {'envoyes': 1, 'echecs': 0, 'en_attente': 0}
    sms.refresh_from_db()
    assert sms.statut == 'ENVOYE' and sms.tentatives == 2 and passerelle.call_count == 2


def test_abandon_numero_invalide_et_apres_cinq_tentatives(sms_actifs, passerelle):
    passerelle.return_value = (False, "Numéro invalide ignoré : '12' (attendu : 8 chiffres ou +226XXXXXXXX)")
    invalide = tasks.envoyer_sms_async('12', 'Bonjour')
    tasks.envoyer_sms_en_file(invalide)
    invalide.refresh_from_db()
    assert invalide.statut == 'ECHEC' and invalide.tentatives == 1

    passerelle.return_value = (False, 'Modem occupé')
    sms = tasks.envoyer_sms_async('70000000', 'Bonjour')
    delais = []
    for _ in range(5):
        SmsSortant.objects.filter(pk=sms.pk).update(prochaine_tentative=timezone.now() - timedelta(seconds=1))
        sms.refresh_from_db()
        tasks.envoyer_sms_en_file(sms)
        sms.refresh_from_db()
        delais.append(round((sms.prochaine_tentative - timezone.now()).total_seconds() / 60))
    assert sms.statut == 'ECHEC' and sms.tentatives == 5 and delais[:4] == [2, 10, 30, 120]
    assert tasks.traiter_file_sms()['en_attente'] == 0


def test_une_ligne_reservee_n_est_pas_envoyee_deux_fois(sms_actifs, passerelle):
    sms = tasks.envoyer_sms_async('70000000', 'Bonjour')
    SmsSortant.objects.filter(pk=sms.pk).update(prochaine_tentative=timezone.now() + timedelta(minutes=5))  # prise par un autre
    assert tasks.envoyer_sms_en_file(sms) is None and not passerelle.called


def test_commande_sms_file(sms_actifs, passerelle):
    tasks.envoyer_sms_async('70000000', 'A')
    tasks.envoyer_sms_async('70000001', 'B')
    sortie = StringIO()
    call_command('sms_file', '--limite', '1', stdout=sortie)
    assert sortie.getvalue().strip() == '1 envoyé(s), 0 échec(s), 1 en attente.'
