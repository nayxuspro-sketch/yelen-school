"""Rappels d'expiration de la licence.

- Bandeau discret en tête de chaque page pour les administrateurs (Super Admin, Directeur / Proviseur, Directeur
  Réseau) dès J-30, puis « Licence expirée » tant qu'elle n'est pas renouvelée ;
- Notification interne + SMS (+ e-mail si configuré) au Directeur / Proviseur à J-15 et à J-7 — à défaut de compte
  Directeur, aux Super Admin de l'établissement.

Aucun planificateur n'est nécessaire : la vérification part de la première page affichée chaque jour par le
processus web (``contexte``), ainsi que du contrôle des licences lorsqu'il est actif (``LicenceCheckMiddleware``).
Les alertes ``LicenceAlert`` garantissent un seul envoi par palier et par période de licence.
"""
import logging
from datetime import date, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

from core.models import RoleChoices

logger = logging.getLogger(__name__)

SEUIL_BANDEAU = 30
PALIERS = ((30, 'J-30'), (15, 'J-15'), (7, 'J-7'), (1, 'J-1'))
PALIERS_NOTIFIES = ('J-15', 'J-7')
ROLES_BANDEAU = (RoleChoices.SUPER_ADMIN, RoleChoices.DIRECTEUR, RoleChoices.DIRECTEUR_RESEAU)

_verifie_le = {}        # établissement → date de la dernière vérification des paliers par ce processus


def licence_de(utilisateur):
    """Licence de l'établissement de ``utilisateur`` (None si aucun établissement ou aucune licence)."""
    etablissement = getattr(utilisateur, 'etablissement', None)
    if etablissement is None:
        return None
    try:
        return etablissement.licence
    except ObjectDoesNotExist:
        return None


def contexte(request):
    """Context processor : ``rappel_licence`` (jours restants, date, lien de renouvellement) pour les administrateurs
    à partir de J-30 ; déclenche au passage, une fois par jour et par processus, la vérification des paliers."""
    utilisateur = getattr(request, 'user', None)
    if utilisateur is None or not utilisateur.is_authenticated or not getattr(utilisateur, 'etablissement_id', None):
        return {}
    administrateur = utilisateur.est_super_admin or utilisateur.role in ROLES_BANDEAU
    a_verifier = _verifie_le.get(utilisateur.etablissement_id) != date.today()
    if not administrateur and not a_verifier:
        return {}
    licence = licence_de(utilisateur)
    if licence is None:
        return {}
    if a_verifier:
        _verifie_le[utilisateur.etablissement_id] = date.today()
        try:
            emettre_rappels(licence)
        except Exception:
            logger.exception("Vérification des rappels de licence impossible")
    if not administrateur:
        return {}
    jours = licence.jours_restants()
    if jours > SEUIL_BANDEAU:
        return {}
    return {'rappel_licence': {
        'jours': jours, 'date_expiration': licence.date_expiration, 'expiree': jours < 0,
        'lien': reverse('licences:renouveler') if utilisateur.est_super_admin else '',
    }}


def emettre_rappels(licence):
    """Crée les alertes des paliers atteints (une seule fois par palier et par période de licence) et, lorsqu'un palier
    J-15 ou J-7 vient d'être atteint, prévient la direction. Retourne les types d'alerte créés."""
    from .models import LicenceAlert, LicenceAuditLog

    jours = licence.jours_restants()
    crees = []
    for seuil, type_alerte in PALIERS:
        if jours > seuil or _alerte_de_la_periode(licence, type_alerte, seuil).exists():
            continue
        alerte = LicenceAlert.objects.create(licence=licence, type_alerte=type_alerte)
        crees.append(alerte)
        LicenceAuditLog.objects.create(licence=licence, action='VERIFICATION', acteur_systeme=True,
                                       description=f"Alerte {type_alerte} créée ({jours} jours restants)")
    a_notifier = [alerte for alerte in crees if alerte.type_alerte in PALIERS_NOTIFIES]
    if a_notifier and jours >= 0:                      # une licence déjà expirée relève du contrôle d'expiration
        destinataires = prevenir_direction(licence, jours)
        for alerte in a_notifier:
            alerte.marquer_comme_envoyee([u.email or u.telephone for u in destinataires])
    return [alerte.type_alerte for alerte in crees]


def _alerte_de_la_periode(licence, type_alerte, seuil):
    """Alertes de ce palier créées pour la période en cours : une alerte J-n ne peut dater que de la fenêtre
    [expiration − n − 1 jour, …[ ; celles d'une période renouvelée depuis sont antérieures et ne comptent plus."""
    from .models import LicenceAlert
    debut_fenetre = licence.date_expiration - timedelta(days=seuil + 1)
    return LicenceAlert.objects.filter(licence=licence, type_alerte=type_alerte, date_alerte__date__gte=debut_fenetre)


def destinataires_direction(licence):
    """Comptes actifs Directeur / Proviseur de l'établissement ; à défaut, ses Super Admin."""
    from accounts.models import User
    comptes = User.objects.filter(etablissement=licence.etablissement, is_active=True)
    direction = list(comptes.filter(role=RoleChoices.DIRECTEUR))
    return direction or list(comptes.filter(role=RoleChoices.SUPER_ADMIN))


def prevenir_direction(licence, jours):
    """Notification interne (+ SMS et e-mail selon la configuration) à la direction ; retourne les destinataires."""
    from core.models import Notification
    from core.notifications import creer_notification

    destinataires = destinataires_direction(licence)
    echeance = "aujourd'hui" if jours == 0 else f"dans {jours} jour{'s' if jours > 1 else ''}"
    titre = f"Licence : expire {echeance}"
    message = (f"La licence de l'école expire le {licence.date_expiration.strftime('%d/%m/%Y')}. "
               "Renouvelez-la pour éviter l'interruption du service.")
    for utilisateur in destinataires:
        lien = reverse('licences:renouveler') if utilisateur.est_super_admin else ''
        creer_notification(utilisateur, Notification.TypeChoices.GENERAL, titre, message, lien=lien)
    if not destinataires:
        logger.warning("Licence %s : aucun compte Directeur ni Super Admin à prévenir", licence.pk)
    return destinataires
