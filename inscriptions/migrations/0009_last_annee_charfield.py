from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscriptions', '0008_inscription_statut_eleve'),
        ('parametres', '0001_initial'),
    ]

    operations = [
        # 1. Supprimer l'ancienne colonne FK (last_annee_id)
        migrations.RemoveField(
            model_name='eleve',
            name='last_annee',
        ),
        # 2. Ajouter la nouvelle colonne CharField (last_annee)
        migrations.AddField(
            model_name='eleve',
            name='last_annee',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Ex : 2024-2025',
                max_length=20,
                verbose_name='Dernière année scolaire',
            ),
        ),
    ]
