"""Veille d'exploitation : les alertes de la page Exploitation (aucune sauvegarde ou sauvegarde trop ancienne, disque
faible, erreurs applicatives répétées, SMS en échec) sont relayées à la direction — Directeurs et Super Admin —
par notification interne (+ e-mail si configuré), et par SMS pour les alertes de niveau « danger ». Une alerte est
relayée une fois par jour tant qu'elle dure ; le registre est la table des notifications (titre identique le même
jour), ce qui vaut pour tous les processus et survit aux redémarrages.

Déclenchement : la première requête du jour reçue par chaque processus (``VeilleMiddleware``), en arrière-plan, sans
planificateur ni configuration. La surveillance Windows (installer/surveiller-yelen.ps1) reste utile pour le seul cas
que l'application ne peut pas constater elle-même : le serveur arrêté.
"""
import logging
import threading
from datetime import date

from django.db import connection
from django.db.models import Q
from django.urls import reverse

logger = logging.getLogger(__name__)

PREFIXE_TITRE = 'Serveur : '
_verrou = threading.Lock()
_verifie_le = None          # date de la dernière vérification lancée par ce processus


class VeilleMiddleware:
    """Lance la vérification quotidienne à la première requête du jour, puis laisse passer la requête."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        declencher()
        return self.get_response(request)


def declencher(aujourd_hui=None):
    """Lance la vérification en arrière-plan si elle n'a pas encore eu lieu aujourd'hui ; retourne True si lancée."""
    global _verifie_le
    aujourd_hui = aujourd_hui or date.today()
    with _verrou:
        if _verifie_le == aujourd_hui:
            return False
        _verifie_le = aujourd_hui
    _en_arriere_plan(relayer_alertes)
    return True


def _en_arriere_plan(fonction):
    threading.Thread(target=_executer, args=(fonction,), daemon=True).start()


def _executer(fonction):
    try:
        fonction()
    except Exception:
        logger.exception("Veille d'exploitation interrompue")
    finally:
        connection.close()


def destinataires():
    """Comptes actifs Directeur / Proviseur et Super Admin (rôle ou superuser), tous établissements confondus."""
    from accounts.models import User
    from core.models import RoleChoices
    return list(User.objects.filter(is_active=True).filter(
        Q(role__in=(RoleChoices.DIRECTEUR, RoleChoices.SUPER_ADMIN)) | Q(is_superuser=True)))


def relayer_alertes(aujourd_hui=None):
    """Relaye chaque alerte d'exploitation en cours aux destinataires qui ne l'ont pas encore reçue aujourd'hui.
    Retourne le nombre de notifications créées."""
    from core.exploitation import etat_exploitation
    from core.models import Notification
    from core.notifications import creer_notification

    alertes = etat_exploitation()['alertes']
    if not alertes:
        return 0
    aujourd_hui = aujourd_hui or date.today()
    comptes = destinataires()
    lien = reverse('core:exploitation')
    creees = 0
    for alerte in alertes:
        titre = PREFIXE_TITRE + alerte['titre']
        deja = set(Notification.objects.filter(titre=titre, created_at__date=aujourd_hui, destinataire__in=comptes)
                   .values_list('destinataire_id', flat=True))
        for compte in comptes:
            if compte.pk in deja:
                continue
            creer_notification(compte, Notification.TypeChoices.GENERAL, titre, alerte['detail'], lien=lien,
                               envoyer_sms=alerte['niveau'] == 'danger')
            creees += 1
    if creees:
        logger.info("Veille d'exploitation : %d alerte(s) relayée(s) à la direction (%d notification(s))",
                    len(alertes), creees)
    return creees
