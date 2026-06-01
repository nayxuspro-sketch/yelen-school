"""
api/authentication.py — Authentification par token avec expiration
===================================================================
Remplace la TokenAuthentication DRF standard par une version qui invalide
automatiquement les tokens après TOKEN_EXPIRY_HOURS heures d'inactivité.

Configuration dans settings.py :
    TOKEN_EXPIRY_HOURS = 24  # expiration après 24 h (défaut)

Le champ `created` du modèle Token DRF est utilisé comme référence temporelle.
Aucune migration n'est nécessaire.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Authentification par token DRF avec expiration automatique.
    Un token trop vieux est révoqué et une erreur 401 est renvoyée.
    """

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        expiry_hours = getattr(settings, 'TOKEN_EXPIRY_HOURS', 24)
        expiry_delta = timedelta(hours=expiry_hours)

        if timezone.now() > token.created + expiry_delta:
            token.delete()
            raise AuthenticationFailed(
                "Token expiré. Veuillez vous reconnecter pour obtenir un nouveau token."
            )

        return user, token
