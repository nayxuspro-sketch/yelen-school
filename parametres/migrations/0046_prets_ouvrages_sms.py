# Migration 5.50.0 — SMS de relance des prêts d'ouvrages (modèle PRET, déclencheur PRETS_RETARD).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parametres', '0045_periodeevaluation_derogation_ouverte'),
    ]

    operations = [
        migrations.AlterField(
            model_name='declencheursms',
            name='type_declencheur',
            field=models.CharField(choices=[('ABSENCE_J1', 'Absences non justifiées (J+1)'), ('ECHEANCIER', "Rappel d'échéancier"), ('RESULTATS', 'Bulletin disponible'), ('PRETS_RETARD', "Prêt d'ouvrage en retard"), ('COMPTE_RENDU', 'Compte rendu quotidien du promoteur')], max_length=20, verbose_name='Type de déclencheur'),
        ),
        migrations.AlterField(
            model_name='modelemessage',
            name='type',
            field=models.CharField(choices=[('BULLETIN', 'Disponibilité du bulletin'), ('ABSENCE', 'Absence élève'), ('RETARD', 'Retard élève'), ('SEUIL_ABSENCES', "Seuil d'absences atteint"), ('SANCTION', 'Sanction disciplinaire'), ('PAIEMENT', 'Relance paiement'), ('PRET', "Prêt d'ouvrage en retard"), ('REUNION', "Réunion parents d'élèves")], max_length=20, verbose_name='Type de message'),
        ),
    ]
