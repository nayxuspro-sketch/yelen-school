# Relie chaque manuel au cycle réellement configuré dans l'établissement.
import django.db.models.deletion
from django.db import migrations, models


CYCLES_HISTORIQUES = {
    'PRESCOLAIRE': ('PRES', 'Préscolaire', 1),
    'PRIMAIRE': ('PRIM', 'Primaire', 2),
    'POST_PRIMAIRE': ('POST', 'Post-primaire', 3),
    'SECONDAIRE': ('SEC', 'Secondaire', 4),
}
CYCLES_PAR_CODE = {configuration[0]: code for code, configuration in CYCLES_HISTORIQUES.items()}


def migrer_cycles_manuels(apps, schema_editor):
    """Transfère l'ancien code fixe vers le cycle relationnel de chaque établissement."""
    ManuelScolaire = apps.get_model('manuels', 'ManuelScolaire')
    Cycle = apps.get_model('parametres', 'Cycle')
    alias = schema_editor.connection.alias

    for manuel in ManuelScolaire.objects.using(alias).all().iterator():
        configuration = CYCLES_HISTORIQUES.get(manuel.cycle)
        if configuration is None:
            raise RuntimeError(
                f"Cycle historique non reconnu pour le manuel {manuel.pk} : {manuel.cycle!r}. "
                "Corrigez cette valeur avant de relancer les migrations."
            )
        code, nom, ordre = configuration
        cycle, _ = Cycle.objects.using(alias).get_or_create(
            etablissement_id=manuel.etablissement_id,
            code=code,
            defaults={'nom': nom, 'ordre': ordre, 'actif': True},
        )
        ManuelScolaire.objects.using(alias).filter(pk=manuel.pk).update(cycle_relationnel_id=cycle.pk)


def restaurer_cycles_manuels(apps, schema_editor):
    """Rollback : rétablit le code historique si le cycle peut être représenté."""
    ManuelScolaire = apps.get_model('manuels', 'ManuelScolaire')
    Cycle = apps.get_model('parametres', 'Cycle')
    alias = schema_editor.connection.alias

    for manuel in ManuelScolaire.objects.using(alias).all().iterator():
        cycle = Cycle.objects.using(alias).get(pk=manuel.cycle_relationnel_id)
        code_historique = CYCLES_PAR_CODE.get(cycle.code)
        if code_historique is None:
            raise RuntimeError(
                f"Impossible de restaurer le cycle du manuel {manuel.pk} : "
                f"le cycle {cycle.code!r} n'a pas d'équivalent historique."
            )
        ManuelScolaire.objects.using(alias).filter(pk=manuel.pk).update(cycle=code_historique)


class Migration(migrations.Migration):

    dependencies = [
        ('manuels', '0003_prets_echeance_retour'),
        ('parametres', '0049_directions_cycles_and_identity_labels'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manuelscolaire',
            name='cycle',
            field=models.CharField(
                blank=True,
                choices=[
                    ('PRESCOLAIRE', 'Préscolaire'),
                    ('PRIMAIRE', 'Primaire'),
                    ('POST_PRIMAIRE', 'Post-primaire'),
                    ('SECONDAIRE', 'Secondaire'),
                ],
                max_length=20,
                null=True,
                verbose_name='Cycle',
            ),
        ),
        migrations.AddField(
            model_name='manuelscolaire',
            name='cycle_relationnel',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='manuels',
                to='parametres.cycle',
                verbose_name='Cycle configuré',
            ),
        ),
        migrations.RunPython(migrer_cycles_manuels, restaurer_cycles_manuels),
        migrations.RemoveField(
            model_name='manuelscolaire',
            name='cycle',
        ),
        migrations.RenameField(
            model_name='manuelscolaire',
            old_name='cycle_relationnel',
            new_name='cycle',
        ),
        migrations.AlterField(
            model_name='manuelscolaire',
            name='cycle',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='manuels',
                to='parametres.cycle',
                verbose_name='Cycle',
            ),
        ),
    ]
