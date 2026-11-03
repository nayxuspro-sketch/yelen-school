"""Notifications push (Web Push : RFC 8030 remise, RFC 8291 chiffrement, RFC 8292 VAPID).

L'utilisateur active les notifications depuis son appareil (page Notifications du portail parent ou de l'application) ;
chaque notification interne qui lui est destinée — pour un parent : absence, retard, bulletin publié, sanction, rappel
de paiement, réunion ; pour le personnel : seuil d'absences, alerte du serveur, rappel de licence — lui est alors
poussée sur l'appareil, application fermée comprise. Les clés VAPID de l'installation sont générées à la première
utilisation et conservées en base ; la remise passe par le service de notifications du navigateur (Google, Mozilla,
Apple), le serveur doit donc accéder à Internet. Rien ne part pour un utilisateur sans appareil abonné.
"""
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from django.conf import settings
from django.db import connection, transaction
from django.db.models import F
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

TTL = 3 * 24 * 3600         # le service garde la notification trois jours si le téléphone est éteint
DELAI = 10                  # secondes accordées au service de notifications
PREFIXE_PORTAIL = '/portail/parent/'
PREFIXE_PORTAIL_ELEVE = '/portail/eleve/'
OK, EXPIRE, INJOIGNABLE, REFUSE = 'ok', 'expire', 'injoignable', 'refuse'


# ── Clés de l'installation ────────────────────────────────────────────────────────────────────────

def cles():
    """Clés VAPID de l'installation ; générées une fois (ligne unique pk=1)."""
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid, b64urlencode

    from core.models import ClesWebPush

    ligne = ClesWebPush.objects.filter(pk=1).first()
    if ligne is None:
        vapid = Vapid()
        vapid.generate_keys()
        privee = b64urlencode(vapid.private_key.private_numbers().private_value.to_bytes(32, 'big'))
        publique = b64urlencode(vapid.public_key.public_bytes(serialization.Encoding.X962,
                                                                serialization.PublicFormat.UncompressedPoint))
        ligne, _ = ClesWebPush.objects.get_or_create(pk=1, defaults={'cle_privee': privee, 'cle_publique': publique})
    return ligne


def cle_publique():
    """Clé publique remise au navigateur (``applicationServerKey``)."""
    return cles().cle_publique


# ── Abonnements ───────────────────────────────────────────────────────────────────────────────────

def enregistrer_abonnement(utilisateur, donnees, navigateur=''):
    """Crée ou met à jour l'abonnement d'un navigateur (``{endpoint, keys: {p256dh, auth}}`` tel que le fournit
    ``PushSubscription.toJSON()``) ; un endpoint déjà connu est rattaché à ``utilisateur``. ValueError si invalide."""
    from core.models import AbonnementPush

    endpoint = donnees.get('endpoint') if isinstance(donnees, dict) else None
    keys = donnees.get('keys') if isinstance(donnees, dict) else None
    if (not isinstance(endpoint, str) or not endpoint.startswith('https://') or len(endpoint) > 1000
            or not isinstance(keys, dict) or not keys.get('p256dh') or not keys.get('auth')):
        raise ValueError("Abonnement invalide.")
    abonnement, _ = AbonnementPush.objects.update_or_create(endpoint=endpoint, defaults={
        'utilisateur': utilisateur, 'p256dh': str(keys['p256dh'])[:200], 'auth': str(keys['auth'])[:100],
        'navigateur': (navigateur or '')[:200], 'echecs': 0,
    })
    return abonnement


def supprimer_abonnement(utilisateur, endpoint):
    """Retire l'abonnement ``endpoint`` de ``utilisateur`` ; retourne le nombre de lignes supprimées."""
    from core.models import AbonnementPush
    return AbonnementPush.objects.filter(utilisateur=utilisateur, endpoint=endpoint or '').delete()[0]


# ── Envoi ─────────────────────────────────────────────────────────────────────────────────────────

def page_notifications(utilisateur):
    """Liste des notifications de ``utilisateur`` : portail parent, portail élève, ou application."""
    if utilisateur.role == 'PARENT':
        return reverse('core:portail_parent_notifications')
    if utilisateur.role == 'ELEVE':
        return reverse('core:portail_eleve_notifications')
    return reverse('core:notifications_list')


def charge_utile(notification):
    """Contenu poussé : titre, message et page à ouvrir — le lien de la notification s'il est consultable par son
    destinataire (portail parent, portail élève ou application), sinon sa page de notifications."""
    lien, destinataire = notification.lien or '', notification.destinataire
    if destinataire.role == 'PARENT':
        prefixe = PREFIXE_PORTAIL
    elif destinataire.role == 'ELEVE':
        prefixe = PREFIXE_PORTAIL_ELEVE
    else:
        prefixe = '/'
    if not lien.startswith(prefixe):
        lien = page_notifications(destinataire)
    return {'titre': notification.titre, 'message': notification.message[:300], 'url': lien,
            'tag': f'notification-{notification.pk}'}


def notifier(notification):
    """Pousse ``notification`` sur les appareils abonnés de son destinataire, en arrière-plan une fois la transaction
    validée. Retourne False (et ne fait rien) si le destinataire n'a aucun appareil abonné."""
    from core import mode_demo
    from core.models import AbonnementPush

    if mode_demo.actif():
        return False
    if not AbonnementPush.objects.filter(utilisateur_id=notification.destinataire_id).exists():
        return False
    transaction.on_commit(lambda: _en_arriere_plan(envoyer_notification, notification.pk))
    return True


def _en_arriere_plan(fonction, *args):
    threading.Thread(target=_executer, args=(fonction, *args), daemon=True).start()


def _executer(fonction, *args):
    try:
        fonction(*args)
    except Exception:
        logger.exception("Envoi push en arrière-plan interrompu")
    finally:
        connection.close()


def envoyer_notification(notification_id):
    """Envoie la notification à chaque appareil de son destinataire ; retourne le nombre de remises acceptées."""
    from core.models import AbonnementPush, Notification

    notification = Notification.objects.select_related('destinataire').filter(pk=notification_id).first()
    if notification is None:
        return 0
    contenu = charge_utile(notification)
    abonnements = list(AbonnementPush.objects.filter(utilisateur_id=notification.destinataire_id))
    return sum(envoyer(abonnement, contenu) == OK for abonnement in abonnements)


def envoyer(abonnement, contenu):
    """Chiffre ``contenu`` pour l'appareil (aes128gcm) et le remet, signé VAPID, au service de notifications.
    Retourne OK, EXPIRE (abonnement supprimé : le navigateur l'a révoqué), INJOIGNABLE (pas d'Internet, délai) ou
    REFUSE (réponse 4xx/5xx) ; les deux derniers incrémentent le compteur d'échecs de l'abonnement."""
    import http_ece
    from cryptography.hazmat.primitives.asymmetric import ec
    from py_vapid import Vapid, b64urldecode

    corps = http_ece.encrypt(
        json.dumps(contenu, ensure_ascii=False).encode('utf-8'),
        private_key=ec.generate_private_key(ec.SECP256R1()),        # clé éphémère du serveur pour cet envoi
        dh=b64urldecode(abonnement.p256dh.encode()), auth_secret=b64urldecode(abonnement.auth.encode()),
        version='aes128gcm',
    )
    origine = urlparse(abonnement.endpoint)
    en_tetes = Vapid.from_raw(cles().cle_privee.encode()).sign({
        'aud': f'{origine.scheme}://{origine.netloc}', 'exp': int(time.time()) + 12 * 3600,
        'sub': settings.WEBPUSH_CONTACT,
    })
    en_tetes.update({'Content-Encoding': 'aes128gcm', 'Content-Type': 'application/octet-stream',
                     'TTL': str(TTL), 'Urgency': 'normal'})
    try:
        statut = _poster(abonnement.endpoint, corps, en_tetes)
    except urllib.error.HTTPError as erreur:
        statut = erreur.code
    except (urllib.error.URLError, OSError) as erreur:
        logger.warning("Service de notifications %s injoignable : %s", origine.netloc, erreur)
        return _echec(abonnement, INJOIGNABLE)

    if statut in (404, 410):
        logger.info("Abonnement push %s expiré : supprimé.", abonnement.pk)
        abonnement.delete()
        return EXPIRE
    if statut >= 400:
        logger.warning("Push refusé (%s) pour l'abonnement %s", statut, abonnement.pk)
        return _echec(abonnement, REFUSE)
    type(abonnement).objects.filter(pk=abonnement.pk).update(dernier_envoi=timezone.now(), echecs=0)
    return OK


def _echec(abonnement, resultat):
    type(abonnement).objects.filter(pk=abonnement.pk).update(echecs=F('echecs') + 1)
    return resultat


def _poster(endpoint, corps, en_tetes):
    """POST du message chiffré au service de notifications ; retourne le code HTTP (201 = accepté)."""
    requete = urllib.request.Request(endpoint, data=corps, headers=en_tetes, method='POST')
    with urllib.request.urlopen(requete, timeout=DELAI) as reponse:
        return reponse.status
