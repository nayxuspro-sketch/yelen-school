from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inscriptions', '0007_last_classe_charfield'),
        ('parametres', '0008_typesanction'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscription',
            name='statut_eleve',
            field=models.ForeignKey(
                blank=True,
                help_text="Détermine les tarifs de scolarité applicables à cet élève",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='inscriptions',
                to='parametres.statuteleve',
                verbose_name='Statut élève',
            ),
        ),
    ]
