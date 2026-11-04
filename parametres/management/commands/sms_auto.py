"""
management command : sms_auto
=================================
YELEN SCHOOL — Envoi des SMS automatiques planifiés.

Usage :
    python manage.py sms_auto
    python manage.py sms_auto --type ABSENCE_J1
    python manage.py sms_auto --type ECHEANCIER
    python manage.py sms_auto --type RESULTATS
    python manage.py sms_auto --type COMPTE_RENDU   # compte rendu du promoteur, à la demande (bouton Tester)
    python manage.py sms_auto --dry-run
    python manage.py sms_auto --etablissement <uuid>

Cron recommandé (Windows Task Scheduler ou Linux cron) :
    0 7 * * * /path/to/venv/bin/python manage.py sms_auto

Le compte rendu quotidien du promoteur n'est pas traité par l'exécution planifiée : il part à son heure par le
service SMS (``sms_recus --boucle``) ; ici seulement sur demande explicite (``--type COMPTE_RENDU``).
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
            choices=['ABSENCE_J1', 'ECHEANCIER', 'RESULTATS', 'PRETS_RETARD', 'COMPTE_RENDU'],
            help="Exécuter uniquement ce type de déclencheur",
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Simuler sans envoyer de SMS",
        )
        parser.add_argument(
            '--etablissement',
            type=str,
            help="UUID d'un établissement à traiter (défaut : tous)",
        )

    def handle(self, *args, **options):
        from core.sms import sms_actifs
        if not sms_actifs():
            self.stdout.write(self.style.WARNING("SMS_ENABLED=False — aucun SMS envoyé."))
            return

        from parametres.models import DeclencheurSMS
        filtre_type = options.get('type')
        etablissement_id = options.get('etablissement')
        dry_run = options.get('dry_run', False)

        qs = DeclencheurSMS.objects.filter(actif=True).select_related('etablissement')
        if filtre_type:
            qs = qs.filter(type_declencheur=filtre_type)
        else:   # le compte rendu du promoteur part à son heure par le service SMS, pas avec le lot du matin
            qs = qs.exclude(type_declencheur=DeclencheurSMS.TypeChoices.COMPTE_RENDU)
        if etablissement_id:
            qs = qs.filter(etablissement_id=etablissement_id)

        total = 0
        for declencheur in qs:
            nb = self._run_declencheur(declencheur, dry_run)
            total += nb
            if nb > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"[{declencheur.get_type_declencheur_display()}] {nb} SMS {'(simulé)' if dry_run else 'envoyé(s)'}")
                )

        self.stdout.write(self.style.SUCCESS(f"Total : {total} SMS {'simulés' if dry_run else 'envoyés'}."))
        if not dry_run:
            from core.tasks import traiter_file_sms
            bilan = traiter_file_sms()
            self.stdout.write(f"File SMS : {bilan['envoyes']} envoyé(s), {bilan['echecs']} échec(s), "
                              f"{bilan['en_attente']} en attente.")

    def _run_declencheur(self, declencheur, dry_run):
        if declencheur.type_declencheur == declencheur.TypeChoices.COMPTE_RENDU:
            return self._compte_rendu(declencheur, dry_run)

        # Une exécution planifiée ne doit pas renvoyer deux fois le même
        # déclencheur le même jour (clic manuel + tâche Windows, par exemple).
        if not dry_run and declencheur.last_run:
            last_run_date = timezone.localtime(declencheur.last_run).date()
            if last_run_date >= timezone.localdate():
                logger.info("Déclencheur SMS déjà exécuté aujourd'hui : %s", declencheur)
                return 0

        t = declencheur.type_declencheur
        etab = declencheur.etablissement
        nb = 0

        if t == 'ABSENCE_J1':
            nb = self._absence_j1(declencheur, etab, dry_run)
        elif t == 'ECHEANCIER':
            nb = self._echeancier_rappel(declencheur, etab, dry_run)
        elif t == 'RESULTATS':
            nb = self._resultats_dispo(declencheur, etab, dry_run)
        elif t == 'PRETS_RETARD':
            nb = self._prets_retard(declencheur, etab, dry_run)

        if not dry_run:
            declencheur.last_run = timezone.now()
            update_fields = ['last_run']
            if nb > 0:
                declencheur.nb_envoyes_total = (declencheur.nb_envoyes_total or 0) + nb
                update_fields.append('nb_envoyes_total')
            declencheur.save(update_fields=update_fields)

        return nb

    # ── COMPTE RENDU DU PROMOTEUR (à la demande) ───────────────────

    def _compte_rendu(self, declencheur, dry_run):
        """Envoi immédiat du compte rendu du moment ; ``last_run`` reste celui de l'envoi automatique du jour,
        qui a donc toujours lieu à l'heure prévue."""
        from communication.compte_rendu import envoyer
        nb = envoyer(declencheur, dry_run=dry_run)
        if nb and not dry_run:
            declencheur.nb_envoyes_total = (declencheur.nb_envoyes_total or 0) + nb
            declencheur.save(update_fields=['nb_envoyes_total'])
        return nb

    # ── ABSENCE J+1 ────────────────────────────────────────────────

    def _absence_j1(self, declencheur, etab, dry_run):
        from presences.models import Presence
        hier = timezone.now().date() - timedelta(days=1)

        # Le projet stocke les absences dans Presence (statut ABSENT), liées
        # à un Appel ; il n'existe pas de modèle Absence séparé. Un élève peut
        # avoir plusieurs appels le même jour : un seul SMS est envoyé.
        absences = (
            Presence.objects
            .filter(
                inscription__classe__etablissement=etab,
                appel__date=hier,
                statut=Presence.StatutChoices.ABSENT,
            )
            .select_related('inscription__eleve', 'inscription__classe')
        )

        etab_nom = etab.nom
        nb = 0
        inscriptions_deja_traitees = set()
        for absence in absences:
            inscription_id = absence.inscription_id
            if inscription_id in inscriptions_deja_traitees:
                continue
            inscriptions_deja_traitees.add(inscription_id)
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
                date_limite=seuil,
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
                'montant': f"{ech.montant_du:,.0f}".replace(',', ' '),
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

    # ── PRÊTS D'OUVRAGES EN RETARD ─────────────────────────────────

    def _prets_retard(self, declencheur, etab, dry_run):
        """Relance les familles des ouvrages non rendus à l'échéance : un avis par prêt et par période de
        ``jours_avant`` jours (3 par défaut), jamais deux pour le même prêt."""
        from django.utils import timezone
        from core.notifications import notifier_pret_retard
        from manuels.models import AttributionManuel

        today = timezone.localdate()
        intervalle = timedelta(days=declencheur.jours_avant or 3)
        retards = (
            AttributionManuel.objects
            .filter(
                exemplaire__manuel__etablissement=etab,
                date_retour__isnull=True,
                date_retour_prevue__lt=today,
            )
            .select_related('exemplaire__manuel', 'inscription__eleve', 'inscription__classe')
        )

        nb = 0
        for attribution in retards:
            deja = attribution.derniere_relance_le
            if deja and timezone.now() - deja < intervalle:
                continue
            if dry_run:
                nb += 1
                continue
            if notifier_pret_retard(attribution):
                nb += 1
        return nb
