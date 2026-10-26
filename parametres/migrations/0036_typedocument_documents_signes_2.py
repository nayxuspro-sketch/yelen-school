from django.db import migrations

# Documents que l'application imprime avec une case « Le Directeur » restée manuscrite ou sans aucune
# signature : absents du catalogue, ils ne pouvaient recevoir ni nom, ni prénom, ni signature scannée.
TYPES = (
    ('DOSSIER_TRANSFERT', 'Dossier de Transfert', 'SCOLARITE', 'Dossier de transfert inter-établissements'),
    ('LISTE_CANDIDATS', 'Liste des Candidats', 'SCOLARITE', "Liste des candidats d'une session d'examen"),
    ('LISTE_BOURSIERS', 'Liste des Boursiers', 'FINANCE', 'Liste des élèves boursiers'),
    ('PV_CONSEIL', 'Procès-Verbal de Conseil de Classe', 'PEDAGOGIE', 'Procès-verbal du conseil de classe'),
    ('MANUELS_SCOLAIRES', 'Manuels Scolaires', 'PEDAGOGIE', 'Inventaire, attributions et manuels non rendus'),
    ('CONTRAT_TRAVAIL', 'Contrat de Travail', 'PERSONNEL', 'Contrat de travail du personnel'),
    ('BULLETIN_SALAIRE', 'Bulletin de Salaire', 'PERSONNEL', 'Bulletin de salaire du personnel'),
    ('BULLETIN_VACATION', 'Bulletin de Vacation', 'PERSONNEL', 'Bulletin de vacation des vacataires'),
)

CHAMPS_COPIES = ('membre_personnel_id', 'fonction', 'titre', 'titre_honorifique', 'titres_honorifiques')


def ajouter_types(apps, schema_editor):
    """Crée les types manquants puis leur applique, par cycle et année, le signataire déjà configuré
    pour leur catégorie (même règle que l'écran « Configurer les signataires », qui affecte une catégorie)."""
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
        ('parametres', '0035_typedocument_documents_signes'),
    ]

    operations = [
        migrations.RunPython(ajouter_types, reverse_code=migrations.RunPython.noop),
    ]
