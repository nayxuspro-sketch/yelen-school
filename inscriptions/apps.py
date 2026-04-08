import os
from django.apps import AppConfig


class InscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inscriptions'
    path = os.path.dirname(__file__)
