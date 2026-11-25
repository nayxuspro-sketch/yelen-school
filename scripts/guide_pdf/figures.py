"""Schémas vectoriels du guide de déploiement.

Chaque fonction reçoit un canevas, une largeur et une hauteur en points, et dessine son schéma
dans ce cadre (origine en bas à gauche). Les tracés sont purement vectoriels : ils restent nets
à l'impression comme à l'écran, et aucune image bitmap n'est nécessaire.
"""
from __future__ import annotations

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

ENCRE = HexColor('#0A1628')
CREUX = HexColor('#14283F')
OR = HexColor('#B0803A')
OR_CLAIR = HexColor('#D8B675')
IVOIRE = HexColor('#FBF9F4')
VERT = HexColor('#00A86B')
VERT_FONCE = HexColor('#067955')
VERT_PALE = HexColor('#EAF6F0')
BLEU_PALE = HexColor('#F1F5FA')
BLEU = HexColor('#34506F')
AMBRE = HexColor('#FDF6E8')
AMBRE_TRAIT = HexColor('#C58C2A')
AMBRE_ENCRE = HexColor('#8A5A12')
GRIS = HexColor('#6C7787')
GRIS_CLAIR = HexColor('#AEB9C6')
FILET = HexColor('#C9D0D8')
TEXTE = HexColor('#3B4655')
BLANC = HexColor('#FFFFFF')


def _cadre(c, x, y, l, h, fond=IVOIRE, trait=OR, epaisseur=0.6):
    c.setFillColor(fond)
    c.setStrokeColor(trait)
    c.setLineWidth(epaisseur)
    c.roundRect(x, y, l, h, 1.4 * mm, stroke=1, fill=1)
    c.setFillColor(trait)
    c.rect(x + 0.35 * mm, y + h - 0.8 * mm, l - 0.7 * mm, 0.7 * mm, stroke=0, fill=1)


def _texte(c, x, y, txt, police='Inter', taille=6.4, couleur=ENCRE):
    c.setFillColor(couleur)
    c.setFont(police, taille)
    c.drawString(x, y, txt)


def _fleche(c, x1, y1, x2, y2, couleur=OR, epaisseur=0.8):
    c.setStrokeColor(couleur)
    c.setFillColor(couleur)
    c.setLineWidth(epaisseur)
    c.line(x1, y1, x2 - 1.0 * mm, y2)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - 1.3 * mm, y2 + 0.65 * mm)
    p.lineTo(x2 - 1.3 * mm, y2 - 0.65 * mm)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _etapes(c, etapes, largeur, y0, hauteur, h_carte, titre=None, note=None):
    """Chaîne de cartes d'étapes, centrée verticalement dans la bande `[y0, y0 + hauteur]`."""
    marge_haut = 5.6 * mm if titre else 0.0
    marge_bas = 4.6 * mm if note else 0.2 * mm
    marge = 1.0 * mm
    if titre:
        _texte(c, marge + 0.4 * mm, y0 + hauteur - 3.6 * mm, titre.upper(), 'Inter-Bd', 5.7, OR)
    n = len(etapes)
    ecart = 2.6 * mm
    larg = (largeur - 2 * marge - ecart * (n - 1)) / n
    dispo = hauteur - marge_haut - marge_bas
    h_carte = max(16 * mm, min(h_carte, dispo))
    y = y0 + marge_bas + (dispo - h_carte) / 2
    for i, etape in enumerate(etapes):
        titre_e, lignes = etape[0], etape[1]
        final = i == n - 1
        x = marge + i * (larg + ecart)
        _cadre(c, x, y, larg, h_carte, VERT_PALE if final else IVOIRE, VERT if final else OR)
        _texte(c, x + 2.3 * mm, y + h_carte - 4.6 * mm, f'ÉTAPE {i + 1}', 'Inter-Bd', 5.0,
               VERT_FONCE if final else OR)
        _texte(c, x + 2.3 * mm, y + h_carte - 9.6 * mm, titre_e, 'Inter-Sb', 6.6, ENCRE)
        c.setStrokeColor(VERT if final else OR_CLAIR)
        c.setLineWidth(0.6)
        c.line(x + 2.3 * mm, y + h_carte - 12.4 * mm, x + 8.3 * mm, y + h_carte - 12.4 * mm)
        for k, ligne in enumerate(lignes):
            _texte(c, x + 2.3 * mm, y + 3.4 * mm + (len(lignes) - 1 - k) * 3.4 * mm, ligne, 'Inter', 5.2, TEXTE)
        if not final:
            _fleche(c, x + larg + 0.35 * mm, y + h_carte / 2, x + larg + ecart - 0.35 * mm,
                    y + h_carte / 2)
    if note:
        _texte(c, marge + 0.4 * mm, y0 + 1.0 * mm, note, 'Inter', 5.2, GRIS)


# ── Architecture du serveur d'école ─────────────────────────────────────────
def architecture(c, largeur, hauteur, compact=False):
    """Accès, cinq conteneurs Docker et hôte Windows."""
    marge = 1.0 * mm
    h_hote = 11.2 * mm
    h_acces = 12.4 * mm
    y_hote = marge
    y_acces = hauteur - marge - h_acces
    y_docker = y_hote + h_hote + 3.4 * mm
    h_docker = y_acces - 2.8 * mm - y_docker

    # hôte
    c.setFillColor(ENCRE)
    c.roundRect(marge, y_hote, largeur - 2 * marge, h_hote, 1.4 * mm, stroke=0, fill=1)
    _texte(c, marge + 3.0 * mm, y_hote + h_hote - 4.4 * mm, 'HÔTE WINDOWS  ·  C:\\YELEN-SCHOOL',
           'Inter-Sb', 6.2, BLANC)
    _texte(c, marge + 3.0 * mm, y_hote + 2.8 * mm,
           '.env  ·  logs\\  ·  data\\  ·  media\\  ·  volumes Docker conservés entre les mises à jour',
           'Inter', 5.3, GRIS_CLAIR)

    # accès
    larg = (largeur - 2 * marge - 2 * 2.6 * mm) / 3
    acces = [('Poste du réseau local', 'http://NOM-PC:8001', BLEU_PALE, BLEU),
             ('HTTPS local (option)', 'https://NOM-PC:8443', VERT_PALE, VERT),
             ('Internet — portail parents', 'Tailscale Funnel · 443', VERT_PALE, VERT)]
    for i, (titre, url, fond, trait) in enumerate(acces):
        x = marge + i * (larg + 2.6 * mm)
        _cadre(c, x, y_acces, larg, h_acces, fond, trait)
        _texte(c, x + 2.4 * mm, y_acces + h_acces - 4.4 * mm, titre, 'Inter-Sb', 6.1, ENCRE)
        _texte(c, x + 2.4 * mm, y_acces + h_acces - 8.8 * mm, url, 'Mono', 5.1, TEXTE)

    # hôte Docker
    c.setFillColor(IVOIRE)
    c.setStrokeColor(FILET)
    c.setLineWidth(0.6)
    c.setDash(2.2, 1.8)
    c.roundRect(marge, y_docker, largeur - 2 * marge, h_docker, 1.4 * mm, stroke=1, fill=1)
    c.setDash()
    _texte(c, marge + 2.6 * mm, y_docker + h_docker - 4.0 * mm, 'DOCKER DESKTOP  ·  RÉSEAU INTERNE',
           'Inter-Bd', 5.2, GRIS)
    haut = y_docker + h_docker - 7.6 * mm
    h_carte = (haut - y_docker - 2.6 * mm - 2.2 * mm) / 2
    largeur_carte = (largeur - 2 * marge - 4.0 * mm - 2 * 2.2 * mm) / 3
    rangees = [[('proxy', 'Caddy · TLS', 'ports 8001 et 8443', VERT_PALE, VERT),
                ('web', 'Django + Gunicorn', 'port 8000', VERT_PALE, VERT),
                ('sms', 'réception des SMS', 'webhook passerelle', IVOIRE, OR)],
               [('db', 'PostgreSQL 15', 'volume pgdata', IVOIRE, OR),
                ('redis', 'cache, sessions, files', 'volume redisdata', IVOIRE, OR),
                ('backups\\', 'dump + médias', 'copie hors machine', IVOIRE, OR)]]
    for r, rangee in enumerate(rangees):
        y = haut - (r + 1) * h_carte - r * 2.2 * mm
        for i, (nom, role, detail, fond, trait) in enumerate(rangee):
            x = marge + 2.0 * mm + i * (largeur_carte + 2.2 * mm)
            _cadre(c, x, y, largeur_carte, h_carte, fond, trait)
            _texte(c, x + 2.1 * mm, y + h_carte - 4.0 * mm, nom, 'Mono-Sb', 6.2, ENCRE)
            _texte(c, x + 2.1 * mm, y + h_carte - 7.8 * mm, role, 'Inter', 5.2, TEXTE)
            if h_carte >= 10.4 * mm:
                _texte(c, x + 2.1 * mm, y + h_carte - 11.2 * mm, detail, 'Inter', 4.9, GRIS)

    # liaisons verticales
    x_milieu = largeur / 2
    _fleche(c, x_milieu, y_acces - 0.3 * mm, x_milieu, y_docker + h_docker + 0.5 * mm, OR_CLAIR)
    _fleche(c, x_milieu, y_docker - 0.3 * mm, x_milieu, y_hote + h_hote + 0.5 * mm, OR_CLAIR)


# ── Cycle d'une sauvegarde ──────────────────────────────────────────────────
def sauvegarde(c, largeur, hauteur, compact=False):
    """Export, chiffrement, rétention, copie externe, essai de restauration."""
    etapes = [('Export', ['.dump PostgreSQL', '+ _media.tar.gz']),
              ('Chiffrement', ['suffixe .enc', 'phrase secrète à part']),
              ('Rétention', ['30 paires par défaut', '-Keep pour ajuster']),
              ('Copie externe', ['disque, NAS, autre poste', 'hors du serveur (§5.2)']),
              ('Essai', ['restauration réelle', 'une fois par trimestre'])]
    h_encart = 0.0 if compact else 11.6 * mm
    bande = hauteur - h_encart - (1.6 * mm if not compact else 0)
    _etapes(c, etapes, largeur, 0.0 if compact else h_encart + 1.2 * mm, bande, 22.5 * mm)
    if not compact:
        marge = 1.0 * mm
        c.setFillColor(AMBRE)
        c.setStrokeColor(AMBRE_TRAIT)
        c.setLineWidth(0.6)
        c.roundRect(marge, 0.6 * mm, largeur - 2 * marge, h_encart - 1.2 * mm, 1.2 * mm, stroke=1, fill=1)
        c.setFillColor(AMBRE_TRAIT)
        c.rect(marge + 1.2 * mm, 0.6 * mm + 1.4 * mm, 0.9 * mm, h_encart - 4.0 * mm, stroke=0, fill=1)
        _texte(c, marge + 4.2 * mm, h_encart - 4.2 * mm,
               "Une sauvegarde jamais restaurée n'est pas une sauvegarde prouvée.", 'Inter-Sb', 5.9, AMBRE_ENCRE)
        _texte(c, marge + 4.2 * mm, 2.6 * mm,
               "Fichier tronqué, phrase secrète perdue, volume média absent : l'essai trimestriel est la seule preuve.",
               'Inter', 5.2, AMBRE_ENCRE)


# ── Mise à jour en un clic ──────────────────────────────────────────────────
def mise_a_jour(c, largeur, hauteur, compact=False):
    """Cinq étapes, garanties de retour arrière et options du script."""
    etapes = [('Version', ['VERSION + dépôt', 'GitHub (main)']),
              ('Sauvegarde', ['complète et chiffrée', '(§5)']),
              ('Mise à jour', ['code, image,', 'redémarrage']),
              ('Contrôle', ["/health/ jusqu'à la", 'bonne version']),
              ('Trois contrôles', ['version, conteneurs,', 'recette 2 min (§8.5)'])]
    marge = 1.0 * mm
    if compact:
        _etapes(c, etapes, largeur, 0.0, hauteur, 22.5 * mm)
        return
    h_garanties = 11.6 * mm
    h_pied = 4.4 * mm
    _etapes(c, etapes, largeur, h_garanties + h_pied, hauteur - h_garanties - h_pied, 24.5 * mm,
            titre='Mise à jour en un clic — mettre-a-jour.bat')
    larg = (largeur - 2 * marge - 3.2 * mm) / 2
    for i, (titre, detail, fond, trait, teinte) in enumerate([
            ('Sauvegarde impossible', "la mise à jour est annulée, rien n'est modifié.", AMBRE, AMBRE_TRAIT,
             AMBRE_ENCRE),
            ('Échec de reconstruction', "l'ancienne version est reconstruite et redémarrée (§8.4).", BLEU_PALE, BLEU,
             BLEU)]):
        x = marge + i * (larg + 3.2 * mm)
        _cadre(c, x, h_pied, larg, h_garanties - 1.0 * mm, fond, trait)
        _texte(c, x + 2.4 * mm, h_pied + h_garanties - 5.2 * mm, titre, 'Inter-Sb', 5.9, teinte)
        _texte(c, x + 2.4 * mm, h_pied + 2.6 * mm, detail, 'Inter', 5.2, TEXTE)
    _texte(c, marge, 1.0 * mm,
           'Journal : logs\\mise-a-jour.log  ·  options : -SansSauvegarde, -DelaiAttente 600', 'Inter', 5.1, GRIS)


# ── Variantes compactes pour les ouvertures de partie ───────────────────────
def conteneurs(c, largeur, hauteur):
    """Bandeau de l'ouverture de partie : cinq conteneurs alignés au-dessus de l'hôte Windows."""
    marge = 1.0 * mm
    h_hote = 8.4 * mm
    h_carte = hauteur - h_hote - 2.6 * mm - 2 * marge
    n = 5
    ecart = 2.2 * mm
    larg = (largeur - 2 * marge - ecart * (n - 1)) / n
    cartes = [('proxy', 'Caddy · TLS'), ('web', 'Django'), ('sms', 'SMS'), ('db', 'PostgreSQL'),
              ('redis', 'Redis')]
    for i, (nom, role) in enumerate(cartes):
        x = marge + i * (larg + ecart)
        _cadre(c, x, hauteur - marge - h_carte, larg, h_carte, VERT_PALE if i < 3 else IVOIRE,
               VERT if i < 3 else OR)
        _texte(c, x + 2.2 * mm, hauteur - marge - 4.2 * mm, nom, 'Mono-Sb', 6.2, ENCRE)
        if h_carte > 8.6 * mm:
            _texte(c, x + 2.2 * mm, hauteur - marge - 7.6 * mm, role, 'Inter', 5.1, TEXTE)
    c.setFillColor(ENCRE)
    c.roundRect(marge, marge * 0.4, largeur - 2 * marge, h_hote, 1.0 * mm, stroke=0, fill=1)
    _texte(c, marge + 2.6 * mm, marge * 0.4 + 3.0 * mm, 'HÔTE WINDOWS  ·  C:\\YELEN-SCHOOL  ·  volumes Docker',
           'Inter-Sb', 5.6, BLANC)


def installation(c, largeur, hauteur):
    _etapes(c, [('Distribution', ['archive client', 'signée']),
                ('Docker', ['images chargées', 'volumes créés']),
                ('Premier accès', ['compte admin', '.env généré']),
                ('Validation', ['/health/ = 200', 'licence active'])],
            largeur, 0.0, hauteur, 22.0 * mm)


def sauvegarde_mini(c, largeur, hauteur):
    sauvegarde(c, largeur, hauteur, compact=True)


def retour(c, largeur, hauteur):
    _etapes(c, [('Restaurer', ['.dump + médias', 'essai à blanc']),
                ('Mettre à jour', ['image, code', 'sans perte']),
                ('Contrôler', ['version, santé', 'recette 2 min']),
                ('Revenir', ['build précédent', 'automatique'])],
            largeur, 0.0, hauteur, 22.0 * mm)


def reseau_mini(c, largeur, hauteur):
    _etapes(c, [('Local', ['http, port 8001', 'pare-feu ouvert']),
                ('HTTPS local', ['Caddy, 8443', 'certificat interne']),
                ('Distance', ['Tailscale', 'Funnel 443']),
                ('Supervision', ['UptimeRobot', 'Healthchecks'])],
            largeur, 0.0, hauteur, 22.0 * mm)


def reprise(c, largeur, hauteur):
    _etapes(c, [('Nouvelle machine', ['Windows +', 'Docker Desktop']),
                ('Configuration', ['.env restauré', 'ou régénéré']),
                ('Données', ['dump + médias', 'vérifiés']),
                ('Tâches', ['planificateur', 'réarmé'])],
            largeur, 0.0, hauteur, 22.0 * mm)


def memo(c, largeur, hauteur):
    _etapes(c, [('Ne jamais', ['supprimer', 'les volumes']),
                ('Toujours', ['sauvegarder', "avant d'agir"]),
                ('Copier', ['hors de', 'la machine']),
                ('Tester', ['une restauration', 'par trimestre'])],
            largeur, 0.0, hauteur, 22.0 * mm)


DESSINS = {
    'architecture': architecture,
    'sauvegarde': sauvegarde,
    'mise_a_jour': mise_a_jour,
    'conteneurs': conteneurs,
    'installation': installation,
    'sauvegarde_mini': sauvegarde_mini,
    'retour': retour,
    'reseau_mini': reseau_mini,
    'reprise': reprise,
    'memo': memo,
}


# ── Point d'entrée ──────────────────────────────────────────────────────────
def dessiner(nom, c, largeur, hauteur):
    """Dessine le schéma `nom` dans le cadre (largeur, hauteur) en points, origine en bas à gauche."""
    DESSINS[nom](c, largeur, hauteur)
