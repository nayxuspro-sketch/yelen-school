"""
Traite la file persistante des SMS (nouvelles tentatives des envois échoués).
    python manage.py sms_file              # jusqu'à 50 SMS
    python manage.py sms_file --limite 200
À planifier si l'établissement envoie beaucoup de SMS ; sinon la file est aussi reprise à chaque nouvel envoi,
par la commande ``sms_auto`` et depuis la page Exploitation.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Envoie les SMS en attente dans la file persistante (nouvelles tentatives)."

    def add_arguments(self, parser):
        parser.add_argument('--limite', type=int, default=50)

    def handle(self, *args, **options):
        from core.tasks import traiter_file_sms
        bilan = traiter_file_sms(limite=options['limite'])
        self.stdout.write(f"{bilan['envoyes']} envoyé(s), {bilan['echecs']} échec(s), {bilan['en_attente']} en attente.")
