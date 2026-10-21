"""Vérification active des paiements Mobile Money en ligne (CinetPay).

Exécutée par la tâche planifiée Windows (programmer-verification-paiements.bat) toutes les
10 minutes : les demandes en attente munies d'un lien sont contrôlées auprès de la passerelle
et confirmées (paiement, reçu, SMS) dès que le parent a payé.
"""
from django.core.management.base import BaseCommand

from finances.paiements_mobiles import cinetpay_configure, verifier_en_attente


class Command(BaseCommand):
    help = "Vérifie auprès de CinetPay les demandes Mobile Money en attente munies d'un lien de paiement."

    def add_arguments(self, parser):
        parser.add_argument('--limite', type=int, default=50, help="Nombre maximal de demandes vérifiées (50).")
        parser.add_argument('--jours', type=int, default=7, help="Ancienneté maximale des demandes, en jours (7).")

    def handle(self, *args, **options):
        if not cinetpay_configure():
            self.stdout.write("Paiement en ligne non configuré (CINETPAY_API_KEY, CINETPAY_SITE_ID, CINETPAY_URL_PUBLIQUE) : rien à faire.")
            return
        bilan = verifier_en_attente(limite=options['limite'], jours=options['jours'])
        self.stdout.write(
            f"Vérification : {bilan.get('CONFIRME', 0)} confirmé(s), {bilan.get('EN_ATTENTE', 0)} en attente, "
            f"{bilan.get('REFUSE', 0)} refusé(s), {bilan.get('ERREUR', 0)} erreur(s)."
        )
