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


class ClesWebPush(models.Model):
    """Paire de clés VAPID de l'installation (notifications push, ``core.push``) : générée à la première
    utilisation par ``core.push.cles`` et conservée avec la base — une seule ligne (pk=1)."""
    cle_privee = models.CharField(max_length=100)      # 32 octets, base64url
    cle_publique = models.CharField(max_length=100)    # point non compressé (65 octets), base64url, remise au navigateur
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Clés Web Push'
        verbose_name_plural = 'Clés Web Push'


class AbonnementPush(models.Model):
    """Abonnement Web Push d'un navigateur (un appareil) d'un utilisateur — parent ou personnel —, qui peut en avoir
    plusieurs. Un abonnement que le service de notifications déclare expiré (404/410) est supprimé à l'envoi."""
    utilisateur = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='abonnements_push')
    endpoint = models.CharField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    navigateur = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    dernier_envoi = models.DateTimeField(null=True, blank=True)
    echecs = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Abonnement push'
        verbose_name_plural = 'Abonnements push'

    def __str__(self):
        return f"{self.utilisateur} — {self.navigateur or self.endpoint[:40]}"


class CampagneSms(models.Model):
    """Campagne SMS ciblée : un message libre (variables {eleve}, {classe}, {reste}, {etablissement}) envoyé à un
    public choisi — parents de l'école, de classes, redevables, parents d'élèves absents un jour donné, personnel.
    Chaque SMS de la campagne est une ligne de la file ``SmsSortant`` : le suivi (envoyés, échecs) en découle."""

    class Cible(models.TextChoices):
        PARENTS_TOUS = 'PARENTS_TOUS', "Parents de tous les élèves inscrits"
        PARENTS_CLASSES = 'PARENTS_CLASSES', "Parents des élèves de classes choisies"
        PARENTS_RETARD = 'PARENTS_RETARD', "Parents des élèves ayant un reste à payer"
        PARENTS_ABSENTS = 'PARENTS_ABSENTS', "Parents des élèves absents un jour donné"
        PERSONNEL = 'PERSONNEL', "Membres du personnel"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Envoyée le')
    etablissement = models.ForeignKey('etablissements.Etablissement', on_delete=models.CASCADE, related_name='campagnes_sms')
    annee_scolaire = models.ForeignKey('parametres.AnneeScolaire', on_delete=models.SET_NULL, null=True, blank=True)
    titre = models.CharField(max_length=120, verbose_name='Titre')
    message = models.TextField(verbose_name='Message (modèle)')
    cible = models.CharField(max_length=20, choices=Cible.choices)
    criteres = models.JSONField(default=dict, blank=True, help_text="Classes choisies, date d'absence…")
    nb_destinataires = models.PositiveIntegerField(default=0)
    envoyee_par = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='campagnes_sms')

    class Meta:
        verbose_name = 'Campagne SMS'
        verbose_name_plural = 'Campagnes SMS'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.titre} — {self.created_at:%d/%m/%Y}"

    def bilan(self):
        """{'envoyes', 'echecs', 'en_attente'} d'après la file."""
        compte = {s: 0 for s, _ in SmsSortant.Statut.choices}
        for ligne in self.sms.order_by().values('statut').annotate(n=models.Count('pk')):
            compte[ligne['statut']] = ligne['n']
        return {'envoyes': compte['ENVOYE'], 'echecs': compte['ECHEC'], 'en_attente': compte['EN_ATTENTE']}


class SmsSortant(models.Model):
    """File persistante des SMS à envoyer : rien ne se perd si l'application redémarre pendant l'envoi, les échecs
    passagers (passerelle injoignable, modem occupé) sont retentés, les échecs définitifs restent visibles."""

    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        ENVOYE = 'ENVOYE', 'Envoyé'
        ECHEC = 'ECHEC', 'Échec'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Mis en file le')
    numero = models.CharField(max_length=20, verbose_name='Destinataire')
    message = models.TextField(verbose_name='Message')
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.EN_ATTENTE)
    tentatives = models.PositiveSmallIntegerField(default=0)
    prochaine_tentative = models.DateTimeField(default=timezone.now)
    derniere_erreur = models.CharField(max_length=255, blank=True, default='')
    date_envoi = models.DateTimeField(null=True, blank=True)
    notification = models.ForeignKey(Notification, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='sms_sortants', help_text="Notification à marquer « SMS envoyé ».")
    campagne = models.ForeignKey(CampagneSms, on_delete=models.CASCADE, null=True, blank=True, related_name='sms')
    destinataire = models.CharField(max_length=120, blank=True, default='',
                                    help_text="Nom affiché dans le suivi d'une campagne (élève(s) ou agent).")

    class Meta:
        verbose_name = 'SMS sortant'
        verbose_name_plural = 'SMS sortants'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['statut', 'prochaine_tentative'], name='core_sms_statut_prochaine')]

    def __str__(self):
        return f"{self.numero} — {self.get_statut_display()}"
