"""
licences/heartbeat.py
=====================
Phone-home heartbeat signé + révocation + bail offline fenêtre décroissante.

- Payload signé HMAC (LICENCE_SIGNING_KEY) + Ed25519 si clé privée dispo
- Réponse serveur vérifiée (HMAC + Ed25519)
- Si succès : reset failures, bail = now + OFFLINE_MAX_DAYS
- Si échec : failures++, bail décroissant jusqu'à OFFLINE_GRACE_DAYS
- Si bail expiré : licence considérée invalide (middleware bloque)

Utilisation :
    from licences.heartbeat import send_heartbeat
    result = send_heartbeat(licence)  # dict avec ok, action, etc.

Commande cron / management :
    python manage.py check_licences --heartbeat

Le serveur éditeur (LICENCE_HEARTBEAT_URL) doit répondre JSON :
{
  "cle_licence": "YELEN-XXXX-XXXX-XXXX",
  "statut": "ACTIVE" | "REVOQUEE" | "EXPIREE",
  "timestamp": "2026-09-17T10:00:00Z",
  "hmac": "<hex>",
  "ed25519": "<hex optional>",
  "message": "optionnel"
}
"""

import hashlib
import hmac
import json
import logging
from datetime import timedelta
from typing import Dict, Optional
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('licences.heartbeat')


def _get_signing_key() -> bytes:
    key = getattr(settings, 'LICENCE_SIGNING_KEY', '') or settings.SECRET_KEY
    return key.encode('utf-8')


def _load_public_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    import base64
    pub_hex = getattr(settings, 'LICENCE_PUBLIC_KEY', '') or ''
    if not pub_hex:
        return None
    try:
        if len(pub_hex) == 64 and all(c in '0123456789abcdefABCDEF' for c in pub_hex):
            raw = bytes.fromhex(pub_hex)
        else:
            raw = base64.b64decode(pub_hex)
        return Ed25519PublicKey.from_public_bytes(raw)
    except Exception:
        return None


def send_heartbeat(licence, timeout: int = 10) -> Dict:
    """
    Envoie un heartbeat signé au serveur éditeur.

    Returns:
        dict: {
            'ok': bool,
            'action': 'success'|'failure'|'revoked'|'expired'|'no_url'|'error',
            'bail_jours_restants': int|None,
            'message': str,
            'response': dict|None
        }
    """
    url = getattr(settings, 'LICENCE_HEARTBEAT_URL', '') or ''
    if not url:
        return {
            'ok': True,
            'action': 'no_url',
            'bail_jours_restants': licence.get_bail_jours_restants(),
            'message': 'LICENCE_HEARTBEAT_URL non configuré — heartbeat désactivé',
            'response': None,
        }

    payload = licence.generate_heartbeat_payload()
    # Sauvegarde payload pour debug
    try:
        from licences.models import Licence
        Licence.objects.filter(pk=licence.pk).update(heartbeat_payload=payload)
    except Exception:
        pass

    try:
        # Utilise urllib pour éviter dépendance requests
        body = json.dumps(payload).encode('utf-8')
        req = urllib_request.Request(
            url,
            data=body,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'YELEN-SCHOOL-licence-heartbeat/1.0',
                'X-Licence-Key': licence.cle_licence,
            },
            method='POST',
        )
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode('utf-8')
            data = json.loads(resp_body)

        # Vérifier réponse
        if not licence.verify_heartbeat_response(data):
            logger.warning(
                "[HEARTBEAT] Réponse heartbeat invalide (signature) pour %s",
                licence.cle_licence,
            )
            licence.record_heartbeat_failure()
            return {
                'ok': False,
                'action': 'failure',
                'bail_jours_restants': licence.get_bail_jours_restants(),
                'message': 'Signature réponse heartbeat invalide',
                'response': data,
            }

        statut_resp = data.get('statut', '').upper()
        if statut_resp == 'REVOQUEE':
            # Révocation distante → marquer licence révoquée localement
            from licences.models import StatutLicence, LicenceAuditLog
            from django.utils import timezone as tz
            licence.statut = 'REVOQUEE'
            licence.notes_interne += f"\n[{tz.now()}] Révoquée par serveur éditeur (heartbeat)"
            # Sauvegarde via update pour éviter régénération signature avec statut révoqué ?
            # On veut que la signature couvre le nouveau statut, donc save() complet
            try:
                licence.save()
            except Exception:
                from licences.models import Licence as L
                L.objects.filter(pk=licence.pk).update(statut='REVOQUEE')
            # Audit
            try:
                LicenceAuditLog.objects.create(
                    licence=licence,
                    action='REVOCATION',
                    description=f"Révocation distante via heartbeat : {data.get('message','')}",
                    acteur_systeme=True,
                )
            except Exception:
                pass
            logger.critical("[HEARTBEAT] Licence %s révoquée par serveur éditeur", licence.cle_licence)
            return {
                'ok': False,
                'action': 'revoked',
                'bail_jours_restants': 0,
                'message': 'Licence révoquée par serveur éditeur',
                'response': data,
            }

        if statut_resp == 'EXPIREE':
            from licences.models import StatutLicence
            from licences.models import Licence as L
            L.objects.filter(pk=licence.pk).update(statut='EXPIREE')
            logger.warning("[HEARTBEAT] Licence %s expirée selon serveur éditeur", licence.cle_licence)
            return {
                'ok': False,
                'action': 'expired',
                'bail_jours_restants': licence.get_bail_jours_restants(),
                'message': 'Licence expirée selon serveur éditeur',
                'response': data,
            }

        # Succès
        licence.record_heartbeat_success()
        logger.info("[HEARTBEAT] Heartbeat OK pour %s — bail jusqu'à %s", licence.cle_licence, licence.bail_offline_expire_le)
        return {
            'ok': True,
            'action': 'success',
            'bail_jours_restants': licence.get_bail_jours_restants(),
            'message': 'Heartbeat réussi',
            'response': data,
        }

    except (URLError, HTTPError) as exc:
        logger.warning("[HEARTBEAT] Échec heartbeat %s : %s", licence.cle_licence, exc)
        licence.record_heartbeat_failure()
        if licence.is_bail_offline_expired():
            logger.critical("[HEARTBEAT] Bail offline expiré pour %s — blocage imminent", licence.cle_licence)
            return {
                'ok': False,
                'action': 'bail_expired',
                'bail_jours_restants': 0,
                'message': f"Bail offline expiré après {licence.heartbeat_failures} échecs : {exc}",
                'response': None,
            }
        return {
            'ok': False,
            'action': 'failure',
            'bail_jours_restants': licence.get_bail_jours_restants(),
            'message': f"Échec heartbeat ({licence.heartbeat_failures} échecs) : {exc}",
            'response': None,
        }
    except Exception as exc:
        logger.exception("[HEARTBEAT] Erreur inattendue heartbeat %s : %s", licence.cle_licence, exc)
        return {
            'ok': False,
            'action': 'error',
            'bail_jours_restants': licence.get_bail_jours_restants(),
            'message': f"Erreur heartbeat : {exc}",
            'response': None,
        }


def check_all_heartbeats() -> Dict:
    """Envoie heartbeat pour toutes les licences actives qui en ont besoin."""
    from licences.models import Licence, StatutLicence
    result = {
        'total': 0,
        'sent': 0,
        'success': 0,
        'failures': 0,
        'revoked': 0,
        'bail_expired': [],
        'errors': [],
    }
    licences = Licence.objects.filter(statut=StatutLicence.ACTIVE)
    result['total'] = licences.count()
    for lic in licences:
        if not lic.is_heartbeat_required():
            continue
        result['sent'] += 1
        hb = send_heartbeat(lic)
        if hb['ok'] and hb['action'] == 'success':
            result['success'] += 1
        elif hb['action'] == 'revoked':
            result['revoked'] += 1
        elif hb['action'] == 'bail_expired':
            result['bail_expired'].append(lic.cle_licence)
            result['failures'] += 1
        elif not hb['ok']:
            result['failures'] += 1
            if hb['action'] == 'error':
                result['errors'].append(f"{lic.cle_licence}: {hb['message']}")
    return result
