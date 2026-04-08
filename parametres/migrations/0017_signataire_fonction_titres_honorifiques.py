from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0016_add_titre_to_signataire'),
    ]

    operations = [
        migrations.AddField(
            model_name='signatairedocument',
            name='fonction',
            field=models.CharField(
                blank=True,
                default='Le Directeur',
                help_text="Fonction affichée entre la date et le nom, ex: 'Directeur des Études'",
                max_length=150,
                verbose_name='Fonction',
            ),
        ),
        migrations.AddField(
            model_name='signatairedocument',
            name='titres_honorifiques',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Liste ordonnée de titres honorifiques affichés sous le nom",
                verbose_name='Titres Honorifiques',
            ),
        ),
    ]
