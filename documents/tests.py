import re

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


@pytest.mark.django_db
def test_convocation_form_selecteur_classe_sans_inline(client):
    """Le filtre de classe est un formulaire GET (CSP) et la liste des élèves s'affiche pour la classe choisie."""
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, actif=True)
    inscription = baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee)

    response = client.get(reverse('documents:convocation_form') + f'?classe={classe.pk}')

    assert response.status_code == 200
    html = response.content.decode()
    assert not re.search(r'\son[a-z]+="', html) and 'toggleAll' not in html
    assert '<form method="get"' in html and 'name="classe"' in html and 'data-csp-submit-on-change' in html
    assert f'<option value="{classe.pk}" selected>' in html
    assert f'value="{inscription.pk}" class="eleve-cb"' in html and 'class="convocation-eleve"' in html
    assert all('nonce="' in b for b in re.findall(r'<script(?![^>]*\ssrc=)[^>]*>', html))
