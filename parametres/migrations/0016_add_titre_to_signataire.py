from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0015_add_liste_redevables_typedocument'),
    ]

    operations = [
        migrations.AddField(
            model_name='signatairedocument',
            name='titre',
            field=models.CharField(
                blank=True,
                default='',
                max_length=100,
                verbose_name='Titre / Fonction',
                help_text='Ex: Directeur, Proviseur, Censeur — affiché sur le document',
            ),
        ),
    ]
