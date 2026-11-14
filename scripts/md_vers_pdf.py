"""Compose le guide Markdown de `docs/` en PDF éditorial prêt à imprimer.

Usage :
    python scripts/md_vers_pdf.py [source.md] [sortie.pdf]

Chaîne : Markdown → HTML structuré (couverture, pages liminaires, sommaire paginé,
ouvertures de partie, chapitres, encadrés, tableaux, figures) → WeasyPrint (PDF A4
300 ppp, polices embarquées).

Dépendances : `markdown`, `beautifulsoup4`, `lxml`, `weasyprint` (requirements/dev.txt).
Les polices (Inter, Source Serif 4, JetBrains Mono) sont livrées dans `scripts/guide_pdf/fonts`.
"""
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup, NavigableString
from weasyprint import CSS, HTML

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_pdf.documents import DOCUMENTS  # noqa: E402

ICI = Path(__file__).resolve().parent
GABARIT = ICI / 'guide_pdf'
RACINE = ICI.parent
DOCS = RACINE / 'docs'

# ── Parties du guide (regroupement éditorial des chapitres) ──────────────────
PARTIES = [
    ('I', 'Prise en main', 'Le contexte du produit, la connexion, le tableau de bord et les paramètres '
                           'de l\'établissement : de quoi ouvrir l\'application et la configurer.',
     [1, 2, 3]),
    ('II', 'Élèves, personnel et pédagogie', 'Inscriptions, dossiers du personnel, notes et bulletins, présences '
                                             'et vie scolaire : le cœur du travail quotidien.',
     [4, 5, 6, 7, 8]),
    ('III', 'Argent et évaluation', 'Scolarité, encaissements, dépenses, examens officiels et vacations : '
                                    'tout ce qui se compte et se justifie.', [9, 10, 11]),
    ('IV', 'Documents et pilotage', 'Documents administratifs, licences, statistiques et état des fonctionnalités : '
                                    'les productions et les tableaux de bord de la direction.', [12, 13, 14, 15]),
    ('V', 'Références et interface', 'Questions fréquentes, glossaire et design system : le vocabulaire et les règles '
                                     'graphiques de l\'application.', [16, 17, 18]),
    ('VI', 'Portails, innovations et familles', 'Portail parent, signature électronique, prédiction de réussite, APC/API, '
                                                'bourses, assistant IA, budget, manuels, hors ligne, communication, '
                                                'emploi du temps, localisations.', [19, 20, 21, 22, 23, 24, 25, 26,
                                                                                  27, 28, 29, 30]),
    ('VII', 'Exploitation, sécurité et qualité', 'Mode autonome, SMS des familles, galerie d\'écrans, sécurité, source '
                                                 'de vérité, import de fichiers, services annexes, contrôle qualité et '
                                                 'offre hébergée.', [31, 32, 33, 34, 35, 36, 37, 38, 39]),
    ('VIII', 'Annexes pratiques', 'Exemples de saisie champ par champ : des valeurs réelles à recopier pour chaque '
                                  'formulaire du logiciel.', [40]),
]

ACRONYMES = {
    'YELEN', 'SCHOOL', 'SMS', 'PDF', 'PWA', 'FAQ', 'APC', 'IA', 'QR', 'API', 'HTTP', 'HTTPS', 'CSV', 'JSON',
    'SQL', 'XLSX', 'DOCX', 'UV', 'GPS', 'RGPD', 'AVS', 'FCFA', 'CEP', 'BEPC', 'BAC', 'CEPE', 'PC', 'RH',
    'CA', 'PDF/A',
}

EMOJI = {                                   # pictogramme → icône dessinée
    '\u2705': 'coche', '\u2714': 'coche', '\u2713': 'coche', '\u2611': 'coche',
    '\u274c': 'croix', '\u2717': 'croix', '\u2718': 'croix', '\u2715': 'croix',
    '\u26a0': 'alerte', '\u2757': 'alerte', '\u203c': 'alerte',
    '\U0001f4a1': 'ampoule',
    '\U0001f512': 'cadenas', '\U0001f510': 'cadenas', '\U0001f511': 'cadenas', '\U0001f6e1': 'cadenas',
    '\U0001f4ca': 'graphique', '\U0001f4c8': 'graphique', '\U0001f4c9': 'graphique',
    '\U0001f4c4': 'document', '\U0001f4c3': 'document', '\U0001f4d1': 'document',
    '\U0001f4dc': 'document', '\U0001f9fe': 'document', '\U0001f5a8': 'document',
    '\U0001f4cb': 'blocnotes', '\U0001f5d2': 'blocnotes', '\U0001f4dd': 'blocnotes',
    '\U0001f4d3': 'blocnotes', '\U0001f4cc': 'blocnotes', '\U0001f4ce': 'blocnotes', '\u270f': 'blocnotes',
    '\U0001f393': 'diplome', '\U0001f3c6': 'diplome', '\U0001f947': 'diplome',
    '\U0001f948': 'diplome', '\U0001f949': 'diplome',
    '\U0001f464': 'personne', '\U0001f468': 'personne', '\U0001f3e0': 'personne',
    '\U0001f465': 'personnes', '\U0001f3eb': 'personnes',
    '\U0001f534': 'pastille-rouge', '\U0001f7e0': 'pastille-orange', '\U0001f7e1': 'pastille-orange',
    '\U0001f7e2': 'pastille-verte', '\U0001f535': 'pastille-bleue',
    '\u26ab': 'pastille-encre', '\u26aa': 'pastille-claire',
    '\u2605': 'etoile', '\u2b50': 'etoile', '\u2606': 'etoile',
    '\u27a1': 'fleche', '\u2192': 'fleche', '\u2194': 'fleche', '\u21b3': 'fleche',
    '\U0001f50d': 'loupe', '\U0001f50e': 'loupe',
    '\u26a1': 'eclair', '\U0001f504': 'eclair', '\u21bb': 'eclair',
    '\U0001f4b0': 'argent', '\U0001f4b3': 'argent', '\u2696': 'argent',
    '\U0001f4c5': 'calendrier', '\U0001f5d3': 'calendrier', '\U0001f4c6': 'calendrier',
    '\u23f1': 'horloge', '\u23f3': 'horloge', '\u23f0': 'horloge',
    '\U0001f4ac': 'message', '\U0001f4e8': 'message', '\u2709': 'message',
    '\U0001f4e7': 'message', '\U0001f4de': 'message',
    '\U0001f514': 'cloche',
    '\U0001f522': 'chiffres', '\u2460': 'chiffres', '\u2461': 'chiffres',
    '\u2462': 'chiffres', '\u2463': 'chiffres',
    '\u2753': 'question', '\u2754': 'question',
    '\U0001f916': 'robot',
    '\U0001f5bc': 'image',
    '\u2610': 'case', '\u25cf': 'pastille-encre', '\u25cb': 'pastille-claire',
    # signes purement décoratifs : retirés sans laisser de vide
    '\U0001f6aa': '', '\u2708': '', '\u2702': '', '\U0001f9e9': '', '\u2699': '',
    '\U0001f527': '', '\U0001f3ad': '', '\U0001f4bc': '', '\U0001f517': '', '\u25ba': '', '\u25be': '',
    '\u25bd': '', '\u25bc': '', '\u25b8': '', '\u22ee': '',
    '\u25c0': '', '\u25b6': '', '\u25aa': '', '\u25ab': '', '\U0001f53d': '', '\U0001f53c': '',
}

ICONES = {
    'coche': ('#0E9F66', '<circle cx="12" cy="12" r="9.2" fill="none" stroke="{c}" stroke-width="1.9"/>'
                         '<path d="M7.8 12.3l2.7 2.7 5.7-5.7" fill="none" stroke="{c}" stroke-width="1.9" '
                         'stroke-linecap="round" stroke-linejoin="round"/>'),
    'croix': ('#B23B32', '<circle cx="12" cy="12" r="9.2" fill="none" stroke="{c}" stroke-width="1.9"/>'
                         '<path d="M9 9l6 6M15 9l-6 6" fill="none" stroke="{c}" stroke-width="1.9" '
                         'stroke-linecap="round"/>'),
    'alerte': ('#C58C2A', '<path d="M12 3.6l9.2 16.2H2.8z" fill="none" stroke="{c}" stroke-width="1.8" '
                          'stroke-linejoin="round"/><path d="M12 9.4v4.9" stroke="{c}" stroke-width="1.9" '
                          'stroke-linecap="round"/><circle cx="12" cy="17.2" r="1.05" fill="{c}"/>'),
    'ampoule': ('#067955', '<path d="M12 3.6a6.1 6.1 0 00-3.5 11.1v1.6h7v-1.6A6.1 6.1 0 0012 3.6z" '
                           'fill="none" stroke="{c}" stroke-width="1.7" stroke-linejoin="round"/>'
                           '<path d="M9.4 19h5.2M10.4 21.4h3.2" stroke="{c}" stroke-width="1.7" '
                           'stroke-linecap="round"/>'),
    'cadenas': ('#34506F', '<rect x="4.8" y="10.4" width="14.4" height="9.6" rx="1.8" fill="none" '
                           'stroke="{c}" stroke-width="1.8"/><path d="M8.2 10.4V7.8a3.8 3.8 0 017.6 0v2.6" '
                           'fill="none" stroke="{c}" stroke-width="1.8"/><circle cx="12" cy="15.2" r="1.2" '
                           'fill="{c}"/>'),
    'document': ('#5A6675', '<path d="M6.6 3.6h6.8l4.9 4.9v11.9H6.6z" fill="none" stroke="{c}" '
                            'stroke-width="1.7" stroke-linejoin="round"/><path d="M13.2 3.6v5h5.1" fill="none" '
                            'stroke="{c}" stroke-width="1.7" stroke-linejoin="round"/>'),
    'blocnotes': ('#5A6675', '<rect x="5.4" y="4.6" width="13.2" height="15.8" rx="1.8" fill="none" '
                             'stroke="{c}" stroke-width="1.7"/><path d="M9 4.6V2.9M15 4.6V2.9M9 10h6M9 14h4" '
                             'stroke="{c}" stroke-width="1.7" stroke-linecap="round"/>'),
    'diplome': ('#5A6675', '<path d="M2.8 9.3L12 4.8l9.2 4.5-9.2 4.5z" fill="none" stroke="{c}" '
                           'stroke-width="1.6" stroke-linejoin="round"/><path d="M6.6 11.4v4.4c0 1.6 2.4 2.9 '
                           '5.4 2.9s5.4-1.3 5.4-2.9v-4.4" fill="none" stroke="{c}" stroke-width="1.6"/>'),
    'personne': ('#5A6675', '<circle cx="12" cy="8.3" r="3.6" fill="none" stroke="{c}" stroke-width="1.7"/>'
                            '<path d="M4.9 20.2a7.1 7.1 0 0114.2 0" fill="none" stroke="{c}" stroke-width="1.7" '
                            'stroke-linecap="round"/>'),
    'personnes': ('#5A6675', '<circle cx="9" cy="8.6" r="3.2" fill="none" stroke="{c}" stroke-width="1.7"/>'
                             '<path d="M3 19.6a6 6 0 0112 0" fill="none" stroke="{c}" stroke-width="1.7"/>'
                             '<path d="M15.4 5.9a3.2 3.2 0 010 6M17 19.6a6 6 0 00-1.6-4.1" fill="none" stroke="{c}" '
                             'stroke-width="1.7" stroke-linecap="round"/>'),
    'graphique': ('#5A6675', '<path d="M4 20V4" stroke="{c}" stroke-width="1.7" stroke-linecap="round"/>'
                             '<path d="M4 20h16" stroke="{c}" stroke-width="1.7" stroke-linecap="round"/>'
                             '<rect x="7" y="12.4" width="3" height="5.2" fill="{c}"/>'
                             '<rect x="12" y="8.6" width="3" height="9" fill="{c}"/>'
                             '<rect x="17" y="5.6" width="3" height="12" fill="{c}"/>'),
    'pastille-rouge': ('#C0392B', '<circle cx="12" cy="12" r="5.4" fill="{c}"/>'),
    'pastille-verte': ('#12A06E', '<circle cx="12" cy="12" r="5.4" fill="{c}"/>'),
    'pastille-orange': ('#D89B28', '<circle cx="12" cy="12" r="5.4" fill="{c}"/>'),
    'etoile': ('#B0803A', '<path d="M12 3.4l2.6 5.7 6.2.7-4.6 4.2 1.2 6.1-5.4-3-5.4 3 1.2-6.1L3.2 9.8l6.2-.7z" '
                          'fill="{c}"/>'),
    'pastille-bleue': ('#2E6DA4', '<circle cx="12" cy="12" r="5.4" fill="{c}"/>'),
    'pastille-encre': ('#22303F', '<circle cx="12" cy="12" r="5.4" fill="{c}"/>'),
    'pastille-claire': ('#C9D0D8', '<circle cx="12" cy="12" r="5.4" fill="{c}"/>'),
    'loupe': ('#34506F', '<circle cx="10.6" cy="10.6" r="6" fill="none" stroke="{c}" stroke-width="1.8"/>'
                         '<path d="M15 15l5 5" stroke="{c}" stroke-width="1.9" stroke-linecap="round"/>'),
    'eclair': ('#C58C2A', '<path d="M13.4 2.8L6 13.4h4.6l-1 7.8 7.7-11h-4.7z" fill="none" stroke="{c}" '
                          'stroke-width="1.6" stroke-linejoin="round"/>'),
    'argent': ('#067955', '<circle cx="12" cy="12" r="8.6" fill="none" stroke="{c}" stroke-width="1.7"/>'
                          '<path d="M14.8 8.8a3.6 3.6 0 00-5.6 1.6c-.7 1.7.5 3.5 2.2 3.9 1.7.4 2.7 2.2 2 3.9" '
                          'fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="round"/>'),
    'calendrier': ('#34506F', '<rect x="4.4" y="5.8" width="15.2" height="13.8" rx="1.6" fill="none" '
                              'stroke="{c}" stroke-width="1.7"/><path d="M4.4 10h15.2M8.6 3.6v3.6M15.4 3.6v3.6" '
                              'stroke="{c}" stroke-width="1.7" stroke-linecap="round"/>'),
    'horloge': ('#34506F', '<circle cx="12" cy="12" r="8.4" fill="none" stroke="{c}" stroke-width="1.7"/>'
                           '<path d="M12 7.6V12l3.2 2" fill="none" stroke="{c}" stroke-width="1.7" '
                           'stroke-linecap="round"/>'),
    'message': ('#34506F', '<path d="M4 5.8h16v10.4H9.4L5 20v-3.8H4z" fill="none" stroke="{c}" '
                           'stroke-width="1.7" stroke-linejoin="round"/>'),
    'cloche': ('#C58C2A', '<path d="M6.6 16.6V11a5.4 5.4 0 0110.8 0v5.6l1.6 2H5z" fill="none" stroke="{c}" '
                          'stroke-width="1.7" stroke-linejoin="round"/><path d="M10.2 20.4a1.9 1.9 0 003.6 0" '
                          'fill="none" stroke="{c}" stroke-width="1.7" stroke-linecap="round"/>'),
    'chiffres': ('#34506F', '<path d="M9.4 5.4l-1.9 13M15.6 5.4l-1.9 13M5.2 9.6h14M4.4 14.4h14" fill="none" '
                            'stroke="{c}" stroke-width="1.7" stroke-linecap="round"/>'),
    'question': ('#34506F', '<circle cx="12" cy="12" r="8.6" fill="none" stroke="{c}" stroke-width="1.7"/>'
                            '<path d="M9.4 9.4a2.7 2.7 0 015.2.9c0 1.9-2.6 2-2.6 4" fill="none" stroke="{c}" '
                            'stroke-width="1.7" stroke-linecap="round"/><circle cx="12" cy="17.2" r="1.1" '
                            'fill="{c}"/>'),
    'robot': ('#34506F', '<rect x="4.4" y="7.4" width="15.2" height="11.2" rx="2.2" fill="none" stroke="{c}" '
                         'stroke-width="1.7"/><path d="M12 3.6v3.8" stroke="{c}" stroke-width="1.7" '
                         'stroke-linecap="round"/><circle cx="9.2" cy="12.6" r="1.2" fill="{c}"/>'
                         '<circle cx="14.8" cy="12.6" r="1.2" fill="{c}"/>'),
    'image': ('#34506F', '<rect x="4" y="5.4" width="16" height="13.2" rx="1.8" fill="none" stroke="{c}" '
                         'stroke-width="1.7"/><circle cx="9" cy="10.2" r="1.6" fill="{c}"/>'
                         '<path d="M4.6 17.4l4.8-4.6 3.4 3.2 2.6-2.4 4 3.8" fill="none" stroke="{c}" '
                         'stroke-width="1.7" stroke-linejoin="round"/>'),
    'case': ('#6C7787', '<rect x="4.6" y="4.6" width="14.8" height="14.8" rx="2" fill="none" stroke="{c}" '
                        'stroke-width="1.7"/>'),
    'fleche': ('#067955', '<path d="M4.5 12h14M13.4 6.9L18.6 12l-5.2 5.1" fill="none" stroke="{c}" '
                          'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>'),
}

MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre',
        'novembre', 'décembre']


# ── Utilitaires ─────────────────────────────────────────────────────────────

def sans_accent(txt):
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')


def ancre(txt, prefixe='', vues=None):
    base = re.sub(r'[^a-z0-9]+', '-', sans_accent(txt).lower()).strip('-')[:60]
    base = f'{prefixe}{base}'
    if vues is None:
        return base
    n = vues.get(base, 0) + 1
    vues[base] = n
    return base if n == 1 else f'{base}-{n}'


def joli_titre(txt):
    """« ÉTAT DES FONCTIONNALITÉS » → « État des fonctionnalités » (sigles et noms propres conservés)."""
    def mot(m):
        t = m.group(0)
        nu = t.strip('()«».!:;,')
        if not nu or nu in ACRONYMES or nu.isdigit() or not nu.isupper():
            return t
        if len(nu) <= 3:                       # petits mots de liaison : « et », « de », « du »
            return t.replace(nu, nu.lower())
        return t.replace(nu, nu[0] + nu[1:].lower())
    return re.sub(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9'’\-]+", mot, txt)


def css_icones():
    """Classes `.ic-<nom>` en images SVG encodées (aucune dépendance réseau)."""
    regles = []
    for nom, (couleur, gabarit) in ICONES.items():
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">'
               f'{gabarit.format(c=couleur)}</svg>')
        regles.append(f'.ic-{nom}{{background-image:url("data:image/svg+xml,{quote(svg, safe="")}")}}')
    return '\n'.join(regles)


def cle_callout(texte, classes):
    t = sans_accent(texte).lower()
    if 'regle de securite' in t or 'interdit' in t or 'danger' in t:
        return 'regle', 'Règle de sécurité', 'cadenas'
    if '⚠' in texte or t.startswith('attention') or 'important' in t or 'avertissement' in t:
        return 'alerte', 'Avertissement', 'alerte'
    if '💡' in texte or t.startswith('astuce') or 'conseil' in t or 'recommand' in t:
        return 'astuce', 'Astuce', 'ampoule'
    if t.startswith('acces') or 'acces :' in t[:40]:
        return 'acces', 'Accès', 'fleche'
    if t.startswith('exemple'):
        return 'note', 'Exemple', 'blocnotes'
    if t.startswith('note') or 'remarque' in t[:30]:
        return 'note', 'Note', 'document'
    return '', '', ''


# ── Lecture du Markdown ─────────────────────────────────────────────────────

def lire_entete(txt):
    m = re.match(r'^---\n(.*?)\n---\n', txt, re.S)
    if not m:
        return {}, txt
    meta = {}
    for ligne in m.group(1).splitlines():
        if ':' in ligne:
            k, v = ligne.split(':', 1)
            meta[k.strip()] = v.strip()
    return meta, txt[m.end():]


def decouper(txt, config):
    """Sépare le Markdown en avant-propos et chapitres, selon le dossier documentaire fourni."""
    entete, corps = lire_entete(txt)
    blocs, courant, tampon = [], None, []
    for ligne in corps.split('\n'):
        m = re.match(r'^##\s+(.*)$', ligne)
        if m:
            if courant is not None:
                courant['md'] = '\n'.join(tampon)
                blocs.append(courant)
            courant = {'titre': m.group(1).strip()}
            tampon = []
        elif courant is not None:
            tampon.append(ligne)
    if courant is not None:
        courant['md'] = '\n'.join(tampon)
        blocs.append(courant)

    avant, chapitres = [], []
    for bloc in blocs:
        titre = bloc['titre']
        if titre in config.get('ignorer', ()):
            continue
        m = re.match(r'^(\d+)[.)]?\s+(.*)$', titre)
        sous = re.match(r'^(\d+)\.\d+\s+(.*)$', titre)
        if sous:
            chapitres.append({'num': None, 'parent': int(sous.group(1)), 'titre': titre,
                              'md': bloc['md'], 'kind': 'sous-chapitre'})
        elif m:
            chapitres.append({'num': int(m.group(1)), 'titre': m.group(2), 'md': bloc['md'], 'kind': 'chapitre'})
        elif titre in config.get('annexes', ()):
            chapitres.append({'num': None, 'titre': titre, 'md': bloc['md'], 'kind': 'annexe'})
        elif chapitres:
            chapitres.append({'num': None, 'titre': titre, 'md': bloc['md'], 'kind': 'annexe'})
        else:
            avant.append(bloc['md'])
    return entete, avant, chapitres


def reparer_listes(markdown_src):
    """Rend lisibles les listes qui contiennent un bloc de code ou un paragraphe indenté.

    python-markdown abandonne une liste dès qu'un contenu indenté atteint exactement la
    largeur du marqueur (« 1. » → 3 espaces) : le point suivant repart alors dans une
    nouvelle liste et le bloc de code sort du cadre. Les continuations sont donc réindentées
    à quatre espaces, et les blocs ``` convertis en jetons réinjectés ensuite en `<pre>`.
    """
    blocs = {}
    lignes = markdown_src.split('\n')
    sortie = []
    indent_liste = None
    i = 0
    while i < len(lignes):
        ligne = lignes[i]
        m_item = re.match(r'^(\s*)(\d+\.|[-*+])\s', ligne)
        if m_item:
            indent_liste = len(m_item.group(1))
            sortie.append(ligne)
            i += 1
            continue

        vide = not ligne.strip()
        indentation = len(ligne) - len(ligne.lstrip(' '))
        if indent_liste is not None and not vide and indentation > indent_liste:
            supplement = indentation - indent_liste
            ligne = ' ' * 4 + ' ' * max(0, supplement - 3) + ligne.lstrip(' ')
            m_bloc = re.match(r'^(\s{4,})```[a-zA-Z0-9]*\s*$', ligne)
            if m_bloc:
                contenu = []
                i += 1
                while i < len(lignes) and not re.match(r'^\s*```\s*$', lignes[i]):
                    contenu.append(lignes[i])
                    i += 1
                i += 1                                 # fermeture du bloc
                jeton = f'YELENBLOC{len(blocs)}CODE'
                corps = '\n'.join(l.strip() for l in contenu)
                corps = corps.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                blocs[jeton] = f'<pre class="code"><code>{corps}</code></pre>'
                sortie.append(' ' * 4 + jeton)
                continue
            sortie.append(ligne)
            i += 1
            continue

        if not vide and indentation <= (indent_liste or 0):
            indent_liste = None
        sortie.append(ligne)
        i += 1

    # une liste collée au paragraphe précédent est avalée par celui-ci : on aère
    aeree = []
    for ligne in sortie:
        if re.match(r'^(\d+\.|[-*+])\s', ligne) and aeree:
            precedente = aeree[-1].strip()
            if precedente and not re.match(r'^(\d+\.|[-*+])\s', aeree[-1]) and not precedente.startswith('|'):
                aeree.append('')
        aeree.append(ligne)
    return '\n'.join(aeree), blocs


def injecter_blocs(html, blocs):
    """Remet les blocs de code à la place de leurs jetons."""
    for jeton, code in blocs.items():
        html = re.sub(rf'<p>\s*{jeton}\s*</p>', lambda _: code, html)
        html = html.replace(jeton, code)
    return html


def md_vers_html(markdown_src):
    import markdown as md_lib
    return md_lib.markdown(
        markdown_src,
        extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list', 'codehilite_marker'],
        extension_configs={},
        output_format='html5',
    )


def remplacer_emoji(soup):
    """Remplace les pictogrammes du texte par de petites icônes vectorielles."""
    for noeud in list(soup.find_all(string=True)):
        txt = str(noeud).replace('\ufe0f', '').replace('\u200d', '')
        if not any(c in EMOJI for c in txt):
            if txt != str(noeud):
                noeud.replace_with(NavigableString(txt))
            continue
        morceaux, tampon = [], ''
        for car in txt:
            if car in EMOJI:
                if tampon:
                    morceaux.append(NavigableString(tampon))
                    tampon = ''
                if EMOJI[car]:
                    morceaux.append(soup.new_tag('span', attrs={'class': f'ic ic-{EMOJI[car]}'}))
            else:
                tampon += car
        if tampon:
            morceaux.append(NavigableString(tampon))
        noeud.replace_with(*morceaux)


def frag_texte(soup, txt):
    return NavigableString(txt)


def _etiquette_entete(premier):
    """Étiquette en tête de paragraphe (« **Astuce :** … », « 💡 … ») → texte et reste du paragraphe."""
    gras = premier.find('strong')
    if gras is not None and premier.contents and premier.contents[0] is gras:
        etiquette = gras.get_text(' ', strip=True).rstrip(':').strip()
        if 0 < len(etiquette) <= 48:
            return etiquette
    return None


def _commence_un_encadre(paragraphe):
    """Un paragraphe ouvre-t-il un encadré autonome (pictogramme ou étiquette en gras) ?"""
    if paragraphe.name != 'p':
        return False
    premier = paragraphe.contents[0] if paragraphe.contents else None
    if isinstance(premier, NavigableString):
        if any(c in EMOJI for c in str(premier)[:3]):
            return True
    elif premier is not None and premier.name == 'strong':
        return _etiquette_entete(paragraphe) is not None
    return False


def _construire_encadre(soup, contenu):
    """Construit un encadré à partir d'une liste de nœuds, en déduisant sa famille."""
    texte = ' '.join(n.get_text(' ', strip=True) for n in contenu)
    classes, label, icone = cle_callout(texte, [])
    div = soup.new_tag('div', attrs={'class': ('callout ' + classes).strip()})
    etiq = None
    if contenu and contenu[0].name == 'p':
        etiq = _etiquette_entete(contenu[0])
        if etiq:
            for enfant in list(contenu[0].contents):
                if enfant is not None and getattr(enfant, 'name', None) == 'strong' and not contenu[0].get_text(strip=True):
                    enfant.extract()
            gras = contenu[0].find('strong')
            if gras is not None:
                gras.extract()
    if label and contenu and contenu[0].name == 'p' and contenu[0].contents:
        tete = contenu[0].contents[0]
        if isinstance(tete, NavigableString):
            nettoye = str(tete).replace('\ufe0f', '')
            for em in list(EMOJI):
                nettoye = nettoye.replace(em, '')
            contenu[0].contents[0].replace_with(NavigableString(nettoye.lstrip()))
    if label:
        entete = soup.new_tag('div', attrs={'class': 'label'})
        entete.append(soup.new_tag('span', attrs={'class': f'ic ic-{icone}'}))
        entete.append(NavigableString(etiq or label))
        div.append(entete)
    elif etiq:
        entete = soup.new_tag('div', attrs={'class': 'label'})
        entete.append(NavigableString(etiq))
        div.append(entete)
    for noeud in contenu:
        div.append(noeud.extract())
    # après retrait de l'étiquette, la phrase reprend par une majuscule
    for paragraphe in div.find_all('p'):
        for enfant in paragraphe.contents:
            if isinstance(enfant, NavigableString) and enfant.strip():
                texte = str(enfant)
                if texte.lstrip()[:1].islower():
                    position = len(texte) - len(texte.lstrip())
                    enfant.replace_with(NavigableString(
                        texte[:position] + texte[position].upper() + texte[position + 1:]))
                break
    for paragraphe in div.find_all('p'):
        if not paragraphe.get_text(strip=True) and not paragraphe.find('img'):
            paragraphe.decompose()
    if not label and not etiq:
        div['class'] = 'citation'
    return div


def traiter_blocquote(bq, soup):
    while bq.find('blockquote'):                       # citations imbriquées (>) : on aplatit
        bq.find('blockquote').unwrap()
    enfants = [n for n in bq.contents if not (isinstance(n, NavigableString) and not n.strip())]
    groupes, courant = [], []
    for noeud in enfants:
        if _commence_un_encadre(noeud) and courant:
            groupes.append(courant)
            courant = [noeud]
        else:
            courant.append(noeud)
    if courant:
        groupes.append(courant)
    if not groupes:
        return
    for groupe in groupes:
        encadre = _construire_encadre(soup, groupe)
        bq.insert_before(encadre)
    bq.decompose()


def traiter_figure(img, soup, etat):
    """Encadre une capture dans une figure légendée et numérotée (index des figures)."""
    etat['figures'] += 1
    num = etat['figures']
    img['id'] = f'fig-{num}'
    src = img.get('src', '')
    if not src.startswith('/'):
        img['src'] = str((DOCS / src).resolve())
    alt = img.get('alt', '').strip()
    figure = soup.new_tag('figure')
    cible = img.parent if (img.parent is not None and img.parent.name in ('p', 'div')
                           and not img.parent.get_text(strip=True)) else img
    cible.insert_before(figure)
    figure.append(img.extract())
    legende = soup.new_tag('figcaption')
    fort = soup.new_tag('b')
    fort.string = f'Figure {num} — '
    legende.append(fort)
    legende.append(NavigableString(alt))
    figure.append(legende)
    etat['liste_figures'].append((num, alt, f'fig-{num}'))
    if cible is not img and cible.parent is not None:
        cible.decompose()
    return figure


def traiter_fragment(html, etat):
    soup = BeautifulSoup(html, 'lxml')
    corps = soup.body or soup
    for bq in corps.find_all('blockquote'):
        if bq.parent is not None:
            traiter_blocquote(bq, soup)
    remplacer_emoji(corps)
    vues = {}
    for titre in corps.find_all(['h3', 'h4', 'h5']):
        txt = titre.get_text(' ', strip=True)
        tid = ancre(txt, vues=vues)
        titre['id'] = tid
        if titre.name == 'h3':
            etat['sections'].append((txt, tid))
    for paragraphe in corps.find_all('p'):
        txt = paragraphe.get_text(' ', strip=True)
        if txt.startswith('--- '):
            for enfant in list(paragraphe.contents):
                if isinstance(enfant, NavigableString) and '---' in enfant:
                    enfant.replace_with(NavigableString(str(enfant).replace('---', '', 1).lstrip()))
                    break
            paragraphe['class'] = 'exergue'
    for paragraphe in corps.find_all('p'):
        txt = paragraphe.get_text(' ', strip=True)
        if 'screenshots' in txt and 'référencées dans chaque section' in txt:
            paragraphe.decompose()
    for table in corps.find_all('table'):
        if table.parent is not None and not (table.parent.name == 'div' and 'table-wrap' in table.parent.get('class', [])):
            wrap = soup.new_tag('div', attrs={'class': 'table-wrap'})
            table.wrap(wrap)
    for pre in corps.find_all('pre'):
        pre['class'] = pre.get('class', []) + ['code']
    return corps.decode_contents()


def traiter_images(html, etat):
    soup = BeautifulSoup(html, 'lxml')
    corps = soup.body or soup
    for img in list(corps.find_all('img')):
        traiter_figure(img, soup, etat)
    return corps.decode_contents()


def _brief(html):
    """Transforme une suite d'encadrés étiquetés en un tableau de synthèse compact (avant-propos)."""
    soup = BeautifulSoup(html, 'lxml')
    corps = soup.body or soup
    encadres = corps.find_all('div', class_='callout')
    if len(encadres) < 2:
        return html
    table = soup.new_tag('table', attrs={'class': 'brief'})
    for encadre in encadres:
        etiquette = encadre.find('div', class_='label')
        libelle = etiquette.get_text(' ', strip=True) if etiquette else ''
        if etiquette:
            etiquette.decompose()
        ligne = soup.new_tag('tr')
        cap = soup.new_tag('th')
        cap.string = libelle
        cellule = soup.new_tag('td')
        for enfant in list(encadre.contents):
            cellule.append(enfant.extract())
        ligne.append(cap)
        ligne.append(cellule)
        table.append(ligne)
        encadre.decompose()
    cadre = soup.new_tag('div', attrs={'class': 'brief-cadre'})
    cadre.append(table)
    corps.insert(0, cadre)
    return corps.decode_contents()


def _figures_index(etat):
    """Sommaire des illustrations (captures et schémas), avec la page imprimée."""
    if not etat['liste_figures']:
        return ''
    lignes = ''.join(
        f'<div class="item"><span class="t"><b>{label}</b> — {alt}</span>'
        f'<span class="p" data-ref="#{fid}"></span></div>'
        for label, alt, fid in etat['liste_figures'])
    return f"""
<section class="front dernier">
  <div class="front-kicker">Illustrations</div>
  <h1 class="front-titre">Index des figures et schémas</h1>
  <div class="front-rule"></div>
  <div class="som-figures">{lignes}</div>
</section>"""


def _schema_html(schema, etat):
    """Insère un schéma vectoriel en figure légendée."""
    etat['schemas'] = etat.get('schemas', 0) + 1
    numero = etat['schemas']
    fid = f'schema-{numero}'
    etat['liste_figures'].append((f'Schéma {numero}', schema['titre'], fid))
    return (f'<figure class="figure-schema" id="{fid}"><div class="schema-cadre">{schema["svg"]}</div>'
            f'<figcaption><b>Schéma {numero} — </b>{schema["titre"]}</figcaption></figure>')


def _couverture(config, version, date_txt, nb_chapitres, logo):
    return f"""
<section class="couverture">
  <div class="cv-halo"></div>
  <div class="cv-cadre"></div>
  <div class="cv-inner">
    <div class="cv-surtitre">{config['surtitre'].format(version=version)}</div>
    <div class="cv-filet-or"></div>
    <img class="cv-logo" src="{logo}">
    <div class="cv-marque">YELEN<span>SCHOOL</span></div>
    <div class="cv-titre">{config['couverture_titre']}</div>
    <div class="cv-sous-titre">{config['couverture_sous_titre']}</div>
  </div>
  <div class="cv-bas">
    <div class="rule"></div>
    <table><tr>
      <td style="width:34%">Document<b>{config['titre_court'].split('· ')[-1]}</b></td>
      <td style="width:22%">Version<b>{version}</b></td>
      <td style="width:22%">Mise à jour<b>{date_txt}</b></td>
      <td class="g" style="width:22%">Chapitres<b>{nb_chapitres:02d}</b></td>
    </tr></table>
  </div>
</section>"""


def _fiche(config, valeurs):
    lignes = ''.join(f'<tr><th>{libelle}</th><td>{valeur.format(**valeurs)}</td></tr>'
                     for libelle, valeur in config['fiche'])
    intro = ''.join(f'<p style="font-size:9.1pt; color:#3B4655">{p.format(**valeurs)}</p>'
                    for p in config['fiche_intro'])
    return f"""
<section class="front">
  <div class="front-kicker">Fiche du document</div>
  <h1 class="front-titre">{config['fiche_titre']}</h1>
  <div class="front-rule"></div>
  <table class="fiche">{lignes}</table>
  {intro}
</section>"""


LEGENDE = """
<section class="front">
  <div class="front-kicker">Mode d'emploi du manuel</div>
  <h1 class="front-titre">Comment lire ce guide</h1>
  <div class="front-rule"></div>
  <p>Quatre familles d'encadrés ponctuent le texte. Elles signalent ce qui fait gagner du temps, ce qui évite une
  erreur, et ce qui relève d'une règle de gestion.</p>
  <div class="legende-grille">
    <div class="legende-item">
      <div class="callout astuce" style="margin-top:0"><div class="label"><span class="ic ic-ampoule"></span>Astuce
      </div><p>Raccourci, réglage ou méthode qui fait gagner du temps au quotidien.</p></div>
    </div>
    <div class="legende-item">
      <div class="callout alerte" style="margin-top:0"><div class="label"><span class="ic ic-alerte"></span>Avertissement
      </div><p>Point de vigilance : une erreur ici coûte une correction ou une ressaisie.</p></div>
    </div>
    <div class="legende-item">
      <div class="callout acces" style="margin-top:0"><div class="label"><span class="ic ic-fleche"></span>Accès
      </div><p>Chemin exact dans le menu et droits nécessaires pour ouvrir l'écran.</p></div>
    </div>
    <div class="legende-item">
      <div class="callout regle" style="margin-top:0"><div class="label"><span class="ic ic-cadenas"></span>Règle de
      sécurité</div><p>Comportement imposé par le logiciel : il ne peut pas être contourné.</p></div>
    </div>
  </div>

  <h3 style="margin-top:9mm">Repères typographiques</h3>
  <table class="fiche">
    <tr><th>Chemins de menu</th><td>Écrits en clair ou entre accents graves, par exemple
      <code>Finances → Paiements</code> : ce sont les libellés que vous voyez à l'écran.</td></tr>
    <tr><th>Champs à saisir</th><td>Le nom exact du champ est cité entre guillemets droits, suivi d'un exemple de
      valeur lorsque plusieurs formats existent.</td></tr>
    <tr><th>Blocs monospace</th><td>Commandes à recopier telles quelles, sorties de console ou arborescences de
      fichiers ; ils se lisent en largeur et n'ont pas à être traduits.</td></tr>
    <tr><th>Figures et schémas</th><td>Chaque capture et chaque schéma est numéroté et légendé ; l'index des
      illustrations donne sa page.</td></tr>
    <tr><th>Tableaux</th><td>Les tableaux reprennent la structure exacte des écrans ou des fichiers : la première
      ligne est l'en-tête affiché.</td></tr>
  </table>
</section>"""


def _sommaire(config, chapitres, version):
    par_num = {c['num']: c for c in chapitres if c['num'] is not None}
    par_titre = {c['titre_brut']: c for c in chapitres}
    blocs = ['<section class="sommaire">',
             '<div class="front-kicker">Navigation</div>',
             '<h1 class="som-titre">Sommaire</h1>',
             f'<p class="som-intro">{config["som_intro"]}</p>']
    for lettre, nom, resume, refs in config['parties']:
        blocs.append(f'<div class="som-part">Partie {lettre} <span>· {nom}</span></div>')
        for ref in refs:
            c = par_num.get(ref) if isinstance(ref, int) else par_titre.get(ref)
            if not c:
                continue
            nb = len(c['sections'])
            detail = f'<small>{nb} section{"s" if nb > 1 else ""}</small>' if nb else ''
            num = f'{c["num"]}' if c['num'] is not None else ''
            blocs.append(f'<div class="som-chap"><span class="n">{num}</span>'
                         f'<span class="t">{c["titre"]}{detail}</span>'
                         f'<span class="p" data-ref="#{c["id"]}"></span></div>')
    blocs.append('</section>')
    return '\n'.join(blocs)


def assembler(source: Path, sortie: Path, cle='utilisation'):
    """Compose le PDF éditorial d'un guide à partir de son dossier documentaire."""
    config = DOCUMENTS[cle]
    texte = source.read_text(encoding='utf-8')
    entete, avant_md, chapitres_md = decouper(texte, config)
    version = entete.get('version_logiciel') or (RACINE / 'VERSION').read_text(encoding='utf-8').strip()
    date_txt = entete.get('date_mise_a_jour', '').split('(')[0].strip()
    if not date_txt:
        auj = __import__('datetime').date.today()
        date_txt = f'{auj:%d/%m/%Y}'
    etat = {'figures': 0, 'schemas': 0, 'liste_figures': [], 'sections': []}

    # les sections numérotées « 3.5 … » sont rendues dans leur chapitre parent
    fusionnes = []
    for bloc in chapitres_md:
        if bloc.get('kind') == 'sous-chapitre':
            parent = next((c for c in reversed(fusionnes) if c['num'] == bloc['parent']), None)
            if parent is not None:
                parent['md'] += f"\n\n### {bloc['titre']}\n\n{bloc['md']}"
                continue
        fusionnes.append(bloc)
    chapitres_md = fusionnes

    import markdown as md_lib
    chapitres = []
    vues_chap = {}
    for bloc in chapitres_md:
        etat['sections'] = []
        source_md, blocs_code = reparer_listes(bloc['md'])
        html = md_lib.markdown(source_md, extensions=['tables', 'fenced_code', 'sane_lists', 'attr_list'],
                               output_format='html5')
        html = injecter_blocs(html, blocs_code)
        contenu = traiter_fragment(html, etat)
        contenu = traiter_images(contenu, etat)
        if bloc['num'] is not None:
            for schema in config['schemas']:
                if schema['chapitre'] == bloc['num']:
                    contenu = _schema_html(schema, etat) + contenu
        cid = ancre(f"chapitre-{bloc['num']}-{bloc['titre']}", vues=vues_chap)
        chapitres.append({'num': bloc['num'], 'titre': joli_titre(bloc['titre']), 'titre_brut': bloc['titre'],
                          'id': cid, 'html': contenu, 'sections': list(etat['sections']),
                          'kind': bloc['kind']})

    # ── Pages liminaires ───────────────────────────────────────────────────
    logo = (RACINE / 'yelen-school-icon.svg').resolve()
    valeurs = {
        'version': version, 'date': date_txt,
        'version_guide': entete.get('version_guide', ''),
        'modules': entete.get('modules_documentes', ''),
        'redaction': entete.get('redige_par', 'Équipe YELEN SCHOOL'),
    }
    nb_numerotes = len([c for c in chapitres if c['num'] is not None])
    couverture = _couverture(config, version, date_txt, nb_numerotes, logo)
    fiche = _fiche(config, valeurs)

    avant_propos = ''
    if config.get('avant_propos') and avant_md:
        source_avant, blocs_avant = reparer_listes('\n'.join(avant_md))
        html_avant = md_lib.markdown(source_avant, extensions=['tables', 'fenced_code', 'sane_lists',
                                                              'attr_list'], output_format='html5')
        corps_avant = traiter_fragment(injecter_blocs(html_avant, blocs_avant), etat)
        corps_avant = _brief(corps_avant)
        avant_propos = f"""
<section class="front">
  <div class="front-kicker">À lire en premier</div>
  <h1 class="front-titre">{config['avant_propos']}</h1>
  <div class="front-rule"></div>
  {corps_avant}
</section>"""

    sommaire = _sommaire(config, chapitres, version)
    index_figures = _figures_index(etat)

    # ── Corps : parties + chapitres ────────────────────────────────────────
    par_num = {c['num']: c for c in chapitres if c['num'] is not None}
    par_titre = {c['titre_brut']: c for c in chapitres}
    referencees = {ref for _, _, _, refs in config['parties'] for ref in refs}
    orphelins = [c for c in chapitres
                 if c['num'] not in referencees and c['titre_brut'] not in referencees]
    if orphelins:
        parties = [list(p) for p in config['parties']]
        parties[-1][3] = list(parties[-1][3]) + [c['titre_brut'] for c in orphelins]
        config = dict(config, parties=[tuple(p) for p in parties])

    corps = ['<div class="corps-debut"></div>']
    styles_chapitres = []
    for lettre, nom, resume, refs in config['parties']:
        membres = [par_num.get(ref) if isinstance(ref, int) else par_titre.get(ref) for ref in refs]
        membres = [c for c in membres if c]
        liste = ''.join(f'<div><b>{c["num"] if c["num"] is not None else "·"}</b>{c["titre"]}</div>'
                        for c in membres)
        corps.append(f"""
<section class="ouverture">
  <div class="halo"></div>
  <div class="bloc">
    <div class="part-num">{lettre}</div>
    <div class="part-label">Partie {lettre}</div>
    <div class="part-titre">{nom}</div>
    <div class="part-filet"></div>
    <div class="part-resume">{resume}</div>
    <div class="part-liste">{liste}</div>
  </div>
  <div class="part-folio">{config['titre_court']} · Édition {version}</div>
</section>""")
        for c in membres:
            sections = ''.join(f'<li><a href="#{sid}">{st}</a></li>' for st, sid in c['sections'])
            bloc_dans = (f'<div class="dans"><div class="label">Dans ce chapitre</div><ul>{sections}</ul></div>'
                         if c['sections'] else '')
            if c['num'] is not None:
                kicker = f'Chapitre {c["num"]}'
                num_html = f'<div class="num">{c["num"]:02d}</div>'
            else:
                kicker = 'Repères'
                num_html = ''
            classe_num = 'num-bloc' if num_html else 'num-bloc sans-num'
            court = re.split(r'\s+—\s+|\s+\(', c['titre'])[0][:38]
            styles_chapitres.append(
                f'#{c["id"]} .chapeau h2 {{ string-set: chapitre-courant "{court}"; }}')
            corps.append(f"""
<section class="chapitre" id="{c['id']}">
  <div class="chapeau">
    <div class="sur-titre">{kicker}</div>
    <div class="{classe_num}">{num_html}<h2>{c['titre']}</h2></div>
    {bloc_dans}
  </div>
  {c['html']}
</section>""")

    fin_paragraphes = ''.join(f'<p>{p.format(version=version)}</p>' for p in config['fin'])
    fin = f"""
<section class="fin">
  <div class="bloc">
    <div class="marque">YELEN<span>SCHOOL</span></div>
    <div class="devise">« Illuminer chaque parcours scolaire »</div>
    <div class="filet"></div>
    {fin_paragraphes}
  </div>
  <div class="mentions">Document interne — {config['titre_court']} · Édition {version} — {date_txt} ·
    composé en Inter, Source Serif 4 et JetBrains Mono</div>
</section>"""

    document = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>{config['titre_court']} {version}</title>
<meta name="author" content="YELEN SCHOOL">
<meta name="description" content="{config['titre_court']}, version {version} : {config['couverture_sous_titre']}">
<meta name="keywords" content="YELEN SCHOOL, {config['cle']}, gestion scolaire, Burkina Faso, {version}">
<meta name="generator" content="scripts/md_vers_pdf.py">
<style>
{css_icones()}
{''.join(styles_chapitres)}
</style>
</head>
<body>
{couverture}
{fiche}
{LEGENDE}
{avant_propos}
{sommaire}
{index_figures}
{''.join(corps)}
{fin}
</body>
</html>"""

    # ── Rendu : passes successives pour que chaque renvoi indique la page imprimée ──
    css_version = CSS(string="""
      html { string-set: livre "__LIVRE__"; }
    """.replace('__LIVRE__', config['titre_court']))
    css_folios = CSS(string="""
      .corps-debut { counter-reset: page 0; }
    """)
    css_renvois = CSS(string="""
      .som-chap .p::after, .som-figures .item .p::after { content: attr(data-page); }
      .chapeau .dans li a::after { content: "  " attr(data-page); }
    """)
    css_mesure = CSS(string="""
      .som-chap .p::after, .som-figures .item .p::after { content: target-counter(attr(data-ref), page); }
      .chapeau .dans li a::after { content: "  " target-counter(attr(href), page); }
    """)

    feuille = _feuille(version, date_txt)
    premiere_cible = next((c['id'] for c in chapitres), '')
    numeros = {}
    for _ in range(3):
        html_passe = _injecter_pages(document, numeros)
        rendu = HTML(string=html_passe, base_url=str(GABARIT)).render(
            stylesheets=[feuille, css_version, css_renvois if numeros else css_mesure])
        releve = {}
        for index, page in enumerate(rendu.pages):
            for nom in getattr(page, 'anchors', {}):
                releve.setdefault(nom, index + 1)
        premiere = releve.get(premiere_cible, 1)
        nouveaux = {nom: max(1, page - premiere + 1) for nom, page in releve.items()}
        if nouveaux == numeros:
            break
        numeros = nouveaux

    document = _injecter_pages(document, numeros)
    HTML(string=document, base_url=str(GABARIT)).write_pdf(
        str(sortie), stylesheets=[feuille, css_version, css_folios, css_renvois],
        metadata_title=f"{config['titre_court']} {version}",
        attachments=[str(RACINE / 'VERSION')],
    )
    return sortie


def _feuille(version, date_txt):
    """Feuille de style du guide, avec le pied de page renseigné (édition et date)."""
    texte = (GABARIT / 'style.css').read_text(encoding='utf-8')
    texte = texte.replace('__PIED_DROIT__', f'Édition {version} · {date_txt}')
    return CSS(string=texte, base_url=str(GABARIT))


def _injecter_pages(document, numeros):
    """Porte la page imprimée sur chaque renvoi (sommaire, sections, index des figures)."""
    def remplacer(m):
        attr, cible = m.group(1), m.group(2)
        page = numeros.get(cible.lstrip('#'))
        if page is None:
            return m.group(0)
        return f'{attr}="{cible}" data-page="{page}"'
    return re.sub(r'(data-ref|href)="(#[^"]+)"', remplacer, document)


def main():
    args = [a for a in sys.argv[1:]]
    cle = 'utilisation'
    if args and args[0] in DOCUMENTS:
        cle = args.pop(0)
    config = DOCUMENTS[cle]
    source = Path(args[0]) if args else DOCS / config['fichier']
    sortie = Path(args[1]) if len(args) > 1 else DOCS / config['sortie']
    assembler(source, sortie, cle)
    print(f'{sortie} ({sortie.stat().st_size / 1_048_576:.1f} Mo)')


if __name__ == '__main__':
    main()
