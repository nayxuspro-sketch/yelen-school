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

try:                                     # importé comme paquet (scripts/guide_pdf)
    from guide_pdf import figures as _figures
except ImportError:                      # exécuté depuis le dossier
    import figures as _figures

# ── Charte ───────────────────────────────────────────────────────────────────
ENCRE, ENCRE_DOUCE, SOURDINE = HexColor('#16202E'), HexColor('#3B4655'), HexColor('#6C7787')
MARINE, MARINE_2 = HexColor('#0A1628'), HexColor('#12233A')
VERT, VERT_FONCE = HexColor('#00A86B'), HexColor('#067955')
OR, OR_CLAIR = HexColor('#B0803A'), HexColor('#D8B675')
FILET, FILET_FONCE, BLANC = HexColor('#E2E6EB'), HexColor('#C9D0D8'), HexColor('#FFFFFF')
MARINE_TETE = HexColor('#0F1E33')
MARINE_CARTE = HexColor('#14283F')   # fond des cartes du plan d'architecture
ZEBRE = HexColor('#F8F9FB')

# Rôles éditoriaux de chaque chapitre : (étiquette, icône) — pastille du chapeau, ouverture de partie.
CHAPEAUX = {}       # numéro → (étiquette, icône)
FIGURES = {}        # numéro de chapitre → [(légende, dessin, hauteur en mm)]
OUVERTURE_SCHEMA = {}   # lettre de partie → (dessin, légende)

ZONES = {   # type → (fond, filet, libellé, couleur du libellé, icône)
    'astuce': (HexColor('#F0F9F4'), VERT, 'ASTUCE', VERT_FONCE, 'ampoule'),
    'alerte': (HexColor('#FDF6E8'), HexColor('#C58C2A'), 'AVERTISSEMENT', HexColor('#8A5A12'), 'alerte'),
    'acces': (HexColor('#F1F5FA'), HexColor('#34506F'), 'ACCÈS', HexColor('#2C3E55'), 'cible'),
    'note': (HexColor('#F7F6F3'), OR, 'NOTE', HexColor('#8A6A32'), 'note'),
    'securite': (HexColor('#FBF1F1'), HexColor('#A8443B'), 'SÉCURITÉ', HexColor('#8C332B'), 'cadenas'),
    'regle': (HexColor('#FBF1F1'), HexColor('#A8443B'), 'RÈGLE DE SÉCURITÉ', HexColor('#8C332B'), 'cadenas'),
}

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
POLICES, DOCS = ICI / 'fonts', RACINE / 'docs'

LARGEUR, HAUTEUR = 210 * mm, 297 * mm
MARGE_INT, MARGE_EXT, MARGE_HAUT, MARGE_BAS = 26 * mm, 20 * mm, 24 * mm, 20 * mm
CORPS_L = LARGEUR - MARGE_INT - MARGE_EXT

# ── Profil documentaire ──────────────────────────────────────────────────────
# Le moteur est partagé par les deux guides ; ce profil porte tout ce qui les distingue
# (identité de couverture, parties, textes de liminaires, pastilles d'ouverture).
UTILISATION_PROFIL = {
    'cle': 'utilisation',
    'livre': "YELEN SCHOOL · GUIDE D'UTILISATION",
    'titre_pdf': "YELEN SCHOOL — Guide d'utilisation",
    'sujet_pdf': 'Manuel officiel du logiciel de gestion scolaire',
    'surtitre': 'MANUEL OFFICIEL',
    'fichier': 'GUIDE_UTILISATION_YELEN_SCHOOL.md',
    'sortie': 'GUIDE_UTILISATION_YELEN_SCHOOL.pdf',
    'couverture_titre': ["Guide", "d'utilisation"],
    'couverture_sous_titre': ['Gestion scolaire complète — inscriptions, pédagogie,',
                              'finances, documents et communication avec les familles.'],
    'couverture_meta': [('DOCUMENT', "Guide d'utilisation"), ('VERSION', '{version}'),
                        ('MISE À JOUR', '{date}'), ('CHAPITRES', '{chapitres}')],
    'fiche_kicker': 'FICHE DU DOCUMENT',
    'fiche_titre': "YELEN SCHOOL<br/>Guide d'utilisation",
    'fiche': [
        ('Logiciel', "YELEN SCHOOL — gestion d'établissement scolaire (Django, mode autonome SQLite ou serveur "
                     'PostgreSQL), interface en français.'),
        ('Version documentée', '{version}'),
        ('Édition du guide', '{date}'),
        ('Public', 'Direction, secrétariat, comptabilité, enseignants, surveillants, parents et élèves.'),
        ('Portée', '{portee}'),
        ('Rédaction', 'Équipe YELEN SCHOOL'),
    ],
    'fiche_intro': [
        "Ce manuel décrit le comportement réel du logiciel : chaque écran cité existe, chaque libellé de "
        "champ correspond à celui affiché par l'application. Les captures proviennent d'une base de "
        'démonstration, avec des noms et des montants fictifs.',
        "Il s'utilise de deux façons : en lecture linéaire pour une prise en main complète, ou comme "
        'référence — le sommaire donne la page de chaque chapitre.',
    ],
    'mode_emploi_kicker': "MODE D'EMPLOI DU MANUEL",
    'mode_emploi_titre': 'Comment lire ce guide',
    'mode_emploi_intro': "Quatre familles d'encadrés ponctuent le texte. Elles signalent ce qui fait gagner du "
                         "temps, ce qui évite une erreur, et ce qui relève d'une règle de gestion.",
    'mode_emploi_zones': [
        ('astuce', 'Raccourci, réglage ou méthode qui fait gagner du temps au quotidien.'),
        ('alerte', 'Point de vigilance : une erreur ici coûte une correction ou une ressaisie.'),
        ('acces', "Chemin exact dans le menu et droits nécessaires pour ouvrir l'écran."),
        ('regle', 'Comportement imposé par le logiciel : il ne peut pas être contourné.'),
    ],
    'reperes_titre': 'Repères typographiques',
    'reperes': [
        ('Chemins de menu', "Écrits en clair ou entre accents graves, par exemple Finances → Paiements : ce sont "
                            "les libellés que vous voyez à l'écran."),
        ('Champs à saisir', "Le nom exact du champ est cité entre guillemets droits, suivi d'un exemple de valeur "
                            'lorsque plusieurs formats existent.'),
        ('Blocs monospace', "Commandes à recopier telles quelles, sorties de console ou arborescences de fichiers ; "
                            "ils se lisent en largeur et n'ont pas à être traduits."),
        ('Figures', 'Chaque capture est numérotée et légendée sous son cadre.'),
        ('Tableaux', "Ils reprennent la structure exacte des écrans ou des fichiers : la première ligne est "
                     "l'en-tête affiché."),
    ],
    'sommaire_sous': 'Chapitres et parties, avec leur page.',
    'ouverture_kicker': 'PARTIE',
    'chapeau_label': 'CHAPITRE',
    'colophon_kicker': 'FIN DU GUIDE',
    'colophon_titre': 'YELEN SCHOOL',
    'portee': "{chapitres} chapitres : de la connexion aux fonctions les plus récentes, avec les écrans réels "
              "de l'application et des exemples de saisie champ par champ.",
    'colophon_meta': ('{chapitres} chapitres · {pages} pages',),
    'colophon_sous': 'Gestion scolaire complète — Burkina Faso',
    'parties': [
        ('I', 'Prise en main', "Le contexte du produit, la connexion, le tableau de bord et les paramètres de "
                               "l'établissement : de quoi ouvrir l'application et la configurer.", [1, 2, 3]),
        ('II', 'Élèves, personnel et pédagogie', 'Inscriptions, dossiers du personnel, notes et bulletins, '
                                                 'présences et vie scolaire : le cœur du travail quotidien.',
         [4, 5, 6, 7, 8]),
        ('III', 'Argent et évaluation', 'Scolarité, encaissements, dépenses, examens officiels et vacations : '
                                        'tout ce qui se compte et se justifie.', [9, 10, 11]),
        ('IV', 'Documents et pilotage', 'Documents administratifs, licences, statistiques et état des '
                                        'fonctionnalités : les productions et les tableaux de bord de la direction.',
         [12, 13, 14, 15]),
        ('V', 'Références et interface', 'Questions fréquentes, glossaire et design system : le vocabulaire et les '
                                         "règles graphiques de l'application.", [16, 17, 18]),
        ('VI', 'Portails, innovations et familles', 'Portail parent, signature électronique, prédiction de '
                                                    'réussite, APC/API, bourses, assistant IA, budget, manuels, '
                                                    'hors ligne, communication, emploi du temps, localisations.',
         [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]),
        ('VII', 'Exploitation, sécurité et qualité', "Mode autonome, SMS des familles, galerie d'écrans, sécurité, "
                                                     'source de vérité, import de fichiers, services annexes, '
                                                     'contrôle qualité et offre hébergée.',
         [31, 32, 33, 34, 35, 36, 37, 38, 39]),
        ('VIII', 'Annexes pratiques', 'Exemples de saisie champ par champ : des valeurs réelles à recopier pour '
                                      'chaque formulaire du logiciel.', [40]),
    ],
}

# ── Profil du guide de déploiement ──────────────────────────────────────────
# Même charte, autre voix : le lecteur est un administrateur technique, pas un utilisateur.
DEPLOIEMENT_PROFIL = {
    'cle': 'deploiement',
    'fichier': 'GUIDE_DEPLOIEMENT_WINDOWS.md',
    'sortie': 'GUIDE_DEPLOIEMENT_WINDOWS.pdf',
    'livre': 'YELEN SCHOOL · GUIDE DE DÉPLOIEMENT',
    'edition': '13/11/2026',
    'ignorer': ('Sommaire',),
    'annexes': ('Règles essentielles à retenir',),
    'preambule': 'Installation locale autonome chez un client',
    'avant_propos_kicker': 'AVANT-PROPOS',
    'avant_propos_titre': 'À qui ce guide s’adresse',
    'avant_propos_texte': [
        "Ce guide est le mode d'emploi technique du serveur d'école. Il suppose un lecteur qui sait ouvrir une "
        "invite de commandes, éditer un fichier texte et redémarrer un service ; il ne suppose aucune connaissance "
        'de Django, de PostgreSQL ni de Docker.',
        "Chaque commande est donnée telle qu'elle doit être saisie, avec le résultat attendu juste après. Les "
        "opérations irréversibles — restauration, retour arrière, remise à zéro d'un mot de passe — sont signalées "
        "par un encadré de sécurité, à lire avant d'agir.",
    ],
    'fin_kicker': 'POUR ALLER PLUS LOIN',
    'fin_titre': 'Après ce guide',
    'fin': [
        "Ce guide décrit la version {version} du logiciel. Toute mise à jour de l'application s'accompagne "
        "d'une relecture du chapitre 8 et des trois contrôles qui le terminent.",
        "Le mode d'emploi fonctionnel — droits par rôle, écrans, exemples de saisie champ par champ — se trouve "
        "dans le guide d'utilisation (<i>docs/GUIDE_UTILISATION_YELEN_SCHOOL</i>). Les contrôles de "
        "commercialisation restant à exécuter sont listés dans <i>docs/VALIDATION_COMMERCIALISATION.md</i>.",
    ],
    'titre_pdf': 'YELEN SCHOOL — Guide de déploiement Windows',
    'sujet_pdf': "Installation, exploitation et maintenance du serveur d'école",
    'surtitre': 'GUIDE TECHNIQUE',
    'couverture_titre': ['Guide de', 'déploiement', 'Windows'],
    'couverture_sous_titre': ['Installation, configuration, sauvegardes, mises à jour et dépannage',
                              "du serveur d'école — cinq conteneurs Docker, PostgreSQL et Redis."],
    'couverture_meta': [('DOCUMENT', 'Déploiement Windows'), ('VERSION', '{version}'),
                        ('MISE À JOUR', '{date}'), ('CHAPITRES', '{chapitres}')],
    'fiche_kicker': 'FICHE DU DOCUMENT',
    'fiche_titre': 'YELEN SCHOOL<br/>Guide de déploiement Windows',
    'fiche': [
        ('Logiciel', "YELEN SCHOOL — gestion d'établissement scolaire, cinq conteneurs Docker "
                     '(<font name="Mono">proxy</font>, <font name="Mono">web</font>, '
                     '<font name="Mono">sms</font>, <font name="Mono">db</font>, '
                     '<font name="Mono">redis</font>).'),
        ('Version couverte', '{version}'),
        ('Édition du guide', '{date}'),
        ('Public', "Administrateur technique de l'établissement, ou prestataire qui installe la machine."),
        ('Objet', "Installer, exploiter, sauvegarder, mettre à jour et dépanner le serveur d'école sous Windows, "
                  "puis l'ouvrir au réseau local et, si besoin, à distance."),
        ('Environnement', 'Windows 10 ou 11, Docker Desktop avec WSL 2, PostgreSQL et Redis dans leurs volumes '
                          'Docker, accès Internet optionnel.'),
        ('Dossier', '<font name="Mono">C:\\YELEN-SCHOOL</font> — <font name="Mono">.env</font>, '
                    '<font name="Mono">logs\\</font>, <font name="Mono">data\\</font>, '
                    '<font name="Mono">media\\</font>'),
        ('Ports', '<font name="Mono">8001</font> (HTTP), <font name="Mono">8443</font> (HTTPS local et Tailscale '
                  'Serve), <font name="Mono">443</font> (portail parents par Funnel)'),
        ('Rédaction', 'Équipe YELEN SCHOOL'),
    ],
    'fiche_intro': [
        "Ce guide décrit une installation réelle, validée chez un client : les commandes, les chemins, les ports "
        "et les journaux cités existent sur le serveur d'école tel qu'il est livré.",
        "Il se lit dans l'ordre pour une installation neuve, puis se consulte chapitre par chapitre en "
        "exploitation — chaque chapitre commence par un rappel de ce qu'il protège.",
    ],
    'mode_emploi_kicker': "MODE D'EMPLOI DU GUIDE",
    'mode_emploi_titre': 'Comment lire ce guide technique',
    'mode_emploi_intro': "Ce guide se lit dans l'ordre lors d'une installation neuve, puis se consulte chapitre par "
                         "chapitre en exploitation. Quatre familles d'encadrés signalent ce qui protège les "
                         "données, ce qui coûte une panne, et ce qui ne se rattrape pas.",
    'mode_emploi_zones': [
        ('astuce', 'Réglage ou méthode qui fait gagner du temps sur le serveur, sans risque pour les données.'),
        ('alerte', "Point de vigilance : une erreur ici provoque une indisponibilité ou une perte de données."),
        ('acces', 'Chemin exact dans Windows, nom de fichier ou de conteneur concerné par la manipulation.'),
        ('regle', "Règle de sécurité du serveur : elle ne se contourne pas, même en cas d'urgence."),
    ],
    'reperes_titre': 'Repères de lecture',
    'reperes': [
        ('Commandes', "Blocs monospace à recopier tels quels dans PowerShell ou l'invite de commandes, depuis "
                      '<font name="Mono">C:\\YELEN-SCHOOL</font> sauf mention contraire.'),
        ('Résultats attendus', "Chaque commande est suivie de la sortie normale : un écart signale une anomalie "
                               'avant de poursuivre.'),
        ('Chemins de fichiers', 'Écrits entre accents graves ou en monospace : <font name="Mono">.env</font>, '
                                '<font name="Mono">logs\\</font>, <font name="Mono">data\\</font>, '
                                '<font name="Mono">media\\</font>.'),
        ('Schémas', "Trois schémas vectoriels expliquent l'architecture, le cycle de sauvegarde et la mise à jour ; "
                    'ils sont numérotés et légendés sous leur cadre.'),
        ('Encadrés de sécurité', 'Toute opération irréversible est précédée du rappel de la sauvegarde à faire et '
                                 'du moyen de revenir en arrière.'),
    ],
    'sommaire_sous': 'Parties, chapitres et annexes, avec leur page.',
    'colophon_kicker': 'FIN DU GUIDE',
    'colophon_titre': 'YELEN SCHOOL',
    'colophon_sous': "Serveur d'école — déploiement Windows",
    'portee': "{chapitres} chapitres : de l'architecture du serveur à la reprise sur une nouvelle machine, avec "
              "chaque commande et son résultat attendu.",
    'colophon_meta': ('{chapitres} chapitres · {pages} pages',),
    'parties': [
        ('I', 'Socle technique', "Ce que l'installation met en place : les cinq conteneurs, les prérequis de la "
                                 "machine, l'arborescence du dossier et la répartition sur plusieurs partitions.",
         [1]),
        ('II', 'Installation et première configuration', "De l'obtention des fichiers au premier accès réussi : "
                                                         'installation, fichier <font name="Mono">.env</font>, '
                                                         'compte initial, adresse locale, validations et licence '
                                                         'signée.', [2, 3]),
        ('III', 'Exploitation quotidienne', 'Démarrer, arrêter, lire les journaux, sauvegarder et vérifier une '
                                            'sauvegarde, programmer les tâches automatiques.', [4, 5, 6]),
        ('IV', 'Incidents et mises à jour', 'Restaurer après incident, mettre à jour sans perte de données, revenir '
                                            'en arrière et contrôler après chaque évolution.', [7, 8]),
        ('V', 'Réseau, accès et dépannage', 'Adresse locale, pare-feu Windows, HTTPS, portail parents, accès du '
                                            'personnel par Tailscale et remèdes aux pannes courantes.', [9, 10]),
        ('VI', "Continuité d'exploitation", 'Reprise sur une nouvelle machine, sans jamais perdre les volumes ni '
                                            "les données d'exploitation.", [11]),
        ('VII', 'Mémo de terrain', "Les règles à ne jamais oublier sur le serveur d'école, réunies sur une page "
                                   'à afficher dans le local technique.', ['Règles essentielles à retenir']),
    ],
}

# Profil actif : remplacé par `charger_profil()` avant chaque composition.
PROFIL = dict(UTILISATION_PROFIL)

# Parties extraites de la prose du guide, hors numérotation : ajoutées après les précédentes
PARTIES_ANNEXES = []


def parties():
    """Parties du document courant : celles du profil, augmentées des annexes déclarées."""
    return PROFIL['parties'] + PARTIES_ANNEXES


# Rôles éditoriaux des chapitres du guide de déploiement : (étiquette, icône)
CHAPEAUX_DEPLOIEMENT = {
    1: ('Socle technique', 'cube'),
    2: ('Installation', 'disque'),
    3: ('Configuration', 'reglage'),
    4: ('Exploitation', 'horloge'),
    5: ('Sauvegardes', 'archive'),
    6: ('Automatisation', 'engrenage'),
    7: ('Restauration', 'retour'),
    8: ('Mises à jour', 'fleche'),
    9: ('Réseau et accès', 'reseau'),
    10: ('Dépannage', 'outil'),
    11: ('Continuité', 'cycle'),
}

# Annexe hors numérotation, rassemblée en dernière partie
PARTIES_ANNEXES.append(
    ('VII', 'Mémo de terrain', "Les règles à ne jamais oublier sur le serveur d'école, réunies sur une page "
                               "à afficher dans le local technique.", ['Règles essentielles à retenir']))

# Figures dessinées à la composition, insérées avant le premier sous-titre du chapitre indiqué
FIGURES_DEPLOIEMENT = {
    1: [("Architecture du serveur d'école : accès, cinq conteneurs Docker et hôte Windows",
         'architecture', 74)],
    5: [("Cycle de vie d'une sauvegarde : export, chiffrement, rétention, copie externe et essai de restauration",
         'sauvegarde', 44)],
    8: [("Mise à jour en un clic : cinq étapes, contrôle de version et garanties de retour arrière",
         'mise_a_jour', 66)],
}

# Schéma de couverture des ouvertures de partie : (dessin, légende)
OUVERTURE_DEPLOIEMENT = {
    'I': ('conteneurs', 'Cinq conteneurs, un seul hôte, une arborescence unique'),
    'II': ('installation', 'De la distribution client au premier accès validé'),
    'III': ('sauvegarde_mini', "Une paire de fichiers, un essai de restauration par trimestre"),
    'IV': ('retour', "Restaurer, mettre à jour, revenir en arrière sans perte"),
    'V': ('reseau_mini', "Réseau local, pare-feu, HTTPS et accès à distance"),
    'VI': ('reprise', "Reprendre sur une nouvelle machine, sans jamais perdre les volumes"),
    'VII': ('memo', "Les dix règles qui protègent les données de l'école"),
}


def charger_profil(cle: str):
    """Applique le dossier documentaire d'un guide (`utilisation` ou `deploiement`)."""
    global PROFIL
    PROFIL = dict(UTILISATION_PROFIL if cle == 'utilisation' else DEPLOIEMENT_PROFIL)
    CHAPEAUX.clear()
    FIGURES.clear()
    OUVERTURE_SCHEMA.clear()
    if cle == 'deploiement':
        CHAPEAUX.update(CHAPEAUX_DEPLOIEMENT)
        FIGURES.update(FIGURES_DEPLOIEMENT)
        OUVERTURE_SCHEMA.update(OUVERTURE_DEPLOIEMENT)
    return PROFIL


# ── Polices ──────────────────────────────────────────────────────────────────
def enregistrer_polices():
    plan = [('Inter', 'Inter-Regular.ttf'), ('Inter-It', 'Inter-Italic.ttf'), ('Inter-Md', 'Inter-Medium.ttf'),
            ('Inter-Sb', 'Inter-SemiBold.ttf'), ('Inter-Bd', 'Inter-Bold.ttf'),
            ('Inter-Xb', 'Inter-ExtraBold.ttf'), ('Serif', 'SourceSerif4-Regular.ttf'),
            ('Serif-It', 'SourceSerif4-Italic.ttf'), ('Serif-Sb', 'SourceSerif4-SemiBold.ttf'),
            ('Mono', 'JetBrainsMono-Regular.ttf'), ('Mono-Sb', 'JetBrainsMono-SemiBold.ttf')]
    for nom, fichier in plan:
        if nom not in pdfmetrics.getRegisteredFontNames():
            fonte = TTFont(nom, str(POLICES / fichier))
            # ReportLab indexe les fontes TTF par nom de *face* : les cinq graisses d'Inter portent
            # toutes « Inter-Regular » et seraient fusionnées en une seule (gras silencieusement perdu).
            fonte.face.name = nom.encode('ascii', 'replace')
            pdfmetrics.registerFont(fonte)
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
_TAG = re.compile(r'(</?(?:font|b|i|br/?)(?:\s[^<>]*)?>)')
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
    # le dossier documentaire peut fournir un balisage éditorial (monospace, gras, italique) :
    # il est mis de côté, échappé avec le reste du texte, puis réintroduit intact
    balises: list[str] = []
    def _reserver(m):
        balises.append(m.group(1))
        return f'\x02{len(balises) - 1}\x02'

    txt = _TAG.sub(_reserver, txt)
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
    txt = re.sub(r'\x00(\d+)\x00', _rendre, txt)
    return re.sub(r'\x02(\d+)\x02', lambda m: balises[int(m.group(1))], txt)


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
    # allowWidows/allowOrphans à 0 : une ligne isolée (un seul mot en haut de page) ne se produit plus
    base = dict(fontName='Inter', fontSize=9.1, leading=13.6, textColor=ENCRE_DOUCE, spaceAfter=2.8 * mm,
                allowWidows=0, allowOrphans=0)
    return {
        # les chemins et noms de fichiers sont des mots insécables très longs : en justification
        # stricte, ils creusent des blancs ; on compose ces paragraphes au fer à gauche.
        'corps': ParagraphStyle('corps', alignment=TA_LEFT, **base),
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
        'encart': ParagraphStyle('encart', fontName='Serif-It', fontSize=10.4, leading=15.4, textColor=MARINE,
                                 alignment=TA_LEFT, spaceAfter=0),
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
            doc = self.canv._doctemplate
            cadre = getattr(doc, 'frame', None)
            if getattr(cadre, '_atTop', False):
                return 0, 0          # déjà en haut de page : un saut créerait une page blanche
            doc.handle_pageBreak()
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

    NIVEAUX = {1: (0, 0), 2: (1, 0), 3: (2, 0)}

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


class Destination(Flowable):
    """Destination de lien interne, posée à l'endroit exact du flux où elle est déclarée."""

    def __init__(self, nom):
        super().__init__()
        self.nom = nom

    def wrap(self, *_):
        return 0, 0

    def draw(self):
        self.canv.bookmarkHorizontal(self.nom, 0, 0)


def _ancre_chapitre(num):
    return f'chapitre-{num}' if isinstance(num, int) else f'annexe-{abs(hash(num)) % 10**8}'


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
        # une dernière ligne de texte ne doit pas dépasser sous le fond de l'encadré : les blocs
        # composés en paragraphes sont mesurés ligne à ligne, on ajoute la garde du filet
        if self._h < 8 * mm:
            self.height += 1.2 * mm
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
        _pictogramme(c, self.icone or 'note', 3.2 * mm, self.couleur)
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
    elif nom == 'cible':
        c.circle(t / 2, t / 2, t * 0.46, stroke=1, fill=0)
        c.circle(t / 2, t / 2, t * 0.24, stroke=1, fill=0)
        c.circle(t / 2, t / 2, t * 0.06, stroke=0, fill=1)
    elif nom == 'note':
        c.rect(t * 0.16, 0, t * 0.68, t * 0.9, stroke=1, fill=0)
        for k, long in enumerate((0.46, 0.46, 0.26)):
            y = t * (0.68 - k * 0.22)
            c.line(t * 0.26, y, t * (0.26 + long), y)
    elif nom == 'cube':                      # socle technique : trois arêtes d'un volume
        c.line(t * 0.5, t * 0.94, t * 0.94, t * 0.7)
        c.line(t * 0.5, t * 0.94, t * 0.06, t * 0.7)
        c.line(t * 0.06, t * 0.7, t * 0.06, t * 0.24)
        c.line(t * 0.94, t * 0.7, t * 0.94, t * 0.24)
        c.line(t * 0.06, t * 0.24, t * 0.5, t * 0.02)
        c.line(t * 0.94, t * 0.24, t * 0.5, t * 0.02)
        c.line(t * 0.5, t * 0.48, t * 0.5, t * 0.02)
        c.line(t * 0.5, t * 0.48, t * 0.06, t * 0.7)
        c.line(t * 0.5, t * 0.48, t * 0.94, t * 0.7)
    elif nom == 'disque':                    # installation : disque et son axe
        c.circle(t / 2, t * 0.66, t * 0.36, stroke=1, fill=0)
        c.circle(t / 2, t * 0.66, t * 0.1, stroke=1, fill=0)
        c.rect(t * 0.4, t * 0.06, t * 0.2, t * 0.34, stroke=1, fill=0)
    elif nom == 'reglage':                   # configuration : curseurs
        for k, (y, xg) in enumerate(((0.78, 0.5), (0.5, 0.24), (0.22, 0.62))):
            yy = t * y
            c.line(t * 0.06, yy, t * 0.94, yy)
            c.circle(t * xg, yy, t * 0.12, stroke=0, fill=1)
    elif nom == 'horloge':                   # exploitation quotidienne
        c.circle(t / 2, t / 2, t * 0.46, stroke=1, fill=0)
        c.line(t / 2, t / 2, t / 2, t * 0.78)
        c.line(t / 2, t / 2, t * 0.72, t * 0.44)
    elif nom == 'archive':                   # sauvegardes : pile de disques
        for y in (0.78, 0.46, 0.14):
            c.ellipse(t * 0.08, t * y, t * 0.92, t * (y + 0.16), stroke=1, fill=0)
    elif nom == 'engrenage':                 # automatisation : roue dentée simplifiée
        c.circle(t / 2, t / 2, t * 0.26, stroke=1, fill=0)
        for k in range(8):
            import math
            a = k * math.pi / 4
            c.line(t / 2 + t * 0.3 * math.cos(a), t / 2 + t * 0.3 * math.sin(a),
                   t / 2 + t * 0.46 * math.cos(a), t / 2 + t * 0.46 * math.sin(a))
    elif nom == 'reseau':                    # accès réseau : trois nœuds reliés
        c.circle(t * 0.5, t * 0.86, t * 0.12, stroke=0, fill=1)
        c.circle(t * 0.13, t * 0.14, t * 0.12, stroke=0, fill=1)
        c.circle(t * 0.87, t * 0.14, t * 0.12, stroke=0, fill=1)
        c.line(t * 0.5, t * 0.74, t * 0.13, t * 0.26)
        c.line(t * 0.5, t * 0.74, t * 0.87, t * 0.26)
        c.line(t * 0.25, t * 0.14, t * 0.75, t * 0.14)
    elif nom == 'outil':                     # dépannage : clé à molette
        c.circle(t * 0.28, t * 0.72, t * 0.22, stroke=1, fill=0)
        c.line(t * 0.42, t * 0.58, t * 0.9, t * 0.1)
    elif nom == 'cycle':                     # continuité : flèche circulaire
        c.circle(t / 2, t / 2, t * 0.36, stroke=1, fill=0)
        p = c.beginPath()
        p.moveTo(t * 0.5, t * 0.96)
        p.lineTo(t * 0.74, t * 0.78)
        p.lineTo(t * 0.5, t * 0.6)
        c.drawPath(p, stroke=1, fill=0)
    elif nom == 'memo':                      # mémo : feuillet corné
        p = c.beginPath()
        p.moveTo(t * 0.16, t * 0.94)
        p.lineTo(t * 0.62, t * 0.94)
        p.lineTo(t * 0.86, t * 0.7)
        p.lineTo(t * 0.86, t * 0.06)
        p.lineTo(t * 0.16, t * 0.06)
        p.close()
        c.drawPath(p, stroke=1, fill=0)
        c.line(t * 0.62, t * 0.94, t * 0.62, t * 0.7)
        c.line(t * 0.62, t * 0.7, t * 0.86, t * 0.7)
        for y in (0.52, 0.36, 0.2):
            c.line(t * 0.28, t * y, t * 0.72, t * y)
    elif nom == 'retour':                    # restauration : flèche vers l'arrière
        p = c.beginPath()
        p.moveTo(t * 0.9, t * 0.5)
        p.arcTo(t * 0.1, t * 0.1, t * 0.9, t * 0.9, startAng=0, extent=270)
        c.drawPath(p, stroke=1, fill=0)
        p2 = c.beginPath()
        p2.moveTo(t * 0.9, t * 0.94)
        p2.lineTo(t * 0.9, t * 0.5)
        p2.lineTo(t * 0.46, t * 0.5)
        c.drawPath(p2, stroke=1, fill=0)
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
            # une puce ou une étape dont la suite est repliée sur la ligne suivante (sans ligne
            # vide) appartient au même paragraphe : on la recolle, sinon la fin part en texte courant
            if tampon and tampon[-1].strip() and re.match(r'^ {0,3}([-*+]|\d+[.)])\s+\S', tampon[-1]) \
                    and re.match(r'^ {2,}\S', ligne) and not re.match(r'^\s*([-*+]|\d+[.)])\s+', ligne) \
                    and not re.match(r'^\s*(```|\|)', ligne):
                tampon[-1] = tampon[-1].rstrip() + ' ' + ligne.strip()
            else:
                tampon.append(ligne)
    if courant is not None:
        courant['md'] = '\n'.join(tampon)
        blocs.append(courant)

    chapitres = []
    for bloc in blocs:
        titre = bloc['titre']
        if titre.upper().startswith('TABLE DES MATI') or titre in IGNORER:
            continue
        if titre == PROFIL.get('preambule'):
            PREAMBULE['md'] = bloc['md']
            continue
        # « ## 3.5 Licence… » : sous-section écrite au niveau 2 dans la source ; elle rejoint le
        # chapitre 3 comme titre de niveau 3, numérotation conservée.
        m = re.match(r'^(\d+)\.(\d+)\s+(.*)$', titre)
        if m:
            parent = next((c for c in chapitres if c['num'] == int(m.group(1))), None)
            if parent is not None:
                parent['md'] += f'\n\n### {m.group(1)}.{m.group(2)} {m.group(3)}\n\n' + bloc['md']
                continue
        m = re.match(r'^(\d+)[.)]?\s+(.*)$', titre)
        if m:
            chapitres.append({'num': int(m.group(1)), 'titre': m.group(2), 'md': bloc['md']})
        elif titre.strip().lower().startswith(tuple(ANNEXES)) if ANNEXES else False:
            # section hors numérotation promue en annexe : elle apparaît dans le sommaire et les signets
            chapitres.append({'num': titre.strip(), 'titre': titre.strip(), 'md': bloc['md'], 'annexe': True})
    return chapitres


PREAMBULE = {}      # section d'ouverture rédigée (public, objectif, validation) → page d'avant-propos
IGNORER = set()     # titres de niveau 2 volontairement écartés (sommaire rédigé à la main, etc.)
ANNEXES = set()     # titres de niveau 2 non numérotés conservés comme annexes (en minuscules)


def etiq(num):
    """Étiquette de chapitre : « 04 » pour un chapitre, le titre pour une annexe."""
    return f'{num:02d}' if isinstance(num, int) else 'A'


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


def dedenter_code(src: str) -> str:
    """Blocs de code indentés dans une liste : leur retrait est ramené à la marge de la colonne.

    Dans la source, un bloc replié sous une puce ou une étape porte trois espaces de retrait ; livré
    tel quel, il réduit d'autant la largeur utile et décale les blocs monospace hors de l'axe du
    texte. Les lignes vides à l'intérieur du bloc sont conservées.
    """
    sortie, bloc = [], None
    for ligne in src.split('\n'):
        if re.match(r'^\s*```', ligne):
            if bloc is None:                       # ouverture : on relève le retrait de la clôture
                bloc = (len(ligne) - len(ligne.lstrip()), [ligne.lstrip()])
            else:
                bloc[1].append(ligne.lstrip())
                sortie.extend(bloc[1])
                bloc = None
            continue
        if bloc is not None:
            bloc[1].append(ligne[bloc[0]:] if len(ligne) >= bloc[0] else ligne.lstrip())
            continue
        sortie.append(ligne)
    if bloc is not None:
        sortie.extend(bloc[1])
    return '\n'.join(sortie)


def _tableau(lignes, st, largeur):
    lignes = [l for l in lignes if not re.match(r'^\|[\s:|-]*$', l.strip())] or lignes
    rangees = [[c.strip() for c in brute.strip().strip('|').split('|')] for brute in lignes]
    entete, corps = rangees[0], rangees[1:]
    nb = len(entete)

    def poids(txt):
        # longueur utile : on ignore le balisage et on compte les cellules vides pour ce qu'elles sont
        return max(4.0, min(26.0, len(re.sub(r'</?[a-z][^<>]*>|[*`]', '', txt)) / 2.4 + 3.6))

    def necessaire(txt, cellule=False):
        # largeur minimale pour que le mot le plus long tienne (police de cellule ou d'en-tête)
        taille = 7.7 if cellule else 6.8
        mots = re.sub(r'</?[a-z][^<>]*>|[*`]', '', txt).split()
        return max((pdfmetrics.stringWidth(m, 'Inter', taille) for m in mots), default=0) + 5.2 * mm

    parts = [poids(c) for c in entete]
    total = sum(parts) or 1
    largeurs = [largeur * p / total for p in parts]
    # aucune colonne ne descend sous son mot le plus long : les autres lui cèdent la place
    for i, colonne in enumerate(entete):
        mini = max(necessaire(colonne), max((necessaire(l[i], True) for l in corps if i < len(l)), default=0))
        if largeurs[i] < mini:
            manque = mini - largeurs[i]
            donateurs = [j for j in range(nb) if j != i and largeurs[j] - manque * 0.6 > necessaire(entete[j])]
            poids_don = sum(largeurs[j] for j in donateurs) or 1
            for j in donateurs:
                largeurs[j] -= manque * largeurs[j] / poids_don
            largeurs[i] = mini
    def cellule(txt, style, marques=False):
        # une case réduite à une coche ou à une croix reçoit sa couleur d'état : le tableau se lit d'un
        # coup d'œil, sans texte, et reste net à l'impression (le glyphe vient d'Inter, jamais du mono)
        if marques:
            nu = sans_emoji(txt).strip()
            if nu in ('✓', '**✓**'):
                txt = '<font color="#067955">✓</font>'
            elif nu in ('✗', '**✗**'):
                txt = '<font color="#B3261E">✗</font>'
        return Paragraph(inline(txt) or '&nbsp;', style)

    donnees = [[Paragraph(inline(c), st['entete']) for c in entete]]
    for ligne in corps:
        ligne = (ligne + [''] * nb)[:nb]
        donnees.append([cellule(c, st['cellule'], marques=True) for c in ligne])
    t = Table(donnees, colWidths=largeurs, repeatRows=1, hAlign='LEFT')
    commandes = [('FONTNAME', (0, 0), (-1, -1), 'Inter'),
                 ('BACKGROUND', (0, 0), (-1, 0), MARINE_TETE), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                 ('TOPPADDING', (0, 0), (-1, -1), 2.0 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.0 * mm),
                 ('LEFTPADDING', (0, 0), (-1, -1), 2.2 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 2.2 * mm),
                 ('LINEBELOW', (0, 1), (-1, -1), 0.35, FILET), ('LINEBELOW', (0, -1), (-1, -1), 0.8, FILET_FONCE)]
    for i in range(1, len(donnees)):
        if i % 2 == 0:
            commandes.append(('BACKGROUND', (0, i), (-1, i), ZEBRE))
    t.setStyle(TableStyle(commandes))
    # un tableau court ne se coupe pas : l'en-tête et les quelques lignes qui le suivent restent
    # solidaires. Les longs tableaux, eux, se poursuivent page suivante, en-tête répété.
    if len(donnees) <= 9:
        return t          # (garde mesurée par le flux, voir _besoin_sous_titre)
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
    plain = texte.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&#160;')
    # XPreformatted conserve l'indentation et les retours à la ligne ; les lignes trop larges ont
    # déjà été pliées ci-dessus, ce qui évite tout débordement hors de la colonne de texte.
    style = ParagraphStyle('code', fontName='Mono', fontSize=taille, leading=taille * 1.42,
                           textColor=HexColor('#1F2937'))
    rendu = XPreformatted(plain, style)
    t = Table([[rendu]], colWidths=[largeur], hAlign='LEFT')
    t.setStyle(TableStyle([('FONTNAME', (0, 0), (-1, -1), 'Mono'),
                           ('BACKGROUND', (0, 0), (-1, -1), HexColor('#FBF9F4')),
                           ('LINEBEFORE', (0, 0), (0, -1), 1.6, OR_CLAIR),
                           ('LEFTPADDING', (0, 0), (-1, -1), 3.2 * mm),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 2.6 * mm),
                           ('TOPPADDING', (0, 0), (-1, -1), 2.4 * mm),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 2.4 * mm), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    # une seule ligne : le tableau ne se coupe pas, mais reste un flowable simple (pas un conteneur),
    # ce qui permet de l'associer à un paragraphe sans KeepTogether imbriqué
    return [Spacer(1, 1.4 * mm), t, Spacer(1, 4.2 * mm)]


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
    md = dedenter_code(reparer_listes(md))
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
                commande = _code(bloc, largeur)
                # une phrase d'annonce (« depuis le dossier racine : ») ne reste jamais seule en bas
                # de page : elle voyage avec la commande qu'elle introduit
                if flux and isinstance(flux[-1], Paragraph) and _annonce(flux[-1]) \
                        and _mesure_hauteur(KeepTogether(commande), largeur) <= 92 * mm:
                    flux.append(KeepTogether([flux.pop()] + commande))
                else:
                    flux.extend(commande)
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
                flux.append(Signet(joli_titre(titre), 3))
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
            # un titre ne doit jamais rester seul en bas de page : on mesure le premier bloc qui
            # le suit (commande, tableau, citation, liste) et on exige la place correspondante
            besoin = _besoin_sous_titre(lignes, i, entete, st, largeur, ctx)
            if besoin:
                flux.append(Saut(besoin + _espace_avant(entete)))
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

        m = re.match(r'^(\s*)(\d+)[.)]\s+(.*)$', ligne)
        if m:
            profondeur = len(m.group(1))
            parent = st['puce2'] if profondeur >= 2 else st['puce']
            # une étape peut porter plusieurs paragraphes (suite repliée, encadré de commandes) :
            # ils forment un seul bloc solidaire, comme dans la source
            corps = [m.group(3).strip()]
            i += 1
            while i < len(lignes):
                suite = lignes[i]
                if not suite.strip():
                    j = i
                    while j < len(lignes) and not lignes[j].strip():
                        j += 1
                    if j < len(lignes) and re.match(r'^ {3,}\S', lignes[j]) \
                            and not re.match(r'^\s*([-*+]|\d+[.)])\s+', lignes[j]):
                        i = j
                        continue
                    break
                if re.match(r'^\s*([-*+]|\d+[.)])\s+', suite) or re.match(r'^ {0,2}\S', suite):
                    break
                corps.append(suite.strip())
                i += 1
            texte_etape = ' '.join(corps)
            style = ParagraphStyle(f'n{profondeur}', parent=parent, bulletFontName='Inter-Sb',
                                   bulletColor=OR, leftIndent=parent.leftIndent + 1.6 * mm,
                                   bulletIndent=parent.bulletIndent)
            flux.append(KeepTogether([Paragraph(inline(texte_etape), style, bulletText=f'{m.group(2)}.')]))
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
                         initialFontName='Inter',
                         title=PROFIL['titre_pdf'], author='YELEN SCHOOL',
                         subject=PROFIL['sujet_pdf'], creator='YELEN SCHOOL',
                         keywords=f"YELEN SCHOOL, guide, {PROFIL['cle']}, gestion scolaire, Burkina Faso")
        self.version_ouvrage, self.date_ouvrage = version, date_txt
        self.nb_chapitres = len(chapitres)
        self.livre = PROFIL['livre']
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
        c.drawString(x, HAUTEUR - 34 * mm, f'ÉDITION {self.version_ouvrage}   ·   {PROFIL["surtitre"]}')
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
        taille_titre = 30 if len(PROFIL['couverture_titre']) <= 2 else 26
        c.setFont('Serif-Sb', taille_titre)
        for k, ligne in enumerate(PROFIL['couverture_titre']):
            c.drawString(x, HAUTEUR - 150 * mm - k * (taille_titre * 0.38) * mm, ligne)

        c.setFillColor(HexColor('#C6D0DB'))
        c.setFont('Serif-It', 11.2)
        for k, ligne in enumerate(PROFIL['couverture_sous_titre']):
            c.drawString(x, HAUTEUR - (175 + 6 * k) * mm, ligne)

        y = 34 * mm
        c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.4))
        c.setLineWidth(0.5)
        c.line(x, y + 12 * mm, LARGEUR - 24 * mm, y + 12 * mm)
        pas = (LARGEUR - 48 * mm) / 4
        meta = [(lib, val.format(version=self.version_ouvrage, date=self.date_ouvrage,
                                 chapitres=f'{self.nb_chapitres:02d}'))
                for lib, val in PROFIL['couverture_meta']]
        for i, (libelle, valeur) in enumerate(meta):
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
        y = HAUTEUR - 74 * mm
        c.setFillColor(OR_CLAIR)
        c.setFont('Serif', 54)
        c.drawString(x, y, num)
        c.setFillColor(HexColor('#7E8B9A'))
        c.setFont('Inter-Bd', 7.1)
        c.drawString(x + 1.2 * mm, y - 7.6 * mm, 'PARTIE')
        c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.45))
        c.setLineWidth(0.6)
        c.line(x, y - 12.4 * mm, x + 26 * mm, y - 12.4 * mm)

        lignes_titre = _couper(titre, 'Serif-Sb', 23, 152 * mm)
        c.setFillColor(BLANC)
        c.setFont('Serif-Sb', 23)
        y -= 27 * mm
        for k, ligne in enumerate(lignes_titre):
            c.drawString(x, y - k * 10.4 * mm, ligne)
        y -= (len(lignes_titre) - 1) * 10.4 * mm + 7.6 * mm

        c.setFillColor(HexColor('#B9C4D0'))
        c.setFont('Inter', 9.0)
        lignes_resume = _couper(_sans_balise(resume), 'Inter', 9.0, 128 * mm)
        for k, ligne in enumerate(lignes_resume):
            c.drawString(x, y - k * 5.1 * mm, ligne)
        y -= (len(lignes_resume) - 1) * 5.1 * mm + 9.0 * mm

        c.setFillColor(OR)
        c.rect(x, y, 24 * mm, 1.2, stroke=0, fill=1)
        y -= 9.4 * mm
        # les chapitres de la partie occupent le bas de la page, au-dessus du schéma
        schema = OUVERTURE_SCHEMA.get(num)
        plancher = (52 * mm + len(chapitres) * 6.4 * mm) if schema else 30 * mm
        place = y - plancher
        pas = 6.4 * mm if len(chapitres) * 6.4 * mm <= place else max(4.9 * mm, place / len(chapitres))
        for k, (n, titre_chap) in enumerate(chapitres):
            yy = y - k * pas
            c.setFillColor(OR_CLAIR)
            c.setFont('Inter-Sb', 8.6)
            c.drawString(x, yy, etiq(n))
            c.setFillColor(HexColor('#D7DEE6'))
            c.setFont('Inter', 8.6)
            c.drawString(x + 9 * mm, yy, _tronquer(joli_titre(titre_chap), 'Inter', 8.6, 126 * mm))
            c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.17))
            c.setLineWidth(0.4)
            c.line(x, yy - 2.3 * mm, x + 142 * mm, yy - 2.3 * mm)
        if schema:
            self._schema_ouverture(c, x, schema)

    @staticmethod
    def _schema_ouverture(c, x, schema):
        """Bandeau de schéma qui ferme l'ouverture de partie, posé sur le fond bleu nuit."""
        nomin, legende = schema
        largeur = LARGEUR - 2 * x
        hauteur = 36 * mm
        base = 26 * mm
        c.setFillColor(Color(1, 1, 1, alpha=0.055))
        c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.22))
        c.setLineWidth(0.5)
        c.roundRect(x, base, largeur, hauteur, 1.6 * mm, stroke=1, fill=1)
        c.saveState()
        c.translate(x + 3.6 * mm, base + 6.0 * mm)
        c.setFillColor(HexColor('#FBF9F4'))
        c.rect(0, 0, largeur - 7.2 * mm, hauteur - 9.6 * mm, stroke=0, fill=1)
        _figures.dessiner(nomin, c, largeur - 7.2 * mm, hauteur - 9.6 * mm)
        c.restoreState()
        c.setFillColor(HexColor('#8D99A8'))
        c.setFont('Inter', 6.6)
        c.drawString(x, base - 4.6 * mm, legende.upper())

    @staticmethod
    def _liste_partie(c, x, y, chapitres, schema=None):
        """Sommaire de la partie : numéro d'or, titre, filet ; quitte à deux colonnes s'il le faut."""
        deux = len(chapitres) > 8
        colonne = 0
        haut = y
        for k, (n, titre_chap) in enumerate(chapitres):
            if deux and k == (len(chapitres) + 1) // 2:
                colonne, y = 1, haut
            yy = y
            if deux:
                x_col = x + colonne * 74 * mm
                largeur_txt = 62 * mm
                largeur_filet = 68 * mm
            else:
                x_col = x
                largeur_txt = 128 * mm
                largeur_filet = 142 * mm
            c.setFillColor(OR_CLAIR)
            c.setFont('Inter-Sb', 8.7)
            c.drawString(x_col, yy, f'{n:02d}' if isinstance(n, int) else '§')
            c.setFillColor(HexColor('#D7DEE6'))
            c.setFont('Inter', 8.7)
            c.drawString(x_col + 9 * mm, yy, _tronquer(joli_titre(titre_chap), 'Inter', 8.7, largeur_txt))
            c.setStrokeColor(Color(0.85, 0.71, 0.46, alpha=0.17))
            c.setLineWidth(0.4)
            c.line(x_col, yy - 2.4 * mm, x_col + largeur_filet, yy - 2.4 * mm)
            y -= 6.4 * mm
        return y - 3.0 * mm

    def _colophon(self, c, doc):
        c.setFillColor(HexColor('#0F2438'))
        c.circle(LARGEUR * 0.92, HAUTEUR * 0.95, 92 * mm, stroke=0, fill=1)
        x = 26 * mm
        c.setFillColor(OR)
        c.setFont('Inter-Bd', 7.1)
        c.drawString(x, HAUTEUR - 118 * mm, PROFIL['colophon_kicker'])
        c.setFillColor(BLANC)
        c.setFont('Serif-Sb', 20)
        c.drawString(x, HAUTEUR - 130 * mm, PROFIL['colophon_titre'])
        c.setFillColor(HexColor('#B9C4D0'))
        c.setFont('Serif-It', 12.5)
        c.drawString(x, HAUTEUR - 138 * mm, PROFIL['colophon_sous'])
        c.setStrokeColor(OR)
        c.setLineWidth(1.1)
        c.line(x, HAUTEUR - 145 * mm, x + 28 * mm, HAUTEUR - 145 * mm)
        c.setFillColor(HexColor('#8C97A5'))
        c.setFont('Inter', 8.4)
        champs = {'version': self.version_ouvrage, 'date': self.date_ouvrage, 'chapitres': self.nb_chapitres,
                  'pages': self.nb_pages}
        for k, ligne in enumerate([f'Édition {self.version_ouvrage} — {self.date_ouvrage}',
                                   _format(PROFIL['colophon_meta'][0], champs)]):
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


def _champs(version, date_txt, chapitres):
    """Valeurs de substitution disponibles dans les textes du dossier documentaire."""
    return {'version': version, 'date': date_txt, 'chapitres': len(chapitres), 'portee': PROFIL['portee']}


def _sans_balise(texte: str) -> str:
    """Version texte d'un paragraphe balisé : pour les tracés qui n'interprètent pas le HTML."""
    return re.sub(r'<[^>]+>', '', texte)


def _format(texte, champs):
    try:
        return texte.format(**champs)
    except (KeyError, IndexError):
        return texte


def fiche_document(version, date_txt, chapitres, st):
    flux = _en_tete_section(PROFIL['fiche_kicker'], PROFIL['fiche_titre'])
    champs = _champs(version, date_txt, chapitres)
    lignes = [(lib, _format(val, champs)) for lib, val in PROFIL['fiche']]
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
    for para in PROFIL['fiche_intro']:
        flux.append(Paragraph(inline(para), ParagraphStyle('fi', fontName='Inter', fontSize=8.9, leading=13.2,
                                                           textColor=ENCRE_DOUCE, alignment=TA_JUSTIFY,
                                                           spaceAfter=2.6 * mm)))
    flux.append(PageBreak())
    return flux


def mode_emploi(st):
    flux = _en_tete_section(PROFIL['mode_emploi_kicker'], PROFIL['mode_emploi_titre'])
    flux.append(Paragraph(inline(PROFIL['mode_emploi_intro']),
                          ParagraphStyle('p', fontName='Inter', fontSize=9, leading=13.4, textColor=ENCRE_DOUCE,
                                         alignment=TA_JUSTIFY, spaceAfter=4 * mm)))
    for zone, explication in PROFIL['mode_emploi_zones']:
        flux.append(Encadre(CORPS_L, [Paragraph(inline(explication), st['zone_fin'])], zone))
        flux.append(Spacer(1, 2.6 * mm))
    flux += [Spacer(1, 8 * mm),
             Paragraph(PROFIL['reperes_titre'], ParagraphStyle('h2b', fontName='Serif-Sb', fontSize=14,
                                                               leading=18, textColor=MARINE, spaceAfter=3 * mm))]
    reperes = PROFIL['reperes']
    donnees = [[Paragraph(lib.upper(), ParagraphStyle('rl', fontName='Inter-Bd', fontSize=6.7,
                                                      textColor=HexColor('#8A6A32'), leading=9)),
                Paragraph(inline(txt), st['cellule'])] for lib, txt in reperes]
    t = Table(donnees, colWidths=[36 * mm, CORPS_L - 36 * mm], hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0.4, FILET),
                           ('TOPPADDING', (0, 0), (-1, -1), 2.2 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2 * mm),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 1), (-1, -1), 2 * mm)]))
    flux.append(t)
    return flux


def _chapeau_md(md):
    """Analyse le chapeau en citations : renvoie [(libellé, texte)] et les paragraphes sans libellé."""
    faits, libres, courant = [], [], None
    for brute in md.split('\n'):
        ligne = re.sub(r'^>\s?', '', brute).strip()
        if not ligne or re.match(r'^-{3,}$|^\*\*?$', ligne):
            courant = None
            continue
        m = re.match(r'^\*\*(.+?)\*\*\s*:?\s*(.*)$', ligne)
        if m:
            gras = m.group(1).strip()
            if ':' in gras:                      # « **Version couverte : 5.53.1 (…).** »
                libelle, valeur = gras.split(':', 1)
                courant = [libelle.strip(), (valeur.strip() + ' ' + m.group(2).strip()).strip()]
            else:
                courant = [gras.rstrip(':'), m.group(2).strip()]
            faits.append(courant)
        elif courant is not None:
            courant[1] = (courant[1] + ' ' + ligne).strip()
        else:
            libres.append(ligne)
    return [(lib, re.sub(r'\s+', ' ', txt).strip()) for lib, txt in faits], libres


def avant_propos(st):
    """Page d'avant-propos : le chapeau du document, mis en page comme une note de service."""
    flux = [PageBreak()]
    flux += _en_tete_section(PROFIL.get('avant_propos_kicker', 'AVANT-PROPOS'),
                            PROFIL.get('avant_propos_titre', 'Avant-propos'))
    champs = PROFIL.get('_champs', {})
    for para in PROFIL.get('avant_propos_texte', []):
        flux.append(Paragraph(inline(_format(para, champs)),
                              ParagraphStyle('av', fontName='Inter', fontSize=9.1, leading=14.2,
                                             textColor=ENCRE_DOUCE, alignment=TA_LEFT, spaceAfter=3.2 * mm)))

    faits, libres = _chapeau_md(PREAMBULE.get('md', ''))
    # la version du chapeau d'origine est celle de l'édition précédente du document : elle est
    # réalignée sur la version du logiciel compilé, comme la couverture et la fiche
    version, edition = champs.get('version', ''), champs.get('date', '')

    def remplacement(m):
        return f'{version} ({edition}).' if m.group(1) else f'{version}.'

    faits = [
        (lib, re.sub(r'^\d+(?:\.\d+)*\s*(\([^)]*\))?\.?', remplacement, txt, count=1))
        if version and lib.lower().startswith('version') else (lib, txt)
        for lib, txt in faits]
    faits = [(lib, txt[:1].upper() + txt[1:] if txt else txt) for lib, txt in faits]
    if faits:
        flux.append(Spacer(1, 2.6 * mm))
        donnees = [[Paragraph(lib.upper(), ParagraphStyle('pl', fontName='Inter-Bd', fontSize=6.8,
                                                          textColor=SOURDINE, leading=9.2)),
                    Paragraph(inline(txt), ParagraphStyle('pv', fontName='Inter', fontSize=8.7, leading=12.4,
                                                          textColor=ENCRE_DOUCE))]
                   for lib, txt in faits]
        t = Table(donnees, colWidths=[34 * mm, CORPS_L - 34 * mm], hAlign='LEFT')
        t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0.4, FILET),
                               ('TOPPADDING', (0, 0), (-1, -1), 2.4 * mm),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 2.4 * mm),
                               ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 1), (-1, -1), 2 * mm)]))
        flux.append(t)
    for para in libres:
        flux.append(Paragraph(inline(para), ParagraphStyle('av2', fontName='Inter', fontSize=9.0, leading=13.8,
                                                           textColor=ENCRE_DOUCE, spaceAfter=3 * mm)))
    return flux


def fin_ouvrage(st):
    """Page de clôture : ce que le lecteur doit retenir et où aller ensuite."""
    flux = _en_tete_section(PROFIL.get('fin_kicker', 'POUR ALLER PLUS LOIN'),
                            PROFIL.get('fin_titre', 'Après ce guide'))
    for para in PROFIL.get('fin', []):
        flux.append(Paragraph(inline(_format(para, PROFIL.get('_champs', {}))),
                              ParagraphStyle('fi', fontName='Inter', fontSize=9.1, leading=14.2,
                                             textColor=ENCRE_DOUCE, alignment=TA_LEFT, spaceAfter=3.2 * mm)))
    flux.append(Spacer(1, 10 * mm))
    flux.append(Paragraph('<a href="#SOMMAIRE" color="#0A1628">Revenir au sommaire</a>',
                          ParagraphStyle('retour', fontName='Inter-Sb', fontSize=8.2, leading=11,
                                         textColor=MARINE, spaceAfter=0)))
    flux.append(Spacer(1, 6 * mm))
    flux.append(Filet(CORPS_L, 0.8, OR_CLAIR))
    flux.append(Spacer(1, 3.4 * mm))
    champs = PROFIL.get('_champs', {})
    flux.append(Paragraph(f'Édition {champs.get("version", "")} — {champs.get("date", "")} · '
                          f'YELEN SCHOOL · {champs.get("chapitres", "")} chapitres',
                          ParagraphStyle('acheve', fontName='Inter', fontSize=7.4, leading=10.4,
                                         textColor=SOURDINE)))
    return flux


def sommaire(chapitres, pages, st, premier=None):
    """Sommaire paginé : parties en capitales d'or, chapitres et folio en serif.

    Les renvois portent le folio imprimé (première page de chapitre = 1), pas la page du fichier.
    """
    def folio_de(n):
        page = pages.get(n)
        if page is None or premier is None:
            return str(page or '')
        return str(page - premier + 1)

    flux = [PageBreak(), Destination('SOMMAIRE'),
            Paragraph('Sommaire', ParagraphStyle('st', fontName='Serif-Sb', fontSize=24, leading=28,
                                                 textColor=MARINE, spaceAfter=1.5 * mm)),
            Paragraph(PROFIL['sommaire_sous'], ParagraphStyle('si', fontName='Inter-It',
                                                                              fontSize=8.6, textColor=SOURDINE,
                                                                              spaceAfter=7 * mm))]
    par_num = {c['num']: c['titre'] for c in chapitres}
    vus = set()
    for lettre, titre, _resume, nums in parties():
        presents = [n for n in nums if n in par_num and n not in vus]
        vus.update(presents)
        if not presents:
            continue
        flux.append(Spacer(1, 4.4 * mm))
        flux.append(Paragraph(f'PARTIE {lettre} &nbsp;·&nbsp; {titre.upper()}',
                              ParagraphStyle('sp', fontName='Inter-Bd', fontSize=7.4, textColor=OR,
                                             spaceAfter=1.6 * mm)))
        flux.append(Filet(CORPS_L, 0.6, OR_CLAIR, apres=2 * mm))
        for n in presents:
            titre_chap = joli_titre(par_num[n])
            num = Paragraph(etiq(n), ParagraphStyle('cn', fontName='Serif-Sb', fontSize=9.6, textColor=OR))
            txt = Paragraph(f'<a href="#{_ancre_chapitre(n)}" color="#0A1628">{inline(titre_chap)}</a>',
                            ParagraphStyle('ct', fontName='Inter-Sb', fontSize=9.3,
                                           leading=12, textColor=MARINE))
            folio = Paragraph(folio_de(n), ParagraphStyle('cp', fontName='Serif-Sb', fontSize=9.6,
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
def _sections(md):
    """Titres de niveau 3 du chapitre, dans l'ordre : sert à placer les schémas d'ouverture."""
    return [m.group(2).strip() for m in (re.match(r'^###\s+(.*)$', ligne) for ligne in md.split('\n'))
            if m and not m.group(1).strip().startswith('###')]


def _inserer_schema(md, avant_titre, bloc):
    """Insère un bloc Markdown juste avant le sous-titre `avant_titre` (ou en fin de chapitre)."""
    if not avant_titre:
        return md + '\n' + bloc
    lignes = md.split('\n')
    for i, ligne in enumerate(lignes):
        if re.match(r'^###\s+', ligne) and avant_titre in ligne:
            return '\n'.join(lignes[:i] + [bloc, ''] + lignes[i:])
    return md + '\n' + bloc


def _corps_du_guide(doc, chapitres, st, registre):
    """Flux du corps : pages d'ouverture, chapitres, repères de pagination.

    Les sauts sont posés **en tête** de chaque page (jamais en fin de contenu et jamais deux
    fois de suite) : aucune page blanche ne peut apparaître à une frontière de chapitre ou de partie.
    """
    flux, ctx = [], {'ancres': {}, 'figures': 0, 'schemas': 0, 'sections': []}
    par_num = {c['num']: c for c in chapitres}
    registre = registre if registre is not None else {}
    deja = set()

    def chapitre(num, titre, md):
        flux.append(NextPageTemplate('corps'))
        flux.append(PageBreak())
        flux.append(Signet(f'{etiq(num)} · {joli_titre(titre)}' if isinstance(num, int)
                            else joli_titre(titre), 2))
        flux.append(Destination(_ancre_chapitre(num)))
        flux.append(Repere(num, registre))
        schema = next(iter(FIGURES.get(num, [])), None)
        if schema:                              # (légende, dessin, hauteur) → (dessin, légende, hauteur)
            ctx['figures'] += 1
            ctx['schemas'] += 1
            schema = (schema[1], schema[0], schema[2])
        flux.append(_Chapeau(num, titre, st, schema))
        flux.extend(composer(md, st, CORPS_L, ctx))

    vus = set()
    for lettre, titre, resume, nums in parties():
        presents = [(n, par_num[n]['titre']) for n in nums if n in par_num and n not in vus]
        vus.update(n for n, _ in presents)
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
    if PROFIL.get('fin'):
        flux.append(NextPageTemplate('corps'))
        flux.append(PageBreak())
        flux.append(Repere('fin', registre))
        flux.append(Destination('fin-ouvrage'))
        flux.extend(fin_ouvrage(st))
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


class Schema(Flowable):
    """Schéma vectoriel légendé : cadre, dessin, légende numérotée et filet de pied."""

    PAD = 3.4 * mm

    def __init__(self, nom, hauteur_mm, legende, numero=None, largeur=CORPS_L):
        super().__init__()
        self.nom, self.legende, self.numero, self.largeur = nom, legende, numero, largeur
        self.h_dessin = hauteur_mm * mm
        self._legende = Paragraph(
            f'<font name="Inter-Bd" color="#B0803A">FIGURE\u00a0{numero or ""}</font>'
            f'&nbsp;&nbsp;{inline(legende)}', STYLE_LEGENDE)

    def wrap(self, aw, ah):
        _, h_leg = self._legende.wrap(self.largeur - 2 * self.PAD, ah)
        self.height = self.h_dessin + h_leg + 2 * self.PAD + 1.4 * mm
        return self.largeur, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(HexColor('#FCFBF7'))
        c.setStrokeColor(FILET)
        c.setLineWidth(0.5)
        c.rect(0, 0, self.largeur, self.height, stroke=1, fill=1)
        c.saveState()
        c.translate(self.PAD, self.height - self.PAD - self.h_dessin)
        _figures.dessiner(self.nom, c, self.largeur - 2 * self.PAD, self.h_dessin)
        c.restoreState()
        c.setStrokeColor(OR_CLAIR)
        c.setLineWidth(0.7)
        c.line(self.PAD, self.height - self.PAD - self.h_dessin - 0.7 * mm,
               self.PAD + 12 * mm, self.height - self.PAD - self.h_dessin - 0.7 * mm)
        self._legende.drawOn(c, self.PAD, self.PAD - 0.6 * mm)


STYLE_LEGENDE = ParagraphStyle('legende_schema', fontName='Inter', fontSize=7.3, leading=9.8,
                               textColor=SOURDINE)


def _mesure_hauteur(flowable, largeur):
    """Hauteur d'un bloc, mesurée sans dessin (un KeepTogether n'a pas de canevas)."""
    if isinstance(flowable, KeepTogether):
        return sum(_mesure_hauteur(f, largeur) for f in flowable._content)
    return flowable.wrap(largeur, 300 * mm)[1]


def _annonce(paragraphe):
    """Vrai si le paragraphe introduit le bloc qui le suit (il finit par deux-points)."""
    try:
        texte = paragraphe.getPlainText().strip()
    except Exception:
        return False
    return texte.endswith(':') and not texte.startswith(('>', '|'))


def _espace_avant(paragraphe):
    """Espace vertical déjà consommé avant un titre (le style le pose hors de sa hauteur mesurée)."""
    return getattr(getattr(paragraphe, 'style', None), 'spaceBefore', 0) or 0


def _besoin_sous_titre(lignes, i, entete, st, largeur, ctx):
    """Place à réserver avant un sous-titre : sa hauteur plus celle du bloc insécable qui le suit.

    Sans cette garde, un sous-titre suivi d'une commande ou d'un tableau reste seul en bas de page,
    la commande partant à la page suivante. On ne réserve jamais plus d'une demi-page.
    """
    while i < len(lignes) and not lignes[i].strip():
        i += 1
    if i >= len(lignes):
        return 0
    ligne = lignes[i]
    if not (ligne.startswith('```') or ligne.startswith('|')):
        return 0                      # paragraphes et listes se coupent proprement : rien à réserver
    j = i + 1
    if ligne.startswith('```'):
        while j < len(lignes) and not lignes[j].startswith('```'):
            j += 1
        j += 1
    else:
        while j < len(lignes) and lignes[j].startswith('|'):
            j += 1
    flux = composer('\n'.join(lignes[i:j]), st, largeur, ctx)
    if not flux:
        return 0
    hauteur = entete.wrap(largeur, 300 * mm)[1]

    def mesurer(f, dispo):
        if isinstance(f, KeepTogether):
            return sum(mesurer(x, dispo) for x in f._content)
        return f.wrap(dispo, 300 * mm)[1]

    for f in flux:
        hauteur += mesurer(f, largeur)
    return min(hauteur, 130 * mm)


def _schema_pleine_largeur(nom, hauteur, legende, numero):
    """Schéma inséré entre deux paragraphes, précédé de son espace de respiration."""
    return KeepTogether([Spacer(1, 2.4 * mm), Schema(nom, hauteur, legende, numero), Spacer(1, 4.6 * mm)])


class _Chapeau(Flowable):
    """Chapeau de chapitre : numéro d'or, titre serif, pastille de rôle et filet."""

    MARGE_HAUT = 5 * mm

    def __init__(self, num, titre, st, schema=None):
        super().__init__()
        self.num, self.titre, self.st = num, titre, st
        self.schema = schema                  # (nom du dessin, légende, hauteur en mm)
        mineur = not isinstance(num, int)
        self.etiquette, self.icone = CHAPEAUX.get(num, ('Mémo', 'memo') if mineur else (None, None))
        self._h = 0

    def wrap(self, aw, ah):
        titre_propre = joli_titre(self.titre)
        self._titre = Paragraph(inline(titre_propre),
                                ParagraphStyle('ct', fontName='Serif-Sb', fontSize=21.5, leading=25.5,
                                               textColor=MARINE, spaceAfter=0))
        marque = f'{self.num:02d}' if isinstance(self.num, int) else 'A'
        self._num = Paragraph(f'<font name="Serif" color="#B0803A" size="31">{marque}</font>',
                              ParagraphStyle('cn', fontName='Serif', fontSize=31, leading=30,
                                             textColor=OR, spaceAfter=0))
        self._num.wrap(20 * mm, ah)
        self._titre.wrap(aw - 20 * mm, ah)
        self._h = max(self._num.height, self._titre.height) + self.MARGE_HAUT + 5.4 * mm
        if self.schema:
            # bandeau d'ouverture : cadre à filets d'or, dessin vectoriel et légende sous le chapeau
            self._legende = Paragraph(inline(self.schema[1]), STYLE_LEGENDE)
            self._legende.wrap(aw - 2 * 4.2 * mm, ah)
            self._h_bandeau = self.schema[2] * mm + self._legende.height + 7.6 * mm
            self._h += self._h_bandeau + 4.2 * mm
        return aw, self._h

    def draw(self):
        c = self.canv
        haute = self._h - self.MARGE_HAUT
        if self.etiquette:
            surtitre = f'CHAPITRE {self.num:02d}' if isinstance(self.num, int) else 'ANNEXE'
            _pastille(c, 0, haute + 0.6 * mm, surtitre, self.etiquette, self.icone)
        self._num.drawOn(c, 0, haute - self._num.height + 1.4 * mm)
        self._titre.drawOn(c, 19.6 * mm, haute - self._num.height + 1.4 * mm)
        largeur = c._doctemplate.width          # largeur du cadre de texte (marges déjà déduites)
        if self.schema:
            h_dessin = self.schema[2] * mm
            base = self._h - h_dessin - self._legende.height - 5.8 * mm - (self._h_bandeau - h_dessin
                                                                          - self._legende.height - 7.6 * mm)
            c.setFillColor(HexColor('#FCFBF7'))
            c.setStrokeColor(OR_CLAIR)
            c.setLineWidth(0.6)
            c.rect(0, 0.2 * mm, largeur, self._h_bandeau, stroke=1, fill=1)
            c.saveState()
            c.translate(4.6 * mm, self._legende.height + 5.4 * mm)
            _figures.dessiner(self.schema[0], c, largeur - 2 * 4.6 * mm, h_dessin)
            c.restoreState()
            self._legende.drawOn(c, 4.6 * mm, 3.6 * mm)
            c.setStrokeColor(FILET)
            c.setLineWidth(0.5)
            c.line(0, self._h_bandeau + 1.6 * mm, largeur, self._h_bandeau + 1.6 * mm)
            _ = base
        else:
            c.setStrokeColor(FILET)
            c.setLineWidth(0.5)
            c.line(0, 0.9 * mm, largeur, 0.9 * mm)


def _pastille(c, x, y, surtitre, etiquette, icone=None, extra=''):
    """Petite étiquette éditoriale : surtitre or, libellé capitales, filet de rappel."""
    c.saveState()
    c.setFillColor(OR)
    c.setFont('Inter-Bd', 6.3)
    c.drawString(x, y + 3.1 * mm, surtitre)
    largeur = c.stringWidth(surtitre, 'Inter-Bd', 6.3) + 2.6 * mm
    c.setFillColor(MARINE)
    c.setFont('Inter-Bd', 6.3)
    c.drawString(x + largeur, y + 3.1 * mm, etiquette.upper())
    largeur += c.stringWidth(etiquette.upper(), 'Inter-Bd', 6.3)
    if icone:
        c.saveState()
        c.translate(x + largeur + 1.8 * mm, y + 3.0 * mm)
        _pictogramme(c, icone, 2.7 * mm, OR)
        c.restoreState()
        largeur += 5.4 * mm
    if extra:
        c.setFillColor(SOURDINE)
        c.setFont('Inter', 6.3)
        c.drawString(x + largeur + 2 * mm, y + 3.1 * mm, extra)
    c.setStrokeColor(OR_CLAIR)
    c.setLineWidth(0.7)
    c.line(x, y + 1.2 * mm, x + 9 * mm, y + 1.2 * mm)
    c.restoreState()


def assembler(source: Path, sortie: Path, cle: str = 'utilisation'):
    """Compose le PDF en deux passes : pagination mesurée, puis sommaire et en-têtes définitifs."""
    charger_profil(cle)
    enregistrer_polices()          # avant le gabarit : le préambule de page y réfère Inter
    st = styles()
    _, corps_txt = lire_entete(source.read_text(encoding='utf-8'))
    version = (RACINE / 'VERSION').read_text(encoding='utf-8').strip()
    # la date d'édition peut être figée dans le dossier documentaire : elle ne doit pas dépendre
    # de l'horloge de la machine qui compose l'ouvrage
    date_txt = PROFIL.get('edition') or date.today().strftime('%d/%m/%Y')
    PREAMBULE.clear()
    IGNORER.clear()
    IGNORER.update(PROFIL.get('ignorer', ()))
    ANNEXES.clear()
    ANNEXES.update(t.strip().lower() for t in PROFIL.get('annexes', ()))
    chapitres = decouper(corps_txt)
    chapitres_map = {c['num']: c for c in chapitres}
    PROFIL['_champs'] = _champs(version, date_txt, chapitres)

    def flux_liminaires(pages):
        flux = [NextPageTemplate('liminaire'), PageBreak()]
        flux += fiche_document(version, date_txt, chapitres, st)
        flux += mode_emploi(st)
        if PROFIL.get('avant_propos_texte'):
            flux += avant_propos(st)
        flux += sommaire(chapitres, pages, st, min(pages.values()) if pages else None)
        return flux

    # — passe 1 : composition réelle, sommaire aux folios provisoires ; on relève la pagination
    doc = Guide(sortie, version, date_txt, chapitres)
    doc.build(flux_liminaires({}) + _corps_du_guide(doc, chapitres, st, doc.registre))
    pages = dict(doc.registre)
    debut = min(pages.values()) if pages else 0        # folio 1 = première page de chapitre
    total = doc.page
    libelles_fixes = {'fin': PROFIL.get('fin_kicker', 'POUR ALLER PLUS LOIN')}
    entetes = sorted([(page, f'{etiq(num)} · {joli_titre(chapitres_map[num]["titre"])}'
                       if isinstance(num, int) else joli_titre(chapitres_map[num]['titre']))
                      for num, page in pages.items() if num in chapitres_map]
                     + [(page, libelles_fixes[cle]) for cle, page in pages.items() if cle in libelles_fixes])

    # — passe 2 : mêmes pages, sommaire réel et en-têtes courants
    doc2 = Guide(sortie, version, date_txt, chapitres)
    doc2.pleines, doc2.chapitres_pages = doc.pages_pleines, entetes
    doc2.debut_corps, doc2.nb_pages = debut, total
    doc2.build(flux_liminaires(pages) + _corps_du_guide(doc2, chapitres, st, {}))
    print(f'  {len(chapitres)} chapitres · {doc2.page} pages · folio 1 = p. {debut}')
    _purger_polices(sortie)
    return doc2


def _purger_polices(chemin):
    """Retire la police standard Helvetica que ReportLab réserve dans le préambule de chaque page.

    ReportLab inscrit « BT /F1 12 Tf 14.4 TL ET » (Helvetica, police standard non embarquée) en tête
    du flux de chaque page, sans jamais s'en servir. Un imprimeur y verrait une police manquante : le
    flux est réécrit sans cet appel et la ressource correspondante est retirée. Le document est cloné
    pour conserver signets, liens et métadonnées.
    """
    import re

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject

    ecrivain = PdfWriter(clone_from=str(chemin))
    for page in ecrivain.pages:
        ressources = page.get('/Resources')
        polices = ressources['/Font'].get_object() if ressources and '/Font' in ressources else {}
        standard = [nom for nom, ref in polices.items()
                    if 'Helvetica' in str(ref.get_object().get('/BaseFont', ''))]
        if not standard:
            continue
        flux = page.get_contents().get_data().decode('latin-1')
        for nom in standard:
            flux = re.sub(r'BT\s+/' + re.escape(nom.lstrip('/')) + r'\s+[\d.]+\s+Tf\s+[\d.]+\s+TL\s+ET\s*',
                          '', flux)
        nouveau = DecodedStreamObject()
        nouveau.set_data(flux.encode('latin-1'))
        page[NameObject('/Contents')] = ecrivain._add_object(nouveau)
        for nom in standard:
            del polices[NameObject(nom)]
    with open(chemin, 'wb') as sortie:
        ecrivain.write(sortie)


if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser(description='Compose un guide YELEN SCHOOL en PDF éditorial.')
    ap.add_argument('source', nargs='?', type=Path)
    ap.add_argument('sortie', nargs='?', type=Path)
    ap.add_argument('--document', default='utilisation', choices=('utilisation', 'deploiement'),
                    help='dossier documentaire appliqué (identité, parties, textes)')
    args = ap.parse_args()
    profil = charger_profil(args.document)
    src = args.source or DOCS / profil.get('fichier', 'GUIDE_UTILISATION_YELEN_SCHOOL.md')
    out = args.sortie or DOCS / profil.get('sortie', 'GUIDE_UTILISATION_YELEN_SCHOOL.pdf')
    assembler(src, out, args.document)
    print(f'PDF composé : {out}')
