"""Apparence (5.32.0) : thème sombre par défaut, clair ou « selon l'appareil », choisi dans Mon profil, rendu par
l'attribut data-theme de base.html et la feuille de style ; le mode automatique est résolu par static/js/theme.js."""
import pytest
from django.conf import settings
from django.urls import reverse
from model_bakery import baker

pytestmark = pytest.mark.django_db


@pytest.fixture
def compte(client):
    utilisateur = baker.make('accounts.User', role='COMPTABLE', must_change_password=False, email='awa@yelen.test',
                             etablissement=baker.make('etablissements.Etablissement'))
    client.force_login(utilisateur)
    return utilisateur


def test_theme_choisi_dans_le_profil_et_rendu_par_base(client, compte):
    assert compte.theme == 'sombre'
    assert 'data-theme="sombre"' in client.get(reverse('accounts:profile')).content.decode()

    donnees = {'first_name': 'Awa', 'last_name': 'KABORE', 'email': compte.email, 'telephone': '', 'theme': 'clair'}
    assert client.post(reverse('accounts:profile'), donnees).status_code == 302
    compte.refresh_from_db()
    assert compte.theme == 'clair'
    html = client.get(reverse('core:notifications_list')).content.decode()
    assert '<html lang="fr" data-theme="clair">' in html and 'js/theme.' in html

    reponse = client.post(reverse('accounts:profile'), {**donnees, 'theme': 'rose'})
    assert reponse.status_code == 200 and reponse.context['form'].errors['theme']
    compte.refresh_from_db()
    assert compte.theme == 'clair'


def test_feuille_de_style_et_script_du_theme():
    css = (settings.BASE_DIR / 'static' / 'css' / 'yelen.css').read_text(encoding='utf-8')
    assert '--ink:' in css and ':root[data-theme="clair"]' in css
    script = (settings.BASE_DIR / 'static' / 'js' / 'theme.js').read_text(encoding='utf-8')
    assert "'auto'" in script and 'prefers-color-scheme: light' in script
