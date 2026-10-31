"""Types de documents officiels et signataires (mono et cosignataires)."""

from typing import Optional
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel

from .etablissement import Cycle
from .annee import AnneeScolaire


class TypeDocument(BaseModel):
    """
    Types de documents pouvant porter une signature.

    10 types prédéfinis (fixtures) :
    - CERT_SCOL        : Certificat de Scolarité
    - BULLETIN         : Bulletin de Notes
    - RECU_PAIEMENT    : Reçu de Paiement
    - AUTORISATION     : Autorisation d'Absence
    - ATTESTATION      : Attestation de Non-Redevabilité
    - CURSUS           : Cursus Scolaire Complet
    - CARTE_ID         : Carte d'Identité Scolaire
    - LISTE_CLASSE     : Liste Alphabétique de Classe
    - LISTE_PERSONNEL  : Liste du Personnel
    - LISTE_REDEVABLES : Liste des Redevables
    """

    class CategorieChoices(models.TextChoices):
        SCOLARITE = 'SCOLARITE', _('Scolarité')
        FINANCE = 'FINANCE', _('Finance')
        ADMINISTRATIF = 'ADMINISTRATIF', _('Administratif')
        PEDAGOGIE = 'PEDAGOGIE', _('Pédagogie')
        PERSONNEL = 'PERSONNEL', _('Personnel')

    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Code"),
        help_text=_("Ex: CERT_SCOL, BULLETIN, RECU_PAIEMENT")
    )

    libelle = models.CharField(
        max_length=100,
        verbose_name=_("Libellé"),
        help_text=_("Ex: Certificat de Scolarité")
    )

    categorie = models.CharField(
        max_length=20,
        choices=CategorieChoices.choices,
        default=CategorieChoices.SCOLARITE,
        verbose_name=_("Catégorie")
    )

    cycle = models.ForeignKey(
        'parametres.Cycle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Cycle"),
        help_text=_("Laisser vide pour applies à tous les cycles")
    )

    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Type actif")
    )

    class Meta:
        verbose_name = _("Type de Document")
        verbose_name_plural = _("Types de Documents")
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} ({self.code})"


class SignataireDocumentManager(models.Manager):
    """Manager pour les signataires."""

    def get_signataire(
        self,
        cycle,
        type_document,
        annee_scolaire
    ) -> Optional['SignataireDocument']:
        """
        Récupère le signataire pour un cycle × document × année.

        Stratégie de recherche avec repli progressif :
        1. Correspondance exacte (cycle + document + année)
        2. Repli : même cycle + même document, n'importe quelle année → prend le plus récent
        3. Repli : même document, n'importe quel cycle/année → prend le plus récent
        4. Repli : même catégorie de document (même cycle, puis tout cycle) — un type ajouté au
           catalogue hérite du signataire de sa catégorie tant qu'il n'est pas configuré lui-même
        5. Repli : même cycle, tout document ; 6. tout signataire actif.
        À chaque étape, un signataire dont le membre du personnel a été supprimé est ignoré.

        Args:
            cycle: Instance de Cycle
            type_document: Instance de TypeDocument
            annee_scolaire: Instance d'AnneeScolaire

        Returns:
            SignataireDocument ou None si non trouvé
        """
        if type_document is not None:
            # 1. Correspondance exacte
            sig = self._premier_valide(self.filter(
                cycle=cycle,
                type_document=type_document,
                annee_scolaire=annee_scolaire,
            ))
            if sig:
                return sig

            # 2. Même cycle + même document, toute année
            if cycle is not None:
                sig = self._premier_valide(self.filter(cycle=cycle, type_document=type_document))
                if sig:
                    return sig

            # 3. Même document, tout cycle
            sig = self._premier_valide(self.filter(type_document=type_document))
            if sig:
                return sig

            # 4. Même catégorie de document : même cycle d'abord, puis tout cycle
            for portee in ({'cycle': cycle}, {}) if cycle is not None else ({},):
                sig = self._premier_valide(self.filter(
                    type_document__categorie=type_document.categorie,
                    **portee,
                ))
                if sig:
                    return sig

        # 5. Même cycle, tout document
        if cycle is not None:
            sig = self._premier_valide(self.filter(cycle=cycle))
            if sig:
                return sig

        # 6. Tout signataire actif (dernier recours absolu)
        return self._premier_valide(self.all())

    @staticmethod
    def _premier_valide(candidats):
        """Signataire actif le plus récent de la file dont le membre du personnel existe encore.

        Un signataire pointant vers un membre supprimé est ignoré : le document se replie sur le
        candidat suivant au lieu de rester sans signature.
        """
        for sig in candidats.filter(actif=True).order_by('-updated_at'):
            if sig.get_membre_personnel() is not None:
                return sig
        return None


class SignataireDocument(BaseModel):
    """
    Signataires paramétrables par Cycle × Type Document × Année.

    Permet de configurer qui signe quel document pour chaque cycle.
    Ex: Le Directeur du Primaire signe les bulletins du Primaire,
        Le Proviseur du Secondaire signe les bulletins du Secondaire.

    Contrainte unique : Un seul signataire actif par (cycle, document, année).
    """

    cycle = models.ForeignKey(
        Cycle,
        on_delete=models.CASCADE,
        related_name='signataires',
        verbose_name=_("Cycle")
    )

    type_document = models.ForeignKey(
        TypeDocument,
        on_delete=models.CASCADE,
        related_name='signataires',
        verbose_name=_("Type de Document")
    )

    # FK vers le module personnel (sera migré après personnel)
    # Temporairement en CharField
    membre_personnel_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("ID Membre du Personnel Signataire")
    )

    @property
    def membre_personnel(self):
        """Retourne le membre du personnel (après migration FK)."""
        if hasattr(self, '_membre_personnel_cache'):
            return self._membre_personnel_cache
        return None

    def get_membre_personnel(self):
        """Récupère le membre du personnel depuis la base."""
        from personnel.models import MembrePersonnel
        if self.membre_personnel_id:
            try:
                return MembrePersonnel.objects.get(id=self.membre_personnel_id)
            except MembrePersonnel.DoesNotExist:
                return None
        return None

    def set_membre_personnel(self, personnel):
        """Définit le membre du personnel."""
        self.membre_personnel_id = personnel.id if personnel else None
        self._membre_personnel_cache = personnel

    titre = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Titre / Fonction (ancien)"),
        help_text=_("Champ hérité — utiliser 'fonction' à la place")
    )

    titre_honorifique = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_("Titre Honorifique (ancien)"),
        help_text=_("Champ hérité — utiliser 'titres_honorifiques' à la place")
    )

    fonction = models.CharField(
        max_length=150,
        blank=True,
        default='Le Directeur',
        verbose_name=_("Fonction"),
        help_text=_("Fonction affichée entre la date et le nom, "
                    "ex: 'Directeur des Études', 'Le Proviseur', 'La Directrice'")
    )

    titres_honorifiques = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Titres Honorifiques"),
        help_text=_("Liste ordonnée de titres honorifiques affichés sous le nom, "
                    "ex: [\"Chevalier de l'Ordre du Mérite\", "
                    "\"Chevalier des Palmes Académiques\"]")
    )

    annee_scolaire = models.ForeignKey(
        AnneeScolaire,
        on_delete=models.CASCADE,
        related_name='signataires_documents',
        verbose_name=_("Année Scolaire")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Signataire actif")
    )

    # Manager personnalisé
    objects = SignataireDocumentManager()

    class Meta:
        verbose_name = _("Signataire de Document")
        verbose_name_plural = _("Signataires de Documents")
        ordering = ['cycle', 'type_document']
        unique_together = [['cycle', 'type_document', 'annee_scolaire']]

    def __str__(self):
        personnel = self.get_membre_personnel()
        personnel_str = str(personnel) if personnel else "Aucun"
        return (
            f"{self.cycle.nom} - {self.type_document.libelle} - "
            f"{personnel_str}"
        )

    def get_nom_complet_avec_titre(self) -> str:
        """
        Retourne le nom complet du signataire avec titre.

        Returns:
            str: "M. le Directeur Jean OUÉDRAOGO"
        """
        personnel = self.get_membre_personnel()
        if not personnel:
            return self.titre_honorifique or ""

        if self.titre_honorifique:
            return f"{self.titre_honorifique} {personnel.get_nom_complet()}"
        return personnel.get_nom_complet()


class CoSignataire(BaseModel):
    """
    Signataire(s) supplémentaire(s) pour un document.

    Lié au SignataireDocument principal (le 1er signataire).
    Permet d'avoir, ex. : Directeur (principal) + Censeur (co).

    Le rendu PDF aligne tous les signataires côte à côte.
    """

    signataire_principal = models.ForeignKey(
        SignataireDocument,
        on_delete=models.CASCADE,
        related_name='co_signataires',
        verbose_name=_("Signataire principal")
    )

    membre_personnel_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name=_("ID Membre du Personnel")
    )

    fonction = models.CharField(
        max_length=150,
        default='',
        blank=True,
        verbose_name=_("Fonction"),
        help_text=_("Ex : 'Le Censeur', 'La Directrice des Études'")
    )

    titres_honorifiques = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Titres honorifiques")
    )

    ordre = models.PositiveSmallIntegerField(
        default=2,
        verbose_name=_("Ordre d'affichage"),
        help_text=_("1 = premier à gauche ; le signataire principal est toujours en position 1")
    )

    actif = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Co-Signataire")
        verbose_name_plural = _("Co-Signataires")
        ordering = ['ordre']

    def __str__(self):
        m = self.get_membre_personnel()
        nom = str(m) if m else "—"
        return f"{self.fonction or 'Co-signataire'} : {nom}"

    def get_membre_personnel(self):
        """Récupère le membre du personnel depuis la base."""
        from personnel.models import MembrePersonnel
        if self.membre_personnel_id:
            try:
                return MembrePersonnel.objects.get(id=self.membre_personnel_id)
            except MembrePersonnel.DoesNotExist:
                return None
        return None
