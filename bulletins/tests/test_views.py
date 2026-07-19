import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestBulletinsViews:
    def test_index_redirect_anon(self, client):
        url = reverse('bulletins:index')
        response = client.get(url)
        assert response.status_code == 302

    def test_index_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('bulletins:index')
        response = client.get(url)
        assert response.status_code == 200

    def test_index_sans_etablissement(self, client):
        user = baker.make('accounts.User', etablissement=None)
        client.force_login(user)
        url = reverse('bulletins:index')
        response = client.get(url)
        assert response.status_code == 200
