"""Champs de modèle partagés."""
from django.db import models


class URLFieldHTTPS(models.URLField):
    """
    URLField dont le champ de formulaire complète « https:// » quand le schéma
    est omis (« ecole.bf » → « https://ecole.bf »).

    C'est le comportement par défaut de Django 6.0 ; l'expliciter ici supprime
    le RemovedInDjango60Warning émis par Django 5.x à chaque construction de
    formulaire, sans recourir au réglage transitoire FORMS_URLFIELD_ASSUME_HTTPS
    (lui-même déprécié).
    """

    def formfield(self, **kwargs):
        kwargs.setdefault('assume_scheme', 'https')
        return super().formfield(**kwargs)

    def deconstruct(self):
        # Colonne strictement identique à models.URLField : aucune migration.
        name, _path, args, kwargs = super().deconstruct()
        return name, 'django.db.models.URLField', args, kwargs
