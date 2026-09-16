"""Génère la paire de clés Ed25519 du fournisseur.

Cette commande est un outil d'émission, pas une opération à exécuter sur un
serveur client. La clé privée doit rester dans un coffre ou un poste fournisseur
isolé et ne doit jamais être copiée dans l'installation YELEN SCHOOL.
"""

from __future__ import annotations

import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from licences.crypto import LicenseCryptoError, generate_key_pair


class Command(BaseCommand):
    help = "Génère une paire de clés Ed25519 pour la signature des licences."

    def add_arguments(self, parser):
        parser.add_argument(
            "--private-output",
            required=True,
            help="Chemin du fichier PEM privé chiffré (hors dépôt et hors client).",
        )
        parser.add_argument(
            "--public-output",
            required=True,
            help="Chemin du fichier texte contenant la clé publique Base64.",
        )
        parser.add_argument(
            "--password-env",
            default="YELEN_LICENSE_PRIVATE_KEY_PASSWORD",
            help="Variable d'environnement contenant le mot de passe de la clé privée.",
        )

    def handle(self, *args, **options):
        password = os.environ.get(options["password_env"], "")
        if not password:
            raise CommandError(
                f"Définissez {options['password_env']} avant de générer une clé privée."
            )

        private_path = Path(options["private_output"]).expanduser()
        public_path = Path(options["public_output"]).expanduser()
        if private_path.exists() or public_path.exists():
            raise CommandError("Refus : un fichier de sortie existe déjà.")

        try:
            private_pem, public_b64 = generate_key_pair(password.encode("utf-8"))
        except LicenseCryptoError as exc:
            raise CommandError(str(exc)) from exc

        private_path.parent.mkdir(parents=True, exist_ok=True)
        public_path.parent.mkdir(parents=True, exist_ok=True)
        private_path.write_bytes(private_pem)
        public_path.write_text(public_b64 + "\n", encoding="ascii")
        try:
            os.chmod(private_path, 0o600)
        except OSError:
            # Les ACL Windows doivent être posées par le script d'installation
            # fournisseur ; l'absence de chmod Unix n'invalide pas la génération.
            pass

        self.stdout.write(self.style.SUCCESS("Paire Ed25519 générée."))
        self.stdout.write(f"Clé publique : {public_path}")
        self.stdout.write(
            "IMPORTANT : intégrer uniquement la clé publique dans "
            "licences/embedded_key.py avant le build."
        )
        self.stdout.write(f"Clé privée : {private_path} — NE PAS DISTRIBUER")
