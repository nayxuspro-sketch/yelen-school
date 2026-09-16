"""Cryptographie des licences hors ligne YELEN SCHOOL.

La licence commerciale est un document signé avec Ed25519 :
- la clé privée reste chez l'éditeur ;
- seule la clé publique est embarquée dans l'application ;
- aucune clé secrète de signature n'est stockée chez le client.

Ce module ne lit volontairement pas une clé publique depuis ``.env`` en
production. Une clé publique fournie par l'installation cliente pourrait être
remplacée avec le code ou la base et ne constituerait plus une racine de
confiance. La clé officielle est définie dans ``embedded_key.py`` lors du
processus de release.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any, Mapping

try:  # La dépendance est obligatoire pour une installation commerciale.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
except ImportError:  # pragma: no cover - couvert par le contrôle de dépendance
    serialization = None
    Ed25519PrivateKey = None
    Ed25519PublicKey = None

from .embedded_key import ED25519_PUBLIC_KEY_B64


class LicenseCryptoError(ValueError):
    """Erreur de format ou de configuration cryptographique de licence."""


def canonical_payload(payload: Mapping[str, Any]) -> bytes:
    """Sérialise un payload de manière déterministe avant signature."""
    if not isinstance(payload, Mapping):
        raise LicenseCryptoError("Le payload de licence doit être un objet JSON.")
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise LicenseCryptoError("Le payload de licence contient une valeur invalide.") from exc


def _decode_base64(value: str, *, expected_length: int, label: str) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise LicenseCryptoError(f"{label} absente.")
    try:
        raw = base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise LicenseCryptoError(f"{label} Base64 invalide.") from exc
    if len(raw) != expected_length:
        raise LicenseCryptoError(
            f"{label} invalide : {expected_length} octets attendus, {len(raw)} reçus."
        )
    return raw


def _require_crypto() -> None:
    if Ed25519PublicKey is None or Ed25519PrivateKey is None or serialization is None:
        raise LicenseCryptoError(
            "La dépendance cryptography est absente. "
            "Une installation commerciale ne peut pas vérifier une licence sans elle."
        )


def public_key_from_base64(public_key_b64: str | None = None):
    """Construit une clé publique Ed25519 depuis sa représentation Base64."""
    _require_crypto()
    key_b64 = ED25519_PUBLIC_KEY_B64 if public_key_b64 is None else public_key_b64
    raw = _decode_base64(key_b64, expected_length=32, label="Clé publique Ed25519")
    return Ed25519PublicKey.from_public_bytes(raw)


def signature_from_base64(signature_b64: str) -> bytes:
    """Décode une signature Ed25519 de 64 octets."""
    return _decode_base64(signature_b64, expected_length=64, label="Signature Ed25519")


def verify_signed_payload(
    payload: Mapping[str, Any],
    signature_b64: str,
    *,
    public_key_b64: str | None = None,
) -> bool:
    """Vérifie une signature Ed25519.

    Toute erreur de format, clé absente ou signature invalide retourne False.
    Le détail ne doit pas être exposé à un utilisateur distant.
    """
    try:
        public_key = public_key_from_base64(public_key_b64)
        signature = signature_from_base64(signature_b64)
        public_key.verify(signature, canonical_payload(payload))
    except Exception:
        # InvalidSignature et les erreurs de format doivent toutes produire un
        # refus fermé, sans exposer de détail cryptographique à distance.
        return False
    return True


def _load_private_key(private_key_data: bytes, password: bytes | None = None):
    _require_crypto()
    if not isinstance(private_key_data, bytes):
        raise LicenseCryptoError("La clé privée doit être fournie sous forme binaire.")
    try:
        key = serialization.load_pem_private_key(private_key_data, password=password)
    except (ValueError, TypeError) as exc:
        raise LicenseCryptoError("Clé privée Ed25519 PEM invalide ou mot de passe incorrect.") from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise LicenseCryptoError("La clé privée fournie n'est pas une clé Ed25519.")
    return key


def sign_payload(
    payload: Mapping[str, Any],
    private_key_data: bytes,
    *,
    password: bytes | None = None,
) -> str:
    """Signe un payload pour l'outil d'émission fournisseur.

    Cette fonction ne doit jamais être appelée avec une clé privée installée
    chez un client. Le résultat est une signature Base64 standard.
    """
    key = _load_private_key(private_key_data, password=password)
    signature = key.sign(canonical_payload(payload))
    return base64.b64encode(signature).decode("ascii")


def generate_key_pair(password: bytes | None = None) -> tuple[bytes, str]:
    """Génère une clé privée PEM et sa clé publique Base64.

    La clé privée est chiffrée avec ``password`` lorsqu'il est fourni. L'outil
    fournisseur exige un mot de passe afin de ne pas créer par inadvertance
    une clé privée en clair sur disque.
    """
    _require_crypto()
    private_key = Ed25519PrivateKey.generate()
    encryption = (
        serialization.BestAvailableEncryption(password)
        if password
        else serialization.NoEncryption()
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )
    public_b64 = base64.b64encode(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    return private_pem, public_b64


def payload_matches_licence(
    payload: Mapping[str, Any],
    *,
    license_id: str,
    etablissement_id: str,
    type_licence: str,
    date_expiration: str,
) -> bool:
    """Vérifie que la ligne locale correspond aux champs signés."""
    expected = {
        "license_id": str(license_id),
        "etablissement_id": str(etablissement_id),
        "type_licence": str(type_licence),
        "date_expiration": str(date_expiration),
    }
    return all(str(payload.get(key, "")) == value for key, value in expected.items())
