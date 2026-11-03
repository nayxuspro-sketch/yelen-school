"""Garde-fous d'architecture modulaire (P1-8 / P2-16b).

Garantit :
- qu'aucun module Python applicatif (hors ``migrations/`` et ``tests/``) n'atteint 1 000 lignes ;
- que ``core/templates/core/base.html`` délègue la barre latérale à ``partials/sidebar.html``
  et reste sous 500 lignes sans ``style=`` inline ;
- que les façades de ré-export des 5 paquets découpés restent rétrocompatibles.
"""
from pathlib import Path

from django.conf import settings


EXCLUDED_DIRS = {
    '.git', '.venv', 'venv', 'env', '__pycache__', 'node_modules',
    'staticfiles', 'media', 'migrations', 'tests',
}


def test_aucun_module_applicatif_ne_depasse_999_lignes():
    base_dir = Path(settings.BASE_DIR)
    trop_longs = []
    for py_file in sorted(base_dir.rglob('*.py')):
        rel = py_file.relative_to(base_dir)
        if any(part in EXCLUDED_DIRS or part.startswith('.') for part in rel.parts):
            continue
        if rel.name.startswith('test_') or rel.name == 'conftest.py':
            continue
        nb_lignes = sum(1 for _ in py_file.open(encoding='utf-8'))
        if nb_lignes >= 1000:
            trop_longs.append(f'{rel}: {nb_lignes} lignes')
    assert not trop_longs, f'Modules applicatifs >= 1 000 lignes : {trop_longs}'


def test_base_html_delegue_sidebar_sans_style_inline():
    base_dir = Path(settings.BASE_DIR)
    base_html = base_dir / 'core' / 'templates' / 'core' / 'base.html'
    sidebar_html = base_dir / 'core' / 'templates' / 'core' / 'partials' / 'sidebar.html'

    assert sidebar_html.is_file()
    contenu_base = base_html.read_text(encoding='utf-8')
    contenu_sidebar = sidebar_html.read_text(encoding='utf-8')

    assert "{% include 'core/partials/sidebar.html' %}" in contenu_base
    assert len(contenu_base.splitlines()) < 500
    assert 'style=' not in contenu_base
    assert 'style=' not in contenu_sidebar


def test_facades_retrocompatibles_des_paquets_decoupes():
    from communication import views as comm_views
    from core import chatbot
    from finances import models as fin_models
    from licences import models as lic_models
    from personnel import views as pers_views

    for symbole in ('Licence', 'LicenceActivation', 'LicenceAuditLog', 'LicenceAlert', 'FEATURE_FLAGS'):
        assert hasattr(lic_models, symbole), f'licences.models.{symbole} manquant'
    for symbole in ('Paiement', 'Echeancier', 'Depense', 'ClotureCaisse', 'CODES_RUBRIQUE_SERVICE'):
        assert hasattr(fin_models, symbole), f'finances.models.{symbole} manquant'
    for symbole in ('chat', '_process', '_search_guide', '_req_effectifs', '_GUIDE_KB'):
        assert hasattr(chatbot, symbole), f'core.chatbot.{symbole} manquant'
    for symbole in ('personnel_list', 'personnel_detail', 'paie_mois', 'conge_list', 'absence_list'):
        assert hasattr(pers_views, symbole), f'personnel.views.{symbole} manquant'
    for symbole in ('message_list', 'webhook_incoming_sms', 'campagne_list', 'messages_recus', 'commandes_sms'):
        assert hasattr(comm_views, symbole), f'communication.views.{symbole} manquant'
