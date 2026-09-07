"""
Compatibilité multi-SGBD pour les migrations historiques de `etablissements`.

Historique : les migrations 0002 et 0003 ont introduit `Etablissement.cycles`
en tant qu'ArrayField (PostgreSQL uniquement). Depuis la migration 0005, ce champ
est un JSONField portable (PostgreSQL + SQLite).

Pour que l'historique de migrations reste rejouable sur SQLite (nouvelle
installation autonome) SANS changer ce qui a déjà été appliqué sur les bases
PostgreSQL existantes, `cycles_field_historique()` renvoie :
  - l'ArrayField d'origine   si le backend est PostgreSQL ;
  - un JSONField équivalent  sinon.

Sur PostgreSQL, la migration 0005 convertit ensuite réellement la colonne
varchar[] -> jsonb. Sur SQLite, la colonne est déjà du JSON : 0005 est un no-op.
"""
from django.db import connection, models

CYCLE_CHOICES = [
    ('PRESCOLAIRE', 'Préscolaire'),
    ('PRIMAIRE', 'Primaire'),
    ('POST_PRIMAIRE', 'Post-primaire'),
    ('SECONDAIRE', 'Secondaire'),
]


def is_postgresql():
    return connection.vendor == 'postgresql'


def cycles_field_historique():
    """Champ `cycles` tel qu'il existait entre les migrations 0002 et 0004."""
    if is_postgresql():
        from django.contrib.postgres.fields import ArrayField
        return ArrayField(
            base_field=models.CharField(choices=CYCLE_CHOICES, max_length=20),
            blank=True,
            default=list,
            size=None,
            verbose_name='Cycles proposés',
        )
    return models.JSONField(blank=True, default=list, verbose_name='Cycles proposés')
