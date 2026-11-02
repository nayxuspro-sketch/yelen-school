"""Mesure de référence des six écrans les plus utilisés (audit P1-9, livrée en 5.47.2).

Le banc d'essai du projet datait : cette commande rejoue, sur les données réelles de l'établissement,
le même jeu de six pages à chaque livraison et affiche durée et nombre de requêtes SQL. Elle sert de
repère objectif (une régression se voit en secondes) et peut être planifiée :

    python manage.py mesure_reference                 # affiche le tableau
    python manage.py mesure_reference --json          # sortie machine (supervision)
    python manage.py mesure_reference --seuil-ms 2000 # code retour 1 si une page dépasse

La page d'accueil, la liste des élèves, les évaluations (entrée de la saisie des notes), les
redevables, les paiements et les bulletins couvrent les six familles d'écrans quotidiens.
"""
import json
import statistics
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import NoReverseMatch, reverse

PAGES = (
    ('Accueil', 'core:home'),
    ('Élèves', 'inscriptions:eleve_list'),
    ('Évaluations (notes)', 'pedagogie:evaluation_list'),
    ('Redevables', 'finances:liste_redevables'),
    ('Paiements', 'finances:paiement_list'),
    ('Bulletins', 'bulletins:index'),
)


class Command(BaseCommand):
    help = "Mesure la durée et le nombre de requêtes SQL des six écrans de référence."

    def add_arguments(self, parser):
        parser.add_argument('--utilisateur', help="Nom d'utilisateur à utiliser (par défaut : premier Super Admin)")
        parser.add_argument('--repeter', type=int, default=3, help='Mesures par page, la médiane est retenue (défaut : 3)')
        parser.add_argument('--seuil-ms', type=int, default=2000,
                            help='Durée au-delà de laquelle la commande échoue (défaut : 2 000 ms)')
        parser.add_argument('--json', action='store_true', help='Sortie JSON pour la supervision')

    def handle(self, *args, **options):
        from accounts.models import User

        if options['repeter'] < 1:
            raise CommandError('--repeter doit être supérieur ou égal à 1.')

        utilisateur = self._utilisateur(options['utilisateur'], User)
        client = Client()
        client.force_login(utilisateur)

        hotes = list(settings.ALLOWED_HOSTS) + ['testserver']
        lignes = []
        with override_settings(ALLOWED_HOSTS=hotes):
            for libelle, nom_url in PAGES:
                try:
                    url = reverse(nom_url)
                except NoReverseMatch as exc:                             # URL retirée ou renommée
                    lignes.append({'page': libelle, 'url': nom_url, 'statut': 0,
                                   'duree_ms': None, 'requetes': None, 'octets': None,
                                   'erreur': f'URL introuvable : {exc}'})
                    continue
                lignes.append(self._mesurer(client, libelle, url, options['repeter']))

        self._afficher(lignes, options)
        if any(l['statut'] != 200 or (l['duree_ms'] or 0) > options['seuil_ms'] for l in lignes):
            raise CommandError(f"Au moins une page dépasse le seuil de {options['seuil_ms']} ms "
                               "ou ne répond pas 200 : voir le tableau.")

    @staticmethod
    def _utilisateur(nom, User):
        qs = User.objects.filter(is_active=True)
        if nom:
            utilisateur = qs.filter(username=nom).first()
            if utilisateur is None:
                raise CommandError(f"Utilisateur « {nom} » introuvable.")
            return utilisateur
        utilisateur = qs.filter(is_superuser=True, must_change_password=False).order_by('username').first()
        if utilisateur is None:
            raise CommandError("Aucun Super Admin actif : préciser --utilisateur.")
        return utilisateur

    def _mesurer(self, client, libelle, url, repetitions):
        """Une passe à blanc (compilation des gabarits, caches froids), puis la médiane des passes réelles."""
        echauffement = client.get(url)
        if echauffement.status_code != 200:
            return {'page': libelle, 'url': url, 'statut': echauffement.status_code,
                    'duree_ms': None, 'requetes': None, 'octets': len(echauffement.content),
                    'erreur': f'Réponse {echauffement.status_code} au lieu de 200'}

        durees, requetes, taille = [], [], 0
        for _ in range(repetitions):
            with CaptureQueriesContext(connection) as capture:
                debut = time.perf_counter()
                reponse = client.get(url)
                durees.append((time.perf_counter() - debut) * 1000)
            requetes.append(len(capture.captured_queries))
            taille = len(reponse.content)
        return {'page': libelle, 'url': url, 'statut': 200,
                'duree_ms': round(statistics.median(durees), 1),
                'requetes': int(statistics.median(requetes)), 'octets': taille, 'erreur': None}

    def _afficher(self, lignes, options):
        if options['json']:
            self.stdout.write(json.dumps({'version': settings.YELEN_VERSION,
                                          'utilisateur': options['utilisateur'] or 'auto',
                                          'pages': lignes}, ensure_ascii=False))
            return
        self.stdout.write(f"Mesure de référence — YELEN SCHOOL {settings.YELEN_VERSION} "
                          f"({options['repeter']} passes, médiane)")
        self.stdout.write('')
        self.stdout.write(f"{'Page':<24}{'Statut':>7}{'Durée (ms)':>12}{'Requêtes':>10}{'Taille (Ko)':>13}")
        self.stdout.write('-' * 66)
        for l in lignes:
            if l['duree_ms'] is None:
                self.stdout.write(f"{l['page']:<24}{l['statut']:>7}{'—':>12}{'—':>10}{'—':>13}  {l['erreur']}")
                continue
            self.stdout.write(f"{l['page']:<24}{l['statut']:>7}{l['duree_ms']:>12.1f}"
                              f"{l['requetes']:>10}{l['octets'] / 1024:>13.0f}")
        self.stdout.write('-' * 66)
        mesurees = [l['duree_ms'] for l in lignes if l['duree_ms'] is not None]
        if mesurees:
            self.stdout.write(f"Seuil : {options['seuil_ms']} ms par page · "
                              f"plus lente : {max(mesurees):.0f} ms · médiane : {statistics.median(mesurees):.0f} ms")
