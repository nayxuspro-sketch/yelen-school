# Migration 5.50.0 — échéance de retour et dernière relance des prêts d'ouvrages.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manuels', '0002_creance'),
    ]

    operations = [
        migrations.AddField(
            model_name='attributionmanuel',
            name='date_retour_prevue',
            field=models.DateField(blank=True, help_text='Échéance du prêt ; au-delà, le prêt passe en retard et les familles peuvent être relancées.', null=True, verbose_name='Retour prévu'),
        ),
        migrations.AddField(
            model_name='attributionmanuel',
            name='derniere_relance_le',
            field=models.DateTimeField(blank=True, help_text='Date de la dernière relance envoyée à la famille pour ce prêt.', null=True, verbose_name='Dernière relance'),
        ),
    ]
