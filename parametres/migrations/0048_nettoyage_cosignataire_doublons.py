# Nettoyage des doublons de co-signataires + contrainte d'unicité.
from collections import defaultdict

from django.db import migrations, models


def supprimer_doublons_cosignataire(apps, schema_editor):
    """Garde un seul co-signataire actif par (signataire_principal, membre)."""
    CoSignataire = apps.get_model('parametres', 'CoSignataire')
    groupes = defaultdict(list)
    for cs in CoSignataire.objects.filter(
        actif=True, membre_personnel_id__isnull=False
    ).order_by('created_at'):
        groupes[(cs.signataire_principal_id, cs.membre_personnel_id)].append(cs)
    for cosigs in groupes.values():
        # Garder le plus ancien (premier créé), supprimer les doublons.
        for cs in cosigs[1:]:
            cs.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0047_pointage_evaluation_personnel'),
    ]

    operations = [
        migrations.RunPython(
            supprimer_doublons_cosignataire,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name='cosignataire',
            constraint=models.UniqueConstraint(
                fields=['signataire_principal', 'membre_personnel_id'],
                condition=models.Q(actif=True),
                name='unique_cosignataire_actif_par_membre',
            ),
        ),
    ]
