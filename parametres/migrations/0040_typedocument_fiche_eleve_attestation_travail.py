from django.db import migrations

# Lot J : deux nouveaux documents signés — la fiche individuelle de l'élève et l'attestation de travail.
TYPES = (
    ('FICHE_ELEVE', "Fiche Individuelle de l'Élève", 'SCOLARITE', "Fiche individuelle de l'élève (identité, famille, santé, parcours)"),
    ('ATTESTATION_TRAVAIL', 'Attestation de Travail', 'PERSONNEL', 'Attestation de travail du personnel'),
)

CHAMPS_COPIES = ('membre_personnel_id', 'fonction', 'titre', 'titre_honorifique', 'titres_honorifiques')


def ajouter_types(apps, schema_editor):
    """Crée les types manquants puis leur applique, par cycle et année, le signataire déjà configuré
    pour leur catégorie (même règle que la migration 0036)."""
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    SignataireDocument = apps.get_model('parametres', 'SignataireDocument')
    for code, libelle, categorie, description in TYPES:
        type_doc, _ = TypeDocument.objects.get_or_create(code=code, defaults={
            'libelle': libelle, 'categorie': categorie, 'description': description, 'actif': True,
        })
        modeles = (
            SignataireDocument.objects.filter(type_document__categorie=categorie, actif=True)
            .exclude(type_document=type_doc).order_by('cycle_id', 'annee_scolaire_id', '-updated_at')
        )
        vus = set()
        for modele in modeles:
            cle = (modele.cycle_id, modele.annee_scolaire_id)
            if cle in vus:
                continue
            vus.add(cle)
            SignataireDocument.objects.get_or_create(
                cycle_id=modele.cycle_id, type_document=type_doc, annee_scolaire_id=modele.annee_scolaire_id,
                defaults={**{champ: getattr(modele, champ) for champ in CHAMPS_COPIES}, 'actif': True},
            )


class Migration(migrations.Migration):
    dependencies = [
        ('parametres', '0039_modele_message_sanction'),
    ]

    operations = [
        migrations.RunPython(ajouter_types, reverse_code=migrations.RunPython.noop),
    ]
