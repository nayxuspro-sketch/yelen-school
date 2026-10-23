"""Aucun `except Exception` silencieux dans le code applicatif.

Un gestionnaire qui capture `Exception` (ou tout, avec `except:`) doit soit
relancer, soit journaliser (`logger.*`, `logging.*`, `self.stderr/stdout`,
`warnings.warn`, `print`). Sinon, une erreur réelle (SMS, licence, PDF…)
disparaît sans trace — voir audit du 23/10/2026.
"""
import ast
from pathlib import Path

from django.conf import settings

RACINE = Path(__file__).resolve().parents[2]
DOSSIERS_IGNORES = {
    '.git', '.claude', '.venv', 'venv', 'node_modules', 'staticfiles', 'migrations', 'tests',
    'build', 'dist', '__pycache__',
}
FICHIERS_IGNORES = {'conftest.py', 'tests.py'}
LARGES = {'Exception', 'BaseException'}
METHODES_JOURNAL = {'exception', 'error', 'warning', 'critical', 'info', 'debug', 'log', 'write', 'warn'}


def _fichiers_python():
    for chemin in RACINE.rglob('*.py'):
        rel = chemin.relative_to(RACINE)
        if DOSSIERS_IGNORES & set(rel.parts[:-1]):
            continue
        if chemin.name in FICHIERS_IGNORES or chemin.name.startswith('test_'):
            continue
        yield chemin


def _capture_large(handler):
    t = handler.type
    if t is None:
        return True
    noms = t.elts if isinstance(t, ast.Tuple) else [t]
    return any(isinstance(n, ast.Name) and n.id in LARGES for n in noms)


def _signale(handler):
    for noeud in ast.walk(handler):
        if isinstance(noeud, ast.Raise):
            return True
        if isinstance(noeud, ast.Call):
            f = noeud.func
            if isinstance(f, ast.Name) and f.id == 'print':
                return True
            if isinstance(f, ast.Attribute) and f.attr in METHODES_JOURNAL:
                return True
    return False


def test_aucun_except_exception_silencieux():
    silencieux = []
    for chemin in _fichiers_python():
        arbre = ast.parse(chemin.read_text(encoding='utf-8'), filename=str(chemin))
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.ExceptHandler) and _capture_large(noeud) and not _signale(noeud):
                silencieux.append(f'{chemin.relative_to(RACINE)}:{noeud.lineno}')
    assert not silencieux, 'except Exception sans journalisation ni raise :\n  ' + '\n  '.join(silencieux)


def test_journaux_applicatifs_relies_a_un_fichier():
    """Sans logger racine, `logging.getLogger(__name__)` n'écrit nulle part."""
    racine = settings.LOGGING['root']
    assert {'console', 'file'} <= set(racine['handlers'])
    assert racine['level'] in {'DEBUG', 'INFO', 'WARNING'}
