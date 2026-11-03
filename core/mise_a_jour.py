"""Dépôt et vérification d'une archive de mise à jour `.zip` depuis l'interface web.

L'application web ne monte jamais `/var/run/docker.sock` : elle vérifie l'intégrité du `.zip`
(absence de traversée de chemin, plafond de taille, en-tête git bundle, empreinte SHA-256 et
progression de version), dépose atomiquement le bundle vérifié et `demande.json` dans le dossier
partagé `mises-a-jour/`, puis l'agent planifié côté hôte Windows exécute `mettre-a-jour.ps1`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
import zipfile
from datetime import timedelta
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.audit import record_audit

logger = logging.getLogger(__name__)

TAILLE_MAX_DECOMPRESSEE = 300 * 1024 * 1024  # 300 Mo
DELAI_EXPIRATION_EN_COURS = timedelta(minutes=30)
_RE_BUNDLE = re.compile(r'^yelen-school-(\d+\.\d+\.\d+)\.bundle$')
_RE_VERSION = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')
_RE_SHA256 = re.compile(r'^[0-9a-f]{64}$')
_ENTETES_BUNDLE = (b'# v2 git bundle\n', b'# v3 git bundle\n')


class ErreurArchiveMiseAJour(ValueError):
    """Archive absente, corrompue, mal formée ou d'une version antérieure."""


def dossier_mises_a_jour() -> Path:
    chemin = getattr(settings, 'YELEN_UPDATE_DIR', None)
    return Path(chemin) if chemin else Path(settings.BASE_DIR) / 'mises-a-jour'


def parser_version(texte: str) -> tuple[int, int, int]:
    m = _RE_VERSION.fullmatch((texte or '').strip())
    if not m:
        raise ErreurArchiveMiseAJour(f"Numéro de version invalide : {texte!r}.")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def etat_demande() -> dict | None:
    """Retourne l'état courant de `mises-a-jour/demande.json` (ou `None` s'il n'y en a pas)."""
    fichier = dossier_mises_a_jour() / 'demande.json'
    if not fichier.is_file():
        return None
    try:
        demande = json.loads(fichier.read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Lecture impossible de %s : %s", fichier, exc)
        return None
    if not isinstance(demande, dict):
        return None

    statut = demande.get('statut')
    cible = demande.get('version_cible')
    if statut in ('EN_ATTENTE', 'EN_COURS') and cible:
        try:
            if parser_version(settings.YELEN_VERSION) >= parser_version(cible):
                demande = {
                    **demande,
                    'statut': 'TERMINEE',
                    'message': f"Mise à jour vers {cible} appliquée avec succès.",
                }
        except ErreurArchiveMiseAJour as exc:
            logger.warning("Version cible illisible dans demande.json : %s", exc)
    return demande


def _est_en_cours_recent(demande: dict | None) -> bool:
    if not demande or demande.get('statut') != 'EN_COURS':
        return False
    horodatage = demande.get('debut_le') or demande.get('demande_le') or ''
    debut = parse_datetime(str(horodatage)) if horodatage else None
    if debut is None:
        return False
    if timezone.is_naive(debut):
        debut = timezone.make_aware(debut, timezone.get_current_timezone())
    return (timezone.now() - debut) < DELAI_EXPIRATION_EN_COURS


def _verifier_chemin_membre(nom: str) -> str:
    normalise = nom.replace('\\', '/')
    if normalise.startswith('/'):
        raise ErreurArchiveMiseAJour("Chemin absolu interdit dans l'archive .zip.")
    parties = PurePosixPath(normalise).parts
    if '..' in parties:
        raise ErreurArchiveMiseAJour("Chemin relatif sortant interdit dans l'archive .zip.")
    return PurePosixPath(normalise).name


def _inspecter_zip(zf: zipfile.ZipFile) -> tuple[zipfile.ZipInfo, zipfile.ZipInfo, str, str]:
    taille_totale = 0
    bundles: list[tuple[zipfile.ZipInfo, str, str]] = []
    par_nom: dict[str, zipfile.ZipInfo] = {}

    for info in zf.infolist():
        if info.is_dir():
            continue
        nom_court = _verifier_chemin_membre(info.filename)
        if info.file_size < 0:
            raise ErreurArchiveMiseAJour("Taille de membre invalide dans l'archive .zip.")
        taille_totale += info.file_size
        if taille_totale > TAILLE_MAX_DECOMPRESSEE:
            raise ErreurArchiveMiseAJour("Archive trop volumineuse (limite de 300 Mo décompressés).")
        par_nom[nom_court] = info
        m = _RE_BUNDLE.fullmatch(nom_court)
        if m:
            bundles.append((info, nom_court, m.group(1)))

    if not bundles:
        raise ErreurArchiveMiseAJour(
            "Archive incomplète : aucun fichier yelen-school-<version>.bundle trouvé dans le .zip."
        )
    if len(bundles) > 1:
        raise ErreurArchiveMiseAJour("Archive ambiguë : plusieurs fichiers .bundle présents dans le .zip.")

    info_bundle, nom_bundle, version_cible = bundles[0]
    info_sha = par_nom.get(f'{nom_bundle}.sha256')
    if info_sha is None:
        raise ErreurArchiveMiseAJour(
            f"Empreinte SHA-256 absente de l'archive ({nom_bundle}.sha256 manquant)."
        )
    if info_sha.file_size > 4096:
        raise ErreurArchiveMiseAJour("Fichier d'empreinte SHA-256 anormalement volumineux.")
    return info_bundle, info_sha, nom_bundle, version_cible


def _lire_empreinte_attendue(zf: zipfile.ZipFile, info_sha: zipfile.ZipInfo) -> str:
    try:
        brut = zf.read(info_sha).decode('utf-8-sig').strip()
    except UnicodeDecodeError as exc:
        logger.warning("Fichier .sha256 non UTF-8 : %s", exc)
        raise ErreurArchiveMiseAJour("Empreinte SHA-256 illisible dans l'archive.") from exc
    jeton = (brut.split() or [''])[0].lower()
    if not _RE_SHA256.fullmatch(jeton):
        raise ErreurArchiveMiseAJour("Empreinte SHA-256 mal formée dans l'archive (64 caractères hexadécimaux attendus).")
    return jeton


def _ecrire_json_atomique(cible: Path, donnees: dict) -> None:
    tmp = cible.parent / f'.{cible.name}.{uuid.uuid4().hex}.tmp'
    try:
        tmp.write_text(json.dumps(donnees, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(tmp, cible)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def deposer_archive_zip(fichier_upload, *, utilisateur, request=None) -> dict:
    """Valide une archive `.zip` de mise à jour et prépare son exécution dans `mises-a-jour/`."""
    if not fichier_upload:
        raise ErreurArchiveMiseAJour("Veuillez sélectionner une archive de mise à jour (.zip).")

    if _est_en_cours_recent(etat_demande()):
        raise ErreurArchiveMiseAJour(
            "Une mise à jour est déjà en cours d'application sur le serveur. Patientez jusqu'à la fin de l'opération."
        )

    dossier = dossier_mises_a_jour()
    dossier.mkdir(parents=True, exist_ok=True)
    tmp_bundle = dossier / f'.upload-{uuid.uuid4().hex}.tmp'

    try:
        try:
            zf_ctx = zipfile.ZipFile(fichier_upload)
        except (zipfile.BadZipFile, OSError) as exc:
            logger.warning("Archive de mise à jour non valide : %s", exc)
            raise ErreurArchiveMiseAJour("Le fichier sélectionné n'est pas une archive .zip valide.") from exc

        with zf_ctx as zf:
            info_bundle, info_sha, nom_bundle, version_cible = _inspecter_zip(zf)
            attendu = _lire_empreinte_attendue(zf, info_sha)

            calcul = hashlib.sha256()
            entete_verifie = False
            octets_lus = 0
            with zf.open(info_bundle) as source, tmp_bundle.open('wb') as sortie:
                while True:
                    bloc = source.read(1024 * 1024)
                    if not bloc:
                        break
                    octets_lus += len(bloc)
                    if octets_lus > TAILLE_MAX_DECOMPRESSEE:
                        raise ErreurArchiveMiseAJour("Archive trop volumineuse (limite de 300 Mo décompressés).")
                    if not entete_verifie:
                        if not bloc.startswith(_ENTETES_BUNDLE):
                            raise ErreurArchiveMiseAJour(
                                "Le fichier .bundle contenu dans l'archive n'est pas un bundle Git valide."
                            )
                        entete_verifie = True
                    calcul.update(bloc)
                    sortie.write(bloc)

            if not entete_verifie:
                raise ErreurArchiveMiseAJour("Le fichier .bundle contenu dans l'archive est vide.")

            reel = calcul.hexdigest().lower()
            if reel != attendu:
                raise ErreurArchiveMiseAJour(
                    "Empreinte SHA-256 incorrecte : l'archive est altérée ou incomplète. Rien n'a été modifié."
                )

        t_cible = parser_version(version_cible)
        t_actuelle = parser_version(settings.YELEN_VERSION)
        if t_cible < t_actuelle:
            raise ErreurArchiveMiseAJour(
                f"Version antérieure refusée ({version_cible} < {settings.YELEN_VERSION})."
            )
        if t_cible == t_actuelle:
            return {'deja_a_jour': True, 'version_cible': version_cible}

        for ancien in dossier.glob('yelen-school-*.bundle*'):
            ancien.unlink(missing_ok=True)

        chemin_bundle = dossier / nom_bundle
        os.replace(tmp_bundle, chemin_bundle)
        (dossier / f'{nom_bundle}.sha256').write_text(f'{attendu}  {nom_bundle}\n', encoding='utf-8')

        demande = {
            'version_avant': settings.YELEN_VERSION,
            'version_cible': version_cible,
            'archive': nom_bundle,
            'empreinte': attendu,
            'statut': 'EN_ATTENTE',
            'demande_le': timezone.now().isoformat(),
            'demande_par': getattr(utilisateur, 'username', '') or str(utilisateur),
            'message': (
                "Archive vérifiée (SHA-256). En attente d'application automatique par le serveur "
                "(délai habituel : moins d'une minute)."
            ),
        }
        _ecrire_json_atomique(dossier / 'demande.json', demande)

        record_audit(
            action='SECURITY',
            user=utilisateur,
            request=request,
            app_label='core',
            model_name='miseajour',
            object_id=version_cible,
            object_repr=f"Mise à jour {settings.YELEN_VERSION} -> {version_cible}",
            reason='Dépôt archive .zip vérifiée',
            changes={
                'version_avant': settings.YELEN_VERSION,
                'version_cible': version_cible,
                'archive': nom_bundle,
                'empreinte': attendu,
            },
        )
        return demande
    finally:
        if tmp_bundle.exists():
            tmp_bundle.unlink(missing_ok=True)
