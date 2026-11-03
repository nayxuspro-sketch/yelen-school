"""Activations serveur (binding matériel), journal d'audit et alertes de licence."""
import hashlib
import hmac
import logging
from typing import List

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel

from .licence import Licence

logger = logging.getLogger(__name__)
User = get_user_model()


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
            logger.exception("Licence %s : signature HMAC de l'empreinte impossible", self.cle_licence)
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
            logger.warning("Licence %s : signature Ed25519 de l'empreinte impossible", self.cle_licence, exc_info=True)
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
            # Empreinte ne correspond plus aux attributs stockés → clonage ou
            # modification de l'enregistrement : binding invalide (P1 anti-fraude).
            return False

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
                logger.warning("Licence %s : signature Ed25519 de l'empreinte invalide", self.cle_licence)
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
                logger.warning("Licence %s : vérification HMAC de l'empreinte impossible", self.cle_licence, exc_info=True)
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
        # Première sauvegarde uniquement (append-only) — P2 fix : utiliser _state.adding
        # car pk est pré-rempli par default=uuid.uuid4
        if not self._state.adding:
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
