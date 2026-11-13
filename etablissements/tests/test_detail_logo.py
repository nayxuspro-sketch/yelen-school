"""L'ancienne URL établissements ouvre désormais la fiche unique, sans formulaire dupliqué."""
import re

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
def test_ancienne_url_ouvre_la_fiche_unique_sans_champs_repetes(client):
    etab = baker.make('etablissements.Etablissement', code='LOGO', nom='Lycée Logo')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, must_change_password=False))

    response = client.get(reverse('etablissements:detail'))
    html = response.content.decode()

    assert response.status_code == 200
    assert "Fiche de l'établissement" in html
    assert html.count('name="nom_etablissement"') == 1
    assert html.count('name="telephone"') == 1
    assert html.count('name="email"') == 1
    assert html.count('name="logo"') == 1
    assert 'previewImage' not in html and 'onchange=' not in html and 'onmouseover=' not in html
    assert all('nonce="' in balise for balise in re.findall(r'<script(?![^>]*\ssrc=)[^>]*>', html))
