"""
Migration 0005 — Ajout des modèles SalairePersonnel et CongePersonnel
"""

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0001_initial'),
        ('personnel', '0004_inscriptionpersonnel_created_by_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── SalairePersonnel ────────────────────────────────────────
        migrations.CreateModel(
            name='SalairePersonnel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('mois', models.IntegerField(choices=[
                    (1, 'Janvier'), (2, 'Février'), (3, 'Mars'),
                    (4, 'Avril'), (5, 'Mai'), (6, 'Juin'),
                    (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'),
                    (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre'),
                ], verbose_name='Mois')),
                ('annee', models.IntegerField(verbose_name='Année')),
                ('salaire_base', models.DecimalField(
                    decimal_places=0, default=0, max_digits=12,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Salaire de base (FCFA)')),
                ('indemnite_transport', models.DecimalField(
                    decimal_places=0, default=0, max_digits=10,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Indemnité de transport (FCFA)')),
                ('indemnite_logement', models.DecimalField(
                    decimal_places=0, default=0, max_digits=10,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Indemnité de logement (FCFA)')),
                ('prime_anciennete', models.DecimalField(
                    decimal_places=0, default=0, max_digits=10,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name="Prime d'ancienneté (FCFA)")),
                ('autres_primes', models.DecimalField(
                    decimal_places=0, default=0, max_digits=10,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Autres primes / avantages (FCFA)')),
                ('retenue_cnss', models.DecimalField(
                    decimal_places=0, default=0, max_digits=10,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Retenue CNSS (FCFA)')),
                ('retenue_iuts', models.DecimalField(
                    decimal_places=0, default=0, max_digits=10,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Retenue IUTS (FCFA)')),
                ('autres_retenues', models.DecimalField(
                    decimal_places=0, default=0, max_digits=10,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Autres retenues (FCFA)')),
                ('statut', models.CharField(
                    choices=[('BROUILLON', 'Brouillon'), ('VALIDE', 'Validé'), ('PAYE', 'Payé')],
                    default='BROUILLON', max_length=10, verbose_name='Statut')),
                ('date_paiement', models.DateField(blank=True, null=True, verbose_name='Date de paiement')),
                ('reference_paiement', models.CharField(
                    blank=True, default='', max_length=100, verbose_name='Référence de paiement')),
                ('observations', models.TextField(blank=True, default='', verbose_name='Observations')),
                ('personnel', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='salaires',
                    to='personnel.membrepersonnel',
                    verbose_name='Membre du personnel')),
                ('annee_scolaire', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='salaires_personnel',
                    to='parametres.anneescolaire',
                    verbose_name='Année scolaire')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='salaires_saisis',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Saisi par')),
            ],
            options={
                'verbose_name': 'Salaire Personnel',
                'verbose_name_plural': 'Salaires Personnel',
                'ordering': ['-annee', '-mois', 'personnel__nom'],
                'unique_together': {('personnel', 'mois', 'annee')},
            },
        ),

        # ── CongePersonnel ───────────────────────────────────────────
        migrations.CreateModel(
            name='CongePersonnel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('type_conge', models.CharField(
                    choices=[
                        ('ANNUEL', 'Congé annuel'), ('MALADIE', 'Congé maladie'),
                        ('MATERNITE', 'Congé de maternité'), ('PATERNITE', 'Congé de paternité'),
                        ('EVENEMENT', 'Événement familial'), ('SANS_SOLDE', 'Congé sans solde'),
                    ],
                    default='ANNUEL', max_length=15, verbose_name='Type de congé')),
                ('date_debut', models.DateField(verbose_name='Date de début')),
                ('date_fin', models.DateField(verbose_name='Date de fin')),
                ('nombre_jours', models.IntegerField(
                    default=0,
                    validators=[django.core.validators.MinValueValidator(0)],
                    verbose_name='Nombre de jours ouvrables')),
                ('motif', models.TextField(blank=True, default='', verbose_name='Motif / Justification')),
                ('statut', models.CharField(
                    choices=[
                        ('DEMANDE', 'Demandé'), ('APPROUVE', 'Approuvé'),
                        ('REFUSE', 'Refusé'), ('ANNULE', 'Annulé'),
                    ],
                    default='DEMANDE', max_length=10, verbose_name='Statut')),
                ('date_approbation', models.DateField(blank=True, null=True, verbose_name="Date d'approbation")),
                ('observations', models.TextField(blank=True, default='', verbose_name='Observations')),
                ('personnel', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='conges',
                    to='personnel.membrepersonnel',
                    verbose_name='Membre du personnel')),
                ('approuve_par', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='conges_approuves',
                    to='personnel.membrepersonnel',
                    verbose_name='Approuvé / Refusé par')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='conges_saisis',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Saisi par')),
            ],
            options={
                'verbose_name': 'Congé Personnel',
                'verbose_name_plural': 'Congés Personnel',
                'ordering': ['-date_debut', 'personnel__nom'],
            },
        ),
    ]
