import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestViescolaireViews:
    def test_conseil_list_redirect_anon(self, client):
        url = reverse('viescolaire:conseil_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_conseil_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('viescolaire:conseil_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_activite_list_redirect_anon(self, client):
        url = reverse('viescolaire:activite_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_activite_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('viescolaire:activite_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_sanction_list_redirect_anon(self, client):
        url = reverse('viescolaire:sanction_list')
        response = client.get(url)
        assert response.status_code == 302
