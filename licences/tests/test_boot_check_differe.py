"""
Le boot check des licences ne doit plus interroger la base pendant
AppConfig.ready() (avertissement Django « Accessing the database during app
initialization is discouraged ») : il s'exécute une fois, à la première requête.
"""
import warnings

import pytest
from django.apps import apps
from django.db import connection
from django.test.utils import CaptureQueriesContext

from licences import boot_check


@pytest.fixture(autouse=True)
def etat_propre():
    boot_check.reinitialiser_etat_boot()
    yield
    boot_check.reinitialiser_etat_boot()


@pytest.mark.django_db
def test_ready_n_execute_aucune_requete():
    config = apps.get_app_config('licences')
    with warnings.catch_warnings():
        warnings.simplefilter('error')          # tout avertissement = échec
        with CaptureQueriesContext(connection) as requetes:
            config.ready()
    assert len(requetes) == 0


@pytest.mark.django_db
def test_premiere_requete_declenche_le_controle_une_seule_fois(monkeypatch):
    appels = []
    monkeypatch.setattr(boot_check, 'run_boot_check', lambda strict=False: appels.append(strict) or {
        'ok': True, 'tampering': [], 'bail_expired': [], 'binding_invalid': [],
        'antitamper': {'ok': True, 'issues': []},
    })
    boot_check.verifier_au_premier_appel()
    boot_check.verifier_au_premier_appel()
    assert appels == [False]
    assert boot_check.blocage_boot() is None


@pytest.mark.django_db
def test_mode_strict_anomalie_critique_bloque_l_application(monkeypatch, settings, client):
    settings.LICENSE_ENFORCEMENT = True
    settings.LICENCE_ANTITAMPER_ENABLED = True
    monkeypatch.delenv('LICENCE_DISABLE_STRICT_BOOT', raising=False)
    monkeypatch.setattr(boot_check, 'run_boot_check', lambda strict=False: {
        'ok': False, 'tampering': ['YLN-TEST'], 'bail_expired': [], 'binding_invalid': [],
        'antitamper': {'ok': True, 'issues': []},
    })
    boot_check.verifier_au_premier_appel()
    assert 'YLN-TEST' in boot_check.blocage_boot()

    settings.MIDDLEWARE = list(settings.MIDDLEWARE) + ['licences.middleware.LicenceCheckMiddleware']
    response = client.get('/accounts/login/')
    assert response.status_code == 503


@pytest.mark.django_db
def test_hors_mode_strict_une_anomalie_ne_bloque_pas(monkeypatch, settings):
    settings.LICENSE_ENFORCEMENT = False
    monkeypatch.setattr(boot_check, 'run_boot_check', lambda strict=False: {
        'ok': False, 'tampering': ['YLN-TEST'], 'bail_expired': [], 'binding_invalid': [],
        'antitamper': {'ok': True, 'issues': []},
    })
    boot_check.verifier_au_premier_appel()
    assert boot_check.blocage_boot() is None
