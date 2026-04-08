import datetime
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0006_add_statut_eleve_to_paiement'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Remboursement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Dernière modification')),
                ('is_active', models.BooleanField(default=True, help_text='Décocher pour désactiver sans supprimer.', verbose_name='Actif')),
                ('montant', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Montant remboursé')),
                ('motif', models.CharField(blank=True, max_length=255, verbose_name='Motif du remboursement')),
                ('date_remboursement', models.DateField(default=datetime.date.today, verbose_name='Date de remboursement')),
                ('paiement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remboursements', to='finances.paiement', verbose_name="Paiement d'origine")),
                ('rembourse_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Remboursé par')),
            ],
            options={
                'verbose_name': 'Remboursement',
                'verbose_name_plural': 'Remboursements',
                'ordering': ['-date_remboursement', '-created_at'],
            },
        ),
    ]
