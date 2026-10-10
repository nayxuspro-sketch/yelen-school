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


# ── Barre d'actions groupées (templates/partials/bulk_actions.html) ──────────────────────
# Les cases à cocher portaient onchange="toggleBulkBar()" (bloqué) et la barre embarquait son
# propre <script> : rejoué à chaque échange HTMX avec un nonce différent, donc bloqué lui aussi.
# Le comportement vit désormais dans csp_handlers.js (délégation .bulk-checkbox / data-csp-action).

def test_barre_actions_groupees_sans_script_ni_gestionnaire_inline():
    partiel = (RACINE / 'templates/partials/bulk_actions.html').read_text(encoding='utf-8')
    assert '<script' not in partiel and not re.search(r'\son[a-z]+="', partiel)
    assert partiel.count('data-csp-action="bulk-select-all"') == 1
    assert partiel.count('data-csp-action="bulk-deselect-all"') == 1
    assert partiel.count('data-csp-action="bulk-export" data-export-url="{{ export_url }}"') == 1
    assert 'id="bulk-actions-bar" class="card bulk-actions-bar" hidden' in partiel

    fautifs = [
        str(f.relative_to(RACINE)) for f in _gabarits()
        if 'toggleBulkBar' in f.read_text(encoding='utf-8')
        or re.search(r'class="bulk-checkbox"[^>]*\son[a-z]+=', f.read_text(encoding='utf-8'))
    ]
    assert fautifs == [], fautifs

    js = (RACINE / 'static/js/csp_handlers.js').read_text(encoding='utf-8')
    for attendu in ("case 'bulk-select-all':", "case 'bulk-deselect-all':", "case 'bulk-export':",
                    "sel.classList.contains('bulk-checkbox')", "'.bulk-checkbox[value]:checked'"):
        assert attendu in js, attendu
