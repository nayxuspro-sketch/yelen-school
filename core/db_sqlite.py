"""
core/db_sqlite.py — Réglages SQLite pour le mode autonome (DB_ENGINE=sqlite)
=============================================================================

Django 4.2 n'offre pas d'option ``init_command`` pour SQLite : on applique donc
les PRAGMA à l'ouverture de chaque connexion via le signal ``connection_created``.

Pourquoi ces réglages sont indispensables avec plusieurs utilisateurs :

- ``journal_mode=WAL``   : les lectures ne sont plus bloquées par les écritures
                           (et inversement). Sans WAL, 20 utilisateurs génèrent
                           rapidement des erreurs « database is locked ».
- ``synchronous=NORMAL`` : durable en mode WAL (pas de corruption en cas de
                           coupure de courant), nettement plus rapide que FULL.
- ``busy_timeout``       : un worker qui veut écrire pendant qu'un autre écrit
                           attend (jusqu'à 30 s) au lieu d'échouer immédiatement.
- ``foreign_keys=ON``    : Django l'active déjà, on le garantit explicitement.
- ``cache_size`` / ``temp_store`` : performances des agrégations (bulletins, stats).

Le fichier doit résider sur un disque LOCAL du serveur (jamais un partage réseau
SMB/NFS : le verrouillage WAL n'y est pas fiable).
"""
import logging

from django.conf import settings
from django.db.backends.signals import connection_created

logger = logging.getLogger(__name__)

SQLITE_PRAGMAS = (
    'PRAGMA journal_mode=WAL',
    'PRAGMA synchronous=NORMAL',
    'PRAGMA busy_timeout=30000',
    'PRAGMA foreign_keys=ON',
    'PRAGMA cache_size=-65536',   # 64 Mo de cache de pages par connexion
    'PRAGMA temp_store=MEMORY',
    'PRAGMA mmap_size=268435456',  # 256 Mo de lecture par mmap (accélère les lectures)
)


def configure_sqlite(sender, connection, **kwargs):
    """Applique les PRAGMA sur toute nouvelle connexion SQLite."""
    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        for pragma in SQLITE_PRAGMAS:
            try:
                cursor.execute(pragma)
            except Exception as exc:  # pragma: no cover — ne doit jamais bloquer l'appli
                logger.warning("SQLite: impossible d'appliquer %s (%s)", pragma, exc)


def register():
    """Branche le signal (appelé depuis CoreConfig.ready)."""
    if getattr(settings, 'IS_SQLITE', False):
        connection_created.connect(configure_sqlite, dispatch_uid='yelen_sqlite_pragmas')
