"""Postes, statuts d'élève et titres du personnel."""

from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class Poste(BaseModel):
    """
    Postes/fonctions du personnel de l'établissement.

    Ex: Directeur, Enseignant, Surveillant, AVS, Secrétaire, etc.
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='postes',
        verbose_name=_("Établissement")
    )

    titre = models.CharField(
        max_length=100,
        verbose_name=_("Titre du poste"),
        help_text=_("Ex: Directeur, Enseignant, AVS, etc.")
    )

    code = models.CharField(
        max_length=20,
        verbose_name=_("Code"),
        help_text=_("Code court unique, ex: DIR, ENS, AVS, SECR")
    )

    categorie = models.CharField(
        max_length=20,
        choices=[
            ('DIRECTION', _('Direction')),
            ('ENSEIGNEMENT', _('Enseignement')),
            ('ADMINISTRATION', _('Administration')),
            ('VIE_SCOLAIRE', _('Vie Scolaire')),
            ('TECHNIQUE', _('Personnel Technique')),
        ],
        default='ENSEIGNEMENT',
        verbose_name=_("Catégorie")
    )

    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Poste actif")
    )

    class Meta:
        verbose_name = _("Poste")
        verbose_name_plural = _("Postes")
        ordering = ['categorie', 'titre']
        unique_together = [['etablissement', 'code']]

    def __str__(self):
        return f"{self.titre} ({self.code})"


class LocalisationPoste(BaseModel):
    """
    Localisation géographique des postes (bureau, salle).

    Pour localiser rapidement le personnel dans l'établissement.
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='localisations',
        verbose_name=_("Établissement")
    )

    nom = models.CharField(
        max_length=100,
        verbose_name=_("Nom de la localisation"),
        help_text=_("Ex: Bureau directeur, Salle des professeurs, Secrétariat")
    )

    type_localisation = models.CharField(
        max_length=20,
        choices=[
            ('BUREAU', _('Bureau')),
            ('SALLE', _('Salle de classe')),
            ('LABORATOIRE', _('Laboratoire')),
            ('AUTRE', _('Autre')),
        ],
        default='BUREAU',
        verbose_name=_("Type")
    )

    batiment = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("Bâtiment"),
        help_text=_("Ex: Bâtiment A, Bloc administratif, etc.")
    )

    etage = models.IntegerField(
        default=0,
        verbose_name=_("Étage"),
        help_text=_("0 = Rez-de-chaussée")
    )

    numero = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Numéro"),
        help_text=_("Numéro de salle ou bureau")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Localisation active")
    )

    class Meta:
        verbose_name = _("Localisation")
        verbose_name_plural = _("Localisations")
        ordering = ['batiment', 'etage', 'numero']

    def __str__(self):
        return f"{self.nom} - {self.batiment}"


class StatutEleve(BaseModel):
    """
    Statuts possibles des élèves.

    Impacte le calcul des frais de scolarité via TarifScolarite.
    Ex: Affecté, Non affecté, Boursier, Exonéré, Redoublant, etc.
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='statuts_eleves',
        verbose_name=_("Établissement")
    )

    nom = models.CharField(
        max_length=50,
        verbose_name=_("Nom du statut"),
        help_text=_("Ex: Affecté, Boursier, Exonéré, etc.")
    )

    code = models.CharField(
        max_length=20,
        verbose_name=_("Code"),
        help_text=_("Code court unique, ex: AFF, BOURS, EXON")
    )

    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description")
    )

    couleur = models.CharField(
        max_length=7,
        default='#00A86B',
        verbose_name=_("Couleur"),
        help_text=_("Code couleur hexadécimal pour l'affichage")
    )

    ordre = models.IntegerField(
        default=1,
        verbose_name=_("Ordre d'affichage")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Statut actif")
    )

    class Meta:
        verbose_name = _("Statut Élève")
        verbose_name_plural = _("Statuts Élèves")
        ordering = ['ordre', 'nom']
        unique_together = [['etablissement', 'code']]

    def __str__(self):
        return f"{self.nom} ({self.code})"


class TitreFonction(BaseModel):
    """
    Liste configurable des titres/fonctions du personnel.

    Ex: Directeur, Censeur, Professeur principal, Secrétaire, etc.
    Ces valeurs alimentent le champ « Titre » dans la fiche personnel.
    """

    nom = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Titre / Fonction"),
        help_text=_("Ex: Directeur, Censeur, Professeur Principal")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Actif")
    )

    class Meta:
        verbose_name = _("Titre Fonction")
        verbose_name_plural = _("Titres Fonctions")
        ordering = ['nom']

    def __str__(self):
        return self.nom


class TitreHonorifiquePersonnel(BaseModel):
    """
    Liste configurable des titres honorifiques du personnel.

    Ex: M. le Directeur, Chevalier de l'Ordre des Palmes académiques, Dr., etc.
    Ces valeurs alimentent le champ « Titre honorifique » dans la fiche personnel.
    """

    nom = models.CharField(
        max_length=150,
        unique=True,
        verbose_name=_("Titre honorifique"),
        help_text=_("Ex: M. le Directeur, Chevalier de l'Ordre des Palmes académiques")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Actif")
    )

    class Meta:
        verbose_name = _("Titre Honorifique")
        verbose_name_plural = _("Titres Honorifiques")
        ordering = ['nom']

    def __str__(self):
        return self.nom
