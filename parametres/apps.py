import os
from django.apps import AppConfig


class ParametresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parametres'
    path = os.path.dirname(__file__)
