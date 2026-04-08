"""
licences/boot_check.py
======================
Vérification d'intégrité des licences au démarrage de l'application.

Appelé depuis LicencesConfig.ready() — s'exécute une seule fois au boot.

Contrôles effectués :
  1. HMAC — la signature stockée correspond-elle aux données actuelles ?
  2. Expiration — des licences ACTIVE sont-elles déjà expirées sans mise à jour ?
  3. Révocation — les licences REVOQUEE sont-elles correctement marquées ?

En cas d'anomalie :
  - La licence est marquée REVOQUEE (si signature invalide) ou EXPIREE
  - Un avertissement CRITIQUE est émis dans le logger Django
  - Le démarrage N'EST PAS bloqué (dégradation gracieuse)
"""

import logging

logger = logging.getLogger('licences.boot')


def run_boot_check() -> dict:
    """
    Exécute la vérification complète des licences.

    Returns:
        dict avec les clés :
            ok          (bool)  — True si aucune anomalie détectée
            total       (int)   — Nombre de licences vérifiées
            valides     (int)   — Licences saines
            tampering   (list)  — Clés de licences avec signature invalide
            expirees    (list)  — Licences ACTIVE mais date dépassée
            errors      (list)  — Erreurs techniques (DB inaccessible, etc.)
    """
    result = {
        'ok': True,
        'total': 0,
        'valides': 0,
        'tampering': [],
        'expirees': [],
        'errors': [],
    }

    try:
        from django.utils import timezone
        from .models import Licence, StatutLicence

        licences = list(
            Licence.objects.only(
                'id', 'cle_licence', 'type_licence',
                'date_expiration', 'statut', 'signature_hmac',
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
        return result

    result['ok'] = not (result['tampering'] or result['expirees'] or result['errors'])
    _log_summary(result)
    return result


def _verifier_licence(licence, timezone, Licence, StatutLicence, result):
    """Vérifie une licence individuelle et met à jour result."""

    # ── 1. Vérification HMAC (intégrité cryptographique) ──────────────────
    if not licence.verifier_signature():
        result['tampering'].append(licence.cle_licence)
        result['ok'] = False

        logger.critical(
            "[LICENCES BOOT] TAMPERING DÉTECTÉ — Licence %s : "
            "signature HMAC invalide. Révocation automatique.",
            licence.cle_licence,
        )

        # Marquer comme révoquée sans passer par save() complet
        # (évite de regénérer la signature avec les données corrompues)
        Licence.objects.filter(pk=licence.pk).update(
            statut=StatutLicence.REVOQUEE,
        )
        _audit_systeme(licence, 'TENTATIVE_FRAUDE',
                       "Boot check : signature HMAC invalide — révocation automatique")
        return  # Ne pas continuer la vérification d'une licence corrompue

    # ── 2. Vérification expiration (licences ACTIVE expirées) ─────────────
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

    # ── 3. Tout est sain ───────────────────────────────────────────────────
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
    Utilise update() pour éviter les effets de bord du save() de LicenceAuditLog.
    """
    try:
        from django.utils import timezone as tz
        from .models import LicenceAuditLog
        import hashlib

        # Dernière entrée pour le chaînage
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

        # bulk_create bypass save() (qui appelle _generer_hash avec created_at=None)
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
        "%d signature(s) invalide(s), %d expirée(s), %d erreur(s).",
        result['total'],
        result['valides'],
        len(result['tampering']),
        len(result['expirees']),
        len(result['errors']),
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
