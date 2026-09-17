from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0013_budget_depenses'),
    ]

    operations = [
        migrations.AddField(
            model_name='depense',
            name='motif_annulation',
            field=models.TextField(blank=True, verbose_name="Motif d'annulation"),
        ),
    ]
