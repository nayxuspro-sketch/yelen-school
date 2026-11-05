"""
Module Personnel - Models
=========================
YELEN SCHOOL v3.4 - Gestion du personnel scolaire

Ce module contient :
1. MembrePersonnel   - Informations complètes du membre du personnel
2. InscriptionPersonnel - Inscription annuelle du personnel par cycle/poste

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

# Import pour le chiffrement des données sensibles
try:
    from core.encryption import encrypt_sensitive_data, decrypt_sensitive_data, mask_cni
except ImportError:
    encrypt_sensitive_data = decrypt_sensitive_data = lambda x: x
    def mask_cni(x): return x if x else ''


# Pointage et évaluation annuelle : définis dans personnel/pointage.py et ré-exportés ici
# (garde-fou des 1 000 lignes ; « from personnel.models import PointagePersonnel » reste valable).
from personnel.pointage import (  # noqa: E402,F401
    EvaluationAnnuelle,
    PointagePersonnel,
    ProfilPointage,
    ReglagePointage,
)

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
# 1. MEMBRE DU PERSONNEL
# ═══════════════════════════════════════════════════════════════════

class GenreChoices(models.TextChoices):
    """Genres disponibles pour le personnel."""
    MASCULIN = 'M', _('Masculin')
    FEMININ = 'F', _('Féminin')


class SituationMatrimonialeChoices(models.TextChoices):
    """Situations matrimoniales."""
    CELIBATAIRE = 'CELIBATAIRE', _('Célibataire')
    MARIE = 'MARIE', _('Marié(e)')
    DIVORCE = 'DIVORCE', _('Divorcé(e)')
    VEUF = 'VEUF', _('Veuf/Veuve')


class MembrePersonnel(BaseModel):
    """
    Informations complètes d'un membre du personnel.
    
    Chaque membre a un matricule unique au format: {CODE_ETAB}-P-{ANNEE}-{SEQ}
    Ex: 01-P-2026-2 (01 = code établissement, P = Personnel, 2026 = année, 2 = numéro d'enregistrement)
    
    Note v3.3: Le personnel doit avoir une InscriptionPersonnel validée
    chaque année pour être actif dans les emplois du temps, présences, etc.
    """
    
    # Identification
    matricule = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        default='',
        verbose_name=_("Matricule"),
        help_text=_("Format: {CODE_ETAB}-P-{ANNEE}-{SEQ}")
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
    
    nationalite = models.CharField(
        max_length=100,
        default='Burkinabè',
        verbose_name=_("Nationalité")
    )
    
    # Contact
    telephone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Téléphone")
    )
    
    email = models.EmailField(
        blank=True,
        default='',
        verbose_name=_("Adresse email")
    )
    
    adresse = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Adresse complète")
    )
    
    # Pièce d'identité (chiffré)
    _numero_cni_encrypted = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Numéro CNI (chiffré)"),
        db_column='numero_cni_encrypted',
    )
    
    @property
    def numero_cni(self):
        """Retourne le numéro CNI déchiffré."""
        if self._numero_cni_encrypted:
            return decrypt_sensitive_data(self._numero_cni_encrypted)
        return ''
    
    @numero_cni.setter
    def numero_cni(self, value):
        """Définit le numéro CNI en le chiffrant."""
        if value:
            self._numero_cni_encrypted = encrypt_sensitive_data(value)
        else:
            self._numero_cni_encrypted = ''
    
    def get_numero_cni_masked(self):
        """Retourne le numéro CNI masqué pour l'affichage."""
        return mask_cni(self.numero_cni)

    MOTS_ENSEIGNANT = ('enseignant', 'enseignante', 'professeur', 'maitre', 'maître', 'instituteur',
                       'institutrice', 'vacataire', 'moniteur', 'formatrice', 'formateur', 'éducateur',
                       'educateur')

    def deviner_profil_pointage(self):
        """Profil déduit du titre (« Enseignant », « Professeur de maths »…) : à défaut, administration."""
        texte = f"{self.fonction or ''} {self.titre_capacite or ''}".lower()
        if any(mot in texte for mot in self.MOTS_ENSEIGNANT):
            return ProfilPointage.ENSEIGNANT
        return ProfilPointage.ADMINISTRATION

    def heure_limite_pointage(self, reglage=None):
        """Heure limite d'arrivée applicable : celle de l'agent, sinon celle de son profil, sinon celle
        de l'établissement."""
        if self.heure_arrivee_limite:
            return self.heure_arrivee_limite
        if reglage is not None:
            return reglage.limite_pour(self.profil_pointage)
        return ReglagePointage.HEURE_PAR_DEFAUT

    def heure_depart_pointage(self, reglage=None):
        """Heure normale de départ applicable (None si l'établissement n'en a pas fixé)."""
        if self.heure_depart_normale:
            return self.heure_depart_normale
        return reglage.depart_pour(self.profil_pointage) if reglage is not None else None
    
    # Informations professionnelles
    fonction = models.CharField(
        max_length=100,
        verbose_name=_("Titre")
    )

    profil_pointage = models.CharField(
        max_length=15,
        choices=ProfilPointage.choices,
        blank=True,
        default=ProfilPointage.ADMINISTRATION,
        verbose_name=_("Profil de pointage"),
        help_text=_("Détermine les horaires appliqués par défaut : enseignant ou administration.")
    )

    # Horaires de référence propres à l'agent (vides = ceux de son profil, puis de l'établissement)
    heure_arrivee_limite = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Heure limite d'arrivée"),
        help_text=_("Vide : l'heure limite de son profil (enseignant ou administration).")
    )

    heure_depart_normale = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Heure normale de départ"),
        help_text=_("Vide : l'heure de départ de son profil, puis celle de l'établissement.")
    )

    titre_honorifique = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name=_("Titre honorifique"),
        help_text=_("Ex: M. le Directeur, Le Proviseur, Dr.")
    )

    titre_capacite = models.CharField(
        max_length=35,
        blank=True,
        default='',
        verbose_name=_("Titre de capacité"),
        help_text=_("Ex: CAPES, CAP-CEG, Licence, Master")
    )

    date_embauche = models.DateField(
        verbose_name=_("Date d'embauche")
    )
    
    est_contractuel = models.BooleanField(
        default=False,
        verbose_name=_("Personnel contractuel")
    )
    
    est_vacataire = models.BooleanField(
        default=False,
        verbose_name=_("Professeur vacataire")
    )
    
    # Rôle de direction
    est_directeur = models.BooleanField(
        default=False,
        verbose_name=_("Directeur/Proviseur"),
        help_text=_("Cocher si ce membre est le directeur de l'établissement")
    )
    
    est_censeur = models.BooleanField(
        default=False,
        verbose_name=_("Censeur/Proviseur adjoint"),
        help_text=_("Cocher si ce membre est censeur ou proviseur adjoint")
    )
    
    # Informations familiales
    situation_matrimoniale = models.CharField(
        max_length=20,
        choices=SituationMatrimonialeChoices.choices,
        default=SituationMatrimonialeChoices.CELIBATAIRE,
        verbose_name=_("Situation matrimoniale")
    )
    
    nombre_enfants = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Nombre d'enfants à charge")
    )
    
    # Photo
    photo = models.ImageField(
        upload_to='personnel/photos/',
        blank=True,
        null=True,
        verbose_name=_("Photo d'identité")
    )

    signature = models.ImageField(
        upload_to='personnel/signatures/',
        blank=True,
        null=True,
        verbose_name=_("Signature scannée"),
        help_text=_("Image PNG à fond transparent recommandée ; apposée à l'emplacement de la signature "
                    "sur les documents dont ce membre est le signataire")
    )
    
    # Relations
    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='personnel',
        verbose_name=_("Établissement")
    )
    
    # Poste principal - temporairement en CharField, migrera vers FK après
    poste_principal_code = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name=_("Code Poste"),
        help_text=_("Code du poste principal (temporaire)")
    )
    
    cycles = models.ManyToManyField(
        'parametres.Cycle',
        related_name='personnel',
        blank=True,
        verbose_name=_("Cycles d'enseignement")
    )

    classe_affectation = models.ForeignKey(
        'parametres.Classe',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enseignants_titulaires',
        verbose_name=_("Classe d'affectation"),
        help_text=_("Classe dont l'agent est titulaire : il signe les bulletins de notes et la liste "
                    "alphabétique de cette classe.")
    )

    class QualiteAffectation(models.TextChoices):
        TITULAIRE = 'TITULAIRE', _('Titulaire de la classe')
        SUPPLEANT = 'SUPPLEANT', _('Suppléant de la classe')

    qualite_affectation = models.CharField(
        max_length=10,
        choices=QualiteAffectation.choices,
        default=QualiteAffectation.TITULAIRE,
        verbose_name=_("Qualité"),
        help_text=_("Titulaire : signe les bulletins et la liste alphabétique de la classe. "
                    "Suppléant : signe les bulletins de la classe, à côté du titulaire.")
    )
    
    class Meta:
        verbose_name = _("Membre du Personnel")
        verbose_name_plural = _("Membres du Personnel")
        ordering = ['nom', 'prenom']
    
    def __str__(self) -> str:
        return f"{self.prenom} {self.nom} ({self.matricule})"
    
    def get_nom_complet(self) -> str:
        """Retourne le nom complet en majuscules."""
        return f"{self.nom.upper()} {self.prenom}"
    
    @property
    def age(self) -> Optional[int]:
        """Calcule l'âge dynamiquement (non stocké en base)."""
        if self.date_naissance:
            today = date.today()
            return (today - self.date_naissance).days // 365
        return None
    
    def save(self, *args, **kwargs):
        """Générer le matricule automatiquement si vide et déduire le profil de pointage."""
        if not self.matricule:
            self._generate_matricule()
        if (self._state.adding and self.profil_pointage == ProfilPointage.ADMINISTRATION
                and self.deviner_profil_pointage() == ProfilPointage.ENSEIGNANT):
            self.profil_pointage = ProfilPointage.ENSEIGNANT
        super().save(*args, **kwargs)
    
    def _generate_matricule(self):
        """Génère le matricule au format: {CODE_ETAB}-P-{ANNEE}-{SEQ}."""
        from datetime import date as date_module
        
        etab_code = 'XX'
        if self.etablissement and self.etablissement.code:
            etab_code = self.etablissement.code.upper()
        # Le matricule est limité à 30 caractères : {CODE}-P-AAAA-NN → suffixe
        # 10 car. minimum (« -P-2026-01 »), donc le code établissement est
        # tronqué à 18 pour garder une marge sur la séquence.
        etab_code = etab_code[:18]
        
        annee = date_module.today().year
        prefix = f"{etab_code}-P-{annee}-"

        # Séquence suivante = max NUMÉRIQUE des suffixes existants (un tri alphabétique
        # classerait « -1 » après « -02 » ou « -99 » après « -100 » → doublon → IntegrityError).
        sequences = []
        for matricule in MembrePersonnel.objects.filter(matricule__startswith=prefix).values_list('matricule', flat=True):
            try:
                sequences.append(int(matricule[len(prefix):]))
            except ValueError:
                continue  # suffixe non numérique (saisie manuelle) : ignoré
        next_seq = max(sequences, default=0) + 1

        # Format {CODE_ETAB}-P-AAAA-NN (NN sur 2 chiffres minimum)
        self.matricule = f"{prefix}{next_seq:02d}"


# ═══════════════════════════════════════════════════════════════════
# 2. INSCRIPTION ANNUELLE DU PERSONNEL
# ═══════════════════════════════════════════════════════════════════

class InscriptionPersonnel(BaseModel):
    """
    Inscription annuelle d'un membre du personnel.
    
    Chaque personnel doit être inscrit chaque année scolaire pour être
    actif dans les emplois du temps, les présences, les bulletins de
    notes, etc.
    
    Contrainte: Un même personnel ne peut avoir qu'une seule inscription
    active par cycle × année scolaire.
    """
    
    personnel = models.ForeignKey(
        MembrePersonnel,
        on_delete=models.CASCADE,
        related_name='inscriptions',
        verbose_name=_("Membre du personnel")
    )
    
    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='inscriptions_personnel',
        verbose_name=_("Année scolaire")
    )
    
    poste = models.ForeignKey(
        'parametres.Poste',
        on_delete=models.CASCADE,
        related_name='inscriptions',
        verbose_name=_("Poste occupé")
    )
    
    cycle = models.ForeignKey(
        'parametres.Cycle',
        on_delete=models.CASCADE,
        related_name='inscriptions_personnel',
        verbose_name=_("Cycle d'affectation")
    )
    
    est_actif = models.BooleanField(
        default=True,
        verbose_name=_("Inscription active")
    )
    
    date_inscription = models.DateField(
        auto_now_add=True,
        verbose_name=_("Date d'inscription")
    )
    
    date_debut = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Date de début de fonction")
    )
    
    date_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Date de fin de fonction")
    )
    
    observations = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Observations")
    )
    
    # Heures hebdomadaires (pour les vacataires)
    heures_hebdomadaires = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        verbose_name=_("Heures hebdomadaires"),
        help_text=_("Pour les professeurs vacataires")
    )
    
    class Meta:
        verbose_name = _("Inscription Personnel")
        verbose_name_plural = _("Inscriptions Personnel")
        ordering = ['-annee_scolaire', 'personnel__nom']
        unique_together = [['personnel', 'annee_scolaire', 'cycle']]
    
    def __str__(self) -> str:
        return (
            f"{self.personnel} - {self.cycle.nom} - "
            f"{self.annee_scolaire.libelle}"
        )
    
    def clean(self):
        """Validation métier."""
        from django.core.exceptions import ValidationError

        # Vérifier qu'une seule inscription active par année × cycle
        # (ignoré si une FK obligatoire manque : le formulaire signale déjà le champ)
        if self.est_actif and self.personnel_id and self.annee_scolaire_id and self.cycle_id:
            existing = InscriptionPersonnel.objects.filter(
                personnel=self.personnel,
                annee_scolaire=self.annee_scolaire,
                cycle=self.cycle,
                est_actif=True
            ).exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError(
                    _(f"Ce personnel a déjà une inscription active "
                      f"pour {self.cycle.nom} en {self.annee_scolaire.libelle}")
                )


# ═══════════════════════════════════════════════════════════════════
# 3. SALAIRE MENSUEL DU PERSONNEL
# ═══════════════════════════════════════════════════════════════════

class SalairePersonnel(BaseModel):
    """
    Bulletin de salaire mensuel pour un membre du personnel permanent/contractuel.

    Composition du salaire :
      Brut = salaire_base + indemnite_transport + indemnite_logement
             + prime_anciennete + autres_primes
      Net  = Brut − retenue_cnss − retenue_iuts − autres_retenues

    La prime d'ancienneté peut être calculée automatiquement
    à partir de la date d'embauche du membre.
    """

    class StatutChoices(models.TextChoices):
        BROUILLON = 'BROUILLON', _('Brouillon')
        VALIDE    = 'VALIDE',    _('Validé')
        PAYE      = 'PAYE',      _('Payé')

    MOIS_CHOICES = [
        (1, _('Janvier')), (2, _('Février')),  (3, _('Mars')),
        (4, _('Avril')),   (5, _('Mai')),       (6, _('Juin')),
        (7, _('Juillet')), (8, _('Août')),      (9, _('Septembre')),
        (10, _('Octobre')),(11, _('Novembre')),(12, _('Décembre')),
    ]

    personnel = models.ForeignKey(
        MembrePersonnel,
        on_delete=models.CASCADE,
        related_name='salaires',
        verbose_name=_("Membre du personnel")
    )

    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='salaires_personnel',
        verbose_name=_("Année scolaire")
    )

    mois = models.IntegerField(choices=MOIS_CHOICES, verbose_name=_("Mois"))
    annee = models.IntegerField(verbose_name=_("Année"))

    # ── Éléments de rémunération ──────────────────────────────────
    salaire_base = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Salaire de base (FCFA)")
    )
    indemnite_transport = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Indemnité de transport (FCFA)")
    )
    indemnite_logement = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Indemnité de logement (FCFA)")
    )
    prime_anciennete = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Prime d'ancienneté (FCFA)"),
        help_text=_("Calculée automatiquement ou saisie manuellement")
    )
    autres_primes = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Autres primes / avantages (FCFA)")
    )

    # ── Retenues ─────────────────────────────────────────────────
    retenue_cnss = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Retenue CNSS (FCFA)"),
        help_text=_("Cotisation sociale employé")
    )
    retenue_iuts = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Retenue IUTS (FCFA)"),
        help_text=_("Impôt unique sur les traitements et salaires")
    )
    autres_retenues = models.DecimalField(
        max_digits=10, decimal_places=0, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Autres retenues (FCFA)")
    )

    # ── Statut & paiement ────────────────────────────────────────
    statut = models.CharField(
        max_length=10, choices=StatutChoices.choices,
        default=StatutChoices.BROUILLON,
        verbose_name=_("Statut")
    )
    date_paiement = models.DateField(
        blank=True, null=True,
        verbose_name=_("Date de paiement")
    )
    reference_paiement = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name=_("Référence de paiement")
    )
    observations = models.TextField(
        blank=True, default='',
        verbose_name=_("Observations")
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='salaires_saisis',
        verbose_name=_("Saisi par")
    )

    class Meta:
        verbose_name = _("Salaire Personnel")
        verbose_name_plural = _("Salaires Personnel")
        ordering = ['-annee', '-mois', 'personnel__nom']
        unique_together = [['personnel', 'mois', 'annee']]

    def __str__(self):
        return (
            f"Salaire {self.personnel.get_nom_complet()} — "
            f"{self.get_mois_display()} {self.annee}"
        )

    @property
    def salaire_brut(self):
        return (
            self.salaire_base + self.indemnite_transport +
            self.indemnite_logement + self.prime_anciennete +
            self.autres_primes
        )

    @property
    def total_retenues(self):
        return self.retenue_cnss + self.retenue_iuts + self.autres_retenues

    @property
    def salaire_net(self):
        return self.salaire_brut - self.total_retenues

    @classmethod
    def calculer_prime_anciennete(cls, membre, salaire_base):
        """
        Calcule la prime d'ancienneté selon les tranches :
          0-2 ans   →  0 %
          2-5 ans   →  5 %
          5-10 ans  → 10 %
          10-15 ans → 15 %
          15-20 ans → 20 %
          20+ ans   → 25 %
        """
        from decimal import Decimal
        from datetime import date as date_module
        if not membre.date_embauche:
            return Decimal('0')
        anciennete = (date_module.today() - membre.date_embauche).days // 365
        if anciennete < 2:
            taux = Decimal('0')
        elif anciennete < 5:
            taux = Decimal('0.05')
        elif anciennete < 10:
            taux = Decimal('0.10')
        elif anciennete < 15:
            taux = Decimal('0.15')
        elif anciennete < 20:
            taux = Decimal('0.20')
        else:
            taux = Decimal('0.25')
        return (salaire_base * taux).quantize(Decimal('1'))


# ═══════════════════════════════════════════════════════════════════
# 4. CONGÉS DU PERSONNEL
# ═══════════════════════════════════════════════════════════════════

class CongePersonnel(BaseModel):
    """
    Demande et suivi des congés du personnel permanent.

    Droits annuels : 30 jours ouvrables par année de service
    (2.5 jours par mois de service effectif, norme Burkina Faso).
    """

    class TypeCongeChoices(models.TextChoices):
        ANNUEL     = 'ANNUEL',     _('Congé annuel')
        MALADIE    = 'MALADIE',    _('Congé maladie')
        MATERNITE  = 'MATERNITE',  _('Congé de maternité')
        PATERNITE  = 'PATERNITE',  _('Congé de paternité')
        EVENEMENT  = 'EVENEMENT',  _('Événement familial')
        SANS_SOLDE = 'SANS_SOLDE', _('Congé sans solde')

    class StatutChoices(models.TextChoices):
        DEMANDE  = 'DEMANDE',  _('Demandé')
        APPROUVE = 'APPROUVE', _('Approuvé')
        REFUSE   = 'REFUSE',   _('Refusé')
        ANNULE   = 'ANNULE',   _('Annulé')

    DROITS_ANNUELS = 30  # jours ouvrables par an

    personnel = models.ForeignKey(
        MembrePersonnel,
        on_delete=models.CASCADE,
        related_name='conges',
        verbose_name=_("Membre du personnel")
    )
    type_conge = models.CharField(
        max_length=15, choices=TypeCongeChoices.choices,
        default=TypeCongeChoices.ANNUEL,
        verbose_name=_("Type de congé")
    )
    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_fin   = models.DateField(verbose_name=_("Date de fin"))
    nombre_jours = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        verbose_name=_("Nombre de jours ouvrables")
    )
    motif = models.TextField(
        blank=True, default='',
        verbose_name=_("Motif / Justification")
    )
    statut = models.CharField(
        max_length=10, choices=StatutChoices.choices,
        default=StatutChoices.DEMANDE,
        verbose_name=_("Statut")
    )
    date_approbation = models.DateField(
        blank=True, null=True,
        verbose_name=_("Date d'approbation")
    )
    approuve_par = models.ForeignKey(
        MembrePersonnel,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conges_approuves',
        verbose_name=_("Approuvé / Refusé par")
    )
    observations = models.TextField(
        blank=True, default='',
        verbose_name=_("Observations")
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conges_saisis',
        verbose_name=_("Saisi par")
    )

    class Meta:
        verbose_name = _("Congé Personnel")
        verbose_name_plural = _("Congés Personnel")
        ordering = ['-date_debut', 'personnel__nom']

    def __str__(self):
        return (
            f"{self.personnel.get_nom_complet()} — "
            f"{self.get_type_conge_display()} — "
            f"du {self.date_debut.strftime('%d/%m/%Y')} au {self.date_fin.strftime('%d/%m/%Y')}"
        )

    def save(self, *args, **kwargs):
        if self.date_debut and self.date_fin:
            self.nombre_jours = self._calcul_jours_ouvrables()
        super().save(*args, **kwargs)

    def _calcul_jours_ouvrables(self):
        """Compte les jours ouvrables (lun–sam) entre date_debut et date_fin inclus."""
        from datetime import timedelta
        if not self.date_debut or not self.date_fin:
            return 0
        jours = 0
        for i in range((self.date_fin - self.date_debut).days + 1):
            if (self.date_debut + timedelta(days=i)).weekday() < 6:
                jours += 1
        return jours

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError(_("La date de fin doit être postérieure à la date de début."))

    @classmethod
    def jours_pris_annee(cls, membre, annee):
        """Total jours de congé ANNUEL approuvés pour ce membre sur l'année civile."""
        return (
            cls.objects.filter(
                personnel=membre,
                type_conge=cls.TypeCongeChoices.ANNUEL,
                statut=cls.StatutChoices.APPROUVE,
                date_debut__year=annee,
            ).aggregate(total=models.Sum('nombre_jours'))['total'] or 0
        )

    @classmethod
    def jours_restants(cls, membre, annee):
        """Jours de congé annuel restants pour ce membre sur l'année civile."""
        return cls.DROITS_ANNUELS - cls.jours_pris_annee(membre, annee)


# ═══════════════════════════════════════════════════════════════════
# ABSENCES DU PERSONNEL
# ═══════════════════════════════════════════════════════════════════

class ObservationAbsence(BaseModel):
    """Observation proposée dans le champ déroulant des absences du personnel (5.57.0).

    Deux niveaux : la ligne **sans établissement** est commune à toutes les écoles (raison de santé, congé…,
    posées à l'installation) ; une ligne rattachée à un établissement n'apparaît que chez lui. Le bouton
    « + » du formulaire d'absence en ajoute une ici, sans toucher au code.
    """

    etablissement = models.ForeignKey('etablissements.Etablissement', on_delete=models.CASCADE, null=True,
                                      blank=True, related_name='observations_absence',
                                      verbose_name=_("Établissement"),
                                      help_text=_("Vide : observation commune à toutes les écoles."))
    libelle = models.CharField(max_length=80, verbose_name=_("Observation"))
    actif = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("Observation d'absence")
        verbose_name_plural = _("Observations d'absence")
        ordering = ['libelle']
        constraints = [
            models.UniqueConstraint(fields=['etablissement', 'libelle'], name='observation_absence_unique'),
        ]

    def __str__(self):
        return self.libelle

    @classmethod
    def disponibles(cls, etablissement=None):
        """Observations actives applicables à l'établissement : communes puis les siennes."""
        condition = models.Q(etablissement__isnull=True)
        if etablissement is not None:
            condition |= models.Q(etablissement=etablissement)
        return cls.objects.filter(condition, actif=True).order_by('libelle')


class AbsencePersonnel(BaseModel):
    """Absence d'un agent (jours calendaires) : justifiée ou non ; une absence non justifiée marquée « retenue » est
    proposée en retenue sur le brouillon de paie du mois (1/30e du salaire de base par jour)."""

    class MotifChoices(models.TextChoices):
        MALADIE = 'MALADIE', _('Maladie')
        PERMISSION = 'PERMISSION', _('Permission')
        FORMATION = 'FORMATION', _('Formation / mission')
        NON_JUSTIFIEE = 'NON_JUSTIFIEE', _('Non justifiée')
        AUTRE = 'AUTRE', _('Autre')

    personnel = models.ForeignKey(MembrePersonnel, on_delete=models.CASCADE, related_name='absences',
                                  verbose_name=_("Membre du personnel"))
    # Séance manquée (saisie quotidienne des professeurs, 5.58.0) : classe, matière et créneau horaire.
    classe = models.ForeignKey('parametres.Classe', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='absences_personnel', verbose_name=_("Classe"))
    matiere = models.ForeignKey('pedagogie.Matiere', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='absences_personnel', verbose_name=_("Matière"))
    # Primaire : un seul enseignant dispense toutes les disciplines de sa classe → « Toutes les matières ».
    toutes_matieres = models.BooleanField(default=False, verbose_name=_("Toutes les matières"))
    heure_debut = models.TimeField(null=True, blank=True, verbose_name=_("Heure de début"))
    heure_fin = models.TimeField(null=True, blank=True, verbose_name=_("Heure de fin"))
    date_debut = models.DateField(verbose_name=_("Du"))
    date_fin = models.DateField(verbose_name=_("Au"))
    motif = models.CharField(max_length=15, choices=MotifChoices.choices, default=MotifChoices.NON_JUSTIFIEE,
                             verbose_name=_("Motif"))
    justifiee = models.BooleanField(default=False, verbose_name=_("Justifiée (pièce fournie)"))
    retenue = models.BooleanField(default=True, verbose_name=_("Retenue sur salaire"),
                                  help_text=_("Proposée sur le brouillon de paie du mois si l'absence n'est pas justifiée"))
    observation = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Observation"))
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='absences_personnel_saisies', verbose_name=_("Saisie par"))

    class Meta:
        verbose_name = _("Absence du personnel")
        verbose_name_plural = _("Absences du personnel")
        ordering = ['-date_debut']

    def __str__(self):
        return f"{self.personnel.get_nom_complet()} — {self.date_debut:%d/%m/%Y} → {self.date_fin:%d/%m/%Y}"

    @property
    def nombre_jours(self):
        return (self.date_fin - self.date_debut).days + 1

    @property
    def matiere_libelle(self):
        """Matière affichée : « Toutes les matières », le nom de la matière retenue, ou un tiret."""
        if self.toutes_matieres:
            return "Toutes les matières"
        return self.matiere.nom if self.matiere_id else "—"

    @property
    def nombre_heures(self):
        """Durée de la séance manquée, en heures décimales (0 si l'un des deux horaires manque)."""
        if not (self.heure_debut and self.heure_fin):
            return 0.0
        debut = self.heure_debut.hour * 60 + self.heure_debut.minute
        fin = self.heure_fin.hour * 60 + self.heure_fin.minute
        return round(max(0, fin - debut) / 60, 2)

    @property
    def a_retenir(self):
        return self.retenue and not self.justifiee

    @classmethod
    def jours_retenus(cls, membre, mois, annee):
        """Jours d'absence non justifiés à retenir pour ``membre`` sur le mois civil (bornés au mois)."""
        import calendar
        debut, fin = date(annee, mois, 1), date(annee, mois, calendar.monthrange(annee, mois)[1])
        total = 0
        for a in cls.objects.filter(personnel=membre, retenue=True, justifiee=False, date_debut__lte=fin, date_fin__gte=debut):
            total += (min(a.date_fin, fin) - max(a.date_debut, debut)).days + 1
        return total
