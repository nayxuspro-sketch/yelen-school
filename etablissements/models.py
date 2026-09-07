"""
Modèles pour l'application Etablissements.
Géré par: YELEN SCHOOL
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel, CycleChoices


def validate_cycles(value):
    """Valide la liste des cycles (remplace la validation des choices de l'ex-ArrayField).

    Le champ est un JSONField portable (PostgreSQL et SQLite) : on s'assure
    qu'il contient bien une liste de codes appartenant à CycleChoices.
    """
    if value in (None, ''):
        return
    if not isinstance(value, list):
        raise ValidationError(_("Les cycles doivent être fournis sous forme de liste."))
    valides = set(CycleChoices.values)
    invalides = [c for c in value if c not in valides]
    if invalides:
        raise ValidationError(
            _("Cycle(s) invalide(s) : %(cycles)s"),
            params={'cycles': ', '.join(map(str, invalides))},
        )


class GroupeEtablissements(BaseModel):
    """
    Groupe (réseau) regroupant plusieurs établissements sous une même entité.
    Accessible uniquement avec la licence RESEAU.
    """
    nom = models.CharField(
        max_length=255,
        verbose_name=_("Nom du groupe"),
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Code du groupe"),
        help_text=_("Code unique, ex: YELEN-GRP"),
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_("Description"),
    )

    class Meta:
        verbose_name = _("Groupe d'établissements")
        verbose_name_plural = _("Groupes d'établissements")
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.code})"

    @property
    def nb_etablissements(self):
        return self.etablissements.count()


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
    # JSONField (liste de codes CycleChoices) — portable PostgreSQL / SQLite.
    # Remplace l'ancien ArrayField (PostgreSQL uniquement) ; même usage côté code :
    # une liste Python, ex. ['PRIMAIRE', 'SECONDAIRE'].
    cycles = models.JSONField(
        blank=True,
        default=list,
        validators=[validate_cycles],
        verbose_name=_("Cycles proposés"),
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
    groupe = models.ForeignKey(
        GroupeEtablissements,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='etablissements',
        verbose_name=_("Groupe / Réseau"),
        help_text=_("Groupe d'établissements auquel appartient cet établissement (Licence RESEAU)"),
    )

    class Meta:
        verbose_name = _('Établissement')
        verbose_name_plural = _('Établissements')
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.code})"
