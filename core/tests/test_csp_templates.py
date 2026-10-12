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


def test_page_autonome_utilisant_data_csp_charge_csp_handlers():
    """Une page complète (hors base.html) qui s'appuie sur des attributs data-csp-* doit charger
    csp_handlers.js, sinon ses boutons sont inertes (ex. « Imprimer » de la liste des appels)."""
    fautifs = [
        str(f.relative_to(RACINE))
        for f in _gabarits()
        for s in [f.read_text(encoding='utf-8')]
        if '<!DOCTYPE' in s and 'data-csp-' in s and 'csp_handlers.js' not in s
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


# ── Aperçus d'images et champs conditionnels (lot B) ─────────────────────────────────────
# identite_etablissement.html et etablissements/detail.html embarquaient un <script> sans nonce
# (previewImage jamais définie) et des onchange / onmouseover inline ; classe_form.html basculait
# les champs d'examen par un onchange. Tout passe par csp_handlers.js (data-csp-preview-image,
# data-csp-toggle-target) et par le CSS (.logo-dropzone:hover).

def test_apercus_images_et_bascule_examen_sans_inline():
    fichiers = {
        'parametres/templates/parametres/identite_etablissement.html': 3,
        'etablissements/templates/etablissements/detail.html': 1,
    }
    for chemin, nb in fichiers.items():
        html = (RACINE / chemin).read_text(encoding='utf-8')
        assert '<script' not in html and 'previewImage' not in html, chemin
        assert not re.search(r'\son[a-z]+="', html), chemin
        assert html.count('data-csp-preview-image="') == nb, chemin

    classe_form = (RACINE / 'parametres/templates/parametres/partials/classe_form.html').read_text(encoding='utf-8')
    assert 'data-csp-toggle-target="exam-fields"' in classe_form and 'onchange=' not in classe_form

    js = (RACINE / 'static/js/csp_handlers.js').read_text(encoding='utf-8')
    for attendu in ('sel.dataset.cspToggleTarget', 'sel.dataset.cspPreviewImage', 'sel.dataset.previewReveal',
                    'sel.dataset.previewConceal'):
        assert attendu in js, attendu
    css = (RACINE / 'static/css/yelen.css').read_text(encoding='utf-8')
    assert '.logo-dropzone:hover' in css


def test_formulaires_bourses_sans_gestionnaire_inline():
    """Les scripts des formulaires de bourse portent le nonce et câblent eux-mêmes leurs écouteurs."""
    attendus = {
        'finances/templates/finances/type_bourse_form.html': (
            "addEventListener('change', majValeur)", "addEventListener('input', majApercu)", 'toUpperCase()'),
        'finances/templates/finances/bourse_form.html': ("sel.addEventListener('change', calculerMontant)",),
    }
    for chemin, fragments in attendus.items():
        html = (RACINE / chemin).read_text(encoding='utf-8')
        assert not re.search(r'\son[a-z]+="', html), chemin
        assert html.count('<script') == 1 and '<script nonce="{{ request.csp_nonce }}">' in html, chemin
        for fragment in fragments:
            assert fragment in html, (chemin, fragment)


def test_selecteurs_de_classe_et_appels_sans_inline():
    """Lot D : sélecteurs ?classe= en formulaire GET, scripts et styles de page noncés, écouteurs câblés."""
    gabarits = {
        'documents/templates/documents/convocation_form.html': ('class="convocation-eleve"',),
        'viescolaire/templates/viescolaire/sanction_create.html': (),
        'viescolaire/templates/viescolaire/appel_decision_traiter.html': (
            "forEach(inp => inp.addEventListener('change', toggleNouvelleDecision))",),
        'presences/templates/presences/appel_saisie.html': (
            "document.getElementById('appel-form').addEventListener('change', updateCounts);",),
    }
    for chemin, fragments in gabarits.items():
        html = (RACINE / chemin).read_text(encoding='utf-8')
        assert not re.search(r'\son[a-z]+="', html), chemin
        assert 'location.href' not in html, chemin
        balises = re.findall(r'<(?:script|style)\b[^>]*>', html)
        assert all('nonce="{{ request.csp_nonce }}"' in b for b in balises), (chemin, balises)
        for fragment in fragments:
            assert fragment in html, (chemin, fragment)
    for chemin in ('documents/templates/documents/convocation_form.html',
                   'viescolaire/templates/viescolaire/sanction_create.html'):
        html = (RACINE / chemin).read_text(encoding='utf-8')
        assert html.count('<form method="get"') == 1 and 'name="classe"' in html, chemin
        assert 'data-csp-submit-on-change' in html, chemin
    assert '.convocation-eleve:hover' in (RACINE / 'static/css/yelen.css').read_text(encoding='utf-8')


# Gabarits PDF (WeasyPrint, sans CSP) et gabarits jamais rendus : hors du périmètre du garde-fou ci-dessous.
_HORS_CSP = (
    '/pdf/', '_pdf.html', 'bulletin_base.html', 'static/img/',
    'templates/500.html',                                 # rendu sans request : pas de nonce possible
)
_BALISE = re.compile(r'<(script|style)\b([^>]*)>', re.I)


def test_scripts_et_styles_de_page_portent_le_nonce():
    """Tout <script> inline ou <style> d'un gabarit servi doit porter le nonce, sinon la CSP le bloque."""
    fautifs = []
    for chemin in _gabarits():
        rel = chemin.relative_to(RACINE).as_posix()
        if any(motif in rel for motif in _HORS_CSP):
            continue
        html = chemin.read_text(encoding='utf-8')
        for balise, attrs in _BALISE.findall(html):
            if balise.lower() == 'script' and ('src=' in attrs or 'application/json' in attrs):
                continue
            if 'nonce="{{ request.csp_nonce }}"' not in attrs:
                fautifs.append(f'{rel} : <{balise}{attrs}>')
        if 'hx-on:' in html:
            fautifs.append(f'{rel} : hx-on (évalué, interdit par la CSP)')
    assert not fautifs, '\n'.join(fautifs)


def test_aucun_gestionnaire_inline_genere_par_les_formulaires():
    for py in RACINE.glob('*/forms.py'):
        assert not re.search(r"""['"]on[a-z]+['"]\s*:""", py.read_text(encoding='utf-8')), py.name
