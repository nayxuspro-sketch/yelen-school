"""Tableaux de liste sur téléphone (5.47.0) — garde-fous statiques.

Le repli mobile est **global** : un script pose les libellés de colonnes sur chaque cellule, une règle CSS
transforme la ligne en carte sous 768 px. Ces tests vérifient que la mécanique reste branchée et que les
matrices (statistiques, bulletins, emplois du temps) en sont exclues — sans quoi une matrice deviendrait
illisible en cartes.
"""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def test_le_script_de_repli_mobile_est_charge_avec_le_nonce_csp():
    base = (RACINE / 'core' / 'templates' / 'core' / 'base.html').read_text(encoding='utf-8')
    ligne = [l for l in base.splitlines() if 'js/tableaux_mobile.js' in l]
    assert len(ligne) == 1, 'le script des tableaux mobiles est absent ou chargé deux fois'
    assert 'nonce="{{ request.csp_nonce }}"' in ligne[0]


def test_la_regle_css_ne_s_active_que_sur_les_tableaux_marques():
    css = (RACINE / 'static' / 'css' / 'yelen.css').read_text(encoding='utf-8')
    assert 'table[data-cartes="oui"]' in css
    assert '@media (max-width: 768px)' in css.split('table[data-cartes="oui"]', 1)[0][-400:]
    # Impression : retour à la forme tabulaire, pour les listes à signer.
    assert '@media print' in css and 'table[data-cartes="oui"] { display: table;' in css


def test_les_matrices_ne_sont_pas_converties_en_cartes():
    script = (RACINE / 'static' / 'js' / 'tableaux_mobile.js').read_text(encoding='utf-8')
    assert "'table-stats'" in script and "'edt-table'" in script      # matrices écartées par classe
    assert "data-cartes') === 'non'" in script                        # ou par attribut explicite
    assert 'COLONNES_MAX' in script                                   # garde-fou de largeur

    bulletins = (RACINE / 'bulletins' / 'templates' / 'bulletins' / 'index.html').read_text(encoding='utf-8')
    assert 'data-cartes="non"' in bulletins, 'la matrice classes × trimestres doit rester un tableau'


def test_le_script_ne_modifie_pas_le_contenu_des_cellules():
    script = (RACINE / 'static' / 'js' / 'tableaux_mobile.js').read_text(encoding='utf-8')
    # Seuls des attributs sont posés : aucun innerHTML, aucun remplacement de texte.
    assert 'innerHTML' not in script
    assert "setAttribute('data-label'" in script and "setAttribute('data-titre'" in script
