"""Reconstruit le jeu de démonstration d'une instance d'essai (offre hébergée, chantier B8).

    python manage.py reinitialiser_demo

Supprime l'établissement de démonstration et le recharge (``charger_demo --reset``) : c'est la remise à zéro
d'une instance publique, où les visiteurs créent, modifient et suppriment sans conséquence. La commande
refuse de s'exécuter hors mode démonstration : sur une école, elle effacerait les données réelles.

L'instance de démonstration tourne sur SQLite (comme une installation d'école autonome) : sous PostgreSQL,
un paiement comptabilisé est immuable et la suppression est refusée, avec la marche à suivre.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Recharge le jeu de démonstration (réservé à DEMO_MODE=true, base SQLite)."

    def add_arguments(self, parser):
        parser.add_argument('--eleves', type=int, default=48, help="Nombre d'élèves du jeu (48).")
        parser.add_argument('--etablissement', default='DEMO', help="Code de l'établissement (DEMO).")

    def handle(self, *args, **options):
        from core import mode_demo

        if not mode_demo.actif():
            raise CommandError(
                "reinitialiser_demo est réservée aux instances de démonstration (DEMO_MODE=true) : "
                "sur une école, elle effacerait les données réelles."
            )

        call_command('charger_demo', '--etablissement', options['etablissement'],
                     '--eleves', str(options['eleves']), '--reset', verbosity=0)
        # Traces laissées par les visiteurs en dehors de l'établissement (élève créé puis abandonné avant son
        # inscription) : la démonstration ne doit rien conserver d'une session à l'autre.
        from inscriptions.models import Eleve
        Eleve.objects.filter(inscriptions__isnull=True).delete()
        self.stdout.write(self.style.SUCCESS(
            f"Démonstration reconstruite : {options['etablissement'].upper()}."))
