import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()

ADMIN_EMAIL = "admin@yelen.edu"
LEGACY_ADMIN_PASSWORD = "admin123"


class Command(BaseCommand):
    help = "Crée le super administrateur initial sans réinitialiser un compte existant."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help="Réinitialise explicitement le mot de passe avec INITIAL_ADMIN_PASSWORD.",
        )

    def _initial_password(self):
        password = os.environ.get('INITIAL_ADMIN_PASSWORD', '').strip()
        if not password or password.lower().startswith(('generer-', 'votre-', 'changez')):
            raise CommandError(
                'INITIAL_ADMIN_PASSWORD doit être défini avec un secret aléatoire '
                'd’au moins 12 caractères.'
            )
        if len(password) < 12:
            raise CommandError('INITIAL_ADMIN_PASSWORD doit contenir au moins 12 caractères.')
        return password

    def handle(self, *args, **options):
        # Valider avant la création afin qu'un installateur mal configuré ne
        # laisse pas en base un compte initial sans mot de passe utilisable.
        initial_password = None
        if not User.objects.filter(email=ADMIN_EMAIL).exists():
            initial_password = self._initial_password()

        user, created = User.objects.get_or_create(
            email=ADMIN_EMAIL,
            defaults={
                "username": ADMIN_EMAIL,
                "first_name": "Super",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "role": "SUPER_ADMIN",
                "must_change_password": True,
            },
        )

        update_fields = []
        if created:
            password = initial_password or self._initial_password()
            user.set_password(password)
            user.must_change_password = True
            update_fields = ['password', 'must_change_password']
            message = (
                f"Super administrateur {ADMIN_EMAIL} créé. "
                "Le changement du mot de passe est obligatoire à la première connexion."
            )
        else:
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.role = "SUPER_ADMIN"
            update_fields = ['is_staff', 'is_superuser', 'is_active', 'role']

            # Les installations historiques utilisant encore admin123 doivent
            # passer par le même parcours de remplacement obligatoire.
            if user.check_password(LEGACY_ADMIN_PASSWORD):
                user.must_change_password = True
                update_fields.append('must_change_password')

            if options.get('reset'):
                password = self._initial_password()
                user.set_password(password)
                user.must_change_password = True
                # Une réinitialisation explicite doit aussi rendre le compte
                # immédiatement utilisable après plusieurs tentatives
                # erronées, sans attendre l'expiration du verrouillage.
                user.failed_login_attempts = 0
                user.locked_until = None
                update_fields.extend([
                    'password',
                    'must_change_password',
                    'failed_login_attempts',
                    'locked_until',
                ])
                message = (
                    f"Mot de passe de {ADMIN_EMAIL} réinitialisé. "
                    "Le changement est obligatoire à la prochaine connexion."
                )
            else:
                message = f"Super administrateur {ADMIN_EMAIL} vérifié sans réinitialiser son mot de passe."

        if update_fields:
            user.save(update_fields=list(dict.fromkeys(update_fields)))
        self.stdout.write(self.style.SUCCESS(message))
