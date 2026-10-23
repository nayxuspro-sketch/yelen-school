"""Garde-fous d'accessibilité (WCAG 2.1 A/AA, critères 1.1.1, 1.3.1, 2.4.1, 4.1.2) sur les gabarits
HTML de l'interface et sur le gabarit de base rendu."""
import re
from pathlib import Path

import pytest
from django.urls import reverse
from model_bakery import baker

RACINE = Path(__file__).resolve().parents[2]
EXCLUS = {'staticfiles', 'node_modules', '.venv', 'venv'}


def _gabarits():
    for f in sorted(RACINE.rglob('templates/**/*.html')):
        if EXCLUS.intersection(f.parts) or 'pdf' in f.parts or 'pdf' in f.name:
            continue
        yield f


def _source_sans_scripts(f):
    """Le HTML construit dans les scripts (chaînes JS) n'est pas analysé."""
    return re.sub(r'<script\b.*?</script>', '', f.read_text(encoding='utf-8'), flags=re.I | re.S)


def _a(attrs, nom):
    return re.search(r'(^|\s)' + re.escape(nom) + r'\s*=', attrs, re.I) is not None


def _ligne(s, pos):
    return s[:pos].count('\n') + 1


def _fautifs(regle):
    return [
        f'{f.relative_to(RACINE)}:{_ligne(s, pos)}'
        for f in _gabarits()
        for s in [_source_sans_scripts(f)]
        for pos in regle(s)
    ]


def test_images_avec_alternative_textuelle():
    def regle(s):
        return [m.start() for m in re.finditer(r'<img\b([^>]*)>', s, re.I | re.S) if not _a(m.group(1), 'alt')]
    assert _fautifs(regle) == []


def test_icones_svg_masquees_aux_lecteurs_d_ecran():
    """Un SVG inline est décoratif (aria-hidden) ou nommé (aria-label / role / <title>)."""
    def regle(s):
        fautifs = []
        for m in re.finditer(r'<svg\b([^>]*)>', s, re.I | re.S):
            a = m.group(1)
            if _a(a, 'aria-hidden') or _a(a, 'aria-label') or _a(a, 'aria-labelledby') or _a(a, 'role'):
                continue
            fin = s.find('</svg>', m.end())
            if fin == -1 or '<title' not in s[m.end():fin]:
                fautifs.append(m.start())
        return fautifs
    assert _fautifs(regle) == []


def test_boutons_et_liens_icone_seule_ont_un_nom():
    def regle(s):
        fautifs = []
        for m in re.finditer(r'<(button|a)\b([^>]*)>(.*?)</\1>', s, re.I | re.S):
            attrs, inner = m.group(2), m.group(3)
            if '<svg' not in inner.lower():
                continue
            texte = re.sub(r'<svg\b.*?</svg>', '', inner, flags=re.I | re.S)
            texte = re.sub(r'<[^>]+>|{%.*?%}|{#.*?#}', '', texte, flags=re.S)
            texte = re.sub(r'&\w+;|&#\d+;', 'x', texte)
            if texte.strip():
                continue
            if not (_a(attrs, 'aria-label') or _a(attrs, 'aria-labelledby') or _a(attrs, 'title')):
                fautifs.append(m.start())
        return fautifs
    assert _fautifs(regle) == []


def test_etiquettes_associees_a_leur_champ():
    """Un <label> sans for directement suivi d'un champ exige que ce champ porte un id (ou un nom ARIA)."""
    motif = re.compile(
        r'<label\b([^>]*)>.*?</label>\s*(?:{#.*?#}\s*)?(?:<div\b[^>]*>\s*)?<(?:input|select|textarea)\b([^>]*?)/?>',
        re.I | re.S,
    )

    def regle(s):
        return [
            m.start() for m in motif.finditer(s)
            if not _a(m.group(1), 'for')
            and not re.search(r'type="(hidden|submit|button)"', m.group(2))
            and not (_a(m.group(2), 'id') or _a(m.group(2), 'aria-label') or _a(m.group(2), 'aria-labelledby'))
        ]
    assert _fautifs(regle) == []


def test_modales_declarees_comme_dialogues():
    def regle(s):
        return [m.start() for m in re.finditer(r'<div class="modal-box[^"]*"([^>]*)>', s) if 'role="dialog"' not in m.group(0)]
    assert _fautifs(regle) == []


@pytest.mark.django_db
def test_gabarit_de_base_navigation_clavier(client, settings):
    settings.TWO_FACTOR_REQUIRED = False
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='SUPER_ADMIN', etablissement=etab, is_superuser=True,
                                  must_change_password=False))

    page = client.get('/').content.decode()

    assert page.index('<a href="#main-content" class="skip-link">Aller au contenu</a>') < page.index('<aside id="sidebar"')
    assert '<main class="content" id="main-content" tabindex="-1">' in page
    assert '<nav class="sb-nav-modern" aria-label="Navigation principale">' in page
    assert 'aria-expanded="false" aria-controls="inscriptions-submenu"' in page
    assert 'id="menu-btn" type="button" aria-label="Ouvrir le menu" aria-controls="sidebar" aria-expanded="false"' in page
    assert '<div id="toast-container" aria-live="polite"></div>' in page
    assert 'role="dialog" aria-modal="true" aria-labelledby="confirm-title"' in page


def test_feuille_de_style_focus_et_animations_reduites():
    css = (RACINE / 'static' / 'css' / 'yelen.css').read_text(encoding='utf-8')
    assert '.skip-link:focus' in css
    assert ':focus-visible {' in css
    assert '@media (prefers-reduced-motion: reduce)' in css


@pytest.mark.django_db
def test_page_de_connexion_erreur_annoncee(client):
    reponse = client.post(reverse('accounts:login'), {'username': 'inconnu@yelen.edu', 'password': 'mauvais'})

    assert 'role="alert"' in reponse.content.decode()
