from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel
from parametres.models import Classe, AnneeScolaire
from pedagogie.models import Trimestre, Enseignement
from inscriptions.models import Inscription
from django.conf import settings


class JourSemaine(models.IntegerChoices):
    LUNDI = 1, _('Lundi')
    MARDI = 2, _('Mardi')
    MERCREDI = 3, _('Mercredi')
    JEUDI = 4, _('Jeudi')
    VENDREDI = 5, _('Vendredi')
    SAMEDI = 6, _('Samedi')
    DIMANCHE = 7, _('Dimanche')


class SeanceCours(BaseModel):
    """Une plage horaire dans l'emploi du temps d'une classe."""
    enseignement = models.ForeignKey(Enseignement, on_delete=models.CASCADE, related_name='seances')
    jour = models.IntegerField(choices=JourSemaine.choices)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    salle = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = _("Séance de cours")
        verbose_name_plural = _("Séances de cours")
        ordering = ['jour', 'heure_debut']
        unique_together = [['enseignement', 'jour', 'heure_debut']]

    def __str__(self):
        return f"{self.enseignement} - {self.get_jour_display()} ({self.heure_debut}-{self.heure_fin})"


class ConseilClasse(BaseModel):
    """Conseil de classe trimestriel pour une classe."""

    class DecisionChoices(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', _('En attente')
        PASSAGE = 'PASSAGE', _('Passage en classe supérieure')
        REDOUBLEMENT = 'REDOUBLEMENT', _('Redoublement')
        ORIENTATION = 'ORIENTATION', _('Réorientation')
        EXCLUSION = 'EXCLUSION', _('Exclusion définitive')

    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='conseils_classe', verbose_name=_("Classe"))
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, related_name='conseils_classe', verbose_name=_("Trimestre"))
    date_conseil = models.DateField(verbose_name=_("Date du conseil"))
    president = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='conseils_presides',
        verbose_name=_("Président du conseil")
    )
    observations = models.TextField(blank=True, verbose_name=_("Observations générales"))
    tenu = models.BooleanField(default=False, verbose_name=_("Conseil tenu"))

    class Meta:
        verbose_name = _("Conseil de classe")
        verbose_name_plural = _("Conseils de classe")
        ordering = ['-date_conseil']
        unique_together = [['classe', 'trimestre']]

    def __str__(self):
        return f"Conseil {self.classe} - {self.trimestre}"


class DecisionConseil(BaseModel):
    """Décision individuelle prise lors d'un conseil de classe."""

    class DecisionChoices(models.TextChoices):
        PASSAGE = 'PASSAGE', _('Passage')
        REDOUBLEMENT = 'REDOUBLEMENT', _('Redoublement')
        ORIENTATION = 'ORIENTATION', _('Réorientation')
        EXCLUSION = 'EXCLUSION', _('Exclusion')
        RACHAT = 'RACHAT', _('Rachat accordé')

    conseil = models.ForeignKey(ConseilClasse, on_delete=models.CASCADE, related_name='decisions', verbose_name=_("Conseil"))
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='decisions_conseil', verbose_name=_("Inscription"))
    decision = models.CharField(max_length=20, choices=DecisionChoices.choices, default=DecisionChoices.PASSAGE, verbose_name=_("Décision"))
    appreciation = models.TextField(blank=True, verbose_name=_("Appréciation"))
    mention_honneur = models.BooleanField(default=False, verbose_name=_("Mention d'honneur"))
    encouragements = models.BooleanField(default=False, verbose_name=_("Encouragements"))
    felicitations = models.BooleanField(default=False, verbose_name=_("Félicitations"))

    class Meta:
        verbose_name = _("Décision du conseil")
        verbose_name_plural = _("Décisions du conseil")
        unique_together = [['conseil', 'inscription']]

    def __str__(self):
        return f"{self.inscription.eleve} - {self.get_decision_display()}"


class SanctionDisciplinaire(BaseModel):
    """Sanction disciplinaire appliquée à un élève."""

    class StatutChoices(models.TextChoices):
        EN_COURS = 'EN_COURS', _('En cours de traitement')
        CONFIRME = 'CONFIRME', _('Confirmée')
        ANNULE = 'ANNULE', _('Annulée')
        LEVEE = 'LEVEE', _('Levée')

    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='sanctions', verbose_name=_("Élève"))
    type_sanction = models.ForeignKey(
        'parametres.TypeSanction',
        on_delete=models.PROTECT,
        related_name='sanctions',
        verbose_name=_("Type de sanction")
    )
    date_sanction = models.DateField(verbose_name=_("Date de la sanction"))
    motif = models.TextField(verbose_name=_("Motif"))
    duree_jours = models.PositiveIntegerField(default=0, verbose_name=_("Durée (jours)"), help_text=_("Pour les exclusions temporaires"))
    date_retour = models.DateField(null=True, blank=True, verbose_name=_("Date de retour prévue"))
    prononcee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='sanctions_prononcees',
        verbose_name=_("Prononcée par")
    )
    statut = models.CharField(max_length=20, choices=StatutChoices.choices, default=StatutChoices.EN_COURS, verbose_name=_("Statut"))
    observations = models.TextField(blank=True, verbose_name=_("Observations"))
    parents_convoques = models.BooleanField(default=False, verbose_name=_("Parents convoqués"))
    date_convocation = models.DateField(null=True, blank=True, verbose_name=_("Date convocation parents"))

    # ── Impact sur la moyenne trimestrielle ──────────────────────────────────
    trimestre = models.ForeignKey(
        'pedagogie.Trimestre',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sanctions_disciplinaires',
        verbose_name=_("Trimestre d'application"),
        help_text=_("Trimestre sur lequel les points sont ajoutés ou retirés.")
    )
    points = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_("Points (+ ajout / − retrait)"),
        help_text=_("Valeur positive pour un bonus, négative pour une pénalité appliquée au total des points.")
    )
    appreciation_conduite = models.CharField(
        max_length=200, blank=True,
        verbose_name=_("Appréciation de la conduite"),
        help_text=_("Ex : Très bonne conduite, Conduite à améliorer…")
    )

    class Meta:
        verbose_name = _("Sanction disciplinaire")
        verbose_name_plural = _("Sanctions disciplinaires")
        ordering = ['-date_sanction']

    def __str__(self):
        return f"{self.inscription.eleve} - {self.get_type_sanction_display()} ({self.date_sanction})"

    @property
    def a_impact_points(self):
        return self.trimestre is not None and self.points != 0 and self.statut == self.StatutChoices.CONFIRME


class ActiviteParascolaire(BaseModel):
    """Activité parascolaire (club, sport, atelier...)."""

    class TypeActiviteChoices(models.TextChoices):
        SPORT = 'SPORT', _('Sport')
        CLUB = 'CLUB', _('Club / Association')
        ART = 'ART', _('Art & Culture')
        ACADEMIQUE = 'ACADEMIQUE', _('Académique')
        AUTRE = 'AUTRE', _('Autre')

    annee_scolaire = models.ForeignKey(AnneeScolaire, on_delete=models.CASCADE, related_name='activites_parascolaires', verbose_name=_("Année scolaire"))
    nom = models.CharField(max_length=100, verbose_name=_("Nom de l'activité"))
    type_activite = models.CharField(max_length=20, choices=TypeActiviteChoices.choices, default=TypeActiviteChoices.CLUB, verbose_name=_("Type"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='activites_responsable',
        verbose_name=_("Responsable")
    )
    capacite_max = models.PositiveIntegerField(default=30, verbose_name=_("Capacité max"))
    jour_reunion = models.IntegerField(choices=JourSemaine.choices, null=True, blank=True, verbose_name=_("Jour de réunion"))
    heure_debut = models.TimeField(null=True, blank=True, verbose_name=_("Heure de début"))

    class Meta:
        verbose_name = _("Activité parascolaire")
        verbose_name_plural = _("Activités parascolaires")
        ordering = ['type_activite', 'nom']
        unique_together = [['annee_scolaire', 'nom']]

    def __str__(self):
        return f"{self.nom} ({self.get_type_activite_display()})"

    @property
    def nb_participants(self):
        return self.participations.filter(is_active=True).count()


class ParticipationActivite(BaseModel):
    """Participation d'un élève à une activité parascolaire."""
    activite = models.ForeignKey(ActiviteParascolaire, on_delete=models.CASCADE, related_name='participations', verbose_name=_("Activité"))
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='activites', verbose_name=_("Élève"))
    date_inscription = models.DateField(auto_now_add=True, verbose_name=_("Date d'inscription"))
    observations = models.CharField(max_length=200, blank=True, verbose_name=_("Observations"))

    class Meta:
        verbose_name = _("Participation à une activité")
        verbose_name_plural = _("Participations aux activités")
        unique_together = [['activite', 'inscription']]

    def __str__(self):
        return f"{self.inscription.eleve} → {self.activite.nom}"
