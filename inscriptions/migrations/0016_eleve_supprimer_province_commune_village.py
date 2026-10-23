from django.db import migrations


def reporter_dans_lieu_residence(apps, schema_editor):
    """Avant suppression des colonnes, leurs valeurs sont reportées dans le lieu de résidence s'il est vide."""
    Eleve = apps.get_model('inscriptions', 'Eleve')
    modifies = []
    for eleve in Eleve.objects.filter(lieu_residence='').exclude(village='', commune='', province=''):
        parties = []
        for valeur in (eleve.village, eleve.commune, eleve.province):
            valeur = valeur.strip()
            if valeur and valeur.lower() not in (p.lower() for p in parties):
                parties.append(valeur)
        eleve.lieu_residence = ', '.join(parties)[:150]
        modifies.append(eleve)
    Eleve.objects.bulk_update(modifies, ['lieu_residence'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('inscriptions', '0015_eleve_lieu_residence'),
    ]

    operations = [
        migrations.RunPython(reporter_dans_lieu_residence, migrations.RunPython.noop),
        migrations.RemoveField(model_name='eleve', name='province'),
        migrations.RemoveField(model_name='eleve', name='commune'),
        migrations.RemoveField(model_name='eleve', name='village'),
    ]
