"""Relève la boîte de réception du téléphone passerelle (app SMS Gateway, GET /inbox) et traite les SMS des parents.

    python manage.py sms_recus              # une relève, bilan affiché
    python manage.py sms_recus --boucle     # service : relève toutes les --intervalle secondes (docker compose : service « sms »)

À chaque passage, les SMS sortants dont la reprise est due (réponses, relances échouées) sont aussi renvoyés.
"""
import time

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Relève les SMS reçus par le téléphone passerelle et y répond (AIDE / NOTE / SOLDE / ABS)."

    def add_arguments(self, parser):
        parser.add_argument('--boucle', action='store_true', help="Tourne sans fin (service).")
        parser.add_argument('--intervalle', type=int, default=15, help="Secondes entre deux relèves en mode --boucle (défaut 15).")
        parser.add_argument('--iterations', type=int, default=0, help="En mode --boucle : nombre de passages (0 = sans fin).")

    def handle(self, *args, **options):
        from communication.sms_recus import relever_boite_reception
        from core.tasks import traiter_file_sms

        passages = 0
        while True:
            try:
                bilan = relever_boite_reception()
                if bilan['ok']:
                    file_sms = traiter_file_sms(limite=20)
                    if bilan['nouveaux'] or file_sms['envoyes'] or file_sms['echecs'] or not options['boucle']:
                        self.stdout.write(f"Relève : {bilan['nouveaux']} nouveau(x) SMS, {bilan['ignores']} ignoré(s) ; "
                                          f"file SMS : {file_sms['envoyes']} envoyé(s), {file_sms['echecs']} échec(s), "
                                          f"{file_sms['en_attente']} en attente.")
                elif not options['boucle'] or passages % 40 == 0:   # en boucle : un rappel toutes les ~10 min
                    self.stdout.write(f"Relève impossible : {bilan['motif']}")
            except Exception as e:  # le service ne doit jamais s'arrêter sur une erreur passagère
                self.stderr.write(f"Relève interrompue : {e}")
            finally:
                connection.close()
            passages += 1
            if not options['boucle'] or (options['iterations'] and passages >= options['iterations']):
                break
            time.sleep(max(1, options['intervalle']))
