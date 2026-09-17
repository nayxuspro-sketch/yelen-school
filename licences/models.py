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
from datetime import date, datetime, time, timedelta
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
    
    def _get_signing_key(self) -> bytes:
        """Retourne la clé de signature dédiée (P1) ou fallback SECRET_KEY."""
        # P1 : LICENCE_SIGNING_KEY dédiée, sinon SECRET_KEY (transition)
        key = getattr(settings, 'LICENCE_SIGNING_KEY', '') or settings.SECRET_KEY
        return key.encode('utf-8')

    def generer_cle_licence(self, type_licence: str, etablissement_id: str) -> str:
        """
        Génère une clé de licence au format YELEN-XXXX-XXXX-XXXX.
        
        Args:
            type_licence: Type de licence (STARTER, STANDARD, PREMIUM, RESEAU)
            etablissement_id: UUID de l'établissement
            
        Returns:
            str: Clé de licence générée
        """
        # P1 : utilise LICENCE_SIGNING_KEY dédiée
        secret_key = self._get_signing_key()
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
    
    # Signature HMAC pour vérification d'intégrité (legacy, v1/v2)
    signature_hmac = models.CharField(
        max_length=64,  # SHA-256 en hexadécimal
        editable=False,
        verbose_name=_("Signature HMAC"),
        help_text=_("Signature cryptographique legacy (HMAC-SHA256) — conservée pour transition")
    )
    # P1 — Signature asymétrique Ed25519 (clé privée éditeur, publique dans app)
    signature_ed25519 = models.CharField(
        max_length=128,  # 64 bytes en hex (128 chars) ou base64 88 chars
        blank=True,
        default='',
        editable=False,
        verbose_name=_("Signature Ed25519"),
        help_text=_("Signature asymétrique Ed25519 — clé privée chez éditeur, publique dans app")
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

    # ── P1 — Phone-home heartbeat + bail offline fenêtre décroissante ──────
    dernier_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Dernier heartbeat"),
        help_text=_("Date du dernier heartbeat réussi vers serveur éditeur")
    )
    bail_offline_expire_le = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Bail offline expire le"),
        help_text=_("Date d'expiration du bail offline (fenêtre décroissante)")
    )
    heartbeat_failures = models.IntegerField(
        default=0,
        verbose_name=_("Échecs heartbeat consécutifs"),
        help_text=_("Nombre d'échecs heartbeat consécutifs")
    )
    heartbeat_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Dernier payload heartbeat"),
        help_text=_("Payload signé du dernier heartbeat (debug)")
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
    
    @staticmethod
    def _fmt_datetime(dt) -> str:
        """Formatage canonique (UTC, secondes au millième) d'un DateTimeField
        pour la signature HMAC.

        Nécessaire car l'isoformat() d'un datetime en mémoire (naïf ou dans un
        fuseau donné) diffère de celui du même instant relus depuis la base
        (UTC, microsecondes) : la signature devrait alors diverger. Le format
        canonique en UTC élimine toute ambiguïté.
        """
        if dt is None:
            return ''
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, time.min)
        if timezone.is_naive(dt):
            # Même convention que Django au save : datetime naïf interprété
            # dans le fuseau par défaut de l'application.
            dt = timezone.make_aware(dt)
        return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    def _message_signature_v2(self) -> str:
        """Message couvert par la signature HMAC — format v2 (complet).

        v2 : cle:type:statut:etablissement_id:date_activation:date_expiration

        Couvre le statut (une révocation locale invalide la signature),
        l'établissement rattaché (anti-transfert de licence) et la date
        d'activation (anti-recalage).
        """
        date_act = self._fmt_datetime(self.date_activation)
        etab_id = str(self.etablissement_id) if self.etablissement_id else ''
        return (
            f"{self.cle_licence}:{self.type_licence}:{self.statut}:"
            f"{etab_id}:{date_act}:{self.date_expiration.isoformat()}"
        )

    def _message_signature_v1(self) -> str:
        """Message du format v1 (légacy) : cle:type:date_expiration."""
        return (
            f"{self.cle_licence}:{self.type_licence}:"
            f"{self.date_expiration.isoformat()}"
        )

    def _get_signing_key_bytes(self) -> bytes:
        """P1 : clé dédiée LICENCE_SIGNING_KEY ou fallback SECRET_KEY."""
        key = getattr(settings, 'LICENCE_SIGNING_KEY', '') or settings.SECRET_KEY
        return key.encode('utf-8')

    def _signer(self, message: str) -> str:
        """Calcule le HMAC-SHA256 du message avec la clé dédiée (P1)."""
        return hmac.new(
            self._get_signing_key_bytes(),
            message.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

    def _generer_signature_hmac(self) -> None:
        """Génère la signature HMAC (format v2) pour cette licence."""
        self.signature_hmac = self._signer(self._message_signature_v2())
        # P1 : si clé privée Ed25519 dispo (éditeur), génère aussi signature asymétrique
        try:
            self._generer_signature_ed25519()
        except Exception:
            # En prod école, pas de clé privée → on garde seulement HMAC
            # Si signature_ed25519 déjà présente (licence importée), on la conserve
            if not self.signature_ed25519:
                self.signature_ed25519 = ''

    # ── P1 — Ed25519 ──────────────────────────────────────────────────
    def _load_private_key(self):
        """Charge la clé privée Ed25519 depuis settings (éditeur uniquement)."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        import base64
        priv_hex = getattr(settings, 'LICENCE_PRIVATE_KEY', '') or ''
        if not priv_hex:
            return None
        # Support hex 64 chars (32 bytes) ou base64
        try:
            if len(priv_hex) == 64 and all(c in '0123456789abcdefABCDEF' for c in priv_hex):
                raw = bytes.fromhex(priv_hex)
            else:
                # base64
                raw = base64.b64decode(priv_hex)
            return Ed25519PrivateKey.from_private_bytes(raw)
        except Exception:
            return None

    def _load_public_key(self):
        """Charge la clé publique Ed25519 depuis settings (app)."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        import base64
        pub_hex = getattr(settings, 'LICENCE_PUBLIC_KEY', '') or ''
        if not pub_hex:
            return None
        try:
            if len(pub_hex) == 64 and all(c in '0123456789abcdefABCDEF' for c in pub_hex):
                raw = bytes.fromhex(pub_hex)
            else:
                raw = base64.b64decode(pub_hex)
            return Ed25519PublicKey.from_public_bytes(raw)
        except Exception:
            return None

    def _generer_signature_ed25519(self) -> None:
        """Génère la signature Ed25519 du message v2 (si clé privée dispo)."""
        priv = self._load_private_key()
        if priv is None:
            return
        message = self._message_signature_v2().encode('utf-8')
        sig = priv.sign(message)
        # Stockage hex (128 chars) pour lisibilité
        self.signature_ed25519 = sig.hex()

    def verifier_signature_ed25519(self) -> bool:
        """Vérifie la signature Ed25519 avec la clé publique."""
        if not self.signature_ed25519:
            return False
        pub = self._load_public_key()
        if pub is None:
            return False
        try:
            import binascii
            # Support hex ou base64
            sig_str = self.signature_ed25519.strip()
            try:
                sig_bytes = bytes.fromhex(sig_str)
            except ValueError:
                import base64
                sig_bytes = base64.b64decode(sig_str)
            message = self._message_signature_v2().encode('utf-8')
            pub.verify(sig_bytes, message)
            return True
        except Exception:
            return False

    def verifier_signature(self) -> bool:
        """
        Vérifie l'intégrité de la licence.

        Ordre P1 :
        1. Ed25519 si signature_ed25519 présente + LICENCE_PUBLIC_KEY configurée
           → clé privée jamais dans l'app, forger impossible même avec .env/base
        2. Fallback HMAC v2/v1 avec LICENCE_SIGNING_KEY (transition)

        Returns:
            bool: True si signature valide
        """
        # 1. Ed25519 prioritaire (P1)
        if self.signature_ed25519:
            if self.verifier_signature_ed25519():
                return True
            # Si Ed25519 présente mais invalide → fraude, on ne fallback pas vers HMAC
            # (évite downgrade attack) sauf si pas de clé publique configurée (mode dev)
            if getattr(settings, 'LICENCE_PUBLIC_KEY', ''):
                return False

        # 2. Fallback HMAC legacy (transition)
        stockee = self.signature_hmac or ''
        for message in (self._message_signature_v2(), self._message_signature_v1()):
            if hmac.compare_digest(stockee, self._signer(message)):
                return True
        return False
    
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

    # ── P1 — Heartbeat / bail offline fenêtre décroissante ───────────────
    def _get_heartbeat_signing_key(self) -> bytes:
        return self._get_signing_key_bytes()

    def generate_heartbeat_payload(self) -> dict:
        """Génère le payload heartbeat signé à envoyer au serveur éditeur."""
        now = timezone.now()
        payload = {
            'cle_licence': self.cle_licence,
            'type_licence': self.type_licence,
            'statut': self.statut,
            'etablissement_id': str(self.etablissement_id) if self.etablissement_id else '',
            'timestamp': now.isoformat(),
            'jours_restants': self.jours_restants(),
            'signature_ed25519': self.signature_ed25519,
        }
        # Signer le payload avec HMAC (clé dédiée) + Ed25519 si dispo
        message = f"{payload['cle_licence']}:{payload['timestamp']}:{payload['etablissement_id']}".encode('utf-8')
        payload['hmac'] = hmac.new(self._get_heartbeat_signing_key(), message, hashlib.sha256).hexdigest()
        # Ed25519 si clé privée dispo (éditeur side, normalement pas en prod école)
        try:
            priv = self._load_private_key()
            if priv:
                sig = priv.sign(message)
                payload['ed25519'] = sig.hex()
        except Exception:
            pass
        return payload

    def record_heartbeat_success(self) -> None:
        """Appelé quand heartbeat réussi : reset failures, étend bail."""
        from django.conf import settings as _s
        now = timezone.now()
        max_days = getattr(_s, 'LICENCE_OFFLINE_MAX_DAYS', 30)
        self.dernier_heartbeat = now
        self.heartbeat_failures = 0
        # Bail offline = maintenant + MAX_DAYS
        self.bail_offline_expire_le = now + timedelta(days=max_days)
        # Sauvegarde partielle pour éviter de regénérer signature si inchangée
        # mais on doit passer par save() pour updated_at ; on utilise update_fields
        # et on regénère signature via save() complet si besoin — ici on fait update
        # direct pour ne pas toucher signature.
        Licence.objects.filter(pk=self.pk).update(
            dernier_heartbeat=self.dernier_heartbeat,
            bail_offline_expire_le=self.bail_offline_expire_le,
            heartbeat_failures=0,
        )
        # Refresh instance
        self.refresh_from_db(fields=['dernier_heartbeat', 'bail_offline_expire_le', 'heartbeat_failures'])

    def record_heartbeat_failure(self) -> None:
        """Appelé quand heartbeat échoue : incrémente failures, réduit bail (fenêtre décroissante)."""
        from django.conf import settings as _s
        now = timezone.now()
        grace_days = getattr(_s, 'LICENCE_OFFLINE_GRACE_DAYS', 7)
        max_days = getattr(_s, 'LICENCE_OFFLINE_MAX_DAYS', 30)
        # Incrément
        self.heartbeat_failures = (self.heartbeat_failures or 0) + 1
        # Fenêtre décroissante : à chaque échec, on réduit le bail restant
        # Formule : bail_restant = max(grace, max - failures * decay)
        # decay = (max - grace) / 10 par exemple → après 10 échecs, on est à grace
        decay_step = max(1, (max_days - grace_days) // 10) if max_days > grace_days else 1
        remaining_bail_days = max(grace_days, max_days - self.heartbeat_failures * decay_step)
        # Si bail déjà expiré ou non défini, on le met à now + remaining
        # Sinon, on le réduit si nécessaire (on ne l'étend jamais sur échec)
        new_bail = now + timedelta(days=remaining_bail_days)
        if self.bail_offline_expire_le is None or self.bail_offline_expire_le > new_bail:
            self.bail_offline_expire_le = new_bail
        # Si premier heartbeat jamais réussi, on initialise dernier_heartbeat à None, bail à grace
        if self.dernier_heartbeat is None and self.bail_offline_expire_le is None:
            self.bail_offline_expire_le = now + timedelta(days=grace_days)
        Licence.objects.filter(pk=self.pk).update(
            heartbeat_failures=self.heartbeat_failures,
            bail_offline_expire_le=self.bail_offline_expire_le,
        )
        self.refresh_from_db(fields=['heartbeat_failures', 'bail_offline_expire_le'])

    def is_bail_offline_expired(self) -> bool:
        """True si le bail offline est expiré (plus de heartbeat depuis trop longtemps)."""
        if not self.bail_offline_expire_le:
            return False  # pas encore de bail défini → tolérant
        return timezone.now() > self.bail_offline_expire_le

    def get_bail_jours_restants(self) -> Optional[int]:
        """Jours restants avant expiration du bail offline."""
        if not self.bail_offline_expire_le:
            return None
        delta = self.bail_offline_expire_le - timezone.now()
        return max(0, delta.days)

    def is_heartbeat_required(self) -> bool:
        """True si un heartbeat est dû (intervalle dépassé)."""
        from django.conf import settings as _s
        interval_h = getattr(_s, 'LICENCE_HEARTBEAT_INTERVAL_HOURS', 24)
        if not getattr(_s, 'LICENCE_HEARTBEAT_URL', ''):
            return False  # pas de serveur configuré
        if not self.dernier_heartbeat:
            return True
        return timezone.now() >= self.dernier_heartbeat + timedelta(hours=interval_h)

    def verify_heartbeat_response(self, response_data: dict) -> bool:
        """Vérifie la réponse heartbeat du serveur éditeur (signature Ed25519 si configurée)."""
        # Réponse attendue : {'statut': 'ACTIVE'|'REVOQUEE', 'timestamp': ..., 'signature': ..., 'ed25519': ...}
        # Vérif HMAC
        try:
            cle = response_data.get('cle_licence', '')
            if cle != self.cle_licence:
                return False
            ts = response_data.get('timestamp', '')
            statut_resp = response_data.get('statut', '')
            hmac_resp = response_data.get('hmac', '')
            if not hmac_resp:
                # Si pas de HMAC, on tolère si Ed25519 valide
                pass
            else:
                message = f"{cle}:{statut_resp}:{ts}".encode('utf-8')
                expected = hmac.new(self._get_heartbeat_signing_key(), message, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expected, hmac_resp):
                    # Tentative de downgrade ? On vérifie Ed25519 si présent
                    if not response_data.get('ed25519'):
                        return False
            # Vérif Ed25519 si clé publique configurée et signature fournie
            ed_sig = response_data.get('ed25519', '')
            if ed_sig and getattr(settings, 'LICENCE_PUBLIC_KEY', ''):
                pub = self._load_public_key()
                if pub:
                    try:
                        sig_bytes = bytes.fromhex(ed_sig) if len(ed_sig) == 128 else __import__('base64').b64decode(ed_sig)
                        msg = f"{cle}:{statut_resp}:{ts}".encode('utf-8')
                        pub.verify(sig_bytes, msg)
                    except Exception:
                        return False
            return True
        except Exception:
            return False


# ═══════════════════════════════════════════════════════════════════
# MODÈLE : ACTIVATION DE LICENCE (Binding serveur)
# ═══════════════════════════════════════════════════════════════════

class LicenceActivation(BaseModel):
    """
    Enregistre les activations de licence avec binding au serveur — P1 multi-attributs.

    P1 : empreinte signée (HMAC + Ed25519 si dispo), 1 active/licence garantie par
    contrainte DB partielle (UniqueConstraint condition est_active=True), et
    multi-attributs (MAC, hostname, CPU ID, disk serial, system UUID, OS).
    """

    licence = models.ForeignKey(
        Licence,
        on_delete=models.CASCADE,
        related_name='activations',
        verbose_name=_("Licence")
    )

    # Informations du serveur — base
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

    # P1 — multi-attributs pour binding robuste
    cpu_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name=_("CPU ID"),
        help_text=_("Identifiant CPU (optionnel, renforce binding)")
    )
    disk_serial = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name=_("Numéro série disque"),
        help_text=_("Numéro de série disque système")
    )
    system_uuid = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name=_("System UUID"),
        help_text=_("UUID système (SMBIOS)")
    )
    os_info = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name=_("OS info"),
        help_text=_("Informations OS / platform")
    )
    platform_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Données plateforme"),
        help_text=_("Attributs additionnels (arch, machine, etc.)")
    )
    # Empreinte canonique (hash SHA256 de tous les attributs triés)
    machine_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name=_("Empreinte machine"),
        help_text=_("SHA256 canonique de MAC+hostname+CPU+disk+UUID+OS")
    )
    # Signature de l'empreinte (HMAC avec LICENCE_SIGNING_KEY, + Ed25519 si clé privée dispo)
    fingerprint_signature = models.CharField(
        max_length=256,
        blank=True,
        default='',
        verbose_name=_("Signature empreinte"),
        help_text=_("HMAC-SHA256 de l'empreinte, ou Ed25519 hex")
    )
    fingerprint_signature_ed25519 = models.CharField(
        max_length=128,
        blank=True,
        default='',
        verbose_name=_("Signature empreinte Ed25519"),
        help_text=_("Signature Ed25519 de l'empreinte (clé privée éditeur)")
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
        # P1 : unique_together legacy conservé pour compat, mais vraie garantie = partial unique index
        unique_together = [['licence', 'mac_address', 'hostname']]
        constraints = [
            # 1 active/licence garantie DB (Postgres & SQLite supportent condition)
            models.UniqueConstraint(
                fields=['licence'],
                condition=models.Q(est_active=True),
                name='unique_active_activation_per_licence',
            ),
        ]
        indexes = [
            models.Index(fields=['licence', 'est_active']),
            models.Index(fields=['mac_address', 'hostname']),
            models.Index(fields=['machine_fingerprint']),
        ]

    def __str__(self) -> str:
        return f"{self.licence.cle_licence} - {self.hostname} ({self.mac_address})"

    # ── P1 — génération empreinte multi-attributs ────────────────────────
    @staticmethod
    def _canonical_fingerprint_payload(attrs: dict) -> str:
        """Construit la chaîne canonique triée pour hash."""
        # On normalise : lower, strip, tri des clés
        parts = []
        for k in sorted(attrs.keys()):
            v = str(attrs.get(k, '')).strip().lower()
            if v:
                parts.append(f"{k}={v}")
        return "|".join(parts)

    @staticmethod
    def generate_fingerprint(attrs: dict) -> str:
        """
        Génère l'empreinte SHA256 canonique à partir d'un dict d'attributs.

        attrs attendu : mac_address, hostname, cpu_id, disk_serial,
                        system_uuid, os_info, etc.
        """
        canonical = LicenceActivation._canonical_fingerprint_payload(attrs)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def build_attrs_dict(self) -> dict:
        """Retourne le dict d'attributs actuels pour empreinte."""
        return {
            'mac_address': self.mac_address or '',
            'hostname': self.hostname or '',
            'cpu_id': self.cpu_id or '',
            'disk_serial': self.disk_serial or '',
            'system_uuid': self.system_uuid or '',
            'os_info': self.os_info or '',
            'ip_address': str(self.ip_address) if self.ip_address else '',
            # platform_data peut contenir arch, etc. — on l'aplatit
            **{f"platform_{k}": str(v) for k, v in (self.platform_data or {}).items()},
        }

    def compute_and_sign_fingerprint(self) -> None:
        """Calcule machine_fingerprint + signatures HMAC/Ed25519."""
        attrs = self.build_attrs_dict()
        fp = self.generate_fingerprint(attrs)
        self.machine_fingerprint = fp

        # HMAC avec LICENCE_SIGNING_KEY dédiée
        try:
            key = getattr(settings, 'LICENCE_SIGNING_KEY', '') or settings.SECRET_KEY
            sig_hmac = hmac.new(key.encode('utf-8'), fp.encode('utf-8'), hashlib.sha256).hexdigest()
            self.fingerprint_signature = sig_hmac
        except Exception:
            self.fingerprint_signature = ''

        # Ed25519 si clé privée dispo (éditeur)
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            import base64
            priv_hex = getattr(settings, 'LICENCE_PRIVATE_KEY', '') or ''
            if priv_hex:
                if len(priv_hex) == 64 and all(c in '0123456789abcdefABCDEF' for c in priv_hex):
                    raw = bytes.fromhex(priv_hex)
                else:
                    raw = base64.b64decode(priv_hex)
                priv = Ed25519PrivateKey.from_private_bytes(raw)
                sig = priv.sign(fp.encode('utf-8'))
                self.fingerprint_signature_ed25519 = sig.hex()
        except Exception:
            if not self.fingerprint_signature_ed25519:
                self.fingerprint_signature_ed25519 = ''

    def verify_fingerprint(self) -> bool:
        """Vérifie la signature de l'empreinte (Ed25519 prioritaire, fallback HMAC)."""
        if not self.machine_fingerprint:
            return False
        # Vérif que l'empreinte stockée correspond aux attributs actuels
        attrs = self.build_attrs_dict()
        expected_fp = self.generate_fingerprint(attrs)
        if not hmac.compare_digest(expected_fp, self.machine_fingerprint):
            # Empreinte ne correspond plus aux attributs → possible clonage / modif
            # On continue quand même à vérifier la signature de l'empreinte stockée
            pass

        # 1. Ed25519 si présent + clé publique configurée
        if self.fingerprint_signature_ed25519:
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                import base64
                pub_hex = getattr(settings, 'LICENCE_PUBLIC_KEY', '') or ''
                if pub_hex:
                    if len(pub_hex) == 64 and all(c in '0123456789abcdefABCDEF' for c in pub_hex):
                        raw = bytes.fromhex(pub_hex)
                    else:
                        raw = base64.b64decode(pub_hex)
                    pub = Ed25519PublicKey.from_public_bytes(raw)
                    sig_str = self.fingerprint_signature_ed25519.strip()
                    try:
                        sig_bytes = bytes.fromhex(sig_str)
                    except ValueError:
                        sig_bytes = base64.b64decode(sig_str)
                    pub.verify(sig_bytes, self.machine_fingerprint.encode('utf-8'))
                    return True
                # Si Ed25519 présent mais pas de clé publique (dev) → on tolère si HMAC OK
            except Exception:
                # Si clé publique configurée, Ed25519 invalide = échec (anti-downgrade)
                if getattr(settings, 'LICENCE_PUBLIC_KEY', ''):
                    return False

        # 2. Fallback HMAC
        if self.fingerprint_signature:
            try:
                key = getattr(settings, 'LICENCE_SIGNING_KEY', '') or settings.SECRET_KEY
                expected = hmac.new(key.encode('utf-8'), self.machine_fingerprint.encode('utf-8'), hashlib.sha256).hexdigest()
                return hmac.compare_digest(expected, self.fingerprint_signature)
            except Exception:
                return False

        # Si aucune signature stockée (licence legacy), on considère l'empreinte comme non vérifiable
        # mais on ne bloque pas — on la resigne au prochain save si possible
        return bool(self.machine_fingerprint)

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

    def save(self, *args, **kwargs):
        # Génère empreinte + signature si pas déjà fait ou si attributs changés
        if not self.machine_fingerprint:
            self.compute_and_sign_fingerprint()
        else:
            # Si attributs ont changé, recalculer (on détecte via build)
            # Pour éviter recalcul inutile, on compare fingerprint actuel vs attendu
            attrs = self.build_attrs_dict()
            expected = self.generate_fingerprint(attrs)
            if expected != self.machine_fingerprint:
                self.compute_and_sign_fingerprint()
        super().save(*args, **kwargs)

    def revoquer(self) -> None:
        """Révoque cette activation."""
        self.est_active = False
        self.date_revocation = timezone.now()
        self.save(update_fields=['est_active', 'date_revocation', 'updated_at'])

    def get_empreinte_serveur(self) -> str:
        """
        Génère une empreinte unique du serveur — P1 multi-attributs.

        Returns:
            str: Hash SHA-256 multi-attributs (legacy si pas de fingerprint)
        """
        if self.machine_fingerprint:
            return self.machine_fingerprint
        # Fallback legacy
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