"""Signaux bulletins — notification publication."""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


@receiver(pre_save, sender='bulletins.Bulletin')
def bulletin_pre_save(sender, instance, **kwargs):
    """Mémorise l'état de publication avant modification."""
    if instance.pk:
        try:
            instance._ancien_publie = sender.objects.values('est_publie').get(pk=instance.pk)['est_publie']
        except sender.DoesNotExist:
            instance._ancien_publie = False
    else:
        instance._ancien_publie = False


@receiver(post_save, sender='bulletins.Bulletin')
def bulletin_post_save(sender, instance, created, **kwargs):
    """Notifie les parents si le bulletin vient d'être publié."""
    ancien = getattr(instance, '_ancien_publie', False)
    if not ancien and instance.est_publie:
        from core.notifications import notifier_bulletin_publie
        notifier_bulletin_publie(instance)
