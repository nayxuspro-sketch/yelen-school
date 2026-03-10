"""
Modèles pour l'application Etablissements.
Géré par: YELEN SCHOOL
"""

from django.db import models

from django.utils.translation import gettext_lazy as _

from core.models import BaseModel, CycleChoices


class Etablissement(BaseModel):
    """
    Entité représentant un établissement scolaire (école, collège, lycée).
    Peut proposer un ou plusieurs cycles d'enseignement.
    """
    nom = models.CharField(
        max_length=255,
        verbose_name=_("Nom de l'établissement")
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Code de l'établissement"),
        help_text=_("Code unique d'identification, ex: YSK")
    )
    adresse = models.TextField(
        blank=True,
        verbose_name=_("Adresse géographique")
    )
    telephone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Téléphone principal")
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_("Adresse email")
    )
    logo = models.ImageField(
        upload_to='etablissements/logos/',
        blank=True,
        null=True,
        verbose_name=_("Logo de l'établissement")
    )
    cycles = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_("Cycles proposés"),
        help_text=_("Cycles séparés par des virgules : PRIMAIRE,SECONDAIRE")
    )
    ville = models.CharField(
        max_length=100,
        verbose_name=_("Ville")
    )
    pays = models.CharField(
        max_length=100,
        default='Burkina Faso',
        verbose_name=_("Pays")
    )

    class Meta:
        verbose_name = _('Établissement')
        verbose_name_plural = _('Établissements')
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.code})"
