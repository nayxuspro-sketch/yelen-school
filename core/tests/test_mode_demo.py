"""Mode démonstration (offre hébergée, chantier B8) : aucune sortie, bandeau, /health/, réinitialisation.

L'instance d'essai publique est ouverte à des inconnus : elle ne doit jamais envoyer un SMS, un e-mail, une
notification push ni créer un lien de paiement, et sa remise à zéro nocturne ne doit pas pouvoir être lancée
sur une école.
"""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.urls import reverse
from model_bakery import baker

from core import mode_demo, push
from core.notifications import creer_notification
from core.sms import envoyer_sms, sms_actifs
from finances.paiements_mobiles import cinetpay_configure

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo(settings):
    settings.DEMO_MODE = True
    return settings


# ── Le commutateur ──────────────────────────────────────────────────────────────────────────

def test_mode_demo_inactif_par_defaut(settings):
    settings.DEMO_MODE = False
    assert mode_demo.actif() is False


def test_mode_demo_actif_par_reglage(demo):
    assert mode_demo.actif() is True


# ── Sorties bloquées ────────────────────────────────────────────────────────────────────────

def test_les_sms_ne_partent_pas(demo, settings, mocker):
    settings.SMS_ENABLED = True
    passerelle = mocker.patch('core.sms._envoyer_http')
    assert sms_actifs() is False
    succes, motif = envoyer_sms('70112233', 'Message de test')
    assert succes is False and 'SMS_ENABLED' in motif
    passerelle.assert_not_called()


def test_aucun_sms_mis_en_file(demo):
    from core.models import SmsSortant
    from core.tasks import envoyer_sms_async
    assert envoyer_sms_async('70112233', 'Message de test') is None
    assert not SmsSortant.objects.exists()


def test_la_notification_est_creee_sans_email_ni_sms(demo, mocker):
    """La cloche se remplit (le visiteur voit le mécanisme), mais rien ne sort de l'instance."""
    from core.models import SmsSortant

    envoi_sms = mocker.patch('core.tasks.envoyer_sms_async')
    envoi_email = mocker.patch('core.notifications.send_mail')
    destinataire = baker.make('accounts.User', email='parent@exemple.bf', telephone='70112233')

    notification = creer_notification(destinataire, 'GENERAL', 'Test', 'Message de démonstration')

    assert notification.email_envoye is False
    envoi_email.assert_not_called()
    envoi_sms.assert_not_called()
    assert not SmsSortant.objects.exists()


def test_aucune_notification_push(demo):
    from core.models import AbonnementPush, Notification
    utilisateur = baker.make('accounts.User')
    baker.make(AbonnementPush, utilisateur=utilisateur)
    notification = baker.make(Notification, destinataire=utilisateur)
    assert push.notifier(notification) is False


def test_le_mobile_money_est_repute_non_configure(demo, settings):
    settings.CINETPAY_API_KEY = 'cle'
    settings.CINETPAY_SITE_ID = 'site'
    settings.CINETPAY_URL_PUBLIQUE = 'https://pay.exemple.bf'
    assert cinetpay_configure() is False


@override_settings(CINETPAY_API_KEY='cle', CINETPAY_SITE_ID='site',
                   CINETPAY_URL_PUBLIQUE='https://pay.exemple.bf', DEMO_MODE=False)
def test_hors_demonstration_la_passerelle_reste_configuree():
    assert cinetpay_configure() is True


# ── Bandeau et supervision ─────────────────────────────────────────────────────────────────

def test_bandeau_visible_quand_la_demonstration_est_active(client, demo):
    baker.make('accounts.User', is_superuser=True, must_change_password=False)
    reponse = client.get(reverse('accounts:login'))
    assert 'id="demo-banner"' in reponse.content.decode()
    assert 'DÉMONSTRATION' in reponse.content.decode()


def test_bandeau_absent_hors_demonstration(client, settings):
    settings.DEMO_MODE = False
    reponse = client.get(reverse('accounts:login'))
    assert 'demo-banner' not in reponse.content.decode()


def test_health_expose_l_etat_de_demonstration(client, demo):
    reponse = client.get(reverse('core:health_check'))
    assert reponse.status_code == 200 and reponse.json()['demo'] is True


def test_health_hors_demonstration(client, settings):
    settings.DEMO_MODE = False
    assert client.get(reverse('core:health_check')).json()['demo'] is False


# ── Réinitialisation ───────────────────────────────────────────────────────────────────────

def test_reinitialiser_demo_refuse_hors_demonstration(settings):
    settings.DEMO_MODE = False
    with pytest.raises(CommandError, match='DEMO_MODE'):
        call_command('reinitialiser_demo')


def test_reinitialiser_demo_vide_puis_recharge(demo):
    from etablissements.models import Etablissement
    from inscriptions.models import Eleve
    call_command('charger_demo', '--eleves', '8', verbosity=0)
    identite = Etablissement.objects.get(code='DEMO')
    baker.make('inscriptions.Eleve', nom='INTRUS')       # trace laissée par un visiteur

    call_command('reinitialiser_demo', '--eleves', '8', verbosity=0)

    assert not Eleve.objects.filter(nom='INTRUS').exists()
    assert Etablissement.objects.get(code='DEMO').pk != identite.pk
    assert Eleve.objects.count() == 8
