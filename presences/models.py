"""
Module Présences - Models
==========================
YELEN SCHOOL v3.4 - Gestion des présences et absences

Ce module contient :
1. Appel       - Appel journalier par classe et matière
2. Presence    - Présence/absence individuelle d'un élève
3. Justification - Justification d'une absence

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


# ═══════════════════════════════════════════════════════════════════
# 1. APPEL
# ═══════════════════════════════════════════════════════════════════

class Appel(BaseModel):
    """
    Appel journalier effectué par un enseignant pour une classe.

    Un appel correspond à une séance : une classe, une date, une heure,
    éventuellement liée à un enseignement précis.
    """

    classe = models.ForeignKey(
        'parametres.Classe',
        on_delete=models.CASCADE,
        related_name='appels',
        verbose_name=_("Classe")
    )

    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='appels',
        verbose_name=_("Année scolaire")
    )

    matiere = models.ForeignKey(
        'pedagogie.Matiere',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appels',
        verbose_name=_("Matière")
    )

    date = models.DateField(verbose_name=_("Date"))

    heure_debut = models.TimeField(
        blank=True,
        null=True,
        verbose_name=_("Heure de début")
    )

    heure_fin = models.TimeField(
        blank=True,
        null=True,
        verbose_name=_("Heure de fin")
    )

    effectue_par = models.ForeignKey(
        'personnel.MembrePersonnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appels_effectues',
        verbose_name=_("Effectué par")
    )

    est_clos = models.BooleanField(
        default=False,
        verbose_name=_("Appel clôturé"),
        help_text=_("Une fois clôturé, les présences ne peuvent plus être modifiées")
    )

    observations = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Observations")
    )

    class Meta:
        verbose_name = _("Appel")
        verbose_name_plural = _("Appels")
        ordering = ['-date', 'classe']
        unique_together = [['classe', 'date', 'matiere']]
        indexes = [
            # Appels du jour / d'une période (tableau de bord, pilotage) : la contrainte unique
            # commence par classe et ne sert pas aux filtres par date seule.
            models.Index(fields=['date'], name='appel_date_idx'),
        ]

    def __str__(self):
        matiere = self.matiere.nom if self.matiere else "—"
        return f"Appel {self.classe.nom} — {matiere} — {self.date}"

    @property
    def nb_presents(self):
        return self.presences.filter(statut=Presence.StatutChoices.PRESENT).count()

    @property
    def nb_absents(self):
        return self.presences.filter(statut=Presence.StatutChoices.ABSENT).count()

    @property
    def nb_retards(self):
        return self.presences.filter(statut=Presence.StatutChoices.RETARD).count()


# ═══════════════════════════════════════════════════════════════════
# 2. PRÉSENCE
# ═══════════════════════════════════════════════════════════════════

class Presence(BaseModel):
    """
    Statut de présence d'un élève pour un appel donné.

    Créé automatiquement lors de la clôture de l'appel
    pour tous les élèves inscrits dans la classe.
    """

    class StatutChoices(models.TextChoices):
        PRESENT = 'PRESENT', _('Présent')
        ABSENT = 'ABSENT', _('Absent')
        RETARD = 'RETARD', _('En retard')
        EXCUSE = 'EXCUSE', _('Excusé')

    appel = models.ForeignKey(
        Appel,
        on_delete=models.CASCADE,
        related_name='presences',
        verbose_name=_("Appel")
    )

    inscription = models.ForeignKey(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='presences',
        verbose_name=_("Inscription élève")
    )

    statut = models.CharField(
        max_length=10,
        choices=StatutChoices.choices,
        default=StatutChoices.PRESENT,
        verbose_name=_("Statut")
    )

    minutes_retard = models.IntegerField(
        default=0,
        verbose_name=_("Minutes de retard"),
        help_text=_("0 si non applicable")
    )

    observations = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Observations")
    )

    parents_notifies_le = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Parents notifiés le"),
        help_text=_("Date d'envoi du SMS d'absence ou de retard aux parents (à la clôture de l'appel)")
    )

    class Meta:
        verbose_name = _("Présence")
        verbose_name_plural = _("Présences")
        ordering = ['appel__date', 'inscription__eleve__nom']
        unique_together = [['appel', 'inscription']]
        indexes = [
            # Comptages par statut depuis les appels (absents du jour, pilotage 30 j, effectifs
            # présents par appel) : parcours d'index seul sur la plus grosse table de la base.
            models.Index(fields=['appel', 'statut'], name='presence_appel_statut_idx'),
        ]

    def __str__(self):
        return (
            f"{self.inscription.eleve.get_nom_complet()} — "
            f"{self.appel.date} — {self.get_statut_display()}"
        )


# ═══════════════════════════════════════════════════════════════════
# 3. JUSTIFICATION
# ═══════════════════════════════════════════════════════════════════

class Justification(BaseModel):
    """
    Justification d'une ou plusieurs absences pour un élève.

    Peut couvrir une période (date_debut → date_fin)
    et être validée ou refusée par le personnel.
    """

    class StatutChoices(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', _('En attente')
        ACCEPTEE = 'ACCEPTEE', _('Acceptée')
        REFUSEE = 'REFUSEE', _('Refusée')

    inscription = models.ForeignKey(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='justifications',
        verbose_name=_("Inscription élève")
    )

    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_fin = models.DateField(verbose_name=_("Date de fin"))

    motif = models.TextField(verbose_name=_("Motif"))

    document = models.FileField(
        upload_to='presences/justifications/',
        blank=True,
        null=True,
        verbose_name=_("Document justificatif"),
        help_text=_("Certificat médical, courrier, etc.")
    )

    statut = models.CharField(
        max_length=15,
        choices=StatutChoices.choices,
        default=StatutChoices.EN_ATTENTE,
        verbose_name=_("Statut")
    )

    traitee_par = models.ForeignKey(
        'personnel.MembrePersonnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='justifications_traitees',
        verbose_name=_("Traitée par")
    )

    date_traitement = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Date de traitement")
    )

    observation_traitement = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Observation du responsable")
    )

    deposee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='justifications_deposees',
        verbose_name=_("Déposée par"),
        help_text=_("Compte parent ayant déposé le justificatif depuis le portail ; vide pour une saisie au secrétariat."),
    )

    class Meta:
        verbose_name = _("Justification")
        verbose_name_plural = _("Justifications")
        ordering = ['-date_debut']

    def __str__(self):
        return (
            f"Justification {self.inscription.eleve.get_nom_complet()} "
            f"du {self.date_debut} au {self.date_fin}"
        )

    @property
    def nb_jours(self):
        return (self.date_fin - self.date_debut).days + 1

    @property
    def via_portail(self):
        return self.deposee_par_id is not None


# ═══════════════════════════════════════════════════════════════════
# 4. SEUIL D'ABSENCES — alerte direction / parents
# ═══════════════════════════════════════════════════════════════════

class SeuilAbsences(BaseModel):
    """Réglage par établissement : au bout de ``seuil`` absences non justifiées sur la période, une alerte est créée
    à la clôture de l'appel (notification de la direction, SMS au parent)."""

    etablissement = models.OneToOneField('etablissements.Etablissement', on_delete=models.CASCADE,
                                         related_name='seuil_absences', verbose_name=_("Établissement"))
    actif = models.BooleanField(default=True, verbose_name=_("Alertes actives"))
    seuil = models.PositiveSmallIntegerField(default=5, verbose_name=_("Seuil d'absences non justifiées"))
    par_periode = models.BooleanField(default=True, verbose_name=_("Compter par période (trimestre)"),
                                      help_text=_("Décoché : le compte court sur toute l'année scolaire."))
    sms_parent = models.BooleanField(default=True, verbose_name=_("Prévenir le parent par SMS"))

    class Meta:
        verbose_name = _("Seuil d'absences")
        verbose_name_plural = _("Seuils d'absences")

    def __str__(self):
        return f"Seuil d'absences {self.etablissement} : {self.seuil}"

    @classmethod
    def pour(cls, etablissement):
        return cls.objects.get_or_create(etablissement=etablissement)[0]


class AlerteAbsences(BaseModel):
    """Palier de seuil franchi par un élève sur une période (1 = seuil atteint, 2 = deux fois le seuil…) ; la direction
    la marque traitée (convocation, entretien)."""

    inscription = models.ForeignKey('inscriptions.Inscription', on_delete=models.CASCADE,
                                    related_name='alertes_absences', verbose_name=_("Inscription"))
    periode = models.CharField(max_length=100, verbose_name=_("Période"))
    palier = models.PositiveSmallIntegerField(default=1, verbose_name=_("Palier"))
    seuil = models.PositiveSmallIntegerField(verbose_name=_("Seuil appliqué"))
    nb_absences = models.PositiveSmallIntegerField(verbose_name=_("Absences non justifiées"))
    date_appel = models.DateField(verbose_name=_("Date de l'appel déclencheur"))
    sms_envoye = models.BooleanField(default=False, verbose_name=_("SMS envoyé au parent"))
    traitee = models.BooleanField(default=False, verbose_name=_("Traitée"))
    traitee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='alertes_absences_traitees', verbose_name=_("Traitée par"))
    traitee_le = models.DateTimeField(null=True, blank=True, verbose_name=_("Traitée le"))
    observation = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Suite donnée"))

    class Meta:
        verbose_name = _("Alerte d'absences")
        verbose_name_plural = _("Alertes d'absences")
        ordering = ['traitee', '-created_at']
        unique_together = [['inscription', 'periode', 'palier']]

    def __str__(self):
        return f"{self.inscription.eleve.get_nom_complet()} — {self.nb_absences} absences ({self.periode})"
