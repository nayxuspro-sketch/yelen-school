"""Veille d'exploitation : les alertes de la page Exploitation sont relayées à la direction (notification, SMS pour le
niveau danger), une fois par jour tant qu'elles durent, sans planificateur (première requête du jour)."""
from datetime import date, timedelta

import pytest
from django.urls import reverse
from model_bakery import baker

from core import veille
from core.models import Notification

pytestmark = pytest.mark.django_db

DANGER = {'niveau': 'danger', 'titre': 'Sauvegarde trop ancienne',
          'detail': 'Dernière sauvegarde le 29/10/2026 à 02:00 (52 h) ; attendue toutes les 36 h au plus.'}
WARNING = {'niveau': 'warning', 'titre': 'SMS en difficulté', 'detail': '2 en attente de nouvelle tentative.'}


@pytest.fixture
def direction():
    etab = baker.make('etablissements.Etablissement')
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', telephone='+22670000001',
                           must_change_password=False)
    super_admin = baker.make('accounts.User', etablissement=etab, role='SUPER_ADMIN', telephone='+22670000002',
                             must_change_password=False)
    baker.make('accounts.User', etablissement=etab, role='COMPTABLE', telephone='+22670000003', must_change_password=False)
    baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', is_active=False, must_change_password=False)
    return directeur, super_admin


@pytest.fixture
def sms(mocker):
    mocker.patch('core.sms.get_sms_val', return_value=True)
    return mocker.patch('core.tasks.envoyer_sms_async')


@pytest.fixture
def alertes(mocker):
    return mocker.patch('core.exploitation.etat_exploitation', return_value={'alertes': [DANGER, WARNING]})


def test_relais_notification_et_sms_selon_le_niveau(direction, sms, alertes):
    directeur, super_admin = direction
    assert veille.relayer_alertes() == 4                      # 2 alertes × 2 destinataires
    for compte in direction:
        titres = set(Notification.objects.filter(destinataire=compte).values_list('titre', flat=True))
        assert titres == {'Serveur : Sauvegarde trop ancienne', 'Serveur : SMS en difficulté'}
    notification = Notification.objects.get(destinataire=directeur, titre='Serveur : Sauvegarde trop ancienne')
    assert notification.message == DANGER['detail'] and notification.lien == reverse('core:exploitation')
    numeros = sorted(appel.args[0] for appel in sms.call_args_list)
    assert numeros == ['+22670000001', '+22670000002']        # SMS pour le niveau danger seulement, jamais au comptable
    assert all('Sauvegarde trop ancienne' in appel.args[1] and len(appel.args[1]) <= 160 for appel in sms.call_args_list)


def test_une_fois_par_jour_tant_que_l_alerte_dure(direction, sms, alertes):
    assert veille.relayer_alertes() == 4
    assert veille.relayer_alertes() == 0                      # même jour : rien de plus, quel que soit le processus
    assert veille.relayer_alertes(aujourd_hui=date.today() + timedelta(days=1)) == 4
    alertes.return_value = {'alertes': []}
    assert veille.relayer_alertes(aujourd_hui=date.today() + timedelta(days=2)) == 0
    assert sms.call_count == 4


def test_declenchement_par_la_premiere_requete_du_jour(client, direction, mocker, monkeypatch):
    monkeypatch.setattr(veille, '_verifie_le', None)
    fond = mocker.patch('core.veille._en_arriere_plan')
    client.get('/health/')
    client.get('/health/')
    fond.assert_called_once_with(veille.relayer_alertes)
    assert veille._verifie_le == date.today()
    assert veille.declencher(aujourd_hui=date.today() + timedelta(days=1)) is True
    assert fond.call_count == 2


def test_titre_stable_des_erreurs_applicatives(tmp_path, settings):
    from core import exploitation
    journal = tmp_path / 'django.log'
    quand = exploitation.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    journal.write_text(f"ERROR {quand},123 core.views 1 1 Boom\n", encoding='utf-8')
    erreurs = exploitation.erreurs_recentes(fichier=journal)
    assert erreurs['nombre'] == 1 and erreurs['dernieres'][0]['message'] == 'Boom'
    settings.LOG_DIR = tmp_path
    alerte = next(a for a in exploitation.etat_exploitation()['alertes']
                  if a['titre'] == 'Erreurs applicatives répétées')
    assert alerte['titre'] == 'Erreurs applicatives répétées' and alerte['detail'].startswith('1 erreur(s) en 24 h. Dernière : Boom')
