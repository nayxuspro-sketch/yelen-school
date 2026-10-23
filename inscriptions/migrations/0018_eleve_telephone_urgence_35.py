from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inscriptions', '0017_eleve_lieu_residence_obligatoire'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eleve',
            name='telephone_urgence',
            field=models.CharField(blank=True, default='', max_length=35, verbose_name="Téléphone d'urgence"),
        ),
    ]
