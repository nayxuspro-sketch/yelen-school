"""
Commande de gestion : check_licences
=====================================
Vérifie l'intégrité de toutes les licences et affiche un rapport.

Usage :
    python manage.py check_licences
    python manage.py check_licences --strict   # Exit code 1 si anomalie

Exemples d'utilisation :
    # Dans un Docker healthcheck
    HEALTHCHECK CMD python manage.py check_licences --strict || exit 1

    # Dans un script de déploiement
    python manage.py check_licences && echo "Licences OK"

    # En cron (toutes les heures)
    0 * * * * cd /app && python manage.py check_licences >> /var/log/licences.log 2>&1
"""

import sys

from django.core.management.base import BaseCommand

from licences.boot_check import run_boot_check


class Command(BaseCommand):
    help = "Vérifie l'intégrité cryptographique et la validité de toutes les licences."

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            default=False,
            help="Quitte avec le code 1 si une anomalie est détectée (utile pour les healthchecks).",
        )
        parser.add_argument(
            '--json',
            action='store_true',
            default=False,
            help="Affiche le résultat en JSON (pour les scripts automatisés).",
        )

    def handle(self, *args, **options):
        result = run_boot_check()

        if options['json']:
            import json
            self.stdout.write(json.dumps(result, indent=2, default=str))
            if options['strict'] and not result['ok']:
                sys.exit(1)
            return

        # ── Affichage lisible ─────────────────────────────────────────────
        style_ok = self.style.SUCCESS
        style_err = self.style.ERROR
        style_warn = self.style.WARNING

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("=" * 52))
        self.stdout.write(self.style.HTTP_INFO("  YELEN SCHOOL - Verification des licences"))
        self.stdout.write(self.style.HTTP_INFO("=" * 52))
        self.stdout.write(f"  Licences controlees  : {result['total']}")
        self.stdout.write(style_ok(f"  Valides              : {result['valides']}"))

        if result['tampering']:
            self.stdout.write(style_err(
                f"  Signatures invalides : {len(result['tampering'])}"
            ))
            for cle in result['tampering']:
                self.stdout.write(style_err(f"    [X] TAMPERING - {cle}"))
        else:
            self.stdout.write(style_ok("  Signatures invalides : 0"))

        if result['expirees']:
            self.stdout.write(style_warn(
                f"  Expirees corrigees   : {len(result['expirees'])}"
            ))
            for cle in result['expirees']:
                self.stdout.write(style_warn(f"    [!] EXPIREE - {cle}"))
        else:
            self.stdout.write(style_ok("  Expirees corrigees   : 0"))

        if result['errors']:
            self.stdout.write(style_warn(
                f"  Erreurs techniques   : {len(result['errors'])}"
            ))
            for err in result['errors']:
                self.stdout.write(style_warn(f"    ! {err}"))

        self.stdout.write(self.style.HTTP_INFO("=" * 52))

        if result['ok']:
            self.stdout.write(style_ok("  [OK] Toutes les licences sont saines."))
        else:
            self.stdout.write(style_err("  [X] Des anomalies ont ete detectees et corrigees."))

        self.stdout.write(self.style.HTTP_INFO("=" * 52))
        self.stdout.write("")

        if options['strict'] and not result['ok']:
            sys.exit(1)
