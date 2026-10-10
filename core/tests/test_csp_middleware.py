"""En-tête Content-Security-Policy posé par CSPNonceMiddleware."""
import re

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestEnteteCSP:
    @pytest.fixture
    def reponse(self, client):
        client.force_login(baker.make('accounts.User', is_superuser=True, must_change_password=False))
        return client.get(reverse('pedagogie:matiere_list'))

    def test_directives(self, reponse):
        csp = reponse['Content-Security-Policy']
        directives = {d.split(' ', 1)[0]: d.split(' ', 1)[1] for d in csp.split('; ')}

        nonce = re.fullmatch(r"'self' 'nonce-([A-Za-z0-9_-]{16,})'", directives['script-src'])
        assert nonce, directives['script-src']
        assert directives['style-src'] == f"'self' 'nonce-{nonce.group(1)}'"
        # Les gestionnaires inline (onclick=…) restent interdits ; les attributs style="…" sont autorisés
        assert directives['script-src-attr'] == "'none'"
        assert directives['style-src-attr'] == "'unsafe-inline'"
        assert "'unsafe-inline'" not in directives['script-src'] and "'unsafe-inline'" not in directives['style-src']
        assert directives['frame-ancestors'] == "'none'" and directives['form-action'] == "'self'"

    def test_nonce_de_la_page_correspond_a_l_entete(self, reponse):
        nonce = re.search(r"'nonce-([^']+)'", reponse['Content-Security-Policy']).group(1)
        assert f'nonce="{nonce}"' in reponse.content.decode()

    def test_absent_des_reponses_non_html(self, client):
        client.force_login(baker.make('accounts.User', is_superuser=True, must_change_password=False))
        reponse = client.get(reverse('pedagogie:matiere_list'), HTTP_HX_REQUEST='true')
        assert 'Content-Security-Policy' in reponse  # partiel HTMX : HTML
        from django.http import JsonResponse
        from yelen_school.csp_middleware import CSPNonceMiddleware
        json = CSPNonceMiddleware(lambda request: JsonResponse({}))(type('R', (), {})())
        assert 'Content-Security-Policy' not in json
