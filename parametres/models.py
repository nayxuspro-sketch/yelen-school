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
9. AppreciationMoyenneSecondaire - Grille d'appréciation des moyennes pour le secondaire
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

from core.fields import URLFieldHTTPS


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


# ═══════════════════════════════════════════════════════════════════
# 2. CYCLE SCOLAIRE
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 9. APPRÉCIATION CONDUITE
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 9b. APPRÉCIATION MOYENNE PRIMAIRE
# ═══════════════════════════════════════════════════════════════════

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
# 11. CATÉGORIE DISCIPLINE
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 11. DISCIPLINE (Matières)
# ═══════════════════════════════════════════════════════════════════

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
    
    10 types prédéfinis (fixtures) :
    - CERT_SCOL        : Certificat de Scolarité
    - BULLETIN         : Bulletin de Notes
    - RECU_PAIEMENT    : Reçu de Paiement
    - AUTORISATION     : Autorisation d'Absence
    - ATTESTATION      : Attestation de Non-Redevabilité
    - CURSUS           : Cursus Scolaire Complet
    - CARTE_ID         : Carte d'Identité Scolaire
    - LISTE_CLASSE     : Liste Alphabétique de Classe
    - LISTE_PERSONNEL  : Liste du Personnel
    - LISTE_REDEVABLES : Liste des Redevables
    """
    
    class CategorieChoices(models.TextChoices):
        SCOLARITE = 'SCOLARITE', _('Scolarité')
        FINANCE = 'FINANCE', _('Finance')
        ADMINISTRATIF = 'ADMINISTRATIF', _('Administratif')
        PEDAGOGIE = 'PEDAGOGIE', _('Pédagogie')
        PERSONNEL = 'PERSONNEL', _('Personnel')
    
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
    
    categorie = models.CharField(
        max_length=20,
        choices=CategorieChoices.choices,
        default=CategorieChoices.SCOLARITE,
        verbose_name=_("Catégorie")
    )
    
    cycle = models.ForeignKey(
        'parametres.Cycle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Cycle"),
        help_text=_("Laisser vide pour applies à tous les cycles")
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
# 14. TYPE SANCTION
# ═══════════════════════════════════════════════════════════════════

class TypeSanction(BaseModel):
    """
    Types de sanctions disciplinaires configurables.
    
    Ex: AVERTISSEMENT, BLAME, EXCLUSION_TEMP, etc.
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Code"),
        help_text=_("Ex: AVERTISSEMENT, BLAME, EXCLUSION_TEMP")
    )
    
    libelle = models.CharField(
        max_length=100,
        verbose_name=_("Libellé"),
        help_text=_("Ex: Avertissement, Blâme, Exclusion temporaire")
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    
    actif = models.BooleanField(
        default=True,
        verbose_name=_("Type actif")
    )

    points_defaut = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_("Points par défaut"),
        help_text=_("Valeur pré-remplie lors de la création d'une sanction (négatif = pénalité).")
    )

    class Meta:
        verbose_name = _("Type de Sanction")
        verbose_name_plural = _("Types de Sanctions")
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} ({self.code})"


# ═══════════════════════════════════════════════════════════════════
# 15. SIGNATAIRE DOCUMENT (v3.4)
# ═══════════════════════════════════════════════════════════════════

class SignataireDocumentManager(models.Manager):
    """Manager pour les signataires."""

    def get_signataire(
        self,
        cycle,
        type_document,
        annee_scolaire
    ) -> Optional['SignataireDocument']:
        """
        Récupère le signataire pour un cycle × document × année.

        Stratégie de recherche avec repli progressif :
        1. Correspondance exacte (cycle + document + année)
        2. Repli : même cycle + même document, n'importe quelle année → prend le plus récent
        3. Repli : même document, n'importe quel cycle/année → prend le plus récent

        Args:
            cycle: Instance de Cycle
            type_document: Instance de TypeDocument
            annee_scolaire: Instance d'AnneeScolaire

        Returns:
            SignataireDocument ou None si non trouvé
        """
        if type_document is not None:
            # 1. Correspondance exacte
            sig = self.filter(
                cycle=cycle,
                type_document=type_document,
                annee_scolaire=annee_scolaire,
                actif=True
            ).first()
            if sig:
                return sig

            # 2. Même cycle + même document, toute année
            if cycle is not None:
                sig = self.filter(
                    cycle=cycle,
                    type_document=type_document,
                    actif=True
                ).order_by('-updated_at').first()
                if sig:
                    return sig

            # 3. Même document, tout cycle
            sig = self.filter(
                type_document=type_document,
                actif=True
            ).order_by('-updated_at').first()
            if sig:
                return sig

        # 4. Même cycle, tout document
        if cycle is not None:
            sig = self.filter(
                cycle=cycle,
                actif=True
            ).order_by('-updated_at').first()
            if sig:
                return sig

        # 5. Tout signataire actif (dernier recours absolu)
        return self.filter(actif=True).order_by('-updated_at').first()


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
    
    # FK vers le module personnel (sera migré après personnel)
    # Temporairement en CharField
    membre_personnel_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("ID Membre du Personnel Signataire")
    )
    
    @property
    def membre_personnel(self):
        """Retourne le membre du personnel (après migration FK)."""
        if hasattr(self, '_membre_personnel_cache'):
            return self._membre_personnel_cache
        return None
    
    def get_membre_personnel(self):
        """Récupère le membre du personnel depuis la base."""
        from personnel.models import MembrePersonnel
        if self.membre_personnel_id:
            try:
                return MembrePersonnel.objects.get(id=self.membre_personnel_id)
            except MembrePersonnel.DoesNotExist:
                return None
        return None
    
    def set_membre_personnel(self, personnel):
        """Définit le membre du personnel."""
        self.membre_personnel_id = personnel.id if personnel else None
        self._membre_personnel_cache = personnel
    
    titre = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Titre / Fonction (ancien)"),
        help_text=_("Champ hérité — utiliser 'fonction' à la place")
    )

    titre_honorifique = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("Titre Honorifique (ancien)"),
        help_text=_("Champ hérité — utiliser 'titres_honorifiques' à la place")
    )

    fonction = models.CharField(
        max_length=150,
        blank=True,
        default='Le Directeur',
        verbose_name=_("Fonction"),
        help_text=_("Fonction affichée entre la date et le nom, "
                    "ex: 'Directeur des Études', 'Le Proviseur', 'La Directrice'")
    )

    titres_honorifiques = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Titres Honorifiques"),
        help_text=_("Liste ordonnée de titres honorifiques affichés sous le nom, "
                    "ex: [\"Chevalier de l'Ordre du Mérite\", "
                    "\"Chevalier des Palmes Académiques\"]")
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
        personnel = self.get_membre_personnel()
        personnel_str = str(personnel) if personnel else "Aucun"
        return (
            f"{self.cycle.nom} - {self.type_document.libelle} - "
            f"{personnel_str}"
        )
    
    def get_nom_complet_avec_titre(self) -> str:
        """
        Retourne le nom complet du signataire avec titre.

        Returns:
            str: "M. le Directeur Jean OUÉDRAOGO"
        """
        personnel = self.get_membre_personnel()
        if not personnel:
            return self.titre_honorifique or ""

        if self.titre_honorifique:
            return f"{self.titre_honorifique} {personnel.get_nom_complet()}"
        return personnel.get_nom_complet()


# ═══════════════════════════════════════════════════════════════════
# 15b. CO-SIGNATAIRES
# ═══════════════════════════════════════════════════════════════════

class CoSignataire(BaseModel):
    """
    Signataire(s) supplémentaire(s) pour un document.

    Lié au SignataireDocument principal (le 1er signataire).
    Permet d'avoir, ex. : Directeur (principal) + Censeur (co).

    Le rendu PDF aligne tous les signataires côte à côte.
    """

    signataire_principal = models.ForeignKey(
        SignataireDocument,
        on_delete=models.CASCADE,
        related_name='co_signataires',
        verbose_name=_("Signataire principal")
    )

    membre_personnel_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("ID Membre du Personnel")
    )

    fonction = models.CharField(
        max_length=150,
        default='',
        blank=True,
        verbose_name=_("Fonction"),
        help_text=_("Ex : 'Le Censeur', 'La Directrice des Études'")
    )

    titres_honorifiques = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Titres honorifiques")
    )

    ordre = models.PositiveSmallIntegerField(
        default=2,
        verbose_name=_("Ordre d'affichage"),
        help_text=_("1 = premier à gauche ; le signataire principal est toujours en position 1")
    )

    actif = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Co-Signataire")
        verbose_name_plural = _("Co-Signataires")
        ordering = ['ordre']

    def __str__(self):
        m = self.get_membre_personnel()
        nom = str(m) if m else "—"
        return f"{self.fonction or 'Co-signataire'} : {nom}"

    def get_membre_personnel(self):
        """Récupère le membre du personnel depuis la base."""
        from personnel.models import MembrePersonnel
        if self.membre_personnel_id:
            try:
                return MembrePersonnel.objects.get(id=self.membre_personnel_id)
            except MembrePersonnel.DoesNotExist:
                return None
        return None


# ═══════════════════════════════════════════════════════════════════
# 16. TITRE FONCTION PERSONNEL
# ═══════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════
# 17. TITRE HONORIFIQUE PERSONNEL
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# CALENDRIER SCOLAIRE
# ═══════════════════════════════════════════════════════════════════

class EvenementCalendrier(BaseModel):
    """
    Événements du calendrier scolaire : congés, jours fériés,
    examens nationaux, réunions pédagogiques, fermetures exceptionnelles.

    Rattaché à une AnneeScolaire pour filtrage et affichage mensuel.
    """

    class TypeChoices(models.TextChoices):
        CONGE          = 'CONGE',          'Congé scolaire'
        JOUR_FERIE     = 'JOUR_FERIE',     'Jour férié'
        EXAMEN         = 'EXAMEN',         'Examen / Évaluation'
        REUNION        = 'REUNION',        'Réunion pédagogique'
        FERMETURE      = 'FERMETURE',      'Fermeture exceptionnelle'
        AUTRE          = 'AUTRE',          'Autre événement'

    # Couleur CSS par type — utilisée dans le calendrier
    COULEUR_PAR_TYPE = {
        'CONGE':      '#3b82f6',   # bleu
        'JOUR_FERIE': '#f59e0b',   # ambre
        'EXAMEN':     '#ef4444',   # rouge
        'REUNION':    '#8b5cf6',   # violet
        'FERMETURE':  '#6b7280',   # gris
        'AUTRE':      '#10b981',   # vert
    }

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='evenements_calendrier',
        verbose_name=_("Établissement"),
    )
    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='evenements',
        verbose_name=_("Année scolaire"),
    )
    titre = models.CharField(
        max_length=150,
        verbose_name=_("Titre"),
    )
    type = models.CharField(
        max_length=20,
        choices=TypeChoices.choices,
        default=TypeChoices.AUTRE,
        verbose_name=_("Type"),
    )
    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_fin = models.DateField(verbose_name=_("Date de fin"))
    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description"),
    )
    journee_complete = models.BooleanField(
        default=True,
        verbose_name=_("Journée complète"),
    )

    class Meta:
        verbose_name = _("Événement calendrier")
        verbose_name_plural = _("Événements calendrier")
        ordering = ['date_debut']
        indexes = [
            models.Index(fields=['etablissement', 'annee_scolaire', 'date_debut']),
        ]

    def __str__(self):
        return f"{self.titre} ({self.date_debut})"

    @property
    def couleur(self):
        return self.COULEUR_PAR_TYPE.get(self.type, '#10b981')

    @property
    def nb_jours(self):
        return (self.date_fin - self.date_debut).days + 1


class ModeleMessage(BaseModel):
    """
    Modèles de messages personnalisables pour les notifications SMS/email.

    Variables disponibles selon le type :
      BULLETIN  : {nom_eleve}, {classe}, {trimestre}, {etablissement}
      ABSENCE   : {nom_eleve}, {date}, {matiere}, {etablissement}
      RETARD    : {nom_eleve}, {date}, {matiere}, {etablissement}
      PAIEMENT  : {nom_eleve}, {montant}, {rubrique}, {etablissement}
      REUNION   : {date}, {heure}, {lieu}, {objet}, {etablissement}
    """

    class TypeChoices(models.TextChoices):
        BULLETIN = 'BULLETIN', 'Disponibilité du bulletin'
        ABSENCE  = 'ABSENCE',  'Absence élève'
        RETARD   = 'RETARD',   'Retard élève'
        PAIEMENT = 'PAIEMENT', 'Relance paiement'
        REUNION  = 'REUNION',  'Réunion parents d\'élèves'

    DEFAUTS = {
        'BULLETIN': (
            "Bonjour, le bulletin de {nom_eleve} ({classe}) pour le {trimestre} "
            "est disponible. Contactez {etablissement} pour le consulter."
        ),
        'ABSENCE': (
            "Bonjour, votre enfant {nom_eleve} a été absent(e) le {date}"
            "{matiere}. Contactez {etablissement} pour régularisation."
        ),
        'RETARD': (
            "Bonjour, votre enfant {nom_eleve} est arrivé(e) en retard le {date}"
            "{matiere}. — {etablissement}"
        ),
        'PAIEMENT': (
            "Bonjour, un rappel de paiement : {rubrique} de {montant} FCFA "
            "pour {nom_eleve} est en attente. Contactez {etablissement}."
        ),
        'REUNION': (
            "Bonjour, une réunion parents-élèves est prévue le {date} à {heure} "
            "({lieu}). Objet : {objet}. — {etablissement}"
        ),
    }

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='modeles_messages',
        verbose_name=_("Établissement"),
    )
    type = models.CharField(
        max_length=20,
        choices=TypeChoices.choices,
        verbose_name=_("Type de message"),
    )
    contenu_sms = models.TextField(
        verbose_name=_("Contenu SMS"),
        help_text=_("Max 160 caractères pour un SMS simple. Variables : {nom_eleve}, {classe}, etc."),
    )
    actif = models.BooleanField(
        default=True,
        verbose_name=_("Actif"),
    )

    class Meta:
        verbose_name = _("Modèle de message")
        verbose_name_plural = _("Modèles de messages")
        ordering = ['type']
        unique_together = [['etablissement', 'type']]

    def __str__(self):
        return f"{self.get_type_display()} — {self.etablissement}"

    @classmethod
    def get_contenu(cls, etablissement, type_msg, variables):  # noqa: E501 (original method continues)
        """
        Retourne le contenu SMS personnalisé pour ce type,
        ou le message par défaut si aucun modèle n'est configuré.
        """
        try:
            modele = cls.objects.get(etablissement=etablissement, type=type_msg, actif=True)
            contenu = modele.contenu_sms
        except cls.DoesNotExist:
            contenu = cls.DEFAUTS.get(type_msg, '')
        try:
            return contenu.format(**variables)
        except KeyError:
            return contenu


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


# ═══════════════════════════════════════════════════════════════════
# DÉCLENCHEURS SMS AUTOMATIQUES
# ═══════════════════════════════════════════════════════════════════

class DeclencheurSMS(BaseModel):
    """
    Configuration d'un envoi SMS automatique planifié.

    Chaque déclencheur correspond à un type d'événement (absence, échéancier, résultats).
    L'exécution est déclenchée par la commande management `sms_auto` ou manuellement
    depuis l'interface Paramètres.

    Types disponibles :
      ABSENCE_J1  — SMS J+1 pour absences non justifiées de la veille
      ECHEANCIER  — Rappel N jours avant l'échéance impayée
      RESULTATS   — SMS à la publication d'un nouveau bulletin
    """

    class TypeChoices(models.TextChoices):
        ABSENCE_J1 = 'ABSENCE_J1', _('Absences non justifiées (J+1)')
        ECHEANCIER = 'ECHEANCIER', _("Rappel d'échéancier")
        RESULTATS  = 'RESULTATS',  _('Bulletin disponible')

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='declencheurs_sms',
        verbose_name=_("Établissement"),
    )

    type_declencheur = models.CharField(
        max_length=20,
        choices=TypeChoices.choices,
        verbose_name=_("Type de déclencheur"),
    )

    actif = models.BooleanField(
        default=False,
        verbose_name=_("Actif"),
    )

    jours_avant = models.PositiveSmallIntegerField(
        default=3,
        verbose_name=_("Jours avant l'échéance"),
        help_text=_("Utilisé pour le type Échéancier : envoyer le rappel N jours avant la date limite."),
    )

    last_run = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Dernière exécution"),
    )

    nb_envoyes_total = models.PositiveIntegerField(
        default=0,
        verbose_name=_("SMS envoyés au total"),
    )

    class Meta:
        verbose_name = _("Déclencheur SMS automatique")
        verbose_name_plural = _("Déclencheurs SMS automatiques")
        unique_together = [['etablissement', 'type_declencheur']]
        ordering = ['type_declencheur']

    def __str__(self):
        statut = "✅" if self.actif else "⏸"
        return f"{statut} {self.get_type_declencheur_display()} — {self.etablissement}"
