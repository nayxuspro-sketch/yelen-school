import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personnel', '0010_membrepersonnel_titre_capacite'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AbsencePersonnel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Dernière modification')),
                ('is_active', models.BooleanField(default=True, help_text='Décocher pour désactiver sans supprimer.', verbose_name='Actif')),
                ('date_debut', models.DateField(verbose_name='Du')),
                ('date_fin', models.DateField(verbose_name='Au')),
                ('motif', models.CharField(choices=[('MALADIE', 'Maladie'), ('PERMISSION', 'Permission'), ('FORMATION', 'Formation / mission'), ('NON_JUSTIFIEE', 'Non justifiée'), ('AUTRE', 'Autre')], default='NON_JUSTIFIEE', max_length=15, verbose_name='Motif')),
                ('justifiee', models.BooleanField(default=False, verbose_name='Justifiée (pièce fournie)')),
                ('retenue', models.BooleanField(default=True, help_text="Proposée sur le brouillon de paie du mois si l'absence n'est pas justifiée", verbose_name='Retenue sur salaire')),
                ('observation', models.CharField(blank=True, default='', max_length=200, verbose_name='Observation')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='absences_personnel_saisies', to=settings.AUTH_USER_MODEL, verbose_name='Saisie par')),
                ('personnel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='absences', to='personnel.membrepersonnel', verbose_name='Membre du personnel')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Modifié par')),
            ],
            options={
                'verbose_name': 'Absence du personnel',
                'verbose_name_plural': 'Absences du personnel',
                'ordering': ['-date_debut'],
            },
        ),
    ]
