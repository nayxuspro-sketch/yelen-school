"""Rubriques de paiement et grille tarifaire (classe × statut)."""

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

from .etablissement import Cycle, Classe
from .structure import StatutEleve


class RubriquePaiement(BaseModel):
    """
    Types de frais scolaires.

    Ex: Scolarité, Inscription, Cantine, Transport, Tenue, etc.
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='rubriques_paiement',
        verbose_name=_("Établissement")
    )

    nom = models.CharField(
        max_length=200,
        verbose_name=_("Nom de la rubrique"),
        help_text=_("Ex: Scolarité, Inscription, Cantine, etc.")
    )

    code = models.CharField(
        max_length=20,
        verbose_name=_("Code"),
        help_text=_("Code court unique, ex: SCOL, INSC, CANT")
    )

    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description")
    )

    soumise_plafond = models.BooleanField(
        default=True,
        verbose_name=_("Comptée dans les frais de scolarité plafonnés"),
        help_text=_("Décochez pour les services annexes (cantine, transport, internat) et les frais autorisés par la tutelle"),
    )
    obligatoire = models.BooleanField(
        default=True,
        verbose_name=_("Rubrique obligatoire"),
        help_text=_("Si True, tous les élèves doivent payer")
    )

    ordre = models.IntegerField(
        default=1,
        verbose_name=_("Ordre d'affichage")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Rubrique active")
    )

    montant = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Montant (FCFA)"),
        help_text=_("Montant par défaut en Francs CFA")
    )

    class Meta:
        verbose_name = _("Rubrique de Paiement")
        verbose_name_plural = _("Rubriques de Paiement")
        ordering = ['ordre', 'nom']
        unique_together = [['etablissement', 'code']]

    def __str__(self):
        return f"{self.nom} ({self.code})"


class TarifScolarite(BaseModel):
    """
    Matrice tarifaire : Classe × Statut Élève × Rubrique → Montant.

    Permet une tarification flexible par profil d'élève.
    Ex: Un élève Affecté en 6ème paie X FCFA de scolarité,
        Un élève Boursier en 6ème paie 0 FCFA.
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_("Établissement")
    )

    cycle = models.ForeignKey(
        Cycle,
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_("Cycle"),
        null=True,
        blank=True,
        help_text=_("Laisser vide pour appliquer à tous les cycles")
    )

    classe = models.ForeignKey(
        Classe,
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_("Classe")
    )

    statut_eleve = models.ForeignKey(
        StatutEleve,
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_("Statut Élève")
    )

    rubrique = models.ForeignKey(
        RubriquePaiement,
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_("Rubrique")
    )

    montant = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Montant (FCFA)"),
        help_text=_("Montant en Francs CFA")
    )

    annee_scolaire = models.ForeignKey(
        'AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='tarifs',
        verbose_name=_("Année Scolaire")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Tarif actif")
    )

    class Meta:
        verbose_name = _("Tarif Scolarité")
        verbose_name_plural = _("Tarifs Scolarité")
        ordering = ['classe', 'statut_eleve', 'rubrique']
        unique_together = [['classe', 'statut_eleve', 'rubrique', 'annee_scolaire']]

    def __str__(self):
        return (
            f"{self.classe.nom} - {self.statut_eleve.nom} - "
            f"{self.rubrique.nom} : {self.montant} FCFA"
        )
