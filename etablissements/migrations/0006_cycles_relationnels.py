# Cycles de l'établissement : migration de l'ancienne liste JSON vers la relation Cycle.
from django.db import migrations


CYCLES_HISTORIQUES = {
    'PRESCOLAIRE': ('PRES', 'Préscolaire', 1),
    'PRIMAIRE': ('PRIM', 'Primaire', 2),
    'POST_PRIMAIRE': ('POST', 'Post-primaire', 3),
    'SECONDAIRE': ('SEC', 'Secondaire', 4),
}
ORDRE_CODES = tuple(CYCLES_HISTORIQUES)
CYCLES_PAR_CODE = {configuration[0]: code for code, configuration in CYCLES_HISTORIQUES.items()}


def migrer_cycles_vers_relation(apps, schema_editor):
    """Crée les cycles relationnels manquants sans remplacer les configurations existantes."""
    Etablissement = apps.get_model('etablissements', 'Etablissement')
    Cycle = apps.get_model('parametres', 'Cycle')
    alias = schema_editor.connection.alias

    for etablissement in Etablissement.objects.using(alias).all().iterator():
        codes = etablissement.cycles or []
        if isinstance(codes, str):
            codes = [code.strip() for code in codes.split(',') if code.strip()]
        if not isinstance(codes, list):
            raise RuntimeError(
                f"Cycles historiques invalides pour l'établissement {etablissement.pk} : {codes!r}"
            )

        for code_historique in dict.fromkeys(codes):
            configuration = CYCLES_HISTORIQUES.get(code_historique)
            if configuration is None:
                raise RuntimeError(
                    f"Cycle historique non reconnu pour l'établissement {etablissement.pk} : "
                    f"{code_historique!r}. Corrigez cette valeur avant de relancer les migrations."
                )
            code, nom, ordre = configuration
            Cycle.objects.using(alias).get_or_create(
                etablissement_id=etablissement.pk,
                code=code,
                defaults={'nom': nom, 'ordre': ordre, 'actif': True},
            )


def restaurer_liste_historique(apps, schema_editor):
    """Rollback : reconstruit la liste JSON à partir des cycles relationnels connus."""
    Etablissement = apps.get_model('etablissements', 'Etablissement')
    Cycle = apps.get_model('parametres', 'Cycle')
    alias = schema_editor.connection.alias

    for etablissement in Etablissement.objects.using(alias).all().iterator():
        codes_relationnels = set(
            Cycle.objects.using(alias)
            .filter(etablissement_id=etablissement.pk)
            .values_list('code', flat=True)
        )
        inconnus = codes_relationnels.difference(set(CYCLES_PAR_CODE) | {'TOUT'})
        if inconnus:
            raise RuntimeError(
                f"Impossible de restaurer la liste historique de l'établissement {etablissement.pk} : "
                f"codes relationnels non représentables {sorted(inconnus)!r}."
            )

        codes_historiques = {
            CYCLES_PAR_CODE[code] for code in codes_relationnels if code in CYCLES_PAR_CODE
        }
        if 'TOUT' in codes_relationnels:
            codes_historiques.update(CYCLES_HISTORIQUES)
        etablissement.cycles = [code for code in ORDRE_CODES if code in codes_historiques]
        etablissement.save(using=alias, update_fields=['cycles'])


class Migration(migrations.Migration):

    dependencies = [
        ('etablissements', '0005_cycles_arrayfield_to_jsonfield'),
        ('parametres', '0048_nettoyage_cosignataire_doublons'),
    ]

    operations = [
        migrations.RunPython(migrer_cycles_vers_relation, restaurer_liste_historique),
        migrations.RemoveField(
            model_name='etablissement',
            name='cycles',
        ),
    ]
