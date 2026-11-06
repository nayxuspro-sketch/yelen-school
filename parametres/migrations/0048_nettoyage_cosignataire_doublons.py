# Nettoyage des doublons de co-signataires + contrainte d'unicité.
from django.db import migrations, models


def supprimer_doublons_cosignataire(apps, schema_editor):
    """Garde un seul co-signataire actif par (signataire_principal, membre)."""
    CoSignataire = apps.get_model('parametres', 'CoSignataire')
    doublons = (
        CoSignataire.objects.filter(actif=True, membre_personnel_id__isnull=False)
        .values('signataire_principal', 'membre_personnel_id')
        .annotate(count=models.Count('id'), min_id=models.Min('id'))
        .filter(count__gt=1)
    )
    for groupe in doublons:
        CoSignataire.objects.filter(
            signataire_principal_id=groupe['signataire_principal'],
            membre_personnel_id=groupe['membre_personnel_id'],
            actif=True,
        ).exclude(id=groupe['min_id']).delete()


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
