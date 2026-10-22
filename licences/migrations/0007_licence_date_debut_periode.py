from django.db import migrations, models


def renseigner_debut_periode(apps, schema_editor):
    """Période en cours des licences existantes : activation, à défaut création."""
    Licence = apps.get_model('licences', 'Licence')
    for licence in Licence.objects.all().only('pk', 'date_activation', 'created_at'):
        debut = licence.date_activation or licence.created_at
        if debut is not None:
            # update() : la signature de la licence ne couvre pas ce champ et n'est pas recalculée.
            Licence.objects.filter(pk=licence.pk).update(date_debut_periode=debut.date())


class Migration(migrations.Migration):

    dependencies = [
        ('licences', '0006_licence_jeton_signe_empreinte_serveur'),
    ]

    operations = [
        migrations.AddField(
            model_name='licence',
            name='date_debut_periode',
            field=models.DateField(
                blank=True,
                help_text='Activation ou dernier renouvellement : borne la durée affichée',
                null=True,
                verbose_name='Début de la période en cours',
            ),
        ),
        migrations.RunPython(renseigner_debut_periode, migrations.RunPython.noop),
    ]
