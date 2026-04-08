import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('examens', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlacementExamen',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Dernière modification')),
                ('is_active', models.BooleanField(default=True, help_text='Décocher pour désactiver sans supprimer.', verbose_name='Actif')),
                ('numero_place', models.PositiveSmallIntegerField(blank=True, null=True, help_text='Position numérotée dans la salle (optionnel)', verbose_name='Numéro de place')),
                ('salle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='placements', to='examens.salleexamen', verbose_name='Salle')),
                ('candidat', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='placement', to='examens.inscriptionexamen', verbose_name='Candidat')),
            ],
            options={
                'verbose_name': 'Placement en Salle',
                'verbose_name_plural': 'Placements en Salle',
                'ordering': ['salle', 'numero_place', 'candidat__numero_table'],
            },
        ),
    ]
