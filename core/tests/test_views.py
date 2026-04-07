import pytest
from django.urls import reverse
from model_bakery import baker

@pytest.mark.django_db
class TestCoreViews:
    def test_home_view_redirect_anon(self, client):
        url = reverse('core:home')
        response = client.get(url)
        assert response.status_code == 302

    def test_home_view_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab, is_superuser=True)
        client.force_login(user)
        url = reverse('core:home')
        response = client.get(url)
        assert response.status_code == 200
