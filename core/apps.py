import os
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    path = os.path.dirname(__file__)

    def ready(self):
        import core.signals  # noqa: F401
        # Mode autonome (DB_ENGINE=sqlite) : PRAGMA WAL & co. sur chaque connexion
        from core.db_sqlite import register as register_sqlite_pragmas
        register_sqlite_pragmas()
