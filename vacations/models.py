"""
Module Vacations - Models
==========================
YELEN SCHOOL v3.4 - Gestion des vacataires et heures supplémentaires

Les vacataires sont des enseignants payés à l'heure.
Ce module gère :
1. ContratVacation    - Contrat annuel d'un vacataire
2. HeureVacation      - Saisie mensuelle des heures effectuées
3. BulletinVacation   - Récapitulatif mensuel de paiement

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


# ═══════════════════════════════════════════════════════════════════
# 1. CONTRAT VACATION
# ═══════════════════════════════════════════════════════════════════

class ContratVacation(BaseModel):
    """
    Contrat annuel d'un enseignant vacataire.

    Définit le taux horaire, le volume hebdomadaire prévu et la classe.
    Lié à une InscriptionPersonnel pour rattacher le vacataire à une classe.
    """

    personnel = models.ForeignKey(
        'personnel.MembrePersonnel',
        on_delete=models.CASCADE,
        related_name='contrats_vacation',
        verbose_name=_("Vacataire")
    )

    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='contrats_vacation',
        verbose_name=_("Année scolaire")
    )

    enseignement = models.ForeignKey(
        'pedagogie.Enseignement',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contrats_vacation',
        verbose_name=_("Enseignement (matière × classe)")
    )

    taux_horaire = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=Decimal('2500'),
        validators=[MinValueValidator(0)],
        verbose_name=_("Taux horaire (FCFA)"),
        help_text=_("Montant payé par heure de cours effectuée")
    )

    heures_hebdo_prevues = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=Decimal('2.0'),
        validators=[MinValueValidator(Decimal('0.5'))],
        verbose_name=_("Heures hebdomadaires prévues")
    )

    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_fin = models.DateField(blank=True, null=True, verbose_name=_("Date de fin"))

    actif = models.BooleanField(default=True, verbose_name=_("Contrat actif"))

    class Meta:
        verbose_name = _("Contrat de Vacation")
        verbose_name_plural = _("Contrats de Vacation")
        ordering = ['-annee_scolaire', 'personnel__nom']
        unique_together = [['personnel', 'annee_scolaire', 'enseignement']]

    def __str__(self):
        matiere = self.enseignement.matiere.nom if self.enseignement else "—"
        return f"{self.personnel.get_nom_complet()} — {matiere} — {self.annee_scolaire}"


# ═══════════════════════════════════════════════════════════════════
# 2. HEURES DE VACATION (saisie mensuelle)
# ═══════════════════════════════════════════════════════════════════

class HeureVacation(BaseModel):
    """
    Saisie mensuelle des heures effectuées par un vacataire.

    Une ligne par mois et par contrat.
    Le montant dû = heures_effectuees × contrat.taux_horaire.
    """

    MOIS_CHOICES = [
        (1, _('Janvier')), (2, _('Février')), (3, _('Mars')),
        (4, _('Avril')), (5, _('Mai')), (6, _('Juin')),
        (7, _('Juillet')), (8, _('Août')), (9, _('Septembre')),
        (10, _('Octobre')), (11, _('Novembre')), (12, _('Décembre')),
    ]

    contrat = models.ForeignKey(
        ContratVacation,
        on_delete=models.CASCADE,
        related_name='heures',
        verbose_name=_("Contrat")
    )

    mois = models.IntegerField(
        choices=MOIS_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_("Mois")
    )

    annee = models.IntegerField(verbose_name=_("Année"))

    heures_effectuees = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('0.0'),
        validators=[MinValueValidator(0)],
        verbose_name=_("Heures effectuées")
    )

    heures_annulees = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal('0.0'),
        validators=[MinValueValidator(0)],
        verbose_name=_("Heures annulées / non remplacées")
    )

    valide_par = models.ForeignKey(
        'personnel.MembrePersonnel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='heures_vacation_validees',
        verbose_name=_("Validé par")
    )

    est_valide = models.BooleanField(
        default=False,
        verbose_name=_("Heures validées")
    )

    observations = models.TextField(
        blank=True, default='',
        verbose_name=_("Observations")
    )

    class Meta:
        verbose_name = _("Heures de Vacation")
        verbose_name_plural = _("Heures de Vacation")
        ordering = ['-annee', '-mois']
        unique_together = [['contrat', 'mois', 'annee']]

    def __str__(self):
        return (
            f"{self.contrat.personnel.get_nom_complet()} — "
            f"{self.get_mois_display()} {self.annee} — "
            f"{self.heures_effectuees}h"
        )

    @property
    def heures_nettes(self):
        """Heures payables = effectuées − annulées."""
        return max(self.heures_effectuees - self.heures_annulees, Decimal('0'))

    @property
    def montant_du(self):
        """Montant à payer pour ce mois."""
        return self.heures_nettes * self.contrat.taux_horaire


# ═══════════════════════════════════════════════════════════════════
# 3. BULLETIN DE VACATION (récapitulatif mensuel)
# ═══════════════════════════════════════════════════════════════════

class BulletinVacation(BaseModel):
    """
    Récapitulatif mensuel de toutes les heures d'un vacataire.

    Généré automatiquement (ou manuellement) pour servir de
    document de paiement officiel.
    """

    class StatutChoices(models.TextChoices):
        BROUILLON = 'BROUILLON', _('Brouillon')
        VALIDE = 'VALIDE', _('Validé')
        PAYE = 'PAYE', _('Payé')

    personnel = models.ForeignKey(
        'personnel.MembrePersonnel',
        on_delete=models.CASCADE,
        related_name='bulletins_vacation',
        verbose_name=_("Vacataire")
    )

    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='bulletins_vacation',
        verbose_name=_("Année scolaire")
    )

    mois = models.IntegerField(
        choices=HeureVacation.MOIS_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_("Mois")
    )

    annee = models.IntegerField(verbose_name=_("Année"))

    total_heures = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        default=Decimal('0.0'),
        verbose_name=_("Total heures payables")
    )

    montant_total = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=Decimal('0'),
        verbose_name=_("Montant total (FCFA)")
    )

    statut = models.CharField(
        max_length=10,
        choices=StatutChoices.choices,
        default=StatutChoices.BROUILLON,
        verbose_name=_("Statut")
    )

    date_paiement = models.DateField(
        blank=True, null=True,
        verbose_name=_("Date de paiement")
    )

    reference_paiement = models.CharField(
        max_length=100,
        blank=True, default='',
        verbose_name=_("Référence paiement")
    )

    class Meta:
        verbose_name = _("Bulletin de Vacation")
        verbose_name_plural = _("Bulletins de Vacation")
        ordering = ['-annee', '-mois', 'personnel__nom']
        unique_together = [['personnel', 'mois', 'annee']]

    def __str__(self):
        return (
            f"Vacation {self.personnel.get_nom_complet()} — "
            f"{self.get_mois_display()} {self.annee}"
        )

    def calculer_totaux(self):
        """Recalcule total_heures et montant_total depuis les HeureVacation."""
        from django.db.models import Sum
        heures = HeureVacation.objects.filter(
            contrat__personnel=self.personnel,
            contrat__annee_scolaire=self.annee_scolaire,
            mois=self.mois,
            annee=self.annee,
            est_valide=True
        )
        total_h = Decimal('0')
        total_m = Decimal('0')
        for h in heures:
            total_h += h.heures_nettes
            total_m += h.montant_du
        self.total_heures = total_h
        self.montant_total = total_m
        self.save(update_fields=['total_heures', 'montant_total'])
