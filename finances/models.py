import datetime
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel
from parametres.models import AnneeScolaire, Classe
from inscriptions.models import Inscription
from django.conf import settings

class TypeFrais(models.TextChoices):
    SCOLARITE = 'SCOLARITE', _('Scolarité')
    INSCRIPTION = 'INSCRIPTION', _('Inscription')
    EXAMEN = 'EXAMEN', _('Frais d\'examen')
    AUTRE = 'AUTRE', _('Autre')

class FraisScolarite(BaseModel):
    """Configuration des frais par classe ou cycle."""
    annee_scolaire = models.ForeignKey(AnneeScolaire, on_delete=models.CASCADE, verbose_name=_("Année Scolaire"))
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, verbose_name=_("Classe"), null=True, blank=True)
    cycle = models.CharField(
        max_length=20, 
        choices=[
            ('PRESCOLAIRE', 'Préscolaire'),
            ('PRIMAIRE', 'Primaire'),
            ('POST_PRIMAIRE', 'Post-primaire'),
            ('SECONDAIRE', 'Secondaire'),
        ],
        null=True, blank=True
    )
    type_frais = models.CharField(max_length=20, choices=TypeFrais.choices, default=TypeFrais.SCOLARITE)
    montant = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Montant (FCFA)"))
    
    class Meta:
        verbose_name = _("Frais de Scolarité")
        verbose_name_plural = _("Frais de Scolarité")
        unique_together = ('annee_scolaire', 'classe', 'type_frais')

    def __str__(self):
        target = self.classe.nom if self.classe else self.get_cycle_display()
        return f"{self.get_type_frais_display()} - {target} ({self.montant} FCFA)"

class ModePaiement(models.TextChoices):
    ESPECES = 'ESPECES', _('Espèces')
    VIREMENT = 'VIREMENT', _('Virement Bancaire')
    MOBILE_MONEY = 'MOBILE_MONEY', _('Mobile Money')
    CHEQUE = 'CHEQUE', _('Chèque')

class Paiement(BaseModel):
    """Enregistrement d'un paiement effectué par un élève."""
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='paiements')
    numero_recu = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_("Numéro de reçu"),
    )
    rubrique = models.ForeignKey(
        'parametres.RubriquePaiement',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Rubrique de paiement")
    )
    # Statut de l'élève au moment du paiement (figé pour l'historique)
    statut_eleve = models.ForeignKey(
        'parametres.StatutEleve',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Statut élève au paiement"),
        help_text=_("Statut de l'élève tel qu'il était au moment du versement")
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Montant Versé"))
    date_paiement = models.DateField(default=datetime.date.today, verbose_name=_("Date de transaction"))
    mode_paiement = models.CharField(max_length=20, choices=ModePaiement.choices, default=ModePaiement.ESPECES)
    reference = models.CharField(max_length=100, blank=True, verbose_name=_("Référence Transaction"))
    encaisse_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    echeance = models.DateField(null=True, blank=True, verbose_name=_("Échéance"))
    observation = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
        ordering = ['-date_paiement', '-created_at']

    def save(self, *args, **kwargs):
        if not self.numero_recu:
            self.numero_recu = self._generer_numero_recu()
        super().save(*args, **kwargs)

    def _generer_numero_recu(self):
        """Génère un numéro de reçu unique: REC-2026-00001"""
        from django.utils import timezone
        annee = timezone.now().year
        dernier = Paiement.objects.filter(
            numero_recu__startswith=f'REC-{annee}'
        ).order_by('-numero_recu').first()
        
        if dernier and dernier.numero_recu:
            try:
                seq = int(dernier.numero_recu.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        
        return f'REC-{annee}-{seq:05d}'

    def __str__(self):
        return f"Paiement {self.inscription.eleve} - {self.montant} FCFA"

class Remboursement(BaseModel):
    """Remboursement total ou partiel d'un paiement."""
    paiement = models.ForeignKey(
        Paiement,
        on_delete=models.CASCADE,
        related_name='remboursements',
        verbose_name=_("Paiement d'origine"),
    )
    montant = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name=_("Montant remboursé"),
    )
    motif = models.CharField(
        max_length=255, blank=True,
        verbose_name=_("Motif du remboursement"),
    )
    date_remboursement = models.DateField(
        default=datetime.date.today,
        verbose_name=_("Date de remboursement"),
    )
    rembourse_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Remboursé par"),
    )

    class Meta:
        verbose_name = _("Remboursement")
        verbose_name_plural = _("Remboursements")
        ordering = ['-date_remboursement', '-created_at']

    def __str__(self):
        return f"Remboursement {self.montant} FCFA — {self.paiement}"


class Echeancier(BaseModel):
    """Calendrier de paiement pour un élève."""
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='echeancier')
    libelle = models.CharField(max_length=100)
    date_limite = models.DateField()
    montant_du = models.DecimalField(max_digits=12, decimal_places=2)
    paye = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Échéance de paiement")
        verbose_name_plural = _("Échéancier")
        ordering = ['date_limite']

    def __str__(self):
        return f"{self.libelle} - {self.inscription.eleve} ({self.montant_du} FCFA)"


class TypeReduction(models.TextChoices):
    POURCENTAGE = 'POURCENTAGE', _('Pourcentage (%)')
    MONTANT_FIXE = 'MONTANT_FIXE', _('Montant fixe (FCFA)')


class SourceBourse(models.TextChoices):
    ETAT = 'ETAT', _('État / Gouvernement')
    ONG = 'ONG', _('ONG / Organisation internationale')
    ETABLISSEMENT = 'ETABLISSEMENT', _('Établissement')
    AUTRE = 'AUTRE', _('Autre')


class TypeBourse(BaseModel):
    """Type de bourse ou d'aide scolaire (paramétrable par établissement)."""
    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='types_bourses',
        verbose_name=_("Établissement"),
    )
    nom = models.CharField(max_length=100, verbose_name=_("Nom"))
    code = models.CharField(max_length=20, verbose_name=_("Code"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    source = models.CharField(
        max_length=20,
        choices=SourceBourse.choices,
        default=SourceBourse.ETABLISSEMENT,
        verbose_name=_("Source"),
    )
    type_reduction = models.CharField(
        max_length=20,
        choices=TypeReduction.choices,
        default=TypeReduction.POURCENTAGE,
        verbose_name=_("Type de réduction"),
    )
    valeur_reduction = models.DecimalField(
        max_digits=8, decimal_places=2,
        verbose_name=_("Valeur de la réduction"),
        help_text=_("Pourcentage (ex: 50) ou montant fixe (ex: 25000)"),
    )
    rubrique = models.ForeignKey(
        'parametres.RubriquePaiement',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Rubrique concernée"),
        help_text=_("Laisser vide pour appliquer sur le total toutes rubriques"),
    )
    actif = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Type de bourse")
        verbose_name_plural = _("Types de bourses")
        unique_together = ('etablissement', 'code')
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.get_source_display()})"


class BourseEleve(BaseModel):
    """Attribution d'une bourse ou aide scolaire à une inscription."""
    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.CASCADE,
        related_name='bourses',
        verbose_name=_("Inscription"),
    )
    type_bourse = models.ForeignKey(
        TypeBourse,
        on_delete=models.CASCADE,
        related_name='attributions',
        verbose_name=_("Type de bourse"),
    )
    montant_accorde = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name=_("Montant accordé (FCFA)"),
        help_text=_("Calculé automatiquement à partir du type; peut être modifié"),
    )
    rubrique = models.ForeignKey(
        'parametres.RubriquePaiement',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Rubrique ciblée"),
        help_text=_("Laisser vide pour réduction globale sur le total dû"),
    )
    date_attribution = models.DateField(
        default=datetime.date.today,
        verbose_name=_("Date d'attribution"),
    )
    date_expiration = models.DateField(
        null=True, blank=True,
        verbose_name=_("Date d'expiration"),
    )
    reference_document = models.CharField(
        max_length=100, blank=True,
        verbose_name=_("Référence / N° décision"),
    )
    observation = models.TextField(blank=True, verbose_name=_("Observation"))
    attribue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Attribué par"),
    )
    actif = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Bourse / Aide scolaire")
        verbose_name_plural = _("Bourses / Aides scolaires")
        ordering = ['-date_attribution']

    def __str__(self):
        return (
            f"{self.type_bourse.nom} — {self.inscription.eleve.get_nom_complet()} "
            f"({self.montant_accorde} FCFA)"
        )


class CanalRelance(models.TextChoices):
    PDF = 'PDF', _('PDF imprimé')
    SMS = 'SMS', _('SMS')


class HistoriqueRelance(BaseModel):
    """Trace chaque relance envoyée (PDF ou SMS) pour un élève et une rubrique."""
    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.CASCADE,
        related_name='relances',
        verbose_name=_("Inscription"),
    )
    rubrique = models.ForeignKey(
        'parametres.RubriquePaiement',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Rubrique"),
    )
    canal = models.CharField(
        max_length=10,
        choices=CanalRelance.choices,
        default=CanalRelance.PDF,
        verbose_name=_("Canal"),
    )
    montant_reclame = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name=_("Montant réclamé (FCFA)"),
    )
    envoye_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Envoyé par"),
    )
    date_relance = models.DateField(
        default=datetime.date.today,
        verbose_name=_("Date de relance"),
    )
    succes = models.BooleanField(
        default=True,
        verbose_name=_("Envoi réussi"),
        help_text=_("False si l'envoi SMS a échoué ou si le numéro était invalide"),
    )
    detail = models.CharField(
        max_length=255, blank=True,
        verbose_name=_("Détail"),
        help_text=_("Numéro de téléphone pour SMS, nom du fichier PDF, etc."),
    )

    class Meta:
        verbose_name = _("Historique de relance")
        verbose_name_plural = _("Historiques de relances")
        ordering = ['-date_relance', '-created_at']

    def __str__(self):
        return (
            f"Relance {self.get_canal_display()} — "
            f"{self.inscription.eleve} — {self.date_relance}"
        )
