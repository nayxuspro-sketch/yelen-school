"""
Module Pédagogie - Models
=========================
YELEN SCHOOL v3.4 - Gestion pédagogique

Ce module contient :
1. Matiere           - Matières/Enseignements
2. Enseignement      - Association matière-classe-année
3. TypeEvaluation    - Types d'évaluations
4. Trimestre        - Trimestres/Semestres
5. Evaluation        - Évaluations planifiées
6. Note             - Notes des élèves
7. Resultat         - Résultats par élève
8. MoyenneGenerale  - Moyenne générale par période

Auteur: YELEN SCHOOL Team
Date: Mars 2026
Version: 3.4
"""

import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings
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
# 1. MATIÈRE / ENSEIGNEMENT
# ═══════════════════════════════════════════════════════════════════

class Matiere(BaseModel):
    """Matières ou enseignements proposés dans l'établissement."""

    code = models.CharField(max_length=10, unique=True, verbose_name=_("Code matière"))
    nom = models.CharField(max_length=100, verbose_name=_("Nom de la matière"))
    nom_complet = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Nom complet"))

    class CategorieChoices(models.TextChoices):
        LANGUE = 'LANGUE', _('Langue')
        SCIENTIFIQUE = 'SCIENTIFIQUE', _('Scientifique')
        SOCIAL = 'SOCIAL', _('Sciences Humaines et Sociales')
        ART = 'ART', _('Arts et Sports')
        TECHNIQUE = 'TECHNIQUE', _('Technique')
        AUTRE = 'AUTRE', _('Autre')

    categorie = models.CharField(max_length=20, choices=CategorieChoices.choices, default=CategorieChoices.AUTRE, verbose_name=_("Catégorie"))
    coefficient = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('1.00'), verbose_name=_("Coefficient par défaut"))
    moy_min = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("Barème minimal par défaut"))
    moy_max = models.DecimalField(max_digits=5, decimal_places=2, default=20, verbose_name=_("Barème maximal par défaut"))
    heures_hebdomadaires = models.DecimalField(max_digits=4, decimal_places=2, default=0, verbose_name=_("Heures hebdomadaires"))
    est_discipline = models.BooleanField(default=False, verbose_name=_("Matière de discipline"))
    est_obligatoire = models.BooleanField(default=True, verbose_name=_("Matière obligatoire"))

    class Meta:
        verbose_name = _("Matière")
        verbose_name_plural = _("Matières")
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def get_config_cycle(self, cycle):
        """Retourne la configuration MatiereCycle pour ce cycle, ou None."""
        return self.configurations_cycle.filter(cycle=cycle).first()


# ═══════════════════════════════════════════════════════════════════
# 1b. CONFIGURATION MATIÈRE PAR CYCLE
# ═══════════════════════════════════════════════════════════════════

class MatiereCycle(BaseModel):
    """
    Configuration spécifique d'une matière pour un cycle donné.
    Permet d'avoir des coefficients et barèmes différents par cycle.
    Ex : Mathématiques → Primaire (coeff=1, /20) vs Secondaire (coeff=3, /20)
    """

    matiere = models.ForeignKey(
        Matiere, on_delete=models.CASCADE,
        related_name='configurations_cycle',
        verbose_name=_("Matière")
    )
    cycle = models.ForeignKey(
        'parametres.Cycle', on_delete=models.CASCADE,
        related_name='matieres_configurees',
        verbose_name=_("Cycle")
    )
    coefficient = models.DecimalField(
        max_digits=3, decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_("Coefficient")
    )
    moy_min = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Barème minimal")
    )
    moy_max = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('20.00'),
        verbose_name=_("Barème maximal")
    )
    heures_hebdomadaires = models.DecimalField(
        max_digits=4, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_("Heures hebdomadaires")
    )
    est_obligatoire = models.BooleanField(
        default=True,
        verbose_name=_("Obligatoire dans ce cycle")
    )

    class Meta:
        verbose_name = _("Configuration matière/cycle")
        verbose_name_plural = _("Configurations matière/cycle")
        unique_together = [['matiere', 'cycle']]
        ordering = ['cycle__ordre', 'cycle__nom']

    def __str__(self):
        return f"{self.matiere.code} – {self.cycle.nom} (coeff {self.coefficient})"


# ═══════════════════════════════════════════════════════════════════
# 2. ENSEIGNEMENT
# ═══════════════════════════════════════════════════════════════════

class Enseignement(BaseModel):
    """Association d'une matière à une classe pour une année scolaire."""
    
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='enseignements', verbose_name=_("Matière"))
    classe = models.ForeignKey('parametres.Classe', on_delete=models.CASCADE, related_name='enseignements', verbose_name=_("Classe"))
    annee_scolaire = models.ForeignKey('parametres.AnneeScolaire', on_delete=models.CASCADE, related_name='enseignements', verbose_name=_("Année scolaire"))
    personnel = models.ForeignKey('personnel.MembrePersonnel', on_delete=models.SET_NULL, null=True, blank=True, related_name='enseignements', verbose_name=_("Enseignant"))
    coefficient = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, verbose_name=_("Coefficient"))
    heures_hebdomadaires = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True, verbose_name=_("Heures hebdomadaires"))
    est_actif = models.BooleanField(default=True, verbose_name=_("Enseignement actif"))
    
    class Meta:
        verbose_name = _("Enseignement")
        verbose_name_plural = _("Enseignements")
        unique_together = [['matiere', 'classe', 'annee_scolaire']]
    
    def __str__(self):
        return f"{self.matiere.nom} - {self.classe.nom}"
    
    def get_coefficient(self):
        """Coefficient effectif : enseignement > config cycle > matière (défaut)."""
        if self.coefficient is not None:
            return self.coefficient
        cycle = getattr(self.classe, 'cycle', None)
        if cycle is not None:
            config = self.matiere.get_config_cycle(cycle)
            if config is not None:
                return config.coefficient
        return self.matiere.coefficient

    def get_moy_max(self):
        """Barème maximal effectif selon le cycle de la classe."""
        cycle = getattr(self.classe, 'cycle', None)
        if cycle is not None:
            config = self.matiere.get_config_cycle(cycle)
            if config is not None:
                return config.moy_max
        return self.matiere.moy_max

    def get_moy_min(self):
        """Barème minimal effectif selon le cycle de la classe."""
        cycle = getattr(self.classe, 'cycle', None)
        if cycle is not None:
            config = self.matiere.get_config_cycle(cycle)
            if config is not None:
                return config.moy_min
        return self.matiere.moy_min


# ═══════════════════════════════════════════════════════════════════
# 3. TYPE D'ÉVALUATION
# ═══════════════════════════════════════════════════════════════════

class TypeEvaluation(BaseModel):
    """Types d'évaluations."""
    
    code = models.CharField(max_length=10, unique=True, verbose_name=_("Code"))
    nom = models.CharField(max_length=50, verbose_name=_("Nom"))
    description = models.TextField(blank=True, default='', verbose_name=_("Description"))
    coefficient = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('1.00'), verbose_name=_("Coefficient"))
    ponderation = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'), verbose_name=_("Pondération"))
    nb_meilleures_notes = models.IntegerField(default=0, verbose_name=_("Nombre de meilleures notes conservées"))
    est_visible = models.BooleanField(default=True, verbose_name=_("Visible dans le bulletin"))
    ordre = models.IntegerField(default=0, verbose_name=_("Ordre d'affichage"))
    
    class Meta:
        verbose_name = _("Type d'évaluation")
        verbose_name_plural = _("Types d'évaluations")
        ordering = ['ordre', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.nom}"


# ═══════════════════════════════════════════════════════════════════
# 4. TRIMESTRE / PÉRIODE
# ═══════════════════════════════════════════════════════════════════

class Trimestre(BaseModel):
    """Périodes de l'année scolaire."""
    
    class TypePeriodeChoices(models.TextChoices):
        TRIMESTRE = 'TRIMESTRE', _('Trimestre')
        SEMESTRE = 'SEMESTRE', _('Semestre')
    
    annee_scolaire = models.ForeignKey('parametres.AnneeScolaire', on_delete=models.CASCADE, related_name='trimestres', verbose_name=_("Année scolaire"))
    type_periode = models.CharField(max_length=20, choices=TypePeriodeChoices.choices, default=TypePeriodeChoices.TRIMESTRE, verbose_name=_("Type de période"))
    nom = models.CharField(max_length=50, verbose_name=_("Nom"))
    numero = models.IntegerField(default=1, verbose_name=_("Numéro"))
    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_fin = models.DateField(verbose_name=_("Date de fin"))
    notes_saisies = models.BooleanField(default=False, verbose_name=_("Saisie des notes terminée"))
    date_fermeture = models.DateField(blank=True, null=True, verbose_name=_("Date de fermeture"))
    
    class Meta:
        verbose_name = _("Trimestre")
        verbose_name_plural = _("Trimestres")
        ordering = ['annee_scolaire', 'numero']
        unique_together = [['annee_scolaire', 'numero']]
    
    def __str__(self):
        return f"{self.nom} - {self.annee_scolaire.libelle}"


# ═══════════════════════════════════════════════════════════════════
# 5. ÉVALUATION
# ═══════════════════════════════════════════════════════════════════

class Evaluation(BaseModel):
    """Évaluation, devoir ou composition planifié."""
    
    class StatutChoices(models.TextChoices):
        PLANIFIEE = 'PLANIFIEE', _('Planifiée')
        EN_COURS = 'EN_COURS', _('En cours')
        TERMINEE = 'TERMINEE', _('Terminée')
        ANNULEE = 'ANNULEE', _('Annulée')
    
    enseignement = models.ForeignKey(Enseignement, on_delete=models.CASCADE, related_name='evaluations', verbose_name=_("Enseignement"))
    type_evaluation = models.ForeignKey(TypeEvaluation, on_delete=models.PROTECT, related_name='evaluations', verbose_name=_("Type d'évaluation"))
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, related_name='evaluations', verbose_name=_("Trimestre"))
    titre = models.CharField(max_length=200, verbose_name=_("Titre"))
    description = models.TextField(blank=True, default='', verbose_name=_("Description"))
    date_planifiee = models.DateField(verbose_name=_("Date prévue"))
    date_effectuee = models.DateField(blank=True, null=True, verbose_name=_("Date effective"))
    bareme = models.DecimalField(max_digits=5, decimal_places=2, default=20, verbose_name=_("Barème"))
    duree_minutes = models.IntegerField(default=60, verbose_name=_("Durée (minutes)"))
    coefficient = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, verbose_name=_("Coefficient"))
    statut = models.CharField(max_length=20, choices=StatutChoices.choices, default=StatutChoices.PLANIFIEE, verbose_name=_("Statut"))
    observations = models.TextField(blank=True, default='', verbose_name=_("Observations"))
    
    class Meta:
        verbose_name = _("Évaluation")
        verbose_name_plural = _("Évaluations")
        ordering = ['-date_planifiee']
    
    def __str__(self):
        return f"{self.titre} ({self.type_evaluation.nom})"


# ═══════════════════════════════════════════════════════════════════
# 6. NOTE
# ═══════════════════════════════════════════════════════════════════

class Note(BaseModel):
    """Note d'un élève à une évaluation."""
    
    inscription = models.ForeignKey('inscriptions.Inscription', on_delete=models.CASCADE, related_name='notes', verbose_name=_("Inscription"))
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='notes', verbose_name=_("Évaluation"))
    valeur = models.DecimalField(max_digits=5, decimal_places=2, verbose_name=_("Note"))
    observation = models.TextField(blank=True, default='', verbose_name=_("Observation"))
    
    class StatutNoteChoices(models.TextChoices):
        ENREGISTREE = 'ENREGISTREE', _('Enregistrée')
        VALIDEE = 'VALIDEE', _('Validée')
        MODIFIEE = 'MODIFIEE', _('Modifiée')
        ANNULEE = 'ANNULEE', _('Annulée')
    
    statut = models.CharField(max_length=20, choices=StatutNoteChoices.choices, default=StatutNoteChoices.ENREGISTREE, verbose_name=_("Statut"))
    date_validation = models.DateTimeField(blank=True, null=True, verbose_name=_("Date de validation"))
    validee_par = models.ForeignKey('personnel.MembrePersonnel', on_delete=models.SET_NULL, null=True, blank=True, related_name='notes_validees', verbose_name=_("Validée par"))
    
    class Meta:
        verbose_name = _("Note")
        verbose_name_plural = _("Notes")
        unique_together = [['inscription', 'evaluation']]
    
    def __str__(self):
        return f"{self.inscription.eleve} - {self.evaluation}: {self.valeur}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.valeur is not None and self.valeur < 0:
            raise ValidationError({'valeur': "La note ne peut pas être négative."})
        if self.evaluation and self.valeur is not None and self.valeur > self.evaluation.bareme:
            raise ValidationError({
                'valeur': f"La note ({self.valeur}) dépasse le barème ({self.evaluation.bareme})."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def bareme(self):
        return self.evaluation.bareme if self.evaluation else 20
    
    @property
    def note_sur_20(self):
        if self.bareme and self.bareme > 0:
            return (self.valeur / self.bareme) * 20
        return self.valeur


# ═══════════════════════════════════════════════════════════════════
# 7. RÉSULTAT
# ═══════════════════════════════════════════════════════════════════

class Resultat(BaseModel):
    """Résultat calculé pour un élève dans une matière."""
    
    inscription = models.ForeignKey('inscriptions.Inscription', on_delete=models.CASCADE, related_name='resultats', verbose_name=_("Inscription"))
    enseignement = models.ForeignKey(Enseignement, on_delete=models.CASCADE, related_name='resultats', verbose_name=_("Enseignement"))
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, related_name='resultats', verbose_name=_("Trimestre"))
    moyenne = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name=_("Moyenne"))
    moyenne_sur_20 = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name=_("Moyenne sur 20"))
    rang = models.IntegerField(blank=True, null=True, verbose_name=_("Rang"))
    nb_notes = models.IntegerField(default=0, verbose_name=_("Nombre de notes"))
    meilleure_note = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name=_("Meilleure note"))
    pire_note = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name=_("Pire note"))
    appreciation = models.TextField(blank=True, default='', verbose_name=_("Appréciation"))
    coefficient_utilise = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True, verbose_name=_("Coefficient utilisé"))
    dispense = models.BooleanField(default=False, verbose_name=_("Dispensé"))
    
    class Meta:
        verbose_name = _("Résultat")
        verbose_name_plural = _("Résultats")
        unique_together = [['inscription', 'enseignement', 'trimestre']]
    
    def __str__(self):
        return f"{self.inscription.eleve} - {self.enseignement.matiere}: {self.moyenne}"

class MoyenneGenerale(BaseModel):
    """Moyenne générale calculée pour un élève pour un trimestre."""
    
    inscription = models.ForeignKey('inscriptions.Inscription', on_delete=models.CASCADE, related_name='moyennes_generales', verbose_name=_("Inscription"))
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, related_name='moyennes_generales', verbose_name=_("Trimestre"))
    
    moyenne = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name=_("Moyenne"))
    moyenne_sur_20 = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name=_("Moyenne sur 20"))
    rang = models.IntegerField(blank=True, null=True, verbose_name=_("Rang"))
    
    total_points = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name=_("Total des points"))
    total_coefficients = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name=_("Total des coefficients"))
    
    nb_matieres_validees = models.IntegerField(default=0, verbose_name=_("Nombre de matières validées"))
    nb_matieres_total = models.IntegerField(default=0, verbose_name=_("Total des matières"))
    
    appreciation = models.TextField(blank=True, default='', verbose_name=_("Appréciation"))
    observation_generale = models.TextField(blank=True, default='', verbose_name=_("Observation générale"))
    
    est_valide = models.BooleanField(default=False, verbose_name=_("Moyenne validée"))

    @property
    def total_points_max(self):
        """Total de points maximum possible = total_coefficients × 20."""
        return round(self.total_coefficients * 20, 2)

    class Meta:
        verbose_name = _("Moyenne générale")
        verbose_name_plural = _("Moyennes générales")
        unique_together = [['inscription', 'trimestre']]
        ordering = ['trimestre', '-moyenne']
    
    def __str__(self):
        return f"{self.inscription.eleve} - {self.trimestre}: {self.moyenne}"


# ═══════════════════════════════════════════════════════════════════
# 9. RISQUE DE DÉCROCHAGE SCOLAIRE
# ═══════════════════════════════════════════════════════════════════

class RisqueDecrochage(BaseModel):
    """
    Score de risque de décrochage calculé pour un élève sur une année scolaire.

    Calculé par le management command `calculer_risques` (à programmer en cron
    ou à lancer manuellement). Stocke le score brut (0–100), le niveau de risque
    et le détail des facteurs ayant contribué au score.

    Niveaux :
        FAIBLE   0–25   — aucune action immédiate
        MODERE  26–50   — surveillance renforcée
        ELEVE   51–75   — entretien avec les parents recommandé
        CRITIQUE 76–100 — intervention urgente
    """

    class NiveauChoices(models.TextChoices):
        FAIBLE   = 'FAIBLE',   _('Faible')
        MODERE   = 'MODERE',   _('Modéré')
        ELEVE    = 'ELEVE',    _('Élevé')
        CRITIQUE = 'CRITIQUE', _('Critique')

    inscription = models.OneToOneField(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='risque_decrochage',
        verbose_name=_("Inscription"),
    )
    score = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Score de risque (0–100)"),
    )
    niveau = models.CharField(
        max_length=10,
        choices=NiveauChoices.choices,
        default=NiveauChoices.FAIBLE,
        verbose_name=_("Niveau de risque"),
    )
    facteurs = models.JSONField(
        default=list,
        verbose_name=_("Facteurs contributeurs"),
        help_text=_("Liste de dicts {libelle, points, detail}"),
    )
    date_calcul = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Date du dernier calcul"),
    )

    class Meta:
        verbose_name = _("Risque de décrochage")
        verbose_name_plural = _("Risques de décrochage")
        ordering = ['-score']

    def __str__(self):
        return f"{self.inscription.eleve} — {self.niveau} ({self.score}/100)"

    @property
    def couleur_css(self):
        return {
            self.NiveauChoices.FAIBLE:   '#00A86B',
            self.NiveauChoices.MODERE:   '#F5A623',
            self.NiveauChoices.ELEVE:    '#E67E22',
            self.NiveauChoices.CRITIQUE: '#DC3545',
        }.get(self.niveau, '#888')

    @staticmethod
    def niveau_pour_score(score):
        if score <= 25:
            return RisqueDecrochage.NiveauChoices.FAIBLE
        if score <= 50:
            return RisqueDecrochage.NiveauChoices.MODERE
        if score <= 75:
            return RisqueDecrochage.NiveauChoices.ELEVE
        return RisqueDecrochage.NiveauChoices.CRITIQUE


# ═══════════════════════════════════════════════════════════════════
# 10. CAHIER DE TEXTES
# ═══════════════════════════════════════════════════════════════════

class CahierTextes(BaseModel):
    """
    Entrée du cahier de textes numérique.

    L'enseignant renseigne après chaque cours : le contenu traité,
    les devoirs donnés et leur date de remise. Le directeur dispose
    d'une vue consolidée de l'avancement des programmes.
    """

    enseignement = models.ForeignKey(
        Enseignement,
        on_delete=models.CASCADE,
        related_name='entrees_cahier',
        verbose_name=_("Enseignement"),
    )
    date = models.DateField(verbose_name=_("Date du cours"))
    heure_debut = models.TimeField(null=True, blank=True, verbose_name=_("Heure de début"))
    heure_fin = models.TimeField(null=True, blank=True, verbose_name=_("Heure de fin"))
    contenu = models.TextField(verbose_name=_("Contenu du cours"))
    devoirs = models.TextField(blank=True, default='', verbose_name=_("Devoirs donnés"))
    date_remise_devoirs = models.DateField(
        null=True, blank=True, verbose_name=_("Date de remise des devoirs")
    )
    redige_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='entrees_cahier',
        verbose_name=_("Rédigé par"),
    )

    class Meta:
        verbose_name = _("Entrée du cahier de textes")
        verbose_name_plural = _("Cahier de textes")
        ordering = ['-date', '-created_at']

    def __str__(self):
        return (
            f"{self.enseignement.matiere.nom} — "
            f"{self.enseignement.classe.nom} — "
            f"{self.date.strftime('%d/%m/%Y')}"
        )

    @property
    def a_des_devoirs(self):
        return bool(self.devoirs.strip())

    @property
    def devoirs_en_retard(self):
        from django.utils import timezone
        return (
            self.a_des_devoirs
            and self.date_remise_devoirs
            and self.date_remise_devoirs < timezone.now().date()
        )


# ═══════════════════════════════════════════════════════════════════
# 11. PRÉDICTION DE RÉUSSITE AUX EXAMENS OFFICIELS
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# 10. BULLETINS DE COMPÉTENCES (Préscolaire / Primaire)
# ═══════════════════════════════════════════════════════════════════

class Competence(BaseModel):
    """
    Compétence du référentiel pédagogique pour les cycles Préscolaire et Primaire.
    Ex : "Reconnaît et écrit les chiffres de 0 à 9" (Mathématiques, Primaire).
    """

    cycle = models.ForeignKey(
        'parametres.Cycle',
        on_delete=models.CASCADE,
        related_name='competences',
        verbose_name=_("Cycle"),
    )
    matiere = models.ForeignKey(
        Matiere,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='competences',
        verbose_name=_("Matière"),
    )
    libelle = models.CharField(
        max_length=300,
        verbose_name=_("Libellé de la compétence"),
    )
    description = models.TextField(
        blank=True, default='',
        verbose_name=_("Description / indicateurs"),
    )
    ordre = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Ordre d'affichage"),
    )
    actif = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Compétence")
        verbose_name_plural = _("Compétences")
        ordering = ['cycle', 'matiere__code', 'ordre', 'libelle']

    def __str__(self):
        mat = self.matiere.code if self.matiere else "—"
        return f"[{mat}] {self.libelle}"


class EvaluationCompetence(BaseModel):
    """
    Niveau d'acquisition d'une compétence pour un élève à un trimestre donné.
    """

    class NiveauChoices(models.TextChoices):
        ACQUIS     = 'ACQUIS',     _('Acquis')
        EN_COURS   = 'EN_COURS',   _("En cours d'acquisition")
        NON_ACQUIS = 'NON_ACQUIS', _('Non acquis')
        NON_EVALUE = 'NON_EVALUE', _('Non évalué')

    inscription = models.ForeignKey(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='evaluations_competences',
        verbose_name=_("Inscription"),
    )
    competence = models.ForeignKey(
        Competence,
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name=_("Compétence"),
    )
    trimestre = models.ForeignKey(
        Trimestre,
        on_delete=models.CASCADE,
        related_name='evaluations_competences',
        verbose_name=_("Trimestre"),
    )
    niveau = models.CharField(
        max_length=12,
        choices=NiveauChoices.choices,
        default=NiveauChoices.NON_EVALUE,
        verbose_name=_("Niveau d'acquisition"),
    )
    observation = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name=_("Observation"),
    )

    class Meta:
        verbose_name = _("Évaluation de compétence")
        verbose_name_plural = _("Évaluations de compétences")
        unique_together = [('inscription', 'competence', 'trimestre')]
        ordering = ['competence__ordre']

    def __str__(self):
        return f"{self.inscription.eleve} — {self.competence} — {self.niveau}"

    @property
    def pictogramme(self):
        return {
            self.NiveauChoices.ACQUIS:     '✅',
            self.NiveauChoices.EN_COURS:   '🔄',
            self.NiveauChoices.NON_ACQUIS: '❌',
            self.NiveauChoices.NON_EVALUE: '—',
        }.get(self.niveau, '—')

    @property
    def badge_class(self):
        return {
            self.NiveauChoices.ACQUIS:     'badge-success',
            self.NiveauChoices.EN_COURS:   'badge-warning',
            self.NiveauChoices.NON_ACQUIS: 'badge-danger',
            self.NiveauChoices.NON_EVALUE: 'badge-neutral',
        }.get(self.niveau, 'badge-neutral')


# ═══════════════════════════════════════════════════════════════════
# 11. PRÉDICTION DE RÉUSSITE AUX EXAMENS OFFICIELS
# ═══════════════════════════════════════════════════════════════════

class PredictionReussiteExamen(BaseModel):
    """
    Score de probabilité de réussite à l'examen officiel de fin d'année
    (BEPC pour le post-primaire, BAC pour le secondaire).

    Calculé à partir de :
    - La dernière moyenne générale (pondération 70%)
    - La tendance inter-trimestrielle (bonus/malus jusqu'à ±10 pts)
    - Le taux d'assiduité / absences non justifiées (malus jusqu'à -15 pts)
    """

    class PronosticChoices(models.TextChoices):
        BON       = 'BON',      _('Bon pronostic')
        MOYEN     = 'MOYEN',    _('Pronostic moyen')
        RISQUE    = 'RISQUE',   _('Risqué')
        CRITIQUE  = 'CRITIQUE', _('Très risqué')

    class ExamenChoices(models.TextChoices):
        BEPC  = 'BEPC',  'BEPC'
        BAC   = 'BAC',   'BAC'
        CEP   = 'CEP',   'CEP'
        AUTRE = 'AUTRE', _('Autre')

    inscription = models.OneToOneField(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='prediction_examen',
        verbose_name=_("Inscription"),
    )
    examen_cible = models.CharField(
        max_length=10,
        choices=ExamenChoices.choices,
        default=ExamenChoices.AUTRE,
        verbose_name=_("Examen officiel ciblé"),
    )
    score = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Score de probabilité (0–100 %)"),
    )
    pronostic = models.CharField(
        max_length=10,
        choices=PronosticChoices.choices,
        default=PronosticChoices.MOYEN,
        verbose_name=_("Pronostic"),
    )
    mg_actuelle = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Dernière moyenne générale (/20)"),
    )
    tendance = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_("Tendance (écart entre les 2 derniers trimestres)"),
    )
    nb_absences_nj = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Absences non justifiées (heures)"),
    )
    facteurs = models.JSONField(
        default=list,
        verbose_name=_("Détail des facteurs"),
    )
    date_calcul = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Calculé le"),
    )

    class Meta:
        verbose_name = _("Prédiction réussite examen")
        verbose_name_plural = _("Prédictions réussite examen")
        ordering = ['-score']

    def __str__(self):
        return f"{self.inscription.eleve} — {self.examen_cible} {self.score}%"

    @property
    def couleur_css(self):
        return {
            self.PronosticChoices.BON:      '#00A86B',
            self.PronosticChoices.MOYEN:    '#F5A623',
            self.PronosticChoices.RISQUE:   '#E67E22',
            self.PronosticChoices.CRITIQUE: '#DC3545',
        }.get(self.pronostic, '#888')

    @property
    def badge_class(self):
        return {
            self.PronosticChoices.BON:      'badge-success',
            self.PronosticChoices.MOYEN:    'badge-warning',
            self.PronosticChoices.RISQUE:   'badge-danger',
            self.PronosticChoices.CRITIQUE: 'badge-danger',
        }.get(self.pronostic, 'badge-neutral')

    @staticmethod
    def pronostic_pour_score(score):
        if score >= 70:
            return PredictionReussiteExamen.PronosticChoices.BON
        if score >= 50:
            return PredictionReussiteExamen.PronosticChoices.MOYEN
        if score >= 30:
            return PredictionReussiteExamen.PronosticChoices.RISQUE
        return PredictionReussiteExamen.PronosticChoices.CRITIQUE
