"""
licences/jeton.py
=================
Jeton de licence hors ligne (format v3) — signé Ed25519 par l'éditeur,
vérifié par l'application avec la seule clé publique (LICENCE_PUBLIC_KEY).

Format texte : ``YELEN3.<payload base64url>.<signature base64url>``

Le payload est un JSON canonique (clés triées) contenant l'identité de la
licence : clé, type, établissement (UUID), dates et empreinte du serveur
autorisé (vide = licence non liée à un serveur). La signature porte sur les
octets exacts du payload : aucune clé privée côté école, aucun secret partagé.
"""
from __future__ import annotations

import logging
import base64
import binascii
import json
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

PREFIXE = 'YELEN3'
VERSION = 3
CHAMPS_REQUIS = (
    'v', 'cle', 'type', 'etablissement', 'date_activation',
    'date_expiration', 'empreinte_serveur', 'emis_le',
)


class JetonInvalide(ValueError):
    """Jeton illisible, signature invalide ou contenu incohérent."""


# ── Clés ────────────────────────────────────────────────────────────────────

def _decoder_cle(valeur: str) -> bytes:
    """Clé encodée hex (64 caractères) ou base64 → 32 octets bruts."""
    valeur = (valeur or '').strip()
    if len(valeur) == 64 and all(c in '0123456789abcdefABCDEF' for c in valeur):
        return bytes.fromhex(valeur)
    return base64.b64decode(valeur)


def charger_cle_publique(valeur: str):
    """Clé publique Ed25519 depuis sa forme texte (None si vide ou invalide)."""
    if not (valeur or '').strip():
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        return Ed25519PublicKey.from_public_bytes(_decoder_cle(valeur))
    except Exception:
        logger.error("Jeton : clé publique Ed25519 illisible", exc_info=True)
        return None


def charger_cle_privee(valeur: str):
    """Clé privée Ed25519 depuis sa forme texte (None si vide ou invalide)."""
    if not (valeur or '').strip():
        return None
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        return Ed25519PrivateKey.from_private_bytes(_decoder_cle(valeur))
    except Exception:
        logger.error("Jeton : clé privée Ed25519 illisible", exc_info=True)
        return None


# ── Encodage ────────────────────────────────────────────────────────────────

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def _de_b64url(texte: str) -> bytes:
    texte = texte.strip()
    return base64.urlsafe_b64decode(texte + '=' * (-len(texte) % 4))


def construire_payload(*, cle, type_licence, etablissement_id, date_expiration,
                       empreinte_serveur='', date_activation=None) -> dict:
    """Payload canonique d'un jeton v3 (toutes les valeurs en texte)."""
    if date_activation is None:
        date_activation = datetime.now(timezone.utc)
    if isinstance(date_expiration, (datetime, date)):
        date_expiration = date_expiration.isoformat()[:10]
    return {
        'v': VERSION,
        'cle': str(cle).strip().upper(),
        'type': str(type_licence).strip().upper(),
        'etablissement': str(etablissement_id),
        'date_activation': date_activation.isoformat(),
        'date_expiration': str(date_expiration),
        'empreinte_serveur': (empreinte_serveur or '').strip().lower(),
        'emis_le': datetime.now(timezone.utc).isoformat(),
    }


def emettre_jeton(payload: dict, cle_privee) -> str:
    """Signe le payload (éditeur) et retourne le jeton texte."""
    octets = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=True).encode('utf-8')
    signature = cle_privee.sign(octets)
    return f"{PREFIXE}.{_b64url(octets)}.{_b64url(signature)}"


# ── Décodage / vérification ────────────────────────────────────────────────

def normaliser_jeton(texte: str) -> str:
    """Supprime espaces et retours à la ligne (jeton collé ou copié d'un courriel)."""
    return ''.join((texte or '').split())


def lire_jeton(texte: str) -> tuple[dict, bytes, bytes]:
    """Décompose un jeton → (payload, octets du payload, signature). Ne vérifie pas la signature."""
    texte = normaliser_jeton(texte)
    parties = texte.split('.')
    if len(parties) != 3 or parties[0] != PREFIXE:
        raise JetonInvalide("Format de code de licence non reconnu.")
    try:
        octets = _de_b64url(parties[1])
        signature = _de_b64url(parties[2])
        payload = json.loads(octets.decode('utf-8'))
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise JetonInvalide("Code de licence illisible.") from exc
    if not isinstance(payload, dict) or payload.get('v') != VERSION:
        raise JetonInvalide("Version de code de licence non prise en charge.")
    manquants = [c for c in CHAMPS_REQUIS if c not in payload]
    if manquants:
        raise JetonInvalide("Code de licence incomplet.")
    return payload, octets, signature


def verifier_jeton(texte: str, cle_publique) -> dict:
    """Vérifie la signature Ed25519 du jeton et retourne son payload.

    Raises:
        JetonInvalide: clé publique absente, format invalide ou signature fausse.
    """
    if cle_publique is None:
        raise JetonInvalide("Clé publique de l'éditeur non configurée (LICENCE_PUBLIC_KEY).")
    payload, octets, signature = lire_jeton(texte)
    try:
        cle_publique.verify(signature, octets)
    except Exception as exc:
        raise JetonInvalide("Signature du code de licence invalide.") from exc
    return payload


def payload_correspond(payload: dict, licence) -> bool:
    """Le payload décrit-il exactement cette licence (identité immuable) ?"""
    return (
        payload.get('cle') == licence.cle_licence
        and payload.get('type') == licence.type_licence
        and payload.get('etablissement') == str(licence.etablissement_id)
        and payload.get('date_expiration') == licence.date_expiration.isoformat()
        and (payload.get('empreinte_serveur') or '') == (licence.empreinte_serveur or '')
    )
