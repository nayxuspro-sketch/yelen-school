# Relie les frais de scolarité au cycle configuré de leur établissement.
import django.db.models.deletion
from django.db import migrations, models


CYCLES_HISTORIQUES = {
    'PRESCOLAIRE': ('PRES', 'Préscolaire', 1),
    'PRIMAIRE': ('PRIM', 'Primaire', 2),
    'POST_PRIMAIRE': ('POST', 'Post-primaire', 3),
    'SECONDAIRE': ('SEC', 'Secondaire', 4),
}
CYCLES_PAR_CODE = {configuration[0]: code for code, configuration in CYCLES_HISTORIQUES.items()}


def migrer_cycles_frais(apps, schema_editor):
    """Transfère les codes historiques vers le cycle de l'établissement concerné."""
    FraisScolarite = apps.get_model('finances', 'FraisScolarite')
    AnneeScolaire = apps.get_model('parametres', 'AnneeScolaire')
    Cycle = apps.get_model('parametres', 'Cycle')
    alias = schema_editor.connection.alias

    frais_scolarite = FraisScolarite.objects.using(alias).select_related('annee_scolaire')
    for frais in frais_scolarite.iterator():
        configuration = CYCLES_HISTORIQUES.get(frais.cycle)
        if frais.cycle in (None, ''):
            continue
        if configuration is None:
            raise RuntimeError(
                f"Cycle historique non reconnu pour les frais {frais.pk} : {frais.cycle!r}. "
                "Corrigez cette valeur avant de relancer les migrations."
            )
        code, nom, ordre = configuration
        annee = AnneeScolaire.objects.using(alias).only('etablissement_id').get(
            pk=frais.annee_scolaire_id,
        )
        cycle, _ = Cycle.objects.using(alias).get_or_create(
            etablissement_id=annee.etablissement_id,
            code=code,
            defaults={'nom': nom, 'ordre': ordre, 'actif': True},
        )
        FraisScolarite.objects.using(alias).filter(pk=frais.pk).update(cycle_relationnel_id=cycle.pk)


def restaurer_cycles_frais(apps, schema_editor):
    """Rollback : rétablit le code historique si le cycle est représentable."""
    FraisScolarite = apps.get_model('finances', 'FraisScolarite')
    Cycle = apps.get_model('parametres', 'Cycle')
    alias = schema_editor.connection.alias

    frais_scolarite = FraisScolarite.objects.using(alias).exclude(cycle_relationnel__isnull=True).iterator()
    for frais in frais_scolarite:
        cycle = Cycle.objects.using(alias).get(pk=frais.cycle_relationnel_id)
        code_historique = CYCLES_PAR_CODE.get(cycle.code)
        if code_historique is None:
            raise RuntimeError(
                f"Impossible de restaurer le cycle des frais {frais.pk} : "
                f"le cycle {cycle.code!r} n'a pas d'équivalent historique."
            )
        FraisScolarite.objects.using(alias).filter(pk=frais.pk).update(cycle=code_historique)


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0023_lot_f_caisse_parametres'),
        ('parametres', '0049_directions_cycles_and_identity_labels'),
    ]

    operations = [
        migrations.AddField(
            model_name='fraisscolarite',
            name='cycle_relationnel',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='frais_scolarite',
                to='parametres.cycle',
                verbose_name='Cycle',
            ),
        ),
        migrations.RunPython(migrer_cycles_frais, restaurer_cycles_frais),
        migrations.RemoveField(
            model_name='fraisscolarite',
            name='cycle',
        ),
        migrations.RenameField(
            model_name='fraisscolarite',
            old_name='cycle_relationnel',
            new_name='cycle',
        ),
        migrations.AlterField(
            model_name='fraisscolarite',
            name='cycle',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='frais_scolarite',
                to='parametres.cycle',
                verbose_name='Cycle',
            ),
        ),
    ]
