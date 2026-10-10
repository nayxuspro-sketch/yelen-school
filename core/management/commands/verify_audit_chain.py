from django.core.management.base import BaseCommand, CommandError

from core.audit import verify_audit_chain


class Command(BaseCommand):
    help = "Vérifie l'intégrité de la chaîne append-only du journal d'audit."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None)

    def handle(self, *args, **options):
        result = verify_audit_chain(options.get('limit'))
        legacy = result.get('legacy', 0)
        if not result['ok']:
            raise CommandError(
                f"Chaîne d'audit invalide ({len(result['invalid'])} entrée(s)): "
                + ', '.join(result['invalid'])
            )
        chained = result['checked'] - legacy
        message = f"Chaîne d'audit valide : {chained} entrée(s) chaînée(s) vérifiée(s)."
        if legacy:
            message += (
                f" {legacy} entrée(s) antérieure(s) au chaînage (avant la migration core.0004)"
                " conservée(s) sans garantie cryptographique."
            )
        self.stdout.write(self.style.SUCCESS(message))
