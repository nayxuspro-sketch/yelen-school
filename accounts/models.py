"""
accounts/models.py — Authentification et rôles RBAC YELEN SCHOOL

Ce module contient :
- UserManager  : Manager personnalisé pour la création d'utilisateurs
- User         : Modèle utilisateur personnalisé (AbstractUser + BaseModel)

Référence : docs/PROMPT_V3_3.md §2.2
"""

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models

from core.models import BaseModel, RoleChoices


class UserManager(DjangoUserManager):
    """Manager personnalisé pour le modèle User YELEN SCHOOL.

    Surcharge create_user et create_superuser pour :
    - Exiger un email à la création
    - Normaliser l'email
    - Attribuer automatiquement le rôle SUPER_ADMIN aux superusers
    """

    def create_user(
        self,
        username: str,
        email: str | None = None,
        password: str | None = None,
        **extra_fields,
    ):
        """Crée et retourne un utilisateur avec email normalisé."""
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email).lower()
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return super().create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )

    def create_superuser(
        self,
        username: str,
        email: str | None = None,
        password: str | None = None,
        **extra_fields,
    ):
        """Crée un superuser avec rôle SUPER_ADMIN automatique."""
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email).lower()
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', RoleChoices.SUPER_ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Un superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Un superuser doit avoir is_superuser=True.')

        return super().create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )


class User(AbstractUser, BaseModel):
    """Modèle utilisateur personnalisé YELEN SCHOOL.

    Hérite de :
    - AbstractUser : système auth Django (username, password, is_staff, etc.)
    - BaseModel    : UUID pk, created_at, updated_at, is_active

    Champs ajoutés :
    - email        : identifiant principal (unique)
    - role         : rôle RBAC (RoleChoices)
    - etablissement: FK vers l'établissement de rattachement
    - telephone    : numéro de téléphone

    Note v3.3 : Directeur = "Directeur / Proviseur" (jamais "Directeur/SG")
    """

    email = models.EmailField(
        unique=True,
        verbose_name='Adresse email',
        help_text='Utilisé comme identifiant de connexion.',
    )
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.ENSEIGNANT,
        verbose_name='Rôle',
        help_text='Rôle RBAC déterminant les permissions.',
    )
    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs',
        verbose_name='Établissement',
        help_text='Établissement de rattachement. Null pour Super Admin.',
    )
    groupe = models.ForeignKey(
        'etablissements.GroupeEtablissements',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='utilisateurs_reseau',
        verbose_name='Groupe / Réseau',
        help_text='Groupe géré (pour le rôle Directeur Réseau).',
    )
    telephone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='Téléphone',
    )
    eleves_lies = models.ManyToManyField(
        'inscriptions.Eleve',
        blank=True,
        related_name='utilisateurs_lies',
        verbose_name='Élèves liés',
        help_text='Élèves associés à ce compte (enfants pour un parent, soi-même pour un élève).',
    )

    # ── Double authentification (TOTP) ──
    totp_secret = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name='Secret TOTP',
        help_text='Secret base32 pour la double authentification (TOTP).',
    )
    totp_enabled = models.BooleanField(
        default=False,
        verbose_name='2FA activée',
        help_text='Authentification à deux facteurs via application TOTP.',
    )

    # ── Verrouillage de compte (brute force protection) ──
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name='Tentatives de connexion échouées',
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Compte verrouillé jusqu\'à',
        help_text='Date de fin du verrouillage temporaire.',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['last_name', 'first_name']

    def __str__(self) -> str:
        return f'{self.get_full_name()} ({self.get_role_display()})'

    # ── Méthodes de vérification de rôle ──

    def is_directeur(self) -> bool:
        """L'utilisateur a-t-il le rôle Directeur / Proviseur ?"""
        return self.role == RoleChoices.DIRECTEUR

    def is_censeur(self) -> bool:
        """L'utilisateur a-t-il le rôle Censeur / Proviseur ?"""
        return self.role == RoleChoices.CENSEUR

    def is_avs(self) -> bool:
        """L'utilisateur a-t-il le rôle Agent de Vie Scolaire ?"""
        return self.role == RoleChoices.AVS

    def is_enseignant(self) -> bool:
        """L'utilisateur a-t-il le rôle Enseignant ?"""
        return self.role == RoleChoices.ENSEIGNANT

    def is_comptable(self) -> bool:
        """L'utilisateur a-t-il le rôle Comptable ?"""
        return self.role == RoleChoices.COMPTABLE

    def is_secretaire(self) -> bool:
        """L'utilisateur a-t-il le rôle Secrétaire ?"""
        return self.role == RoleChoices.SECRETAIRE

    def is_parent(self) -> bool:
        return self.role == RoleChoices.PARENT

    def is_eleve(self) -> bool:
        return self.role == RoleChoices.ELEVE
