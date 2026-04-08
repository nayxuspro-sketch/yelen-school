import os
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    path = os.path.dirname(__file__)

    def ready(self):
        import core.signals  # noqa: F401
