from django.db import migrations

# Types de documents signés par l'application mais absents des types prédéfinis : « Configurer les
# Signataires » ne les proposait pas (l'emploi du temps n'avait aucun type et était rendu avec un
# signataire de repli ; convocation, circulaire et congé n'apparaissaient qu'après un premier document).
TYPES = (
    ('EMPLOI_DU_TEMPS', 'Emploi du Temps', 'PEDAGOGIE', 'Emploi du temps de classe et de professeur'),
    ('CONVOCATION', 'Convocation', 'ADMINISTRATIF', 'Convocation adressée aux parents'),
    ('CIRCULAIRE', 'Circulaire', 'ADMINISTRATIF', 'Circulaire adressée aux parents'),
    ('CONGE_PERSONNEL', 'Autorisation de Congé Personnel', 'PERSONNEL', 'Autorisation de congé ou de permission du personnel'),
)


def ajouter_types(apps, schema_editor):
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    for code, libelle, categorie, description in TYPES:
        TypeDocument.objects.get_or_create(code=code, defaults={
            'libelle': libelle, 'categorie': categorie, 'description': description, 'actif': True,
        })


class Migration(migrations.Migration):
    dependencies = [
        ('parametres', '0034_distinction'),
    ]

    operations = [
        migrations.RunPython(ajouter_types, reverse_code=migrations.RunPython.noop),
    ]
