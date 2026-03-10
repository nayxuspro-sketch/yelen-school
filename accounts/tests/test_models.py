"""
Tests unitaires pour accounts/models.py

Vérifie l'authentification et les rôles YELEN SCHOOL :
- UserManager : create_user (email obligatoire/normalisé), create_superuser (rôle, is_staff, is_superuser)
- User : Héritage BaseModel, email unique, role (RoleChoices), etablissement (FK), is_directeur() etc.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase

from core.models import BaseModel, RoleChoices
from etablissements.models import Etablissement

User = get_user_model()


class UserModelTest(TestCase):
    """Tests pour le modèle User personnalisé."""

    @classmethod
    def setUpTestData(cls):
        cls.etab = Etablissement.objects.create(nom="Lycée Test", code="LTST")

    def test_user_inherits_base_model(self):
        """User doit hériter de BaseModel (UUID pk, is_active, etc.)."""
        self.assertTrue(issubclass(User, BaseModel))
        # Vérif pk est UUID
        pk_field = User._meta.get_field('id')
        self.assertIsInstance(pk_field, models.UUIDField)

    def test_user_has_role_field(self):
        """Vérifie le champ `role`."""
        field = User._meta.get_field('role')
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.default, RoleChoices.ENSEIGNANT)
        self.assertEqual(field.choices, RoleChoices.choices)

    def test_user_has_etablissement_fk(self):
        """Vérifie le champ `etablissement`."""
        field = User._meta.get_field('etablissement')
        self.assertIsInstance(field, models.ForeignKey)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_user_has_email_unique(self):
        """Vérifie le champ `email` (unique)."""
        field = User._meta.get_field('email')
        self.assertIsInstance(field, models.EmailField)
        self.assertTrue(field.unique)

    def test_is_directeur_method(self):
        user = User(role=RoleChoices.DIRECTEUR)
        self.assertTrue(user.is_directeur())
        user.role = RoleChoices.ENSEIGNANT
        self.assertFalse(user.is_directeur())

    def test_is_avs_method(self):
        user = User(role=RoleChoices.AVS)
        self.assertTrue(user.is_avs())
        user.role = RoleChoices.ENSEIGNANT
        self.assertFalse(user.is_avs())

    def test_is_secretaire_method(self):
        user = User(role=RoleChoices.SECRETAIRE)
        self.assertTrue(user.is_secretaire())
        user.role = RoleChoices.ENSEIGNANT
        self.assertFalse(user.is_secretaire())

    def test_is_enseignant_method(self):
        user = User(role=RoleChoices.ENSEIGNANT)
        self.assertTrue(user.is_enseignant())
        user.role = RoleChoices.AVS
        self.assertFalse(user.is_enseignant())


class UserManagerTest(TestCase):
    """Tests pour le UserManager personnalisé."""

    def test_create_user(self):
        """Test la création d'un utilisateur standard."""
        user = User.objects.create_user(
            username='testuser',
            email='Test@EXAMPLE.com',
            password='Password123!',
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')  # Email normalisé
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, RoleChoices.ENSEIGNANT) # default

    def test_create_user_requires_email(self):
        """Un email est obligatoire."""
        with self.assertRaises(ValueError):
            User.objects.create_user(username='test', password='pw')

    def test_create_superuser(self):
        """Test la création d'un superuser."""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='SuperPassword123!',
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, RoleChoices.SUPER_ADMIN)
        self.assertEqual(admin.username, 'admin')

    def test_create_superuser_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(username='admin', password='pw')

    def test_create_superuser_invalid_flags(self):
        """Vérifie que les flags is_staff et is_superuser ne peuvent pas être False."""
        with self.assertRaisesMessage(ValueError, 'Un superuser doit avoir is_staff=True.'):
            User.objects.create_superuser(
                username='admin', email='a@b.com', password='pw', is_staff=False
            )
        with self.assertRaisesMessage(ValueError, 'Un superuser doit avoir is_superuser=True.'):
            User.objects.create_superuser(
                username='admin', email='a@b.com', password='pw', is_superuser=False
            )


class SettingsTest(TestCase):
    def test_auth_user_model_setting(self):
        from django.conf import settings
        self.assertEqual(settings.AUTH_USER_MODEL, 'accounts.User')
