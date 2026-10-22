import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viescolaire', '0007_configedt_disponibiliteenseignant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configedt',
            name='heure_debut_aprem',
            field=models.TimeField(
                blank=True, default=datetime.time(14, 0),
                help_text="Laisser vide pour une journée continue (pas de cours l'après-midi)",
                null=True, verbose_name='Début après-midi',
            ),
        ),
        migrations.AlterField(
            model_name='configedt',
            name='heure_fin_aprem',
            field=models.TimeField(blank=True, default=datetime.time(17, 20), null=True, verbose_name='Fin après-midi'),
        ),
    ]
