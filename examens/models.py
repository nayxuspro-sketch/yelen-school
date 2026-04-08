"""
Module Examens - Models
========================
YELEN SCHOOL v3.4 - Gestion des examens officiels

Ce module couvre les examens officiels du système éducatif burkinabè :
- CEP (Certificat d'Études Primaires) — Classe CM2
- BEPC (Brevet d'Études du Premier Cycle) — Classe 3ème
- BAC (Baccalauréat) — Classe Terminale

Modèles :
1. SessionExamen       - Session d'examen (CEP 2025-2026, BEPC 2026, etc.)
2. CentreExamen        - Centre d'écriture et/ou de délibération
3. InscriptionExamen   - Inscription d'un élève à une session
4. SalleExamen         - Salles et leur composition
5. PlacementExamen     - Placement d'un candidat dans une salle

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


# ═══════════════════════════════════════════════════════════════════
# 1. SESSION D'EXAMEN
# ═══════════════════════════════════════════════════════════════════

class SessionExamen(BaseModel):
    """
    Session officielle d'examen (CEP, BEPC, BAC) pour une année scolaire.

    Chaque session correspond à un type d'examen et une année scolaire.
    Ex : "CEP 2025-2026", "BEPC session 2026", "BAC série D 2026"
    """

    class TypeExamenChoices(models.TextChoices):
        CEP = 'CEP', _('CEP — Certificat d\'Études Primaires')
        BEPC = 'BEPC', _('BEPC — Brevet du Premier Cycle')
        BAC = 'BAC', _('BAC — Baccalauréat')
        AUTRES = 'AUTRES', _('Autre examen')

    class StatutChoices(models.TextChoices):
        PLANIFIEE = 'PLANIFIEE', _('Planifiée')
        EN_COURS = 'EN_COURS', _('En cours')
        TERMINEE = 'TERMINEE', _('Terminée')
        DELIBEREE = 'DELIBEREE', _('Délibérée')

    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='sessions_examen',
        verbose_name=_("Année scolaire")
    )

    type_examen = models.CharField(
        max_length=10,
        choices=TypeExamenChoices.choices,
        verbose_name=_("Type d'examen")
    )

    libelle = models.CharField(
        max_length=100,
        verbose_name=_("Libellé"),
        help_text=_("Ex: CEP 2025-2026, BEPC Session 2026")
    )

    date_debut = models.DateField(verbose_name=_("Date de début des épreuves"))
    date_fin = models.DateField(verbose_name=_("Date de fin des épreuves"))
    date_deliberation = models.DateField(
        blank=True, null=True,
        verbose_name=_("Date de délibération")
    )

    statut = models.CharField(
        max_length=15,
        choices=StatutChoices.choices,
        default=StatutChoices.PLANIFIEE,
        verbose_name=_("Statut")
    )

    observations = models.TextField(
        blank=True, default='',
        verbose_name=_("Observations")
    )

    class Meta:
        verbose_name = _("Session d'Examen")
        verbose_name_plural = _("Sessions d'Examens")
        ordering = ['-date_debut']
        unique_together = [['annee_scolaire', 'type_examen']]

    def __str__(self):
        return f"{self.libelle} ({self.get_type_examen_display()})"


# ═══════════════════════════════════════════════════════════════════
# 2. CENTRE D'EXAMEN
# ═══════════════════════════════════════════════════════════════════

class CentreExamen(BaseModel):
    """
    Centre d'écriture et/ou de délibération d'une session.

    Un établissement peut accueillir des candidats d'autres écoles.
    """

    session = models.ForeignKey(
        SessionExamen,
        on_delete=models.CASCADE,
        related_name='centres',
        verbose_name=_("Session")
    )

    nom = models.CharField(
        max_length=200,
        verbose_name=_("Nom du centre"),
        help_text=_("Ex: Centre CEP de l'École A de Koudougou")
    )

    code_centre = models.CharField(
        max_length=20,
        verbose_name=_("Code du centre")
    )

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='centres_examen',
        verbose_name=_("Établissement hôte")
    )

    adresse = models.TextField(
        blank=True, default='',
        verbose_name=_("Adresse")
    )

    capacite = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Capacité d'accueil")
    )

    class Meta:
        verbose_name = _("Centre d'Examen")
        verbose_name_plural = _("Centres d'Examens")
        ordering = ['session', 'code_centre']
        unique_together = [['session', 'code_centre']]

    def __str__(self):
        return f"{self.code_centre} — {self.nom}"


# ═══════════════════════════════════════════════════════════════════
# 3. INSCRIPTION À L'EXAMEN
# ═══════════════════════════════════════════════════════════════════

class InscriptionExamen(BaseModel):
    """
    Inscription d'un élève (via son Inscription annuelle) à une session d'examen.

    Contient le numéro de table et le centre d'affectation.
    """

    class StatutChoices(models.TextChoices):
        INSCRIT = 'INSCRIT', _('Inscrit')
        ADMIS = 'ADMIS', _('Admis')
        AJOURNÉ = 'AJOURNE', _('Ajourné')
        ABSENT = 'ABSENT', _('Absent le jour J')
        EXCLU = 'EXCLU', _('Exclu')

    session = models.ForeignKey(
        SessionExamen,
        on_delete=models.CASCADE,
        related_name='inscriptions_examen',
        verbose_name=_("Session")
    )

    inscription = models.ForeignKey(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='inscriptions_examen',
        verbose_name=_("Inscription scolaire")
    )

    centre = models.ForeignKey(
        CentreExamen,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='candidats',
        verbose_name=_("Centre d'affectation")
    )

    numero_table = models.CharField(
        max_length=20,
        blank=True, default='',
        verbose_name=_("Numéro de table"),
        help_text=_("Numéro attribué au candidat pour l'examen")
    )

    statut = models.CharField(
        max_length=10,
        choices=StatutChoices.choices,
        default=StatutChoices.INSCRIT,
        verbose_name=_("Statut")
    )

    moyenne_examen = models.DecimalField(
        max_digits=5, decimal_places=2,
        blank=True, null=True,
        verbose_name=_("Moyenne à l'examen")
    )

    mention = models.CharField(
        max_length=50,
        blank=True, default='',
        verbose_name=_("Mention"),
        help_text=_("Ex: Passable, Assez Bien, Bien, Très Bien")
    )

    observations = models.TextField(
        blank=True, default='',
        verbose_name=_("Observations")
    )

    class Meta:
        verbose_name = _("Inscription à l'Examen")
        verbose_name_plural = _("Inscriptions aux Examens")
        ordering = ['session', 'numero_table']
        unique_together = [['session', 'inscription']]

    def __str__(self):
        eleve = self.inscription.eleve.get_nom_complet()
        return f"{eleve} — {self.session} (Table {self.numero_table or '?'})"


# ═══════════════════════════════════════════════════════════════════
# 4. SALLE D'EXAMEN
# ═══════════════════════════════════════════════════════════════════

class SalleExamen(BaseModel):
    """Salle d'écriture au sein d'un centre."""

    centre = models.ForeignKey(
        CentreExamen,
        on_delete=models.CASCADE,
        related_name='salles',
        verbose_name=_("Centre")
    )

    nom = models.CharField(
        max_length=50,
        verbose_name=_("Nom/numéro de salle"),
        help_text=_("Ex: Salle A, Salle 01, Amphithéâtre")
    )

    capacite = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        verbose_name=_("Capacité")
    )

    surveillant_principal = models.ForeignKey(
        'personnel.MembrePersonnel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='salles_surveillees',
        verbose_name=_("Surveillant principal")
    )

    class Meta:
        verbose_name = _("Salle d'Examen")
        verbose_name_plural = _("Salles d'Examen")
        ordering = ['centre', 'nom']
        unique_together = [['centre', 'nom']]

    def __str__(self):
        return f"{self.centre.code_centre} — {self.nom} ({self.capacite} places)"


# ═══════════════════════════════════════════════════════════════════
# 5. PLACEMENT EN SALLE
# ═══════════════════════════════════════════════════════════════════

class PlacementExamen(BaseModel):
    """
    Placement d'un candidat dans une salle d'examen.

    Un candidat ne peut être placé que dans une seule salle (OneToOneField).
    La salle doit appartenir au même centre que le candidat.
    """

    salle = models.ForeignKey(
        SalleExamen,
        on_delete=models.CASCADE,
        related_name='placements',
        verbose_name=_("Salle")
    )

    candidat = models.OneToOneField(
        InscriptionExamen,
        on_delete=models.CASCADE,
        related_name='placement',
        verbose_name=_("Candidat")
    )

    numero_place = models.PositiveSmallIntegerField(
        blank=True, null=True,
        verbose_name=_("Numéro de place"),
        help_text=_("Position numérotée dans la salle (optionnel)")
    )

    class Meta:
        verbose_name = _("Placement en Salle")
        verbose_name_plural = _("Placements en Salle")
        ordering = ['salle', 'numero_place', 'candidat__numero_table']

    def __str__(self):
        eleve = self.candidat.inscription.eleve.get_nom_complet()
        return f"{eleve} → {self.salle}"
