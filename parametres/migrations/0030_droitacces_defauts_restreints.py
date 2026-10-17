"""Les actes financiers, le budget prévisionnel et la saisie des sanctions repartent de leur règle
historique (rôles par défaut propres dans ``parametres.droits``) : les enregistrements créés par
héritage du module, qui contredisaient les contrôles des vues, sont retirés. Le Super Admin peut
rouvrir ces droits dans la matrice."""
from django.db import migrations


def retirer_droits_herites(apps, schema_editor):
    DroitAcces = apps.get_model('parametres', 'DroitAcces')
    DroitAcces.objects.filter(module='finances').exclude(action='').delete()
    DroitAcces.objects.filter(module='finances', fonctionnalite='/finances/budget/').delete()
    DroitAcces.objects.filter(module='viescolaire', fonctionnalite='/viescolaire/sanctions/', action='prononcer').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0029_droitacces_action'),
    ]

    operations = [
        migrations.RunPython(retirer_droits_herites, migrations.RunPython.noop),
    ]
