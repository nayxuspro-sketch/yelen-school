import uuid
from decimal import Decimal
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pedagogie', '0003_remove_matiere_note_max_remove_matiere_note_min_and_more'),
        ('parametres', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatiereCycle',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('coefficient', models.DecimalField(
                    decimal_places=2, default=Decimal('1.00'), max_digits=3,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.00'))],
                    verbose_name='Coefficient',
                )),
                ('moy_min', models.DecimalField(
                    decimal_places=2, default=Decimal('0.00'), max_digits=5,
                    verbose_name='Barème minimal',
                )),
                ('moy_max', models.DecimalField(
                    decimal_places=2, default=Decimal('20.00'), max_digits=5,
                    verbose_name='Barème maximal',
                )),
                ('heures_hebdomadaires', models.DecimalField(
                    decimal_places=2, default=Decimal('0.00'), max_digits=4,
                    verbose_name='Heures hebdomadaires',
                )),
                ('est_obligatoire', models.BooleanField(default=True, verbose_name='Obligatoire dans ce cycle')),
                ('matiere', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='configurations_cycle',
                    to='pedagogie.matiere',
                    verbose_name='Matière',
                )),
                ('cycle', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='matieres_configurees',
                    to='parametres.cycle',
                    verbose_name='Cycle',
                )),
            ],
            options={
                'verbose_name': 'Configuration matière/cycle',
                'verbose_name_plural': 'Configurations matière/cycle',
                'ordering': ['cycle__ordre', 'cycle__nom'],
                'unique_together': {('matiere', 'cycle')},
            },
        ),
    ]
