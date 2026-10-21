"""Réglages de session appliqués à la connexion."""
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from core.models import RoleChoices


@receiver(user_logged_in)
def limiter_session_caisse(sender, request, user, **kwargs):
    """Caisse (Comptable) : la session expire après CAISSE_INACTIVITE_MINUTES sans requête.

    SESSION_SAVE_EVERY_REQUEST prolonge l'échéance à chaque requête : l'expiration
    est donc liée à l'inactivité. Le script static/js/inactivite.js déconnecte aussi
    le poste resté ouvert sans action de l'utilisateur.
    """
    if user.role == RoleChoices.COMPTABLE:
        request.session.set_expiry(settings.CAISSE_INACTIVITE_MINUTES * 60)
