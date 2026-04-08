import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestApiAuth:
    def test_obtenir_token_champs_manquants(self, client):
        url = reverse('api:obtenir_token')
        response = client.post(url, {}, content_type='application/json')
        assert response.status_code == 400

    def test_obtenir_token_identifiants_invalides(self, client):
        url = reverse('api:obtenir_token')
        response = client.post(
            url,
            {'username': 'inconnu', 'password': 'mauvais'},
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_obtenir_token_valide(self, client):
        user = baker.make('accounts.User')
        user.set_password('testpass123')
        user.save()
        url = reverse('api:obtenir_token')
        response = client.post(
            url,
            {'username': user.username, 'password': 'testpass123'},
            content_type='application/json',
        )
        assert response.status_code == 200
        assert 'token' in response.json()

    def test_eleves_sans_token(self, client):
        url = reverse('api:eleves_list')
        response = client.get(url)
        assert response.status_code == 401

    def test_eleves_avec_token(self, client):
        from rest_framework.authtoken.models import Token
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        token, _ = Token.objects.get_or_create(user=user)
        url = reverse('api:eleves_list')
        response = client.get(url, HTTP_AUTHORIZATION=f'Token {token.key}')
        assert response.status_code == 200
