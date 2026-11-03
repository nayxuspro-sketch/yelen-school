"""Modèle principal Licence, énumérations, feature flags et quotas par palier."""
import hashlib
import hmac
import logging
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel

logger = logging.getLogger(__name__)
User = get_user_model()


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
    date_debut_periode = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Début de la période en cours"),
        help_text=_("Activation ou dernier renouvellement : borne la durée affichée")
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
    # Jeton hors ligne v3 (licences/jeton.py) : émis et signé par l'éditeur,
    # seule preuve de validité lorsque LICENCE_PUBLIC_KEY est configurée.
    jeton_signe = models.TextField(
        blank=True,
        default='',
        editable=False,
        verbose_name=_("Jeton de licence signé"),
        help_text=_("Code de licence YELEN3 émis par l'éditeur (signature Ed25519)")
    )
    empreinte_serveur = models.CharField(
        max_length=64,
        blank=True,
        default='',
        editable=False,
        verbose_name=_("Empreinte du serveur autorisé"),
        help_text=_("Identifiant du serveur auquel la licence est liée (vide = non liée)")
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
        return dt.astimezone(dt_timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

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
            logger.warning("Licence %s : signature Ed25519 non générée", self.cle_licence, exc_info=True)
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
            logger.error("Licence : clé privée Ed25519 illisible", exc_info=True)
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
            logger.error("Licence : clé publique Ed25519 illisible", exc_info=True)
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
            logger.warning("Licence %s : signature Ed25519 invalide", self.cle_licence)
            return False

    def verifier_jeton(self) -> bool:
        """Jeton v3 : signature Ed25519 de l'éditeur valide ET payload identique à cette licence."""
        if not self.jeton_signe:
            return False
        from ..jeton import JetonInvalide, charger_cle_publique, payload_correspond, verifier_jeton
        try:
            payload = verifier_jeton(
                self.jeton_signe,
                charger_cle_publique(getattr(settings, 'LICENCE_PUBLIC_KEY', '')),
            )
        except JetonInvalide:
            return False
        return payload_correspond(payload, self)

    def liee_a_ce_serveur(self) -> bool:
        """Licence utilisable sur le serveur courant (non liée, ou empreinte identique)."""
        if not self.empreinte_serveur:
            return True
        from ..binding import empreinte_serveur
        return hmac.compare_digest(self.empreinte_serveur, empreinte_serveur())

    def verifier_signature(self) -> bool:
        """
        Vérifie l'intégrité de la licence.

        Mode strict (LICENCE_PUBLIC_KEY configurée — production) : seule une
        signature de l'éditeur fait foi — jeton v3 (verifier_jeton) ou
        signature Ed25519 v2 (verifier_signature_ed25519). Aucun repli HMAC :
        la clé HMAC vit dans le .env de l'école et ne prouve rien.

        Mode démonstration (sans clé publique) : HMAC v2/v1 (LICENCE_SIGNING_KEY
        ou SECRET_KEY), Ed25519 acceptée si présente.

        Returns:
            bool: True si signature valide
        """
        if getattr(settings, 'LICENCE_PUBLIC_KEY', ''):
            return self.verifier_jeton() or self.verifier_signature_ed25519()

        if self.signature_ed25519 and self.verifier_signature_ed25519():
            return True
        stockee = self.signature_hmac or ''
        for message in (self._message_signature_v2(), self._message_signature_v1()):
            if hmac.compare_digest(stockee, self._signer(message)):
                return True
        return False
    
    def _verifier_limites(self) -> None:
        """Point d'extension : contrôle des limites (LIMITES_LICENCES) à la sauvegarde — non appliqué pour l'instant."""
    
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
            and (not getattr(settings, 'LICENCE_BINDING_ENABLED', False) or self.liee_a_ce_serveur())
        )
    
    def jours_restants(self) -> int:
        """
        Calcule le nombre de jours restants avant expiration.
        
        Returns:
            int: Nombre de jours (peut être négatif si expirée)
        """
        delta = self.date_expiration - timezone.now().date()
        return delta.days

    def duree_periode(self) -> int:
        """Jours prévus pour la période en cours : du début de période (activation
        ou dernier renouvellement, à défaut création) à l'expiration. Toujours
        supérieur ou égal aux jours restants."""
        debut = self.date_debut_periode or self.date_activation or self.created_at
        if debut is None:
            return max(self.jours_restants(), 0)
        if isinstance(debut, datetime):
            debut = debut.date()
        return max((self.date_expiration - debut).days, 0)

    def progression_periode(self) -> int:
        """Part de la période en cours encore à courir, en pourcentage (0 à 100)."""
        total = self.duree_periode()
        if total <= 0:
            return 0
        return max(0, min(100, round(self.jours_restants() / total * 100)))
    
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
            self.date_debut_periode = self.date_activation.date()
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
        self.date_debut_periode = timezone.now().date()
        self.date_expiration = self.date_debut_periode + timedelta(days=duree_jours)
        
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
            logger.warning("Licence %s : payload heartbeat non signé", self.cle_licence, exc_info=True)
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
                        logger.warning("Heartbeat : signature de la réponse invalide")
                        return False
            return True
        except Exception:
            logger.warning("Heartbeat : réponse illisible", exc_info=True)
            return False

