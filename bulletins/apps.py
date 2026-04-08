import os
from django.apps import AppConfig


class BulletinsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bulletins'
    path = os.path.dirname(__file__)

    def ready(self):
        import bulletins.signals  # noqa: F401
