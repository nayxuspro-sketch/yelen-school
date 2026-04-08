import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestDocumentsViews:
    def test_document_list_redirect_anon(self, client):
        url = reverse('documents:document_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_document_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('documents:document_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_liste_classes_selector_redirect_anon(self, client):
        url = reverse('documents:liste_classes_selector')
        response = client.get(url)
        assert response.status_code == 302

    def test_liste_classes_selector_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('documents:liste_classes_selector')
        response = client.get(url)
        assert response.status_code == 200
