import os
from django.apps import AppConfig


class ExamensConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'examens'
    path = os.path.dirname(__file__)
