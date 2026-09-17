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
            help="Quitte avec le code 1 si une anomalie est détectée (utile pour les healthchecks). En mode LICENCE_ANTITAMPER_ENABLED+LICENSE_ENFORCEMENT, arrête l'app.",
        )
        parser.add_argument(
            '--json',
            action='store_true',
            default=False,
            help="Affiche le résultat en JSON (pour les scripts automatisés).",
        )
        parser.add_argument(
            '--heartbeat',
            action='store_true',
            default=False,
            help="Envoie aussi les heartbeats aux licences actives (si LICENCE_HEARTBEAT_URL configuré).",
        )

    def handle(self, *args, **options):
        # P1 : en mode --strict, on passe strict=True à run_boot_check pour que
        # l'anti-tamper lève RuntimeError si critique
        try:
            result = run_boot_check(strict=options['strict'])
        except RuntimeError as exc:
            # Anti-tamper strict → arrêt app
            self.stderr.write(self.style.ERROR(f"[CRITIQUE] {exc}"))
            if options['json']:
                import json
                self.stdout.write(json.dumps({'ok': False, 'critical': str(exc)}, indent=2, default=str))
            sys.exit(1)

        heartbeat_result = None
        if options['heartbeat']:
            try:
                from licences.heartbeat import check_all_heartbeats
                heartbeat_result = check_all_heartbeats()
                result['heartbeat'] = heartbeat_result
                if heartbeat_result['bail_expired'] or heartbeat_result['revoked']:
                    result['ok'] = False
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f"Erreur heartbeat : {exc}"))
                result['errors'].append(f"HEARTBEAT: {exc}")

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

        if result.get('bail_expired'):
            self.stdout.write(style_err(
                f"  Bail offline expires : {len(result['bail_expired'])}"
            ))
            for cle in result['bail_expired']:
                self.stdout.write(style_err(f"    [X] BAIL EXPIRE - {cle}"))
        else:
            self.stdout.write(style_ok("  Bail offline expires : 0"))

        if result.get('binding_invalid'):
            self.stdout.write(style_err(
                f"  Binding invalides    : {len(result['binding_invalid'])}"
            ))
            for cle in result['binding_invalid']:
                self.stdout.write(style_err(f"    [X] BINDING - {cle}"))
        else:
            self.stdout.write(style_ok("  Binding invalides    : 0"))

        if not result.get('antitamper', {}).get('ok', True):
            self.stdout.write(style_err("  Anti-tamper          : ECHEC"))
            for issue in result['antitamper']['issues']:
                self.stdout.write(style_err(f"    [X] {issue}"))
        else:
            self.stdout.write(style_ok("  Anti-tamper          : OK"))

        if result['errors']:
            self.stdout.write(style_warn(
                f"  Erreurs techniques   : {len(result['errors'])}"
            ))
            for err in result['errors']:
                self.stdout.write(style_warn(f"    ! {err}"))

        if heartbeat_result:
            self.stdout.write(self.style.HTTP_INFO("  --- Heartbeat ---"))
            self.stdout.write(f"  Heartbeats envoyes   : {heartbeat_result['sent']}/{heartbeat_result['total']}")
            self.stdout.write(style_ok(f"  Succes               : {heartbeat_result['success']}"))
            if heartbeat_result['failures']:
                self.stdout.write(style_warn(f"  Echecs               : {heartbeat_result['failures']}"))
            if heartbeat_result['revoked']:
                self.stdout.write(style_err(f"  Revoques distants    : {heartbeat_result['revoked']}"))
            if heartbeat_result['bail_expired']:
                self.stdout.write(style_err(f"  Bail expires         : {len(heartbeat_result['bail_expired'])}"))

        self.stdout.write(self.style.HTTP_INFO("=" * 52))

        if result['ok']:
            self.stdout.write(style_ok("  [OK] Toutes les licences sont saines."))
        else:
            self.stdout.write(style_err("  [X] Des anomalies ont ete detectees et corrigees."))

        self.stdout.write(self.style.HTTP_INFO("=" * 52))
        self.stdout.write("")

        if options['strict'] and not result['ok']:
            sys.exit(1)
