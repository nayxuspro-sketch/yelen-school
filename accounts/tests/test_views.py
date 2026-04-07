import pytest
from django.urls import reverse
from model_bakery import baker

@pytest.mark.django_db
class TestAccountsViews:
    def test_login_view_get(self, client):
        url = reverse('accounts:login')
        response = client.get(url)
        assert response.status_code == 200

    def test_profile_view_redirect_anon(self, client):
        url = reverse('accounts:profile')
        response = client.get(url)
        assert response.status_code == 302

    def test_profile_view_logged_in(self, client):
        user = baker.make('accounts.User')
        client.force_login(user)
        url = reverse('accounts:profile')
        response = client.get(url)
        assert response.status_code == 200
