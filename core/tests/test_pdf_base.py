"""Socle PDF (templates/pdf/base.html) : squelette et en-tête établissement partagés par tous les gabarits PDF.

Garde-fous :
- chaque gabarit PDF hérite du socle (pas de squelette HTML ni de <style> privé) ;
- toute référence ``identite.<attr>`` désigne un vrai attribut d'IdentiteEtablissement (plus de champs fantômes) ;
- l'en-tête rend l'identité complète, se replie sur l'établissement, et ne fuit jamais « None ».
"""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string

from parametres.models import IdentiteEtablissement

RACINE = Path(__file__).resolve().parents[2]
EXCLUS = {'staticfiles', 'node_modules', '.venv', 'venv'}
SOCLES = ('{% extends "pdf/base.html" %}', '{% extends "pdf/base_rapport.html" %}')


def _gabarits_pdf():
    for f in RACINE.rglob('templates/**/*.html'):
        if EXCLUS.intersection(f.parts) or 'templates/pdf/' in f.as_posix() or '/partials/' in f.as_posix():
            continue  # socle et fragments inclus : pas des documents
        if '/pdf/' in f.as_posix() or f.name.endswith('_pdf.html'):
            yield f


def test_tous_les_gabarits_pdf_heritent_du_socle():
    fautifs = []
    for f in _gabarits_pdf():
        s = f.read_text(encoding='utf-8')
        if not s.startswith(SOCLES):
            fautifs.append(f'{f.relative_to(RACINE)} : pas d\'extends du socle en ligne 1')
        for motif in ('<!DOCTYPE', '<html', '<head', '<body', '<style'):
            if motif.lower() in s.lower():
                fautifs.append(f'{f.relative_to(RACINE)} : {motif} (squelette/CSS hors des blocs du socle)')
    assert list(_gabarits_pdf()), 'aucun gabarit PDF trouvé'
    assert not fautifs, '\n'.join(fautifs)


def test_references_identite_existantes():
    """`identite.xxx` dans un gabarit doit être un champ ou un get_xxx_display réel (sinon rendu silencieusement vide)."""
    champs = {f.name for f in IdentiteEtablissement._meta.get_fields()}
    valides = champs | {f'get_{f.name}_display' for f in IdentiteEtablissement._meta.fields if f.choices}
    fautifs = [
        f'{f.relative_to(RACINE)} : identite.{attr}'
        for f in RACINE.rglob('templates/**/*.html')
        if not EXCLUS.intersection(f.parts)
        for attr in set(re.findall(r'\bidentite\.([A-Za-z_]+)', f.read_text(encoding='utf-8')))
        if attr not in valides
    ]
    assert not fautifs, '\n'.join(fautifs)


def _identite(**extra):
    base = dict(
        nom_etablissement='Complexe Scolaire Le Savoir', sigle='CSLS', type_etablissement='PRIVE_LAIC',
        numero_agrement_mena='2019-0123/MENAPLN', adresse_complete='Secteur 15', ville='Ouagadougou',
        telephone='+226 25 00 00 00', email='contact@lesavoir.bf',
    )
    base.update(extra)
    return IdentiteEtablissement(**base)


@pytest.mark.django_db
def test_entete_rend_identite_complete():
    html = render_to_string('pdf/base.html', {
        'identite': _identite(), 'logo_url': '/media/logo.png',
    })
    for attendu in ('COMPLEXE SCOLAIRE LE SAVOIR'.title(), 'N° Agrément : 2019-0123/MENAPLN', 'CSLS',
                    'Secteur 15', '<strong>Ouagadougou</strong>', '+226 25 00 00 00', 'contact@lesavoir.bf',
                    'src="/media/logo.png"', 'class="pdf-entete"'):
        assert attendu in html, attendu
    assert 'None' not in html


def test_entete_sans_identite_se_replie_sur_etablissement():
    etab = SimpleNamespace(nom='LE SAVOIR', adresse='Secteur 15', ville='Ouaga 2000', telephone='70 00 00 00', email='')
    html = render_to_string('pdf/base.html', {'etablissement': etab})
    assert 'LE SAVOIR' in html and 'Secteur 15' in html and 'Ouaga 2000' in html and '70 00 00 00' in html
    assert 'N° Agrément' not in html and 'None' not in html
    assert 'YELEN SCHOOL' not in html


def test_entete_sans_contexte_ne_plante_pas():
    html = render_to_string('pdf/base.html', {})
    assert 'YELEN SCHOOL' in html and 'None' not in html
    assert '<img' not in html


def test_variante_compacte():
    html = render_to_string('pdf/partials/entete.html', {'identite': _identite(), 'compacte': True})
    assert 'class="pdf-entete pdf-entete-compacte"' in html
