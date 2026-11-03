"""Année scolaire et périodes d'évaluation."""

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class AnneeScolaireManager(models.Manager):
    """Manager pour l'année scolaire."""

    def get_annee_courante(self, etablissement):
        """Récupère l'année scolaire en cours pour un établissement."""
        return self.filter(
            etablissement=etablissement,
            est_courante=True
        ).first()


class AnneeScolaire(BaseModel):
    """
    Années scolaires de l'établissement.

    Une seule année peut être marquée comme courante à la fois.
    Ex: 2025-2026, 2026-2027, etc.
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='annees_scolaires',
        verbose_name=_("Établissement")
    )

    libelle = models.CharField(
        max_length=20,
        verbose_name=_("Libellé"),
        help_text=_("Ex: 2025-2026, 2026-2027")
    )

    date_debut = models.DateField(
        verbose_name=_("Date de début"),
        help_text=_("Généralement début octobre au Burkina Faso")
    )

    date_fin = models.DateField(
        verbose_name=_("Date de fin"),
        help_text=_("Généralement fin juin")
    )

    est_courante = models.BooleanField(
        default=False,
        verbose_name=_("Année en cours"),
        help_text=_("Une seule année peut être courante à la fois")
    )

    cloturee = models.BooleanField(
        default=False,
        verbose_name=_("Année clôturée"),
        help_text=_("Si True, aucune modification possible")
    )

    # Manager personnalisé
    objects = AnneeScolaireManager()

    class Meta:
        verbose_name = _("Année Scolaire")
        verbose_name_plural = _("Années Scolaires")
        ordering = ['-date_debut']
        unique_together = [['etablissement', 'libelle']]

    def __str__(self):
        return self.libelle

    def save(self, *args, **kwargs):
        """S'assurer qu'une seule année est courante."""
        if self.est_courante:
            # Désactiver toutes les autres années courantes
            AnneeScolaire.objects.filter(
                etablissement=self.etablissement,
                est_courante=True
            ).exclude(pk=self.pk).update(est_courante=False)

        super().save(*args, **kwargs)


class PeriodeEvaluation(BaseModel):
    """
    Périodes d'évaluation : Trimestres ou Semestres.

    La plupart des établissements burkinabè utilisent 3 trimestres.
    Certains lycées techniques utilisent 2 semestres.
    """

    TYPE_CHOICES = [
        ('TRIMESTRE', _('Trimestre')),
        ('SEMESTRE', _('Semestre')),
    ]

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='periodes_evaluation',
        verbose_name=_("Établissement")
    )

    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='periodes',
        verbose_name=_("Année Scolaire")
    )

    type_periode = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='TRIMESTRE',
        verbose_name=_("Type de période")
    )

    nom = models.CharField(
        max_length=50,
        verbose_name=_("Nom de la période"),
        help_text=_("Ex: Trimestre 1, Semestre 1, etc.")
    )

    numero = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        verbose_name=_("Numéro"),
        help_text=_("1, 2 ou 3")
    )

    date_debut = models.DateField(
        verbose_name=_("Date de début")
    )

    date_fin = models.DateField(
        verbose_name=_("Date de fin")
    )

    est_en_cours = models.BooleanField(
        default=False,
        verbose_name=_("Période en cours")
    )

    cloturee = models.BooleanField(
        default=False,
        verbose_name=_("Période clôturée"),
        help_text=_("Si True, aucune modification des notes possible")
    )

    derogation_ouverte = models.BooleanField(
        default=False,
        verbose_name=_("Dérogation ouverte"),
        help_text=_("Si True, autorise temporairement la saisie sur une période échue")
    )

    class Meta:
        verbose_name = _("Période d'Évaluation")
        verbose_name_plural = _("Périodes d'Évaluation")
        ordering = ['annee_scolaire', 'numero']
        unique_together = [['annee_scolaire', 'numero']]

    def __str__(self):
        return f"{self.nom} ({self.annee_scolaire.libelle})"

    @property
    def echue(self):
        """True dès le lendemain de la date de fin de la période."""
        from django.utils import timezone
        return bool(self.date_fin and timezone.localdate() > self.date_fin)

    @property
    def verrouillee(self):
        """Période verrouillée : clôturée manuellement, ou échue sans dérogation ouverte."""
        if self.cloturee:
            return True
        return self.echue and not self.derogation_ouverte
