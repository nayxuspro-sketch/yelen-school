import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestExamensViews:
    def test_session_list_redirect_anon(self, client):
        url = reverse('examens:session_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_session_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('examens:session_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_session_create_redirect_anon(self, client):
        url = reverse('examens:session_create')
        response = client.get(url)
        assert response.status_code == 302

    def test_session_create_get(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('examens:session_create')
        response = client.get(url)
        assert response.status_code == 200
