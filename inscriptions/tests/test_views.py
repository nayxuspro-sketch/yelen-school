import pytest
from django.urls import reverse
from model_bakery import baker
from inscriptions.models import Eleve

@pytest.mark.django_db
class TestInscriptionsViews:
    @pytest.fixture
    def logged_in_client(self, client):
        user = baker.make('accounts.User', is_superuser=True)
        client.force_login(user)
        return client

    def test_eleve_list_view(self, logged_in_client):
        """Vérifie l'accès à la liste des élèves."""
        baker.make('inscriptions.Eleve', _quantity=3)
        url = reverse('inscriptions:eleve_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'eleve_list' in response.context
        assert len(response.context['eleve_list']) >= 3

    def test_eleve_list_htmx(self, logged_in_client):
        """Vérifie la recherche HTMX dans la liste des élèves."""
        baker.make('inscriptions.Eleve', nom="ZONGO", prenom="Jean")
        url = reverse('inscriptions:eleve_list')
        response = logged_in_client.get(url, {'q': 'ZONGO'}, HTTP_HX_REQUEST='true')
        assert response.status_code == 200
        assert 'ZONGO' in response.content.decode().upper()

    def test_eleve_detail_view(self, logged_in_client):
        """Vérifie l'accès aux détails d'un élève."""
        eleve = baker.make('inscriptions.Eleve')
        url = reverse('inscriptions:eleve_detail', kwargs={'pk': eleve.pk})
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert response.context['eleve'] == eleve

    def test_eleve_create_view_get(self, logged_in_client):
        """Vérifie l'affichage du formulaire de création."""
        url = reverse('inscriptions:eleve_create')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'form' in response.context
