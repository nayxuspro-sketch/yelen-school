from django.db import migrations

# La liste générale des élèves (toutes classes) est distincte de la liste alphabétique d'une classe :
# elle n'a pas de cycle, elle est signée par la direction générale de l'établissement. Son type lui
# permet d'être configurée nommément (Paramètres → Signataires) sans toucher aux listes de classe.
CODE = 'LISTE_ELEVES'
LIBELLE = 'Liste des Élèves'


def ajouter_type(apps, schema_editor):
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    TypeDocument.objects.get_or_create(code=CODE, defaults={
        'libelle': LIBELLE,
        'categorie': 'SCOLARITE',
        'description': "Liste générale des élèves de l'établissement, toutes classes (exports CSV, Excel, PDF)",
        'actif': True,
    })


class Migration(migrations.Migration):
    dependencies = [
        ('parametres', '0050_fusion_droits_fiche_etablissement'),
    ]

    operations = [
        migrations.RunPython(ajouter_type, reverse_code=migrations.RunPython.noop),
    ]
