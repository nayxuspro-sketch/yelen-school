from django.db import migrations, models


def purger_ancien_defaut(apps, schema_editor):
    """L'ancien « Pays de résidence » valait « Burkina Faso » par défaut : ce n'est pas un lieu de résidence."""
    Eleve = apps.get_model('inscriptions', 'Eleve')
    Eleve.objects.filter(lieu_residence__iexact='Burkina Faso').update(lieu_residence='')


class Migration(migrations.Migration):

    dependencies = [
        ('inscriptions', '0014_alter_eleve_matricule'),
    ]

    operations = [
        migrations.RenameField(model_name='eleve', old_name='pays_residence', new_name='lieu_residence'),
        migrations.AlterField(
            model_name='eleve',
            name='lieu_residence',
            field=models.CharField(blank=True, default='', max_length=150,
                                   verbose_name='Lieu de résidence (Village/Quartier/Secteur)'),
        ),
        migrations.RunPython(purger_ancien_defaut, migrations.RunPython.noop),
    ]
