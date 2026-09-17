"""
Commande : generate_licence_keys
===============================
Génère une paire de clés Ed25519 pour signer les licences (côté éditeur).

Usage :
    python manage.py generate_licence_keys
    python manage.py generate_licence_keys --format env

La clé privée ne doit JAMAIS être déployée en prod école — seulement chez l'éditeur.
La clé publique doit être dans LICENCE_PUBLIC_KEY en prod.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère une paire de clés Ed25519 pour la signature des licences (P1)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['env', 'json', 'raw'],
            default='env',
            help="Format de sortie : env (défaut, prêt à copier dans .env), json, raw",
        )

    def handle(self, *args, **options):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        except ImportError:
            self.stderr.write(self.style.ERROR(
                "cryptography n'est pas installé. Installez-le : pip install cryptography"
            ))
            return

        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key()

        priv_raw = priv.private_bytes_raw()
        pub_raw = pub.public_bytes_raw()

        priv_hex = priv_raw.hex()
        pub_hex = pub_raw.hex()

        import base64
        priv_b64 = base64.b64encode(priv_raw).decode('ascii')
        pub_b64 = base64.b64encode(pub_raw).decode('ascii')

        fmt = options['format']

        if fmt == 'json':
            import json
            self.stdout.write(json.dumps({
                'private_key_hex': priv_hex,
                'public_key_hex': pub_hex,
                'private_key_b64': priv_b64,
                'public_key_b64': pub_b64,
            }, indent=2))
        elif fmt == 'raw':
            self.stdout.write(f"Private (hex): {priv_hex}")
            self.stdout.write(f"Public  (hex): {pub_hex}")
            self.stdout.write(f"Private (b64): {priv_b64}")
            self.stdout.write(f"Public  (b64): {pub_b64}")
        else:  # env
            self.stdout.write(self.style.HTTP_INFO("# ── Clés Ed25519 licences P1 ──"))
            self.stdout.write(self.style.WARNING("# ⚠️  PRIVATE KEY : garder chez éditeur uniquement, JAMAIS en prod école !"))
            self.stdout.write(f"LICENCE_PRIVATE_KEY={priv_hex}")
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("# ✅ PUBLIC KEY : à mettre dans .env prod école"))
            self.stdout.write(f"LICENCE_PUBLIC_KEY={pub_hex}")
            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO("# Alternative base64 (si besoin) :"))
            self.stdout.write(f"# LICENCE_PRIVATE_KEY_B64={priv_b64}")
            self.stdout.write(f"# LICENCE_PUBLIC_KEY_B64={pub_b64}")
            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO("# ── Clé HMAC dédiée (optionnelle, mais recommandée) ──"))
            import secrets
            hmac_key = secrets.token_hex(32)
            self.stdout.write(f"LICENCE_SIGNING_KEY={hmac_key}")
