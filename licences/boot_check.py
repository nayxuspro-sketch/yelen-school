"""Vérification de cohérence des licences au démarrage Django.

Le contrôle distingue explicitement :
- une ancienne licence HMAC à migrer ;
- une licence Ed25519 falsifiée ;
- une licence signée liée à un autre serveur ;
- une licence arrivée à expiration.

Une licence copiée sur une autre machine n'est pas automatiquement révoquée :
la révocation destructive empêcherait une procédure légitime de remplacement
de serveur. Elle est signalée et doit être refusée par le middleware actif.
"""

from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger("licences.boot")


def run_boot_check() -> dict:
    """Vérifie les licences sans bloquer les commandes de maintenance Django."""
    result = {
        "ok": True,
        "total": 0,
        "valides": 0,
        "tampering": [],
        "binding": [],
        "expirees": [],
        "legacy": [],
        "errors": [],
    }

    try:
        from django.utils import timezone
        from .models import Licence, StatutLicence

        licences = list(
            Licence.objects.only(
                "id",
                "cle_licence",
                "type_licence",
                "date_expiration",
                "statut",
                "signature_hmac",
                "signature_ed25519",
                "signed_payload",
                "etablissement_id",
            )
        )
        result["total"] = len(licences)

        for licence in licences:
            try:
                _verifier_licence(licence, timezone, Licence, StatutLicence, result)
            except Exception as exc:
                result["errors"].append(f"{licence.cle_licence}: {exc}")
                logger.exception(
                    "[LICENCES BOOT] Erreur inattendue sur %s : %s",
                    licence.cle_licence,
                    exc,
                )
    except Exception as exc:
        # Table absente pendant le premier migrate, ou DB temporairement
        # indisponible : le démarrage est laissé aux contrôles de disponibilité.
        msg = f"Impossible d'accéder aux licences au démarrage : {exc}"
        result["errors"].append(msg)
        logger.warning("[LICENCES BOOT] %s", msg)
        return result

    result["ok"] = not any(
        result[key] for key in ("tampering", "binding", "expirees", "legacy", "errors")
    )
    _log_summary(result)
    return result


def _verifier_licence(licence, timezone, Licence, StatutLicence, result):
    """Vérifie une licence individuelle et met à jour le résultat."""
    if not licence.signature_ed25519 or not licence.signed_payload:
        result["legacy"].append(licence.cle_licence)
        logger.warning(
            "[LICENCES BOOT] Licence %s : ancienne signature HMAC détectée. "
            "Migration Ed25519 obligatoire avant commercialisation.",
            licence.cle_licence,
        )
        # Transition non destructive : l'installation existante n'est pas
        # modifiée, mais cette licence n'est pas considérée comme certifiée.
        return

    if not licence.verifier_signature():
        result["tampering"].append(licence.cle_licence)
        logger.critical(
            "[LICENCES BOOT] TAMPERING — licence %s : signature Ed25519 invalide.",
            licence.cle_licence,
        )
        # Révocation automatique d'une signature falsifiée : le statut local ne
        # doit pas permettre de réactiver une ligne dont les données sont modifiées.
        Licence.objects.filter(pk=licence.pk).update(statut=StatutLicence.REVOQUEE)
        _audit_systeme(
            licence,
            "TENTATIVE_FRAUDE",
            "Boot check : signature Ed25519 invalide — révocation automatique",
        )
        return

    if licence.statut == StatutLicence.ACTIVE and not licence.est_liee_au_serveur():
        result["binding"].append(licence.cle_licence)
        logger.critical(
            "[LICENCES BOOT] BINDING — licence %s utilisée sur un serveur différent.",
            licence.cle_licence,
        )
        _audit_systeme(
            licence,
            "TENTATIVE_FRAUDE",
            "Boot check : empreinte serveur différente — accès à refuser",
        )
        return

    if (
        licence.statut == StatutLicence.ACTIVE
        and licence.date_expiration < timezone.now().date()
    ):
        result["expirees"].append(licence.cle_licence)
        logger.warning(
            "[LICENCES BOOT] Licence %s expirée le %s — mise à jour du statut.",
            licence.cle_licence,
            licence.date_expiration,
        )
        Licence.objects.filter(pk=licence.pk).update(statut=StatutLicence.EXPIREE)
        _audit_systeme(
            licence,
            "EXPIRATION",
            f"Boot check : licence expirée le {licence.date_expiration}",
        )
        return

    result["valides"] += 1
    logger.debug(
        "[LICENCES BOOT] Licence %s (%s) vérifiée — expire le %s",
        licence.cle_licence,
        licence.type_licence,
        licence.date_expiration,
    )


def _audit_systeme(licence, action: str, description: str):
    """Enregistre un événement de licence sans bloquer le démarrage."""
    try:
        from django.utils import timezone as tz
        from .models import LicenceAuditLog

        previous = (
            LicenceAuditLog.objects.filter(licence=licence)
            .order_by("-created_at")
            .values_list("hash_actuel", flat=True)
            .first()
        ) or ""
        now = tz.now()
        content = (
            f"{licence.cle_licence}:{action}:{description}:"
            f"{now.isoformat()}:{previous}"
        ).encode("utf-8")
        LicenceAuditLog.objects.bulk_create(
            [
                LicenceAuditLog(
                    licence=licence,
                    action=action,
                    description=description,
                    acteur_systeme=True,
                    hash_precedent=previous,
                    hash_actuel=hashlib.sha256(content).hexdigest(),
                )
            ]
        )
    except Exception as exc:
        logger.warning("[LICENCES BOOT] Impossible d'enregistrer l'audit : %s", exc)


def _log_summary(result: dict):
    level = logging.INFO if result["ok"] else logging.WARNING
    logger.log(
        level,
        "[LICENCES BOOT] %d licence(s) : %d valide(s), %d falsifiée(s), "
        "%d binding(s) invalide(s), %d expirée(s), %d legacy, %d erreur(s).",
        result["total"],
        result["valides"],
        len(result["tampering"]),
        len(result["binding"]),
        len(result["expirees"]),
        len(result["legacy"]),
        len(result["errors"]),
    )
    if result["tampering"]:
        logger.critical(
            "[LICENCES BOOT] ALERTE — licences falsifiées : %s",
            ", ".join(result["tampering"]),
        )
    if result["binding"]:
        logger.critical(
            "[LICENCES BOOT] ALERTE — licences copiées ou serveur remplacé : %s",
            ", ".join(result["binding"]),
        )
