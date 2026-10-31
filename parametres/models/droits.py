"""Rôles personnalisés, droits d'accès et politique de données personnelles."""

from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel


class RolePersonnalise(BaseModel):
    """Rôle créé par le Super Admin (voir ``parametres.droits``).

    ``base`` est le rôle intégré de référence : il fixe le comportement métier
    (tableau de bord, périmètre d'un enseignant…) et sert de valeur initiale aux
    droits d'accès ; la matrice règle ensuite les droits du rôle lui-même.
    Un utilisateur de ce rôle porte ``role = base`` et ``role_personnalise = ce rôle``.
    """

    code = models.CharField(max_length=30, unique=True, verbose_name=_("Code"))
    libelle = models.CharField(max_length=60, unique=True, verbose_name=_("Libellé"))
    base = models.CharField(max_length=20, verbose_name=_("Rôle de référence"))

    class Meta:
        verbose_name = _("Rôle personnalisé")
        verbose_name_plural = _("Rôles personnalisés")
        ordering = ['libelle']

    def __str__(self):
        return self.libelle

    @property
    def base_libelle(self):
        from core.models import RoleChoices
        return RoleChoices(self.base).label


class DroitAcces(BaseModel):
    """Accès d'un rôle du personnel à un module (voir ``parametres.droits``).

    Matrice gérée par le Super Admin ; un couple (rôle, module) absent prend la
    valeur par défaut définie dans ``parametres.droits.DEFAUTS``.
    """

    role = models.CharField(max_length=30, verbose_name=_("Rôle"))
    module = models.CharField(max_length=30, verbose_name=_("Module"))
    fonctionnalite = models.CharField(
        max_length=60, blank=True, default='', verbose_name=_("Fonctionnalité"),
        help_text=_("Préfixe d'URL de l'entrée de menu ; vide = droit sur le module entier."),
    )
    action = models.CharField(
        max_length=40, blank=True, default='', verbose_name=_("Action"),
        help_text=_("Sous-fonctionnalité (saisie, validation…) ; vide = la fonctionnalité elle-même."),
    )
    autorise = models.BooleanField(default=True, verbose_name=_("Accès autorisé"))

    class Meta:
        verbose_name = _("Droit d'accès")
        verbose_name_plural = _("Droits d'accès")
        unique_together = [('role', 'module', 'fonctionnalite', 'action')]
        ordering = ['role', 'module', 'fonctionnalite', 'action']

    def __str__(self):
        cible = f"{self.module} {self.fonctionnalite} {self.action}".strip()
        return f"{self.role} → {cible} : {'autorisé' if self.autorise else 'refusé'}"


class PolitiqueDonnees(BaseModel):
    """Cycle de vie des données personnelles (loi n° 001-2021/AN) : durée de conservation après la dernière
    inscription, responsable du traitement, dernière anonymisation."""
    etablissement = models.OneToOneField(
        'etablissements.Etablissement', on_delete=models.CASCADE, related_name='politique_donnees',
        verbose_name=_("Établissement"),
    )
    duree_conservation_annees = models.PositiveSmallIntegerField(
        default=10, verbose_name=_("Durée de conservation (années)"),
        help_text=_("Après la fin de la dernière année scolaire d'inscription, les données de l'élève et de ses parents sont anonymisées"),
    )
    responsable_traitement = models.CharField(max_length=150, blank=True, default='', verbose_name=_("Responsable du traitement"))
    contact_responsable = models.CharField(max_length=150, blank=True, default='', verbose_name=_("Contact du responsable"))
    derniere_anonymisation = models.DateTimeField(null=True, blank=True, verbose_name=_("Dernière anonymisation"))

    class Meta:
        verbose_name = _("Politique de données personnelles")
        verbose_name_plural = _("Politiques de données personnelles")

    def __str__(self):
        return f"Conservation {self.duree_conservation_annees} ans — {self.etablissement}"
