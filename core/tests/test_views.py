import re

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


@pytest.mark.django_db
def test_assistant_sans_hx_on(client):
    """L'assistant câble htmx:beforeRequest / afterRequest dans son script noncé (hx-on est évalué, donc bloqué)."""
    client.force_login(baker.make('accounts.User', etablissement=baker.make('etablissements.Etablissement'),
                                  is_superuser=True, role='SUPER_ADMIN'))

    html = client.get(reverse('core:chatbot')).content.decode()

    assert 'hx-on:' not in html
    assert "form.addEventListener('htmx:beforeRequest', showLoading)" in html
    assert all('nonce="' in b for b in re.findall(r'<script(?![^>]*\ssrc=)[^>]*>', html))
