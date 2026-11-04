from django.db import migrations

# Lot 5 (5.51.0) : deux nouveaux documents signés du module personnel — la feuille de pointage mensuelle
# et le compte rendu d'entretien annuel d'évaluation.
TYPES = (
    ('FEUILLE_POINTAGE', 'Feuille de Pointage du Personnel', 'PERSONNEL',
     'Feuille de pointage mensuelle du personnel (jours, heures, retards, absences)'),
    ('EVALUATION_PERSONNEL', "Compte Rendu d'Entretien Annuel", 'PERSONNEL',
     "Compte rendu de l'entretien annuel d'évaluation du personnel"),
)

CHAMPS_COPIES = ('membre_personnel_id', 'fonction', 'titre', 'titre_honorifique', 'titres_honorifiques')


def ajouter_types(apps, schema_editor):
    """Crée les types manquants puis leur applique, par cycle et année, le signataire déjà configuré
    pour leur catégorie (même règle que les migrations 0040 et 0046)."""
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
        ('parametres', '0046_prets_ouvrages_sms'),
    ]

    operations = [
        migrations.RunPython(ajouter_types, reverse_code=migrations.RunPython.noop),
    ]
