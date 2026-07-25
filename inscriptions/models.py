"""
Module Inscriptions - Models
=============================
YELEN SCHOOL v3.4 - Gestion des inscriptions scolaires

Ce module contient :
1. Eleve              - Informations complètes de l'élève
2. Inscription        - Inscription annuelle d'un élève

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

import uuid
from datetime import date
from typing import Optional

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


# Importer BaseModel depuis core
try:
    from core.models import BaseModel
except ImportError:
    class BaseModel(models.Model):
        """Modèle abstrait de base."""
        id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False
        )
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)
        is_active = models.BooleanField(default=True)

        class Meta:
            abstract = True
            ordering = ['-created_at']


# ═══════════════════════════════════════════════════════════════════
# 1. ÉLÈVE
# ═══════════════════════════════════════════════════════════════════

class GenreChoices(models.TextChoices):
    """Genres disponibles pour les élèves."""
    MASCULIN = 'M', _('Masculin')
    FEMININ = 'F', _('Féminin')


class Eleve(BaseModel):
    """
    Informations complètes d'un élève.

    Chaque élève a un matricule unique au format: {CODE_ETAB}-{ANNEE}-{SEQ}
    Ex: 01-2026-5 (01 = code établissement, 2026 = année, 5 = numéro d'enregistrement)

    Note v3.4: L'âge est calculé dynamiquement (non stocké).
    """

    # Matricule unique (format: {CODE_ETAB}-{ANNEE}-{SEQ})
    matricule = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Matricule"),
        help_text=_("Format: {CODE_ETAB}-{ANNEE}-{SEQ}")
    )

    # Informations personnelles
    nom = models.CharField(
        max_length=100,
        verbose_name=_("Nom de famille")
    )

    prenom = models.CharField(
        max_length=100,
        verbose_name=_("Prénom(s)")
    )

    genre = models.CharField(
        max_length=1,
        choices=GenreChoices.choices,
        verbose_name=_("Genre")
    )

    date_naissance = models.DateField(
        verbose_name=_("Date de naissance")
    )

    lieu_naissance = models.CharField(
        max_length=200,
        verbose_name=_("Lieu de naissance")
    )

    # Nationalité et résidence
    nationalite = models.CharField(
        max_length=100,
        default='Burkinabè',
        verbose_name=_("Nationalité")
    )

    pays_residence = models.CharField(
        max_length=100,
        default='Burkina Faso',
        verbose_name=_("Pays de résidence")
    )

    # Localisation (contexte Burkina)
    province = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Province")
    )

    commune = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Commune")
    )

    village = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Village/Ville")
    )

    # Contact d'urgence
    telephone_urgence = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Téléphone d'urgence")
    )

    email = models.EmailField(
        blank=True,
        default='',
        verbose_name=_("Adresse email")
    )

    # Photo
    photo = models.ImageField(
        upload_to='eleves/photos/',
        blank=True,
        null=True,
        verbose_name=_("Photo d'identité")
    )

    # Informations familiales - Père
    nom_pere = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name=_("Nom du père")
    )

    profession_pere = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Profession du père")
    )

    # Informations familiales - Mère
    nom_mere = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name=_("Nom de la mère")
    )

    profession_mere = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Profession de la mère")
    )

    # Contact parent
    telephone_parent = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Téléphone des parents")
    )

    # Tuteur (si différent des parents)
    tuteur_nom = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name=_("Nom du tuteur")
    )

    tuteur_telephone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Téléphone du tuteur")
    )

    tuteur_adresse = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Adresse du tuteur")
    )

    # Établissement d'origine (pour les transferts)
    etablissement_origine = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("Établissement d'origine")
    )

    # Dernière classe et année (pour réinscription)
    last_classe = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("Dernière classe fréquentée")
    )

    last_annee = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Dernière année scolaire"),
        help_text=_("Ex : 2024-2025")
    )

    class Meta:
        verbose_name = _("Élève")
        verbose_name_plural = _("Élèves")
        ordering = ['nom', 'prenom']

    def __str__(self) -> str:
        return f"{self.prenom} {self.nom} ({self.matricule})"

    def get_nom_complet(self) -> str:
        """Retourne le nom complet en majuscules."""
        return f"{self.nom.upper()} {self.prenom.upper()}"

    @property
    def age(self) -> Optional[int]:
        """Calcule l'âge dynamiquement (non stocké en base)."""
        if self.date_naissance:
            today = date.today()
            return (today - self.date_naissance).days // 365
        return None

    @property
    def age_formatted(self) -> str:
        """Retourne l'âge formaté avec l'unité."""
        age = self.age
        if age is not None:
            return f"{age} ans"
        return "N/A"

    def save(self, *args, **kwargs):
        """Génère automatiquement le matricule si non défini."""
        if not self.matricule:
            self._generate_matricule()
        super().save(*args, **kwargs)

    def _generate_matricule(self):
        """
        Génère un matricule unique au format: {CODE_ETAB}-{ANNEE}-{SEQ}
        Ex: 01-2026-5

        Le code établissement est défini via l'attribut _etablissement_code
        sur l'instance (passé par la vue avant la sauvegarde).
        """
        from datetime import datetime

        # Code établissement
        etab_code = getattr(self, '_etablissement_code', None)
        if not etab_code:
            etab_code = 'XX'  # Fallback

        # Année en cours
        year = datetime.now().year

        # Compter les élèves existants pour ce code et année
        count = Eleve.objects.filter(
            matricule__startswith=f'{etab_code}-{year}-'
        ).count() + 1

        # Générer le matricule
        self.matricule = f"{etab_code}-{year}-{count}"


# ═══════════════════════════════════════════════════════════════════
# 2. INSCRIPTION ANNUELLE
# ═══════════════════════════════════════════════════════════════════

class StatutInscriptionChoices(models.TextChoices):
    """Statuts possibles d'une inscription."""
    AFFECTE = 'AFFECTE', _('Affecté')
    NON_AFFECTE = 'NON_AFFECTE', _('Non affecté')
    BOURSIER = 'BOURSIER', _('Boursier')
    EXONERE = 'EXONERE', _('Exonéré')
    ABANDON = 'ABANDON', _('Abandon')


class Inscription(BaseModel):
    """
    Inscription annuelle d'un élève dans une classe.

    Chaque élève doit être inscrit chaque année scolaire dans une classe.
    Une inscription représente une année scolaire × élève × classe.
    """

    # Élève et année scolaire
    eleve = models.ForeignKey(
        Eleve,
        on_delete=models.CASCADE,
        related_name='inscriptions',
        verbose_name=_("Élève")
    )

    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='inscriptions',
        verbose_name=_("Année scolaire")
    )

    date_inscription = models.DateField(
        default=date.today,
        verbose_name=_("Date d'inscription")
    )

    classe = models.ForeignKey(
        'parametres.Classe',
        on_delete=models.CASCADE,
        related_name='inscriptions',
        verbose_name=_("Classe")
    )

    # Statut administratif
    statut = models.CharField(
        max_length=20,
        choices=StatutInscriptionChoices.choices,
        default=StatutInscriptionChoices.AFFECTE,
        verbose_name=_("Statut")
    )

    # Statut élève (Interne, Externe, Demi-pensionnaire…) — détermine les tarifs applicables
    statut_eleve = models.ForeignKey(
        'parametres.StatutEleve',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inscriptions',
        verbose_name=_("Statut élève"),
        help_text=_("Détermine les tarifs de scolarité applicables à cet élève")
    )

    est_exonere = models.BooleanField(
        default=False,
        verbose_name=_("Exonéré")
    )

    raison_exoneration = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Raison d'exonération")
    )

    # Redoublement
    est_redoublant = models.BooleanField(
        default=False,
        verbose_name=_("Redoublant")
    )

    classe_redoublee = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Classe redoublée")
    )

    # Informations financières
    numero_recu = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("Numéro de reçu")
    )

    # Observations
    observations = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Observations")
    )

    class Meta:
        verbose_name = _("Inscription")
        verbose_name_plural = _("Inscriptions")
        ordering = ['-annee_scolaire', 'eleve__nom', 'eleve__prenom']
        # Un élève ne peut avoir qu'une seule inscription par année scolaire
        unique_together = [['eleve', 'annee_scolaire']]

    def __str__(self) -> str:
        return (
            f"{self.eleve} - {self.classe.nom} - "
            f"{self.get_statut_display()} - {self.annee_scolaire.libelle}"
        )

    def clean(self):
        """Validation métier."""
        from django.core.exceptions import ValidationError

        # Vérifier que l'élève n'est pas déjà inscrit cette année
        if not self.pk:
            existing = Inscription.objects.filter(
                eleve=self.eleve,
                annee_scolaire=self.annee_scolaire
            )
            if existing.exists():
                raise ValidationError(
                    _(f"Cet élève est déjà inscrit pour "
                      f"l'année scolaire {self.annee_scolaire.libelle}")
                )

        # Raison d'exonération obligatoire si exonéré
        if self.est_exonere and not self.raison_exoneration.strip():
            raise ValidationError(
                {'raison_exoneration': _("La raison d'exonération est obligatoire si l'élève est exonéré.")}
            )

        # Classe redoublée obligatoire si redoublant
        if self.est_redoublant and not self.classe_redoublee:
            raise ValidationError(
                {'classe_redoublee': _("La classe redoublée est obligatoire si l'élève est redoublant.")}
            )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════
# 3. ÉVÉNEMENT DE PARCOURS
# ═══════════════════════════════════════════════════════════════════

class EvenementParcours(BaseModel):
    """
    Annotation manuelle d'une transition dans le parcours scolaire d'un élève.

    Les transitions PASSAGE/REDOUBLEMENT sont calculées automatiquement
    depuis les inscriptions. Ce modèle sert à enrichir ces données avec :
    - L'établissement d'origine/destination pour les transferts
    - Le nom du diplôme obtenu en fin de cycle
    - Un motif de redoublement ou d'abandon
    - Toute note libre sur la transition
    """

    class TypeEvenement(models.TextChoices):
        PASSAGE         = 'PASSAGE',           _('Passage en classe supérieure')
        REDOUBLEMENT    = 'REDOUBLEMENT',       _('Redoublement')
        TRANSFERT_ENTRANT = 'TRANSFERT_ENTRANT', _('Transfert entrant')
        TRANSFERT_SORTANT = 'TRANSFERT_SORTANT', _('Transfert sortant')
        ABANDON         = 'ABANDON',            _('Abandon scolaire')
        DIPLOME         = 'DIPLOME',            _('Diplôme obtenu')
        AUTRE           = 'AUTRE',              _('Autre')

    eleve = models.ForeignKey(
        Eleve,
        on_delete=models.CASCADE,
        related_name='evenements_parcours',
        verbose_name=_("Élève")
    )

    type_evenement = models.CharField(
        max_length=20,
        choices=TypeEvenement.choices,
        verbose_name=_("Type d'événement")
    )

    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='evenements_parcours',
        verbose_name=_("Année scolaire concernée")
    )

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evenements',
        verbose_name=_("Inscription liée")
    )

    date_evenement = models.DateField(
        default=date.today,
        verbose_name=_("Date")
    )

    motif = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Motif / Observations"),
        help_text=_("Raison du redoublement, nom du diplôme, établissement de destination…")
    )

    etablissement_transfert = models.CharField(
        max_length=250,
        blank=True,
        default='',
        verbose_name=_("Établissement (transfert)"),
        help_text=_("Établissement d'origine ou de destination pour les transferts")
    )

    enregistre_par = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evenements_parcours_enregistres',
        verbose_name=_("Enregistré par")
    )

    class Meta:
        verbose_name = _("Événement de parcours")
        verbose_name_plural = _("Événements de parcours")
        ordering = ['annee_scolaire__date_debut', 'date_evenement']

    def __str__(self):
        return f"{self.get_type_evenement_display()} — {self.eleve} — {self.annee_scolaire}"


# ═══════════════════════════════════════════════════════════════════
# 4. TRANSFERT INTER-ÉTABLISSEMENTS
# ═══════════════════════════════════════════════════════════════════

class TransfertEleve(BaseModel):
    """
    Demande de transfert d'un élève vers un autre établissement.

    Workflow :
      EN_ATTENTE → APPROUVE (inscription marquée ABANDON + EvenementParcours)
                 → REFUSE   (inscription inchangée)
    Un transfert APPROUVE génère le dossier PDF téléchargeable.
    """

    class StatutChoices(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', _('En attente')
        APPROUVE   = 'APPROUVE',   _('Approuvé')
        REFUSE     = 'REFUSE',     _('Refusé')

    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.CASCADE,
        related_name='transferts',
        verbose_name=_("Inscription concernée"),
    )

    etablissement_destination = models.CharField(
        max_length=250,
        verbose_name=_("Établissement de destination"),
    )

    motif = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Motif du transfert"),
    )

    statut = models.CharField(
        max_length=20,
        choices=StatutChoices.choices,
        default=StatutChoices.EN_ATTENTE,
        verbose_name=_("Statut"),
    )

    date_demande = models.DateField(
        default=date.today,
        verbose_name=_("Date de la demande"),
    )

    date_traitement = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de traitement"),
    )

    demandeur = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferts_demandes',
        verbose_name=_("Demandé par"),
    )

    traite_par = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferts_traites',
        verbose_name=_("Traité par"),
    )

    notes_admin = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Notes administratives"),
    )

    class Meta:
        verbose_name = _("Transfert inter-établissements")
        verbose_name_plural = _("Transferts inter-établissements")
        ordering = ['-date_demande']

    def __str__(self):
        return f"Transfert {self.inscription.eleve} → {self.etablissement_destination} ({self.get_statut_display()})"
