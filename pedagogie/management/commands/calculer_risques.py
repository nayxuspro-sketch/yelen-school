"""
Management command : calculer_risques
======================================
Recalcule les scores de risque de décrochage pour tous les élèves actifs
de l'année scolaire courante (ou d'une année spécifiée).

Usage :
    python manage.py calculer_risques
    python manage.py calculer_risques --annee <uuid>
    python manage.py calculer_risques --classe <uuid>
    python manage.py calculer_risques --verbeux

À planifier en cron (ex : chaque nuit à 02h00) :
    0 2 * * * /path/to/venv/bin/python manage.py calculer_risques
"""
from django.core.management.base import BaseCommand

from inscriptions.models import Inscription
from parametres.models import AnneeScolaire
from pedagogie.models import RisqueDecrochage
from pedagogie.utils_ia import calculer_score_risque


class Command(BaseCommand):
    help = "Calcule les scores de risque de décrochage scolaire pour tous les élèves actifs."

    def add_arguments(self, parser):
        parser.add_argument(
            '--annee', type=str, default=None,
            help="UUID de l'année scolaire (défaut : année courante)"
        )
        parser.add_argument(
            '--classe', type=str, default=None,
            help="UUID d'une classe spécifique (optionnel)"
        )
        parser.add_argument(
            '--verbeux', action='store_true',
            help="Affiche le détail de chaque élève traité"
        )

    def handle(self, *args, **options):
        # ── Résoudre l'année scolaire ──────────────────────────────
        annee_id = options.get('annee')
        if annee_id:
            try:
                annee = AnneeScolaire.objects.get(pk=annee_id)
            except AnneeScolaire.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Année scolaire introuvable : {annee_id}"))
                return
        else:
            annee = AnneeScolaire.objects.filter(est_courante=True).first()
            if not annee:
                self.stderr.write(self.style.ERROR("Aucune année scolaire courante définie."))
                return

        self.stdout.write(f"Année scolaire : {annee.libelle}")

        # ── Construire le queryset des inscriptions ────────────────
        qs = (
            Inscription.objects
            .filter(annee_scolaire=annee)
            .exclude(statut='ABANDON')
            .select_related('eleve', 'classe')
        )
        if options.get('classe'):
            qs = qs.filter(classe_id=options['classe'])

        total = qs.count()
        self.stdout.write(f"{total} inscription(s) à traiter…")

        # ── Calcul des scores ──────────────────────────────────────
        created = updated = erreurs = 0

        for inscription in qs.iterator(chunk_size=100):
            try:
                score, facteurs = calculer_score_risque(inscription, annee)
                niveau = RisqueDecrochage.niveau_pour_score(score)

                risque, is_new = RisqueDecrochage.objects.update_or_create(
                    inscription=inscription,
                    defaults={
                        'score': score,
                        'niveau': niveau,
                        'facteurs': facteurs,
                    }
                )
                if is_new:
                    created += 1
                else:
                    updated += 1

                if options['verbeux']:
                    couleur = {
                        'FAIBLE': self.style.SUCCESS,
                        'MODERE': self.style.WARNING,
                        'ELEVE': self.style.WARNING,
                        'CRITIQUE': self.style.ERROR,
                    }.get(niveau, str)
                    self.stdout.write(
                        f"  {inscription.eleve} [{inscription.classe}] "
                        + couleur(f"-> {niveau} ({score}/100)")
                    )

            except Exception as e:
                erreurs += 1
                self.stderr.write(
                    self.style.ERROR(f"  Erreur pour {inscription.eleve} : {e}")
                )

        # ── Résumé ─────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé — {created} créé(s), {updated} mis à jour, {erreurs} erreur(s)."
        ))
        if erreurs == 0:
            self.stdout.write(self.style.SUCCESS("Aucune erreur."))
