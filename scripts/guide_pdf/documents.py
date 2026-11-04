"""Dossiers documentaires des guides YELEN SCHOOL composés en PDF éditorial.

Un dossier décrit, pour un guide Markdown donné : son identité de couverture, sa fiche
documentaire, ses parties, sa page de clôture et, le cas échéant, ses schémas.
`scripts/md_vers_pdf.py` s'en sert pour composer le PDF ; les contenus de fond restent
dans `docs/*.md`, source unique de vérité.
"""

# ── Schéma d'architecture (dessiné pour le guide de déploiement) ──────────────
ARCHITECTURE = """
<svg class="schema" viewBox="0 0 700 372" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Architecture du serveur d'école : accès, cinq conteneurs Docker, hôte Windows">
  <defs>
    <marker id="fleche" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6"
            orient="auto-start-reverse">
      <path d="M0 1.4L8.5 5L0 8.6z" fill="#B0803A"/>
    </marker>
    <style>
      .titre { font-family: Inter, sans-serif; font-size: 11.5px; font-weight: 600; fill: #0A1628; }
      .ligne { font-family: Inter, sans-serif; font-size: 9px; fill: #3B4655; }
      .etape { font-family: Inter, sans-serif; font-size: 9px; font-weight: 700; fill: #B0803A;
               letter-spacing: 1.6px; }
      .note  { font-family: Inter, sans-serif; font-size: 8.5px; fill: #6C7787; }
      .lien  { stroke: #8C97A5; stroke-width: 1.3; fill: none; }
      .accent{ stroke: #B0803A; stroke-width: 1.4; fill: none; }
      .blanc { font-family: Inter, sans-serif; font-size: 10.5px; font-weight: 600; fill: #FFFFFF; }
      .gris  { font-family: Inter, sans-serif; font-size: 8.5px; fill: #AEB9C6; }
    </style>
  </defs>

  <!-- Accès -->
  <text class="etape" x="20" y="22">ACCÈS</text>
  <rect x="20" y="34" width="200" height="54" rx="4" fill="#F1F5FA" stroke="#34506F"/>
  <text class="titre" x="34" y="58">Poste du réseau local</text>
  <text class="ligne" x="34" y="74">http://NOM-PC:8001</text>
  <rect x="240" y="34" width="200" height="54" rx="4" fill="#EAF6F0" stroke="#00A86B"/>
  <text class="titre" x="254" y="58">HTTPS local (option)</text>
  <text class="ligne" x="254" y="74">https://NOM-PC:8443</text>
  <rect x="460" y="34" width="220" height="54" rx="4" fill="#EAF6F0" stroke="#00A86B"/>
  <text class="titre" x="474" y="58">Internet — portail parents</text>
  <text class="ligne" x="474" y="74">Tailscale Funnel · 443</text>

  <path class="lien" d="M120 88V100H570V88"/>
  <path class="lien" d="M340 88V100"/>
  <path class="accent" d="M120 100V134" marker-end="url(#fleche)"/>

  <!-- Docker -->
  <rect x="20" y="106" width="660" height="204" rx="6" fill="#FBF9F4" stroke="#C9D0D8" stroke-dasharray="5 4"/>
  <text class="etape" x="32" y="124" fill="#6C7787">DOCKER DESKTOP · RÉSEAU INTERNE</text>

  <rect x="44" y="140" width="150" height="76" rx="4" fill="#EAF6F0" stroke="#00A86B"/>
  <rect x="44" y="140" width="150" height="3" fill="#00A86B"/>
  <text class="titre" x="56" y="164">proxy</text>
  <text class="ligne" x="56" y="182">Caddy · TLS</text>
  <text class="ligne" x="56" y="198">ports 8001 et 8443</text>

  <rect x="238" y="140" width="170" height="76" rx="4" fill="#EAF6F0" stroke="#00A86B"/>
  <rect x="238" y="140" width="170" height="3" fill="#00A86B"/>
  <text class="titre" x="250" y="164">web</text>
  <text class="ligne" x="250" y="182">Django + Gunicorn</text>
  <text class="ligne" x="250" y="198">port 8000</text>

  <rect x="452" y="140" width="196" height="76" rx="4" fill="#F4EFE4" stroke="#B0803A"/>
  <rect x="452" y="140" width="196" height="3" fill="#B0803A"/>
  <text class="titre" x="464" y="164">sms</text>
  <text class="ligne" x="464" y="182">réception des SMS des parents</text>
  <text class="ligne" x="464" y="198">webhook de la passerelle</text>

  <rect x="238" y="244" width="170" height="62" rx="4" fill="#F4EFE4" stroke="#B0803A"/>
  <text class="titre" x="250" y="266">db</text>
  <text class="ligne" x="250" y="284">PostgreSQL · volume pgdata</text>

  <rect x="452" y="244" width="196" height="62" rx="4" fill="#F4EFE4" stroke="#B0803A"/>
  <text class="titre" x="464" y="266">redis</text>
  <text class="ligne" x="464" y="282">cache, sessions et files d'attente</text>
  <text class="ligne" x="464" y="293">volume redisdata</text>

  <path class="accent" d="M196 170H232" marker-end="url(#fleche)"/>
  <text class="note" x="196" y="164">HTTP</text>
  <path class="accent" d="M414 158H446" marker-end="url(#fleche)"/>
  <text class="note" x="414" y="152">webhook</text>
  <path class="accent" d="M290 218V238" marker-end="url(#fleche)"/>
  <path class="accent" d="M408 202L448 258" marker-end="url(#fleche)"/>

  <!-- Hôte -->
  <path class="accent" d="M350 312V326" marker-end="url(#fleche)"/>
  <rect x="20" y="328" width="660" height="40" rx="4" fill="#0A1628"/>
  <text class="blanc" x="34" y="346">Hôte Windows — C:\\YELEN-SCHOOL</text>
  <text class="gris" x="34" y="361">.env · logs\\ · data\\ · media\\ · volumes nommés conservés entre les mises à jour</text>
</svg>
"""


# ── Schéma : mise à jour en un clic (chapitre 8) ─────────────────────────────
MISE_A_JOUR = """
<svg class="schema" viewBox="0 0 700 208" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Mise à jour en un clic : les cinq étapes et le retour arrière">
  <defs>
    <marker id="f2" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6"
            orient="auto-start-reverse">
      <path d="M0 1.4L8.5 5L0 8.6z" fill="#B0803A"/>
    </marker>
    <marker id="f2g" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6"
            orient="auto-start-reverse">
      <path d="M0 1.4L8.5 5L0 8.6z" fill="#8C97A5"/>
    </marker>
    <style>
      .n   { font-family: Inter, sans-serif; font-size: 8px; font-weight: 700; fill: #B0803A;
             letter-spacing: 1.4px; }
      .t   { font-family: Inter, sans-serif; font-size: 10px; font-weight: 600; fill: #0A1628; }
      .d   { font-family: Inter, sans-serif; font-size: 8.2px; fill: #3B4655; }
      .g   { font-family: Inter, sans-serif; font-size: 8px; fill: #6C7787; }
      .fl  { stroke: #B0803A; stroke-width: 1.4; fill: none; }
      .flg { stroke: #8C97A5; stroke-width: 1.2; fill: none; stroke-dasharray: 4 3; }
    </style>
  </defs>

  <text class="n" x="0" y="12">MISE À JOUR EN UN CLIC — METTRE-A-JOUR.BAT</text>

  <!-- cinq étapes -->
  <g>
    <rect x="0" y="24" width="128" height="72" rx="4" fill="#FBF9F4" stroke="#B0803A"/>
    <text class="n" x="12" y="42">ÉTAPE 1</text>
    <text class="t" x="12" y="60">Version</text>
    <text class="d" x="12" y="76">VERSION + dépôt</text>
    <text class="d" x="12" y="88">GitHub (main)</text>
  </g>
  <g>
    <rect x="144" y="24" width="128" height="72" rx="4" fill="#FBF9F4" stroke="#B0803A"/>
    <text class="n" x="156" y="42">ÉTAPE 2</text>
    <text class="t" x="156" y="60">Sauvegarde</text>
    <text class="d" x="156" y="76">complète et chiffrée</text>
    <text class="d" x="156" y="88">(§5)</text>
  </g>
  <g>
    <rect x="288" y="24" width="128" height="72" rx="4" fill="#FBF9F4" stroke="#B0803A"/>
    <text class="n" x="300" y="42">ÉTAPE 3</text>
    <text class="t" x="300" y="60">Mise à jour</text>
    <text class="d" x="300" y="76">code, image,</text>
    <text class="d" x="300" y="88">redémarrage</text>
  </g>
  <g>
    <rect x="432" y="24" width="128" height="72" rx="4" fill="#FBF9F4" stroke="#B0803A"/>
    <text class="n" x="444" y="42">ÉTAPE 4</text>
    <text class="t" x="444" y="60">Contrôle</text>
    <text class="d" x="444" y="76">/health/ jusqu'à la</text>
    <text class="d" x="444" y="88">bonne version (3 min)</text>
  </g>
  <g>
    <rect x="576" y="24" width="124" height="72" rx="4" fill="#EAF6F0" stroke="#00A86B"/>
    <text class="n" x="588" y="42" fill="#067955">ÉTAPE 5</text>
    <text class="t" x="588" y="60">Trois contrôles</text>
    <text class="d" x="588" y="76">version, conteneurs,</text>
    <text class="d" x="588" y="88">recette 2 min (§8.5)</text>
  </g>

  <path class="fl" d="M128 60H140" marker-end="url(#f2)"/>
  <path class="fl" d="M272 60H284" marker-end="url(#f2)"/>
  <path class="fl" d="M416 60H428" marker-end="url(#f2)"/>
  <path class="fl" d="M560 60H572" marker-end="url(#f2)"/>

  <!-- garanties -->
  <rect x="0" y="116" width="352" height="48" rx="4" fill="#FDF6E8" stroke="#C58C2A"/>
  <text class="t" x="12" y="134" font-size="9.4">Sauvegarde impossible</text>
  <text class="d" x="12" y="150">la mise à jour est annulée, rien n'est modifié.</text>

  <rect x="372" y="116" width="328" height="48" rx="4" fill="#F1F5FA" stroke="#34506F"/>
  <text class="t" x="384" y="134" font-size="9.4">Échec de reconstruction ou de réponse</text>
  <text class="d" x="384" y="150">l'ancienne version est reconstruite et redémarrée (§8.4).</text>

  <path class="flg" d="M208 96V112" marker-end="url(#f2g)"/>
  <path class="flg" d="M352 96L520 112" marker-end="url(#f2g)"/>
  <text class="g" x="0" y="186">Journal : logs\\mise-a-jour.log · options : -SansSauvegarde (déconseillé), -DelaiAttente 600</text>
  <text class="g" x="0" y="200">Les postes connectés adoptent la nouvelle version sans Ctrl+F5 (cache identifié par version).</text>
</svg>
"""

# ── Schéma : cycle de vie d'une sauvegarde (chapitre 5) ─────────────────────
CYCLE_SAUVEGARDE = """
<svg class="schema" viewBox="0 0 700 170" xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Cycle de vie d'une sauvegarde : export, chiffrement, rétention, copie hors machine, essai de restauration">
  <defs>
    <marker id="f3" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6"
            orient="auto-start-reverse">
      <path d="M0 1.4L8.5 5L0 8.6z" fill="#B0803A"/>
    </marker>
    <style>
      .n3 { font-family: Inter, sans-serif; font-size: 8px; font-weight: 700; fill: #B0803A;
            letter-spacing: 1.4px; }
      .t3 { font-family: Inter, sans-serif; font-size: 10px; font-weight: 600; fill: #0A1628; }
      .d3 { font-family: Inter, sans-serif; font-size: 8.2px; fill: #3B4655; }
      .g3 { font-family: Inter, sans-serif; font-size: 8px; fill: #6C7787; }
      .fl3 { stroke: #B0803A; stroke-width: 1.4; fill: none; }
    </style>
  </defs>

  <text class="n3" x="0" y="12">CYCLE DE VIE D'UNE SAUVEGARDE — UNE PAIRE DE FICHIERS, CINQ MAILLONS</text>

  <rect x="0" y="24" width="120" height="76" rx="4" fill="#FBF9F4" stroke="#B0803A"/>
  <text class="t3" x="12" y="44">1 · Export</text>
  <text class="d3" x="12" y="62">.dump PostgreSQL</text>
  <text class="d3" x="12" y="74">+ _media.tar.gz</text>
  <text class="d3" x="12" y="86">écrits ensemble</text>

  <rect x="146" y="24" width="120" height="76" rx="4" fill="#FBF9F4" stroke="#B0803A"/>
  <text class="t3" x="158" y="44">2 · Chiffrement</text>
  <text class="d3" x="158" y="62">suffixe .enc</text>
  <text class="d3" x="158" y="74">phrase secrète</text>
  <text class="d3" x="158" y="86">hors du serveur (§5.4)</text>

  <rect x="292" y="24" width="120" height="76" rx="4" fill="#FBF9F4" stroke="#B0803A"/>
  <text class="t3" x="304" y="44">3 · Rétention</text>
  <text class="d3" x="304" y="62">30 paires par défaut</text>
  <text class="d3" x="304" y="74">-Keep pour ajuster</text>
  <text class="d3" x="304" y="86">tâche planifiée (§6.1)</text>

  <rect x="438" y="24" width="120" height="76" rx="4" fill="#FBF9F4" stroke="#B0803A"/>
  <text class="t3" x="450" y="44">4 · Copie externe</text>
  <text class="d3" x="450" y="62">disque externe,</text>
  <text class="d3" x="450" y="74">NAS, autre poste</text>
  <text class="d3" x="450" y="86">hors du serveur (§5.2)</text>

  <rect x="584" y="24" width="116" height="76" rx="4" fill="#EAF6F0" stroke="#00A86B"/>
  <text class="t3" x="596" y="44">5 · Essai</text>
  <text class="d3" x="596" y="62">restauration réelle</text>
  <text class="d3" x="596" y="74">une fois par trimestre</text>
  <text class="d3" x="596" y="86">(§9.7)</text>

  <path class="fl3" d="M120 62H142" marker-end="url(#f3)"/>
  <path class="fl3" d="M266 62H288" marker-end="url(#f3)"/>
  <path class="fl3" d="M412 62H434" marker-end="url(#f3)"/>
  <path class="fl3" d="M558 62H580" marker-end="url(#f3)"/>

  <rect x="0" y="118" width="700" height="40" rx="4" fill="#FDF6E8" stroke="#C58C2A"/>
  <text class="d3" x="12" y="136">Une sauvegarde qui n'a jamais été restaurée n'est pas une sauvegarde prouvée : le fichier peut être tronqué, la</text>
  <text class="d3" x="12" y="150">phrase secrète perdue, le volume média absent. L'essai trimestriel est la seule preuve acceptée (§9.7).</text>
</svg>
"""

# ── Guide d'utilisation ─────────────────────────────────────────────────────
UTILISATION = {
    'cle': 'utilisation',
    'fichier': 'GUIDE_UTILISATION_YELEN_SCHOOL.md',
    'sortie': 'GUIDE_UTILISATION_YELEN_SCHOOL.pdf',
    'titre_court': "YELEN SCHOOL · Guide d'utilisation",
    'surtitre': "Édition {version} · Manuel officiel",
    'couverture_titre': "Guide<br>d'utilisation",
    'couverture_sous_titre': "Gestion scolaire complète — inscriptions, pédagogie,<br>finances, documents et "
                             "communication avec les familles.",
    'fiche_titre': "YELEN SCHOOL<br>Guide d'utilisation",
    'fiche': [
        ("Logiciel", "YELEN SCHOOL — gestion d'établissement scolaire (Django, mode autonome SQLite ou serveur "
                     "PostgreSQL), interface en français."),
        ("Version documentée", "{version}"),
        ("Édition du guide", "{version_guide} — {date}"),
        ("Public", "Direction, secrétariat, comptabilité, enseignants, surveillants, parents et élèves."),
        ("Portée", "40 chapitres : de la connexion jusqu'aux fonctions les plus récentes, avec les écrans réels "
                   "de l'application et des exemples de saisie champ par champ."),
        ("Modules couverts", "{modules}"),
        ("Rédaction", "{redaction}"),
    ],
    'fiche_intro': [
        "Ce manuel décrit le comportement réel du logiciel : chaque écran cité existe, chaque libellé de champ "
        "correspond à celui affiché par l'application. Les captures proviennent d'une base de démonstration, avec "
        "des noms et des montants fictifs.",
        "Il s'utilise de deux façons : en lecture linéaire pour une prise en main complète, ou comme référence — "
        "le sommaire donne la page de chaque chapitre, et chaque ouverture de chapitre liste ses sections avec "
        "leur page.",
    ],
    'ignorer': ('TABLE DES MATIÈRES',),
    'annexes': (),
    'avant_propos': None,
    'parties': [
        ('I', 'Prise en main', "Le contexte du produit, la connexion, le tableau de bord et les paramètres de "
                               "l'établissement : de quoi ouvrir l'application et la configurer.", [1, 2, 3]),
        ('II', 'Élèves, personnel et pédagogie', "Inscriptions, dossiers du personnel, notes et bulletins, présences "
                                                 "et vie scolaire : le cœur du travail quotidien.", [4, 5, 6, 7, 8]),
        ('III', 'Argent et évaluation', "Scolarité, encaissements, dépenses, examens officiels et vacations : tout "
                                        "ce qui se compte et se justifie.", [9, 10, 11]),
        ('IV', 'Documents et pilotage', "Documents administratifs, licences, statistiques et état des "
                                        "fonctionnalités : les productions et les tableaux de bord de la direction.",
         [12, 13, 14, 15]),
        ('V', 'Références et interface', "Questions fréquentes, glossaire et design system : le vocabulaire et les "
                                         "règles graphiques de l'application.", [16, 17, 18]),
        ('VI', 'Portails, innovations et familles', "Portail parent, signature électronique, prédiction de réussite, "
                                                    "APC, bourses, assistant IA, budget, manuels, hors ligne, "
                                                    "communication, emploi du temps, localisations.",
         [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]),
        ('VII', 'Exploitation, sécurité et qualité', "Mode autonome, SMS des familles, galerie d'écrans, sécurité, "
                                                     "source de vérité, import de fichiers, services annexes, "
                                                     "contrôle qualité et offre hébergée.",
         [31, 32, 33, 34, 35, 36, 37, 38, 39]),
        ('VIII', 'Annexes pratiques', "Exemples de saisie champ par champ : des valeurs réelles à recopier pour "
                                      "chaque formulaire du logiciel.", [40]),
    ],
    'fin': [
        "Ce manuel décrit la version {version} du logiciel. Il est régénéré à chaque évolution de l'interface : "
        "seule l'édition en ligne, à jour, fait foi.",
        "Une question qui n'a pas de réponse ici ? Le chapitre 16 rassemble les questions fréquentes, le chapitre 17 "
        "le vocabulaire, et le guide de déploiement Windows (<i>docs/GUIDE_DEPLOIEMENT_WINDOWS</i>) traite de "
        "l'installation, des sauvegardes et de la mise à jour du serveur.",
    ],
    'som_intro': "Les numéros renvoient à la page imprimée. Chaque ouverture de chapitre détaille ensuite ses "
                 "sections, avec leur page.",
    'schemas': [],
}

# ── Guide de déploiement Windows ────────────────────────────────────────────
DEPLOIEMENT = {
    'cle': 'deploiement',
    'fichier': 'GUIDE_DEPLOIEMENT_WINDOWS.md',
    'sortie': 'GUIDE_DEPLOIEMENT_WINDOWS.pdf',
    'titre_court': "YELEN SCHOOL · Guide de déploiement",
    'surtitre': "Édition {version} · Guide technique",
    'couverture_titre': "Guide de<br>déploiement<br>Windows",
    'couverture_sous_titre': "Installation, configuration, sauvegardes, mises à jour et dépannage<br>du serveur "
                             "d'école — cinq conteneurs Docker, PostgreSQL et Redis.",
    'fiche_titre': "YELEN SCHOOL<br>Guide de déploiement Windows",
    'fiche': [
        ("Logiciel", "YELEN SCHOOL — gestion d'établissement scolaire, cinq conteneurs Docker "
                     "(<code>proxy</code>, <code>web</code>, <code>sms</code>, <code>db</code>, <code>redis</code>)."),
        ("Version couverte", "{version}"),
        ("Édition du guide", "4 novembre 2026"),
        ("Public", "Administrateur technique de l'établissement, ou prestataire qui installe la machine."),
        ("Objet", "Installer, exploiter, sauvegarder, mettre à jour et dépanner le serveur d'école sur Windows, "
                  "puis ouvrir l'application au réseau local et, si besoin, à distance."),
        ("Environnement", "Windows 10 ou 11, Docker Desktop avec WSL 2, PostgreSQL 16 et Redis 7 dans leurs "
                          "volumes Docker, accès optionnel à Internet."),
        ("Dossier", "<code>C:\\YELEN-SCHOOL</code> — <code>.env</code>, <code>logs\\</code>, <code>data\\</code>, "
                    "<code>media\\</code>"),
        ("Ports", "<code>8001</code> (HTTP), <code>8443</code> (HTTPS local et Tailscale Serve), "
                  "<code>443</code> (portail parents par Funnel)"),
    ],
    'fiche_intro': [
        "Ce guide est le mode d'emploi technique du serveur d'école. Il suppose un lecteur qui sait ouvrir une "
        "invite de commandes, éditer un fichier texte et redémarrer un service ; il ne suppose aucune connaissance "
        "de Django, de PostgreSQL ni de Docker.",
        "Chaque commande est donnée telle qu'elle doit être saisie, avec le résultat attendu juste après. Les "
        "opérations irréversibles (restauration, retour arrière, remise à zéro d'un mot de passe) sont signalées "
        "par un encadré de sécurité, à lire avant d'agir.",
    ],
    'ignorer': ('Sommaire',),
    'annexes': ('Règles essentielles à retenir',),
    'avant_propos': "Avant-propos",
    'parties': [
        ('I', 'Socle technique', "Ce que l'installation met en place : les cinq conteneurs, les prérequis de la "
                                 "machine, l'arborescence du dossier et la répartition sur plusieurs partitions.",
         [1]),
        ('II', 'Installation et première configuration', "De l'obtention des fichiers au premier accès réussi : "
                                                         "installation, fichier <code>.env</code>, compte initial, "
                                                         "adresse locale, validations et licence signée.", [2, 3]),
        ('III', 'Exploitation quotidienne', "Démarrer, arrêter, lire les journaux, sauvegarder et vérifier une "
                                            "sauvegarde, programmer les tâches automatiques.", [4, 5, 6]),
        ('IV', 'Incidents et mises à jour', "Restaurer après incident, mettre à jour sans perte de données, revenir "
                                            "en arrière et contrôler après chaque évolution.", [7, 8]),
        ('V', 'Réseau, accès et dépannage', "Adresse locale, pare-feu Windows, HTTPS, portail parents, accès du "
                                            "personnel par Tailscale et remèdes aux pannes courantes.",
         [9, 10]),
        ('VI', 'Continuité d\'exploitation', "Reprise sur une nouvelle machine et les règles à ne jamais oublier.",
         [11, 'Règles essentielles à retenir']),
    ],
    'fin': [
        "Ce guide décrit la version {version} du logiciel. Toute mise à jour de l'application s'accompagne d'une "
        "relecture du chapitre 8 et des trois contrôles qui le terminent.",
        "Le mode d'emploi fonctionnel — droits par rôle, écrans, exemples de saisie champ par champ — se trouve "
        "dans le guide d'utilisation (<i>docs/GUIDE_UTILISATION_YELEN_SCHOOL</i>).",
    ],
    'som_intro': "Les numéros renvoient à la page imprimée. Chaque ouverture de chapitre détaille ensuite ses "
                 "sections, avec leur page.",
    'schemas': [
        {'chapitre': 1, 'titre': "Architecture du serveur d'école — accès, conteneurs et hôte Windows",
         'svg': ARCHITECTURE},
        {'chapitre': 5, 'titre': "Cycle de vie d'une sauvegarde — de l'export à l'essai de restauration",
         'svg': CYCLE_SAUVEGARDE},
        {'chapitre': 8, 'titre': "Mise à jour en un clic — les cinq étapes et les garanties de retour arrière",
         'svg': MISE_A_JOUR},
    ],
}

DOCUMENTS = {d['cle']: d for d in (UTILISATION, DEPLOIEMENT)}
