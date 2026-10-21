"""Services présences — information des parents à la clôture d'un appel."""
from django.utils import timezone

from core.notifications import notifier_absence, notifier_retard
from .models import Presence


def notifier_parents_appel(appel):
    """Informe les parents des absents et retardataires d'un appel clôturé.

    Chaque présence n'est notifiée qu'une seule fois (``parents_notifies_le``) :
    les enregistrements en brouillon n'envoient rien, et une nouvelle clôture
    ne renvoie pas de SMS déjà parti. Renvoie le nombre de familles informées.
    """
    a_notifier = (
        appel.presences
        .filter(statut__in=[Presence.StatutChoices.ABSENT, Presence.StatutChoices.RETARD],
                parents_notifies_le__isnull=True)
        .select_related('appel__matiere', 'inscription__eleve', 'inscription__classe__etablissement')
    )
    nb = 0
    for presence in a_notifier:
        if presence.statut == Presence.StatutChoices.ABSENT:
            notifier_absence(presence)
        else:
            notifier_retard(presence)
        presence.parents_notifies_le = timezone.now()
        presence.save(update_fields=['parents_notifies_le'])
        nb += 1
    return nb
