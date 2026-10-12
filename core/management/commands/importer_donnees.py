"""
Import d'une archive produite par `exporter_donnees` dans une base vierge
(même version de l'application, mêmes clés secrètes dans `.env`).

    python manage.py importer_donnees transfert.zip

Contrôles avant import : archive, migrations identiques, clés identiques, base
cible vierge. L'import est atomique : au moindre écart d'effectif, rien n'est
conservé. Les effectifs importés sont affichés modèle par modèle.
"""
import json
import tempfile
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.migration_donnees import (
    MEMBRE_DONNEES,
    MEMBRE_MANIFESTE,
    MODELES_INITIALISES_PAR_MIGRATE,
    VERSION_MANIFESTE,
    charger_fichier,
    effectifs_base,
    empreinte_cles,
    fmt_nombre,
    migrations_appliquees,
)
from core.signals import disable_audit, enable_audit


@contextmanager
def _cache_cles_naturelles(modele):
    """Mémorise la résolution des clés naturelles d'un modèle pendant l'import :
    une requête par utilisateur au lieu d'une par référence (created_by,
    updated_by, encaisse_par… sur chaque ligne importée)."""
    manager_cls = type(modele._default_manager)
    heritee = 'get_by_natural_key' not in vars(manager_cls)
    original = manager_cls.get_by_natural_key
    cache = {}

    def avec_cache(self, *cle):
        if cle not in cache:
            cache[cle] = original(self, *cle)
        return cache[cle]

    manager_cls.get_by_natural_key = avec_cache
    try:
        yield
    finally:
        if heritee:
            del manager_cls.get_by_natural_key
        else:
            manager_cls.get_by_natural_key = original


class Command(BaseCommand):
    help = "Importe une archive exporter_donnees dans une base vierge (contrôles, import atomique, effectifs)."

    def add_arguments(self, parser):
        parser.add_argument('fichier', help="Archive .zip produite par exporter_donnees")

    def handle(self, *args, **opts):
        archive = Path(opts['fichier'])
        if not archive.is_file():
            raise CommandError(f"Archive introuvable : {archive}")
        with zipfile.ZipFile(archive) as zf:
            if MEMBRE_MANIFESTE not in zf.namelist() or MEMBRE_DONNEES not in zf.namelist():
                raise CommandError("Archive invalide : elle n'a pas été produite par exporter_donnees.")
            manifeste = json.loads(zf.read(MEMBRE_MANIFESTE))
            if manifeste.get('version') != VERSION_MANIFESTE:
                raise CommandError(f"Version d'archive {manifeste.get('version')} non prise en charge.")
            attendus = manifeste['effectifs']
            self._controler(manifeste, attendus)

            t0 = time.monotonic()
            self.stdout.write(f"Import de {fmt_nombre(sum(attendus.values()))} objets ({len(attendus)} modèles)…")
            with tempfile.TemporaryDirectory(dir=archive.parent) as tmp:  # même disque que l'archive
                self._importer(zf.extract(MEMBRE_DONNEES, tmp), attendus)

        for label, n in attendus.items():
            self.stdout.write(f"  {label:<44}{fmt_nombre(n):>12}")
        self.stdout.write(self.style.SUCCESS(
            f"Import terminé : effectifs conformes pour les {len(attendus)} modèles "
            f"({time.monotonic() - t0:.0f} s)."))
        self._verifier_licences()

    def _controler(self, manifeste, attendus):
        ecarts = sorted(set(manifeste['migrations']) ^ set(migrations_appliquees()))
        if ecarts:
            raise CommandError("Versions différentes : migrations non communes (%s%s). Mettez les deux "
                               "installations à la même version, puis recommencez l'export."
                               % (', '.join(ecarts[:5]), '…' if len(ecarts) > 5 else ''))
        if manifeste['empreinte_cles'] != empreinte_cles():
            raise CommandError("SECRET_KEY / LICENCE_SIGNING_KEY différentes de celles de la source : reportez "
                               "les valeurs de l'ancien .env (données chiffrées et licences illisibles sinon).")
        occupes = {label: n for label, n in effectifs_base(attendus).items()
                   if n and label not in MODELES_INITIALISES_PAR_MIGRATE}
        if occupes:
            raise CommandError("Base cible non vide : %s. L'import exige une base vierge (migrate seul, "
                               "ENSURE_ADMIN=false)." % ', '.join(f'{label} ({n})' for label, n in occupes.items()))
        self.stdout.write(f"Contrôles : version, migrations identiques ({len(manifeste['migrations'])}), "
                          "clés identiques, base cible vierge — OK.")

    def _importer(self, chemin, attendus):
        disable_audit()  # les lignes importées existent déjà dans le journal d'audit importé
        try:
            with transaction.atomic(), _cache_cles_naturelles(get_user_model()):
                for label in sorted(MODELES_INITIALISES_PAR_MIGRATE & attendus.keys()):
                    apps.get_model(label)._base_manager.all().delete()
                charger_fichier(chemin)
                obtenus = effectifs_base(attendus)
                ecarts = {label: (n, obtenus[label]) for label, n in attendus.items() if obtenus[label] != n}
                if ecarts:
                    raise CommandError("Effectifs non conformes : " + ', '.join(
                        f'{label} attendu {n} obtenu {m}' for label, (n, m) in ecarts.items()))
        except CommandError as exc:
            raise CommandError(f"Import annulé, aucune donnée conservée — {exc}") from exc
        except Exception as exc:
            raise CommandError(f"Import annulé, aucune donnée conservée — {exc.__class__.__name__} : {exc}") from exc
        finally:
            enable_audit()

    def _verifier_licences(self):
        from licences.models import Licence

        licences = list(Licence._base_manager.all())
        invalides = [lic for lic in licences if not lic.verifier_signature()]
        if invalides:
            self.stdout.write(self.style.WARNING(
                f"Licences : {len(invalides)} signature(s) invalide(s) sur {len(licences)} — vérifiez "
                "LICENCE_SIGNING_KEY / SECRET_KEY, puis python manage.py check_licences."))
        else:
            self.stdout.write(f"Licences : {len(licences)} vérifiée(s), signatures valides.")
