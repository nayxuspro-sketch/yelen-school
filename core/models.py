"""
core/models.py — Fondation YELEN SCHOOL

Ce module contient :
- BaseModel        : Classe abstraite héritée par TOUS les modèles du projet
- CycleChoices     : Les 4 cycles scolaires du Burkina Faso (MENA)
- RoleChoices      : Les 9 rôles RBAC du système

Référence : docs/PROMPT_V3_3.md §2.1, §2.2, §4.2
"""

import uuid

from django.db import models


# ──────────────────────────────────────────────
# Choix constants — réutilisables par toutes les apps
# ──────────────────────────────────────────────

class CycleChoices(models.TextChoices):
    """Cycles scolaires officiels du Burkina Faso (MENA).

    - Préscolaire  : Crèche, PS, MS, GS
    - Primaire     : CP1, CP2, CE1, CE2, CM1, CM2 — examen CEP
    - Post-primaire: 6ème, 5ème, 4ème, 3ème — examen BEPC
    - Secondaire   : 2nde, 1ère, Terminale (A/B/C/D) — examen BAC
    """
    PRESCOLAIRE   = 'PRESCOLAIRE',   'Préscolaire'
    PRIMAIRE      = 'PRIMAIRE',      'Primaire'
    POST_PRIMAIRE = 'POST_PRIMAIRE', 'Post-primaire'
    SECONDAIRE    = 'SECONDAIRE',    'Secondaire'


class RoleChoices(models.TextChoices):
    """Rôles RBAC du système YELEN SCHOOL.

    Aligné sur PROMPT_V3_3.md §2.2.
    Note : Directeur = Directeur / Proviseur (jamais Directeur/SG).
    """
    SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin Éditeur'
    DIRECTEUR   = 'DIRECTEUR',   'Directeur / Proviseur'
    CENSEUR     = 'CENSEUR',     'Censeur / Proviseur'
    AVS         = 'AVS',         'Agent de Vie Scolaire'
    ENSEIGNANT  = 'ENSEIGNANT',  'Enseignant'
    COMPTABLE   = 'COMPTABLE',   'Comptable'
    SECRETAIRE  = 'SECRETAIRE',  'Secrétaire'
    PARENT      = 'PARENT',      'Parent'
    ELEVE       = 'ELEVE',       'Élève'


# ──────────────────────────────────────────────
# Modèle de base abstrait
# ──────────────────────────────────────────────

class BaseModel(models.Model):
    """Classe abstraite héritée par TOUS les modèles YELEN SCHOOL.

    Fournit :
    - id         : UUID comme clé primaire (pas d'AutoField int)
    - created_at : Date de création (auto)
    - updated_at : Date de dernière modification (auto)
    - is_active  : Soft-delete / filtre d'activité
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='Identifiant',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Dernière modification',
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Décocher pour désactiver sans supprimer.',
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']
