"""
Management command : auto_generer_annee_scolaire
==================================================
YELEN SCHOOL — Génération automatique de la nouvelle année scolaire.

À partir du 5 juillet, crée l'année scolaire ``YYYY-YYYY+1``
pour chaque établissement et bascule automatiquement dessus.

Usage :
    python manage.py auto_generer_annee_scolaire
    python manage.py auto_generer_annee_scolaire --force   (ignorer la date)
    python manage.py auto_generer_annee_scolaire --dry-run (simulation)

Cron recommandé (quotidien à 02h00) :
    0 2 * * * /path/to/venv/bin/python manage.py auto_generer_annee_scolaire
"""

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Génère automatiquement la nouvelle année scolaire "
        "à partir du 5 juillet et bascule le système dessus."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help="Forcer la création même avant le 5 juillet",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Simuler sans créer ni modifier",
        )

    def handle(self, *args, **options):
        from parametres.services import auto_generer_annee_scolaire

        force = options.get('force', False)
        dry_run = options.get('dry_run', False)

        if dry_run:
            from datetime import date
            from django.utils import timezone
            from etablissements.models import Etablissement
            from parametres.models import AnneeScolaire

            today = timezone.now().date()
            an = today.year

            if not force and (today.month < 7 or (today.month == 7 and today.day < 5)):
                self.stdout.write(
                    self.style.WARNING(
                        "Avant le 5 juillet — aucune année à générer. "
                        "Utilisez --force pour forcer."
                    )
                )
                return

            libelle = f"{an}-{an + 1}"
            self.stdout.write(f"--- Simulation ---")
            self.stdout.write(f"Date         : {today}")
            self.stdout.write(f"Libellé      : {libelle}")
            self.stdout.write(f"Date début   : {an}-10-01")
            self.stdout.write(f"Date fin     : {an + 1}-06-30")

            for etab in Etablissement.objects.filter(is_active=True):
                existe = AnneeScolaire.objects.filter(
                    etablissement=etab, libelle=libelle
                ).exists()
                statut = "DÉJÀ EXISTANTE" if existe else "SERAIT CRÉÉE"
                self.stdout.write(f"  [{statut}] {etab.nom} ({etab.code})")
            return

        created = auto_generer_annee_scolaire(force=force)

        if not created:
            self.stdout.write(
                self.style.WARNING(
                    "Aucune nouvelle année scolaire à générer."
                )
            )
            return

        for annee in created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Année {annee.libelle} créée et activée "
                    f"pour {annee.etablissement.nom}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(created)} année(s) scolaire(s) générée(s)."
            )
        )
