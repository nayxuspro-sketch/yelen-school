from django.db import migrations


def corriger_code(apps, schema_editor):
    """Le code inséré par 0042 dépassait les 20 caractères de TypeDocument.code (refusé par PostgreSQL, toléré par
    SQLite) : on ramène les installations SQLite déjà migrées au code court."""
    TypeDocument = apps.get_model('parametres', 'TypeDocument')
    if TypeDocument.objects.filter(code='CONFORMITE_TARIFAIRE').exists():
        TypeDocument.objects.filter(code='ATTESTATION_CONFORMITE_TARIFAIRE').delete()
    else:
        TypeDocument.objects.filter(code='ATTESTATION_CONFORMITE_TARIFAIRE').update(code='CONFORMITE_TARIFAIRE')


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0042_plafonds_reglementaires'),
    ]

    operations = [
        migrations.RunPython(corriger_code, migrations.RunPython.noop),
    ]
