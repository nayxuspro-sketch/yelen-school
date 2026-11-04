"""Sanctions, distinctions, calendrier, modèles de message et déclencheurs SMS."""

import datetime
import logging
import re
from django.db import models
from django.utils.translation import gettext_lazy as _
logger = logging.getLogger(__name__)
from core.models import BaseModel

from .annee import AnneeScolaire


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


class Distinction(BaseModel):
    """Mentions et distinctions décernées par le conseil de classe (cochées dans la saisie du bulletin).

    Ex: FELICITATIONS, TABLEAU_HONNEUR, ENCOURAGEMENTS, AVERTISSEMENT, BLAME.
    """

    code = models.CharField(max_length=20, unique=True, verbose_name=_("Code"),
                            help_text=_("Ex: FELICITATIONS, TABLEAU_HONNEUR"))
    libelle = models.CharField(max_length=100, verbose_name=_("Libellé"),
                               help_text=_("Ex: Félicitations, Tableau d'honneur"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    ordre = models.PositiveSmallIntegerField(default=0, verbose_name=_("Ordre d'affichage"))
    actif = models.BooleanField(default=True, verbose_name=_("Mention active"))

    class Meta:
        verbose_name = _("Mention / distinction")
        verbose_name_plural = _("Mentions / distinctions")
        ordering = ['ordre', 'libelle']

    def __str__(self):
        return self.libelle


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
      SANCTION  : {nom_eleve}, {classe}, {date}, {sanction}, {motif}, {etablissement}
      PRET      : {nom_eleve}, {classe}, {ouvrage}, {date}, {etablissement}
    """

    class TypeChoices(models.TextChoices):
        BULLETIN = 'BULLETIN', 'Disponibilité du bulletin'
        ABSENCE  = 'ABSENCE',  'Absence élève'
        RETARD   = 'RETARD',   'Retard élève'
        SEUIL_ABSENCES = 'SEUIL_ABSENCES', "Seuil d'absences atteint"
        SANCTION = 'SANCTION', 'Sanction disciplinaire'
        PAIEMENT = 'PAIEMENT', 'Relance paiement'
        PRET     = 'PRET',     "Prêt d'ouvrage en retard"
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
        'SEUIL_ABSENCES': (
            "Bonjour, votre enfant {nom_eleve} ({classe}) totalise {nb} absences non justifiées "
            "({periode}). Merci de contacter {etablissement} rapidement."
        ),
        'SANCTION': (
            "Bonjour, votre enfant {nom_eleve} ({classe}) a reçu une sanction le {date} : {sanction}. "
            "Motif : {motif}. — {etablissement}"
        ),
        'PAIEMENT': (
            "Bonjour, un rappel de paiement : {rubrique} de {montant} FCFA "
            "pour {nom_eleve} est en attente. Contactez {etablissement}."
        ),
        'PRET': (
            "Bonjour, l'ouvrage « {ouvrage} » emprunté par {nom_eleve} ({classe}) devait être rendu le {date}. "
            "Merci de le rapporter à {etablissement}."
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

    VARIABLE = re.compile(r'\{(\w+)\}')

    @classmethod
    def rendre(cls, contenu, variables):
        """Substitue les variables ``{nom}`` connues ; tout autre texte, accolades comprises, reste tel quel
        (jamais d'exception, contrairement à ``str.format``)."""
        return cls.VARIABLE.sub(lambda m: str(variables.get(m.group(1), m.group(0))), contenu)

    @classmethod
    def variables_inconnues(cls, contenu, connues):
        """Noms de variables cités dans ``contenu`` et absents de ``connues``, triés."""
        return sorted({nom for nom in cls.VARIABLE.findall(contenu) if nom not in connues})

    @classmethod
    def get_contenu(cls, etablissement, type_msg, variables):
        """Message SMS de ce type pour l'établissement : son modèle personnalisé actif, ou le texte par défaut
        si aucun n'est configuré — ou si le modèle cite une variable inconnue (le parent recevrait sinon
        ``{nom_eleve}`` ou ``{rubrique}`` tels quels)."""
        defaut = cls.DEFAUTS.get(type_msg, '')
        modele = cls.objects.filter(etablissement=etablissement, type=type_msg, actif=True).first()
        contenu = modele.contenu_sms if modele else defaut
        inconnues = cls.variables_inconnues(contenu, variables)
        if inconnues:
            logger.warning("Modèle SMS %s de %s ignoré (variables inconnues : %s) : texte par défaut utilisé.",
                           type_msg, etablissement, ', '.join(inconnues))
            contenu = defaut
        return cls.rendre(contenu, variables)


class DeclencheurSMS(BaseModel):
    """
    Configuration d'un envoi SMS automatique planifié.

    Chaque déclencheur correspond à un type d'événement (absence, échéancier, résultats).
    L'exécution est déclenchée par la commande management `sms_auto` ou manuellement
    depuis l'interface Paramètres.

    Types disponibles :
      ABSENCE_J1   — SMS J+1 pour absences non justifiées de la veille
      ECHEANCIER   — Rappel N jours avant l'échéance impayée
      RESULTATS    — SMS à la publication d'un nouveau bulletin
      PRETS_RETARD — Relance des prêts d'ouvrages échus (bibliothèque)
      COMPTE_RENDU — Compte rendu quotidien du promoteur (encaissements, caisse, absences), envoyé à
                     ``heure_envoi`` par le service SMS (``communication.compte_rendu``)
    """

    class TypeChoices(models.TextChoices):
        ABSENCE_J1 = 'ABSENCE_J1', _('Absences non justifiées (J+1)')
        ECHEANCIER = 'ECHEANCIER', _("Rappel d'échéancier")
        RESULTATS  = 'RESULTATS',  _('Bulletin disponible')
        PRETS_RETARD = 'PRETS_RETARD', _("Prêt d'ouvrage en retard")
        COMPTE_RENDU = 'COMPTE_RENDU', _('Compte rendu quotidien du promoteur')

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

    heure_envoi = models.TimeField(
        default=datetime.time(18, 0),
        verbose_name=_("Heure d'envoi"),
        help_text=_("Compte rendu quotidien : heure à laquelle le SMS du jour est envoyé."),
    )

    destinataires = models.CharField(
        max_length=120,
        blank=True,
        default='',
        verbose_name=_("Destinataires"),
        help_text=_("Compte rendu quotidien : numéros du promoteur, séparés par des virgules."),
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

    def liste_destinataires(self):
        """Numéros configurés, un par entrée (séparateurs : virgule, point-virgule, espace, retour à la ligne)."""
        return [n for n in re.split(r'[,;\s]+', self.destinataires or '') if n]

    class Meta:
        verbose_name = _("Déclencheur SMS automatique")
        verbose_name_plural = _("Déclencheurs SMS automatiques")
        unique_together = [['etablissement', 'type_declencheur']]
        ordering = ['type_declencheur']

    def __str__(self):
        statut = "✅" if self.actif else "⏸"
        return f"{statut} {self.get_type_declencheur_display()} — {self.etablissement}"
