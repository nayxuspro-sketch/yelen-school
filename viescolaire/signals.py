"""Signaux viescolaire — notification sanction."""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='viescolaire.SanctionDisciplinaire')
def sanction_post_save(sender, instance, created, **kwargs):
    """Notifie les parents à la création d'une sanction."""
    if created:
        from core.notifications import notifier_sanction
        notifier_sanction(instance)
