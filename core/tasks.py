"""
core/tasks.py — Envoi SMS YELEN SCHOOL (sans Celery).

Chaque SMS est d'abord écrit dans la file persistante ``SmsSortant`` puis envoyé immédiatement en arrière-plan ;
un échec passager est retenté plus tard (thread d'un envoi suivant, commande ``sms_file``, bouton de la page
Exploitation, fin de ``sms_auto``). Un redémarrage ne perd donc aucun message.
"""
import logging
import threading
from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_TENTATIVES = 5
DELAIS_MINUTES = (2, 10, 30, 120)          # attente avant la 2e, 3e, 4e, 5e tentative
DUREE_RESERVATION = timedelta(minutes=5)   # une ligne en cours d'envoi n'est pas reprise par un autre travailleur
MOTIFS_DEFINITIFS = ('Numéro invalide', 'SMS_ENABLED', 'SMS_BACKEND inconnu')


def envoyer_sms_async(numero, message, notification_id=None):
    """Met le SMS en file puis tente l'envoi en arrière-plan dès que la transaction courante est validée.

    Retourne la ligne ``SmsSortant`` créée, ou None si les SMS sont désactivés (rien n'est mis en file).
    """
    from core.models import SmsSortant
    from core.sms import sms_actifs

    if not sms_actifs():
        logger.info("SMS désactivés : message pour %s non mis en file.", numero)
        return None
    sms = SmsSortant.objects.create(numero=str(numero).strip(), message=message, notification_id=notification_id)
    transaction.on_commit(lambda: threading.Thread(target=_envoyer_puis_rattraper, args=(sms.pk,), daemon=True).start())
    return sms


def _envoyer_puis_rattraper(pk):
    from core.models import SmsSortant
    try:
        sms = SmsSortant.objects.filter(pk=pk).first()
        if sms is not None:
            envoyer_sms_en_file(sms)
        traiter_file_sms(limite=10)   # rattrape au passage les SMS dont la nouvelle tentative est due
    except Exception:
        logger.exception("Envoi SMS en arrière-plan interrompu (%s)", pk)
    finally:
        connection.close()


def _reserver(sms):
    """Verrou optimiste : un seul travailleur prend la ligne (son heure de reprise est repoussée le temps de l'envoi)."""
    from core.models import SmsSortant
    return SmsSortant.objects.filter(
        pk=sms.pk, statut=SmsSortant.Statut.EN_ATTENTE, prochaine_tentative=sms.prochaine_tentative,
    ).update(prochaine_tentative=timezone.now() + DUREE_RESERVATION) == 1


def envoyer_sms_en_file(sms):
    """Tente l'envoi d'une ligne de la file et enregistre le résultat. Retourne True si le SMS est parti,
    False en cas d'échec (retenté plus tard ou définitif), None si un autre travailleur s'en charge déjà."""
    from core.models import Notification, SmsSortant
    from core.sms import envoyer_sms

    if not _reserver(sms):
        return None
    succes, motif = envoyer_sms(sms.numero, sms.message)
    maintenant = timezone.now()
    sms.tentatives += 1
    if succes:
        sms.statut, sms.date_envoi, sms.derniere_erreur = SmsSortant.Statut.ENVOYE, maintenant, ''
        if sms.notification_id:
            Notification.objects.filter(pk=sms.notification_id).update(sms_envoye=True)
    else:
        sms.derniere_erreur = (motif or 'Échec inconnu')[:255]
        definitif = sms.derniere_erreur.startswith(MOTIFS_DEFINITIFS) or sms.tentatives >= MAX_TENTATIVES
        if definitif:
            sms.statut = SmsSortant.Statut.ECHEC
            logger.warning("SMS abandonné → %s après %s tentative(s) : %s", sms.numero, sms.tentatives, motif)
        else:
            delai = DELAIS_MINUTES[min(sms.tentatives, len(DELAIS_MINUTES)) - 1]
            sms.prochaine_tentative = maintenant + timedelta(minutes=delai)
            logger.warning("SMS échoué → %s (tentative %s, reprise dans %s min) : %s", sms.numero, sms.tentatives, delai, motif)
    sms.save(update_fields=['statut', 'tentatives', 'prochaine_tentative', 'derniere_erreur', 'date_envoi'])
    return succes


def traiter_file_sms(limite=50):
    """Envoie les SMS en attente dont l'heure de reprise est passée (les plus anciens d'abord)."""
    from core.models import SmsSortant

    envoyes = echecs = 0
    dus = (SmsSortant.objects.filter(statut=SmsSortant.Statut.EN_ATTENTE, prochaine_tentative__lte=timezone.now())
           .order_by('created_at')[:limite])
    for sms in list(dus):
        resultat = envoyer_sms_en_file(sms)
        if resultat is True:
            envoyes += 1
        elif resultat is False:
            echecs += 1
    en_attente = SmsSortant.objects.filter(statut=SmsSortant.Statut.EN_ATTENTE).count()
    return {'envoyes': envoyes, 'echecs': echecs, 'en_attente': en_attente}
