"""
core/sms.py — Service SMS YELEN SCHOOL

Deux backends disponibles, sélectionnés via SMS_BACKEND dans settings.py :

  'http'   — Passerelle HTTP locale WiFi via l'app Android "SMS Gateway"
             (recommandé — Android récent, réseau local, sans root)
             App : https://github.com/capcom6/android-sms-gateway
             Config : SMS_HTTP_URL, SMS_HTTP_USER, SMS_HTTP_PASSWORD

  'serial' — Modem GSM USB ou Bluetooth SPP via commandes AT / pyserial
             (modems USB type Huawei E173, ou Android via Bluetooth)
             Config : SMS_MODEM_PORT, SMS_MODEM_BAUD, SMS_MODEM_TIMEOUT

Variables settings.py communes :
  SMS_ENABLED  = True/False
  SMS_BACKEND  = 'http' | 'serial'   (défaut : 'http')
"""

import logging
import re
import time

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

SMS_CACHE_KEY = 'yelen_sms_runtime_config'

SMS_VARS = [
    'SMS_ENABLED', 'SMS_BACKEND',
    'SMS_HTTP_URL', 'SMS_HTTP_USER', 'SMS_HTTP_PASSWORD', 'SMS_HTTP_TIMEOUT',
    'SMS_MODEM_PORT', 'SMS_MODEM_BAUD', 'SMS_MODEM_TIMEOUT',
]

SMS_DEFAULTS = {
    'SMS_ENABLED':       False,
    'SMS_BACKEND':       'http',
    'SMS_HTTP_URL':      'http://192.168.1.100:8080/message',
    'SMS_HTTP_USER':     'admin',
    'SMS_HTTP_PASSWORD': '',
    'SMS_HTTP_TIMEOUT':  10,
    'SMS_MODEM_PORT':    'COM3',
    'SMS_MODEM_BAUD':    9600,
    'SMS_MODEM_TIMEOUT': 10,
}


def get_sms_config() -> dict:
    """Lit la config SMS : priorite au cache (runtime), puis settings."""
    runtime = cache.get(SMS_CACHE_KEY, {})
    config = {}
    for key in SMS_VARS:
        if key in runtime:
            config[key] = runtime[key]
        else:
            config[key] = getattr(settings, key, SMS_DEFAULTS.get(key))
    return config


def get_sms_val(key: str):
    """Lit une seule valeur de config SMS."""
    runtime = cache.get(SMS_CACHE_KEY, {})
    if key in runtime:
        return runtime[key]
    return getattr(settings, key, SMS_DEFAULTS.get(key))


def set_sms_config_runtime(**kwargs):
    """Ecrit les valeurs runtime dans le cache (prise en compte immediate, sans redemarrage)."""
    runtime = cache.get(SMS_CACHE_KEY, {})
    runtime.update(kwargs)
    cache.set(SMS_CACHE_KEY, runtime, timeout=None)
    logger.info(f"Config SMS runtime mise a jour : {', '.join(kwargs.keys())}")


# ── Validation et normalisation ───────────────────────────────────────────────

def _numero_valide(numero: str) -> bool:
    """Vérifie qu'un numéro ressemble à un mobile valide (Burkina ou international)."""
    n = re.sub(r'[\s\-\.]', '', numero or '')
    return bool(re.fullmatch(r'(\+226|00226)?[0-9]{8}', n))


def _normaliser_numero(numero: str) -> str:
    """Normalise en format international +226XXXXXXXX (Burkina Faso)."""
    numero = numero.strip().replace(' ', '').replace('-', '')
    if numero.startswith('00226'):
        return '+226' + numero[5:]
    if len(numero) == 8 and not numero.startswith('+'):
        return '+226' + numero
    return numero


# ── Backend HTTP (WiFi local — recommandé) ────────────────────────────────────

def _envoyer_http(numero: str, message: str) -> tuple:
    """
    Envoie un SMS via l'app Android 'SMS Gateway' sur le réseau WiFi local.

    L'app expose une API REST sur http://<ip-telephone>:<port>.
    Aucune connexion Internet requise — trafic 100 % local.

    App Android (open source, APK disponible hors ligne) :
      https://github.com/capcom6/android-sms-gateway
    Installation :
      1. Installer l'APK sur le téléphone Android
      2. Démarrer le serveur dans l'app (bouton "Start")
      3. Noter l'IP et le port affichés (ex : 192.168.1.45:8080)
      4. Reporter dans SMS_HTTP_URL, SMS_HTTP_USER, SMS_HTTP_PASSWORD
    """
    import urllib.request
    import urllib.error
    import json
    import base64

    url      = get_sms_val('SMS_HTTP_URL')
    user     = get_sms_val('SMS_HTTP_USER')
    password = get_sms_val('SMS_HTTP_PASSWORD')
    timeout  = int(get_sms_val('SMS_HTTP_TIMEOUT'))

    payload = json.dumps({
        'message':      message,
        'phoneNumbers': [numero],
    }).encode('utf-8')

    credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            'Content-Type':  'application/json',
            'Authorization': f'Basic {credentials}',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status in (200, 201, 202):
                logger.info(f"SMS HTTP envoyé → {numero}")
                return True, ''
            body = resp.read().decode('utf-8', errors='replace')
            motif = f"HTTP {resp.status} : {body[:200]}"
            logger.error(f"SMS HTTP échoué → {numero} : {motif}")
            return False, motif
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        motif = f"HTTP {e.code} : {body[:200]}"
        logger.error(f"SMS HTTP erreur → {numero} : {motif}")
        return False, motif
    except urllib.error.URLError as e:
        motif = (
            f"Impossible de joindre la passerelle SMS ({url}). "
            f"Vérifiez que l'app 'SMS Gateway' est démarrée sur le téléphone "
            f"et que le PC et le téléphone sont sur le même réseau WiFi. "
            f"Détail : {e.reason}"
        )
        logger.error(f"SMS HTTP connexion échouée → {numero} : {e.reason}")
        return False, motif
    except Exception as e:
        motif = str(e)
        logger.error(f"SMS HTTP exception → {numero} : {motif}")
        return False, motif


# ── Backend série / AT commands (modem USB ou Bluetooth SPP) ─────────────────

def _get_serial():
    """Ouvre la connexion série vers le modem GSM."""
    try:
        import serial
    except ImportError:
        raise RuntimeError(
            "pyserial non installé. "
            "Copiez le dossier 'serial' depuis votre installation Python vers le venv."
        )
    port    = get_sms_val('SMS_MODEM_PORT')
    baud    = get_sms_val('SMS_MODEM_BAUD')
    timeout = int(get_sms_val('SMS_MODEM_TIMEOUT'))
    return serial.Serial(port, baudrate=baud, timeout=timeout)


def _envoyer_at(ser, commande, attente=1.0):
    """Envoie une commande AT et retourne la réponse."""
    ser.write((commande + '\r').encode('utf-8'))
    time.sleep(attente)
    reponse = ser.read(ser.in_waiting or 64).decode('utf-8', errors='replace')
    return reponse.strip()


def _envoyer_serial(numero: str, message: str) -> tuple:
    """Envoie un SMS via modem GSM (AT commands / pyserial)."""
    try:
        ser = _get_serial()
    except RuntimeError as e:
        return False, str(e)

    try:
        rep = _envoyer_at(ser, 'AT')
        if 'OK' not in rep:
            motif = (
                f"Le modem ne répond pas à la commande AT (réponse : {rep!r}). "
                f"Vérifiez le port {get_sms_val('SMS_MODEM_PORT')} et le branchement."
            )
            logger.error(f"SMS série échoué — {motif}")
            return False, motif

        rep = _envoyer_at(ser, 'AT+CMGF=1')
        if 'OK' not in rep:
            motif = f"Impossible de passer en mode texte (AT+CMGF=1, réponse : {rep!r})."
            logger.error(f"SMS série échoué — {motif}")
            return False, motif

        _envoyer_at(ser, 'AT+CSCS="GSM"')

        ser.write(f'AT+CMGS="{numero}"\r'.encode('utf-8'))
        time.sleep(1.0)
        prompt = ser.read(ser.in_waiting or 16).decode('utf-8', errors='replace')
        if '>' not in prompt:
            motif = (
                f"Le modem n'a pas renvoyé le prompt '>' (reçu : {prompt!r}). "
                "Numéro peut-être invalide."
            )
            logger.error(f"SMS série échoué — {motif}")
            return False, motif

        ser.write((message + '\x1A').encode('utf-8'))
        time.sleep(3.0)
        reponse = ser.read(ser.in_waiting or 128).decode('utf-8', errors='replace')

        if '+CMGS:' in reponse or 'OK' in reponse:
            logger.info(f"SMS série envoyé → {numero}")
            return True, ''

        motif = (
            f"Le réseau a refusé l'envoi (réponse modem : {reponse.strip()!r}). "
            "Vérifiez le crédit SIM et la couverture réseau."
        )
        logger.error(f"SMS série échoué → {numero} : {motif}")
        return False, motif

    finally:
        ser.close()


# ── Point d'entrée principal ──────────────────────────────────────────────────

def envoyer_sms(numero: str, message: str) -> tuple:
    """
    Envoie un SMS via le backend configuré (HTTP ou série).

    Returns:
        (True, '')           si succès
        (False, 'motif')     si échec
    """
    if not get_sms_val('SMS_ENABLED'):
        return False, "SMS_ENABLED est désactivé dans la configuration."

    if not _numero_valide(numero):
        motif = f"Numéro invalide ignoré : {numero!r} (attendu : 8 chiffres ou +226XXXXXXXX)"
        logger.warning(motif)
        return False, motif

    numero = _normaliser_numero(numero)

    if len(message) > 160:
        message = message[:157] + '...'

    backend = str(get_sms_val('SMS_BACKEND')).lower()

    if backend == 'http':
        return _envoyer_http(numero, message)
    if backend == 'serial':
        return _envoyer_serial(numero, message)

    motif = f"SMS_BACKEND inconnu : '{backend}'. Valeurs valides : 'http', 'serial'."
    logger.error(motif)
    return False, motif


# ── Diagnostic ────────────────────────────────────────────────────────────────

def tester_modem() -> dict:
    """
    Teste la connexion au backend SMS actif.

    Returns:
        dict : {'ok': bool, 'message': str, 'operateur': str|None, 'backend': str}
    """
    backend = str(get_sms_val('SMS_BACKEND')).lower()

    if not get_sms_val('SMS_ENABLED'):
        return {
            'ok': False,
            'message': 'SMS désactivé (SMS_ENABLED=False)',
            'operateur': None,
            'backend': backend,
        }

    if backend == 'http':
        import urllib.request
        import urllib.error
        import base64
        url      = get_sms_val('SMS_HTTP_URL')
        user     = get_sms_val('SMS_HTTP_USER')
        password = get_sms_val('SMS_HTTP_PASSWORD')
        timeout  = int(get_sms_val('SMS_HTTP_TIMEOUT'))
        # Ping sur /health (endpoint de l'app SMS Gateway)
        base_url = '/'.join(url.split('/')[:3]) + '/health'
        credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
        req = urllib.request.Request(
            base_url,
            headers={'Authorization': f'Basic {credentials}'},
        )
        try:
            urllib.request.urlopen(req, timeout=timeout)
            return {'ok': True, 'message': 'Passerelle HTTP joignable', 'operateur': None, 'backend': 'http'}
        except Exception as e:
            return {'ok': False, 'message': str(e), 'operateur': None, 'backend': 'http'}

    if backend == 'serial':
        try:
            ser = _get_serial()
            try:
                rep_at = _envoyer_at(ser, 'AT')
                if 'OK' not in rep_at:
                    return {'ok': False, 'message': f'Modem ne répond pas ({rep_at!r})', 'operateur': None, 'backend': 'serial'}
                rep_op = _envoyer_at(ser, 'AT+COPS?')
                operateur = None
                if '+COPS:' in rep_op:
                    parties = rep_op.split('"')
                    if len(parties) >= 2:
                        operateur = parties[1]
                return {'ok': True, 'message': 'Modem connecté', 'operateur': operateur, 'backend': 'serial'}
            finally:
                ser.close()
        except Exception as e:
            return {'ok': False, 'message': str(e), 'operateur': None, 'backend': 'serial'}

    return {'ok': False, 'message': f"Backend inconnu : '{backend}'", 'operateur': None, 'backend': backend}
