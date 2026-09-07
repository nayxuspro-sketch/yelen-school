from django.db import migrations, models

from ._compat import cycles_field_historique


def csv_cycles_to_list(apps, schema_editor):
    """Convertit les cycles CSV ('PRIMAIRE,SECONDAIRE') en liste Python (['PRIMAIRE', 'SECONDAIRE'])."""
    Etablissement = apps.get_model('etablissements', 'Etablissement')
    for etab in Etablissement.objects.all():
        if etab.cycles and isinstance(etab.cycles, str):
            etab.cycles = [c.strip() for c in etab.cycles.split(',') if c.strip()]
            etab.save(update_fields=['cycles'])


def list_cycles_to_csv(apps, schema_editor):
    """Rollback : reconvertit les listes en CSV."""
    Etablissement = apps.get_model('etablissements', 'Etablissement')
    for etab in Etablissement.objects.all():
        if etab.cycles and isinstance(etab.cycles, list):
            etab.cycles = ','.join(etab.cycles)
            etab.save(update_fields=['cycles'])


class Migration(migrations.Migration):

    dependencies = [
        ('etablissements', '0001_initial'),
    ]

    operations = [
        # 1. Renommer l'ancienne colonne en temporaire
        migrations.RenameField(
            model_name='etablissement',
            old_name='cycles',
            new_name='cycles_old',
        ),
        # 2. Ajouter la nouvelle colonne ArrayField (nullable pour l'instant)
        migrations.AddField(
            model_name='etablissement',
            name='cycles',
            # ArrayField sur PostgreSQL / JSONField ailleurs (voir _compat.py)
            field=cycles_field_historique(),
        ),
        # 3. Migration des données CSV → list
        migrations.RunPython(csv_cycles_to_list, list_cycles_to_csv),
        # 4. Supprimer l'ancienne colonne CSV
        migrations.RemoveField(
            model_name='etablissement',
            name='cycles_old',
        ),
    ]
