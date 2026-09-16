"""Tests unitaires indépendants de la vérification de licence."""

import base64

import pytest

crypto = pytest.importorskip("cryptography")
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from licences.crypto import (
    canonical_payload,
    sign_payload,
    verify_signed_payload,
)
from licences.fingerprint import is_valid_server_fingerprint


def _key_material():
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_b64 = base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    return private_pem, public_b64


def test_canonical_payload_is_order_independent():
    assert canonical_payload({"b": 2, "a": 1}) == canonical_payload({"a": 1, "b": 2})


def test_valid_signature_is_accepted_with_explicit_test_key():
    private_pem, public_b64 = _key_material()
    payload = {"schema": 1, "license_id": "YELEN-AAAA-BBBB-CCCC", "limits": {"max": 10}}
    signature = sign_payload(payload, private_pem)

    assert verify_signed_payload(payload, signature, public_key_b64=public_b64)


def test_payload_modification_is_rejected():
    private_pem, public_b64 = _key_material()
    payload = {"schema": 1, "license_id": "YELEN-AAAA-BBBB-CCCC", "max_users": 5}
    signature = sign_payload(payload, private_pem)

    modified = {**payload, "max_users": 50}
    assert not verify_signed_payload(modified, signature, public_key_b64=public_b64)


def test_invalid_signature_and_missing_embedded_key_are_rejected():
    private_pem, public_b64 = _key_material()
    payload = {"schema": 1, "license_id": "YELEN-AAAA-BBBB-CCCC"}
    signature = sign_payload(payload, private_pem)

    assert not verify_signed_payload(payload, "not-base64", public_key_b64=public_b64)
    # Sans clé explicite, le build de développement n'a volontairement pas de
    # racine de confiance embarquée.
    assert not verify_signed_payload(payload, signature)


def test_server_fingerprint_requires_a_sha256_hex_digest():
    assert is_valid_server_fingerprint('a' * 64)
    assert is_valid_server_fingerprint('A' * 64)
    assert not is_valid_server_fingerprint('')
    assert not is_valid_server_fingerprint('a' * 63)
    assert not is_valid_server_fingerprint('g' * 64)
