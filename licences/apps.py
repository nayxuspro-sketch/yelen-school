import os
import logging

from django.apps import AppConfig

logger = logging.getLogger('licences.boot')


class LicencesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'licences'
    path = os.path.dirname(__file__)

    def ready(self):
        """
        Vérification d'intégrité des licences au démarrage Django.

        Appelé une seule fois par le processus principal (worker Gunicorn,
        runserver, management commands). Exécution non bloquante : toute
        exception est capturée pour ne pas empêcher le démarrage.
        """
        # Ne pas exécuter pendant les commandes de gestion techniques
        # (makemigrations, migrate, collectstatic…) où la DB peut être absente.
        import sys
        _SKIP_COMMANDS = {
            'makemigrations', 'migrate', 'collectstatic',
            'createsuperuser', 'shell', 'dbshell',
            'flush', 'loaddata', 'dumpdata',
            'test', 'check',
        }
        argv = sys.argv
        if len(argv) > 1 and argv[1] in _SKIP_COMMANDS:
            return

        try:
            from .boot_check import run_boot_check
            run_boot_check()
        except Exception as exc:
            # Ne jamais bloquer le démarrage
            logger.error(
                "[LICENCES BOOT] Erreur inattendue durant la vérification : %s",
                exc,
                exc_info=True,
            )
