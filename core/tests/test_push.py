"""Notifications push (core/push.py), portail parent et application du personnel : clés de l'installation, abonnement
des appareils, envoi chiffré et signé à la création d'une notification, abonnements expirés, test depuis la page,
service workers et pages."""
import json
import urllib.error
from unittest.mock import patch

import http_ece
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.urls import reverse
from model_bakery import baker
from py_vapid import Vapid, b64urldecode, b64urlencode

from core import push
from core.models import AbonnementPush, ClesWebPush, Notification
from core.notifications import creer_notification

pytestmark = pytest.mark.django_db

ENDPOINT = 'https://fcm.googleapis.com/fcm/send/abc123'


def _appareil():
    """Clés d'un navigateur abonné (comme ``PushSubscription.toJSON()``) + clé privée pour déchiffrer côté test."""
    cle = ec.generate_private_key(ec.SECP256R1())
    p256dh = b64urlencode(cle.public_key().public_bytes(serialization.Encoding.X962,
                                                       serialization.PublicFormat.UncompressedPoint))
    return cle, {'endpoint': ENDPOINT, 'keys': {'p256dh': p256dh, 'auth': b64urlencode(b'0123456789abcdef')}}


@pytest.fixture
def parent(client):
    etab = baker.make('etablissements.Etablissement')
    parent = baker.make('accounts.User', etablissement=etab, role='PARENT', must_change_password=False)
    client.force_login(parent)
    return parent


@pytest.fixture
def abonne(parent):
    cle, donnees = _appareil()
    return cle, push.enregistrer_abonnement(parent, donnees, 'Chrome Android')


def _json(client, nom, corps):
    return client.post(reverse(nom), json.dumps(corps), content_type='application/json')


# ── Clés et abonnements ────────────────────────────────────────────────────────

def test_cles_generees_une_seule_fois():
    premiere = push.cles()
    assert ClesWebPush.objects.count() == 1 and push.cles().pk == premiere.pk
    publique = b64urldecode(premiere.cle_publique.encode())
    assert len(publique) == 65 and publique[0] == 4                       # point non compressé P-256
    assert Vapid.from_raw(premiere.cle_privee.encode()).public_key.public_numbers() == \
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), publique).public_numbers()


def test_abonner_cree_puis_rattache_le_meme_appareil(client, parent):
    _, donnees = _appareil()

    reponse = _json(client, 'core:push_abonner', donnees)
    autre = baker.make('accounts.User', etablissement=parent.etablissement, role='PARENT', must_change_password=False)
    client.force_login(autre)
    _json(client, 'core:push_abonner', donnees)        # même navigateur, autre compte connecté

    assert reponse.status_code == 200 and reponse.json()['ok'] is True
    assert AbonnementPush.objects.count() == 1 and AbonnementPush.objects.get().utilisateur == autre


def test_abonnement_invalide_refuse(client, parent):
    assert _json(client, 'core:push_abonner', {'endpoint': 'http://pas-https', 'keys': {}}).status_code == 400
    assert client.post(reverse('core:push_abonner'), 'pas du json', content_type='application/json').status_code == 400
    client.logout()
    assert _json(client, 'core:push_abonner', _appareil()[1]).status_code == 302
    assert not AbonnementPush.objects.exists()


def test_personnel_abonne_son_appareil_et_recoit_ses_notifications(client, parent):
    """Le personnel (5.30.0) active les notifications depuis la page Notifications de l'application : les alertes qui
    lui sont destinées (seuil d'absences, serveur, licence) ouvrent la page de l'application concernée."""
    directeur = baker.make('accounts.User', etablissement=parent.etablissement, role='DIRECTEUR', must_change_password=False)
    client.force_login(directeur)
    assert _json(client, 'core:push_abonner', _appareil()[1]).json()['ok'] is True
    assert AbonnementPush.objects.get().utilisateur == directeur

    alerte = baker.make('core.Notification', destinataire=directeur, lien='/exploitation/', titre='Serveur : Espace disque faible')
    sans_lien = baker.make('core.Notification', destinataire=directeur, lien='', titre='Licence')
    assert push.charge_utile(alerte)['url'] == '/exploitation/'
    assert push.charge_utile(sans_lien)['url'] == reverse('core:notifications_list')
    with patch.object(push, 'envoyer', return_value=push.OK) as envoyer:
        assert _json(client, 'core:push_test', {'endpoint': ENDPOINT}).json()['ok'] is True
    assert envoyer.call_args[0][1]['url'] == reverse('core:notifications_list')


def test_desabonner_ne_retire_que_son_appareil(client, parent, abonne):
    autre = baker.make('core.AbonnementPush', endpoint='https://updates.push.services.mozilla.com/x',
                       utilisateur=baker.make('accounts.User', role='PARENT', must_change_password=False))

    assert _json(client, 'core:push_desabonner', {'endpoint': autre.endpoint}).json()['ok'] is True
    assert _json(client, 'core:push_desabonner', {'endpoint': ENDPOINT}).json()['ok'] is True

    assert list(AbonnementPush.objects.values_list('pk', flat=True)) == [autre.pk]


# ── Envoi ──────────────────────────────────────────────────────────────────────

def test_notification_poussee_chiffree_et_signee_vers_l_appareil(parent, abonne, django_capture_on_commit_callbacks):
    cle_appareil, abonnement = abonne
    envois = []

    def poster(endpoint, corps, en_tetes):
        envois.append((endpoint, corps, en_tetes))
        return 201

    with patch.object(push, '_poster', poster), patch.object(push, '_en_arriere_plan', lambda f, *a: f(*a)), \
            django_capture_on_commit_callbacks(execute=True):
        creer_notification(parent, 'ABSENCE', 'Absence signalée — 30/10/2026',
                           'OUEDRAOGO Awa a été absent(e) le 30/10/2026.', lien='/bulletins/',
                           envoyer_email=False, envoyer_sms=False)

    (endpoint, corps, en_tetes), = envois
    clair = json.loads(http_ece.decrypt(corps, private_key=cle_appareil, auth_secret=b'0123456789abcdef',
                                        version='aes128gcm'))
    notification = Notification.objects.get()
    assert endpoint == ENDPOINT
    assert clair == {'titre': 'Absence signalée — 30/10/2026', 'message': 'OUEDRAOGO Awa a été absent(e) le 30/10/2026.',
                     'url': '/portail/parent/notifications/', 'tag': f'notification-{notification.pk}'}
    assert en_tetes['Content-Encoding'] == 'aes128gcm' and en_tetes['TTL'] == str(push.TTL)
    jeton, cle_publique = en_tetes['Authorization'].removeprefix('vapid t=').split(',k=')
    assert cle_publique == push.cles().cle_publique
    assert Vapid.verify(en_tetes['Authorization']) is True            # ce que vérifie le service de notifications
    revendications = json.loads(b64urldecode(jeton.split('.')[1].encode()))
    assert revendications['aud'] == 'https://fcm.googleapis.com' and revendications['sub'] == 'mailto:noreply@yelenSchool.bf'
    abonnement.refresh_from_db()
    assert abonnement.dernier_envoi is not None and abonnement.echecs == 0


def test_lien_du_portail_conserve_dans_la_notification(parent, abonne):
    notification = baker.make('core.Notification', destinataire=parent, lien='/portail/parent/vie-scolaire/',
                              titre='Sanction', message='x' * 400)
    contenu = push.charge_utile(notification)
    assert contenu['url'] == '/portail/parent/vie-scolaire/' and len(contenu['message']) == 300


def test_sans_appareil_abonne_rien_ne_part(parent, django_capture_on_commit_callbacks):
    with patch.object(push, '_poster') as poster, django_capture_on_commit_callbacks(execute=True):
        creer_notification(parent, 'GENERAL', 'Info', 'Message', envoyer_email=False, envoyer_sms=False)
    poster.assert_not_called()


def test_abonnement_expire_supprime_et_echec_reseau_compte(parent, abonne):
    _, abonnement = abonne
    contenu = {'titre': 't', 'message': 'm', 'url': '/portail/parent/', 'tag': 'x'}

    with patch.object(push, '_poster', side_effect=urllib.error.URLError('réseau coupé')):
        assert push.envoyer(abonnement, contenu) == push.INJOIGNABLE
    abonnement.refresh_from_db()
    assert abonnement.echecs == 1

    with patch.object(push, '_poster', side_effect=urllib.error.HTTPError(ENDPOINT, 410, 'Gone', {}, None)):
        assert push.envoyer(abonnement, contenu) == push.EXPIRE
    assert not AbonnementPush.objects.exists()


def test_test_depuis_le_portail_rend_compte_du_resultat(client, parent, abonne):
    with patch.object(push, '_poster', return_value=201) as poster:
        reponse = _json(client, 'core:push_test', {'endpoint': ENDPOINT})
    assert reponse.json() == {'ok': True, 'message': "Notification de test envoyée : elle s'affiche dans quelques secondes."}
    assert poster.call_args[0][0] == ENDPOINT

    with patch.object(push, '_poster', side_effect=TimeoutError('timed out')):
        reponse = _json(client, 'core:push_test', {'endpoint': ENDPOINT})
    assert reponse.json()['ok'] is False and 'Internet' in reponse.json()['message']

    assert _json(client, 'core:push_test', {'endpoint': 'https://inconnu'}).status_code == 404


# ── Navigateur ─────────────────────────────────────────────────────────────────

def test_service_worker_du_portail_affiche_et_ouvre_les_notifications(client):
    script = client.get('/sw.js').content.decode()
    assert "addEventListener('push'" in script and 'showNotification(' in script
    assert "addEventListener('notificationclick'" in script and "'/portail/parent/'" in script


def test_ressources_pwa_accessibles_au_parent_connecte(client, parent):
    """Le middleware de rôle laissait passer les parents sur /portail/parent/ mais renvoyait le service worker et le
    manifeste vers le portail : impossible d'installer l'application ou de recevoir les notifications."""
    for url in ('/sw.js', '/manifest.json', reverse('core:pwa_icon', args=[192])):
        assert client.get(url).status_code == 200, url


def test_service_worker_de_l_application_affiche_et_ouvre_les_notifications(client):
    script = client.get('/app-sw.js').content.decode()
    assert "addEventListener('push'" in script and 'showNotification(' in script
    assert "addEventListener('notificationclick'" in script and "'/notifications/'" in script


def test_pages_du_portail_portent_le_reglage(client, parent):
    publique = push.cle_publique()
    for nom in ('core:portail_parent', 'core:portail_parent_notifications'):
        html = client.get(reverse(nom)).content.decode()
        assert f'data-push-cle="{publique}"' in html and 'js/push.' in html, nom
        assert reverse('core:push_abonner') in html and 'data-push-action="activer"' in html
        assert 'data-push-sw="/sw.js"' in html and 'data-push-scope="/portail/parent/"' in html
    assert 'data-push-mode="invitation"' in client.get(reverse('core:portail_parent')).content.decode()


def test_page_notifications_du_personnel_porte_le_reglage(client, parent):
    client.force_login(baker.make('accounts.User', etablissement=parent.etablissement, role='COMPTABLE', must_change_password=False))
    html = client.get(reverse('core:notifications_list')).content.decode()
    assert f'data-push-cle="{push.cle_publique()}"' in html and 'js/push.' in html
    assert 'data-push-sw="/app-sw.js"' in html and 'data-push-scope="/"' in html and 'data-push-action="activer"' in html
    assert 'data-push-cle' not in client.get(reverse('core:notifications_list') + '?_partial=header').content.decode()
