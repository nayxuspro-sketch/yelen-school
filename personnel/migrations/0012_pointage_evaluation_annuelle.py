# Migration 5.51.0 — pointage du personnel et évaluation annuelle.

import datetime
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('etablissements', '0005_cycles_arrayfield_to_jsonfield'),
        ('parametres', '0046_prets_ouvrages_sms'),
        ('personnel', '0011_absencepersonnel'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReglagePointage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Dernière modification')),
                ('is_active', models.BooleanField(default=True, help_text='Décocher pour désactiver sans supprimer.', verbose_name='Actif')),
                ('heure_arrivee_limite', models.TimeField(default=datetime.time(7, 30), help_text='Un pointage postérieur à cette heure est compté en retard.', verbose_name="Heure d'arrivée limite")),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('etablissement', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='reglage_pointage', to='etablissements.etablissement', verbose_name='Établissement')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Modifié par')),
            ],
            options={
                'verbose_name': 'Réglage du pointage',
                'verbose_name_plural': 'Réglages du pointage',
            },
        ),
        migrations.CreateModel(
            name='EvaluationAnnuelle',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Dernière modification')),
                ('is_active', models.BooleanField(default=True, help_text='Décocher pour désactiver sans supprimer.', verbose_name='Actif')),
                ('date_entretien', models.DateField(verbose_name="Date de l'entretien")),
                ('ponctualite', models.PositiveSmallIntegerField(default=3, help_text='Note de 0 à 5', verbose_name='Ponctualité et assiduité')),
                ('competence', models.PositiveSmallIntegerField(default=3, help_text='Note de 0 à 5', verbose_name='Compétence professionnelle')),
                ('qualite', models.PositiveSmallIntegerField(default=3, help_text='Note de 0 à 5', verbose_name='Qualité du travail rendu')),
                ('relations', models.PositiveSmallIntegerField(default=3, help_text='Note de 0 à 5', verbose_name='Relations avec les élèves, les familles et les collègues')),
                ('initiative', models.PositiveSmallIntegerField(default=3, help_text='Note de 0 à 5', verbose_name='Initiative et respect des consignes')),
                ('bilan', models.TextField(blank=True, default='', verbose_name="Bilan de l'année")),
                ('objectifs', models.TextField(blank=True, default='', verbose_name="Objectifs de l'année suivante")),
                ('avis', models.CharField(choices=[('FAVORABLE', 'Favorable'), ('RESERVE', 'Favorable avec réserves'), ('DEFAVORABLE', 'Défavorable')], default='FAVORABLE', max_length=12, verbose_name='Avis')),
                ('annee_scolaire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations_personnel', to='parametres.anneescolaire', verbose_name='Année scolaire')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('evaluateur', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='evaluations_conduites', to='personnel.membrepersonnel', verbose_name='Évaluateur')),
                ('personnel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evaluations', to='personnel.membrepersonnel', verbose_name='Membre du personnel')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Modifié par')),
            ],
            options={
                'verbose_name': 'Évaluation annuelle',
                'verbose_name_plural': 'Évaluations annuelles',
                'ordering': ['-date_entretien'],
                'constraints': [models.UniqueConstraint(fields=('personnel', 'annee_scolaire'), name='evaluation_annuelle_unique')],
            },
        ),
        migrations.CreateModel(
            name='PointagePersonnel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Dernière modification')),
                ('is_active', models.BooleanField(default=True, help_text='Décocher pour désactiver sans supprimer.', verbose_name='Actif')),
                ('date', models.DateField(verbose_name='Date')),
                ('heure_arrivee', models.TimeField(blank=True, null=True, verbose_name='Arrivée')),
                ('heure_depart', models.TimeField(blank=True, null=True, verbose_name='Départ')),
                ('statut', models.CharField(choices=[('PRESENT', 'Présent'), ('RETARD', 'En retard'), ('ABSENT', 'Absent'), ('CONGE', 'En congé')], default='PRESENT', max_length=10, verbose_name='Statut')),
                ('observation', models.CharField(blank=True, default='', max_length=200, verbose_name='Observation')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('personnel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pointages', to='personnel.membrepersonnel', verbose_name='Membre du personnel')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated', to=settings.AUTH_USER_MODEL, verbose_name='Modifié par')),
            ],
            options={
                'verbose_name': 'Pointage du personnel',
                'verbose_name_plural': 'Pointages du personnel',
                'ordering': ['-date', 'personnel__nom'],
                'indexes': [models.Index(fields=['date'], name='pointage_date_idx')],
                'constraints': [models.UniqueConstraint(fields=('personnel', 'date'), name='pointage_personnel_jour_unique')],
            },
        ),
    ]
