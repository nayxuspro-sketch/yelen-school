from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('viescolaire', '0008_configedt_apres_midi_optionnelle'),
    ]

    operations = [
        migrations.AddField(
            model_name='sanctiondisciplinaire',
            name='parents_notifies_le',
            field=models.DateTimeField(blank=True, help_text='SMS et notification du portail parent envoyés à la saisie', null=True, verbose_name='Parents informés le'),
        ),
    ]
