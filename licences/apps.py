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
        runserver, management commands).

        P1 : si LICENSE_ENFORCEMENT=true + LICENCE_ANTITAMPER_ENABLED=true,
        les anomalies critiques (tampering, bail expiré, binding invalide,
        antitampter) lèvent RuntimeError → arrêt app (check_licences --strict).
        Sinon, dégradation gracieuse (log).
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
            from django.conf import settings
            from .boot_check import run_boot_check

            # P1 : mode strict si antitampter + enforcement activés
            is_strict_boot = (
                getattr(settings, 'LICENSE_ENFORCEMENT', False)
                and getattr(settings, 'LICENCE_ANTITAMPER_ENABLED', False)
            )
            # Permettre de désactiver le strict boot via env var pour debug
            if os.environ.get('LICENCE_DISABLE_STRICT_BOOT', 'false').lower() == 'true':
                is_strict_boot = False

            result = run_boot_check(strict=is_strict_boot)
            if not result['ok'] and is_strict_boot:
                # Déjà levé par run_boot_check en strict, mais au cas où
                critical = result['tampering'] or result['bail_expired'] or result['binding_invalid'] or not result['antitamper']['ok']
                if critical:
                    raise RuntimeError(
                        f"[LICENCES BOOT] Arrêt application — anomalies critiques : "
                        f"tampering={result['tampering']}, bail={result['bail_expired']}, "
                        f"binding={result['binding_invalid']}, antitamper={result['antitamper']['issues']}"
                    )

        except RuntimeError as exc:
            # P1 : arrêt app en mode strict — on log CRITICAL et on relance
            logger.critical("[LICENCES BOOT] %s", exc)
            # En production, on veut vraiment arrêter ; en dev/test, on peut tolérer
            # si l'utilisateur a mis LICENCE_DISABLE_STRICT_BOOT, on ne relance pas
            import os as _os
            if _os.environ.get('LICENCE_DISABLE_STRICT_BOOT', 'false').lower() != 'true':
                raise
        except Exception as exc:
            # Ne jamais bloquer le démarrage en mode non-strict
            logger.error(
                "[LICENCES BOOT] Erreur inattendue durant la vérification : %s",
                exc,
                exc_info=True,
            )
