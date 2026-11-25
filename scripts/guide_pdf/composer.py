"""Composition du guide Markdown en PDF éditorial — sans dépendance système.

WeasyPrint (HTML/CSS → PDF) exige `libpango`, absent de certains postes et impossible à installer sans
droits administrateur. Ce module produit le même ouvrage avec ReportLab seul (Python pur) : charte
identique (encre marine, vert institutionnel, or typographique ; Inter, Source Serif 4 et JetBrains
Mono livrées dans `scripts/guide_pdf/fonts`), pagination réelle, en-têtes courants, sommaire paginé,
signets, tableaux à en-tête répété, encadrés, captures et schémas vectoriels.

Usage :
    python scripts/guide_pdf/composer.py [source.md] [sortie.pdf]
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle, XPreformatted)

# ── Charte ───────────────────────────────────────────────────────────────────
ENCRE, ENCRE_DOUCE, SOURDINE = HexColor('#16202E'), HexColor('#3B4655'), HexColor('#6C7787')
MARINE, MARINE_2 = HexColor('#0A1628'), HexColor('#12233A')
VERT, VERT_FONCE = HexColor('#00A86B'), HexColor('#067955')
OR, OR_CLAIR = HexColor('#B0803A'), HexColor('#D8B675')
FILET, FILET_FONCE, BLANC = HexColor('#E2E6EB'), HexColor('#C9D0D8'), HexColor('#FFFFFF')
MARINE_TETE = HexColor('#0F1E33')
ZEBRE = HexColor('#F8F9FB')

ZONES = {   # type → (fond, filet, libellé, couleur du libellé, icône)
    'astuce': (HexColor('#F0F9F4'), VERT, 'ASTUCE', VERT_FONCE, 'ampoule'),
    'alerte': (HexColor('#FDF6E8'), HexColor('#C58C2A'), 'AVERTISSEMENT', HexColor('#8A5A12'), 'alerte'),
    'acces': (HexColor('#F1F5FA'), HexColor('#34506F'), 'ACCÈS', HexColor('#2C3E55'), 'fleche'),
    'note': (HexColor('#F7F6F3'), OR, 'NOTE', HexColor('#8A6A32'), 'note'),
    'regle': (HexColor('#FBF1F1'), HexColor('#A8443B'), 'RÈGLE DE SÉCURITÉ', HexColor('#8C332B'), 'cadenas'),
}

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
POLICES, DOCS = ICI / 'fonts', RACINE / 'docs'

LARGEUR, HAUTEUR = 210 * mm, 297 * mm
MARGE_INT, MARGE_EXT, MARGE_HAUT, MARGE_BAS = 26 * mm, 20 * mm, 24 * mm, 20 * mm
CORPS_L = LARGEUR - MARGE_INT - MARGE_EXT


# ── Polices ──────────────────────────────────────────────────────────────────
def enregistrer_polices():
    plan = [('Inter', 'Inter-Regular.ttf'), ('Inter-It', 'Inter-Italic.ttf'), ('Inter-Md', 'Inter-Medium.ttf'),
            ('Inter-Sb', 'Inter-SemiBold.ttf'), ('Inter-Bd', 'Inter-Bold.ttf'),
            ('Inter-Xb', 'Inter-ExtraBold.ttf'), ('Serif', 'SourceSerif4-Regular.ttf'),
            ('Serif-It', 'SourceSerif4-Italic.ttf'), ('Serif-Sb', 'SourceSerif4-SemiBold.ttf'),
            ('Mono', 'JetBrainsMono-Regular.ttf'), ('Mono-Sb', 'JetBrainsMono-SemiBold.ttf')]
    for nom, fichier in plan:
        if nom not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nom, str(POLICES / fichier)))
    from reportlab.lib.fonts import addMapping
    # les quatre combinaisons de chaque famille doivent être déclarées : sans l'entrée (0,0),
    # ReportLab retombe sur une variante italique pour le texte courant
    familles = {'Inter': ('Inter', 'Inter-Bd', 'Inter-It'),
                'Serif': ('Serif', 'Serif-Sb', 'Serif-It'),
                'Mono': ('Mono', 'Mono-Sb', 'Mono')}
    for famille, (normal, gras, ital) in familles.items():
        for b in (0, 1):
            for it in (0, 1):
                addMapping(famille, b, it, (ital if it else (gras if b else normal)))


# ── Texte ────────────────────────────────────────────────────────────────────
_ACCENTS = str.maketrans('àâäáãåçèêëéîïíìôöòóõûüùúÿñ', 'aaaaaaceeeeiiiiooooouuuuyn')
EMOJI = {'✅': '✓', '☑': '□', '❌': '✗', '✕': '×', '⚠': '▲', '💡': '§', '⚡': '!', '⚙': '•',
         '🔒': '▪', '🔑': '▪', '🛡': '▪', '📄': '▪', '📋': '▪', '📊': '▮', '🔍': '○', '🔔': '◉',
         '🎓': '◆', '🏆': '★', '🥇': '★', '🥈': '★', '🥉': '★', '👤': '▪', '👨': '▪', '🏠': '▪',
         '🏫': '▪', '💰': '▪', '💳': '▪', '💼': '▪', '💬': '▪', '📅': '▪', '📌': '▪', '📎': '▪',
         '📓': '▪', '📝': '▪', '📨': '▪', '✏': '▪', '🔧': '▪', '🔲': '□', '🔴': '●', '🔵': '●',
         '🟠': '●', '🟡': '●', '🟢': '●', '🤖': '▪', '🧩': '▪', '🎭': '▪', '🔄': '↻', '🖨': '▪',
         '🖼': '▪', '🔢': '▪', '🔗': '▪', '🚪': '▪', '✈': '▪', '✂': '▪', '⏱': '◷', '⏳': '◷',
         '❓': '?', '🖱': '▪', '📁': '▪', '📂': '▪', '📘': '▪', '📙': '▪', '📗': '▪', '📦': '▪',
         # caractères absents des polices Inter / Source Serif 4 : substitution obligatoire
         '▸': '›', '▮': '▬', '◉': '●', '◷': '◔', '✦': '*', '☐': '□', '⚖': '§',
         '⋮': '...', '＋': '+', '🔎': '○', '🔐': '▪', '🔽': '▾', '️': '',
         '①': '1', '②': '2', '③': '3', '④': '4', '⑤': '5', '⑥': '6', '⑦': '7', '⑧': '8', '⑨': '9',
         # scories de la source (caractères chinois isolés) : à remplacer par une ellipse
         '信': '...', '形': '', '息': '', '梯': '', '等': ''}


def sans_emoji(txt: str) -> str:
    sortie = []
    for c in txt:
        if c in EMOJI:
            sortie.append(EMOJI[c])
        elif ord(c) >= 0x1F000 or 0xFE00 <= ord(c) <= 0xFE0F or ord(c) == 0x200D:
            continue
        else:
            sortie.append(c)
    return ''.join(sortie)


def _nettoyer_titre(txt: str) -> str:
    """Retire du titre les marqueurs Markdown (code, gras, italique) et normalise les espaces."""
    txt = re.sub(r'`([^`]*)`', r'\1', txt)
    txt = re.sub(r'\*+', '', txt)
    return re.sub(r'\s+', ' ', txt).strip()


def ancre(txt: str, vues: dict) -> str:
    base = re.sub(r'[^a-z0-9]+', '-', txt.lower().translate(_ACCENTS)).strip('-')[:60] or 'section'
    n = vues.get(base, 0) + 1
    vues[base] = n
    return base if n == 1 else f'{base}-{n}'


SIGLES = {'YELEN', 'SCHOOL', 'SMS', 'PDF', 'PWA', 'FAQ', 'APC', 'API', 'IA', 'QR', 'CSV', 'JSON', 'SQL',
          'XLSX', 'DOCX', 'UV', 'GPS', 'RGPD', 'AVS', 'FCFA', 'CEP', 'BEPC', 'BAC', 'CEPE', 'PC', 'RH',
          'CA', 'EDT', 'ACPI', 'PWA', 'SMS', 'MENAPLN', 'YELEN'}


def joli_titre(txt: str) -> str:
    """Casse éditoriale d'un titre, débarrassé du balisage Markdown.

    Les mots écrits ENTIÈREMENT en capitales deviennent « Capitale + bas de casse » ; les sigles
    et les libellés déjà composés (« Vie Scolaire ») sont laissés tels quels ; le premier mot
    entièrement capitalisé ouvre le titre.
    """
    txt = _nettoyer_titre(txt)

    def mot(m):
        t = m.group(0)
        lettres = [c for c in t if c.isalpha()]
        if not lettres or not all(c.isupper() for c in lettres):
            return t
        nu = t.strip('()«».!:;,')
        if nu in SIGLES or nu.isdigit() or len(nu) < 2:
            return t
        if len(nu) <= 3:
            remplacement = nu.lower()
        elif "'" in nu:                       # « L'ÉTABLISSEMENT » → « l'Établissement »
            avant, _, apres = nu.partition("'")
            remplacement = f"{avant.lower()}'{apres[0] + apres[1:].lower()}"
        else:
            remplacement = nu[0] + nu[1:].lower()
        return t.replace(nu, remplacement)
    resultat = re.sub(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9'’\-]+", mot, txt)
    # premier mot entièrement en capitales dans la source : il ouvre le titre
    premier = re.match(r"[A-Za-zÀ-ÖØ-öø-ÿ'’\-]+", txt)
    if premier and premier.group(0).isupper() and premier.group(0) not in SIGLES:
        mot_brut = premier.group(0)
        resultat = mot_brut[0] + resultat[len(mot_brut) - len(mot_brut) + 1:]
    return resultat


_CODE = re.compile(r'`([^`]+)`')
_LIEN = re.compile(r'\[([^\]]+)\]\([^)]+\)')
# italique : astérisque d'ouverture non précédé d'un caractère de mot (donc pas « *élèves* »),
# et jamais un astérisque isolé ni une puce « * » en début de ligne
_ITAL = re.compile(r'(?<![\w*])\*(?!\s)([^*\n]{1,400}?)(?<!\s)\*(?![\w*])')


def _equilibrer(balise: str, txt: str) -> str:
    """Referme une balise ouverte non fermée dans un fragment (gras / italique)."""
    ouvertes = len(re.findall(rf'<{balise}>', txt))
    fermees = len(re.findall(rf'</{balise}>', txt))
    if ouvertes > fermees:
        return txt + f'</{balise}>' * (ouvertes - fermees)
    if fermees > ouvertes:
        return f'<{balise}>' * (fermees - ouvertes) + txt
    return txt


def _corriger_imbrications(txt: str) -> str:
    """Réécrit les segments en balises strictement imbriquées (``<b>…<i>…</i>…</b>``).

    Le Markdown du guide contient des emphases croisées (``**titre *(5.4)* :**``) que ReportLab
    refuse : on relit les segments entre balises et on referme chaque balise avant d'en ouvrir une
    autre, en rouvrant ce qui doit continuer.
    """
    morceaux = re.split(r'(</?[bi]>)', txt)
    pile: list[str] = []
    sortie: list[str] = []
    for morceau in morceaux:
        m = re.fullmatch(r'<(/)?([bi])>', morceau)
        if not m:
            if morceau:
                sortie.append(morceau)
            continue
        fermeture, balise = bool(m.group(1)), m.group(2)
        if not fermeture:
            if balise in pile:                      # « <b>…<b> » : inutile
                continue
            pile.append(balise)
            sortie.append(f'<{balise}>')
            continue
        if balise not in pile:                      # fermeture orpheline : ignorée
            continue
        # refermer d'abord ce qui a été ouvert après elle, puis elle
        while pile and pile[-1] != balise:
            sortie.append(f'</{pile.pop()}>')
        pile.pop()
        sortie.append(f'</{balise}>')
        for ouverte in pile:                        # rouvrir les balises englobantes — sans doublon
            if not sortie or sortie[-1] != f'<{ouverte}>':
                sortie.append(f'<{ouverte}>')
    while pile:
        sortie.append(f'</{pile.pop()}>')
    return ''.join(sortie)


_PUCE = re.compile(r'^\s*[*+\-]\s+(?!\*)')


def inline(txt: str) -> str:
    """Markdown en ligne → balisage ReportLab, toujours équilibré.

    Les segments de code sont mis de côté (leurs astérisques sont du texte), puis l'emphase est
    convertie dans l'ordre du plus long au plus court, et les astérisques orphelins sont retirés :
    une emphase mal appariée dans la source ne peut donc pas produire de balise croisée.
    """
    txt = sans_emoji(txt)
    txt = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    txt = _LIEN.sub(r'\1', txt)

    txt = _PUCE.sub('', txt)          # puce « * » ou « - » en tête : rendue par le flux, pas par le texte
    codes: list[str] = []

    def _garder(m):
        codes.append(m.group(1))
        return f'\x00{len(codes) - 1}\x00'

    txt = _CODE.sub(_garder, txt)
    txt = re.sub(r'\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*', r'<b><i>\1</i></b>', txt, flags=re.S)
    txt = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', txt, flags=re.S)
    txt = _ITAL.sub(r'<i>\1</i>', txt)
    txt = txt.replace('*', '')
    txt = _corriger_imbrications(txt)
    for balise in ('b', 'i'):
        txt = _equilibrer(balise, txt)

    def _rendre(m):
        return f'<font name="Mono" color="#1B3A5C">{codes[int(m.group(1))]}</font>'
    return re.sub(r'\x00(\d+)\x00', _rendre, txt)


def detecter_zone(txt: str) -> str:
    bas = sans_emoji(txt).lower().lstrip('* ')
    if 'règle de sécurité' in bas[:44] or 'interdit' in bas[:70]:
        return 'regle'
    if bas.startswith('attention') or 'avertissement' in bas[:44] or 'important' in bas[:34] \
            or '⚠' in txt:
        return 'alerte'
    if 'astuce' in bas[:34] or 'conseil' in bas[:34] or 'recommand' in bas[:34]:
        return 'astuce'
    if bas.startswith('accès') or bas.startswith('acces') or 'qui peut accéder' in bas[:44] \
            or 'qui peut acceder' in bas[:44] or 'accès menu' in bas[:44]:
        return 'acces'
    return 'note'


# ── Styles ───────────────────────────────────────────────────────────────────
def styles() -> dict:
    base = dict(fontName='Inter', fontSize=9.1, leading=13.6, textColor=ENCRE_DOUCE, spaceAfter=2.8 * mm)
    return {
        'corps': ParagraphStyle('corps', alignment=TA_JUSTIFY, **base),
        'h3': ParagraphStyle('h3', fontName='Serif-Sb', fontSize=13.2, leading=16.6, textColor=MARINE,
                             spaceBefore=6.4 * mm, spaceAfter=2.6 * mm, alignment=TA_LEFT, keepWithNext=1),
        'h4': ParagraphStyle('h4', fontName='Inter-Bd', fontSize=9.1, leading=12.2, textColor=ENCRE,
                             spaceBefore=4.2 * mm, spaceAfter=1.6 * mm, alignment=TA_LEFT, keepWithNext=1),
        'puce': ParagraphStyle('puce', fontName='Inter', fontSize=8.9, leading=12.9, textColor=ENCRE_DOUCE,
                               alignment=TA_LEFT, leftIndent=5.6 * mm, bulletIndent=1.4 * mm,
                               spaceAfter=1.5 * mm),
        'puce2': ParagraphStyle('puce2', fontName='Inter', fontSize=8.7, leading=12.4, textColor=ENCRE_DOUCE,
                                alignment=TA_LEFT, leftIndent=10.4 * mm, bulletIndent=6.2 * mm,
                                spaceAfter=1.2 * mm),
        'zone': ParagraphStyle('zone', fontName='Inter', fontSize=8.9, leading=12.8, textColor=ENCRE_DOUCE,
                               alignment=TA_LEFT, spaceAfter=1.4 * mm),
        'zone_fin': ParagraphStyle('zone_fin', fontName='Inter', fontSize=8.9, leading=12.8,
                                   textColor=ENCRE_DOUCE, alignment=TA_LEFT, spaceAfter=0),
        'cellule': ParagraphStyle('cellule', fontName='Inter', fontSize=7.7, leading=10.5,
                                  textColor=HexColor('#24303F'), alignment=TA_LEFT),
        'entete': ParagraphStyle('entete', fontName='Inter-Sb', fontSize=6.8, leading=8.8, textColor=BLANC,
                                 alignment=TA_LEFT),
        'legende': ParagraphStyle('legende', fontName='Inter', fontSize=7.6, leading=10.6, textColor=SOURDINE,
                                  alignment=TA_LEFT),
    }


# ── Flux graphiques ──────────────────────────────────────────────────────────
class Saut(Flowable):
    """Saut de page conditionnel : n'ajoute une page que si moins de ``besoin`` points restent.

    Évite les pages vides produites par les sauts inconditionnels enchaînés (fin de chapitre,
    changement de gabarit), tout en garantissant qu'un titre de chapitre ne reste pas orphelin.
    """

    def __init__(self, besoin=None):
        super().__init__()
        self.besoin = besoin

    def wrap(self, aw, ah):
        if self.besoin is None or ah < self.besoin:
            self.canv._doctemplate.handle_pageBreak()
        return 0, 0

    def draw(self):
        pass


class Filet(Flowable):
    def __init__(self, largeur, epaisseur=0.4, couleur=FILET, avant=0, apres=0):
        super().__init__()
        self.largeur, self.epaisseur, self.couleur, self.avant, self.apres = largeur, epaisseur, couleur, avant, apres

    def wrap(self, *_):
        return self.largeur, self.epaisseur + self.avant + self.apres

    def draw(self):
        self.canv.setStrokeColor(self.couleur)
        self.canv.setLineWidth(self.epaisseur)
        self.canv.line(0, self.apres + self.epaisseur / 2, self.largeur, self.apres + self.epaisseur / 2)


class Signet(Flowable):
    """Signet de navigation PDF posé sur la page où il tombe."""

    NIVEAUX = {1: (0, 0), 2: (1, 0)}

    def __init__(self, libelle, niveau=1):
        super().__init__()
        self.libelle, self.niveau = libelle, niveau

    def wrap(self, *_):
        return 0, 0

    def draw(self):
        c = self.canv
        marge, reduc = self.NIVEAUX.get(self.niveau, (1, 0))
        c.bookmarkHorizontal(f'signet-{abs(hash((self.libelle, c.getPageNumber()))) % 10**12}',
                             marge * 10, reduc * 7)
        c.addOutlineEntry(self.libelle, f'signet-{abs(hash((self.libelle, c.getPageNumber()))) % 10**12}',
                          level=marge, closed=False)


class Repere(Flowable):
    """Point de repère invisible : note la page où commence un chapitre (passe 1)."""

    def __init__(self, cle, registre):
        super().__init__()
        self.cle, self.registre = cle, registre

    def wrap(self, *_):
        return 0, 0

    def draw(self):
        self.registre[self.cle] = self.canv.getPageNumber()


class Encadre(Flowable):
    """Encadré éditorial : barre colorée, fond teinté, libellé capitales et pictogramme vectoriel."""
    PAD_X, PAD_Y, BARRE = 6.4 * mm, 3.9 * mm, 1.7 * mm

    def __init__(self, largeur, flux, type_zone):
        super().__init__()
        self.largeur, self.flux = largeur, flux
        self.type_zone = type_zone
        self.fond, self.filet, self.libelle, self.couleur, self.icone = ZONES[type_zone]
        self._h = 0

    def wrap(self, aw, ah):
        dispo = self.largeur - 2 * self.PAD_X - self.BARRE
        self._h = 0
        for f in self.flux:
            _, h = f.wrap(dispo, ah)
            self._h += h
        self.height = self._h + 2 * self.PAD_Y
        return self.largeur, self.height

    def split(self, aw, ah):
        if self.height <= ah or ah < 2 * self.PAD_Y + 10 * mm:
            return []
        dispo = self.largeur - 2 * self.PAD_X - self.BARRE
        tete, queue = [], []
        consomme = 0
        for f in self.flux:
            h = f.wrap(dispo, ah)[1]
            if consomme + h <= ah - 2 * self.PAD_Y - 6 * mm:
                tete.append(f)
                consomme += h
                continue
            parties = f.split(dispo, ah - 2 * self.PAD_Y - 6 * mm - consomme)
            if len(parties) == 2:
                tete.append(parties[0])
                queue = [parties[1]] + self.flux[self.flux.index(f) + 1:]
            else:
                queue = self.flux[self.flux.index(f):]
            break
        if not tete or not queue:
            return []
        # chaque moitié garde la couleur et le libellé de la zone d'origine
        return [Encadre(self.largeur, tete, self.type_zone), Encadre(self.largeur, queue, self.type_zone)]

    def draw(self):
        c = self.canv
        h = self.height
        c.setFillColor(self.fond)
        c.rect(0, 0, self.largeur, h, stroke=0, fill=1)
        c.setFillColor(self.filet)
        c.rect(0, 0, self.BARRE, h, stroke=0, fill=1)

        base = h - self.PAD_Y
        c.setFillColor(self.couleur)
        c.setFont('Inter-Bd', 6.4)
        texte = self.libelle
        c.drawString(self.BARRE + self.PAD_X, base - 6.0, texte)
        x_ic = self.BARRE + self.PAD_X + c.stringWidth(texte, 'Inter-Bd', 6.4) + 2.0 * mm
        c.saveState()
        c.translate(x_ic, base - 5.3)
        _pictogramme(c, self.icone, 3.2 * mm, self.couleur)
        c.restoreState()

        c.saveState()
        c.translate(self.BARRE + self.PAD_X, base - 6.4 - 3.2 * mm - self._h)
        y = self._h
        for f in self.flux:                 # la hauteur mesurée reste intacte : un redessin est identique
            y -= getattr(f, 'height', 0)
            f.drawOn(c, 0, y)
        c.restoreState()


def _pictogramme(c, nom, t, couleur):
    c.setStrokeColor(couleur)
    c.setFillColor(couleur)
    c.setLineWidth(0.85)
    if nom == 'alerte':
        p = c.beginPath()
        p.moveTo(t / 2, 0)
        p.lineTo(t, t * 0.9)
        p.lineTo(0, t * 0.9)
        p.close()
        c.drawPath(p, stroke=1, fill=0)
        c.line(t / 2, t * 0.34, t / 2, t * 0.62)
        c.circle(t / 2, t * 0.2, t * 0.05, stroke=0, fill=1)
    elif nom == 'ampoule':
        c.circle(t / 2, t * 0.63, t * 0.32, stroke=1, fill=0)
        c.line(t * 0.37, t * 0.3, t * 0.37, t * 0.14)
        c.line(t * 0.63, t * 0.3, t * 0.63, t * 0.14)
        c.line(t * 0.37, t * 0.14, t * 0.63, t * 0.14)
    elif nom == 'cadenas':
        c.circle(t / 2, t * 0.6, t * 0.25, stroke=1, fill=0)
        c.rect(t * 0.16, 0, t * 0.68, t * 0.5, stroke=1, fill=0)
        c.rect(t * 0.16, 0, t * 0.68, t * 0.2, stroke=0, fill=1)
    elif nom == 'fleche':
        c.line(0, t / 2, t * 0.78, t / 2)
        p = c.beginPath()
        p.moveTo(t * 0.5, t * 0.8)
        p.lineTo(t, t / 2)
        p.lineTo(t * 0.5, t * 0.2)
        c.drawPath(p, stroke=1, fill=0)
    else:
        c.rect(t * 0.06, 0, t * 0.88, t * 0.88, stroke=1, fill=0)
        c.line(t * 0.26, t * 0.62, t * 0.68, t * 0.62)
        c.line(t * 0.26, t * 0.36, t * 0.54, t * 0.36)


# ── Markdown ─────────────────────────────────────────────────────────────────
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


def decouper(corps: str):
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

    chapitres = []
    for bloc in blocs:
        titre = bloc['titre']
        if titre.upper().startswith('TABLE DES MATI'):
            continue
        m = re.match(r'^(\d+)[.)]?\s+(.*)$', titre)
        if m:
            chapitres.append({'num': int(m.group(1)), 'titre': m.group(2), 'md': bloc['md']})
    return chapitres


def reparer_listes(src: str) -> str:
    lignes, code = [], False
    for ligne in src.split('\n'):
        if re.match(r'^ {0,3}(```|~~~)', ligne):
            code = not code
            lignes.append(ligne)
            continue
        if not code:
            ligne = re.sub(r'^( +)(?=([-*+]|\d+\.) )', lambda m: m.group(1) * 2, ligne)
        lignes.append(ligne)
    return '\n'.join(lignes)


def _tableau(lignes, st, largeur):
    lignes = [l for l in lignes if not re.match(r'^\|[\s:|-]*$', l.strip())] or lignes
    rangees = [[c.strip() for c in brute.strip().strip('|').split('|')] for brute in lignes]
    entete, corps = rangees[0], rangees[1:]
    nb = len(entete)

    def poids(txt):
        return max(3.5, min(24.0, len(re.sub(r'[*`]', '', txt)) / 2.6 + 3))

    total = sum(poids(c) for c in entete) or 1
    largeurs = [largeur * poids(c) / total for c in entete]
    donnees = [[Paragraph(inline(c), st['entete']) for c in entete]]
    for ligne in corps:
        ligne = (ligne + [''] * nb)[:nb]
        donnees.append([Paragraph(inline(c) or '&nbsp;', st['cellule']) for c in ligne])
    t = Table(donnees, colWidths=largeurs, repeatRows=1, hAlign='LEFT')
    commandes = [('BACKGROUND', (0, 0), (-1, 0), MARINE_TETE), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                 ('TOPPADDING', (0, 0), (-1, -1), 2.0 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.0 * mm),
                 ('LEFTPADDING', (0, 0), (-1, -1), 2.2 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 2.2 * mm),
                 ('LINEBELOW', (0, 1), (-1, -1), 0.35, FILET), ('LINEBELOW', (0, -1), (-1, -1), 0.8, FILET_FONCE)]
    for i in range(1, len(donnees)):
        if i % 2 == 0:
            commandes.append(('BACKGROUND', (0, i), (-1, i), ZEBRE))
    t.setStyle(TableStyle(commandes))
    return t


def _plier(texte: str, largeur: float, police: str, taille: float) -> str:
    """Coupe les lignes trop larges au caractère près (ReportLab ne coupe pas un « mot » sans espace)."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    if not hasattr(_plier, 'cache'):
        _plier.cache = {}
    sortie = []
    for ligne in texte.split('\n'):
        while stringWidth(ligne, police, taille) > largeur:
            n = len(ligne)
            while n > 1 and stringWidth(ligne[:n], police, taille) > largeur:
                n -= 1
            sortie.append(ligne[:n])
            ligne = ligne[n:]
        sortie.append(ligne)
    return '\n'.join(sortie)


def _code(bloc, largeur):
    """Bloc monospace : retours à la ligne conservés, lignes trop longues repliées dans la colonne."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    texte = '\n'.join(sans_emoji(b) for b in bloc).rstrip('\n')
    dispo = largeur - 5.8 * mm
    _code.dernier = (texte, dispo)
    # schémas ASCII : on réduit la taille plutôt que de casser le dessin, s'il reste lisible
    plus_large = max((stringWidth(l, 'Mono', 6.5) for l in texte.split('\n')), default=0)
    taille = 6.5 * min(1.0, dispo / plus_large) if plus_large > dispo else 6.5
    if taille < 4.6:                       # trop réduit pour être lisible : on replie les lignes
        taille = 6.5
        texte = _plier(texte, dispo, 'Mono', taille)
    plain = texte.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # XPreformatted conserve l'indentation et les retours à la ligne ; les lignes trop larges ont
    # déjà été pliées ci-dessus, ce qui évite tout débordement hors de la colonne de texte.
    style = ParagraphStyle('code', fontName='Mono', fontSize=taille, leading=taille * 1.42,
                           textColor=HexColor('#1F2937'))
    rendu = XPreformatted(plain, style)
    t = Table([[rendu]], colWidths=[largeur], hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HexColor('#FBF9F4')),
                           ('LINEBEFORE', (0, 0), (0, -1), 1.6, OR_CLAIR),
                           ('LEFTPADDING', (0, 0), (-1, -1), 3.2 * mm),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 2.6 * mm),
                           ('TOPPADDING', (0, 0), (-1, -1), 2.4 * mm),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 2.4 * mm), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    return KeepTogether([Spacer(1, 1.4 * mm), t, Spacer(1, 4.2 * mm)])


def _figure(chemin, legende, numero, largeur, st, sous_titre=None):
    """Capture d'écran cadrée et légendée.

    Les captures très hautes (pages entières) sont réduites pour ne pas dépasser la zone de texte ;
    la largeur maximale baisse d'autant, ce qui conserve le cadrage horizontal.
    """
    from PIL import Image as PILImage
    with PILImage.open(chemin) as im:
        px_l, px_h = im.size
    h_max = 178 * mm
    l = min(largeur, 150 * mm)
    h = l * px_h / px_l
    if h > h_max:
        h, l = h_max, h_max * px_l / px_h
    img = Image(str(chemin), width=l, height=h)
    img.hAlign = 'CENTER'
    cadre = Table([[img]], colWidths=[l], hAlign='CENTER')
    cadre.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.4, FILET_FONCE),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                               ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    texte_pied = f'<b>{numero}</b>&nbsp;&nbsp;{inline(legende)}'
    style_pied = st['legende']
    if sous_titre:                      # la phrase italique qui suit la capture dans la source
        texte_pied += f'<br/><font name="Inter-It" color="#5C6774" size="7.4">{inline(sous_titre)}</font>'
    pied = Table([[Paragraph(texte_pied, style_pied)]], colWidths=[l], hAlign='CENTER')
    pied.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 0.8, OR),
                              ('TOPPADDING', (0, 0), (-1, 0), 1.6 * mm),
                              ('LEFTPADDING', (0, 0), (-1, 0), 0), ('RIGHTPADDING', (0, 0), (-1, 0), 0),
                              ('BOTTOMPADDING', (0, 0), (-1, 0), 0)]))
    return KeepTogether([Spacer(1, 2.6 * mm), cadre, pied, Spacer(1, 5 * mm)])


def _figure_suivante(lignes, i, largeur, st, ctx):
    """Construit la figure qui suit immédiatement (lignes vides tolérées) et renvoie (bloc, reprise)."""
    j = i
    while j < len(lignes) and not lignes[j].strip():
        j += 1
    m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', lignes[j]) if j < len(lignes) else None
    if not m:
        return None
    chemin = (DOCS / m.group(2)).resolve()
    if not chemin.is_file():
        return None
    ctx['figures'] += 1
    sous_titre, fin = _sous_titre_figure(lignes, j + 1)
    return _figure(chemin, m.group(1), f'Figure {ctx["figures"]}', largeur, st, sous_titre), fin


def _sous_titre_figure(lignes, i):
    """Phrase en italique placée juste après la capture : légende détaillée rattachée à la figure.

    Renvoie (texte, index de reprise) — la ligne est consommée pour ne pas être répétée.
    """
    j = i
    while j < len(lignes) and not lignes[j].strip():
        j += 1
    if j >= len(lignes):
        return None, i
    ligne = lignes[j].strip()
    if len(ligne) > 1 and ligne.startswith('*') and ligne.endswith('*') and not ligne.startswith('**'):
        return ligne.strip('*').strip(), j + 1
    return None, i


def composer(md: str, st: dict, largeur: float, ctx: dict) -> list:
    md = reparer_listes(md)
    lignes = md.split('\n')
    flux: list = []
    tampon_zone: list[str] = []
    i = 0

    def vider_zone():
        nonlocal tampon_zone
        if not tampon_zone:
            return
        texte = '\n'.join(tampon_zone).strip()
        tampon_zone = []
        if not texte:
            return
        paragraphes = [p for p in re.split(r'\n\s*\n', texte) if p.strip()]
        flux_z = []
        for j, para in enumerate(paragraphes):
            contenu = inline(re.sub(r'\s*\n\s*', ' ', para.strip()))
            flux_z.append(Paragraph(contenu, st['zone_fin'] if j == len(paragraphes) - 1 else st['zone']))
        flux.append(Encadre(largeur, flux_z, detecter_zone(texte)))
        flux.append(Spacer(1, 4.0 * mm))

    while i < len(lignes):
        ligne = lignes[i]

        if ligne.startswith('```'):
            vider_zone()
            i += 1
            bloc = []
            while i < len(lignes) and not lignes[i].startswith('```'):
                bloc.append(lignes[i])
                i += 1
            i += 1
            if bloc:
                flux.append(_code(bloc, largeur))
            continue

        if ligne.startswith('>'):
            tampon_zone.append(re.sub(r'^>\s?', '', ligne))
            i += 1
            continue
        vider_zone()

        m = re.match(r'^(#{3,6})\s+(.*)$', ligne)
        if m:
            niveau, titre = len(m.group(1)), m.group(2).strip()
            if niveau == 3:
                ident = ancre(titre, ctx['ancres'])
                ctx['sections'].append((titre, ident))
                entete = Paragraph(f'<a name="{ident}"/>{inline(titre)}', st['h3'])
            else:
                entete = Paragraph(inline(titre), st['h4'])
            i += 1
            # un titre suivi d'une capture ne doit pas rester seul en bas de page
            j = i
            while j < len(lignes) and not lignes[j].strip():
                j += 1
            if j < len(lignes) and re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', lignes[j]):
                figure = _figure_suivante(lignes, i, largeur, st, ctx)
                if figure is not None:
                    bloc, i = figure
                    flux.append(KeepTogether([entete, bloc]))
                    continue
            flux.append(entete)
            continue

        if re.match(r'^\s*-{3,}\s*$', ligne):
            flux.append(Spacer(1, 2.2 * mm))
            i += 1
            continue

        if ligne.startswith('|') and i + 1 < len(lignes) and re.match(r'^\|?[\s:|-]+\|?\s*$', lignes[i + 1]) \
                and '-' in lignes[i + 1]:
            bloc = []
            while i < len(lignes) and lignes[i].startswith('|'):
                if not re.match(r'^\|[\s:|-]*$', lignes[i]) or not bloc:
                    bloc.append(lignes[i])
                i += 1
            flux.append(Spacer(1, 1.4 * mm))
            flux.append(_tableau(bloc, st, largeur))
            flux.append(Spacer(1, 4.6 * mm))
            continue

        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', ligne)
        if m:
            chemin = (DOCS / m.group(2)).resolve()
            if chemin.is_file():
                ctx['figures'] += 1
                sous_titre, i = _sous_titre_figure(lignes, i + 1)
                flux.append(_figure(chemin, m.group(1), f'Figure {ctx["figures"]}', largeur, st, sous_titre))
            i += 1
            continue

        m = re.match(r'^(\s*)[-*+]\s+(.*)$', ligne)
        if m:
            profondeur = len(m.group(1))
            if profondeur >= 2:
                flux.append(Paragraph(inline(m.group(2).strip()),
                                      ParagraphStyle('b2', parent=st['puce2'], bulletFontName='Inter'),
                                      bulletText='–'))
            else:
                flux.append(Paragraph(inline(m.group(2).strip()),
                                      ParagraphStyle('b1', parent=st['puce'], bulletFontName='Inter-Bd'),
                                      bulletText='›'))
            i += 1
            continue

        m = re.match(r'^(\s*)\d+[.)]\s+(.*)$', ligne)
        if m:
            profondeur = len(m.group(1))
            parent = st['puce2'] if profondeur >= 2 else st['puce']
            flux.append(Paragraph(inline(m.group(2).strip()),
                                  ParagraphStyle('n1', parent=parent, bulletFontName='Inter-Bd'),
                                  bulletText='›'))
            i += 1
            continue

        if ligne.strip():
            tampon = [re.sub(r'^-{3,}\s+', '', ligne.strip())]
            i += 1
            while i < len(lignes) and lignes[i].strip() and not re.match(
                    r'^\s*([-*+]\s|\d+[.)]\s|#{1,6}\s|\||>|```|-{3,}\s*$)', lignes[i]):
                tampon.append(lignes[i].strip())
                i += 1
            flux.append(Paragraph(inline(' '.join(tampon)), st['corps']))
            continue
        i += 1
    vider_zone()
    return flux


# ── Parties éditoriales ──────────────────────────────────────────────────────
PARTIES = [
    ('I', 'Prise en main', "Le contexte du produit, la connexion, le tableau de bord et les paramètres de "
                           "l'établissement : de quoi ouvrir l'application et la configurer.", [1, 2, 3]),
    ('II', 'Élèves, personnel et pédagogie', 'Inscriptions, dossiers du personnel, notes et bulletins, présences '
                                             'et vie scolaire : le cœur du travail quotidien.', [4, 5, 6, 7, 8]),
    ('III', 'Argent et évaluation', 'Scolarité, encaissements, dépenses, examens officiels et vacations : tout '
                                    'ce qui se compte et se justifie.', [9, 10, 11]),
    ('IV', 'Documents et pilotage', 'Documents administratifs, licences, statistiques et état des '
                                    'fonctionnalités : les productions et les tableaux de bord de la direction.',
     [12, 13, 14, 15]),
    ('V', 'Références et interface', 'Questions fréquentes, glossaire et design system : le vocabulaire et les '
                                     "règles graphiques de l'application.", [16, 17, 18]),
    ('VI', 'Portails, innovations et familles', 'Portail parent, signature électronique, prédiction de réussite, '
                                                'APC/API, bourses, assistant IA, budget, manuels, hors ligne, '
                                                'communication, emploi du temps, localisations.',
     [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]),
    ('VII', 'Exploitation, sécurité et qualité', "Mode autonome, SMS des familles, galerie d'écrans, sécurité, "
                                                 'source de vérité, import de fichiers, services annexes, contrôle '
                                                 'qualité et offre hébergée.', [31, 32, 33, 34, 35, 36, 37, 38, 39]),
    ('VIII', 'Annexes pratiques', 'Exemples de saisie champ par champ : des valeurs réelles à recopier pour chaque '
                                  'formulaire du logiciel.', [40]),
]


# ── Gabarit de document ──────────────────────────────────────────────────────
class Guide(BaseDocTemplate):
    def __init__(self, chemin, version, date_txt, chapitres):
        super().__init__(str(chemin), pagesize=(LARGEUR, HAUTEUR), leftMargin=MARGE_INT, rightMargin=MARGE_EXT,
                         topMargin=MARGE_HAUT, bottomMargin=MARGE_BAS,
                         title="YELEN SCHOOL — Guide d'utilisation", author='YELEN SCHOOL',
                         subject='Manuel officiel du logiciel de gestion scolaire', creator='YELEN SCHOOL',
                         keywords='YELEN SCHOOL, guide, utilisation, gestion scolaire, Burkina Faso')
        self.version_ouvrage, self.date_ouvrage = version, date_txt
        self.nb_chapitres = len(chapitres)
        self.livre = "YELEN SCHOOL · GUIDE D'UTILISATION"
        self.chapitre_courant = ''
        self.pages_pleines = {}        # page → (genre, bloc) : ouvertures et colophon (passe 1)
        self.pleines = {}              # idem, figé pour la passe 2
        self.chapitres_pages = []      # (page, libellé) pour l'en-tête courant
        self.registre = {}
        self.pages_sommaire = []
        self.debut_corps = 0      # page (physique) du premier chapitre
        self.nb_pages = 0         # total de pages de l'ouvrage (colophon)
        self.fin_liminaires = 2   # dernière page liminaire (la couverture n'est pas foliotée)
        plein = Frame(0, 0, LARGEUR, HAUTEUR, id='plein', leftPadding=0, rightPadding=0, topPadding=0,
                      bottomPadding=0, showBoundary=0)
        corps = Frame(MARGE_INT, MARGE_BAS, CORPS_L, HAUTEUR - MARGE_HAUT - MARGE_BAS, id='corps',
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0)
        self.addPageTemplates([
            PageTemplate(id='couverture', frames=[plein], onPage=self._couverture),
            PageTemplate(id='pleine', frames=[plein], onPage=self._ouverture),
            PageTemplate(id='liminaire', frames=[corps], onPage=self._liminaire),
            PageTemplate(id='corps', frames=[corps], onPage=self._corps, autoNextPageTemplate='corps'),
        ])

    # — fonds pleine page —
    @staticmethod
    def _fond(c):
        c.setFillColor(MARINE)
        c.rect(0, 0, LARGEUR, HAUTEUR, stroke=0, fill=1)
        c.setFillColor(MARINE_2)
        c.circle(LARGEUR * 0.86, HAUTEUR * 0.9, 118 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor('#0E1E31'))
        c.circle(LARGEUR * 0.05, HAUTEUR * 0.1, 86 * mm, stroke=0, fill=1)

    def _couverture(self, c, doc):
        self._fond(c)
        c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.5))
        c.setLineWidth(0.6)
        c.rect(11 * mm, 11 * mm, LARGEUR - 22 * mm, HAUTEUR - 22 * mm, stroke=1, fill=0)
        x = 24 * mm
        c.setFillColor(OR_CLAIR)
        c.setFont('Inter-Sb', 7.3)
        c.drawString(x, HAUTEUR - 34 * mm, f'ÉDITION {self.version_ouvrage}   ·   MANUEL OFFICIEL')
        c.setFillColor(OR)
        c.rect(x, HAUTEUR - 40.5 * mm, 26 * mm, 1.1, stroke=0, fill=1)
        _logo(c, x, HAUTEUR - 76 * mm, 21 * mm)

        c.setFillColor(BLANC)
        c.setFont('Inter-Xb', 37)
        c.drawString(x, HAUTEUR - 104 * mm, 'YELEN')
        c.setFillColor(VERT)
        c.setFont('Inter-Sb', 12)
        c.drawString(x + 1.4, HAUTEUR - 112 * mm, 'S C H O O L')

        c.setFillColor(BLANC)
        c.setFont('Serif-Sb', 30)
        c.drawString(x, HAUTEUR - 150 * mm, 'Guide')
        c.drawString(x, HAUTEUR - 161.5 * mm, "d'utilisation")

        c.setFillColor(HexColor('#C6D0DB'))
        c.setFont('Serif-It', 11.2)
        c.drawString(x, HAUTEUR - 175 * mm, 'Gestion scolaire complète — inscriptions, pédagogie,')
        c.drawString(x, HAUTEUR - 181 * mm, 'finances, documents et communication avec les familles.')

        y = 34 * mm
        c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.4))
        c.setLineWidth(0.5)
        c.line(x, y + 12 * mm, LARGEUR - 24 * mm, y + 12 * mm)
        pas = (LARGEUR - 48 * mm) / 4
        for i, (libelle, valeur) in enumerate([('DOCUMENT', "Guide d'utilisation"),
                                               ('VERSION', self.version_ouvrage),
                                               ('MISE À JOUR', self.date_ouvrage),
                                               ('CHAPITRES', f'{self.nb_chapitres:02d}')]):
            c.setFillColor(HexColor('#AEB9C6'))
            c.setFont('Inter', 6.6)
            c.drawString(x + i * pas, y + 6.2 * mm, libelle)
            c.setFillColor(BLANC)
            c.setFont('Inter-Sb', 8.6)
            c.drawString(x + i * pas, y + 1.6 * mm, valeur)

    def _ouverture(self, c, doc):
        self._fond(c)
        c.setFillColor(HexColor('#0F2438'))
        c.circle(LARGEUR * 0.92, HAUTEUR * 0.95, 92 * mm, stroke=0, fill=1)
        genre, bloc = self.pleines.get(doc.page, (None, None))
        if genre == 'colophon':
            self._colophon(c, doc)
            return
        if genre != 'ouverture' or not bloc:
            return
        num, titre, resume, chapitres = bloc
        x = 26 * mm
        c.setFillColor(OR_CLAIR)
        c.setFont('Serif', 58)
        c.drawString(x, HAUTEUR - 116 * mm, num)
        c.setFillColor(HexColor('#7E8B9A'))
        c.setFont('Inter-Bd', 7.1)
        c.drawString(x, HAUTEUR - 124 * mm, 'PARTIE')
        lignes_titre = _couper(titre, 'Serif-Sb', 23, 152 * mm)
        c.setFillColor(BLANC)
        c.setFont('Serif-Sb', 23)
        for k, ligne in enumerate(lignes_titre):
            c.drawString(x, HAUTEUR - 140 * mm - k * 10.5 * mm, ligne)
        y = HAUTEUR - 140 * mm - len(lignes_titre) * 10.5 * mm - 5 * mm
        c.setFillColor(HexColor('#B9C4D0'))
        c.setFont('Inter', 9.2)
        lignes_resume = _couper(resume, 'Inter', 9.2, 122 * mm)
        for k, ligne in enumerate(lignes_resume):
            c.drawString(x, y - k * 5.2 * mm, ligne)
        y -= len(lignes_resume) * 5.2 * mm + 8 * mm
        c.setFillColor(OR)
        c.rect(x, y, 28 * mm, 1.3, stroke=0, fill=1)
        y -= 12 * mm
        for n, titre_chap in chapitres:
            c.setFillColor(OR_CLAIR)
            c.setFont('Inter-Sb', 8.7)
            c.drawString(x, y, f'{n:02d}')
            c.setFillColor(HexColor('#D7DEE6'))
            c.setFont('Inter', 8.7)
            c.drawString(x + 9 * mm, y, _tronquer(joli_titre(titre_chap), 'Inter', 8.7, 128 * mm))
            c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.17))
            c.setLineWidth(0.4)
            c.line(x, y - 2.4 * mm, x + 142 * mm, y - 2.4 * mm)
            y -= 6.4 * mm

    def _colophon(self, c, doc):
        c.setFillColor(HexColor('#0F2438'))
        c.circle(LARGEUR * 0.92, HAUTEUR * 0.95, 92 * mm, stroke=0, fill=1)
        x = 26 * mm
        c.setFillColor(OR)
        c.setFont('Inter-Bd', 7.1)
        c.drawString(x, HAUTEUR - 118 * mm, 'FIN DU GUIDE')
        c.setFillColor(BLANC)
        c.setFont('Serif-Sb', 20)
        c.drawString(x, HAUTEUR - 130 * mm, "YELEN SCHOOL")
        c.setFillColor(HexColor('#B9C4D0'))
        c.setFont('Serif-It', 12.5)
        c.drawString(x, HAUTEUR - 138 * mm, "Gestion scolaire complète — Burkina Faso")
        c.setStrokeColor(OR)
        c.setLineWidth(1.1)
        c.line(x, HAUTEUR - 145 * mm, x + 28 * mm, HAUTEUR - 145 * mm)
        c.setFillColor(HexColor('#8C97A5'))
        c.setFont('Inter', 8.4)
        for k, ligne in enumerate(['Édition %s — %s' % (self.version_ouvrage, self.date_ouvrage),
                                   '%d chapitres, %d pages' % (self.nb_chapitres, self.nb_pages)]):
            c.drawString(x, HAUTEUR - 153 * mm - k * 5.2 * mm, ligne)

    def _liminaire(self, c, doc):
        c.setFillColor(HexColor('#8C97A5'))
        c.setFont('Inter', 7.2)
        c.drawCentredString(LARGEUR / 2, MARGE_BAS - 6.5 * mm, _romain(max(1, doc.page - 1)))

    def _corps(self, c, doc):
        y = HAUTEUR - MARGE_HAUT + 8.4 * mm
        c.setFillColor(HexColor('#8C97A5'))
        c.setFont('Inter-Md', 6.4)
        c.drawString(MARGE_INT, y, self.livre)
        courant = ''
        for page, titre in self.chapitres_pages:
            if page <= doc.page:
                courant = titre
            else:
                break
        if courant:
            c.setFillColor(OR)
            c.setFont('Inter-Sb', 6.4)
            c.drawRightString(LARGEUR - MARGE_EXT, y, courant.upper())
        c.setStrokeColor(FILET)
        c.setLineWidth(0.4)
        c.line(MARGE_INT, y - 3.2 * mm, LARGEUR - MARGE_EXT, y - 3.2 * mm)
        c.setFillColor(MARINE)
        c.setFont('Serif-Sb', 10)
        folio = doc.page - doc.debut_corps + 1 if doc.debut_corps else doc.page
        c.drawCentredString(LARGEUR / 2, MARGE_BAS - 11 * mm, str(folio))


def _logo(c, x, y, t):
    c.saveState()
    c.setFillColor(HexColor('#12233A'))
    c.roundRect(x, y, t, t, t * 0.2, stroke=0, fill=1)
    c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.35))
    c.setLineWidth(0.5)
    c.roundRect(x, y, t, t, t * 0.2, stroke=1, fill=0)
    c.setFillColor(BLANC)
    p = c.beginPath()
    p.moveTo(x + t * 0.5, y + t * 0.84)
    p.lineTo(x + t * 0.22, y + t * 0.63)
    p.lineTo(x + t * 0.22, y + t * 0.4)
    p.lineTo(x + t * 0.5, y + t * 0.56)
    p.lineTo(x + t * 0.78, y + t * 0.4)
    p.lineTo(x + t * 0.78, y + t * 0.63)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(VERT)
    c.rect(x + t * 0.27, y + t * 0.25, t * 0.46, t * 0.035, stroke=0, fill=1)
    c.setFillColor(Color(0, 0.66, 0.42, alpha=0.5))
    c.rect(x + t * 0.35, y + t * 0.17, t * 0.3, t * 0.022, stroke=0, fill=1)
    c.restoreState()


def _romain(n):
    out = ''
    for v, s in [(1000, 'm'), (900, 'cm'), (500, 'd'), (400, 'cd'), (100, 'c'), (90, 'xc'), (50, 'l'),
                 (40, 'xl'), (10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')]:
        while n >= v:
            out, n = out + s, n - v
    return out


def _couper(txt, police, taille, largeur):
    lignes, courant = [], ''
    for mot in txt.split():
        essai = f'{courant} {mot}'.strip()
        if pdfmetrics.stringWidth(essai, police, taille) <= largeur:
            courant = essai
        else:
            if courant:
                lignes.append(courant)
            courant = mot
    if courant:
        lignes.append(courant)
    return lignes


def _tronquer(txt, police, taille, largeur):
    if pdfmetrics.stringWidth(txt, police, taille) <= largeur:
        return txt
    while txt and pdfmetrics.stringWidth(txt + '…', police, taille) > largeur:
        txt = txt[:-1]
    return txt + '…'


# ── Pages liminaires ─────────────────────────────────────────────────────────
def _en_tete_section(kicker, titre):
    return [Paragraph(kicker, ParagraphStyle('k', fontName='Inter-Bd', fontSize=7.1, textColor=OR,
                                             spaceAfter=5 * mm)),
            Paragraph(titre, ParagraphStyle('t', fontName='Serif-Sb', fontSize=20.5, leading=24.5,
                                            textColor=MARINE, spaceAfter=3 * mm)),
            Filet(22 * mm, 1.2, OR, apres=8 * mm)]


def fiche_document(version, date_txt, chapitres, st):
    flux = _en_tete_section('FICHE DU DOCUMENT', "YELEN SCHOOL<br/>Guide d'utilisation")
    lignes = [
        ('Logiciel', "YELEN SCHOOL — gestion d'établissement scolaire (Django, mode autonome SQLite ou serveur "
                     'PostgreSQL), interface en français.'),
        ('Version documentée', version),
        ('Édition du guide', date_txt),
        ('Public', 'Direction, secrétariat, comptabilité, enseignants, surveillants, parents et élèves.'),
        ('Portée', f'{len(chapitres)} chapitres : de la connexion aux fonctions les plus récentes, avec les écrans '
                   "réels de l'application et des exemples de saisie champ par champ."),
        ('Rédaction', 'Équipe YELEN SCHOOL'),
    ]
    donnees = [[Paragraph(lib.upper(), ParagraphStyle('fl', fontName='Inter-Bd', fontSize=6.8, textColor=SOURDINE,
                                                      leading=9.2)),
                Paragraph(inline(val), ParagraphStyle('fv', fontName='Inter', fontSize=8.8, leading=12.6,
                                                      textColor=ENCRE_DOUCE))]
               for lib, val in lignes]
    t = Table(donnees, colWidths=[38 * mm, CORPS_L - 38 * mm], hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0.4, FILET),
                           ('TOPPADDING', (0, 0), (-1, -1), 2.5 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5 * mm),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 1), (-1, -1), 2 * mm)]))
    flux += [t, Spacer(1, 6 * mm)]
    for para in ["Ce manuel décrit le comportement réel du logiciel : chaque écran cité existe, chaque libellé de "
                 "champ correspond à celui affiché par l'application. Les captures proviennent d'une base de "
                 'démonstration, avec des noms et des montants fictifs.',
                 "Il s'utilise de deux façons : en lecture linéaire pour une prise en main complète, ou comme "
                 'référence — le sommaire donne la page de chaque chapitre.']:
        flux.append(Paragraph(inline(para), ParagraphStyle('fi', fontName='Inter', fontSize=8.9, leading=13.2,
                                                           textColor=ENCRE_DOUCE, alignment=TA_JUSTIFY,
                                                           spaceAfter=2.6 * mm)))
    flux.append(PageBreak())
    return flux


def mode_emploi(st):
    flux = _en_tete_section("MODE D'EMPLOI DU MANUEL", 'Comment lire ce guide')
    flux.append(Paragraph("Quatre familles d'encadrés ponctuent le texte. Elles signalent ce qui fait gagner du "
                          "temps, ce qui évite une erreur, et ce qui relève d'une règle de gestion.",
                          ParagraphStyle('p', fontName='Inter', fontSize=9, leading=13.4, textColor=ENCRE_DOUCE,
                                         alignment=TA_JUSTIFY, spaceAfter=4 * mm)))
    for zone, explication in [
            ('astuce', 'Raccourci, réglage ou méthode qui fait gagner du temps au quotidien.'),
            ('alerte', 'Point de vigilance : une erreur ici coûte une correction ou une ressaisie.'),
            ('acces', "Chemin exact dans le menu et droits nécessaires pour ouvrir l'écran."),
            ('regle', 'Comportement imposé par le logiciel : il ne peut pas être contourné.')]:
        flux.append(Encadre(CORPS_L, [Paragraph(inline(explication), st['zone_fin'])], zone))
        flux.append(Spacer(1, 2.6 * mm))
    flux += [Spacer(1, 8 * mm),
             Paragraph('Repères typographiques', ParagraphStyle('h2b', fontName='Serif-Sb', fontSize=14,
                                                                leading=18, textColor=MARINE, spaceAfter=3 * mm))]
    reperes = [
        ('Chemins de menu', "Écrits en clair ou entre accents graves, par exemple Finances → Paiements : ce sont "
                            "les libellés que vous voyez à l'écran."),
        ('Champs à saisir', "Le nom exact du champ est cité entre guillemets droits, suivi d'un exemple de valeur "
                            'lorsque plusieurs formats existent.'),
        ('Blocs monospace', "Commandes à recopier telles quelles, sorties de console ou arborescences de fichiers ; "
                            "ils se lisent en largeur et n'ont pas à être traduits."),
        ('Figures', 'Chaque capture est numérotée et légendée sous son cadre.'),
        ('Tableaux', "Ils reprennent la structure exacte des écrans ou des fichiers : la première ligne est "
                     "l'en-tête affiché."),
    ]
    donnees = [[Paragraph(lib.upper(), ParagraphStyle('rl', fontName='Inter-Bd', fontSize=6.7,
                                                      textColor=HexColor('#8A6A32'), leading=9)),
                Paragraph(inline(txt), st['cellule'])] for lib, txt in reperes]
    t = Table(donnees, colWidths=[36 * mm, CORPS_L - 36 * mm], hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0.4, FILET),
                           ('TOPPADDING', (0, 0), (-1, -1), 2.2 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2 * mm),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 1), (-1, -1), 2 * mm)]))
    flux.append(t)
    return flux


def sommaire(chapitres, pages, st):
    """Sommaire paginé : parties en capitales d'or, chapitres et folio en serif."""
    flux = [PageBreak(), Paragraph('Sommaire', ParagraphStyle('st', fontName='Serif-Sb', fontSize=24, leading=28,
                                                 textColor=MARINE, spaceAfter=1.5 * mm)),
            Paragraph('Chapitres et parties, avec leur page.', ParagraphStyle('si', fontName='Inter-It',
                                                                              fontSize=8.6, textColor=SOURDINE,
                                                                              spaceAfter=7 * mm))]
    par_num = {c['num']: c['titre'] for c in chapitres}
    for lettre, titre, _resume, nums in PARTIES:
        presents = [n for n in nums if n in par_num]
        if not presents:
            continue
        flux.append(Spacer(1, 4.4 * mm))
        flux.append(Paragraph(f'PARTIE {lettre} &nbsp;·&nbsp; {titre.upper()}',
                              ParagraphStyle('sp', fontName='Inter-Bd', fontSize=7.4, textColor=OR,
                                             spaceAfter=1.6 * mm)))
        flux.append(Filet(CORPS_L, 0.6, OR_CLAIR, apres=2 * mm))
        for n in presents:
            titre_chap = joli_titre(par_num[n])
            num = Paragraph(f'{n:02d}', ParagraphStyle('cn', fontName='Serif-Sb', fontSize=9.6, textColor=OR))
            txt = Paragraph(inline(titre_chap), ParagraphStyle('ct', fontName='Inter-Sb', fontSize=9.3,
                                                               leading=12, textColor=MARINE))
            folio = Paragraph(str(pages.get(n, '')), ParagraphStyle('cp', fontName='Serif-Sb', fontSize=9.6,
                                                                    textColor=MARINE, alignment=2))
            t = Table([[num, txt, folio]], colWidths=[9 * mm, CORPS_L - 20 * mm, 11 * mm], hAlign='LEFT')
            t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                   ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                   ('TOPPADDING', (0, 0), (-1, -1), 1.8 * mm),
                                   ('BOTTOMPADDING', (0, 0), (-1, -1), 1.8 * mm),
                                   ('LINEBELOW', (0, 0), (-1, -1), 0.3, HexColor('#D5DBE2'))]))
            flux.append(t)
    return flux


# ── Assemblage ───────────────────────────────────────────────────────────────
def _corps_du_guide(doc, chapitres, st, registre):
    """Flux du corps : pages d'ouverture, chapitres, repères de pagination.

    Les sauts sont posés **en tête** de chaque page (jamais en fin de contenu et jamais deux
    fois de suite) : aucune page blanche ne peut apparaître à une frontière de chapitre ou de partie.
    """
    flux, ctx = [], {'ancres': {}, 'figures': 0, 'sections': []}
    par_num = {c['num']: c for c in chapitres}
    registre = registre if registre is not None else {}
    deja = set()

    def chapitre(num, titre, md):
        flux.append(NextPageTemplate('corps'))
        flux.append(PageBreak())
        flux.append(Signet(f'{num:02d} · {joli_titre(titre)}', 2))
        flux.append(Repere(num, registre))
        flux.append(_Chapeau(num, titre, st))
        flux.extend(composer(md, st, CORPS_L, ctx))

    for lettre, titre, resume, nums in PARTIES:
        presents = [(n, par_num[n]['titre']) for n in nums if n in par_num]
        if not presents:
            continue
        flux.append(NextPageTemplate('pleine'))
        flux.append(PageBreak())
        flux.append(Signet(f'Partie {lettre} · {joli_titre(titre)}', 1))
        flux.append(_PleinePage('ouverture', (lettre, titre, resume, presents)))
        for n, _t in presents:
            deja.add(n)
            chapitre(n, par_num[n]['titre'], par_num[n]['md'])
    for c in chapitres:
        if c['num'] not in deja:
            chapitre(c['num'], c['titre'], c['md'])
    flux.append(NextPageTemplate('pleine'))
    flux.append(PageBreak())
    flux.append(_PleinePage('colophon'))
    return flux


class _PleinePage(Flowable):
    """Page entière sans texte courant (ouverture de partie, colophon).

    Le fond est dessiné par le flux : il ne peut donc pas se décaler d'une page par rapport à
    son contenu, contrairement aux fonds posés par les gabarits de page.
    """

    def __init__(self, genre, bloc=None):
        super().__init__()
        self.genre, self.bloc = genre, bloc

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        doc = self.canv._doctemplate
        doc.pages_pleines[self.canv.getPageNumber()] = (self.genre, self.bloc)


class _Chapeau(Flowable):
    """Chapeau de chapitre : numéro d'or, titre serif, surtitre de section et filet."""

    MARGE_HAUT = 5 * mm

    def __init__(self, num, titre, st):
        super().__init__()
        self.num, self.titre, self.st = num, titre, st
        self._h = 0

    def wrap(self, aw, ah):
        titre_propre = joli_titre(self.titre)
        self._titre = Paragraph(inline(titre_propre),
                                ParagraphStyle('ct', fontName='Serif-Sb', fontSize=21.5, leading=25.5,
                                               textColor=MARINE, spaceAfter=0))
        self._num = Paragraph(f'<font name="Serif" color="#B0803A" size="31">{self.num:02d}</font>',
                              ParagraphStyle('cn', fontName='Serif', fontSize=31, leading=30,
                                             textColor=OR, spaceAfter=0))
        self._num.wrap(20 * mm, ah)
        self._titre.wrap(aw - 20 * mm, ah)
        self._h = max(self._num.height, self._titre.height) + self.MARGE_HAUT + 5.4 * mm
        return aw, self._h

    def draw(self):
        haute = self._h - self.MARGE_HAUT
        self._num.drawOn(self.canv, 0, haute - self._num.height + 1.4 * mm)
        self._titre.drawOn(self.canv, 19.6 * mm, haute - self._num.height + 1.4 * mm)
        self.canv.setStrokeColor(FILET)
        self.canv.setLineWidth(0.5)
        self.canv.line(0, 0.9 * mm, self.canv._doctemplate.width - MARGE_INT - MARGE_EXT, 0.9 * mm)


def assembler(source: Path, sortie: Path):
    """Compose le PDF en deux passes : pagination mesurée, puis sommaire et en-têtes définitifs."""
    enregistrer_polices()
    st = styles()
    _, corps_txt = lire_entete(source.read_text(encoding='utf-8'))
    version = (RACINE / 'VERSION').read_text(encoding='utf-8').strip()
    date_txt = date.today().strftime('%d/%m/%Y')
    chapitres = decouper(corps_txt)
    chapitres_map = {c['num']: c for c in chapitres}

    def flux_liminaires(pages):
        flux = [NextPageTemplate('liminaire'), PageBreak()]
        flux += fiche_document(version, date_txt, chapitres, st)
        flux += mode_emploi(st)
        flux += sommaire(chapitres, pages, st)
        return flux

    # — passe 1 : composition réelle, sommaire aux folios provisoires ; on relève la pagination
    doc = Guide(sortie, version, date_txt, chapitres)
    doc.build(flux_liminaires({}) + _corps_du_guide(doc, chapitres, st, doc.registre))
    pages = dict(doc.registre)
    debut = min(pages.values()) if pages else 0        # folio 1 = première page de chapitre
    total = doc.page
    entetes = sorted((page, f'{num:02d} · {joli_titre(chapitres_map[num]["titre"])}')
                     for num, page in pages.items() if num in chapitres_map)

    # — passe 2 : mêmes pages, sommaire réel et en-têtes courants
    doc2 = Guide(sortie, version, date_txt, chapitres)
    doc2.pleines, doc2.chapitres_pages = doc.pages_pleines, entetes
    doc2.debut_corps, doc2.nb_pages = debut, total
    doc2.build(flux_liminaires(pages) + _corps_du_guide(doc2, chapitres, st, {}))
    print(f'  {len(chapitres)} chapitres · {doc2.page} pages · folio 1 = p. {debut}')
    return doc2


if __name__ == '__main__':
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DOCS / 'GUIDE_UTILISATION_YELEN_SCHOOL.md'
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DOCS / 'GUIDE_UTILISATION_YELEN_SCHOOL.pdf'
    assembler(src, out)
    print(f'PDF composé : {out}')
