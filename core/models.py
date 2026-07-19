"""
core/models.py — Fondation YELEN SCHOOL

Ce module contient :
- BaseModel        : Classe abstraite héritée par TOUS les modèles du projet
- CycleChoices     : Les 4 cycles scolaires du Burkina Faso (MENA)
- RoleChoices      : Les 10 rôles RBAC du système

Référence : docs/PROMPT_V3_3.md §2.1, §2.2, §4.2
"""

import uuid

from django.db import models


# ──────────────────────────────────────────────
# Choix constants — réutilisables par toutes les apps
# ──────────────────────────────────────────────

class CycleChoices(models.TextChoices):
    """Cycles scolaires officiels du Burkina Faso (MENA).

    - Préscolaire  : Crèche, PS, MS, GS
    - Primaire     : CP1, CP2, CE1, CE2, CM1, CM2 — examen CEP
    - Post-primaire: 6ème, 5ème, 4ème, 3ème — examen BEPC
    - Secondaire   : 2nde, 1ère, Terminale (A/B/C/D) — examen BAC
    """
    PRESCOLAIRE   = 'PRESCOLAIRE',   'Préscolaire'
    PRIMAIRE      = 'PRIMAIRE',      'Primaire'
    POST_PRIMAIRE = 'POST_PRIMAIRE', 'Post-primaire'
    SECONDAIRE    = 'SECONDAIRE',    'Secondaire'


class RoleChoices(models.TextChoices):
    """Rôles RBAC du système YELEN SCHOOL.

    Aligné sur PROMPT_V3_3.md §2.2.
    Note : Directeur = Directeur / Proviseur (jamais Directeur/SG).
    """
    SUPER_ADMIN       = 'SUPER_ADMIN',       'Super Admin Éditeur'
    DIRECTEUR_RESEAU  = 'DIRECTEUR_RESEAU',  'Directeur Réseau'
    DIRECTEUR         = 'DIRECTEUR',         'Directeur / Proviseur'
    CENSEUR           = 'CENSEUR',           'Censeur / Proviseur'
    AVS               = 'AVS',               'Agent de Vie Scolaire'
    ENSEIGNANT        = 'ENSEIGNANT',         'Enseignant'
    COMPTABLE         = 'COMPTABLE',          'Comptable'
    SECRETAIRE        = 'SECRETAIRE',         'Secrétaire'
    PARENT            = 'PARENT',             'Parent'
    ELEVE             = 'ELEVE',              'Élève'


# ──────────────────────────────────────────────
# Modèle de base abstrait
# ──────────────────────────────────────────────

class BaseModel(models.Model):
    """Classe abstraite héritée par TOUS les modèles YELEN SCHOOL.

    Fournit :
    - id         : UUID comme clé primaire (pas d'AutoField int)
    - created_at : Date de création (auto)
    - updated_at : Date de dernière modification (auto)
    - is_active  : Soft-delete / filtre d'activité
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='Identifiant',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création',
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created',
        verbose_name='Créé par',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Dernière modification',
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated',
        verbose_name='Modifié par',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Décocher pour désactiver sans supprimer.',
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


# ──────────────────────────────────────────────
# Modèle d'Audit Trail
# ──────────────────────────────────────────────

class AuditLog(models.Model):
    """Journal d'audit pour tracer toutes les modifications."""

    class ActionChoices(models.TextChoices):
        CREATE = 'CREATE', 'Création'
        UPDATE = 'UPDATE', 'Modification'
        DELETE = 'DELETE', 'Suppression'

    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date/Heure',
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name='Utilisateur',
    )
    action = models.CharField(
        max_length=10,
        choices=ActionChoices.choices,
        verbose_name='Action',
    )
    app_label = models.CharField(
        max_length=50,
        verbose_name='Application',
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name='Modèle',
    )
    object_id = models.UUIDField(
        verbose_name='ID de l\'objet',
    )
    object_repr = models.CharField(
        max_length=200,
        verbose_name='Objet',
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Modifications',
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Adresse IP',
    )

    class Meta:
        verbose_name = 'Journal d\'audit'
        verbose_name_plural = 'Journaux d\'audit'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['app_label', 'model_name']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.action} - {self.object_repr} - {self.user} - {self.timestamp}"


class Notification(models.Model):
    """Notification in-app envoyée à un utilisateur."""

    class TypeChoices(models.TextChoices):
        BULLETIN   = 'BULLETIN',   'Bulletin publié'
        ABSENCE    = 'ABSENCE',    'Absence signalée'
        SANCTION   = 'SANCTION',   'Sanction disciplinaire'
        GENERAL    = 'GENERAL',    'Information générale'

    destinataire = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Destinataire',
    )
    type = models.CharField(
        max_length=20,
        choices=TypeChoices.choices,
        default=TypeChoices.GENERAL,
    )
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lien = models.CharField(max_length=500, blank=True, default='')
    lu = models.BooleanField(default=False)
    email_envoye = models.BooleanField(default=False)
    sms_envoye = models.BooleanField(default=False, verbose_name='SMS envoyé')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['destinataire', 'lu', '-created_at']),
        ]

    def __str__(self):
        return f"{self.destinataire} — {self.titre}"
