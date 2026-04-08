import os
from django.apps import AppConfig


class ViescolaireConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'viescolaire'
    verbose_name = 'Vie Scolaire'
    path = os.path.dirname(__file__)

    def ready(self):
        import viescolaire.signals  # noqa: F401
