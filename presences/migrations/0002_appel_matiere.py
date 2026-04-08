from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('presences', '0001_initial'),
        ('pedagogie', '0003_remove_matiere_note_max_remove_matiere_note_min_and_more'),
    ]

    operations = [
        # 1. Supprimer l'ancienne contrainte unique_together
        migrations.AlterUniqueTogether(
            name='appel',
            unique_together=set(),
        ),
        # 2. Supprimer le champ enseignement
        migrations.RemoveField(
            model_name='appel',
            name='enseignement',
        ),
        # 3. Ajouter le champ matiere
        migrations.AddField(
            model_name='appel',
            name='matiere',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='appels',
                to='pedagogie.matiere',
                verbose_name='Matière',
            ),
        ),
        # 4. Recréer la contrainte unique_together avec matiere
        migrations.AlterUniqueTogether(
            name='appel',
            unique_together={('classe', 'date', 'matiere')},
        ),
    ]
