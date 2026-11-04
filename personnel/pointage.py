"""
Module Personnel — pointage et évaluation annuelle (5.53.0)
===========================================================
Déplacé hors de ``personnel/models.py`` (garde-fou des 1 000 lignes) et ré-exporté par ce module :
``from personnel.models import ReglagePointage, PointagePersonnel, EvaluationAnnuelle`` continue de fonctionner.

1. ProfilPointage     - Profil de pointage d'un agent (enseignant / administration)
2. ReglagePointage    - Heures de référence de l'établissement et de chaque profil
3. PointagePersonnel  - Arrivée et départ réels d'un agent, un seul par jour
4. EvaluationAnnuelle - Entretien annuel d'évaluation (5 critères notés de 0 à 5)
"""

from datetime import time

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


class ProfilPointage(models.TextChoices):
    """Profil de pointage : détermine les horaires appliqués par défaut à un agent."""
    ENSEIGNANT = 'ENSEIGNANT', _('Enseignant')
    ADMINISTRATION = 'ADMINISTRATION', _('Administration')


class ReglagePointage(BaseModel):
    """Réglages de pointage de l'établissement (une ligne par établissement) : heure d'arrivée retenue comme
    limite, au-delà de laquelle un pointage est compté en retard."""

    HEURE_PAR_DEFAUT = time(7, 30)

    etablissement = models.OneToOneField('etablissements.Etablissement', on_delete=models.CASCADE,
                                         related_name='reglage_pointage', verbose_name=_("Établissement"))
    heure_arrivee_limite = models.TimeField(default=HEURE_PAR_DEFAUT, verbose_name=_("Heure d'arrivée limite"),
                                            help_text=_("Un pointage postérieur à cette heure est compté en retard."))
    heure_arrivee_limite_enseignant = models.TimeField(
        null=True, blank=True, verbose_name=_("Arrivée limite des enseignants"),
        help_text=_("Vide : la limite de l'établissement s'applique aux enseignants."))
    heure_arrivee_limite_administration = models.TimeField(
        null=True, blank=True, verbose_name=_("Arrivée limite de l'administration"),
        help_text=_("Vide : la limite de l'établissement s'applique à l'administration."))
    heure_depart_normale = models.TimeField(
        null=True, blank=True, verbose_name=_("Heure normale de départ"),
        help_text=_("Heure de fin de service retenue pour l'établissement (ex. 12:30)."))
    heure_depart_normale_enseignant = models.TimeField(
        null=True, blank=True, verbose_name=_("Départ normal des enseignants"),
        help_text=_("Un départ plus tôt que cette heure est compté en départ anticipé."))
    heure_depart_normale_administration = models.TimeField(
        null=True, blank=True, verbose_name=_("Départ normal de l'administration"),
        help_text=_("Un départ plus tôt que cette heure est compté en départ anticipé."))

    class Meta:
        verbose_name = _("Réglage du pointage")
        verbose_name_plural = _("Réglages du pointage")

    def __str__(self):
        return f"Pointage — {self.etablissement} (limite {self.heure_arrivee_limite:%H:%M})"

    @classmethod
    def pour(cls, etablissement):
        reglage, _ = cls.objects.get_or_create(etablissement=etablissement)
        return reglage

    def limite_pour(self, profil):
        """Heure limite d'arrivée d'un profil, à défaut celle de l'établissement."""
        if profil == ProfilPointage.ENSEIGNANT and self.heure_arrivee_limite_enseignant:
            return self.heure_arrivee_limite_enseignant
        if profil == ProfilPointage.ADMINISTRATION and self.heure_arrivee_limite_administration:
            return self.heure_arrivee_limite_administration
        return self.heure_arrivee_limite or self.HEURE_PAR_DEFAUT

    def depart_pour(self, profil):
        """Heure normale de départ d'un profil, à défaut celle de l'établissement (ou None)."""
        if profil == ProfilPointage.ENSEIGNANT and self.heure_depart_normale_enseignant:
            return self.heure_depart_normale_enseignant
        if profil == ProfilPointage.ADMINISTRATION and self.heure_depart_normale_administration:
            return self.heure_depart_normale_administration
        return self.heure_depart_normale


class PointagePersonnel(BaseModel):
    """Pointage d'un agent pour une journée : heure d'arrivée et de départ, aucun pointage valant absence."""

    class StatutChoices(models.TextChoices):
        PRESENT = 'PRESENT', _('Présent')
        RETARD  = 'RETARD',  _('En retard')
        ABSENT  = 'ABSENT',  _('Absent')
        CONGE   = 'CONGE',   _('En congé')

    personnel = models.ForeignKey('personnel.MembrePersonnel', on_delete=models.CASCADE, related_name='pointages',
                                  verbose_name=_("Membre du personnel"))
    date = models.DateField(verbose_name=_("Date"))
    heure_arrivee = models.TimeField(null=True, blank=True, verbose_name=_("Arrivée"))
    heure_depart = models.TimeField(null=True, blank=True, verbose_name=_("Départ"))
    statut = models.CharField(max_length=10, choices=StatutChoices.choices, default=StatutChoices.PRESENT,
                              verbose_name=_("Statut"))
    observation = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Observation"))

    class Meta:
        verbose_name = _("Pointage du personnel")
        verbose_name_plural = _("Pointages du personnel")
        ordering = ['-date', 'personnel__nom']
        constraints = [
            models.UniqueConstraint(fields=['personnel', 'date'], name='pointage_personnel_jour_unique'),
        ]
        indexes = [models.Index(fields=['date'], name='pointage_date_idx')]

    def __str__(self):
        return f"{self.personnel.get_nom_complet()} — {self.date:%d/%m/%Y} ({self.get_statut_display()})"

    @property
    def heures_travaillees(self):
        """Amplitude horaire de présence, en heures décimales (0 si l'un des deux pointages manque)."""
        if not (self.heure_arrivee and self.heure_depart):
            return 0.0
        arrivee = self.heure_arrivee.hour * 60 + self.heure_arrivee.minute
        depart = self.heure_depart.hour * 60 + self.heure_depart.minute
        return max(0, depart - arrivee) / 60

    @classmethod
    def statut_depuis(cls, heure_arrivee, heure_limite):
        """Statut déduit de l'heure d'arrivée comparée à l'heure limite de l'agent."""
        if heure_arrivee is None:
            return cls.StatutChoices.ABSENT
        return cls.StatutChoices.RETARD if heure_arrivee > heure_limite else cls.StatutChoices.PRESENT

    def est_depart_anticipe(self, heure_depart_normale=None):
        """Vrai si l'agent est parti avant son heure normale de départ."""
        normale = heure_depart_normale or getattr(self.personnel, 'heure_depart_normale', None)
        return bool(self.heure_depart and normale and self.heure_depart < normale)

    @property
    def heures_attendues(self):
        """Amplitude horaire prévue par les horaires de référence de l'agent (0 si inconnue)."""
        arrivee = getattr(self.personnel, 'heure_arrivee_limite', None)
        depart = getattr(self.personnel, 'heure_depart_normale', None)
        if not (arrivee and depart):
            return 0.0
        return max(0, (depart.hour * 60 + depart.minute) - (arrivee.hour * 60 + arrivee.minute)) / 60


class EvaluationAnnuelle(BaseModel):
    """Entretien annuel d'évaluation d'un agent : cinq critères notés de 0 à 5, bilan, objectifs et avis."""

    class AvisChoices(models.TextChoices):
        FAVORABLE  = 'FAVORABLE',  _('Favorable')
        RESERVE    = 'RESERVE',    _('Favorable avec réserves')
        DEFAVORABLE = 'DEFAVORABLE', _('Défavorable')

    CRITERES = (
        ('ponctualite', 'Ponctualité et assiduité'),
        ('competence', 'Compétence professionnelle'),
        ('qualite', 'Qualité du travail rendu'),
        ('relations', 'Relations avec les élèves, les familles et les collègues'),
        ('initiative', 'Initiative et respect des consignes'),
    )

    personnel = models.ForeignKey('personnel.MembrePersonnel', on_delete=models.CASCADE, related_name='evaluations',
                                  verbose_name=_("Membre du personnel"))
    annee_scolaire = models.ForeignKey('parametres.AnneeScolaire', on_delete=models.CASCADE,
                                       related_name='evaluations_personnel', verbose_name=_("Année scolaire"))
    date_entretien = models.DateField(verbose_name=_("Date de l'entretien"))
    evaluateur = models.ForeignKey('personnel.MembrePersonnel', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='evaluations_conduites', verbose_name=_("Évaluateur"))
    ponctualite = models.PositiveSmallIntegerField(default=3, verbose_name=_("Ponctualité et assiduité"),
                                                   help_text=_("Note de 0 à 5"))
    competence = models.PositiveSmallIntegerField(default=3, verbose_name=_("Compétence professionnelle"),
                                                  help_text=_("Note de 0 à 5"))
    qualite = models.PositiveSmallIntegerField(default=3, verbose_name=_("Qualité du travail rendu"),
                                               help_text=_("Note de 0 à 5"))
    relations = models.PositiveSmallIntegerField(default=3, verbose_name=_("Relations avec les élèves, les familles "
                                                                           "et les collègues"),
                                                 help_text=_("Note de 0 à 5"))
    initiative = models.PositiveSmallIntegerField(default=3, verbose_name=_("Initiative et respect des consignes"),
                                                  help_text=_("Note de 0 à 5"))
    bilan = models.TextField(blank=True, default='', verbose_name=_("Bilan de l'année"))
    objectifs = models.TextField(blank=True, default='', verbose_name=_("Objectifs de l'année suivante"))
    avis = models.CharField(max_length=12, choices=AvisChoices.choices, default=AvisChoices.FAVORABLE,
                            verbose_name=_("Avis"))

    class Meta:
        verbose_name = _("Évaluation annuelle")
        verbose_name_plural = _("Évaluations annuelles")
        ordering = ['-date_entretien']
        constraints = [
            models.UniqueConstraint(fields=['personnel', 'annee_scolaire'], name='evaluation_annuelle_unique'),
        ]

    def __str__(self):
        return f"{self.personnel.get_nom_complet()} — {self.annee_scolaire.libelle}"

    @property
    def notes(self):
        """[(libellé du critère, note)] dans l'ordre d'affichage."""
        return [(libelle, getattr(self, champ)) for champ, libelle in self.CRITERES]

    @property
    def total_points(self):
        return sum(getattr(self, champ) for champ, _libelle in self.CRITERES)

    @property
    def moyenne_sur_20(self):
        """Moyenne des cinq critères ramenée sur 20 (note maximale 5 par critère)."""
        return round(self.total_points / (5 * len(self.CRITERES)) * 20, 2)
