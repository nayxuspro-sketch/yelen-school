import os
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    path = os.path.dirname(__file__)

    def ready(self):
        from . import signals  # noqa: F401 — enregistre les receveurs
