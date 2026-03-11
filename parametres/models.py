"""
Module Paramètres - Models
===========================
YELEN SCHOOL v3.4 - Configuration centralisée de l'établissement scolaire

Ce module contient TOUS les paramètres de configuration nécessaires
au fonctionnement de l'application. Il doit être configuré EN PREMIER
car tous les autres modules en dépendent.

14 modèles :
1. IdentiteEtablissement - Logo, coordonnées, signature
2. Cycle - Préscolaire/Primaire/Post-primaire/Secondaire
3. Classe - Classes par niveau
4. Poste - Postes du personnel
5. LocalisationPoste - Localisation géographique des postes
6. StatutEleve - Statuts des élèves (Affecté, Boursier, etc.)
7. RubriquePaiement - Types de frais (Scolarité, Inscription, etc.)
8. TarifScolarite - Matrice tarifaire (classe × statut × rubrique)
9. AppreciationConduite - Grille d'appréciation comportementale
10. AnneeScolaire - Gestion des années scolaires
11. Discipline - Matières par cycle avec coefficients
12. PeriodeEvaluation - Trimestres ou semestres
13. TypeDocument - Types de documents signables (v3.4)
14. SignataireDocument - Signataires par cycle × document (v3.4)

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

import uuid
from datetime import date
from typing import Optional

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Importer BaseModel depuis core
try:
    from core.models import BaseModel
except ImportError:
    # Si core n'existe pas, définir BaseModel ici
    class BaseModel(models.Model):
        """Modèle abstrait de base."""
        id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False
        )
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)
        
        class Meta:
            abstract = True
            ordering = ['-created_at']


# ═══════════════════════════════════════════════════════════════════
# 1. IDENTITÉ ÉTABLISSEMENT (Singleton)
# ═══════════════════════════════════════════════════════════════════

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
        verbose_name=_("N° Agrément MENA"),
        help_text=_("Numéro officiel d'agrément du Ministère")
    )
    
    date_agrement = models.DateField(
        verbose_name=_("Date d'agrément")
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
        max_length=20,
        verbose_name=_("Téléphone")
    )
    
    email = models.EmailField(
        verbose_name=_("Email")
    )
    
    site_web = models.URLField(
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


# ═══════════════════════════════════════════════════════════════════
# 2. CYCLE SCOLAIRE
# ═══════════════════════════════════════════════════════════════════
from django.utils.translation import gettext_lazy as _

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
    related_name='cycles_parametres',  # <-- nom unique qui n'existe pas encore
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
# ═══════════════════════════════════════════════════════════════════
# 3. CLASSE
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 4. POSTE (Personnel)
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 5. LOCALISATION POSTE
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 6. STATUT ÉLÈVE
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 7. RUBRIQUE PAIEMENT
# ═══════════════════════════════════════════════════════════════════

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
        max_length=100,
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
    
    class Meta:
        verbose_name = _("Rubrique de Paiement")
        verbose_name_plural = _("Rubriques de Paiement")
        ordering = ['ordre', 'nom']
        unique_together = [['etablissement', 'code']]
    
    def __str__(self):
        return f"{self.nom} ({self.code})"


# ═══════════════════════════════════════════════════════════════════
# 8. TARIF SCOLARITÉ (Matrice tarifaire)
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 9. APPRÉCIATION CONDUITE
# ═══════════════════════════════════════════════════════════════════

class AppreciationConduite(BaseModel):
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
    
    note_min = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name=_("Note minimale"),
        help_text=_("Note minimale pour cette appréciation sur 20")
    )
    
    note_max = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=20,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name=_("Note maximale"),
        help_text=_("Note maximale pour cette appréciation sur 20")
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
        verbose_name = _("Appréciation Conduite")
        verbose_name_plural = _("Appréciations Conduite")
        ordering = ['-note_min']
    
    def __str__(self):
        return f"{self.libelle} ({self.note_min}-{self.note_max})"


# ═══════════════════════════════════════════════════════════════════
# 10. ANNÉE SCOLAIRE
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 11. DISCIPLINE (Matières)
# ═══════════════════════════════════════════════════════════════════

class Discipline(BaseModel):
    """
    Matières enseignées par cycle.
    
    Chaque matière a un coefficient qui varie selon le cycle.
    Ex: Mathématiques coeff 4 en Terminale C, coeff 2 en Terminale A.
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
    
    coefficient = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_("Coefficient"),
        help_text=_("Coefficient officiel MENA")
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
        return f"{self.nom} ({self.cycle.nom}) - Coeff. {self.coefficient}"


# ═══════════════════════════════════════════════════════════════════
# 12. PÉRIODE ÉVALUATION (Trimestres/Semestres)
# ═══════════════════════════════════════════════════════════════════

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
    
    class Meta:
        verbose_name = _("Période d'Évaluation")
        verbose_name_plural = _("Périodes d'Évaluation")
        ordering = ['annee_scolaire', 'numero']
        unique_together = [['annee_scolaire', 'numero']]
    
    def __str__(self):
        return f"{self.nom} ({self.annee_scolaire.libelle})"


# ═══════════════════════════════════════════════════════════════════
# 13. TYPE DOCUMENT (v3.4)
# ═══════════════════════════════════════════════════════════════════

class TypeDocument(BaseModel):
    """
    Types de documents pouvant porter une signature.
    
    9 types prédéfinis (fixtures) :
    - CERT_SCOL : Certificat de Scolarité
    - BULLETIN : Bulletin de Notes
    - RECU_PAIEMENT : Reçu de Paiement
    - AUTORISATION : Autorisation d'Absence
    - ATTESTATION : Attestation de Non-Redevabilité
    - CURSUS : Cursus Scolaire Complet
    - CARTE_ID : Carte d'Identité Scolaire
    - LISTE_CLASSE : Liste Alphabétique de Classe
    - LISTE_PERSONNEL : Liste du Personnel
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Code"),
        help_text=_("Ex: CERT_SCOL, BULLETIN, RECU_PAIEMENT")
    )
    
    libelle = models.CharField(
        max_length=100,
        verbose_name=_("Libellé"),
        help_text=_("Ex: Certificat de Scolarité")
    )
    
    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description")
    )
    
    actif = models.BooleanField(
        default=True,
        verbose_name=_("Type actif")
    )
    
    class Meta:
        verbose_name = _("Type de Document")
        verbose_name_plural = _("Types de Documents")
        ordering = ['libelle']
    
    def __str__(self):
        return f"{self.libelle} ({self.code})"


# ═══════════════════════════════════════════════════════════════════
# 14. SIGNATAIRE DOCUMENT (v3.4)
# ═══════════════════════════════════════════════════════════════════

class SignataireDocumentManager(models.Manager):
    """Manager pour les signataires."""
    
    @classmethod
    def get_signataire(
        cls,
        cycle,
        type_document,
        annee_scolaire
    ) -> Optional['SignataireDocument']:
        """
        Récupère le signataire pour un cycle × document × année.
        
        Args:
            cycle: Instance de Cycle
            type_document: Instance de TypeDocument
            annee_scolaire: Instance d'AnneeScolaire
            
        Returns:
            SignataireDocument ou None si non trouvé
        """
        return cls.objects.filter(
            cycle=cycle,
            type_document=type_document,
            annee_scolaire=annee_scolaire,
            actif=True
        ).first()


class SignataireDocument(BaseModel):
    """
    Signataires paramétrables par Cycle × Type Document × Année.
    
    Permet de configurer qui signe quel document pour chaque cycle.
    Ex: Le Directeur du Primaire signe les bulletins du Primaire,
        Le Proviseur du Secondaire signe les bulletins du Secondaire.
    
    Contrainte unique : Un seul signataire actif par (cycle, document, année).
    """
    
    cycle = models.ForeignKey(
        Cycle,
        on_delete=models.CASCADE,
        related_name='signataires',
        verbose_name=_("Cycle")
    )
    
    type_document = models.ForeignKey(
        TypeDocument,
        on_delete=models.CASCADE,
        related_name='signataires',
        verbose_name=_("Type de Document")
    )
    
    # FK vers le module personnel (à créer plus tard)
    membre_personnel = models.ForeignKey(
        'personnel.MembrePersonnel',
        on_delete=models.CASCADE,
        related_name='signatures_documents',
        verbose_name=_("Membre du Personnel Signataire")
    )
    
    titre_honorifique = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("Titre Honorifique"),
        help_text=_("Ex: M., Mme, Dr, Prof., M. le Directeur")
    )
    
    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='signataires_documents',
        verbose_name=_("Année Scolaire")
    )
    
    actif = models.BooleanField(
        default=True,
        verbose_name=_("Signataire actif")
    )
    
    # Manager personnalisé
    objects = SignataireDocumentManager()
    
    class Meta:
        verbose_name = _("Signataire de Document")
        verbose_name_plural = _("Signataires de Documents")
        ordering = ['cycle', 'type_document']
        unique_together = [['cycle', 'type_document', 'annee_scolaire']]
    
    def __str__(self):
        return (
            f"{self.cycle.nom} - {self.type_document.libelle} - "
            f"{self.membre_personnel}"
        )
    
    def get_nom_complet_avec_titre(self) -> str:
        """
        Retourne le nom complet du signataire avec titre.
        
        Returns:
            str: "M. le Directeur Jean OUÉDRAOGO"
        """
        if self.titre_honorifique:
            return f"{self.titre_honorifique} {self.membre_personnel.get_nom_complet()}"
        return self.membre_personnel.get_nom_complet()
