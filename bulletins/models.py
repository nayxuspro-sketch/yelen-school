"""
bulletins/models.py — Gestion de la publication des bulletins
=============================================================
YELEN SCHOOL v3.4

Ce module gère :
- Bulletin              : Publication des bulletins trimestriels
- BulletinAnnuel       : Snapshot calculé du bulletin annuel de notes
"""

import uuid as _uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel


class Bulletin(BaseModel):
    """
    Fiche de publication d'un bulletin trimestriel.

    Un bulletin est créé (ou récupéré) pour chaque élève × trimestre.
    Il complète les données pédagogiques de MoyenneGenerale (pedagogie)
    avec les informations administratives : absences, retards,
    appréciation du conseil de classe et statut de publication.
    """

    inscription = models.ForeignKey(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='bulletins',
        verbose_name=_("Inscription"),
    )
    trimestre = models.ForeignKey(
        'pedagogie.Trimestre',
        on_delete=models.CASCADE,
        related_name='bulletins',
        verbose_name=_("Trimestre"),
    )

    # ── Absences & retards ─────────────────────────────────────────────
    absences_justifiees = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Absences justifiées (heures)"),
    )
    absences_non_justifiees = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Absences non justifiées (heures)"),
    )
    retards = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Retards"),
    )

    # ── Appréciation du conseil de classe ─────────────────────────────
    appreciation_conseil = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Appréciation du conseil de classe"),
        help_text=_("Observation saisie lors du conseil de classe"),
    )

    # ── Publication ───────────────────────────────────────────────────
    est_publie = models.BooleanField(
        default=False,
        verbose_name=_("Publié"),
        help_text=_("Un bulletin publié est visible par les parents / élèves"),
    )
    date_publication = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de publication"),
    )
    publie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulletins_publies',
        verbose_name=_("Publié par"),
    )

    # ── Signature électronique parentale ──────────────────────────────
    token_signature = models.CharField(
        max_length=64, unique=True, null=True, blank=True,
        verbose_name=_("Token de signature"),
    )
    token_expire_le = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Token valide jusqu'au"),
    )
    signe_le = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Signé le"),
    )
    signe_par_nom = models.CharField(
        max_length=100, blank=True,
        verbose_name=_("Signé par"),
    )

    class Meta:
        verbose_name = _("Bulletin")
        verbose_name_plural = _("Bulletins")
        ordering = ['trimestre__numero', 'inscription__eleve__nom', 'inscription__eleve__prenom']
        unique_together = [['inscription', 'trimestre']]

    def __str__(self):
        return (
            f"Bulletin {self.inscription.eleve} — "
            f"{self.trimestre.nom} {self.trimestre.annee_scolaire.libelle}"
        )

    @property
    def total_absences(self):
        return self.absences_justifiees + self.absences_non_justifiees

    def a_moyenne_calculee(self):
        """Retourne True si une MoyenneGenerale existe pour ce bulletin."""
        from pedagogie.models import MoyenneGenerale
        return MoyenneGenerale.objects.filter(
            inscription=self.inscription,
            trimestre=self.trimestre,
        ).exists()

    def publier(self, user):
        """Marque le bulletin comme publié. Lève ValueError si la moyenne n'est pas calculée."""
        if not self.a_moyenne_calculee():
            raise ValueError("Impossible de publier un bulletin sans moyenne calculée.")
        self.est_publie = True
        self.date_publication = timezone.now()
        self.publie_par = user
        if not self.token_signature:
            self.token_signature = _uuid.uuid4().hex
        self.token_expire_le = timezone.now() + timezone.timedelta(days=15)
        self.save(update_fields=[
            'est_publie', 'date_publication', 'publie_par',
            'token_signature', 'token_expire_le', 'updated_at',
        ])

    def depublier(self):
        """Retire la publication du bulletin."""
        self.est_publie = False
        self.date_publication = None
        self.publie_par = None
        self.save(update_fields=['est_publie', 'date_publication', 'publie_par', 'updated_at'])

    @property
    def est_signe(self):
        return bool(self.signe_le)

    @property
    def token_valide(self):
        return bool(
            self.token_signature
            and self.token_expire_le
            and timezone.now() <= self.token_expire_le
        )


# ═══════════════════════════════════════════════════════════════════
# BULLETIN ANNUEL DE NOTES
# ═══════════════════════════════════════════════════════════════════

class BulletinAnnuel(BaseModel):
    """
    Snapshot calculé du bulletin annuel d'un élève.
    
    Document distinct des bulletins trimestriels. Contiene la moyenne annuelle
    de passage (= moyenne arithmétique des moyennes de périodes).
    
    Règles de calcul :
    - moyenne_periode  = Σ(note × coefficient) / Σ(coefficient) pour chaque période
    - moyenne_annuelle = Σ(moyenne_periode) / nombre_periodes
    - est_admis        = moyenne_annuelle >= 10.00
    """

    inscription = models.ForeignKey(
        'inscriptions.Inscription',
        on_delete=models.CASCADE,
        related_name='bulletins_annuels',
        verbose_name=_("Inscription"),
    )
    annee_scolaire = models.ForeignKey(
        'parametres.AnneeScolaire',
        on_delete=models.CASCADE,
        related_name='bulletins_annuels',
        verbose_name=_("Année scolaire"),
    )
    
    donnees_json = models.JSONField(
        default=dict,
        verbose_name=_("Données du bulletin"),
        help_text=_("JSON contenant les moyennes par période"),
    )
    
    moyenne_annuelle = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name=_("Moyenne annuelle"),
    )
    
    est_admis = models.BooleanField(
        default=False,
        verbose_name=_("Admis"),
        help_text=_("True si moyenne_annuelle >= 10.00"),
    )
    
    # ── Statistiques de rang ───────────────────────────────────────────────
    rang_annuel = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Rang annuel"),
        help_text=_("Rang de l'élève basé sur la moyenne annuelle"),
    )
    effectif_classe = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Effectif de la classe"),
    )
    moyenne_max_classe = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Plus forte moyenne de la classe"),
    )
    moyenne_min_classe = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Plus faible moyenne de la classe"),
    )
    moyenne_classe = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Moyenne de la classe"),
    )

    # ── Appréciation du conseil de classe ────────────────────────────────
    appreciation_conseil = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Appréciation du conseil de classe"),
    )

    # ── Signature ─────────────────────────────────────────────────────────
    date_signature = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de signature"),
    )
    lieu_signature = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name=_("Lieu de signature"),
    )

    genere_le = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Généré le"),
    )

    class Meta:
        verbose_name = _("Bulletin annuel")
        verbose_name_plural = _("Bulletins annuels")
        ordering = ['inscription__eleve__nom', 'inscription__eleve__prenom']
        unique_together = [['inscription', 'annee_scolaire']]

    def __str__(self):
        return f"Bulletin annuel {self.inscription.eleve} — {self.annee_scolaire.libelle}"

    @property
    def decision(self):
        """Décision de passage : 'Passe en classe supérieure' ou 'Redouble la classe'."""
        return "Passe en classe supérieure" if self.est_admis else "Redouble la classe"

    def calculer_rang(self):
        """Calcule le rang annuel de l'élève parmi les élèves de la même classe."""
        bulletins = BulletinAnnuel.objects.filter(
            inscription__classe=self.inscription.classe,
            annee_scolaire=self.annee_scolaire,
        ).order_by('-moyenne_annuelle')

        for index, bulletin in enumerate(bulletins, start=1):
            if bulletin.pk == self.pk:
                return index
        return None

    @property
    def a_redouble(self):
        """
        Retourne True si l'élève a redoublé cette année scolaire.
        On s'appuie sur le champ 'classe_redoublee' de l'Inscription
        si celui-ci existe, sinon on retourne False.
        """
        return bool(getattr(self.inscription, 'classe_redoublee', False))
