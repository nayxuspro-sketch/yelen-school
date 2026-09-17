"""
core/models.py — Fondation YELEN SCHOOL

Ce module contient :
- BaseModel        : Classe abstraite héritée par TOUS les modèles du projet
- CycleChoices     : Les 4 cycles scolaires du Burkina Faso (MENA)
- RoleChoices      : Les 10 rôles RBAC du système

Référence : docs/PROMPT_V3_3.md §2.1, §2.2, §4.2
"""

import hashlib
import json
import uuid

from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django.utils import timezone


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

class AuditLogQuerySet(models.QuerySet):
    """Interdit les opérations bulk qui contourneraient l'append-only."""

    def update(self, **kwargs):
        raise ValidationError("Le journal d'audit ne peut pas être modifié.")

    def delete(self):
        raise ValidationError("Le journal d'audit ne peut pas être supprimé.")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Utilisez record_audit() pour ajouter une trace.")


class AuditLogManager(models.Manager.from_queryset(AuditLogQuerySet)):
    pass


class AuditLog(models.Model):
    """Journal append-only, chaîné cryptographiquement.

    ``changes`` contient l'ancien et le nouveau contenu. ``entry_hash`` est
    calculé sur les métadonnées et ``previous_hash`` ; une suppression ou une
    modification SQL laisse donc une rupture détectable par la vérification de
    chaîne. La protection complète exige en plus des droits PostgreSQL séparés
    et un export signé hors de la base.
    """

    class ActionChoices(models.TextChoices):
        CREATE = 'CREATE', 'Création'
        UPDATE = 'UPDATE', 'Modification'
        DELETE = 'DELETE', 'Suppression'
        EXPORT = 'EXPORT', 'Export'
        LOGIN = 'LOGIN', 'Connexion'
        LOGIN_FAILED = 'LOGIN_FAILED', 'Échec de connexion'
        SECURITY = 'SECURITY', 'Événement de sécurité'

    timestamp = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name='Date/Heure',
    )
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name='Utilisateur',
    )
    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Établissement",
    )
    action = models.CharField(
        max_length=20,
        choices=ActionChoices.choices,
        verbose_name='Action',
    )
    app_label = models.CharField(max_length=50, verbose_name='Application')
    model_name = models.CharField(max_length=100, verbose_name='Modèle')
    object_id = models.CharField(max_length=64, verbose_name="ID de l'objet")
    object_repr = models.CharField(max_length=200, verbose_name='Objet')
    changes = models.JSONField(default=dict, blank=True, verbose_name='Modifications')
    reason = models.TextField(blank=True, default='', verbose_name='Motif')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='Adresse IP')
    user_agent = models.CharField(max_length=500, blank=True, default='', verbose_name='Navigateur')
    source = models.CharField(max_length=30, default='HTTP', verbose_name='Source')
    request_id = models.CharField(max_length=64, blank=True, default='', verbose_name='Requête')
    previous_hash = models.CharField(max_length=64, blank=True, default='', editable=False)
    entry_hash = models.CharField(max_length=64, blank=True, default='', editable=False)

    objects = AuditLogManager()

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['app_label', 'model_name']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['etablissement', '-timestamp'], name='core_auditl_etab_ts_idx'),
        ]

    def __str__(self):
        return f"{self.action} - {self.object_repr} - {self.user} - {self.timestamp}"

    def _hash_content(self):
        return json.dumps({
            'timestamp': self.timestamp.isoformat() if self.timestamp else '',
            'user_id': str(self.user_id) if self.user_id else None,
            'etablissement_id': str(self.etablissement_id) if self.etablissement_id else None,
            'action': self.action,
            'app_label': self.app_label,
            'model_name': self.model_name,
            'object_id': self.object_id,
            'object_repr': self.object_repr,
            'changes': self.changes,
            'reason': self.reason,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'source': self.source,
            'request_id': self.request_id,
            'previous_hash': self.previous_hash,
        }, sort_keys=True, ensure_ascii=False, default=str, separators=(',', ':')).encode('utf-8')

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Les entrées d'audit ne peuvent pas être modifiées.")
        self.timestamp = self.timestamp or timezone.now()
        # Verrou PostgreSQL commun à toute la chaîne ; fallback pour les outils
        # de vérification sans PostgreSQL, sans changer la cible officielle.
        with transaction.atomic():
            if connection.vendor == 'postgresql':
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_xact_lock(%s)', [87154231])
            previous = (
                type(self).objects.order_by('-id')
                .values_list('entry_hash', flat=True)
                .first()
            ) or ''
            self.previous_hash = previous
            self.entry_hash = hashlib.sha256(self._hash_content()).hexdigest()
            kwargs.setdefault('force_insert', True)
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Les entrées d'audit ne peuvent jamais être supprimées.")

    def verifier_chaine(self) -> bool:
        expected = hashlib.sha256(self._hash_content()).hexdigest()
        if expected != self.entry_hash:
            return False
        previous = (
            type(self).objects.filter(id__lt=self.id)
            .order_by('-id')
            .values_list('entry_hash', flat=True)
            .first()
        ) or ''
        return previous == self.previous_hash


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
