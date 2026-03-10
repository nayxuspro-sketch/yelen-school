"""
etablissements/models.py — Gestion des établissements scolaires

Stub minimal pour débloquer la FK dans accounts.User.
Sera enrichi dans la phase dédiée aux établissements.

Référence : docs/PROMPT_V3_3.md §2.1
"""

from django.db import models

from core.models import BaseModel


class Etablissement(BaseModel):
    """Établissement scolaire — stub minimal.

    Ce modèle sera enrichi ultérieurement avec :
    - type_etablissement (public/privé/confessionnel)
    - numéro agrément MENA
    - adresse, ville, province, région
    - lien vers IdentiteEtablissement (parametres)
    """

    nom = models.CharField(
        max_length=255,
        verbose_name="Nom de l'établissement",
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Code établissement',
        help_text='Code court unique (ex: YSK, LPO, etc.)',
    )

    class Meta:
        verbose_name = 'Établissement'
        verbose_name_plural = 'Établissements'
        ordering = ['nom']

    def __str__(self) -> str:
        return self.nom
