"""
Sauvegarde à chaud de la base SQLite (mode autonome).

    python manage.py sauvegarde_sqlite                # vers BACKUP_DIR (défaut data/backups)
    python manage.py sauvegarde_sqlite --dest E:\\Sauvegardes --garder 60

Utilise l'API de sauvegarde en ligne de SQLite : cohérent même pendant que
l'application écrit (aucune interruption de service). Un simple « copier-coller »
du fichier .sqlite3 pendant l'utilisation NE serait PAS fiable (WAL).

À planifier chaque nuit (Planificateur de tâches Windows / cron).
"""
import gzip
import os
import shutil
import sqlite3
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sauvegarde à chaud de la base SQLite (mode autonome) avec rotation."

    def add_arguments(self, parser):
        parser.add_argument('--dest', default=os.environ.get('BACKUP_DIR', str(settings.BASE_DIR / 'data' / 'backups')))
        parser.add_argument('--garder', type=int, default=int(os.environ.get('BACKUP_KEEP', '30')),
                            help='Nombre de sauvegardes à conserver (rotation)')
        parser.add_argument('--sans-compression', action='store_true')

    def handle(self, *args, **opts):
        db = settings.DATABASES['default']
        if 'sqlite' not in db['ENGINE']:
            raise CommandError("Cette commande ne s'applique qu'au mode SQLite (DB_ENGINE=sqlite).")
        src = Path(db['NAME'])
        if not src.exists():
            raise CommandError(f"Base introuvable : {src}")

        dest_dir = Path(opts['dest'])
        dest_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime('%Y-%m-%d_%H%M%S')
        tmp = dest_dir / f'yelen_school_{stamp}.sqlite3'

        t0 = time.time()
        with sqlite3.connect(src) as source, sqlite3.connect(tmp) as target:
            source.backup(target, pages=4096, sleep=0.01)  # copie par blocs, sans bloquer l'appli
        # Vérification de la copie (en journal classique : pas de fichiers -wal/-shm résiduels)
        check = sqlite3.connect(tmp)
        try:
            check.execute('PRAGMA journal_mode=DELETE')
            ok = check.execute('PRAGMA integrity_check').fetchone()[0]
        finally:
            check.close()
        for residu in (tmp.with_name(tmp.name + '-wal'), tmp.with_name(tmp.name + '-shm')):
            residu.unlink(missing_ok=True)
        if ok != 'ok':
            tmp.unlink(missing_ok=True)
            raise CommandError(f"Sauvegarde corrompue ({ok}) — fichier supprimé.")

        final = tmp
        if not opts['sans_compression']:
            final = tmp.with_suffix('.sqlite3.gz')
            with open(tmp, 'rb') as f_in, gzip.open(final, 'wb', compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out, length=1024 * 1024)
            tmp.unlink()

        # Rotation
        sauvegardes = sorted(dest_dir.glob('yelen_school_*.sqlite3*'))
        for ancienne in sauvegardes[:-opts['garder']] if opts['garder'] > 0 else []:
            ancienne.unlink()

        taille = final.stat().st_size / 1024 / 1024
        self.stdout.write(self.style.SUCCESS(
            f"Sauvegarde OK : {final} ({taille:.1f} Mo) en {time.time() - t0:.1f} s — "
            f"{min(len(sauvegardes), opts['garder'])} sauvegarde(s) conservée(s)."))
