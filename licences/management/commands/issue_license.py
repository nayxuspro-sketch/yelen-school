"""Émet un fichier de licence Ed25519 hors ligne."""

from __future__ import annotations

import json
import os
import secrets
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from licences.crypto import LicenseCryptoError, sign_payload
from licences.fingerprint import is_valid_server_fingerprint
from licences.models import FEATURE_FLAGS, LIMITES_LICENCES, TypeLicence


class Command(BaseCommand):
    help = "Émet un document de licence hors ligne signé par la clé fournisseur."

    def add_arguments(self, parser):
        parser.add_argument("--etablissement-id", required=True, help="UUID de l'établissement.")
        parser.add_argument(
            "--type",
            dest="type_licence",
            choices=[choice.value for choice in TypeLicence],
            required=True,
        )
        parser.add_argument(
            "--expires",
            required=True,
            help="Date d'expiration ISO, par exemple 2027-09-16.",
        )
        parser.add_argument(
            "--private-key",
            required=True,
            help="Fichier PEM privé fournisseur chiffré.",
        )
        parser.add_argument(
            "--password-env",
            default="YELEN_LICENSE_PRIVATE_KEY_PASSWORD",
            help="Variable d'environnement du mot de passe PEM.",
        )
        parser.add_argument("--output", required=True, help="Fichier JSON de licence à livrer.")
        parser.add_argument(
            "--server-fingerprint",
            default="",
            help="Empreinte SHA-256 hexadécimale du serveur client (obligatoire pour l'activation).",
        )
        parser.add_argument(
            "--license-id",
            default="",
            help="Identifiant YELEN-XXXX-XXXX-XXXX ; généré s'il est omis.",
        )

    def handle(self, *args, **options):
        try:
            expiration = date.fromisoformat(options["expires"])
        except ValueError as exc:
            raise CommandError("--expires doit être une date ISO YYYY-MM-DD.") from exc
        if expiration <= date.today():
            raise CommandError("La date d'expiration doit être dans le futur.")

        license_id = options["license_id"].strip().upper() or self._new_license_id()
        if not self._valid_license_id(license_id):
            raise CommandError("Identifiant invalide : attendu YELEN-XXXX-XXXX-XXXX.")

        private_path = Path(options["private_key"]).expanduser()
        try:
            private_key = private_path.read_bytes()
        except OSError as exc:
            raise CommandError(f"Impossible de lire la clé privée : {exc}") from exc

        password = os.environ.get(options["password_env"], "")
        if not password:
            raise CommandError(
                f"Définissez {options['password_env']} pour déchiffrer la clé privée."
            )

        server_fingerprint = options["server_fingerprint"].strip().lower()
        if not is_valid_server_fingerprint(server_fingerprint):
            raise CommandError(
                "--server-fingerprint doit être une empreinte SHA-256 hexadécimale de 64 caractères."
            )

        type_licence = options["type_licence"]
        payload = {
            "schema": 1,
            "license_id": license_id,
            "etablissement_id": options["etablissement_id"].strip(),
            "type_licence": type_licence,
            "date_expiration": expiration.isoformat(),
            "limits": dict(LIMITES_LICENCES[type_licence]),
            "features": sorted(
                feature for feature, levels in FEATURE_FLAGS.items() if type_licence in levels
            ),
            "server_fingerprint": server_fingerprint,
            "issued_at": timezone.now().replace(microsecond=0).isoformat(),
            "nonce": secrets.token_urlsafe(18),
        }

        try:
            signature = sign_payload(
                payload,
                private_key,
                password=password.encode("utf-8"),
            )
        except LicenseCryptoError as exc:
            raise CommandError(str(exc)) from exc

        document = {
            "format": "yelen-school-license",
            "format_version": 1,
            "signature_algorithm": "Ed25519",
            "payload": payload,
            "signature": signature,
        }
        output = Path(options["output"]).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.stdout.write(self.style.SUCCESS(f"Licence signée écrite dans {output}"))
        self.stdout.write(f"Identifiant : {license_id}")

    @staticmethod
    def _new_license_id() -> str:
        token = secrets.token_hex(6).upper()
        return f"YELEN-{token[:4]}-{token[4:8]}-{token[8:12]}"

    @staticmethod
    def _valid_license_id(value: str) -> bool:
        parts = value.split("-")
        return len(parts) == 4 and parts[0] == "YELEN" and all(
            len(part) == 4 and all(char in "0123456789ABCDEF" for char in part)
            for part in parts[1:]
        )
