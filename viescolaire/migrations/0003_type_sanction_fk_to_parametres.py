from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0018_alter_signatairedocument_fonction_and_more'),
        ('viescolaire', '0002_add_points_conduite_to_sanction'),
    ]

    operations = [
        # 1. Supprimer les sanctions dont le type ne peut pas être mappé
        migrations.RunSQL(
            "DELETE FROM viescolaire_sanctiondisciplinaire;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # 2. Supprimer l'ancienne colonne CharField
        migrations.RemoveField(
            model_name='sanctiondisciplinaire',
            name='type_sanction',
        ),
        # 3. Ajouter la nouvelle colonne FK nullable puis la rendre obligatoire
        migrations.AddField(
            model_name='sanctiondisciplinaire',
            name='type_sanction',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='sanctions',
                to='parametres.typesanction',
                verbose_name='Type de sanction',
            ),
        ),
        migrations.AlterField(
            model_name='sanctiondisciplinaire',
            name='type_sanction',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='sanctions',
                to='parametres.typesanction',
                verbose_name='Type de sanction',
            ),
        ),
    ]
