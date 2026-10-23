from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0031_rolepersonnalise'),
    ]

    operations = [
        migrations.AlterField(
            model_name='identiteetablissement',
            name='telephone',
            field=models.CharField(max_length=35, verbose_name='Téléphone'),
        ),
    ]
