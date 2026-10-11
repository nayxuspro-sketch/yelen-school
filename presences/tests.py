import re

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestPresencesViews:
    def test_appel_list_redirect_anon(self, client):
        url = reverse('presences:appel_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_appel_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('presences:appel_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_justification_list_redirect_anon(self, client):
        url = reverse('presences:justification_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_justification_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('presences:justification_list')
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
def test_appel_saisie_compteurs_sans_inline(client):
    """Les compteurs de l'appel sont recalculés par un écouteur du formulaire, sans attribut onchange (CSP)."""
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab))
    classe = baker.make('parametres.Classe', etablissement=etab)
    appel = baker.make('presences.Appel', classe=classe, est_clos=False)
    presence = baker.make('presences.Presence', appel=appel, inscription__classe=classe, statut='PRESENT')

    response = client.get(reverse('presences:appel_saisie', kwargs={'appel_id': appel.pk}))

    assert response.status_code == 200
    html = response.content.decode()
    assert not re.search(r'\son[a-z]+="', html)
    assert f'id="s_{presence.pk}_PRESENT"' in html and 'data-csp-action="mark-all-present"' in html
    assert "document.getElementById('appel-form').addEventListener('change', updateCounts);" in html
    assert all('nonce="' in b for b in re.findall(r'<script(?![^>]*\ssrc=)[^>]*>', html))
