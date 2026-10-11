"""Page Identité de l'établissement : zone de dépôt du logo sans script inline (CSP)."""
import re

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
def test_zone_logo_sans_script_inline(client):
    etab = baker.make('etablissements.Etablissement', code='LOGO', nom='Lycée Logo')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, must_change_password=False))

    html = client.get(reverse('etablissements:detail')).content.decode()

    assert 'previewImage' not in html and 'onchange=' not in html and 'onmouseover=' not in html
    assert '<div id="logo-dropzone" class="logo-dropzone" data-csp-trigger-click="logo-input">' in html
    assert 'id="logo-input" name="logo" accept="image/*" style="display: none;" ' \
           'data-csp-preview-image="logo-preview" data-preview-conceal="logo-placeholder"' in html
    # Colonnes de la page : classe utilitaire existante (flex-col), « flex-column » n'existait pas dans yelen.css
    assert 'flex-column' not in html and html.count('d-flex flex-col') == 4
    # Seuls les blocs <script> noncés de la page de base subsistent
    assert all('nonce="' in balise for balise in re.findall(r'<script(?![^>]*\ssrc=)[^>]*>', html))
