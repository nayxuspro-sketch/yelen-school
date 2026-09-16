"""Empreinte locale utilisée pour lier une licence à son serveur.

Cette empreinte est une dissuasion contre la copie simple, pas une preuve
contre un administrateur système capable de modifier Windows ou le code.
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import socket
import uuid


def _windows_machine_guid() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\\Microsoft\\Cryptography",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip().lower()
    except (FileNotFoundError, OSError, ImportError):
        return ""


def _unix_machine_id() -> str:
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            value = open(path, "r", encoding="ascii").read().strip().lower()
        except (OSError, UnicodeError):
            continue
        if value:
            return value
    return ""


def is_valid_server_fingerprint(value: str) -> bool:
    """Vérifie le format canonique d'une empreinte serveur SHA-256."""
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value.strip().lower()))


def get_server_fingerprint() -> str:
    """Retourne un SHA-256 stable de plusieurs identifiants locaux."""
    machine_id = _windows_machine_guid() or _unix_machine_id()
    mac = f"{uuid.getnode():012x}"
    hostname = socket.gethostname().strip().lower()
    system = platform.system().strip().lower()
    # Le hostname seul n'est pas suffisamment fiable ; il complète les autres
    # valeurs uniquement pour les environnements dépourvus de machine-id.
    material = "|".join(("yelen-school-v1", system, machine_id, mac, hostname))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
