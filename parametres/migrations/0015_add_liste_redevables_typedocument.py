from django.db import migrations


def add_liste_redevables(apps, schema_editor):
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    TypeDocument.objects.get_or_create(
        code='LISTE_REDEVABLES',
        defaults={
            'libelle': 'Liste des Redevables',
            'description': 'Liste des élèves ayant un reste à payer',
            'categorie': 'FINANCE',
            'actif': True,
        }
    )


def remove_liste_redevables(apps, schema_editor):
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    TypeDocument.objects.filter(code='LISTE_REDEVABLES').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0014_add_is_active_to_titrefonction'),
    ]

    operations = [
        migrations.RunPython(add_liste_redevables, reverse_code=remove_liste_redevables),
    ]
