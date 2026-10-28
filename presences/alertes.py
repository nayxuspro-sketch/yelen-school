"""Seuil d'absences : à la clôture d'un appel, compte les absences non justifiées de chaque absent sur la période et,
à chaque palier du seuil franchi, crée une alerte, notifie la direction et prévient le parent par SMS."""
import logging

from django.urls import reverse

from core.notifications import creer_notification
from core.sms import sms_actifs
from core.tasks import envoyer_sms_async
from pedagogie.models import Trimestre

from .models import AlerteAbsences, Presence, SeuilAbsences

logger = logging.getLogger(__name__)
ROLES_PREVENUS = ('DIRECTEUR', 'CENSEUR')


def periode_de(appel, reglage):
    """(libellé, date_debut, date_fin) de la période de comptage de l'appel : le trimestre qui contient sa date
    si le réglage est « par période » et qu'un trimestre couvre la date, sinon l'année scolaire."""
    annee = appel.annee_scolaire
    if reglage.par_periode:
        trimestre = Trimestre.objects.filter(annee_scolaire=annee, date_debut__lte=appel.date, date_fin__gte=appel.date).first()
        if trimestre:
            return trimestre.nom, trimestre.date_debut, trimestre.date_fin
    return f"Année {annee.libelle}", annee.date_debut, annee.date_fin


def nb_absences(inscription, debut, fin):
    return Presence.objects.filter(inscription=inscription, statut=Presence.StatutChoices.ABSENT,
                                   appel__date__gte=debut, appel__date__lte=fin).count()


def _telephone_parent(eleve):
    return (eleve.telephone_parent or eleve.tuteur_telephone or eleve.telephone_urgence or '').strip()


def verifier_seuils(appel):
    """Crée les alertes dues par cet appel clôturé ; retourne la liste des alertes créées."""
    etab = appel.classe.etablissement
    reglage = SeuilAbsences.pour(etab)
    if not reglage.actif or reglage.seuil <= 0:
        return []
    periode, debut, fin = periode_de(appel, reglage)
    absents = (appel.presences.filter(statut=Presence.StatutChoices.ABSENT)
               .select_related('inscription__eleve', 'inscription__classe'))
    creees = []
    for presence in absents:
        inscription = presence.inscription
        total = nb_absences(inscription, debut, fin)
        palier = total // reglage.seuil
        if palier < 1 or AlerteAbsences.objects.filter(inscription=inscription, periode=periode, palier=palier).exists():
            continue
        alerte = AlerteAbsences.objects.create(inscription=inscription, periode=periode, palier=palier,
                                               seuil=reglage.seuil, nb_absences=total, date_appel=appel.date)
        _prevenir(alerte, etab, reglage)
        creees.append(alerte)
    return creees


def _prevenir(alerte, etab, reglage):
    from accounts.models import User
    from parametres.models import ModeleMessage
    eleve = alerte.inscription.eleve
    classe = alerte.inscription.classe.nom
    lien = reverse('presences:alertes_absences')
    titre = f"Seuil d'absences atteint — {eleve.get_nom_complet()} ({classe})"
    message = (f"{eleve.get_nom_complet()} ({classe}) totalise {alerte.nb_absences} absences non justifiées "
               f"({alerte.periode}) : seuil de {alerte.seuil} atteint.")
    for user in User.objects.filter(etablissement=etab, role__in=ROLES_PREVENUS, is_active=True):
        try:
            creer_notification(user, 'ABSENCE', titre, message, lien=lien, envoyer_email=False, envoyer_sms=False)
        except Exception:  # la notification ne doit jamais bloquer la clôture de l'appel
            logger.exception("Notification de seuil d'absences impossible pour %s", user)
    numero = _telephone_parent(eleve)
    if reglage.sms_parent and numero and sms_actifs():
        texte = ModeleMessage.get_contenu(etab, 'SEUIL_ABSENCES', {
            'nom_eleve': eleve.get_nom_complet(), 'classe': classe, 'nb': alerte.nb_absences,
            'periode': alerte.periode, 'etablissement': etab.nom,
        })
        if envoyer_sms_async(numero, texte) is not None:
            alerte.sms_envoye = True
            alerte.save(update_fields=['sms_envoye'])
