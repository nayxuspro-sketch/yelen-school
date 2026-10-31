"""Appréciations des moyennes et catalogue des disciplines."""

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

from .etablissement import Cycle


class AppreciationMoyenneSecondaire(BaseModel):
    """
    Grille d'appréciation comportementale pour les bulletins.

    Ex: Excellent, Bien, Passable, Insuffisant, Médiocre
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='appreciations_conduite',
        verbose_name=_("Établissement")
    )

    libelle = models.CharField(
        max_length=50,
        verbose_name=_("Libellé"),
        help_text=_("Ex: Excellent, Bien, Passable, etc.")
    )

    moy_min = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name=_("Moyenne minimale"),
        help_text=_("Moyenne minimale pour cette appréciation sur 20")
    )

    moy_max = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name=_("Moyenne maximale"),
        help_text=_("Moyenne maximale pour cette appréciation sur 20")
    )

    couleur = models.CharField(
        max_length=7,
        default='#00A86B',
        verbose_name=_("Couleur"),
        help_text=_("Code couleur hexadécimal")
    )

    ordre = models.IntegerField(
        default=1,
        verbose_name=_("Ordre d'affichage")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Appréciation active")
    )

    class Meta:
        verbose_name = _("Appréciation Moyenne Secondaire")
        verbose_name_plural = _("Appréciations Moyenne Secondaire")
        ordering = ['-moy_min']

    def __str__(self):
        return f"{self.libelle} ({self.moy_min}-{self.moy_max})"


class AppreciationMoyennePrimaire(BaseModel):
    """
    Grille d'appréciation des moyennes pour le cycle Primaire.

    Ex: Excellent, Bien, Passable, Insuffisant, Médiocre
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='appreciations_moyenne_primaire',
        verbose_name=_("Établissement")
    )

    libelle = models.CharField(
        max_length=50,
        verbose_name=_("Libellé"),
        help_text=_("Ex: Excellent, Bien, Passable, etc.")
    )

    moy_min = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name=_("Moyenne minimale"),
        help_text=_("Moyenne minimale pour cette appréciation sur 10")
    )

    moy_max = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=10,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name=_("Moyenne maximale"),
        help_text=_("Moyenne maximale pour cette appréciation sur 10")
    )

    couleur = models.CharField(
        max_length=7,
        default='#00A86B',
        verbose_name=_("Couleur"),
        help_text=_("Code couleur hexadécimal")
    )

    ordre = models.IntegerField(
        default=1,
        verbose_name=_("Ordre d'affichage")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Appréciation active")
    )

    class Meta:
        verbose_name = _("Appréciation Moyenne Primaire")
        verbose_name_plural = _("Appréciations Moyenne Primaire")
        ordering = ['-moy_min']

    def __str__(self):
        return f"{self.libelle} ({self.moy_min}-{self.moy_max})"


class CategorieDiscipline(BaseModel):
    """Catégories de disciplines (ex: Langues, Sciences, Sciences Humaines)"""

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='categorie_disciplines',
        verbose_name=_("Établissement")
    )

    nom = models.CharField(
        max_length=100,
        verbose_name=_("Nom de la catégorie"),
        help_text=_("Ex: Langues, Sciences, Sciences Humaines, etc.")
    )

    code = models.CharField(
        max_length=20,
        verbose_name=_("Code"),
        help_text=_("Code court unique, ex: LNG, SCI, SH")
    )

    couleur = models.CharField(
        max_length=7,
        default='#6366F1',
        verbose_name=_("Couleur"),
        help_text=_("Code couleur pour affichage")
    )

    ordre = models.IntegerField(
        default=1,
        verbose_name=_("Ordre d'affichage")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Catégorie active")
    )

    class Meta:
        verbose_name = _("Catégorie de discipline")
        verbose_name_plural = _("Catégories de disciplines")
        ordering = ['etablissement', 'ordre', 'nom']
        unique_together = [['etablissement', 'code']]

    def __str__(self):
        return self.nom


class Discipline(BaseModel):
    """
    Matières enseignées par cycle.

    Chaque matière appartient à une catégorie paramétrable.
    Ex: Mathématiques en Sciences, Français en Langues.
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='disciplines',
        verbose_name=_("Établissement")
    )

    nom = models.CharField(
        max_length=100,
        verbose_name=_("Nom de la matière"),
        help_text=_("Ex: Mathématiques, Français, Histoire-Géographie, etc.")
    )

    code = models.CharField(
        max_length=20,
        verbose_name=_("Code"),
        help_text=_("Code court unique, ex: MATH, FR, HG")
    )

    cycle = models.ForeignKey(
        Cycle,
        on_delete=models.CASCADE,
        related_name='disciplines',
        verbose_name=_("Cycle")
    )

    categorie = models.ForeignKey(
        CategorieDiscipline,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='disciplines',
        verbose_name=_("Catégorie")
    )

    est_evaluee = models.BooleanField(
        default=True,
        verbose_name=_("Matière évaluée"),
        help_text=_("Si False, matière enseignée mais non notée")
    )

    couleur = models.CharField(
        max_length=7,
        default='#00A86B',
        verbose_name=_("Couleur"),
        help_text=_("Code couleur pour affichage")
    )

    ordre = models.IntegerField(
        default=1,
        verbose_name=_("Ordre d'affichage")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Matière active")
    )

    class Meta:
        verbose_name = _("Discipline")
        verbose_name_plural = _("Disciplines")
        ordering = ['cycle', 'ordre', 'nom']
        unique_together = [['etablissement', 'code', 'cycle']]

    def __str__(self):
        return f"{self.nom} ({self.cycle.nom})"
