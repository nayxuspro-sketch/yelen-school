import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestLicencesViews:
    def test_statut_redirect_anon(self, client):
        url = reverse('licences:statut_licence')
        response = client.get(url)
        assert response.status_code == 302

    def test_statut_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('licences:statut_licence')
        response = client.get(url)
        assert response.status_code == 200

    def test_gestion_redirect_anon(self, client):
        url = reverse('licences:gestion')
        response = client.get(url)
        assert response.status_code == 302

    def test_gestion_superuser_only(self, client):
        user = baker.make('accounts.User', is_superuser=False)
        client.force_login(user)
        url = reverse('licences:gestion')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_gestion_superuser(self, client):
        user = baker.make('accounts.User', is_superuser=True)
        client.force_login(user)
        url = reverse('licences:gestion')
        response = client.get(url)
        assert response.status_code == 200
