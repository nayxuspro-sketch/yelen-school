"""Barre latérale : les entrées de chaque sous-menu sont présentées par ordre alphabétique.

Règle demandée le 31/10/2026 (5.45.5) : « dans chaque menu, réorganise l'affichage des sous-menus par ordre
alphabétique ». L'ordre est écrit dans `core/templates/core/base.html` ; ce test le vérifie sur la page
rendue, donc il vaut aussi pour les entrées conditionnelles (droits) et pour les entrées ajoutées plus tard.
"""
import re
import unicodedata

import pytest
from model_bakery import baker

pytestmark = pytest.mark.django_db


def cle_alphabetique(libelle):
    """Ordre alphabétique français : sans accents ni casse, ponctuation ramenée à l'espace."""
    texte = unicodedata.normalize('NFKD', libelle)
    texte = ''.join(c for c in texte if not unicodedata.combining(c)).casefold()
    return re.sub(r'[^a-z0-9]+', ' ', texte).strip()


def sous_menus(page):
    """{identifiant du sous-menu: [libellés dans l'ordre affiché]}."""
    sortie = {}
    for bloc in re.finditer(r'<div id="([\w-]+)-submenu" class="sb-submenu-modern">(.*?)</div>', page, re.S):
        libelles = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', m.group(1))).strip()
                    for m in re.finditer(r'sub-item-dot"></span>(.*?)</a>', bloc.group(2), re.S)]
        sortie[bloc.group(1)] = libelles
    return sortie


@pytest.fixture
def page_menu(client, settings):
    settings.TWO_FACTOR_REQUIRED = False
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='SUPER_ADMIN', etablissement=etab, is_superuser=True,
                                  must_change_password=False))
    return client.get('/').content.decode()


def test_chaque_sous_menu_est_alphabetique(page_menu):
    menus = sous_menus(page_menu)
    assert len(menus) >= 12, sorted(menus)          # Inscriptions, Pédagogie, … Paramètres
    for nom, libelles in menus.items():
        assert libelles, f'{nom} : sous-menu vide dans la page rendue'
        ordre = [cle_alphabetique(libelle) for libelle in libelles]
        assert ordre == sorted(ordre), f'{nom} : {libelles}'


def test_entrees_conditionnelles_presentes_et_rangees(page_menu):
    """Les entrées derrière un droit (ex. « Mes cours », réservé aux enseignants) suivent la même règle."""
    assert sous_menus(page_menu)['presences'] == sorted(
        sous_menus(page_menu)['presences'], key=cle_alphabetique)
    assert 'Élèves' in sous_menus(page_menu)['inscriptions']
