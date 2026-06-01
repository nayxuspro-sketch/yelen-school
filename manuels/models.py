from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel, CycleChoices


class EtatManuel(models.TextChoices):
    NEUF       = 'NEUF',       'Neuf'
    BON        = 'BON',        'Bon état'
    USAGE      = 'USAGE',      'Usagé'
    DETERIORE  = 'DETERIORE',  'Détérioré'


# ── Catalogue ──────────────────────────────────────────────────────────────

class ManuelScolaire(BaseModel):
    """Titre référencé dans le catalogue de l'établissement."""

    etablissement = models.ForeignKey(
        'etablissements.Etablissement',
        on_delete=models.CASCADE,
        related_name='manuels',
    )
    titre = models.CharField(max_length=200, verbose_name=_("Titre"))
    auteur = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Auteur"))
    editeur = models.CharField(max_length=200, blank=True, default='', verbose_name=_("Éditeur"))
    isbn = models.CharField(max_length=20, blank=True, default='', verbose_name=_("ISBN"))
    cycle = models.CharField(
        max_length=20,
        choices=CycleChoices.choices,
        verbose_name=_("Cycle"),
    )
    classe = models.ForeignKey(
        'parametres.Classe',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manuels',
        verbose_name=_("Classe (facultatif)"),
    )
    matiere = models.ForeignKey(
        'pedagogie.Matiere',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manuels',
        verbose_name=_("Matière"),
    )
    annee_edition = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name=_("Année d'édition"),
    )
    prix_remplacement = models.DecimalField(
        max_digits=10, decimal_places=0,
        default=Decimal('0'),
        verbose_name=_("Prix de remplacement (FCFA)"),
        help_text=_("Facturé à l'élève si le manuel n'est pas rendu."),
    )
    actif = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Manuel scolaire")
        verbose_name_plural = _("Manuels scolaires")
        ordering = ['cycle', 'titre']

    def __str__(self):
        return self.titre

    @property
    def nb_exemplaires(self):
        return self.exemplaires.filter(actif=True).count()

    @property
    def nb_attribues(self):
        # Sous-requête explicite pour éviter le LEFT JOIN ambigu de Django
        # (attributions__date_retour__isnull=True matcherait aussi les
        #  exemplaires sans aucune attribution via NULL IS NULL)
        ids_attribues = AttributionManuel.objects.filter(
            exemplaire__manuel=self,
            exemplaire__actif=True,
            date_retour__isnull=True,
        ).values_list('exemplaire_id', flat=True).distinct()
        return ids_attribues.count()

    @property
    def nb_disponibles(self):
        return self.nb_exemplaires - self.nb_attribues


# ── Exemplaires ────────────────────────────────────────────────────────────

class ExemplaireManuel(BaseModel):
    """Exemplaire physique d'un manuel, identifié par un code unique."""

    manuel = models.ForeignKey(
        ManuelScolaire,
        on_delete=models.CASCADE,
        related_name='exemplaires',
    )
    # Auto-généré : EX-YYYY-NNNNN
    code_exemplaire = models.CharField(
        max_length=15,
        unique=True,
        verbose_name=_("Code exemplaire"),
    )
    etat = models.CharField(
        max_length=10,
        choices=EtatManuel.choices,
        default=EtatManuel.NEUF,
        verbose_name=_("État"),
    )
    annee_acquisition = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name=_("Année d'acquisition"),
    )
    actif = models.BooleanField(default=True, verbose_name=_("Actif"))

    class Meta:
        verbose_name = _("Exemplaire")
        verbose_name_plural = _("Exemplaires")
        ordering = ['code_exemplaire']

    def __str__(self):
        return f"{self.code_exemplaire} — {self.manuel.titre}"

    def save(self, *args, **kwargs):
        if not self.code_exemplaire:
            self.code_exemplaire = self._generer_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generer_code():
        from datetime import date
        annee = date.today().year
        dernier = (
            ExemplaireManuel.objects
            .filter(code_exemplaire__startswith=f'EX-{annee}-')
            .order_by('code_exemplaire')
            .last()
        )
        if dernier:
            seq = int(dernier.code_exemplaire.split('-')[-1]) + 1
        else:
            seq = 1
        return f'EX-{annee}-{seq:05d}'

    @property
    def est_disponible(self):
        return not self.attributions.filter(date_retour__isnull=True).exists()

    @property
    def attribution_courante(self):
        return self.attributions.filter(date_retour__isnull=True).first()


# ── Attributions ───────────────────────────────────────────────────────────

class AttributionManuel(BaseModel):
    """Attribution nominative d'un exemplaire à un élève (via son inscription)."""

    exemplaire = models.ForeignKey(
        ExemplaireManuel,
        on_delete=models.CASCADE,
        related_name='attributions',
    )
    inscription = models.ForeignKey(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='attributions_manuels',
    )
    date_attribution = models.DateField(verbose_name=_("Date d'attribution"))
    etat_sortie = models.CharField(
        max_length=10,
        choices=EtatManuel.choices,
        default=EtatManuel.BON,
        verbose_name=_("État à la sortie"),
    )
    date_retour = models.DateField(
        null=True, blank=True,
        verbose_name=_("Date de retour"),
    )
    etat_retour = models.CharField(
        max_length=10,
        choices=EtatManuel.choices,
        blank=True,
        default='',
        verbose_name=_("État au retour"),
    )
    facture_genere = models.BooleanField(
        default=False,
        verbose_name=_("Frais facturés"),
        help_text=_("Vrai si la pénalité de non-retour a été ajoutée aux frais de l'élève."),
    )
    observation = models.TextField(blank=True, default='', verbose_name=_("Observation"))

    class Meta:
        verbose_name = _("Attribution de manuel")
        verbose_name_plural = _("Attributions de manuels")
        ordering = ['-date_attribution']

    def __str__(self):
        return (
            f"{self.exemplaire.code_exemplaire} → "
            f"{self.inscription.eleve.nom} {self.inscription.eleve.prenom}"
        )

    @property
    def est_rendu(self):
        return self.date_retour is not None
