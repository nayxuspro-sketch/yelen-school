"""
core/notifications.py — Service de notifications YELEN SCHOOL

Gère :
- Création de notifications in-app
- Envoi d'emails via le SMTP Django intégré (gratuit)
- Envoi de SMS via modem GSM local (crédits SIM — aucun composant payant)
"""

import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from core.sms import get_sms_val

logger = logging.getLogger(__name__)


def creer_notification(destinataire, type_notif, titre, message, lien='',
                       envoyer_email=True, envoyer_sms=True):
    """
    Crée une notification in-app, envoie optionnellement un email et/ou un SMS.

    Args:
        destinataire : instance User
        type_notif   : str parmi Notification.TypeChoices
        titre        : str
        message      : str
        lien         : str URL relative (ex: '/bulletins/...')
        envoyer_email: bool — envoyer un email si l'utilisateur a un email valide
        envoyer_sms  : bool — envoyer un SMS si SMS_ENABLED et numéro disponible
    """
    from core.models import Notification

    notif = Notification.objects.create(
        destinataire=destinataire,
        type=type_notif,
        titre=titre,
        message=message,
        lien=lien,
    )

    if envoyer_email and destinataire.email:
        try:
            contenu_html = render_to_string('core/emails/notification.html', {
                'user': destinataire,
                'titre': titre,
                'message': message,
                'lien': lien,
                'type': type_notif,
            })
            send_mail(
                subject=f"[YELEN SCHOOL] {titre}",
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@yelenSchool.bf'),
                recipient_list=[destinataire.email],
                html_message=contenu_html,
                fail_silently=True,
            )
            notif.email_envoye = True
            notif.save(update_fields=['email_envoye'])
        except Exception as e:
            logger.error(f"Notification email échoué pour {destinataire.email}: {e}")

    if envoyer_sms and get_sms_val('SMS_ENABLED'):
        numero = getattr(destinataire, 'telephone', '') or ''
        if numero:
            try:
                from core.tasks import envoyer_sms_async
                sms_texte = f"[YELEN SCHOOL] {titre}\n{message}"
                envoyer_sms_async(numero, sms_texte, notification_id=notif.pk)
            except Exception as e:
                logger.error(f"Planification SMS échouée pour {numero}: {e}")

    return notif


def notifier_parents_eleve(eleve, type_notif, titre, message, lien=''):
    """
    Envoie une notification à tous les utilisateurs PARENT liés à cet élève.
    """
    parents = eleve.utilisateurs_lies.filter(role='PARENT', is_active=True)
    for parent in parents:
        creer_notification(parent, type_notif, titre, message, lien)


def _get_sms_message(etablissement, type_msg, variables):
    """Retourne le message SMS personnalisé ou le message par défaut."""
    from parametres.models import ModeleMessage
    return ModeleMessage.get_contenu(etablissement, type_msg, variables)


def notifier_bulletin_publie(bulletin):
    """Notifie les parents quand un bulletin est publié."""
    try:
        eleve = bulletin.inscription.eleve
        classe = bulletin.inscription.classe.nom
        trimestre = bulletin.trimestre.nom
        etab = bulletin.inscription.classe.etablissement
        titre = f"Bulletin disponible — {trimestre}"
        message_inapp = (
            f"Le bulletin de {eleve.get_nom_complet()} ({classe}) "
            f"pour le {trimestre} est maintenant disponible."
        )
        sms_message = _get_sms_message(etab, 'BULLETIN', {
            'nom_eleve': eleve.get_nom_complet(),
            'classe': classe,
            'trimestre': trimestre,
            'etablissement': etab.nom,
        })
        parents = eleve.utilisateurs_lies.filter(role='PARENT', is_active=True)
        for parent in parents:
            creer_notification(parent, 'BULLETIN', titre, message_inapp,
                               lien='/bulletins/', envoyer_sms=False)
            if get_sms_val('SMS_ENABLED'):
                numero = getattr(parent, 'telephone', '') or ''
                if numero:
                    from core.tasks import envoyer_sms_async
                    envoyer_sms_async(numero, sms_message)
    except Exception as e:
        logger.error(f"notifier_bulletin_publie échoué : {e}")


def notifier_absence(presence):
    """Notifie les parents quand une absence est enregistrée."""
    try:
        eleve = presence.inscription.eleve
        etab = presence.inscription.classe.etablissement
        date_appel = presence.appel.date.strftime('%d/%m/%Y')
        matiere = getattr(presence.appel.matiere, 'nom', '') if presence.appel.matiere else ''
        titre = f"Absence signalée — {date_appel}"
        message_inapp = (
            f"{eleve.get_nom_complet()} a été absent(e) le {date_appel}"
            + (f" en {matiere}" if matiere else "") + "."
        )
        
        # Créer les notifications in-app pour les parents (utilisateurs liés avec role PARENT)
        parents = eleve.utilisateurs_lies.filter(role='PARENT', is_active=True)
        for parent in parents:
            creer_notification(parent, 'ABSENCE', titre, message_inapp, lien='')
        
        # Envoyer le SMS
        sms_message = _get_sms_message(etab, 'ABSENCE', {
            'nom_eleve': eleve.get_nom_complet(),
            'date': date_appel,
            'matiere': f" en {matiere}" if matiere else '',
            'etablissement': etab.nom,
        })
        if get_sms_val('SMS_ENABLED'):
            numero = (
                eleve.telephone_parent
                or eleve.tuteur_telephone
                or eleve.telephone_urgence
                or ''
            ).strip()
            if numero:
                from core.tasks import envoyer_sms_async
                envoyer_sms_async(numero, sms_message)
    except Exception as e:
        logger.error(f"notifier_absence échoué : {e}")


def notifier_retard(presence):
    """Notifie les parents quand un retard est enregistré."""
    try:
        eleve = presence.inscription.eleve
        etab = presence.inscription.classe.etablissement
        date_appel = presence.appel.date.strftime('%d/%m/%Y')
        matiere = getattr(presence.appel.matiere, 'nom', '') if presence.appel.matiere else ''
        titre = f"Retard signalé — {date_appel}"
        message_inapp = (
            f"{eleve.get_nom_complet()} est arrivé(e) en retard le {date_appel}"
            + (f" en {matiere}" if matiere else "") + "."
        )
        
        # Créer les notifications in-app pour les parents
        parents = eleve.utilisateurs_lies.filter(role='PARENT', is_active=True)
        for parent in parents:
            creer_notification(parent, 'ABSENCE', titre, message_inapp, lien='')
        
        # Envoyer le SMS
        sms_message = _get_sms_message(etab, 'RETARD', {
            'nom_eleve': eleve.get_nom_complet(),
            'date': date_appel,
            'matiere': f" en {matiere}" if matiere else '',
            'etablissement': etab.nom,
        })
        if get_sms_val('SMS_ENABLED'):
            numero = (
                eleve.telephone_parent
                or eleve.tuteur_telephone
                or eleve.telephone_urgence
                or ''
            ).strip()
            if numero:
                from core.tasks import envoyer_sms_async
                envoyer_sms_async(numero, sms_message)
    except Exception as e:
        logger.error(f"notifier_retard échoué : {e}")


def notifier_relance_paiement(inscription, rubrique, montant):
    """Envoie une relance de paiement aux parents."""
    try:
        eleve = inscription.eleve
        etab = inscription.classe.etablissement
        titre = f"Rappel paiement — {rubrique}"
        message_inapp = (
            f"Un rappel de paiement : {rubrique} de {montant} FCFA "
            f"pour {eleve.get_nom_complet()} est en attente."
        )
        sms_message = _get_sms_message(etab, 'PAIEMENT', {
            'nom_eleve': eleve.get_nom_complet(),
            'montant': f"{montant:,.0f}".replace(',', ' '),
            'rubrique': rubrique,
            'etablissement': etab.nom,
        })
        parents = eleve.utilisateurs_lies.filter(role='PARENT', is_active=True)
        for parent in parents:
            creer_notification(parent, 'GENERAL', titre, message_inapp, envoyer_sms=False)
            if get_sms_val('SMS_ENABLED'):
                numero = getattr(parent, 'telephone', '') or ''
                if numero:
                    from core.tasks import envoyer_sms_async
                    envoyer_sms_async(numero, sms_message)
    except Exception as e:
        logger.error(f"notifier_relance_paiement échoué : {e}")


def notifier_reunion(etablissement, date, heure, lieu, objet, parents_numeros):
    """
    Envoie une convocation de réunion parents-élèves.

    Args:
        etablissement   : instance Etablissement
        date            : str date au format 'dd/mm/YYYY'
        heure           : str heure au format 'HH:MM'
        lieu            : str lieu de la réunion
        objet           : str objet de la réunion
        parents_numeros : list de (User, numero_tel)
    """
    try:
        sms_message = _get_sms_message(etablissement, 'REUNION', {
            'date': date,
            'heure': heure,
            'lieu': lieu,
            'objet': objet,
            'etablissement': etablissement.nom,
        })
        titre = f"Réunion parents — {date}"
        for parent, numero in parents_numeros:
            creer_notification(parent, 'GENERAL', titre, sms_message, envoyer_sms=False)
            if get_sms_val('SMS_ENABLED') and numero:
                from core.tasks import envoyer_sms_async
                envoyer_sms_async(numero, sms_message)
    except Exception as e:
        logger.error(f"notifier_reunion échoué : {e}")


def notifier_sanction(sanction):
    """Notifie les parents quand une sanction est prononcée."""
    try:
        eleve = sanction.inscription.eleve
        type_sanction = sanction.type_sanction.nom if sanction.type_sanction else 'Sanction'
        date = sanction.date_sanction.strftime('%d/%m/%Y')
        titre = f"{type_sanction} — {date}"
        message = (
            f"Une sanction ({type_sanction}) a été prononcée à l'encontre de "
            f"{eleve.get_nom_complet()} le {date}."
        )
        notifier_parents_eleve(eleve, 'SANCTION', titre, message)
    except Exception as e:
        logger.error(f"notifier_sanction échoué : {e}")
