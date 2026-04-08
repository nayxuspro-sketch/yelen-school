import datetime
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0009_add_numero_recu'),
        ('inscriptions', '0011_eleve_created_by_eleve_updated_by_and_more'),
        ('parametres', '0022_add_modele_message'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoriqueRelance',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='Identifiant')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de modification')),
                ('is_active', models.BooleanField(default=True)),
                ('canal', models.CharField(choices=[('PDF', 'PDF imprimé'), ('SMS', 'SMS')], default='PDF', max_length=10, verbose_name='Canal')),
                ('montant_reclame', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Montant réclamé (FCFA)')),
                ('date_relance', models.DateField(default=datetime.date.today, verbose_name='Date de relance')),
                ('succes', models.BooleanField(default=True, help_text="False si l'envoi SMS a échoué ou si le numéro était invalide", verbose_name='Envoi réussi')),
                ('detail', models.CharField(blank=True, help_text='Numéro de téléphone pour SMS, nom du fichier PDF, etc.', max_length=255, verbose_name='Détail')),
                ('inscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relances', to='inscriptions.inscription', verbose_name='Inscription')),
                ('rubrique', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='parametres.rubriquepaiement', verbose_name='Rubrique')),
                ('envoye_par', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='relances_envoyees', to=settings.AUTH_USER_MODEL, verbose_name='Envoyé par')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historiquerelance_created', to=settings.AUTH_USER_MODEL, verbose_name='Créé par')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historiquerelance_updated', to=settings.AUTH_USER_MODEL, verbose_name='Modifié par')),
            ],
            options={
                'verbose_name': 'Historique de relance',
                'verbose_name_plural': 'Historiques de relances',
                'ordering': ['-date_relance', '-created_at'],
            },
        ),
    ]
