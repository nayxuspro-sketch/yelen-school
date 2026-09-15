from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone
from model_bakery import baker


@pytest.mark.django_db
class TestSmsAutoCommand:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.etablissement = baker.make('etablissements.Etablissement')
        cycle = baker.make('parametres.Cycle')
        classe = baker.make(
            'parametres.Classe',
            etablissement=self.etablissement,
            cycle=cycle,
        )
        eleve = baker.make(
            'inscriptions.Eleve',
            telephone_parent='+22670112233',
            nom='OUEDRAOGO',
            prenom='Adama',
        )
        statut = baker.make(
            'parametres.StatutEleve',
            etablissement=self.etablissement,
        )
        annee = baker.make(
            'parametres.AnneeScolaire',
            etablissement=self.etablissement,
            est_courante=True,
        )
        inscription = baker.make(
            'inscriptions.Inscription',
            eleve=eleve,
            classe=classe,
            annee_scolaire=annee,
            statut_eleve=statut,
        )
        appel = baker.make(
            'presences.Appel',
            classe=classe,
            annee_scolaire=annee,
            date=timezone.localdate() - timedelta(days=1),
        )
        baker.make(
            'presences.Presence',
            appel=appel,
            inscription=inscription,
            statut='ABSENT',
        )
        self.declencheur = baker.make(
            'parametres.DeclencheurSMS',
            etablissement=self.etablissement,
            type_declencheur='ABSENCE_J1',
            actif=True,
        )

    @patch('core.tasks.envoyer_sms_async')
    @patch('core.sms.get_sms_val', return_value=True)
    def test_dry_run_ne_declenche_aucun_envoi(self, mock_sms_config, mock_envoyer):
        output = StringIO()

        call_command('sms_auto', '--dry-run', stdout=output)

        mock_envoyer.assert_not_called()
        self.declencheur.refresh_from_db()
        assert self.declencheur.last_run is None
        assert 'simul' in output.getvalue().lower()

    @patch('core.tasks.envoyer_sms_async')
    @patch('core.sms.get_sms_val', return_value=True)
    def test_absence_envoie_une_fois_et_garde_la_date(self, mock_sms_config, mock_envoyer):
        call_command('sms_auto')

        mock_envoyer.assert_called_once()
        self.declencheur.refresh_from_db()
        assert self.declencheur.last_run is not None
        assert self.declencheur.nb_envoyes_total == 1

        # Une seconde exécution le même jour ne renvoie pas un doublon.
        call_command('sms_auto')
        assert mock_envoyer.call_count == 1
