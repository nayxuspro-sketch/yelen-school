import datetime
import uuid
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('viescolaire', '0006_appeldecision'),
        ('etablissements', '0001_initial'),
        ('personnel', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigEDT',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Dernière modification')),
                ('is_active', models.BooleanField(default=True, help_text='Décocher pour désactiver sans supprimer.', verbose_name='Actif')),
                ('heure_debut_matin', models.TimeField(default=datetime.time(7, 30), verbose_name='Début matin')),
                ('heure_fin_matin', models.TimeField(default=datetime.time(12, 0), verbose_name='Fin matin')),
                ('heure_debut_aprem', models.TimeField(default=datetime.time(14, 0), verbose_name='Début après-midi')),
                ('heure_fin_aprem', models.TimeField(default=datetime.time(17, 20), verbose_name='Fin après-midi')),
                ('duree_seance', models.PositiveIntegerField(default=50, help_text="Durée d'une séance en minutes (ex : 50, 55, 60)", verbose_name='Durée séance (min)')),
                ('jours_actifs', models.JSONField(default=list, help_text='Liste des numéros de jours (1=Lun, 2=Mar, …, 6=Sam)', verbose_name='Jours actifs')),
                ('etablissement', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='config_edt', to='etablissements.etablissement', verbose_name='Établissement')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Modifié par')),
            ],
            options={
                'verbose_name': 'Configuration EDT',
                'verbose_name_plural': 'Configurations EDT',
            },
        ),
        migrations.CreateModel(
            name='DisponibiliteEnseignant',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Dernière modification')),
                ('is_active', models.BooleanField(default=True, help_text='Décocher pour désactiver sans supprimer.', verbose_name='Actif')),
                ('jour', models.IntegerField(choices=[(1, 'Lundi'), (2, 'Mardi'), (3, 'Mercredi'), (4, 'Jeudi'), (5, 'Vendredi'), (6, 'Samedi'), (7, 'Dimanche')], verbose_name='Jour')),
                ('heure_debut', models.TimeField(verbose_name='Heure début')),
                ('heure_fin', models.TimeField(verbose_name='Heure fin')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Modifié par')),
                ('etablissement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='indisponibilites_enseignants', to='etablissements.etablissement', verbose_name='Établissement')),
                ('personnel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='indisponibilites', to='personnel.membrepersonnel', verbose_name='Enseignant')),
            ],
            options={
                'verbose_name': 'Indisponibilité enseignant',
                'verbose_name_plural': 'Indisponibilités enseignants',
                'ordering': ['jour', 'heure_debut'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='disponibiliteenseignant',
            unique_together={('personnel', 'jour', 'heure_debut')},
        ),
    ]
