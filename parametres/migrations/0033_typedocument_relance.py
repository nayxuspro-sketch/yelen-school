from django.db import migrations


def ajouter_relance(apps, schema_editor):
    """Type de document « Relance de Paiement » (catégorie Finance), absent des types prédéfinis :
    la relance PDF ne trouvait donc jamais de signataire. Les signataires Finance déjà configurés
    (portés par la liste des redevables) sont repris pour la relance."""
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    SignataireDocument = apps.get_model('parametres', 'SignataireDocument')
    relance, _ = TypeDocument.objects.get_or_create(code='RELANCE', defaults={
        'libelle': 'Relance de Paiement',
        'description': 'Relance adressée aux parents pour un reste à payer',
        'categorie': 'FINANCE',
        'actif': True,
    })
    for s in SignataireDocument.objects.filter(type_document__code='LISTE_REDEVABLES'):
        SignataireDocument.objects.get_or_create(
            cycle_id=s.cycle_id, type_document=relance, annee_scolaire_id=s.annee_scolaire_id,
            defaults={
                'membre_personnel_id': s.membre_personnel_id, 'fonction': s.fonction, 'titre': s.titre,
                'titre_honorifique': s.titre_honorifique, 'titres_honorifiques': s.titres_honorifiques, 'actif': s.actif,
            },
        )


def retirer_relance(apps, schema_editor):
    apps.get_model('parametres', 'TypeDocument').objects.filter(code='RELANCE').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('parametres', '0032_identiteetablissement_telephone_35'),
    ]

    operations = [
        migrations.RunPython(ajouter_relance, reverse_code=retirer_relance),
    ]
