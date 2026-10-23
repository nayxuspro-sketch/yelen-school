"""Aide en ligne : rendu du guide d'utilisation, ancres contextuelles, captures d'écran, repli."""
import re
from pathlib import Path

import pytest
from django.urls import reverse
from model_bakery import baker

from core import aide

RACINE = Path(__file__).resolve().parents[2]


@pytest.fixture
def connecte(db, client, settings):
    settings.TWO_FACTOR_REQUIRED = False
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='SECRETAIRE', etablissement=etab, must_change_password=False))
    return client


def _ids(html):
    return set(re.findall(r'<h[1-6] id="([^"]+)"', html))


def test_slug_identique_a_github():
    assert aide.slug_github("9. FINANCES ET SCOLARITÉ") == '9-finances-et-scolarité'
    assert aide.slug_github("2. Paramètres de l'Établissement") == '2-paramètres-de-létablissement'
    assert aide.slug_github('29. Communication Bidirectionnelle Établissement ↔ Parent') == \
        '29-communication-bidirectionnelle-établissement--parent'


def test_guide_rendu_complet_et_ancres_du_sommaire_resolues():
    html, sommaire = aide.rendre_guide()
    ids = _ids(html)
    # Chaque titre de niveau 2/3 du Markdown devient un titre HTML (aucun avalé par un bloc de code ouvert).
    for ligne in aide.GUIDE.read_text(encoding='utf-8').splitlines():
        m = re.match(r'^#{2,3} (.+?)\s*$', ligne)
        if m:
            assert aide.slug_github(m.group(1)) in ids, ligne
    # Les ancres du plan contextuel et du sommaire latéral existent dans le document.
    for _prefixe, ancre in aide.SECTIONS:
        assert ancre in ids, ancre
    assert aide.ANCRE_ACCUEIL in ids and aide.ANCRE_SOMMAIRE in ids
    assert all(s['id'] in ids for s in sommaire)
    assert len([s for s in sommaire if s['level'] == 2]) >= 30
    assert 'version_guide' not in html  # en-tête YAML non affiché


def test_ancre_contextuelle_par_module():
    assert aide.ancre_pour('/') == aide.ANCRE_ACCUEIL
    assert aide.ancre_pour('/finances/paiements/') == '9-finances-et-scolarité'
    assert aide.ancre_pour('/presences/appel/') == '7-présences-et-absences'
    assert aide.ancre_pour('/inconnu/') == aide.ANCRE_SOMMAIRE


def test_page_aide_avec_sommaire_et_lien_du_menu(connecte):
    page = connecte.get(reverse('presences:appel_list')).content.decode()
    assert f'href="{reverse("core:aide")}#7-présences-et-absences"' in page

    page = connecte.get(reverse('core:aide')).content.decode()
    assert '<h2 id="9-finances-et-scolarité">' in page
    assert 'id="aide-sommaire-liste"' in page and 'data-section="9-finances-et-scolarité"' in page
    assert reverse('licences:guide') in page
    assert 'src="screenshots/01-login.png"' in page


def test_page_aide_exige_connexion(client):
    assert client.get(reverse('core:aide')).status_code == 302
    assert client.get(reverse('core:aide_capture', args=['01-login.png'])).status_code == 302


def test_captures_servies_sans_traversee(connecte):
    reponse = connecte.get(reverse('core:aide_capture', args=['01-login.png']))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'image/png'
    reponse.close()
    assert connecte.get('/aide/screenshots/..%2F..%2Fmanage.py').status_code == 404
    assert connecte.get(reverse('core:aide_capture', args=['inexistant.png'])).status_code == 404
    # Toutes les images du guide sont présentes.
    for nom in re.findall(r'!\[[^\]]*\]\(screenshots/([^)]+)\)', aide.GUIDE.read_text(encoding='utf-8')):
        assert (aide.CAPTURES / nom).is_file(), nom


def test_repli_si_guide_absent(connecte, tmp_path, monkeypatch):
    monkeypatch.setattr(aide, 'GUIDE', tmp_path / 'absent.md')
    page = connecte.get(reverse('core:aide'))
    assert page.status_code == 200 and "n'est pas présent sur ce serveur" in page.content.decode()


def test_guide_et_captures_embarques_dans_l_image_docker():
    regles = (RACINE / '.dockerignore').read_text().splitlines()
    assert 'docs/*' in regles and '!docs/GUIDE_UTILISATION_YELEN_SCHOOL.md' in regles and '!docs/screenshots' in regles
    assert 'docs/' not in regles
