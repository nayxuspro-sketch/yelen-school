"""Point de santé /health/ : public, sans session, servi même avec le contrôle de licence."""
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

LICENCE_MIDDLEWARES = [
    'licences.middleware.LicenceCheckMiddleware',
    'licences.middleware.LicenceLimitsMiddleware',
    'licences.middleware.LicenceContextMiddleware',
]


def test_health_anonyme_200(client):
    reponse = client.get(reverse('core:health_check'))
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps['status'] == 'ok'
    assert corps['database'] == 'ok'
    assert corps['cache'] == 'ok'


def test_health_servi_avec_controle_de_licence(client, settings):
    settings.LICENSE_ENFORCEMENT = True
    settings.MIDDLEWARE = list(settings.MIDDLEWARE) + LICENCE_MIDDLEWARES
    assert client.get(reverse('core:health_check')).status_code == 200
