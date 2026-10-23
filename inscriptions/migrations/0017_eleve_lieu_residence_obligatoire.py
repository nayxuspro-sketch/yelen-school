from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscriptions', '0016_eleve_supprimer_province_commune_village'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eleve',
            name='lieu_residence',
            field=models.CharField(max_length=150, verbose_name='Lieu de résidence (Village/Quartier/Secteur)'),
        ),
    ]
