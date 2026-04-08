"""Signaux presences — notification absence."""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='presences.Presence')
def presence_post_save(sender, instance, created, **kwargs):
    """Notifie les parents si statut = ABSENT ou RETARD."""
    if instance.statut == 'ABSENT':
        from core.notifications import notifier_absence
        notifier_absence(instance)
    elif instance.statut == 'RETARD':
        from core.notifications import notifier_retard
        notifier_retard(instance)
