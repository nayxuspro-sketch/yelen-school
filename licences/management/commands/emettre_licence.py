"""
Commande : emettre_licence (côté ÉDITEUR)
=========================================
Émet un code de licence hors ligne (jeton YELEN3) signé Ed25519 avec la clé
privée de l'éditeur. Aucune écriture en base : la commande peut s'exécuter
sur n'importe quelle instance (poste éditeur, environnement de test), la clé
privée étant fournie par la variable d'environnement LICENCE_PRIVATE_KEY.

Le client colle ensuite ce code dans « Activer » (Super Admin) ; l'application
le vérifie avec LICENCE_PUBLIC_KEY et le lie au serveur dont l'empreinte a été
déclarée.

Usage :
    python manage.py emettre_licence --etablissement <uuid> --type PREMIUM \\
        --expiration 2027-09-16 --empreinte <identifiant du serveur> [--cle YELEN-XXXX-XXXX-XXXX]

Les deux identifiants (établissement, serveur) sont affichés au client sur la
page Licences → Activer.
"""
import secrets
import uuid
from datetime import date, datetime, timezone

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from licences.jeton import charger_cle_privee, construire_payload, emettre_jeton
from licences.models import TypeLicence


def _generer_cle() -> str:
    hexa = secrets.token_hex(6).upper()
    return f"YELEN-{hexa[0:4]}-{hexa[4:8]}-{hexa[8:12]}"


class Command(BaseCommand):
    help = "Émet un code de licence signé (jeton YELEN3) — réservé à l'éditeur (LICENCE_PRIVATE_KEY)."

    def add_arguments(self, parser):
        parser.add_argument('--etablissement', required=True,
                            help="Identifiant (UUID) de l'établissement, affiché sur la page Activer")
        parser.add_argument('--type', required=True, choices=list(TypeLicence.values),
                            help="Type de licence : STARTER, STANDARD, PREMIUM, RESEAU")
        parser.add_argument('--expiration', required=True,
                            help="Date d'expiration AAAA-MM-JJ")
        parser.add_argument('--empreinte', default='',
                            help="Identifiant du serveur (64 caractères hexadécimaux) ; vide = licence non liée")
        parser.add_argument('--cle', default='',
                            help="Clé de licence YELEN-XXXX-XXXX-XXXX à réutiliser (défaut : générée)")
        parser.add_argument('--activation', default='',
                            help="Date d'activation AAAA-MM-JJ (défaut : aujourd'hui)")
        parser.add_argument('--sortie', default='',
                            help="Fichier dans lequel écrire le code (défaut : affichage seul)")

    def handle(self, *args, **options):
        cle_privee = charger_cle_privee(getattr(settings, 'LICENCE_PRIVATE_KEY', ''))
        if cle_privee is None:
            raise CommandError(
                "LICENCE_PRIVATE_KEY absente ou invalide — cette commande s'exécute uniquement "
                "chez l'éditeur (ex. : docker compose exec -e LICENCE_PRIVATE_KEY=<hex> web python manage.py emettre_licence …)."
            )
        try:
            etablissement_id = uuid.UUID(options['etablissement'])
        except ValueError as exc:
            raise CommandError("--etablissement doit être un UUID.") from exc
        try:
            expiration = date.fromisoformat(options['expiration'])
        except ValueError as exc:
            raise CommandError("--expiration doit être au format AAAA-MM-JJ.") from exc
        if expiration < date.today():
            raise CommandError("La date d'expiration est déjà passée.")

        empreinte = ''.join(options['empreinte'].split()).lower()
        if empreinte and (len(empreinte) != 64 or any(c not in '0123456789abcdef' for c in empreinte)):
            raise CommandError("--empreinte doit comporter 64 caractères hexadécimaux (identifiant du serveur).")

        cle = options['cle'].strip().upper() or _generer_cle()
        if len(cle) != 20 or not cle.startswith('YELEN-'):
            raise CommandError("--cle doit être au format YELEN-XXXX-XXXX-XXXX.")

        activation = None
        if options['activation']:
            try:
                jour = date.fromisoformat(options['activation'])
            except ValueError as exc:
                raise CommandError("--activation doit être au format AAAA-MM-JJ.") from exc
            activation = datetime(jour.year, jour.month, jour.day, tzinfo=timezone.utc)

        payload = construire_payload(
            cle=cle, type_licence=options['type'], etablissement_id=etablissement_id,
            date_expiration=expiration, empreinte_serveur=empreinte, date_activation=activation,
        )
        jeton = emettre_jeton(payload, cle_privee)

        self.stdout.write(self.style.SUCCESS("Code de licence émis"))
        self.stdout.write(f"  Clé           : {cle}")
        self.stdout.write(f"  Type          : {options['type']}")
        self.stdout.write(f"  Établissement : {etablissement_id}")
        self.stdout.write(f"  Expiration    : {expiration.isoformat()}")
        self.stdout.write(f"  Serveur       : {empreinte or 'non lié'}")
        self.stdout.write("")
        self.stdout.write(jeton)
        if options['sortie']:
            with open(options['sortie'], 'w', encoding='utf-8') as fichier:
                fichier.write(jeton + '\n')
            self.stdout.write("")
            self.stdout.write(f"Écrit dans : {options['sortie']}")
