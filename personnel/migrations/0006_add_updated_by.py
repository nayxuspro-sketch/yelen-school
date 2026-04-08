"""
Migration 0006 — Ajout du champ updated_by manquant sur SalairePersonnel et CongePersonnel
(champ hérité de BaseModel omis dans la migration 0005)
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personnel', '0005_salaire_conge'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='salairepersonnel',
            name='updated_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='salairepersonnel_updated',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modifié par',
            ),
        ),
        migrations.AddField(
            model_name='congepersonnel',
            name='updated_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='congepersonnel_updated',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modifié par',
            ),
        ),
    ]
