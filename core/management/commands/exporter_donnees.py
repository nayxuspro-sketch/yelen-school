"""
Export complet des données vers une archive de transfert (changement de serveur,
passage du mode autonome SQLite à PostgreSQL).

    python manage.py exporter_donnees                   # data/transfert_<horodatage>.zip
    python manage.py exporter_donnees E:\\transfert.zip

Arrêter l'application avant l'export : la commande refuse un export incohérent.
L'archive contient toutes les données de l'établissement — à traiter comme une
sauvegarde (copie hors machine, suppression après import). Import sur une base
vierge de la même version avec `importer_donnees` (GUIDE_MODE_AUTONOME_SQLITE §7).
"""
import json
import tempfile
import time
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from core.migration_donnees import (
    EXCLUSIONS,
    FORMAT_DONNEES,
    MEMBRE_DONNEES,
    MEMBRE_MANIFESTE,
    VERSION_MANIFESTE,
    effectifs_base,
    effectifs_fichier,
    empreinte_cles,
    fmt_nombre,
    migrations_appliquees,
)


class Command(BaseCommand):
    help = "Exporte toutes les données dans une archive ZIP transférable (voir importer_donnees)."

    def add_arguments(self, parser):
        parser.add_argument('fichier', nargs='?',
                            help="Archive à créer (défaut : data/transfert_<horodatage>.zip)")

    def handle(self, *args, **opts):
        dest = Path(opts['fichier'] or settings.BASE_DIR / 'data' / f"transfert_{time.strftime('%Y%m%d_%H%M%S')}.zip")
        if dest.exists():
            raise CommandError(f"Le fichier existe déjà : {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.monotonic()
        with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
            donnees = Path(tmp) / MEMBRE_DONNEES
            call_command('dumpdata', format=FORMAT_DONNEES, output=str(donnees), use_base_manager=True,
                         use_natural_foreign_keys=True, exclude=list(EXCLUSIONS), verbosity=0)
            effectifs = effectifs_fichier(donnees)
            if not effectifs:
                raise CommandError("Base vide : rien à exporter.")
            modifies = {label: n for label, n in effectifs_base(effectifs).items() if n != effectifs[label]}
            if modifies:
                raise CommandError("La base a été modifiée pendant l'export (%s) : arrêtez l'application "
                                   "puis recommencez." % ', '.join(sorted(modifies)))
            manifeste = {
                'version': VERSION_MANIFESTE,
                'date': timezone.now().isoformat(timespec='seconds'),
                'source': {'moteur': connection.vendor, 'base': str(settings.DATABASES['default']['NAME'])},
                'empreinte_cles': empreinte_cles(),
                'migrations': migrations_appliquees(),
                'effectifs': effectifs,
            }
            with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(donnees, MEMBRE_DONNEES)
                zf.writestr(MEMBRE_MANIFESTE, json.dumps(manifeste, indent=1, ensure_ascii=False))

        total = sum(effectifs.values())
        self.stdout.write(self.style.SUCCESS(
            f"Export terminé : {dest} ({dest.stat().st_size / 1_048_576:.1f} Mo) — "
            f"{fmt_nombre(total)} objets, {len(effectifs)} modèles, {time.monotonic() - t0:.0f} s."))
        self.stdout.write("Archive confidentielle : copiez-la hors machine, supprimez-la après l'import.")
