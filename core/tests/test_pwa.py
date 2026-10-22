"""PWA : icônes PNG des manifestes (installation Android/iOS), icône iOS, autorité HTTPS téléchargeable."""
import re

import pytest
from django.contrib.staticfiles import finders
from django.urls import reverse
from model_bakery import baker


@pytest.mark.parametrize('nom_url', ['core:app_manifest', 'core:pwa_manifest'])
def test_manifeste_icones_png(client, nom_url):
    """Chrome exige des icônes PNG 192 et 512 (+ maskable) pour proposer « Installer l'application »."""
    icones = client.get(reverse(nom_url)).json()['icons']

    assert {(i['sizes'], i['purpose']) for i in icones} == {('192x192', 'any'), ('512x512', 'any'), ('512x512', 'maskable')}
    for icone in icones:
        assert icone['type'] == 'image/png'
        assert re.fullmatch(r'/static/img/pwa/icon-(192|512|maskable-512)(\.[0-9a-f]{12})?\.png', icone['src']), icone['src']


def test_fichiers_icones_presents():
    for nom in ('icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png'):
        assert finders.find(f'img/pwa/{nom}'), nom


@pytest.mark.django_db
def test_icone_ios_dans_les_pages(client, settings):
    settings.TWO_FACTOR_REQUIRED = False
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='SUPER_ADMIN', etablissement=etab, is_superuser=True,
                                  must_change_password=False))

    page = client.get('/').content.decode()

    assert 'rel="apple-touch-icon"' in page
    assert 'img/pwa/apple-touch-icon' in page


def test_certificat_autorite_absent(client):
    assert client.get(reverse('core:certificat_autorite')).status_code == 404


def test_certificat_autorite_telechargeable(client, settings, tmp_path):
    settings.BASE_DIR = tmp_path
    (tmp_path / 'certs').mkdir()
    (tmp_path / 'certs' / 'yelen-ca.crt').write_text('-----BEGIN CERTIFICATE-----\nTEST\n-----END CERTIFICATE-----\n')

    reponse = client.get(reverse('core:certificat_autorite'))

    assert reponse.status_code == 200
    assert reponse['Content-Type'] == 'application/x-x509-ca-cert'
    assert 'filename="yelen-ca.crt"' in reponse['Content-Disposition']
    assert b'BEGIN CERTIFICATE' in b''.join(reponse.streaming_content)
