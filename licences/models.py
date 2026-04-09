"""
Module Licences - Models
========================
YELEN SCHOOL v3.4 - Système de gestion des licences à 4 niveaux

Ce module gère le cœur commercial de l'application :
- Génération de clés HMAC-SHA256
- Activation online/offline avec binding serveur
- Feature flags par niveau (Starter/Standard/Premium/Réseau)
- Audit trail complet et alertes d'expiration

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 1.1 - Corrigée
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Récupérer le modèle User (compatible avec custom user model)
User = get_user_model()


# ═══════════════════════════════════════════════════════════════════
# MODÈLE DE BASE
# ═══════════════════════════════════════════════════════════════════

# Essayer d'importer BaseModel depuis core, sinon le définir localement
try:
    from core.models import BaseModel
except ImportError:
    # Si core.models n'existe pas encore, définir BaseModel ici temporairement
    # NOTE: Ce modèle devrait être déplacé vers core/models.py pour être partagé
    class BaseModel(models.Model):
        """Modèle abstrait de base pour tous les modèles de l'application."""
        
        id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False,
            verbose_name=_("Identifiant unique")
        )
        created_at = models.DateTimeField(
            auto_now_add=True,
            verbose_name=_("Date de création")
        )
        updated_at = models.DateTimeField(
            auto_now=True,
            verbose_name=_("Date de modification")
        )
        
        class Meta:
            abstract = True
            ordering = ['-created_at']


# ═══════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════

class TypeLicence(models.TextChoices):
    """Types de licences disponibles - ordre croissant de fonctionnalités."""
    STARTER = 'STARTER', _('🥉 Starter - Licence Découverte')
    STANDARD = 'STANDARD', _('🥈 Standard - Licence Essentielle')
    PREMIUM = 'PREMIUM', _('🥇 Premium - Licence Intégrale')
    RESEAU = 'RESEAU', _('🏆 Réseau - Licence Groupe')


class StatutLicence(models.TextChoices):
    """Statut d'une licence."""
    ACTIVE = 'ACTIVE', _('✅ Active')
    EXPIREE = 'EXPIREE', _('⏰ Expirée')
    REVOQUEE = 'REVOQUEE', _('🚫 Révoquée')
    EN_ATTENTE = 'EN_ATTENTE', _('⏳ En attente d\'activation')


# Feature Flags par niveau de licence (v3.4)
FEATURE_FLAGS: Dict[str, List[str]] = {
    # Fonctionnalités disponibles pour TOUS les niveaux
    'inscriptions': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    'enregistrement_eleves': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    'carte_identite_scolaire': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    'notes_bulletins': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    'presences': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    'finances_base': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    'certificats': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    'attestations': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    'autorisations_absence': ['STARTER', 'STANDARD', 'PREMIUM', 'RESEAU'],
    
    # Fonctionnalités STANDARD et supérieur
    'cursus_scolaire': ['STANDARD', 'PREMIUM', 'RESEAU'],
    'examens_officiels': ['STANDARD', 'PREMIUM', 'RESEAU'],
    'portail_parents': ['STANDARD', 'PREMIUM', 'RESEAU'],
    'gestion_personnel': ['STANDARD', 'PREMIUM', 'RESEAU'],
    'vacations': ['STANDARD', 'PREMIUM', 'RESEAU'],
    'statistiques_listes': ['STANDARD', 'PREMIUM', 'RESEAU'],
    
    # Fonctionnalités PREMIUM et supérieur
    'ia_predictive': ['PREMIUM', 'RESEAU'],
    'rapports_avances': ['PREMIUM', 'RESEAU'],
    
    # Fonctionnalité RESEAU uniquement
    'multi_etablissements': ['RESEAU'],
}


# Limites par type de licence
LIMITES_LICENCES: Dict[str, Dict[str, int]] = {
    'STARTER': {
        'max_eleves': 150,
        'max_enseignants': 15,
        'max_classes': 10,
        'prix_annuel_fcfa': 15000,  # ~17 USD
    },
    'STANDARD': {
        'max_eleves': 500,
        'max_enseignants': 50,
        'max_classes': 30,
        'prix_annuel_fcfa': 35000,  # ~40 USD
    },
    'PREMIUM': {
        'max_eleves': 2000,
        'max_enseignants': 200,
        'max_classes': 100,
        'prix_annuel_fcfa': 75000,  # ~86 USD
    },
    'RESEAU': {
        'max_eleves': 999999,  # Illimité
        'max_enseignants': 999999,
        'max_classes': 999999,
        'prix_annuel_fcfa': 0,  # Sur devis
    },
}


# ═══════════════════════════════════════════════════════════════════
# MODÈLE PRINCIPAL : LICENCE
# ═══════════════════════════════════════════════════════════════════

class LicenceManager(models.Manager):
    """Manager personnalisé pour les licences."""
    
    def generer_cle_licence(self, type_licence: str, etablissement_id: str) -> str:
        """
        Génère une clé de licence au format YELEN-XXXX-XXXX-XXXX.
        
        Args:
            type_licence: Type de licence (STARTER, STANDARD, PREMIUM, RESEAU)
            etablissement_id: UUID de l'établissement
            
        Returns:
            str: Clé de licence générée
        """
        # Créer une signature HMAC basée sur les données de la licence
        secret_key = settings.SECRET_KEY.encode('utf-8')
        message = f"{type_licence}:{etablissement_id}:{timezone.now().isoformat()}".encode('utf-8')
        signature = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
        
        # Prendre les 12 premiers caractères et formater
        code = signature[:12].upper()
        cle_formatee = f"YELEN-{code[:4]}-{code[4:8]}-{code[8:12]}"
        
        return cle_formatee
    
    def actives(self):
        """Retourne uniquement les licences actives et non expirées."""
        return self.filter(
            statut=StatutLicence.ACTIVE,
            date_expiration__gt=timezone.now()
        )
    
    def expirant_bientot(self, jours: int = 30):
        """Retourne les licences qui expirent dans N jours."""
        date_limite = timezone.now() + timedelta(days=jours)
        return self.filter(
            statut=StatutLicence.ACTIVE,
            date_expiration__lte=date_limite,
            date_expiration__gt=timezone.now()
        )


class Licence(BaseModel):
    """
    Modèle principal de gestion des licences.
    
    Chaque établissement possède UNE licence qui détermine
    les fonctionnalités accessibles via le système de Feature Flags.
    """
    
    # Référence établissement
    # NOTE: Si l'app etablissements n'existe pas encore, commentez cette ligne
    # et décommentez la ligne suivante (etablissement_id)
    etablissement = models.OneToOneField(
        'etablissements.Etablissement',
        on_delete=models.PROTECT,
        related_name='licence',
        verbose_name=_("Établissement"),
        help_text=_("Établissement associé à cette licence")
    )
    
    # ALTERNATIVE SI etablissements n'existe pas encore :
    # etablissement_id = models.UUIDField(
    #     verbose_name=_("ID Établissement (temporaire)"),
    #     help_text=_("Sera remplacé par FK vers etablissements.Etablissement"),
    #     unique=True
    # )
    
    # Informations de la licence
    cle_licence = models.CharField(
        max_length=20,  # Format: YELEN-XXXX-XXXX-XXXX (20 chars)
        unique=True,
        editable=False,
        verbose_name=_("Clé de licence"),
        help_text=_("Clé unique générée automatiquement")
    )
    
    type_licence = models.CharField(
        max_length=10,
        choices=TypeLicence.choices,
        default=TypeLicence.STARTER,
        verbose_name=_("Type de licence")
    )
    
    statut = models.CharField(
        max_length=15,
        choices=StatutLicence.choices,
        default=StatutLicence.EN_ATTENTE,
        verbose_name=_("Statut")
    )
    
    # Dates de validité
    date_activation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date d'activation"),
        help_text=_("Date de première activation de la licence")
    )
    
    date_expiration = models.DateField(
        verbose_name=_("Date d'expiration"),
        help_text=_("Date de fin de validité de la licence")
    )
    
    # Signature HMAC pour vérification d'intégrité
    signature_hmac = models.CharField(
        max_length=64,  # SHA-256 en hexadécimal
        editable=False,
        verbose_name=_("Signature HMAC"),
        help_text=_("Signature cryptographique pour empêcher la falsification")
    )
    
    # Métadonnées
    notes_interne = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Notes internes"),
        help_text=_("Remarques internes (non visibles par l'établissement)")
    )
    
    derniere_verification = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Dernière vérification"),
        help_text=_("Date de la dernière vérification de validité")
    )
    
    # Manager personnalisé
    objects = LicenceManager()
    
    class Meta:
        verbose_name = _("Licence")
        verbose_name_plural = _("Licences")
        ordering = ['-date_activation']
        indexes = [
            models.Index(fields=['cle_licence']),
            models.Index(fields=['statut', 'date_expiration']),
        ]
    
    def __str__(self) -> str:
        return f"{self.cle_licence} - {self.get_type_licence_display()}"
    
    def save(self, *args, **kwargs):
        """Override save pour générer la clé et la signature HMAC."""
        # Générer la clé de licence si elle n'existe pas
        if not self.cle_licence:
            # Récupérer l'ID de l'établissement
            if hasattr(self, 'etablissement') and self.etablissement:
                etablissement_id = str(self.etablissement.id)
            else:
                # Si utilisation de etablissement_id temporaire
                etablissement_id = str(self.etablissement_id)
            
            self.cle_licence = Licence.objects.generer_cle_licence(
                type_licence=self.type_licence,
                etablissement_id=etablissement_id
            )
        
        # Générer la signature HMAC
        self._generer_signature_hmac()
        
        # Vérifier les limites
        self._verifier_limites()
        
        super().save(*args, **kwargs)
    
    def _generer_signature_hmac(self) -> None:
        """Génère la signature HMAC pour cette licence."""
        secret_key = settings.SECRET_KEY.encode('utf-8')
        message = (
            f"{self.cle_licence}:"
            f"{self.type_licence}:"
            f"{self.date_expiration.isoformat()}"
        ).encode('utf-8')
        
        self.signature_hmac = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
    
    def verifier_signature(self) -> bool:
        """
        Vérifie l'intégrité de la licence via sa signature HMAC.
        
        Returns:
            bool: True si la signature est valide
        """
        signature_calculee = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            (
                f"{self.cle_licence}:"
                f"{self.type_licence}:"
                f"{self.date_expiration.isoformat()}"
            ).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(self.signature_hmac, signature_calculee)
    
    def _verifier_limites(self) -> None:
        """Vérifie que l'établissement respecte les limites de la licence."""
        limites = LIMITES_LICENCES[self.type_licence]
        
        # Ces vérifications seront complétées quand les modules élèves/personnel existeront
        # Pour l'instant, on définit juste la structure
        pass
    
    def est_active(self) -> bool:
        """
        Vérifie si la licence est active et valide.
        
        Returns:
            bool: True si la licence est active et non expirée
        """
        return (
            self.statut == StatutLicence.ACTIVE
            and self.date_expiration >= timezone.now().date()
            and self.verifier_signature()
        )
    
    def jours_restants(self) -> int:
        """
        Calcule le nombre de jours restants avant expiration.
        
        Returns:
            int: Nombre de jours (peut être négatif si expirée)
        """
        delta = self.date_expiration - timezone.now().date()
        return delta.days
    
    def peut_utiliser_feature(self, feature_name: str) -> bool:
        """
        Vérifie si cette licence permet d'utiliser une fonctionnalité.
        
        Args:
            feature_name: Nom de la fonctionnalité (ex: 'cursus_scolaire')
            
        Returns:
            bool: True si la fonctionnalité est accessible
        """
        if not self.est_active():
            return False
        
        feature_levels = FEATURE_FLAGS.get(feature_name, [])
        return self.type_licence in feature_levels
    
    def get_features_disponibles(self) -> List[str]:
        """
        Retourne la liste des fonctionnalités disponibles pour cette licence.
        
        Returns:
            List[str]: Liste des noms de features accessibles
        """
        if not self.est_active():
            return []
        
        return [
            feature_name
            for feature_name, levels in FEATURE_FLAGS.items()
            if self.type_licence in levels
        ]
    
    def activer(self) -> None:
        """Active la licence (appelée lors de la première activation)."""
        if self.statut == StatutLicence.EN_ATTENTE:
            self.statut = StatutLicence.ACTIVE
            self.date_activation = timezone.now()
            self.save()
    
    def revoquer(self, raison: str = "") -> None:
        """
        Révoque la licence.
        
        Args:
            raison: Raison de la révocation
        """
        self.statut = StatutLicence.REVOQUEE
        if raison:
            self.notes_interne += f"\n[{timezone.now()}] Révoquée: {raison}"
        self.save()
    
    def renouveler(self, duree_jours: int = 365) -> None:
        """
        Renouvelle la licence pour une durée donnée.
        
        Args:
            duree_jours: Durée du renouvellement en jours (par défaut 1 an)
        """
        nouvelle_expiration = timezone.now().date() + timedelta(days=duree_jours)
        self.date_expiration = nouvelle_expiration
        
        if self.statut == StatutLicence.EXPIREE:
            self.statut = StatutLicence.ACTIVE
        
        self.save()


# ═══════════════════════════════════════════════════════════════════
# MODÈLE : ACTIVATION DE LICENCE (Binding serveur)
# ═══════════════════════════════════════════════════════════════════

class LicenceActivation(BaseModel):
    """
    Enregistre les activations de licence avec binding au serveur.
    
    Permet l'activation online et offline avec vérification de l'unicité
    du serveur (MAC address + hostname).
    """
    
    licence = models.ForeignKey(
        Licence,
        on_delete=models.CASCADE,
        related_name='activations',
        verbose_name=_("Licence")
    )
    
    # Informations du serveur
    mac_address = models.CharField(
        max_length=17,  # Format: XX:XX:XX:XX:XX:XX
        verbose_name=_("Adresse MAC"),
        help_text=_("Adresse MAC unique du serveur")
    )
    
    hostname = models.CharField(
        max_length=255,
        verbose_name=_("Nom d'hôte"),
        help_text=_("Nom DNS du serveur")
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Adresse IP"),
        help_text=_("Adresse IP du serveur au moment de l'activation")
    )
    
    # Type d'activation
    mode_activation = models.CharField(
        max_length=10,
        choices=[
            ('ONLINE', _('🌐 Online - Activation en ligne')),
            ('OFFLINE', _('📴 Offline - Activation par fichier'))
        ],
        default='ONLINE',
        verbose_name=_("Mode d'activation")
    )
    
    # Métadonnées
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name=_("User Agent"),
        help_text=_("Informations sur le navigateur/système")
    )
    
    est_active = models.BooleanField(
        default=True,
        verbose_name=_("Activation active"),
        help_text=_("False si l'activation a été révoquée")
    )
    
    date_revocation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de révocation")
    )
    
    class Meta:
        verbose_name = _("Activation de licence")
        verbose_name_plural = _("Activations de licence")
        ordering = ['-created_at']
        unique_together = [['licence', 'mac_address', 'hostname']]
        indexes = [
            models.Index(fields=['licence', 'est_active']),
            models.Index(fields=['mac_address', 'hostname']),
        ]
    
    def __str__(self) -> str:
        return f"{self.licence.cle_licence} - {self.hostname} ({self.mac_address})"
    
    def clean(self):
        """Validation personnalisée."""
        # Vérifier qu'une seule activation est active par licence
        if self.est_active:
            activations_actives = LicenceActivation.objects.filter(
                licence=self.licence,
                est_active=True
            ).exclude(pk=self.pk)
            
            if activations_actives.exists():
                raise ValidationError(
                    _("Cette licence est déjà activée sur un autre serveur. "
                      "Veuillez d'abord révoquer l'activation existante.")
                )
    
    def revoquer(self) -> None:
        """Révoque cette activation."""
        self.est_active = False
        self.date_revocation = timezone.now()
        self.save()
    
    def get_empreinte_serveur(self) -> str:
        """
        Génère une empreinte unique du serveur.
        
        Returns:
            str: Hash SHA-256 de MAC + hostname
        """
        empreinte = f"{self.mac_address}:{self.hostname}".encode('utf-8')
        return hashlib.sha256(empreinte).hexdigest()


# ═══════════════════════════════════════════════════════════════════
# MODÈLE : AUDIT LOG (Journal immuable)
# ═══════════════════════════════════════════════════════════════════

class LicenceAuditLog(BaseModel):
    """
    Journal d'audit immuable des actions sur les licences.
    
    Append-only : les entrées ne peuvent jamais être modifiées ou supprimées.
    Chaînage cryptographique pour détecter les tentatives de falsification.
    """
    
    licence = models.ForeignKey(
        Licence,
        on_delete=models.PROTECT,  # Empêcher la suppression des licences avec historique
        related_name='audit_logs',
        verbose_name=_("Licence")
    )
    
    # Informations de l'action
    action = models.CharField(
        max_length=50,
        choices=[
            ('CREATION', _('🆕 Création de licence')),
            ('ACTIVATION', _('✅ Activation')),
            ('RENOUVELLEMENT', _('🔄 Renouvellement')),
            ('REVOCATION', _('🚫 Révocation')),
            ('MODIFICATION', _('✏️ Modification')),
            ('VERIFICATION', _('🔍 Vérification de validité')),
            ('EXPIRATION', _('⏰ Expiration')),
            ('TENTATIVE_FRAUDE', _('⚠️ Tentative de fraude détectée')),
        ],
        verbose_name=_("Action")
    )
    
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Détails de l'action effectuée")
    )
    
    # Acteur (utilisateur ou système)
    acteur_user = models.ForeignKey(
        User,  # Utilise get_user_model()
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Utilisateur"),
        help_text=_("Utilisateur ayant effectué l'action (null si système)")
    )
    
    acteur_systeme = models.BooleanField(
        default=False,
        verbose_name=_("Action système"),
        help_text=_("True si l'action a été effectuée automatiquement")
    )
    
    # Contexte technique
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Adresse IP")
    )
    
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name=_("User Agent")
    )
    
    # Chaînage cryptographique
    hash_precedent = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name=_("Hash de l'entrée précédente"),
        help_text=_("Lien vers l'entrée précédente pour détecter les modifications")
    )
    
    hash_actuel = models.CharField(
        max_length=64,
        editable=False,
        verbose_name=_("Hash de cette entrée")
    )
    
    class Meta:
        verbose_name = _("Entrée d'audit")
        verbose_name_plural = _("Journal d'audit")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['licence', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
        # Empêcher toute modification après création
        permissions = [
            ("view_audit_log", "Peut consulter le journal d'audit"),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_action_display()} - {self.licence.cle_licence} - {self.created_at}"
    
    def save(self, *args, **kwargs):
        """Override save pour générer le hash avec chaînage."""
        # Première sauvegarde uniquement (append-only)
        if self.pk is not None:
            raise ValidationError(
                _("Les entrées d'audit ne peuvent pas être modifiées après création.")
            )
        
        # Sauvegarder d'abord pour obtenir created_at
        super().save(*args, **kwargs)
        
        # Maintenant, récupérer le hash de la dernière entrée et générer le hash
        # Exclure l'instance actuelle de la recherche
        derniere_entree = LicenceAuditLog.objects.filter(
            licence=self.licence
        ).exclude(pk=self.pk).order_by('-created_at').first()
        
        if derniere_entree:
            self.hash_precedent = derniere_entree.hash_actuel
        
        # Générer le hash de cette entrée (maintenant created_at est disponible)
        self._generer_hash()
        
        # Sauvegarder à nouveau avec le hash généré
        super().save(update_fields=['hash_precedent', 'hash_actuel'])
    
    def _generer_hash(self) -> None:
        """Génère le hash SHA-256 de cette entrée."""
        contenu = (
            f"{self.licence.cle_licence}:"
            f"{self.action}:"
            f"{self.description}:"
            f"{self.created_at.isoformat()}:"
            f"{self.hash_precedent}"
        ).encode('utf-8')
        
        self.hash_actuel = hashlib.sha256(contenu).hexdigest()
    
    def verifier_chaine(self) -> bool:
        """
        Vérifie l'intégrité de la chaîne d'audit.
        
        Returns:
            bool: True si la chaîne est intacte
        """
        # Recalculer le hash
        contenu = (
            f"{self.licence.cle_licence}:"
            f"{self.action}:"
            f"{self.description}:"
            f"{self.created_at.isoformat()}:"
            f"{self.hash_precedent}"
        ).encode('utf-8')
        
        hash_attendu = hashlib.sha256(contenu).hexdigest()
        return self.hash_actuel == hash_attendu
    
    def delete(self, *args, **kwargs):
        """Empêcher la suppression."""
        raise ValidationError(
            _("Les entrées d'audit ne peuvent jamais être supprimées.")
        )


# ═══════════════════════════════════════════════════════════════════
# MODÈLE : ALERTES D'EXPIRATION
# ═══════════════════════════════════════════════════════════════════

class LicenceAlert(BaseModel):
    """
    Alertes automatiques d'expiration de licence.
    
    Génère des notifications à J-30, J-15, J-7 et J-1 avant expiration.
    """
    
    licence = models.ForeignKey(
        Licence,
        on_delete=models.CASCADE,
        related_name='alertes',
        verbose_name=_("Licence")
    )
    
    type_alerte = models.CharField(
        max_length=10,
        choices=[
            ('J-30', _('⚠️ Expiration dans 30 jours')),
            ('J-15', _('⚠️ Expiration dans 15 jours')),
            ('J-7', _('🚨 Expiration dans 7 jours')),
            ('J-1', _('🚨 Expiration DEMAIN')),
            ('EXPIREE', _('🔴 Licence expirée')),
        ],
        verbose_name=_("Type d'alerte")
    )
    
    date_alerte = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Date de l'alerte")
    )
    
    envoyee = models.BooleanField(
        default=False,
        verbose_name=_("Alerte envoyée"),
        help_text=_("True si l'email de notification a été envoyé")
    )
    
    date_envoi = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date d'envoi de l'email")
    )
    
    destinataires = models.JSONField(
        default=list,
        verbose_name=_("Destinataires"),
        help_text=_("Liste des emails ayant reçu l'alerte")
    )
    
    class Meta:
        verbose_name = _("Alerte de licence")
        verbose_name_plural = _("Alertes de licence")
        ordering = ['-date_alerte']
        indexes = [
            models.Index(fields=['licence', 'envoyee']),
            models.Index(fields=['type_alerte', 'date_alerte']),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_type_alerte_display()} - {self.licence.cle_licence}"
    
    def marquer_comme_envoyee(self, destinataires: List[str]) -> None:
        """
        Marque l'alerte comme envoyée.
        
        Args:
            destinataires: Liste des adresses email destinataires
        """
        self.envoyee = True
        self.date_envoi = timezone.now()
        self.destinataires = destinataires
        self.save()