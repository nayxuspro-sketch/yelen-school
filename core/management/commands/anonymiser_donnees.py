"""Anonymise les élèves sortis depuis plus de N années (politique de chaque établissement)."""
from django.core.management.base import BaseCommand

from core import donnees_personnelles as dp
from etablissements.models import Etablissement


class Command(BaseCommand):
    help = "Anonymise les données personnelles des élèves dont la conservation a expiré (--dry-run pour compter seulement)."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help="Afficher le nombre d'élèves concernés sans rien modifier")

    def handle(self, *args, **options):
        for etab in Etablissement.objects.all():
            politique = dp.politique_de(etab)
            nb = dp.eleves_a_anonymiser(etab, politique.duree_conservation_annees).count()
            if options['dry_run']:
                self.stdout.write(f"{etab} : {nb} élève(s) à anonymiser (conservation {politique.duree_conservation_annees} ans)")
                continue
            bilan = dp.anonymiser(etab) if nb else {'eleves': 0, 'comptes': 0, 'fichiers': 0, 'preinscriptions': 0}
            self.stdout.write(
                f"{etab} : {bilan['eleves']} élève(s) anonymisé(s), {bilan['comptes']} compte(s) fermé(s), "
                f"{bilan['fichiers']} fichier(s) supprimé(s), {bilan['preinscriptions']} pré-inscription(s) effacée(s)"
            )
