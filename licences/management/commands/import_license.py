"""Importe et active un document de licence signé hors ligne."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from etablissements.models import Etablissement
from licences.crypto import verify_signed_payload
from licences.fingerprint import get_server_fingerprint
from licences.models import Licence, StatutLicence, TypeLicence


class Command(BaseCommand):
    help = "Vérifie puis importe un document de licence Ed25519 hors ligne."

    def add_arguments(self, parser):
        parser.add_argument("license_file", help="Fichier JSON signé fourni par l'éditeur.")
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Active la licence après import ; sinon elle reste en attente.",
        )

    def handle(self, *args, **options):
        path = Path(options["license_file"]).expanduser()
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CommandError(f"Fichier de licence illisible ou JSON invalide : {exc}") from exc

        if (
            document.get("format") != "yelen-school-license"
            or document.get("format_version") != 1
            or document.get("signature_algorithm") != "Ed25519"
        ):
            raise CommandError("Format de licence inconnu ou non supporté.")

        payload = document.get("payload")
        signature = document.get("signature")
        if not isinstance(payload, dict) or not isinstance(signature, str):
            raise CommandError("Payload ou signature manquant.")
        if not verify_signed_payload(payload, signature):
            raise CommandError(
                "Signature Ed25519 invalide. Le fichier est refusé et aucune donnée n'a été modifiée."
            )

        self._validate_payload(payload)
        try:
            expiration = date.fromisoformat(payload["date_expiration"])
        except ValueError as exc:  # Défense supplémentaire après _validate_payload.
            raise CommandError("Date d'expiration invalide.") from exc
        if expiration < date.today():
            raise CommandError("La licence fournie est déjà expirée.")

        try:
            etablissement = Etablissement.objects.get(pk=payload["etablissement_id"])
        except Etablissement.DoesNotExist as exc:
            raise CommandError(
                "L'établissement indiqué par la licence n'existe pas dans cette installation."
            ) from exc

        with transaction.atomic():
            licence = (
                Licence.objects.select_for_update()
                .filter(etablissement=etablissement)
                .first()
            )
            duplicate = Licence.objects.filter(cle_licence=payload["license_id"])
            if licence is not None:
                duplicate = duplicate.exclude(pk=licence.pk)
            if duplicate.exists():
                raise CommandError("Cet identifiant de licence est déjà associé à un autre établissement.")

            if licence is None:
                licence = Licence(
                    etablissement=etablissement,
                    cle_licence=payload["license_id"],
                )
            elif licence.utilise_signature_forte and licence.cle_licence != payload["license_id"]:
                raise CommandError(
                    "Une autre licence signée est déjà installée pour cet établissement. "
                    "Passez par une procédure de remplacement contrôlée."
                )

            licence.cle_licence = payload["license_id"]
            licence.type_licence = payload["type_licence"]
            licence.date_expiration = expiration
            licence.signature_ed25519 = signature
            licence.signed_payload = payload
            licence.statut = (
                StatutLicence.ACTIVE if options["activate"] else StatutLicence.EN_ATTENTE
            )
            if options["activate"] and not licence.date_activation:
                licence.date_activation = timezone.now()
            licence.save()
            if options["activate"] and not licence.est_active():
                raise CommandError(
                    "La licence a été enregistrée mais n'est pas active après validation."
                )

        status = "active" if options["activate"] else "en attente d'activation"
        self.stdout.write(
            self.style.SUCCESS(
                f"Licence {payload['license_id']} importée pour {etablissement.nom} ({status})."
            )
        )

    @staticmethod
    def _validate_payload(payload: dict) -> None:
        required = {
            "schema",
            "license_id",
            "etablissement_id",
            "type_licence",
            "date_expiration",
            "limits",
            "features",
            "server_fingerprint",
            "issued_at",
            "nonce",
        }
        missing = sorted(required.difference(payload))
        if missing:
            raise CommandError(f"Payload incomplet : {', '.join(missing)}.")
        if payload["schema"] != 1:
            raise CommandError("Version de payload non supportée.")
        if payload["type_licence"] not in {choice.value for choice in TypeLicence}:
            raise CommandError("Type de licence inconnu.")
        if not isinstance(payload["limits"], dict) or not isinstance(payload["features"], list):
            raise CommandError("Limites ou fonctionnalités invalides.")
        if not isinstance(payload["server_fingerprint"], str):
            raise CommandError("Empreinte serveur invalide.")
        if not isinstance(payload["nonce"], str) or len(payload["nonce"]) < 16:
            raise CommandError("Nonce de licence absent ou trop court.")
        license_id = payload["license_id"]
        parts = license_id.split("-") if isinstance(license_id, str) else []
        if len(parts) != 4 or parts[0] != "YELEN" or any(len(part) != 4 for part in parts[1:]):
            raise CommandError("Identifiant de licence invalide.")
