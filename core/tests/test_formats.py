"""Lisibilité des nombres : milliers groupés à la française (« 150 000 ») partout où un montant est affiché."""
import re
from pathlib import Path

from core.utils import fcfa

RACINE = Path(__file__).resolve().parents[2]
EXCLUS = {'tests', 'migrations', 'scripts', 'staticfiles', 'node_modules'}


def test_fcfa_groupe_les_milliers_a_la_francaise():
    assert fcfa(150000) == '150\xa0000 FCFA'
    assert fcfa('2500.00') == '2\xa0500 FCFA' and fcfa(999) == '999 FCFA' and fcfa(None) == '0 FCFA'


def test_aucun_montant_affiche_sans_separateur_de_milliers():
    """Gabarits : ``floatformat:0`` doit être ``floatformat:"0g"`` (sauf dans un attribut numérique value / min / max,
    qui doit rester brut) ; code Python : plus de ``:,.0f`` suivi de FCFA (groupement anglais « 150,000 »)."""
    fautifs = []
    for gabarit in RACINE.rglob('templates/**/*.html'):
        for i, ligne in enumerate(gabarit.read_text(encoding='utf-8').splitlines(), 1):
            if re.search(r'\|floatformat:(0|"0")(?=[ |}])', ligne) and not re.search(r'(value|min|max)="[^"]*floatformat', ligne):
                fautifs.append(f'{gabarit.relative_to(RACINE)}:{i}')
    for source in RACINE.rglob('*.py'):
        if EXCLUS & set(source.parts):
            continue
        for i, ligne in enumerate(source.read_text(encoding='utf-8').splitlines(), 1):
            if re.search(r':,\.0f\} ?F ?CFA', ligne):
                fautifs.append(f'{source.relative_to(RACINE)}:{i}')
    assert fautifs == []
