import os
from django.apps import AppConfig


class EtablissementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'etablissements'
    path = os.path.dirname(__file__)
