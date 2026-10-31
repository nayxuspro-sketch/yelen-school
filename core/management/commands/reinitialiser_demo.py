"""Reconstruit le jeu de démonstration d'une instance d'essai (offre hébergée, chantier B8).

    python manage.py reinitialiser_demo

Vide **toutes** les tables puis recharge l'établissement de démonstration (``charger_demo``) : c'est la
réinitialisation nocturne d'une instance publique, où les visiteurs créent, modifient et suppriment sans
conséquence. La commande refuse de s'exécuter hors mode démonstration : sur une école, elle effacerait les
données réelles.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Vide la base et recharge le jeu de démonstration (réservé à DEMO_MODE=true)."

    def add_arguments(self, parser):
        parser.add_argument('--eleves', type=int, default=48, help="Nombre d'élèves du jeu (48).")
        parser.add_argument('--etablissement', default='DEMO', help="Code de l'établissement (DEMO).")
        parser.add_argument('--sans-vidage', action='store_true',
                            help="Recharge le jeu sans vider la base (base déjà vide, premier démarrage).")

    def handle(self, *args, **options):
        from core import mode_demo

        if not mode_demo.actif():
            raise CommandError(
                "reinitialiser_demo est réservée aux instances de démonstration (DEMO_MODE=true) : "
                "sur une école, elle effacerait les données réelles."
            )

        etablissement = options['etablissement'].upper()
        if not options['sans_vidage']:
            with transaction.atomic():
                call_command('flush', interactive=False, verbosity=0)
            self.stdout.write("Base vidée.")

        call_command('charger_demo', '--etablissement', etablissement, '--eleves', str(options['eleves']),
                     verbosity=0)
        self.stdout.write(self.style.SUCCESS(f"Démonstration reconstruite : {etablissement}."))
