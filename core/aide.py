"""Aide en ligne : le guide d'utilisation (docs/GUIDE_UTILISATION_YELEN_SCHOOL.md) rendu dans
l'application, avec sommaire et ancres compatibles GitHub, plus l'ancre contextuelle par module."""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import markdown
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import render

DOSSIER_DOCS = Path(settings.BASE_DIR) / 'docs'
GUIDE = DOSSIER_DOCS / 'GUIDE_UTILISATION_YELEN_SCHOOL.md'
CAPTURES = DOSSIER_DOCS / 'screenshots'

# Préfixe d'URL → ancre de la section du guide (du plus spécifique au plus général).
SECTIONS = [
    ('/pedagogie/', '6-scolarité-et-notes'),
    ('/bulletins/', '67-bulletins-trimestriels-pdf'),
    ('/presences/', '7-présences-et-absences'),
    ('/examens/', '10-examens'),
    ('/viescolaire/', '8-vie-scolaire'),
    ('/personnel/', '5-gestion-du-personnel'),
    ('/finances/', '9-finances-et-scolarité'),
    ('/vacations/', '11-vacations'),
    ('/communication/', '29-communication-bidirectionnelle-établissement--parent'),
    ('/manuels/', '27-gestion-des-manuels-scolaires'),
    ('/documents/', '12-documents-administratifs'),
    ('/parametres/', '2-paramètres-de-létablissement'),
    ('/licences/', '13-gestion-des-licences-super-admin-uniquement'),
    ('/accounts/', '16-gestion-des-comptes-utilisateurs'),
    ('/pilotage/', '14-tableau-de-bord-direction-pilotage'),
    ('/portail/', '20-portail-parent-pwa'),
]
ANCRE_ACCUEIL = '1-connexion-et-tableau-de-bord'
ANCRE_SOMMAIRE = 'table-des-matières'


def ancre_pour(path):
    """Ancre de la section d'aide correspondant à l'URL courante (sommaire si aucune ne s'applique)."""
    if path == '/':
        return ANCRE_ACCUEIL
    for prefixe, ancre in SECTIONS:
        if path.startswith(prefixe):
            return ancre
    return ANCRE_SOMMAIRE


def slug_github(valeur, separateur='-'):
    """Même règle que GitHub (les liens internes du guide y sont écrits à la main) :
    minuscules, ponctuation retirée, espaces → tirets, accents conservés."""
    valeur = unicodedata.normalize('NFKC', valeur).lower().strip()
    valeur = re.sub(r'[^\w\s-]', '', valeur)
    return re.sub(r'\s', separateur, valeur)


def _sans_en_tete_yaml(texte):
    return re.sub(r'\A\s*---\n.*?\n---\n', '', texte, count=1, flags=re.S)


def _listes_imbriquees(texte):
    """Le guide imbrique ses listes avec 2 espaces (convention GitHub) ; Python-Markdown en exige 4.
    Hors blocs de code, l'indentation des puces est doublée."""
    lignes, dans_code = [], False
    for ligne in texte.split('\n'):
        if re.match(r'^ {0,3}(```|~~~)', ligne):
            dans_code = not dans_code
        elif not dans_code:
            ligne = re.sub(r'^( +)(?=([-*+]|\d+\.) )', lambda m: m.group(1) * 2, ligne)
        lignes.append(ligne)
    return '\n'.join(lignes)


@lru_cache(maxsize=2)
def _rendu(cle_cache):
    md = markdown.Markdown(
        extensions=['toc', 'tables', 'fenced_code', 'sane_lists'],
        extension_configs={'toc': {'slugify': slug_github, 'toc_depth': '2-3'}},
    )
    html = md.convert(_listes_imbriquees(_sans_en_tete_yaml(GUIDE.read_text(encoding='utf-8'))))
    return html, [t for t in md.toc_tokens if t['level'] == 2]


def rendre_guide():
    """(html, sommaire) ou None si le fichier est absent ; recalculé quand le fichier change."""
    if not GUIDE.exists():
        return None
    stat = GUIDE.stat()
    return _rendu((stat.st_mtime_ns, stat.st_size))


@login_required
def aide(request):
    rendu = rendre_guide()
    contexte = dict(zip(('contenu', 'sommaire'), rendu)) if rendu else {}
    return render(request, 'core/aide.html', contexte)


@login_required
def aide_capture(request, nom):
    fichier = CAPTURES / Path(nom).name
    if fichier.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.webp') or not fichier.is_file():
        raise Http404
    return FileResponse(open(fichier, 'rb'))
