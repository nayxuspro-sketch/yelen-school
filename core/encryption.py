"""
core/encryption.py — Utilitaires de chiffrement pour données sensibles YELEN SCHOOL

Ce module fournit des fonctions de chiffrement pour protéger les données sensibles
(numéros CNI, données de salaire, etc.) sans dépendance externe.

Méthode : XOR cipher avec clé dérivée (pour développement) + Hash pour vérification
"""

import base64
import hashlib
import os
from django.conf import settings


def _get_encryption_key():
    """Génère une clé de chiffrement à partir de la SECRET_KEY Django."""
    secret = getattr(settings, 'SECRET_KEY', 'default-dev-key')
    return hashlib.sha256(secret.encode()).digest()


def encrypt_sensitive_data(data: str) -> str:
    """Chiffre une chaîne de données sensibles.
    
    Utilise un XOR cipher avec clé dérivée de la SECRET_KEY.
    Retourne une chaîne encodée en base64.
    """
    if not data:
        return ''
    
    key = _get_encryption_key()
    data_bytes = data.encode('utf-8')
    
    # XOR chaque octet avec la clé (streaming)
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data_bytes))
    
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Déchiffre une chaîne précédemment chiffrée."""
    if not encrypted_data:
        return ''
    
    try:
        key = _get_encryption_key()
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        
        # XOR pour déchiffrer
        decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(encrypted_bytes))
        
        return decrypted.decode('utf-8')
    except Exception:
        return ''  # Retourne chaîne vide si erreur


def hash_sensitive(data: str) -> str:
    """Génère un hash sécurisé pour la vérification d'intégrité."""
    if not data:
        return ''
    return hashlib.sha256(data.encode()).hexdigest()


def mask_cni(cni: str) -> str:
    """Masque un numéro CNI pour affichage partiel (ex: 01XXXXXX23)."""
    if not cni or len(cni) < 8:
        return '****'
    return cni[:2] + '*' * (len(cni) - 4) + cni[-2:]


def mask_phone(phone: str) -> str:
    """Masque un numéro de téléphone pour affichage partiel."""
    if not phone or len(phone) < 8:
        return '****'
    return phone[:4] + '*' * (len(phone) - 8) + phone[-4:]


def mask_email(email: str) -> str:
    """Masque une adresse email pour affichage partiel."""
    if not email or '@' not in email:
        return '****'
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"