"""
Module Documents - Models
==========================
YELEN SCHOOL v3.4 - Génération et archivage des documents officiels

Ce module gère la génération des documents scolaires avec signataires
paramétrables (intégration parametres.SignataireDocument).

Documents supportés :
- Certificat de scolarité
- Bulletin de notes (via pedagogie)
- Reçu de paiement (via finances)
- Attestation de non-redevabilité
- Autorisation d'absence
- Cursus scolaire complet
- Carte d'identité scolaire
- Liste alphabétique de classe
- Liste du personnel

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


# ═══════════════════════════════════════════════════════════════════
# 1. DOCUMENT GÉNÉRÉ
# ═══════════════════════════════════════════════════════════════════

class Document(BaseModel):
    """
    Enregistrement d'un document généré pour un élève ou la classe.

    Chaque génération est tracée : qui, quand, quel document, quel fichier.
    Le fichier PDF est stocké dans media/documents/.
    """

    type_document = models.ForeignKey(
        'parametres.TypeDocument',
        on_delete=models.PROTECT,
        related_name='documents',
        verbose_name=_("Type de document")
    )

    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_("Année scolaire")
    )

    # Destinataire : un élève OU une classe (pas les deux)
    inscription = models.ForeignKey(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True,
        verbose_name=_("Inscription (élève)")
    )

    classe = models.ForeignKey(
        'parametres.Classe',
        on_delete=models.CASCADE,
        related_name='documents',
        null=True,
        blank=True,
        verbose_name=_("Classe (document collectif)")
    )

    # Fichier généré
    fichier = models.FileField(
        upload_to='documents/pdf/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_("Fichier PDF")
    )

    # Traçabilité
    genere_par = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_generes',
        verbose_name=_("Généré par")
    )

    # Signataire utilisé lors de la génération (snapshot)
    signataire_nom = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("Nom du signataire (snapshot)"),
        help_text=_("Nom du signataire au moment de la génération")
    )

    numero_document = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("Numéro du document"),
        help_text=_("Numéro de série unique, ex: CERT-2026-00001")
    )

    version = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Version"),
        help_text=_("Numéro de version — incrémenté à chaque regénération du même document")
    )

    observations = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Observations")
    )

    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        ordering = ['-created_at']

    def __str__(self):
        destinataire = (
            self.inscription.eleve.get_nom_complet()
            if self.inscription
            else (self.classe.nom if self.classe else "—")
        )
        v = f" v{self.version}" if self.version > 1 else ""
        return f"{self.type_document.libelle}{v} — {destinataire} — {self.annee_scolaire}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self._compute_version()
            self._generate_numero()
        super().save(*args, **kwargs)

    def _compute_version(self):
        """Calcule le numéro de version parmi les documents du même type pour le même destinataire."""
        qs = Document.objects.filter(
            type_document_id=self.type_document_id,
            annee_scolaire_id=self.annee_scolaire_id,
        )
        if self.inscription_id:
            qs = qs.filter(inscription_id=self.inscription_id)
        elif self.classe_id:
            qs = qs.filter(classe_id=self.classe_id)
        self.version = qs.count() + 1

    def _generate_numero(self):
        """Génère un numéro de document unique."""
        from datetime import datetime
        code = self.type_document.code if self.type_document_id else 'DOC'
        year = datetime.now().year
        count = Document.objects.filter(
            numero_document__startswith=f"{code}-{year}"
        ).count() + 1
        self.numero_document = f"{code}-{year}-{count:05d}"
