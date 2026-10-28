from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0038_modele_message_seuil_absences'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modelemessage',
            name='type',
            field=models.CharField(choices=[('BULLETIN', 'Disponibilité du bulletin'), ('ABSENCE', 'Absence élève'), ('RETARD', 'Retard élève'), ('SEUIL_ABSENCES', "Seuil d'absences atteint"), ('SANCTION', 'Sanction disciplinaire'), ('PAIEMENT', 'Relance paiement'), ('REUNION', "Réunion parents d'élèves")], max_length=20, verbose_name='Type de message'),
        ),
    ]
