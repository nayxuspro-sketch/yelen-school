from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('licences', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='licence',
            name='cle_licence',
            field=models.CharField(
                editable=False,
                help_text='Clé unique générée automatiquement',
                max_length=20,
                unique=True,
                verbose_name='Clé de licence',
            ),
        ),
    ]
