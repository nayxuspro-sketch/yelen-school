"""Budget, dépenses, bourses, services annexes, relances, comptabilité SYSCOHADA et caisse."""
import datetime

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel
from core.utils import fcfa
from inscriptions.models import Inscription
from parametres.models import AnneeScolaire

from .scolarite import Echeancier, ModePaiement, Paiement


#  MODULE BUDGET & DÉPENSES
# ─────────────────────────────────────────────────────────────────────────────

class TypeDepense(models.TextChoices):
    SALAIRES      = 'SALAIRES',      _('Salaires et charges')
    FOURNITURES   = 'FOURNITURES',   _('Fournitures et matériel')
    MAINTENANCE   = 'MAINTENANCE',   _('Maintenance et réparations')
    UTILITIES     = 'UTILITIES',     _('Eau, électricité, internet')
    COMMUNICATION = 'COMMUNICATION', _('Communication et publicité')
    TRANSPORT     = 'TRANSPORT',     _('Transport et déplacements')
    FORMATION     = 'FORMATION',     _('Formation du personnel')
    AUTRE         = 'AUTRE',         _('Autres dépenses')


class StatutDepense(models.TextChoices):
    BROUILLON = 'BROUILLON', _('Brouillon')
    VALIDEE   = 'VALIDEE',   _('Validée')
    ANNULEE   = 'ANNULEE',   _('Annulée')


class CategorieDepense(BaseModel):
    """Catégorie de dépense paramétrable par établissement."""
    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='categories_depenses',
        verbose_name=_("Établissement"),
    )
    nom = models.CharField(max_length=100, verbose_name=_("Nom"))
    code = models.CharField(max_length=20, verbose_name=_("Code"))
    type_depense = models.CharField(
        max_length=20,
        choices=TypeDepense.choices,
        default=TypeDepense.AUTRE,
        verbose_name=_("Type"),
    )
    actif = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Catégorie de dépense")
        verbose_name_plural = _("Catégories de dépenses")
        unique_together = ('etablissement', 'code')
        ordering = ['type_depense', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_type_depense_display()})"


class BudgetAnnuel(BaseModel):
    """Budget prévisionnel par catégorie de dépense et par année scolaire."""
    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='budgets',
        verbose_name=_("Année scolaire"),
    )
    categorie = models.ForeignKey(
        CategorieDepense,
        on_delete=models.CASCADE,
        related_name='budgets',
        verbose_name=_("Catégorie"),
    )
    montant_prevu = models.DecimalField(
        max_digits=14, decimal_places=2,
        default=0,
        verbose_name=_("Montant prévu (FCFA)"),
    )

    class Meta:
        verbose_name = _("Budget annuel")
        verbose_name_plural = _("Budgets annuels")
        unique_together = ('annee_scolaire', 'categorie')
        ordering = ['categorie__type_depense', 'categorie__nom']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(montant_prevu__gte=0),
                name='budget_montant_non_negatif',
            ),
        ]

    def __str__(self):
        return f"{self.categorie} — {self.annee_scolaire} : {self.montant_prevu} FCFA"


class Depense(BaseModel):
    """Enregistrement d'une dépense de l'établissement."""
    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='depenses',
        verbose_name=_("Année scolaire"),
    )
    categorie = models.ForeignKey(
        CategorieDepense,
        on_delete=models.CASCADE,
        related_name='depenses',
        verbose_name=_("Catégorie"),
    )
    numero_depense = models.CharField(
        max_length=20, unique=True, blank=True,
        verbose_name=_("N° dépense"),
    )
    libelle = models.CharField(max_length=200, verbose_name=_("Libellé"))
    montant = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name=_("Montant (FCFA)"),
    )
    date_depense = models.DateField(
        default=datetime.date.today,
        verbose_name=_("Date"),
    )
    mode_paiement = models.CharField(
        max_length=20,
        choices=ModePaiement.choices,
        default=ModePaiement.ESPECES,
        verbose_name=_("Mode de paiement"),
    )
    beneficiaire = models.CharField(
        max_length=200, blank=True,
        verbose_name=_("Bénéficiaire"),
    )
    reference = models.CharField(
        max_length=100, blank=True,
        verbose_name=_("Référence / N° pièce"),
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutDepense.choices,
        default=StatutDepense.BROUILLON,
        verbose_name=_("Statut"),
    )
    observation = models.TextField(blank=True, verbose_name=_("Observation"))
    saisi_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='depenses_saisies',
        verbose_name=_("Saisi par"),
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='depenses_validees',
        verbose_name=_("Validé par"),
    )
    date_validation = models.DateField(null=True, blank=True, verbose_name=_("Date de validation"))
    motif_annulation = models.TextField(blank=True, verbose_name=_("Motif d'annulation"))

    class Meta:
        verbose_name = _("Dépense")
        verbose_name_plural = _("Dépenses")
        ordering = ['-date_depense', '-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(montant__gt=0),
                name='depense_montant_positif',
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.numero_depense:
            self.numero_depense = self._generer_numero()
        super().save(*args, **kwargs)

    def _generer_numero(self):
        from django.utils import timezone
        annee = timezone.now().year
        dernier = Depense.objects.filter(
            numero_depense__startswith=f'DEP-{annee}'
        ).order_by('-numero_depense').first()
        if dernier and dernier.numero_depense:
            try:
                seq = int(dernier.numero_depense.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'DEP-{annee}-{seq:05d}'

    def __str__(self):
        return f"{self.numero_depense} — {self.libelle} ({self.montant} FCFA)"


class OperateurMobileMoney(models.TextChoices):
    ORANGE = 'ORANGE', _('Orange Money')
    MOOV = 'MOOV', _('Moov Money')
    AUTRE = 'AUTRE', _('Autre (agrégateur, banque)')


class ReleveMobileMoney(BaseModel):
    """Relevé marchand Orange Money / Moov Money importé pour rapprochement (hors ligne)."""

    etablissement = models.ForeignKey(
        'etablissements.Etablissement', on_delete=models.CASCADE,
        related_name='releves_mobile_money', verbose_name=_("Établissement"),
    )
    operateur = models.CharField(max_length=10, choices=OperateurMobileMoney.choices, verbose_name=_("Opérateur"))
    nom_fichier = models.CharField(max_length=255, verbose_name=_("Fichier importé"))
    rubrique = models.ForeignKey(
        'parametres.RubriquePaiement', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Rubrique des paiements créés"),
    )
    importe_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='releves_mobile_money_importes', verbose_name=_("Importé par"),
    )
    nb_lignes_fichier = models.PositiveIntegerField(default=0, verbose_name=_("Lignes lues"))
    nb_doublons = models.PositiveIntegerField(default=0, verbose_name=_("Transactions déjà importées"))
    nb_rejets = models.PositiveIntegerField(default=0, verbose_name=_("Lignes rejetées"))

    class Meta:
        verbose_name = _("Relevé Mobile Money")
        verbose_name_plural = _("Relevés Mobile Money")
        ordering = ['-created_at']

    def __str__(self):
        return f"Relevé {self.get_operateur_display()} du {self.created_at:%d/%m/%Y} ({self.nom_fichier})"


class LigneReleve(BaseModel):
    """Transaction d'un relevé Mobile Money et son rapprochement avec un paiement."""

    class Statut(models.TextChoices):
        PROPOSE = 'PROPOSE', _('Rapprochement proposé')
        A_CONFIRMER = 'A_CONFIRMER', _('À confirmer')
        NON_IDENTIFIE = 'NON_IDENTIFIE', _('Non identifié')
        RAPPROCHE = 'RAPPROCHE', _('Rapproché')
        IGNORE = 'IGNORE', _('Ignoré')

    class Methode(models.TextChoices):
        TRANSACTION = 'TRANSACTION', _('N° de transaction d’un paiement saisi au guichet')
        DEMANDE = 'DEMANDE', _('Référence d’une demande Mobile Money')
        MATRICULE = 'MATRICULE', _('Matricule présent dans le motif')
        TELEPHONE = 'TELEPHONE', _('Téléphone du tuteur et montant restant dû')
        MANUEL = 'MANUEL', _('Affectation manuelle')

    releve = models.ForeignKey(ReleveMobileMoney, on_delete=models.CASCADE, related_name='lignes')
    operateur = models.CharField(max_length=10, choices=OperateurMobileMoney.choices)
    numero_transaction = models.CharField(max_length=64, verbose_name=_("N° de transaction"))
    date_operation = models.DateTimeField(verbose_name=_("Date de l'opération"))
    montant = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Montant reçu (FCFA)"))
    frais = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_("Frais (FCFA)"))
    telephone_payeur = models.CharField(max_length=20, blank=True, verbose_name=_("Téléphone du payeur"))
    nom_payeur = models.CharField(max_length=120, blank=True, verbose_name=_("Nom du payeur"))
    motif = models.CharField(max_length=255, blank=True, verbose_name=_("Motif / libellé"))
    statut = models.CharField(max_length=15, choices=Statut.choices, default=Statut.NON_IDENTIFIE)
    methode = models.CharField(max_length=12, choices=Methode.choices, blank=True, verbose_name=_("Méthode"))
    inscription = models.ForeignKey(
        Inscription, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lignes_releve', verbose_name=_("Élève proposé"),
    )
    paiement = models.OneToOneField(
        Paiement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ligne_releve', verbose_name=_("Paiement rapproché"),
    )
    motif_ignore = models.CharField(max_length=255, blank=True, verbose_name=_("Motif d'exclusion"))

    class Meta:
        verbose_name = _("Ligne de relevé Mobile Money")
        verbose_name_plural = _("Lignes de relevé Mobile Money")
        ordering = ['date_operation', 'numero_transaction']
        constraints = [
            models.UniqueConstraint(fields=['operateur', 'numero_transaction'], name='ligne_releve_transaction_unique'),
            models.CheckConstraint(condition=models.Q(montant__gt=0), name='ligne_releve_montant_positif'),
        ]

    def __str__(self):
        return f"{self.numero_transaction} — {self.montant} FCFA"


# ═══════════════════════════════════════════════════════════════════
# SERVICES ANNEXES FACTURÉS — cantine, transport, internat
# ═══════════════════════════════════════════════════════════════════

class TypeService(models.TextChoices):
    CANTINE = 'CANTINE', _('Cantine')
    TRANSPORT = 'TRANSPORT', _('Transport')
    INTERNAT = 'INTERNAT', _('Internat')


class PeriodiciteService(models.TextChoices):
    MENSUEL = 'MENSUEL', _('Mensuel')
    TRIMESTRIEL = 'TRIMESTRIEL', _('Trimestriel')
    ANNUEL = 'ANNUEL', _('Annuel')


# Code de la rubrique de paiement créée automatiquement pour un service.
CODES_RUBRIQUE_SERVICE = {
    TypeService.CANTINE: 'CANT',
    TypeService.TRANSPORT: 'TRANS',
    TypeService.INTERNAT: 'INTER',
}


class ServiceAnnexe(BaseModel):
    """Service facturé en plus de la scolarité ; ses encaissements passent par ``rubrique``."""
    etablissement = models.ForeignKey(
        'etablissements.Etablissement', on_delete=models.CASCADE, related_name='services_annexes',
        verbose_name=_("Établissement"),
    )
    type_service = models.CharField(max_length=10, choices=TypeService.choices, verbose_name=_("Type"))
    nom = models.CharField(max_length=100, verbose_name=_("Nom"))
    rubrique = models.ForeignKey(
        'parametres.RubriquePaiement', on_delete=models.PROTECT, related_name='services_annexes',
        verbose_name=_("Rubrique de paiement"),
    )
    periodicite = models.CharField(
        max_length=12, choices=PeriodiciteService.choices, default=PeriodiciteService.MENSUEL,
        verbose_name=_("Périodicité des tarifs"),
    )
    actif = models.BooleanField(default=True, verbose_name=_("Service actif"))

    class Meta:
        verbose_name = _("Service annexe")
        verbose_name_plural = _("Services annexes")
        ordering = ['type_service', 'nom']
        unique_together = [['etablissement', 'nom']]

    def __str__(self):
        return self.nom

    def nb_periodes(self, date_debut, date_fin):
        """Périodes facturées entre deux dates incluses : mois civils entamés, trimestres (3 mois) ou 1."""
        if self.periodicite == PeriodiciteService.ANNUEL:
            return 1
        mois = (date_fin.year - date_debut.year) * 12 + date_fin.month - date_debut.month + 1
        if self.periodicite == PeriodiciteService.TRIMESTRIEL:
            return -(-mois // 3)
        return mois


class FormuleService(BaseModel):
    """Tarif d'un service par période : zone de transport, régime d'internat, formule de cantine."""
    service = models.ForeignKey(ServiceAnnexe, on_delete=models.CASCADE, related_name='formules', verbose_name=_("Service"))
    libelle = models.CharField(max_length=100, verbose_name=_("Libellé"))
    montant = models.DecimalField(max_digits=10, decimal_places=0, verbose_name=_("Montant par période (FCFA)"))
    actif = models.BooleanField(default=True, verbose_name=_("Formule active"))

    class Meta:
        verbose_name = _("Formule de service")
        verbose_name_plural = _("Formules de service")
        ordering = ['service', 'montant', 'libelle']
        unique_together = [['service', 'libelle']]
        constraints = [models.CheckConstraint(condition=models.Q(montant__gt=0), name='formule_service_montant_positif')]

    def __str__(self):
        return f"{self.service.nom} — {self.libelle}"


class AbonnementService(BaseModel):
    """Souscription d'un élève à une formule ; le montant dû est figé à la souscription."""
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='abonnements_services')
    formule = models.ForeignKey(FormuleService, on_delete=models.PROTECT, related_name='abonnements', verbose_name=_("Formule"))
    date_debut = models.DateField(verbose_name=_("Début"))
    date_fin = models.DateField(verbose_name=_("Fin"))
    nb_periodes = models.PositiveSmallIntegerField(verbose_name=_("Périodes facturées"))
    montant_periode = models.DecimalField(max_digits=10, decimal_places=0, verbose_name=_("Montant par période (FCFA)"))
    montant_total = models.DecimalField(max_digits=12, decimal_places=0, verbose_name=_("Montant dû (FCFA)"))
    actif = models.BooleanField(default=True, verbose_name=_("Abonnement actif"))
    observation = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Observation"))

    class Meta:
        verbose_name = _("Abonnement à un service")
        verbose_name_plural = _("Abonnements aux services")
        ordering = ['formule__service', 'date_debut']
        constraints = [
            models.CheckConstraint(condition=models.Q(date_fin__gte=models.F('date_debut')),
                                   name='abonnement_service_dates_ordonnees'),
        ]

    def __str__(self):
        return f"{self.inscription.eleve} — {self.formule}"

    @property
    def periodes_libelle(self):
        """« 9 mois du 01/10/2026 au 30/06/2027 », « 3 trimestres du … », « forfait annuel du … »."""
        periodicite = self.formule.service.periodicite
        if periodicite == PeriodiciteService.ANNUEL:
            quantite = "forfait annuel"
        elif periodicite == PeriodiciteService.MENSUEL:
            quantite = f"{self.nb_periodes} mois"
        else:
            quantite = f"{self.nb_periodes} trimestre{'s' if self.nb_periodes > 1 else ''}"
        return f"{quantite} du {self.date_debut:%d/%m/%Y} au {self.date_fin:%d/%m/%Y}"

    def calculer(self):
        """Fige périodes et montants d'après la formule et les dates."""
        self.nb_periodes = self.formule.service.nb_periodes(self.date_debut, self.date_fin)
        self.montant_periode = self.formule.montant
        self.montant_total = self.montant_periode * self.nb_periodes

    def save(self, *args, **kwargs):
        if not self.montant_total:
            self.calculer()
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════
# CRÉANCES INDIVIDUELLES (manuel non rendu, dégât matériel…)
# ═══════════════════════════════════════════════════════════════════

class OrigineCreance(models.TextChoices):
    MANUEL = 'MANUEL', _('Manuel non rendu')
    PENALITE = 'PENALITE', _('Pénalité de retard')
    AUTRE = 'AUTRE', _('Autre')


class Creance(BaseModel):
    """Montant dû par un élève à titre individuel, hors tarifs de sa classe. Intégré à sa situation financière
    comme une rubrique à payer : il compte dans le reste à payer et les relances, s'encaisse sur sa rubrique
    (reçu ordinaire) et se solde par un paiement — jamais par un faux paiement."""
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='creances')
    rubrique = models.ForeignKey('parametres.RubriquePaiement', on_delete=models.PROTECT, related_name='creances',
                                 verbose_name=_("Rubrique"))
    origine = models.CharField(max_length=10, choices=OrigineCreance.choices, default=OrigineCreance.AUTRE,
                               verbose_name=_("Origine"))
    libelle = models.CharField(max_length=200, verbose_name=_("Libellé"))
    montant = models.DecimalField(max_digits=12, decimal_places=0, verbose_name=_("Montant dû (FCFA)"))
    date_creance = models.DateField(default=datetime.date.today, verbose_name=_("Date"))
    emise_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='creances_emises', verbose_name=_("Émise par"))
    actif = models.BooleanField(default=True, verbose_name=_("Créance active"))
    observation = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Observation"))
    # Pénalité de retard : échéance qui l'a déclenchée (une seule pénalité active par échéance).
    echeance = models.ForeignKey(Echeancier, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='penalites', verbose_name=_("Échéance d'origine"))

    class Meta:
        verbose_name = _("Créance")
        verbose_name_plural = _("Créances")
        ordering = ['-date_creance', '-created_at']
        constraints = [models.CheckConstraint(condition=models.Q(montant__gt=0), name='creance_montant_positif')]

    def __str__(self):
        return f"{self.inscription.eleve} — {self.libelle} ({fcfa(self.montant)})"

    def annuler(self, observation=''):
        """Plus rien n'est dû ; la créance reste visible pour l'historique."""
        self.actif = False
        if observation:
            self.observation = observation[:200]
        self.save(update_fields=['actif', 'observation', 'updated_at'])


# ═══════════════════════════════════════════════════════════════════
# PARAMÈTRES FINANCIERS, ARRÊTÉ DE CAISSE
# ═══════════════════════════════════════════════════════════════════

class ModePenalite(models.TextChoices):
    AUCUNE = 'AUCUNE', _('Aucune pénalité')
    FIXE = 'FIXE', _('Montant fixe par échéance en retard')
    POURCENT = 'POURCENT', _("Pourcentage de l'échéance en retard")


class ParametresFinances(BaseModel):
    """Réglages financiers de l'établissement : pénalités de retard sur les échéances, blocage des bulletins
    des élèves non à jour, remise fratrie."""
    etablissement = models.OneToOneField('etablissements.Etablissement', on_delete=models.CASCADE,
                                         related_name='parametres_finances', verbose_name=_("Établissement"))
    penalite_mode = models.CharField(max_length=10, choices=ModePenalite.choices, default=ModePenalite.AUCUNE,
                                     verbose_name=_("Pénalité de retard"))
    penalite_valeur = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                          verbose_name=_("Valeur (FCFA ou %)"))
    penalite_delai_jours = models.PositiveSmallIntegerField(default=7, verbose_name=_("Délai de grâce (jours)"),
                                                            help_text=_("Jours après l'échéance avant pénalité"))
    penalite_rubrique = models.ForeignKey('parametres.RubriquePaiement', on_delete=models.SET_NULL, null=True,
                                          blank=True, related_name='+', verbose_name=_("Rubrique d'encaissement"))
    bloquer_bulletins_impayes = models.BooleanField(default=False,
                                                    verbose_name=_("Bloquer les bulletins des élèves non à jour"))
    seuil_blocage_pct = models.PositiveSmallIntegerField(default=100,
                                                         verbose_name=_("Part du dû à régler pour consulter (%)"))
    remise_fratrie = models.ForeignKey('finances.TypeBourse', on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='+', verbose_name=_("Remise fratrie (type de bourse)"))
    remise_fratrie_a_partir = models.PositiveSmallIntegerField(default=2,
                                                               verbose_name=_("Appliquée à partir du n-ième enfant"))

    class Meta:
        verbose_name = _("Paramètres financiers")
        verbose_name_plural = _("Paramètres financiers")

    def __str__(self):
        return f"Paramètres financiers — {self.etablissement}"

    @classmethod
    def pour(cls, etablissement):
        return cls.objects.get_or_create(etablissement=etablissement)[0]


class ClotureCaisse(BaseModel):
    """Arrêté de caisse d'un caissier pour une journée : totaux par mode figés, espèces comptées, écart.
    Après l'arrêté, le caissier ne peut plus saisir d'opération datée de ce jour ou d'un jour antérieur."""
    etablissement = models.ForeignKey('etablissements.Etablissement', on_delete=models.CASCADE,
                                      related_name='clotures_caisse', verbose_name=_("Établissement"))
    date = models.DateField(verbose_name=_("Journée"))
    caissier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='clotures_caisse',
                                 verbose_name=_("Caissier"))
    nb_operations = models.PositiveIntegerField(default=0, verbose_name=_("Opérations"))
    total_especes = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_("Espèces"))
    total_mobile_money = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_("Mobile Money"))
    total_cheque = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_("Chèques"))
    total_virement = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_("Virements"))
    total_rembourse = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                          verbose_name=_("Remboursements (espèces)"))
    montant_compte = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Espèces comptées"))
    ecart = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_("Écart"))
    observation = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Observation"))
    cloture_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='+', verbose_name=_("Arrêté par"))

    class Meta:
        verbose_name = _("Arrêté de caisse")
        verbose_name_plural = _("Arrêtés de caisse")
        ordering = ['-date', '-created_at']
        unique_together = ('etablissement', 'date', 'caissier')

    def __str__(self):
        return f"Caisse {self.caissier} — {self.date:%d/%m/%Y}"

    @property
    def total_encaisse(self):
        return self.total_especes + self.total_mobile_money + self.total_cheque + self.total_virement

    @property
    def especes_theoriques(self):
        return self.total_especes - self.total_rembourse
