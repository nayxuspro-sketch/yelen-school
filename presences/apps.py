import os
from django.apps import AppConfig


class PresencesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'presences'
    path = os.path.dirname(__file__)

    def ready(self):
        import presences.signals  # noqa: F401
