"""Garde-fous CSP sur les gabarits : la CSP (script-src-attr 'none') bloque tout gestionnaire
inline ; les sélecteurs à soumission automatique doivent utiliser data-csp-submit-on-change,
traité par csp_handlers.js (voir yelen_school/csp_middleware.py)."""
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
EXCLUS = {'staticfiles', 'node_modules', '.venv', 'venv'}


def _gabarits():
    for f in RACINE.rglob('*.html'):
        if not EXCLUS.intersection(f.parts):
            yield f


def test_aucune_soumission_de_formulaire_dans_un_onchange_inline():
    fautifs = [
        f"{f.relative_to(RACINE)}:{s[:m.start()].count(chr(10)) + 1}"
        for f in _gabarits()
        for s in [f.read_text(encoding='utf-8')]
        for m in re.finditer(r'onchange="[^"]*\.submit\(\)', s)
    ]
    assert fautifs == [], fautifs


def test_data_csp_submit_on_change_toujours_dans_un_formulaire():
    occurrences, hors_formulaire = 0, []
    for f in _gabarits():
        s = f.read_text(encoding='utf-8')
        for m in re.finditer(r'data-csp-submit-on-change', s):
            occurrences += 1
            avant = s[:m.start()]
            if avant.rfind('<form') <= avant.rfind('</form>'):
                hors_formulaire.append(f"{f.relative_to(RACINE)}:{avant.count(chr(10)) + 1}")
    assert occurrences >= 46 and hors_formulaire == [], hors_formulaire
