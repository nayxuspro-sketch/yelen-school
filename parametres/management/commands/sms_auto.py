"""
management command : sms_auto
=================================
YELEN SCHOOL — Envoi des SMS automatiques planifiés.

Usage :
    python manage.py sms_auto
    python manage.py sms_auto --type ABSENCE_J1
    python manage.py sms_auto --type ECHEANCIER
    python manage.py sms_auto --type RESULTATS
    python manage.py sms_auto --dry-run

Cron recommandé (Windows Task Scheduler ou Linux cron) :
    0 7 * * * /path/to/venv/bin/python manage.py sms_auto
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Envoie les SMS automatiques planifiés (absences, échéanciers, résultats)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['ABSENCE_J1', 'ECHEANCIER', 'RESULTATS'],
            help="Exécuter uniquement ce type de déclencheur",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Simuler sans envoyer de SMS",
        )

    def handle(self, *args, **options):
        from django.conf import settings
        if not getattr(settings, 'SMS_ENABLED', False):
            self.stdout.write(self.style.WARNING("SMS_ENABLED=False — aucun SMS envoyé."))
            return

        from parametres.models import DeclencheurSMS
        filtre_type = options.get('type')
        dry_run = options.get('dry_run', False)

        qs = DeclencheurSMS.objects.filter(actif=True).select_related('etablissement')
        if filtre_type:
            qs = qs.filter(type_declencheur=filtre_type)

        total = 0
        for declencheur in qs:
            nb = self._run_declencheur(declencheur, dry_run)
            total += nb
            if nb > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"[{declencheur.get_type_declencheur_display()}] {nb} SMS {'(simulé)' if dry_run else 'envoyé(s)'}")
                )

        self.stdout.write(self.style.SUCCESS(f"Total : {total} SMS {'simulés' if dry_run else 'envoyés'}."))

    def _run_declencheur(self, declencheur, dry_run):
        t = declencheur.type_declencheur
        etab = declencheur.etablissement
        nb = 0

        if t == 'ABSENCE_J1':
            nb = self._absence_j1(declencheur, etab, dry_run)
        elif t == 'ECHEANCIER':
            nb = self._echeancier_rappel(declencheur, etab, dry_run)
        elif t == 'RESULTATS':
            nb = self._resultats_dispo(declencheur, etab, dry_run)

        if not dry_run and nb > 0:
            declencheur.last_run = timezone.now()
            declencheur.nb_envoyes_total = (declencheur.nb_envoyes_total or 0) + nb
            declencheur.save(update_fields=['last_run', 'nb_envoyes_total'])

        return nb

    # ── ABSENCE J+1 ────────────────────────────────────────────────

    def _absence_j1(self, declencheur, etab, dry_run):
        from presences.models import Absence
        hier = timezone.now().date() - timedelta(days=1)

        absences = (
            Absence.objects
            .filter(
                inscription__classe__etablissement=etab,
                date=hier,
                justifie=False,
            )
            .select_related('inscription__eleve', 'inscription__classe')
        )

        etab_nom = etab.nom
        nb = 0
        for absence in absences:
            eleve = absence.inscription.eleve
            numero = (
                eleve.telephone_parent
                or eleve.tuteur_telephone
                or eleve.telephone_urgence
                or ''
            ).strip()
            if not numero:
                continue

            from parametres.models import ModeleMessage
            msg = ModeleMessage.get_contenu(etab, 'ABSENCE', {
                'nom_eleve': eleve.get_nom_complet(),
                'date': hier.strftime('%d/%m/%Y'),
                'matiere': '',
                'etablissement': etab_nom,
            })

            if not dry_run:
                from core.tasks import envoyer_sms_async
                envoyer_sms_async(numero, msg)
            nb += 1
            logger.info(f"SMS absence → {numero} ({eleve})")

        return nb

    # ── RAPPEL ÉCHÉANCIER ──────────────────────────────────────────

    def _echeancier_rappel(self, declencheur, etab, dry_run):
        from finances.models import Echeancier
        today = timezone.now().date()
        seuil = today + timedelta(days=declencheur.jours_avant)

        echeances = (
            Echeancier.objects
            .filter(
                inscription__classe__etablissement=etab,
                paye=False,
                date_limite__lte=seuil,
                date_limite__gte=today,
            )
            .select_related('inscription__eleve')
        )

        etab_nom = etab.nom
        nb = 0
        for ech in echeances:
            eleve = ech.inscription.eleve
            numero = (
                eleve.telephone_parent
                or eleve.tuteur_telephone
                or eleve.telephone_urgence
                or ''
            ).strip()
            if not numero:
                continue

            from parametres.models import ModeleMessage
            msg = ModeleMessage.get_contenu(etab, 'PAIEMENT', {
                'nom_eleve': eleve.get_nom_complet(),
                'rubrique': ech.libelle,
                'montant': f"{int(ech.montant_du):,}",
                'etablissement': etab_nom,
            })

            if not dry_run:
                from core.tasks import envoyer_sms_async
                envoyer_sms_async(numero, msg)
            nb += 1
            logger.info(f"SMS échéancier → {numero} ({eleve}, {ech.date_limite})")

        return nb

    # ── BULLETINS DISPONIBLES ──────────────────────────────────────

    def _resultats_dispo(self, declencheur, etab, dry_run):
        from bulletins.models import Bulletin
        last_run = declencheur.last_run or (timezone.now() - timedelta(hours=25))

        bulletins = (
            Bulletin.objects
            .filter(
                inscription__classe__etablissement=etab,
                est_publie=True,
                date_publication__gte=last_run,
            )
            .select_related('inscription__eleve', 'trimestre')
        )

        etab_nom = etab.nom
        nb = 0
        for bulletin in bulletins:
            eleve = bulletin.inscription.eleve
            numero = (
                eleve.telephone_parent
                or eleve.tuteur_telephone
                or eleve.telephone_urgence
                or ''
            ).strip()
            if not numero:
                continue

            from parametres.models import ModeleMessage
            msg = ModeleMessage.get_contenu(etab, 'BULLETIN', {
                'nom_eleve': eleve.get_nom_complet(),
                'classe': bulletin.inscription.classe.nom,
                'trimestre': bulletin.trimestre.nom if bulletin.trimestre_id else '—',
                'etablissement': etab_nom,
            })

            if not dry_run:
                from core.tasks import envoyer_sms_async
                envoyer_sms_async(numero, msg)
            nb += 1
            logger.info(f"SMS bulletin → {numero} ({eleve})")

        return nb
