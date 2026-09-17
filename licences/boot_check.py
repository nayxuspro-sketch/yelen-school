"""
licences/boot_check.py
======================
Vérification d'intégrité des licences au démarrage de l'application.

Appelé depuis LicencesConfig.ready() — s'exécute une seule fois au boot.

Contrôles effectués :
  1. Anti-tamper — intégrité code licences (verifier_signature non patchée, clés présentes)
  2. HMAC/Ed25519 — signature stockée correspond-elle aux données actuelles ?
  3. Expiration — licences ACTIVE expirées sans mise à jour ?
  4. Bail offline — heartbeat expiré ?
  5. Binding machine — empreinte invalide ?

En cas d'anomalie :
  - Licence marquée REVOQUEE/EXPIREE
  - Avertissement CRITIQUE logger
  - Si LICENCE_ANTITAMPER_ENABLED + LICENSE_ENFORCEMENT + strict → RuntimeError (arrêt app)
"""

import hashlib
import inspect
import logging
import os
from pathlib import Path

logger = logging.getLogger('licences.boot')


def _check_antitamper() -> dict:
    """
    Vérifie l'intégrité du code licences (anti-tamper P1).

    Returns:
        dict: {'ok': bool, 'issues': list}
    """
    issues = []
    try:
        from django.conf import settings
        # 1. Vérifier que verifier_signature n'a pas été monkey-patchée en stub retournant True
        from . import models as lic_models
        # Inspect source de verifier_signature
        src = inspect.getsource(lic_models.Licence.verifier_signature)
        # Doit contenir 'ed25519' ou 'hmac' ou 'signer' — sinon stub suspect
        if 'verifier_signature_ed25519' not in src and 'signer' not in src and 'hmac' not in src.lower():
            issues.append("verifier_signature semble patchée (pas de vérif crypto détectée)")

        # 2. Vérifier que les settings critiques ne sont pas vides en mode enforcement
        if getattr(settings, 'LICENSE_ENFORCEMENT', False):
            signing_key = getattr(settings, 'LICENCE_SIGNING_KEY', '') or ''
            public_key = getattr(settings, 'LICENCE_PUBLIC_KEY', '') or ''
            # En prod, au moins une des deux doit être configurée pour éviter fallback SECRET_KEY seul
            if not signing_key and not public_key:
                issues.append(
                    "LICENSE_ENFORCEMENT=true mais ni LICENCE_SIGNING_KEY ni LICENCE_PUBLIC_KEY configurés "
                    "— fallback SECRET_KEY seul (faille structurelle)"
                )
            # Si antitampter activé, on exige PUBLIC_KEY (Ed25519) pour vraie asymétrie
            if getattr(settings, 'LICENCE_ANTITAMPER_ENABLED', False) and not public_key:
                issues.append(
                    "LICENCE_ANTITAMPER_ENABLED=true mais LICENCE_PUBLIC_KEY manquante — "
                    "Ed25519 non actif, anti-tamper incomplet"
                )

        # 3. Vérifier que les fichiers critiques existent et ne sont pas vides / stub
        base_dir = Path(__file__).parent
        critical_files = ['models.py', 'middleware.py', 'boot_check.py', 'heartbeat.py']
        for fname in critical_files:
            fpath = base_dir / fname
            if not fpath.exists():
                issues.append(f"Fichier critique manquant : {fname}")
                continue
            size = fpath.stat().st_size
            if size < 100:
                issues.append(f"Fichier critique suspect (trop petit) : {fname} ({size} bytes)")

        # 4. Vérifier que LicenceActivation a bien la contrainte unique active
        from .models import LicenceActivation
        # Vérifier que la contrainte existe dans _meta
        constraint_names = [c.name for c in LicenceActivation._meta.constraints]
        if 'unique_active_activation_per_licence' not in constraint_names:
            issues.append("Contrainte DB unique_active_activation_per_licence manquante — 1 active/licence non garantie")

        # 5. Vérifier que les middlewares de licence sont bien chargés si enforcement
        if getattr(settings, 'LICENSE_ENFORCEMENT', False):
            middlewares = getattr(settings, 'MIDDLEWARE', [])
            required = [
                'licences.middleware.LicenceCheckMiddleware',
                'licences.middleware.LicenceLimitsMiddleware',
            ]
            for mw in required:
                if mw not in middlewares:
                    issues.append(f"Middleware requis manquant en mode enforcement : {mw}")

    except Exception as exc:
        issues.append(f"Erreur vérification anti-tamper : {exc}")
        logger.exception("[LICENCES BOOT] Erreur anti-tamper : %s", exc)

    return {'ok': len(issues) == 0, 'issues': issues}


def run_boot_check(strict: bool = False) -> dict:
    """
    Exécute la vérification complète des licences.

    Args:
        strict: Si True, lève RuntimeError en cas de tampering ou d'anomalie critique
                (utilisé par check_licences --strict et par apps.ready() en mode antitampter)

    Returns:
        dict avec les clés :
            ok          (bool)  — True si aucune anomalie détectée
            total       (int)   — Nombre de licences vérifiées
            valides     (int)   — Licences saines
            tampering   (list)  — Clés de licences avec signature invalide
            expirees    (list)  — Licences ACTIVE mais date dépassée
            bail_expired(list)  — Licences avec bail offline expiré
            binding_invalid(list) — Licences avec binding machine invalide
            antitampter (dict)  — Résultat anti-tamper {'ok': bool, 'issues': []}
            errors      (list)  — Erreurs techniques
    """
    result = {
        'ok': True,
        'total': 0,
        'valides': 0,
        'tampering': [],
        'expirees': [],
        'bail_expired': [],
        'binding_invalid': [],
        'antitamper': {'ok': True, 'issues': []},
        'errors': [],
    }

    # ── 0. Anti-tamper P1 ─────────────────────────────────────────────────
    antitamp = _check_antitamper()
    result['antitamper'] = antitamp
    if not antitamp['ok']:
        result['ok'] = False
        for issue in antitamp['issues']:
            result['errors'].append(f"ANTITAMPER: {issue}")
            logger.critical("[LICENCES BOOT] ANTI-TAMPER — %s", issue)

        # Si strict + antitampter enabled + enforcement → arrêt app
        try:
            from django.conf import settings
            if strict and getattr(settings, 'LICENCE_ANTITAMPER_ENABLED', False) and getattr(settings, 'LICENSE_ENFORCEMENT', False):
                raise RuntimeError(
                    f"[LICENCES BOOT] ANTI-TAMPER ÉCHEC — arrêt application : {'; '.join(antitamp['issues'])}"
                )
        except RuntimeError:
            raise
        except Exception:
            pass

    try:
        from django.utils import timezone
        from .models import Licence, StatutLicence

        licences = list(
            Licence.objects.only(
                'id', 'cle_licence', 'type_licence',
                'date_expiration', 'statut', 'signature_hmac', 'signature_ed25519',
                'dernier_heartbeat', 'bail_offline_expire_le', 'heartbeat_failures',
                'etablissement_id', 'date_activation',
            )
        )
        result['total'] = len(licences)

        for licence in licences:
            try:
                _verifier_licence(licence, timezone, Licence, StatutLicence, result)
            except Exception as exc:
                result['errors'].append(f"{licence.cle_licence}: {exc}")
                logger.exception(
                    "[LICENCES BOOT] Erreur inattendue sur %s : %s",
                    licence.cle_licence, exc
                )

    except Exception as exc:
        # La table n'existe pas encore (première migration) ou autre erreur DB
        msg = f"Impossible d'accéder aux licences au démarrage : {exc}"
        result['errors'].append(msg)
        logger.warning("[LICENCES BOOT] %s", msg)
        # En strict, on ne lève pas si c'est juste table manquante au premier migrate
        if 'no such table' in str(exc).lower() or 'does not exist' in str(exc).lower():
            return result
        if strict:
            # En strict, toute erreur DB est considérée comme critique si enforcement
            try:
                from django.conf import settings
                if getattr(settings, 'LICENSE_ENFORCEMENT', False) and getattr(settings, 'LICENCE_ANTITAMPER_ENABLED', False):
                    raise RuntimeError(f"[LICENCES BOOT] Erreur critique DB en mode strict : {exc}") from exc
            except RuntimeError:
                raise
        return result

    result['ok'] = not (
        result['tampering'] or result['expirees'] or result['bail_expired']
        or result['binding_invalid'] or result['errors'] or not result['antitamper']['ok']
    )
    _log_summary(result)

    # Mode strict : si anomalies et enforcement + antitampter, arrêt app
    if strict and not result['ok']:
        try:
            from django.conf import settings
            if getattr(settings, 'LICENCE_ANTITAMPER_ENABLED', False) and getattr(settings, 'LICENSE_ENFORCEMENT', False):
                # On ne bloque que si tampering ou antitampter ou bail expiré, pas pour simple expiration
                critical = result['tampering'] or result['bail_expired'] or result['binding_invalid'] or not result['antitamper']['ok']
                if critical:
                    raise RuntimeError(
                        f"[LICENCES BOOT] STRICT — anomalies critiques détectées : "
                        f"tampering={result['tampering']}, bail_expired={result['bail_expired']}, "
                        f"binding_invalid={result['binding_invalid']}, antitamper={result['antitamper']['issues']}"
                    )
        except RuntimeError:
            raise
        except Exception:
            pass

    return result


def _verifier_licence(licence, timezone, Licence, StatutLicence, result):
    """Vérifie une licence individuelle et met à jour result."""

    # ── 1. Vérification signature (Ed25519 prioritaire, HMAC fallback) ─────
    if not licence.verifier_signature():
        result['tampering'].append(licence.cle_licence)
        result['ok'] = False

        logger.critical(
            "[LICENCES BOOT] TAMPERING DÉTECTÉ — Licence %s : "
            "signature invalide (Ed25519/HMAC). Révocation automatique.",
            licence.cle_licence,
        )

        Licence.objects.filter(pk=licence.pk).update(
            statut=StatutLicence.REVOQUEE,
        )
        _audit_systeme(licence, 'TENTATIVE_FRAUDE',
                       "Boot check : signature invalide — révocation automatique")
        return

    # ── 2. Vérification expiration ─────────────────────────────────────────
    if (
        licence.statut == StatutLicence.ACTIVE
        and licence.date_expiration < timezone.now().date()
    ):
        result['expirees'].append(licence.cle_licence)
        result['ok'] = False

        logger.warning(
            "[LICENCES BOOT] Licence %s expirée le %s — mise à jour du statut.",
            licence.cle_licence,
            licence.date_expiration,
        )

        Licence.objects.filter(pk=licence.pk).update(
            statut=StatutLicence.EXPIREE,
        )
        _audit_systeme(licence, 'EXPIRATION',
                       f"Boot check : licence expirée le {licence.date_expiration}")
        return

    # ── 3. Vérification bail offline (heartbeat) ───────────────────────────
    try:
        if licence.bail_offline_expire_le and licence.is_bail_offline_expired():
            result['bail_expired'].append(licence.cle_licence)
            result['ok'] = False
            logger.critical(
                "[LICENCES BOOT] BAIL OFFLINE EXPIRÉ — Licence %s : dernier heartbeat %s, bail jusqu'à %s",
                licence.cle_licence,
                licence.dernier_heartbeat,
                licence.bail_offline_expire_le,
            )
            # On ne révoque pas automatiquement, mais on log et on considère comme anomalie
            _audit_systeme(licence, 'EXPIRATION',
                           f"Boot check : bail offline expiré (dernier heartbeat {licence.dernier_heartbeat})")
            # En mode strict + antitampter, cette licence sera bloquée par middleware
    except Exception as exc:
        logger.warning("[LICENCES BOOT] Erreur vérif bail offline %s : %s", licence.cle_licence, exc)

    # ── 4. Vérification binding machine (si activé) ────────────────────────
    try:
        from django.conf import settings as _s
        if getattr(_s, 'LICENCE_BINDING_ENABLED', False):
            # Vérifier les activations actives
            from .models import LicenceActivation
            activations = LicenceActivation.objects.filter(licence=licence, est_active=True)
            for act in activations:
                if not act.verify_fingerprint():
                    result['binding_invalid'].append(f"{licence.cle_licence}@{act.hostname}")
                    result['ok'] = False
                    logger.critical(
                        "[LICENCES BOOT] BINDING INVALIDE — Licence %s activation %s : empreinte invalide",
                        licence.cle_licence, act.id
                    )
                    _audit_systeme(licence, 'TENTATIVE_FRAUDE',
                                   f"Boot check : binding machine invalide pour activation {act.id}")
    except Exception as exc:
        logger.warning("[LICENCES BOOT] Erreur vérif binding %s : %s", licence.cle_licence, exc)

    # ── 5. Tout est sain ───────────────────────────────────────────────────
    if licence.cle_licence not in result['tampering'] and licence.cle_licence not in result['expirees'] and licence.cle_licence not in result['bail_expired']:
        result['valides'] += 1

    logger.debug(
        "[LICENCES BOOT] Licence %s (%s) OK — expire le %s",
        licence.cle_licence,
        licence.type_licence,
        licence.date_expiration,
    )


def _audit_systeme(licence, action: str, description: str):
    """
    Enregistre une entrée d'audit système sans lever d'exception.
    """
    try:
        from django.utils import timezone as tz
        from .models import LicenceAuditLog
        import hashlib

        derniere = (
            LicenceAuditLog.objects
            .filter(licence=licence)
            .order_by('-created_at')
            .values_list('hash_actuel', flat=True)
            .first()
        ) or ''

        now = tz.now()
        contenu = (
            f"{licence.cle_licence}:{action}:{description}:"
            f"{now.isoformat()}:{derniere}"
        ).encode('utf-8')
        hash_actuel = hashlib.sha256(contenu).hexdigest()

        LicenceAuditLog.objects.bulk_create([
            LicenceAuditLog(
                licence=licence,
                action=action,
                description=description,
                acteur_systeme=True,
                hash_precedent=derniere,
                hash_actuel=hash_actuel,
            )
        ])
    except Exception as exc:
        logger.warning("[LICENCES BOOT] Impossible d'enregistrer l'audit : %s", exc)


def _log_summary(result: dict):
    """Émet un résumé lisible dans les logs."""
    level = logging.INFO if result['ok'] else logging.WARNING

    logger.log(
        level,
        "[LICENCES BOOT] Vérification terminée — "
        "%d licence(s) contrôlée(s) : %d valide(s), "
        "%d signature(s) invalide(s), %d expirée(s), %d bail expiré(s), "
        "%d binding invalide(s), %d erreur(s). Antitamper OK=%s",
        result['total'],
        result['valides'],
        len(result['tampering']),
        len(result['expirees']),
        len(result['bail_expired']),
        len(result['binding_invalid']),
        len(result['errors']),
        result['antitamper']['ok'],
    )

    if result['tampering']:
        logger.critical(
            "[LICENCES BOOT] ALERTE SÉCURITÉ — Licences avec tampering : %s",
            ', '.join(result['tampering']),
        )
    if result['expirees']:
        logger.warning(
            "[LICENCES BOOT] Licences expirées corrigées : %s",
            ', '.join(result['expirees']),
        )
    if result['bail_expired']:
        logger.critical(
            "[LICENCES BOOT] BAIL OFFLINE EXPIRÉ — Licences : %s",
            ', '.join(result['bail_expired']),
        )
    if result['binding_invalid']:
        logger.critical(
            "[LICENCES BOOT] BINDING INVALIDE — %s",
            ', '.join(result['binding_invalid']),
        )
    if not result['antitamper']['ok']:
        logger.critical(
            "[LICENCES BOOT] ANTI-TAMPER ÉCHEC — %s",
            '; '.join(result['antitamper']['issues']),
        )
