from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

ADMIN_EMAIL = "admin@yelen.edu"
ADMIN_PASSWORD = "admin123"


class Command(BaseCommand):
    help = "Crée ou réinitialise le super administrateur par défaut."

    def handle(self, *args, **options):
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
            },
        )

        if created:
            user.set_password(ADMIN_PASSWORD)
            user.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS(
                f"Super administrateur {ADMIN_EMAIL} créé avec succès."
            ))
        else:
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.role = "SUPER_ADMIN"
            user.set_password(ADMIN_PASSWORD)
            user.save(update_fields=["password", "is_staff", "is_superuser", "is_active", "role"])
            self.stdout.write(self.style.SUCCESS(
                f"Mot de passe du super administrateur {ADMIN_EMAIL} réinitialisé."
            ))
