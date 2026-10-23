"""Version unique (fichier VERSION) : interface, /health/, cache du Service Worker et rafraîchissement
automatique des postes après une mise à jour (fin du Ctrl+F5)."""
import re

import pytest
from django.conf import settings
from django.urls import reverse
from model_bakery import baker

RECHARGEMENT = "navigator.serviceWorker.addEventListener('controllerchange'"


def test_fichier_version_semver():
    version = (settings.BASE_DIR / 'VERSION').read_text(encoding='utf-8').strip()

    assert re.fullmatch(r'\d+\.\d+\.\d+', version), version
    assert settings.YELEN_VERSION == version


def test_health_expose_la_version(client):
    assert client.get(reverse('core:health_check')).json()['version'] == settings.YELEN_VERSION


def test_service_worker_cache_par_version(client, settings):
    """Le nom du cache change à chaque version : le navigateur installe le nouveau worker et
    purge l'ancien cache sans intervention de l'utilisateur."""
    settings.YELEN_VERSION = '9.8.7'

    script = client.get('/app-sw.js').content.decode()

    assert "const APP_CACHE = 'yelen-app-9.8.7';" in script
    assert '__VERSION__' not in script


@pytest.mark.django_db
def test_page_de_connexion_version_et_rechargement(client, settings):
    settings.YELEN_VERSION = '9.8.7'

    page = client.get(reverse('accounts:login')).content.decode()

    assert '<span>v9.8.7</span>' in page
    assert RECHARGEMENT in page


@pytest.mark.django_db
def test_barre_laterale_version_et_rechargement(client, settings):
    settings.TWO_FACTOR_REQUIRED = False
    settings.YELEN_VERSION = '9.8.7'
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='SUPER_ADMIN', etablissement=etab, is_superuser=True,
                                  must_change_password=False))

    page = client.get('/').content.decode()

    assert '<span class="sb-version">YELEN SCHOOL v9.8.7</span>' in page
    assert RECHARGEMENT in page
