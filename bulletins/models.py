"""
bulletins/models.py — Gestion de la publication des bulletins
=============================================================
YELEN SCHOOL v3.4

Ce module gère le workflow de publication des bulletins trimestriels :
- Saisie des absences / retards par l'AVS ou la secrétaire
- Appréciation du conseil de classe
- Publication / dépublication du bulletin
"""

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
        self.save(update_fields=['est_publie', 'date_publication', 'publie_par', 'updated_at'])

    def depublier(self):
        """Retire la publication du bulletin."""
        self.est_publie = False
        self.date_publication = None
        self.publie_par = None
        self.save(update_fields=['est_publie', 'date_publication', 'publie_par', 'updated_at'])
