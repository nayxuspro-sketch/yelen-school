import os
from django.apps import AppConfig


class PedagogieConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pedagogie'
    path = os.path.dirname(__file__)
