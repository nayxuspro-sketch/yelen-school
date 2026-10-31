"""Fige les indicateurs de chaque année scolaire (effectifs, résultats, recouvrement, assiduité) — depuis 5.39.0."""
from django.core.management.base import BaseCommand

from core import indicateurs
from etablissements.models import Etablissement


class Command(BaseCommand):
    help = "Calcule et enregistre les indicateurs annuels de chaque établissement (à lancer en fin d'année)."

    def add_arguments(self, parser):
        parser.add_argument('--etablissement', help="Identifiant (UUID) d'un seul établissement")

    def handle(self, *args, **options):
        etabs = Etablissement.objects.all()
        if options['etablissement']:
            etabs = etabs.filter(pk=options['etablissement'])
        for etab in etabs:
            lignes = indicateurs.mettre_a_jour(etab)
            self.stdout.write(f"{etab} : {len(lignes)} année(s) d'indicateurs enregistrée(s)")
