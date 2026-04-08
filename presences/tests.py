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
