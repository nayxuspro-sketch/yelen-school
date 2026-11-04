"""Identité, cycles, classes et salles de l'établissement."""

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.fields import URLFieldHTTPS
from core.models import BaseModel


class IdentiteEtablissement(BaseModel):
    """
    Configuration globale de l'établissement.

    Singleton : un seul enregistrement par établissement.
    Contient logo, coordonnées, signature directeur pour tous les documents.
    """

    etablissement = models.OneToOneField(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='identite',
        verbose_name=_("Établissement")
    )

    # Informations officielles
    nom_etablissement = models.CharField(
        max_length=200,
        verbose_name=_("Nom de l'établissement")
    )

    sigle = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Sigle"),
        help_text=_("Ex: CEG, Lycée, etc.")
    )

    type_etablissement = models.CharField(
        max_length=20,
        choices=[
            ('PUBLIC', _('Public')),
            ('PRIVE', _('Privé')),
            ('CONFESSIONNEL', _('Confessionnel')),
        ],
        default='PRIVE',
        verbose_name=_("Type d'établissement")
    )

    numero_agrement_mena = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("N° Agrément"),
        help_text=_("Numéro officiel d'agrément du Ministère")
    )

    date_agrement = models.DateField(
        verbose_name=_("Date d'agrément")
    )
    categorie_reglementaire = models.PositiveSmallIntegerField(
        null=True, blank=True,
        choices=[(1, _('Catégorie 1')), (2, _('Catégorie 2')), (3, _('Catégorie 3'))],
        verbose_name=_("Catégorie réglementaire"),
        help_text=_("Classement de la structure privée (décret n° 2026-0761) ; vide = non classée, aucun plafond appliqué"),
    )
    zone_implantation = models.PositiveSmallIntegerField(
        null=True, blank=True,
        choices=[
            (1, _('Ouagadougou et Bobo-Dioulasso')),
            (2, _('Chefs-lieux de province et communes périurbaines')),
            (3, _('Zones rurales et zones non loties')),
        ],
        verbose_name=_("Zone d'implantation"),
    )

    # Adresse complète
    adresse_complete = models.TextField(
        verbose_name=_("Adresse complète")
    )

    ville = models.CharField(
        max_length=100,
        verbose_name=_("Ville")
    )

    province = models.CharField(
        max_length=100,
        verbose_name=_("Province")
    )

    region = models.CharField(
        max_length=100,
        verbose_name=_("Région"),
        help_text=_("Ex: Centre, Hauts-Bassins, Sahel, etc.")
    )

    # Contact
    telephone = models.CharField(
        max_length=35,
        verbose_name=_("Téléphone")
    )

    email = models.EmailField(
        verbose_name=_("Email")
    )

    site_web = URLFieldHTTPS(
        blank=True,
        default='',
        verbose_name=_("Site web")
    )

    # Éléments visuels pour documents PDF
    logo = models.ImageField(
        upload_to='etablissement/logos/',
        blank=True,
        null=True,
        verbose_name=_("Logo de l'établissement"),
        help_text=_("Format PNG recommandé, 300×300px minimum")
    )

    signature_directeur = models.ImageField(
        upload_to='etablissement/signatures/',
        blank=True,
        null=True,
        verbose_name=_("Signature numérique du directeur"),
        help_text=_("Image PNG transparente de la signature")
    )

    cachet_etablissement = models.ImageField(
        upload_to='etablissement/cachets/',
        blank=True,
        null=True,
        verbose_name=_("Cachet officiel"),
        help_text=_("Image PNG transparente du cachet rond")
    )

    nom_directeur = models.CharField(
        max_length=200,
        verbose_name=_("Nom du Directeur/Proviseur"),
        help_text=_("Nom complet pour les documents officiels")
    )

    devise = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Devise de l'établissement"),
        help_text=_("Slogan ou devise (optionnel)")
    )

    statut_actif = models.BooleanField(
        default=True,
        verbose_name=_("Établissement actif")
    )

    class Meta:
        verbose_name = _("Identité Établissement")
        verbose_name_plural = _("Identités Établissements")

    def __str__(self):
        return self.nom_etablissement

    def save(self, *args, **kwargs):
        """Valider qu'il n'y a qu'une seule identité par établissement."""
        if not self.pk and IdentiteEtablissement.objects.filter(
            etablissement=self.etablissement
        ).exists():
            raise ValidationError(
                _("Une identité existe déjà pour cet établissement.")
            )
        super().save(*args, **kwargs)


class Cycle(BaseModel):
    """
    Cycles scolaires selon le système éducatif burkinabè.
    4 cycles : Préscolaire, Primaire, Post-primaire, Secondaire
    """

    CODE_CHOICES = [
        ('PRES', _('Préscolaire')),
        ('PRIM', _('Primaire')),
        ('POST', _('Post-primaire')),
        ('SEC', _('Secondaire')),
    ]

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='cycles_parametres',
        verbose_name=_("Établissement")
    )

    nom = models.CharField(
        max_length=50,
        verbose_name=_("Nom du cycle"),
        help_text=_("Ex: Préscolaire, Primaire, etc.")
    )

    code = models.CharField(
        max_length=4,
        choices=CODE_CHOICES,
        verbose_name=_("Code cycle")
    )

    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description")
    )

    ordre = models.IntegerField(
        default=1,
        verbose_name=_("Ordre d'affichage"),
        help_text=_("1=Préscolaire, 2=Primaire, 3=Post-primaire, 4=Secondaire")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Cycle actif")
    )

    class Meta:
        verbose_name = _("Cycle")
        verbose_name_plural = _("Cycles")
        ordering = ['ordre']
        unique_together = [['etablissement', 'code']]

    def __str__(self):
        return f"{self.nom} ({self.code})"


class Classe(BaseModel):
    """
    Classes de l'établissement par cycle.

    Ex: CP1, CE2, 6ème, 3ème, Terminale A, etc.
    """

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name=_("Établissement")
    )

    cycle = models.ForeignKey(
        Cycle,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name=_("Cycle")
    )

    nom = models.CharField(
        max_length=50,
        verbose_name=_("Nom de la classe"),
        help_text=_("Ex: CP1, 6ème A, Terminale D, etc.")
    )

    niveau = models.CharField(
        max_length=50,
        verbose_name=_("Niveau"),
        help_text=_("Ex: CP1, CE1, 6ème, 3ème, Terminale, etc.")
    )

    capacite_max = models.IntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        verbose_name=_("Capacité maximale"),
        help_text=_("Nombre maximum d'élèves")
    )

    # Classes d'examen officiels
    est_classe_examen = models.BooleanField(
        default=False,
        verbose_name=_("Classe d'examen officiel"),
        help_text=_("CEP (CM2), BEPC (3ème), BAC (Terminale)")
    )

    type_examen = models.CharField(
        max_length=10,
        blank=True,
        default='',
        choices=[
            ('CEP', _('CEP - Certificat d\'Études Primaires')),
            ('BEPC', _('BEPC - Brevet d\'Études du Premier Cycle')),
            ('BAC', _('BAC - Baccalauréat')),
        ],
        verbose_name=_("Type d'examen")
    )

    serie_bac = models.CharField(
        max_length=10,
        blank=True,
        default='',
        choices=[
            ('A', _('Série A - Littéraire')),
            ('C', _('Série C - Mathématiques Sciences Physiques')),
            ('D', _('Série D - Mathématiques Sciences Naturelles')),
            ('B', _('Série B - Économie')),
        ],
        verbose_name=_("Série BAC"),
        help_text=_("Si classe d'examen BAC")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Classe active")
    )

    class Meta:
        verbose_name = _("Classe")
        verbose_name_plural = _("Classes")
        ordering = ['cycle__ordre', 'nom']
        unique_together = [['etablissement', 'nom']]

    def __str__(self):
        return f"{self.nom} ({self.cycle.nom})"

    @property
    def enseignant_titulaire(self):
        """Enseignant affecté à cette classe : il signe les bulletins de notes et la liste alphabétique."""
        return (self.enseignants_titulaires.filter(is_active=True).order_by('nom', 'prenom').first())


class Salle(BaseModel):
    """Salle de classe de l'établissement : nom unique, capacité indicative. Alimente la saisie de l'emploi du temps
    (suggestions, nom canonique pour la détection des conflits, alerte de capacité) et l'occupation des salles."""

    etablissement = models.ForeignKey('etablissements.Etablissement', on_delete=models.CASCADE, related_name='salles',
                                      verbose_name=_("Établissement"))
    nom = models.CharField(max_length=50, verbose_name=_("Nom"), help_text=_("Ex : A12, Labo SVT, Salle informatique"))
    capacite = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Capacité (places)"))
    actif = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("Salle")
        verbose_name_plural = _("Salles")
        ordering = ['nom']
        unique_together = [['etablissement', 'nom']]

    def __str__(self):
        return self.nom

    @classmethod
    def canonique(cls, etab, saisie):
        """Nom tel qu'enregistré dans le référentiel pour une saisie libre (casse et espaces tolérés) ; la saisie
        inchangée si aucune salle ne correspond."""
        voulu = ' '.join((saisie or '').split()).casefold()
        if not voulu or etab is None:
            return (saisie or '').strip()
        for salle in cls.objects.filter(etablissement=etab, actif=True):
            if ' '.join(salle.nom.split()).casefold() == voulu:
                return salle.nom
        return ' '.join(saisie.split())
