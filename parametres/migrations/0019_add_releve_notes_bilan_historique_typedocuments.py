from django.db import migrations


def add_typedocuments(apps, schema_editor):
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    docs = [
        {
            'code': 'RELEVE_NOTES',
            'libelle': 'Relevé de Notes',
            'description': 'Relevé des notes par matière pour un enseignement donné',
            'categorie': 'PEDAGOGIE',
            'actif': True,
        },
        {
            'code': 'BILAN_ENCAISSEMENTS',
            'libelle': 'Bilan des Encaissements',
            'description': 'Récapitulatif des encaissements par rubrique et par classe',
            'categorie': 'FINANCE',
            'actif': True,
        },
        {
            'code': 'HIST_VERSEMENTS',
            'libelle': 'Historique des Versements',
            'description': 'Historique détaillé des paiements d\'un élève',
            'categorie': 'FINANCE',
            'actif': True,
        },
    ]
    for data in docs:
        TypeDocument.objects.get_or_create(code=data['code'], defaults=data)


def remove_typedocuments(apps, schema_editor):
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    TypeDocument.objects.filter(
        code__in=['RELEVE_NOTES', 'BILAN_ENCAISSEMENTS', 'HIST_VERSEMENTS']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0018_alter_signatairedocument_fonction_and_more'),
    ]

    operations = [
        migrations.RunPython(add_typedocuments, reverse_code=remove_typedocuments),
    ]
