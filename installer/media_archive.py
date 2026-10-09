"""Archive and restore the persistent media volume used by YELEN SCHOOL."""

from __future__ import annotations

import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

MEDIA_ROOT = Path("/app/media")
APP_ROOT = Path("/app")


def archive_media() -> None:
    """Write a gzip-compressed tar archive to stdout."""
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz") as archive:
        archive.add(MEDIA_ROOT, arcname="media", recursive=True)


def _safe_member_target(member: tarfile.TarInfo, extraction_root: Path) -> Path:
    """Return a safe extraction target and reject unsafe tar members."""
    if not member.name or member.issym() or member.islnk():
        raise ValueError(f"Unsupported archive member: {member.name!r}")
    if not (member.isdir() or member.isfile()):
        raise ValueError(f"Unsupported archive member type: {member.name!r}")

    target = (extraction_root / member.name).resolve()
    root = extraction_root.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Archive member outside media directory: {member.name}")
    return target


def _remove_path(path: Path) -> None:
    """Remove a file, symlink, or directory without following symlinks."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def restore_media() -> None:
    """Replace the media volume contents from a gzip tar archive on stdin.

    The archive is extracted to a temporary directory first. This prevents a
    malformed archive from deleting the current media before validation has
    completed, and rejects symlink/hard-link members that could escape the
    media volume.
    """
    if MEDIA_ROOT.is_symlink():
        raise ValueError("The media directory must not be a symbolic link")

    staging_root = Path(tempfile.mkdtemp(prefix=".yelen-media-restore-", dir=APP_ROOT))
    try:
        with tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz") as archive:
            for member in archive:
                _safe_member_target(member, staging_root)
                archive.extract(member, staging_root)

        staged_media = staging_root / "media"
        if not staged_media.is_dir() or staged_media.is_symlink():
            raise ValueError("Archive does not contain a media directory")

        MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        for child in MEDIA_ROOT.iterdir():
            _remove_path(child)
        for child in staged_media.iterdir():
            shutil.move(str(child), str(MEDIA_ROOT / child.name))
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"create", "restore"}:
        raise SystemExit("Usage: media_archive.py create|restore")
    if sys.argv[1] == "create":
        archive_media()
    else:
        restore_media()
