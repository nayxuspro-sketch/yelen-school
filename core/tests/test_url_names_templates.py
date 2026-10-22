"""Tout `{% url 'nom' %}` des gabarits doit désigner une route existante (sinon : erreur 500 au rendu)."""
import re
from pathlib import Path

from django.conf import settings
from django.urls import get_resolver

MOTIF_URL = re.compile(r"""{%\s*url\s+['"]([^'"]+)['"]""")
EXCLUS = ('.git', 'node_modules', 'staticfiles', '.venv')


def _noms_connus(resolver, prefixe=''):
    noms = set()
    for motif in resolver.url_patterns:
        if hasattr(motif, 'url_patterns'):
            noms |= _noms_connus(motif, prefixe + (motif.namespace + ':' if motif.namespace else ''))
        elif motif.name:
            noms.add(prefixe + motif.name)
    return noms


def test_noms_d_url_des_gabarits_existent():
    connus = _noms_connus(get_resolver())
    inconnus = []
    for gabarit in Path(settings.BASE_DIR).rglob('*.html'):
        if any(partie in EXCLUS for partie in gabarit.parts):
            continue
        texte = gabarit.read_text(encoding='utf-8', errors='ignore')
        for m in MOTIF_URL.finditer(texte):
            if m.group(1) not in connus:
                ligne = texte.count('\n', 0, m.start()) + 1
                inconnus.append(f"{gabarit.relative_to(settings.BASE_DIR)}:{ligne} → '{m.group(1)}'")
    assert not inconnus, "Noms d'URL introuvables :\n" + "\n".join(inconnus)
