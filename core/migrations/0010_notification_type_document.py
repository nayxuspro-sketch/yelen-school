# Migration 5.48.1 — nouvelle valeur « Document délivré » (avis aux comptes parent et élève).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_usage_module_quotidien'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('BULLETIN', 'Bulletin publié'), ('ABSENCE', 'Absence signalée'), ('SANCTION', 'Sanction disciplinaire'), ('DOCUMENT', 'Document délivré'), ('GENERAL', 'Information générale')], default='GENERAL', max_length=20),
        ),
    ]
