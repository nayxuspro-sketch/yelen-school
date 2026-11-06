# Nettoyage des doublons de co-signataires + contrainte d'unicité.
from django.db import migrations, models


def supprimer_doublons_cosignataire(apps, schema_editor):
    """Garde un seul co-signataire actif par (signataire_principal, membre)."""
    db_alias = schema_editor.connection.alias
    # Garder le plus ancien (MIN id) par groupe, supprimer les doublons actifs.
    schema_editor.execute(
        """
        DELETE FROM parametres_cosignataire
        WHERE actif = 1
          AND membre_personnel_id IS NOT NULL
          AND id NOT IN (
              SELECT MIN(id)
              FROM parametres_cosignataire
              WHERE actif = 1
                AND membre_personnel_id IS NOT NULL
              GROUP BY signataire_principal_id, membre_personnel_id
          )
        """,
        using=db_alias,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0047_pointage_evaluation_personnel'),
    ]

    operations = [
        migrations.RunPython(
            supprimer_doublons_cosignataire,
            migrations.RunPython.noop,
        ),
        migrations.UniqueConstraint(
            fields=['signataire_principal', 'membre_personnel_id'],
            condition=models.Q(actif=True),
            name='unique_cosignataire_actif_par_membre',
        ),
    ]
