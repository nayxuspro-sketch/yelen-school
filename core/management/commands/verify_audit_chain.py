from django.core.management.base import BaseCommand, CommandError

from core.audit import verify_audit_chain


class Command(BaseCommand):
    help = "Vérifie l'intégrité de la chaîne append-only du journal d'audit."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None)

    def handle(self, *args, **options):
        result = verify_audit_chain(options.get('limit'))
        if not result['ok']:
            raise CommandError(
                f"Chaîne d'audit invalide ({len(result['invalid'])} entrée(s)): "
                + ', '.join(result['invalid'])
            )
        self.stdout.write(self.style.SUCCESS(
            f"Chaîne d'audit valide : {result['checked']} entrée(s) vérifiée(s)."
        ))
