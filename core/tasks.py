"""
core/tasks.py — Envoi SMS YELEN SCHOOL

Exécution synchrone (thread Django) — pas de Celery requis.
L'envoi est fait dans un thread séparé pour ne pas bloquer la réponse HTTP.
"""

import logging
import threading

logger = logging.getLogger(__name__)


def envoyer_sms_async(numero, message, notification_id=None):
    """
    Envoie un SMS dans un thread séparé (non bloquant).

    Args:
        numero          : str — numéro destinataire
        message         : str — contenu du SMS
        notification_id : int|None — pk de la Notification à marquer sms_envoye=True
    """
    def _run():
        from core.sms import envoyer_sms
        succes, motif = envoyer_sms(numero, message)
        if succes and notification_id is not None:
            from core.models import Notification
            Notification.objects.filter(pk=notification_id).update(sms_envoye=True)
        if not succes:
            logger.warning(f"SMS échoué → {numero} : {motif}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
