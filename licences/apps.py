import os

from django.apps import AppConfig


class LicencesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'licences'
    path = os.path.dirname(__file__)

    def ready(self):
        """
        Aucune requête SQL ici (Django : « Accessing the database during app
        initialization is discouraged »). La vérification d'intégrité des
        licences (licences.boot_check) s'exécute une seule fois par processus,
        à la première requête HTTP servie — donc jamais pour les commandes de
        gestion. En mode strict (LICENSE_ENFORCEMENT + LICENCE_ANTITAMPER_ENABLED),
        une anomalie critique met l'application en 503 (LicenceCheckMiddleware).
        """
        from django.core.signals import request_started

        from .boot_check import verifier_au_premier_appel

        request_started.connect(verifier_au_premier_appel, dispatch_uid='licences.boot_check')
