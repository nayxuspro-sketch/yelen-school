"""Sauvegarde déclenchée depuis l'interface (mode autonome SQLite) : base à chaud via ``sauvegarde_sqlite`` + archive
ZIP des médias (photos, signatures, justificatifs), liste des sauvegardes disponibles et téléchargement sûr."""
import os
import re
import time
import zipfile
from datetime import datetime
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from .exploitation import dossiers_sauvegarde

NOM_VALIDE = re.compile(r'^yelen_school_[A-Za-z0-9_.-]+$')
MOTIF = 'yelen_school_*'


def dossier_destination():
    return Path(os.environ.get('BACKUP_DIR') or (settings.BASE_DIR / 'data' / 'backups'))


def mode_sqlite():
    return 'sqlite' in settings.DATABASES['default']['ENGINE']


def _archiver_medias(dest_dir, stamp, garder):
    racine = Path(settings.MEDIA_ROOT)
    fichiers = [f for f in racine.rglob('*') if f.is_file()] if racine.exists() else []
    if not fichiers:
        return None
    archive = dest_dir / f'yelen_school_{stamp}_medias.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for f in fichiers:
            zf.write(f, f.relative_to(racine).as_posix())
    anciennes = sorted(dest_dir.glob('yelen_school_*_medias.zip'))
    for vieille in anciennes[:-garder] if garder > 0 else []:
        vieille.unlink(missing_ok=True)
    return archive


def sauvegarder_maintenant(avec_medias=True):
    """Lance la sauvegarde ; retourne ``{'base': Path, 'medias': Path | None, 'duree': secondes}``.
    Lève ``CommandError`` en mode serveur (PostgreSQL : utiliser ``backup-windows.bat``) ou si la copie échoue."""
    if not mode_sqlite():
        raise CommandError("Mode serveur (PostgreSQL) : la sauvegarde se fait avec installer\\backup-windows.bat "
                           "ou la tâche planifiée « YELEN SCHOOL — Sauvegarde ».")
    dest_dir = dossier_destination()
    dest_dir.mkdir(parents=True, exist_ok=True)
    garder = int(os.environ.get('BACKUP_KEEP', '30'))
    t0 = time.time()
    stamp = time.strftime('%Y-%m-%d_%H%M%S')
    call_command('sauvegarde_sqlite', dest=str(dest_dir), garder=garder, stdout=StringIO())
    bases = sorted(dest_dir.glob('yelen_school_*.sqlite3*'), key=lambda f: f.stat().st_mtime)
    if not bases:
        raise CommandError("La sauvegarde n'a produit aucun fichier.")
    medias = _archiver_medias(dest_dir, stamp, garder) if avec_medias else None
    return {'base': bases[-1], 'medias': medias, 'duree': time.time() - t0}


def lister_sauvegardes(limite=20):
    """Sauvegardes visibles (base et médias), de la plus récente à la plus ancienne."""
    fichiers = {f.resolve(): f for d in dossiers_sauvegarde() for f in d.glob(MOTIF) if f.is_file()}
    lignes = []
    for f in sorted(fichiers.values(), key=lambda f: f.stat().st_mtime, reverse=True)[:limite]:
        st = f.stat()
        lignes.append({'nom': f.name, 'dossier': str(f.parent), 'taille_mo': st.st_size / (1024 * 1024),
                       'date': datetime.fromtimestamp(st.st_mtime, tz=timezone.get_current_timezone()), 'type': 'Médias' if f.name.endswith('_medias.zip') else 'Base de données'})
    return lignes


def chemin_sauvegarde(nom):
    """Chemin du fichier de sauvegarde ``nom`` s'il existe dans un dossier de sauvegarde, sinon None (aucun chemin
    relatif ni caractère hors motif n'est accepté)."""
    if not NOM_VALIDE.match(nom or ''):
        return None
    for d in dossiers_sauvegarde():
        candidat = d / nom
        if candidat.is_file() and candidat.parent.resolve() == d.resolve():
            return candidat
    return None
