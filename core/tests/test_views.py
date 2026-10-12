import re

import pytest
from django.template.loader import render_to_string
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


@pytest.mark.django_db
def test_pages_erreur_bouton_retour_sans_javascript_url(client):
    """404/500 : « ← Retour » passe par data-csp-action (javascript: est bloqué par la CSP) ; la page 500,
    rendue sans request, doit charger csp_handlers.js sans nonce (script-src 'self')."""
    html_404 = client.get('/page-inexistante/').content.decode()
    assert '<a href="/" data-csp-action="history-back"' in html_404
    assert re.search(r'<script nonce="[^"]+" src="/static/js/csp_handlers[^"]*\.js[^"]*"></script>', html_404)

    html_500 = render_to_string('500.html')
    assert '<a href="/" data-csp-action="history-back"' in html_500
    assert re.search(r'<script src="/static/js/csp_handlers[^"]*\.js[^"]*"></script>', html_500)
    assert 'javascript:' not in html_404 + html_500
