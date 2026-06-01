🎓

__YELEN SCHOOL__

*Guide Complet du Développeur*

*"Illuminer chaque parcours scolaire"*

__VERSION 2\.0 — MIS À JOUR POUR LE PROMPT v3\.3__

*10 Skills IA · 13 Apps Django · Nouveaux modules : Personnel · Vacations · Paramètres*

*Âge calculé automatiquement · Matricules PERS\- · Statistiques listes classes · Carte d'Identité Scolaire*

__Élément__

__Détail__

Version guide

2\.0 — Mars 2026

Réf\. spécifications

YELEN\_SCHOOL\_Prompt\_v3\_3\_Documents\_Administratifs

Auteur

Guide mis à jour — YELEN SCHOOL

Destinataire

Développeur YELEN SCHOOL — Burkina Faso

IDE principal

Google Antigravity \(gratuit — préversion publique 2026\)

Stack

Django 4\.2 · PostgreSQL · Redis · Docker · HTMX · Tailwind CSS

Nouveautés v2\.0

Apps : parametres, personnel, vacations · Skills 9 & 10 · Workflows Phase 2 & 3 enrichis · Matricules PERS\- · Âge calculé

📋 Ce guide couvre :

✅ Installation complète de Google Antigravity et configuration pour YELEN SCHOOL

✅ Exploitation du Prompt v3\.3 \(spécification de référence à jour\)

✅ 10 Skills IA spécialisés \(8 existants mis à jour \+ 2 nouveaux pour v3\.3\)

✅ Workflows concrets sprint par sprint avec prompts prêts à copier\-coller

✅ Configuration complète des 13 apps Django \(dont parametres, personnel, vacations\)

✅ Règles métier v3\.3 : matricule unique élève/personnel, âge calculé, Directeur/Proviseur

# PARTIE 1 — MISE EN PLACE DE L'ENVIRONNEMENT DE DÉVELOPPEMENT

## 1\.1 Prérequis système et installations

⚠️  Vérifie ces prérequis AVANT d'installer Antigravity

• Système : Windows 10/11 64\-bit, macOS 12\+, ou Ubuntu 20\.04\+

• RAM disponible : 8 Go minimum libres

• Espace disque : 10 Go libres minimum

• Connexion internet : requise pour l'installation initiale

• Compte Google \(Gmail\) : obligatoire pour Antigravity

__Étape 1\.1\.A — Installe Python 3\.11__

▌ Terminal / PowerShell

python \-\-version

\# Résultat attendu : Python 3\.11\.x ou 3\.12\.x

\# Linux \(Ubuntu\)

sudo apt update && sudo apt install python3\.11 python3\.11\-venv python3\-pip \-y

\# macOS

brew install python@3\.11

\# Windows : télécharge depuis https://python\.org/downloads/

\# ✅ IMPORTANT : coche 'Add Python to PATH' pendant l'installation

__Étape 1\.1\.B — Installe Git__

▌ Installation Git

\# Linux

sudo apt install git \-y

\# Vérifie l'installation

git \-\-version  \# Résultat attendu : git version 2\.x\.x

git config \-\-global user\.name "Ton Nom"

git config \-\-global user\.email "ton@email\.com"

__Étape 1\.1\.C — Installe Docker Desktop__

▌ Installation Docker

\# Windows / macOS : https://www\.docker\.com/products/docker\-desktop/

\# Linux \(Ubuntu\)

curl \-fsSL https://get\.docker\.com | sh

sudo usermod \-aG docker $USER

newgrp docker

docker \-\-version        \# Docker version 24\.x\.x

docker\-compose \-\-version  \# Docker Compose version 2\.x\.x

__Étape 1\.1\.D — Installe Node\.js \(requis pour Tailwind CSS\)__

▌ Installation Node\.js

\# Linux

curl \-fsSL https://deb\.nodesource\.com/setup\_20\.x | sudo \-E bash \-

sudo apt install nodejs \-y

node \-\-version  \# v20\.x\.x

npm \-\-version   \# 10\.x\.x

## 1\.2 Installation de Google Antigravity

💡 Pourquoi Google Antigravity pour YELEN SCHOOL ?

• 100% gratuit en préversion publique \(compte Gmail suffisant\)

• Agent\-first : plusieurs agents IA en parallèle sur différents modules

• Navigateur intégré : test visuel des templates Django sans quitter l'IDE

• Support Claude Sonnet 4\.6 \+ Gemini 3 Pro : meilleure qualité pour Django

• Skills personnalisables : injection de contexte YELEN SCHOOL permanent

▌ Installation Antigravity

→ Va sur : antigravity\.google/download

→ Clique sur ton système : Windows / macOS / Linux

→ Lance l'installeur téléchargé

→ Connexion avec compte Google : Sign in with Google

→ Ajoute l'extension Claude Code \(optionnel\) : Extensions → 'claude code' → Install

   Entre ta clé API Anthropic \(format : sk\-ant\-api03\-XXXXXXXX\)

## 1\.3 Configuration initiale — Règles Globales Antigravity

⭐ Les Règles Globales sont injectées dans CHAQUE message envoyé à l'IA\.

Antigravity → Menu ⋮ \(trois points\) → 'Customizations' → 'Global Rules' → Colle le texte ci\-dessous → Save

⚠️  MISE À JOUR v2\.0 : les règles globales ci\-dessous intègrent les nouvelles règles du Prompt v3\.3 :

  • Matricule élève BF\- et matricule personnel PERS\- distincts

  • Âge calculé automatiquement \(non stocké en base\)

  • Directeur/Proviseur \(remplace Directeur/SG\)

  • Périodes configurables \(trimestres OU semestres\)

  • 13 apps Django \(dont parametres, personnel, vacations\)

▌ global\_rules\.txt — À copier dans Antigravity Customizations

\# ═══════════════════════════════════════════════════════

\# YELEN SCHOOL — Règles Globales Agent IA — v2\.0

\# Réf\. Prompt v3\.3 — Mars 2026

\# ═══════════════════════════════════════════════════════

Tu développes YELEN SCHOOL, une application web Django de

gestion scolaire pour le Burkina Faso\.

\#\# STACK TECHNIQUE \(non négociable\)

\- Backend : Django 4\.2 LTS \+ Django REST Framework

\- Frontend : HTMX \+ Alpine\.js \+ Tailwind CSS

\- BDD : PostgreSQL 15 \(jamais SQLite en dev\)

\- Cache : Redis 7

\- PDF : WeasyPrint 60\+

\- Async : Celery \+ Redis

\- Docker : tout est conteneurisé

\- Fichiers : MinIO \(self\-hosted, jamais AWS S3 payant\)

\#\# APPS DJANGO \(13 apps — toutes obligatoires\)

core, accounts, licences, etablissements, parametres,

inscriptions, personnel, pedagogie, bulletins, presences,

vacations, examens, finances, documents

\#\# RÈGLES CODE \(non négociables\)

\- 100% open\-source, zéro dépendance payante

\- Tests unitaires obligatoires \(pytest, coverage > 80%\)

\- Commentaires en français

\- Type hints Python sur toutes les fonctions

\- Docstrings sur toutes les classes Django

\- Lis TOUJOURS docs/PROMPT\_V3\_3\.md avant tout nouveau module

\#\# RÈGLES MÉTIER v3\.3 — CRITIQUES

\- Matricule ÉLÈVE  : BF\-\{REGION\}\-\{ANNEE\}\-\{SEQ:04d\}

  ex : BF\-OUA\-2026\-0042

\- Matricule PERSONNEL : PERS\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

  ex : PERS\-YSK\-2026\-0001

  TOUJOURS distinguer les deux préfixes — jamais les mélanger

\- ÂGE : JAMAIS stocké en base\. Toujours calculé dynamiquement\.

  Backend  : @property def age\(self\) → \(date\.today\(\) \- self\.date\_naissance\)\.days // 365

  Frontend : onChange\(date\_naissance\) → differenceInYears\(new Date\(\), dateNaissance\)

  Affichage : champ disabled, fond grisé, libellé 'X an\(s\)'

\- INSCRIPTION/RÉINSCRIPTION : matricule = référence unique\.

  Sélection par liste déroulante matricule → auto\-remplissage\.

  JAMAIS ressaisir les infos personnelles déjà enregistrées\.

\- Personnel : InscriptionPersonnel validée OBLIGATOIRE chaque année

  pour qu'un membre soit actif dans emplois du temps, présences, etc\.

\- Directeur/Proviseur \(jamais Directeur/SG\)

\- Censeur/Proviseur \(jamais Censeur/SG\)

\- Périodes : CONFIGURABLE — trimestres OU semestres selon l'étab\.

  Ne jamais hardcoder '3 trimestres'\.

\#\# CONTEXTE BURKINA FASO

\- Notes sur 20 \(jamais sur 100\)

\- Vert si note >= 16, Or si >= 12, Rouge si < 12

\- Montants en FCFA \(jamais $, €\)

\- Dates : JJ/MM/AAAA

\- Examens : CEP \(CM2\) · BEPC \(3ème\) · BAC \(Terminale A/B/C/D\)

\#\# SÉCURITÉ

\- Vérifier Feature Flag licence sur CHAQUE vue

\- Décorateur : @requires\_licence\_feature\('nom'\)

\- Variables sensibles dans \.env \(jamais en dur\)

\#\# DESIGN

\- Fond global : \#0A1628

\- Surface cartes : \#111E35

\- Vert principal : \#00A86B

\- Or : \#F5A623

\- Police : Outfit \(interface\) \+ Playfair Display \(logo\)

\- JAMAIS fond blanc, JAMAIS Arial/Inter dans les templates

## 1\.4 Configuration initiale du projet YELEN SCHOOL

▌ Terminal — Création structure

\# Dans le terminal Antigravity \(Ctrl\+\` pour l'ouvrir\)

cd yelen\-school

\# Crée les dossiers de documentation

mkdir \-p docs skills\. antigravity

\# Copie ton fichier de référence dans docs/

\# → docs/PROMPT\_V3\_3\.md \(contenu du Prompt v3\.3 — fichier de référence\)

\# → docs/DESIGN\_SYSTEM\.md

\# → docs/PREVIEW\_COMPONENTS\.md

▌ \.antigravity/config\.json — ⭐ MIS À JOUR v2\.0 : référence PROMPT\_V3\_3

\{

  "project": "YELEN SCHOOL",

  "version": "3\.3",

  "defaultModel": "gemini\-3\-pro",

  "fallbackModel": "claude\-sonnet\-4\-6",

  "contextFiles": \[

    "docs/DESIGN\_SYSTEM\.md",

    "docs/PROMPT\_V3\_3\.md",

    "docs/PREVIEW\_COMPONENTS\.md"

  \],

  "agents": \{

    "architect": \{ "model": "gemini\-3\-pro",     "mode": "plan",  "description": "Analyse et planifie" \},

    "coder":     \{ "model": "claude\-sonnet\-4\-6","mode": "build", "description": "Implémente Django/Python" \},

    "designer":  \{ "model": "gemini\-3\-pro",     "mode": "build", "description": "Génère templates HTMX" \},

    "reviewer":  \{ "model": "claude\-sonnet\-4\-6","mode": "plan",  "description": "Revue code, sécurité, tests" \}

  \},

  "autoContext": true,

  "alwaysRead": \["docs/DESIGN\_SYSTEM\.md", "docs/PROMPT\_V3\_3\.md"\]

\}

## 1\.5 Initialisation Django — 13 Apps \(mise à jour v2\.0\)

⭐ MISE À JOUR v2\.0 : 3 nouvelles apps ajoutées par rapport au guide v1\.0 :

  • paramètres  — Configuration établissement \(cycles, classes, postes, tarifs…\)

  • personnel   — Enregistrement et inscription annuelle du personnel

  • vacations   — Gestion des professeurs vacataires et bilans mensuels

▌ Terminal — Initialisation Django v2\.0

\# 1\. Crée et active l'environnement virtuel Python

python \-m venv venv

source venv/bin/activate  \# Linux/macOS

venv\\Scripts\\activate     \# Windows

\# 2\. Installe les dépendances

pip install django==4\.2\.\* djangorestframework django\-environ

pip install psycopg2\-binary celery redis django\-redis django\-htmx

pip install weasyprint qrcode pillow python\-dateutil

pip install pytest pytest\-django pytest\-cov model\-bakery

\# 3\. Crée le projet Django

django\-admin startproject yelen\_school \.

\# 4\. ⭐ Crée les 13 apps Django \(v2\.0 — 3 nouvelles vs v1\.0\)

python manage\.py startapp core

python manage\.py startapp accounts

python manage\.py startapp licences

python manage\.py startapp etablissements

python manage\.py startapp parametres      \# ⭐ NOUVEAU v2\.0

python manage\.py startapp inscriptions

python manage\.py startapp personnel       \# ⭐ NOUVEAU v2\.0

python manage\.py startapp pedagogie

python manage\.py startapp bulletins

python manage\.py startapp presences

python manage\.py startapp vacations       \# ⭐ NOUVEAU v2\.0

python manage\.py startapp examens

python manage\.py startapp finances

python manage\.py startapp documents

\# 5\. Génère le fichier requirements\.txt

pip freeze > requirements/base\.txt

# PARTIE 2 — EXPLOITATION DU PROMPT v3\.3 AVEC ANTIGRAVITY

📄 Le Prompt v3\.3 est la SOURCE DE VÉRITÉ du projet YELEN SCHOOL\.

Il remplace le Prompt v2\.0 comme document de référence principal\.

Convertis\-le en Markdown et place\-le dans docs/PROMPT\_V3\_3\.md\.

Toutes les références dans les Skills et prompts pointent vers ce fichier\.

## 2\.1 Conversion et utilisation du Prompt v3\.3

▌ Conversion DOCX → Markdown

pip install mammoth

python \-c "

import mammoth

with open\('YELEN\_SCHOOL\_Prompt\_v3\_3\_Documents\_Administratifs\.docx', 'rb'\) as f:

    result = mammoth\.convert\_to\_markdown\(f\)

with open\('docs/PROMPT\_V3\_3\.md', 'w', encoding='utf\-8'\) as out:

    out\.write\(result\.value\)

print\('Conversion OK \!'\)

"

### Les 4 usages du Prompt v3\.3 dans Antigravity

__Usage__

__Quand l'utiliser__

__Prompt type__

Référence architecture

Avant de créer une nouvelle app Django

Lis docs/PROMPT\_V3\_3\.md section Architecture, puis crée l'app \[nom\]

Règles métier

Avant de coder une vue ou un modèle

Selon docs/PROMPT\_V3\_3\.md section \[X\], implémente la règle : \[règle\]

Feature Flags

Avant toute vue nécessitant une licence

Vérifie dans PROMPT\_V3\_3\.md les Feature Flags du module \[nom\]

Règles v3\.3 spécifiques

Avant tout code touchant élève ou personnel

Applique les règles matricule/âge/Proviseur de PROMPT\_V3\_3\.md section \[N\]

Révision Sprint

Au début de chaque sprint

Lis PROMPT\_V3\_3\.md et liste les tâches de la Phase \[N\] non encore implémentées

__📋 Prompt Architecte — À copier dans Agent Manager__

Mode : Plan | Agent : architect

────────────────────────────────────────────

Lis docs/PROMPT\_V3\_3\.md en entier\.

Je vais implémenter le module \[NOM DU MODULE\] cette semaine\.

Analyse :

1\. Quels modèles Django dois\-je créer ? \(champs, types, relations FK\)

2\. Quelles vues sont nécessaires ? \(CRUD \+ vues spéciales\)

3\. Quels Feature Flags de licence s'appliquent ?

4\. Quelles dépendances avec les autres modules existants ?

5\. Quels tests unitaires sont obligatoires ?

6\. Y a\-t\-il des règles v3\.3 spécifiques \(matricule, âge, Proviseur\) ?

Produis un plan d'implémentation en 5 étapes séquentielles\.

Ne modifie aucun fichier\. Attends ma validation\.

# PARTIE 3 — LES 10 SKILLS IA POUR YELEN SCHOOL

📁 Où placer les Skills ?

yelen\-school/skills/

├── 01\-django\-models\.md          \(mis à jour v2\.0\)

├── 02\-django\-views\.md           \(inchangé\)

├── 03\-htmx\-frontend\.md          \(mis à jour v2\.0 — âge calculé\)

├── 04\-pdf\-generator\.md          \(mis à jour v2\.0 — carte ID scolaire\)

├── 05\-docker\-devops\.md          \(inchangé\)

├── 06\-tests\-qualite\.md          \(inchangé\)

├── 07\-licence\-system\.md         \(mis à jour v2\.0 — nouveaux Feature Flags\)

├── 08\-burkina\-context\.md        \(mis à jour v2\.0 — règles v3\.3\)

├── 09\-age\-matricule\-frontend\.md \(⭐ NOUVEAU v2\.0\)

└── 10\-personnel\-vacations\.md    \(⭐ NOUVEAU v2\.0\)

Dans Antigravity : Settings → Skills → 'Add Skills Folder' → sélectionne skills/

## Skill 1 — Django Models Expert \(mis à jour v2\.0\)

▌ skills/01\-django\-models\.md

\# SKILL : Django Models Expert — YELEN SCHOOL v2\.0

\# ⭐ Mis à jour : nouveaux formats matricules \+ property age \+ modèles v3\.3

\#\# Modèle de base obligatoire

class BaseModel\(models\.Model\):

    created\_at = models\.DateTimeField\(auto\_now\_add=True\)

    updated\_at = models\.DateTimeField\(auto\_now=True\)

    class Meta:

        abstract = True

\#\# ⭐ Property age — JAMAIS stocker l'âge en base

from datetime import date

class Eleve\(BaseModel\):

    date\_naissance = models\.DateField\(\)

    @property

    def age\(self\) \-> int:

        """Âge calculé dynamiquement — non stocké en base\."""

        today = date\.today\(\)

        dob = self\.date\_naissance

        return today\.year \- dob\.year \- \(\(today\.month, today\.day\) < \(dob\.month, dob\.day\)\)

\#\# ⭐ Format matricule ÉLÈVE

\# BF\-\{REGION\}\-\{ANNEE\}\-\{SEQ:04d\}  ex : BF\-OUA\-2026\-0042

\# Généré via signal post\_save — JAMAIS modifiable après création

\#\# ⭐ Format matricule PERSONNEL — DISTINCT du matricule élève

\# PERS\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}  ex : PERS\-YSK\-2026\-0001

\# Préfixe PERS\- obligatoire — distingue visuellement élèves et personnel

\#\# Autres formats de numérotation YELEN SCHOOL

\# Certificats    : CERT\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

\# Attestations   : ATTEST\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

\# Cursus         : CURSUS\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

\# Autorisations  : AUTOR\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

\# Cartes ID      : CARTE\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}  ⭐ NOUVEAU

\# Inscriptions   : INSC\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

\# Licences       : YELEN\-\{4C\}\-\{4C\}\-\{4C\}\-\{4C\}

\#\# Migrations

\# \- help\_text sur les champs complexes

\# \- verbose\_name et verbose\_name\_plural en français

\# \- ordering par défaut sur created\_at desc

\# \- Signaux post\_save pour la génération automatique de numéros

## Skill 3 — HTMX Frontend Expert \(mis à jour v2\.0\)

▌ skills/03\-htmx\-frontend\.md

\# SKILL : HTMX Frontend Expert — YELEN SCHOOL v2\.0

\# ⭐ Mis à jour : patterns âge calculé \+ sélection matricule avec auto\-remplissage

\#\# ⭐ Pattern : Calcul automatique de l'âge \(NOUVEAU v3\.3\)

\# Dès saisie date de naissance → âge affiché en lecture seule

<\!\-\- Formulaire enregistrement élève — Étape 1 \-\->

<input type='date' name='date\_naissance' id='id\_date\_naissance'

       x\-model='dateNaissance'

       @change='calculerAge\(\)'>

<input type='text' id='age\_affiche' readonly disabled

       x\-model='ageAffiche'

       placeholder='Âge calculé automatiquement'

       class='input input\-readonly bg\-gray\-100 cursor\-not\-allowed'

       style='background:\#F5F5F5; border\-style:dashed;'>

<script>

function calculerAge\(\) \{

  const dob = new Date\(document\.getElementById\('id\_date\_naissance'\)\.value\);

  if \(\!dob || isNaN\(dob\)\) return;

  // Calcul âge en années entières révolues

  const diff = Date\.now\(\) \- dob\.getTime\(\);

  const ageDt = new Date\(diff\);

  const age = Math\.abs\(ageDt\.getUTCFullYear\(\) \- 1970\);

  document\.getElementById\('age\_affiche'\)\.value = age \+ ' an\(s\)';

\}

</script>

\#\# ⭐ Pattern : Sélection matricule avec auto\-remplissage \(NOUVEAU v3\.3\)

\# À l'inscription : sélection du matricule → champs personnels en lecture seule

<input type='text' id='matricule\_search'

       hx\-get='/api/eleves/autocomplete/'

       hx\-trigger='keyup changed delay:300ms'

       hx\-target='\#eleve\-infos\-panel'

       hx\-swap='innerHTML'

       placeholder='Matricule ou nom/prénom\.\.\.'>

<\!\-\- Les champs auto\-remplis sont TOUS en lecture seule \-\->

<input type='text' id='nom\_eleve' readonly disabled class='input\-readonly'>

<input type='text' id='date\_naissance\_eleve' readonly disabled class='input\-readonly'>

<input type='text' id='age\_eleve' readonly disabled class='input\-readonly bg\-gray\-100'>

\#\# Patterns HTMX standards

hx\-get='/url/'          → Requête GET au chargement ou événement

hx\-post='/url/'         → Requête POST \(formulaires\)

hx\-target='\#element\-id' → Où injecter la réponse

hx\-swap='innerHTML'     → Comment injecter

hx\-trigger='change'     → Événement déclencheur

hx\-indicator='\#spinner' → Élément loading pendant la requête

\#\# Alpine\.js — Pour les interactions sans serveur

<div x\-data='\{ open: false \}'>

  <button @click='open = \!open'>Menu</button>

  <div x\-show='open' x\-transition>Contenu</div>

</div>

## Skill 4 — PDF Generator Expert \(mis à jour v2\.0\)

▌ skills/04\-pdf\-generator\.md

\# SKILL : PDF Generator Expert — YELEN SCHOOL v2\.0

\# ⭐ Mis à jour : ajout CarteIdentiteScolaireGenerator \(5ème document\)

\#\# Les 5 générateurs PDF \(v3\.3\)

\# 1\. CertificatScolariteGenerator

\# 2\. AttestationNonRedevabiliteGenerator

\# 3\. CursusScolaireGenerator

\# 4\. AutorisationAbsenceGenerator

\# 5\. ⭐ CarteIdentiteScolaireGenerator  — NOUVEAU v3\.3

\#    BilanVacationGenerator            — NOUVEAU v3\.3

\#    ListePersonnelGenerator           — NOUVEAU v3\.3

\#    ListeClasseStatistiquesGenerator  — NOUVEAU v3\.3

\#\# ⭐ Carte d'Identité Scolaire — Spécifications PDF

\# Format : 85mm × 54mm \(standard carte bancaire\)

\# Disposition : 8 cartes par page A4 paysage \(4 colonnes × 2 lignes\)

\# Séparateurs : traits pointillés pour découpe

\# Impression : page 1 = tous les rectos | page 2 = tous les versos

\# Générée PAR CLASSE \(lot d'impression\)

@page \{ size: 85mm 54mm; margin: 2mm; \}  /\* Format carte individuelle \*/

/\* Ou pour impression 8 cartes par page A4 paysage \*/

@page \{ size: A4 landscape; margin: 5mm; \}

\.grid\-cartes \{ display: grid; grid\-template\-columns: repeat\(4, 85mm\); gap: 3mm; \}

\.carte \{ width: 85mm; height: 54mm; border: 1px dashed \#aaa; \}

\#\# Structure BaseDocumentGenerator \(inchangée\)

from weasyprint import HTML, CSS

import hashlib, qrcode, io, base64

class BaseDocumentGenerator:

    template\_name: str = None

    numero\_prefix: str = None

    def generate\(self, instance\) \-> bytes:

        qr\_b64 = self\.\_generate\_qr\(instance\)

        context = self\.get\_context\(instance\)

        context\['qr\_code\_b64'\] = qr\_b64

        html\_str = render\_to\_string\(self\.template\_name, context\)

        pdf = HTML\(string=html\_str, base\_url='/'\)\.write\_pdf\(\)

        instance\.hash\_document = hashlib\.sha256\(pdf\)\.hexdigest\(\)

        instance\.save\(update\_fields=\['hash\_document'\]\)

        return pdf

## Skill 7 — Licence System Expert \(mis à jour v2\.0\)

▌ skills/07\-licence\-system\.md

\# SKILL : Licence System Expert — YELEN SCHOOL v2\.0

\# ⭐ Mis à jour : nouveaux Feature Flags pour les modules v3\.3

\#\# Décorateur Feature Flag — Utilisation obligatoire

from licences\.decorators import requires\_licence\_feature

@requires\_licence\_feature\('carte\_identite\_scolaire'\)

def ma\_vue\(request\): \.\.\.

\#\# ⭐ Feature Flags COMPLETS v3\.3 \(mis à jour\)

\# Disponibles pour tous les niveaux \(Starter, Standard, Premium, Réseau\)

\# inscriptions              → tous

\# enregistrement\_eleves     → tous  ⭐ NOUVEAU

\# notes\_bulletins           → tous

\# presences                 → tous

\# finances\_base             → tous

\# certificats               → tous

\# attestations              → tous

\# autorisations\_absence     → tous

\# carte\_identite\_scolaire   → tous  ⭐ NOUVEAU

\# gestion\_personnel         → tous  ⭐ NOUVEAU

\# vacations                 → tous  ⭐ NOUVEAU

\# statistiques\_listes       → tous  ⭐ NOUVEAU

\# Disponibles à partir de Standard

\# cursus\_scolaire           → Standard, Premium, Réseau

\# examens\_officiels         → Standard, Premium, Réseau

\# portail\_parents           → Standard, Premium, Réseau

\# Disponibles à partir de Premium

\# ia\_predictive             → Premium, Réseau

\# Réseau uniquement

\# multi\_etablissements      → Réseau uniquement

\#\# Vérification dans les templates

\{% if request\.user\.etablissement\.licence\.has\_feature 'carte\_identite\_scolaire' %\}

  <a href='\{% url "carte\_id" %\}'>Carte d'identité scolaire</a>

\{% else %\}

  <span class='feature\-locked'>🔒 Starter requis</span>

\{% endif %\}

## Skill 8 — Burkina Faso Context Expert \(mis à jour v2\.0\)

▌ skills/08\-burkina\-context\.md

\# SKILL : Burkina Faso Context Expert — YELEN SCHOOL v2\.0

\# ⭐ Mis à jour : règles v3\.3 \(matricule PERS\-, âge calculé, périodes configurables\)

\#\# ⭐ Règles v3\.3 — CRITIQUES

\# Matricule élève : BF\-\{REGION\}\-\{ANNEE\}\-\{SEQ:04d\}

\# Matricule personnel : PERS\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

\# Les deux préfixes sont différents — jamais les confondre

\# ÂGE : propriété calculée — JAMAIS stocker en base

\# Calcul : \(date\.today\(\) \- date\_naissance\)\.days // 365

\# Affichage : champ readonly, fond grisé, format 'X an\(s\)'

\# AUTORITÉ : Directeur/Proviseur \(jamais Directeur/SG\)

\# Rôle RBAC : 'directeur\_proviseur' dans le système

\# PÉRIODES D'ÉVALUATION : CONFIGURABLE via PeriodeEvaluation

\# Ne jamais hardcoder '3 trimestres' — certains étabs font des semestres

\# Référencer toujours l'AnneeScolaire\.periodes\_evaluation\.all\(\)

\#\# Notes et moyennes

\# Toutes les notes sont sur 20

\# Coefficients MENA BF :

\# \- Devoir maison : coefficient 1

\# \- Composition   : coefficient 2

\# \- Examen        : coefficient 3

\# Formule moyenne : sum\(note \* coeff\) / sum\(coeff\)

\# Mentions : Très Bien >= 16 | Bien >= 14 | Assez Bien >= 12 | Passable >= 10

\#\# Cycles scolaires BF

\# Préscolaire : Crèche, PS, MS, GS

\# Primaire    : CP1, CP2, CE1, CE2, CM1, CM2

\# Post\-prim\.  : 6ème, 5ème, 4ème, 3ème

\# Secondaire  : Seconde, Première, Terminale \(A, B, C, D\)

\#\# Examens officiels BF

\# CEP  : Certificat d'Études Primaires \(CM2\)

\# BEPC : Brevet d'Études du Premier Cycle \(3ème\)

\# BAC  : Baccalauréat \(Terminale\) — séries A, B, C, D

\#\# Format des données

\# Dates     : JJ/MM/AAAA \(affichage\), ISO en base

\# Montants  : en FCFA, format : '12 500 FCFA' \(avec espace millier\)

\# Régions BF : OUA \(Ouaga\), BBO \(Bobo\), KOG \(Kougri\), etc\.

\#\# Statuts élève standard BF

\# Affecté par l'État \(dans établissements privés\)

\# Non affecté

\# Boursier

\# Exonéré

\# Redoublant

## ⭐ Skill 9 — Âge Calculé & Matricule Frontend Expert \(NOUVEAU v2\.0\)

Ce skill est NEW en v2\.0\. Il couvre toutes les règles d'implémentation

pour le calcul dynamique de l'âge et la sélection par matricule avec auto\-remplissage\.

À utiliser : avant tout écran d'enregistrement, d'inscription ou de réinscription\.

▌ skills/09\-age\-matricule\-frontend\.md

\# SKILL : Âge Calculé & Matricule Frontend Expert — YELEN SCHOOL v2\.0

\# ⭐ NOUVEAU — Règles issues du Prompt v3\.3

\#\# RÈGLE 1 : ÂGE CALCULÉ — JAMAIS STOCKÉ

\#\#\# Backend Python — Property sur le modèle

from datetime import date

class Eleve\(BaseModel\):

    @property

    def age\(self\) \-> int:

        """Âge en années révolues\. Calculé dynamiquement depuis date\_naissance\."""

        if not self\.date\_naissance:

            return None

        today = date\.today\(\)

        dob = self\.date\_naissance

        return today\.year \- dob\.year \- \(\(today\.month, today\.day\) < \(dob\.month, dob\.day\)\)

\#\#\# Serializer DRF — Exposer age en lecture seule

class EleveSerializer\(serializers\.ModelSerializer\):

    age = serializers\.SerializerMethodField\(read\_only=True\)

    def get\_age\(self, obj\) \-> str:

        return f'\{obj\.age\} an\(s\)' if obj\.age is not None else ''

    class Meta:

        model = Eleve

        fields = \['matricule', 'nom', 'prenom', 'date\_naissance', 'age', \.\.\.\]

\#\#\# Frontend JS — Calcul à la saisie \(enregistrement\)

document\.getElementById\('id\_date\_naissance'\)\.addEventListener\('change', function\(\) \{

    const dob = new Date\(this\.value\);

    if \(isNaN\(dob\)\) return;

    const today = new Date\(\);

    let age = today\.getFullYear\(\) \- dob\.getFullYear\(\);

    const m = today\.getMonth\(\) \- dob\.getMonth\(\);

    if \(m < 0 || \(m === 0 && today\.getDate\(\) < dob\.getDate\(\)\)\) age\-\-;

    document\.getElementById\('id\_age\_affiche'\)\.value = age \+ ' an\(s\)';

\}\);

\#\#\# Style du champ âge \(toujours identique\)

// Fond grisé, bordure pointillée, curseur non\-autorisé = signal visuel clair

\.input\-age\-readonly \{

    background\-color: \#F5F5F5;

    border: 1px dashed \#AAAAAA;

    cursor: not\-allowed;

    color: \#555555;

\}

\#\# RÈGLE 2 : SÉLECTION PAR MATRICULE AVEC AUTO\-REMPLISSAGE

\#\#\# Vue DRF — Endpoint autocomplete matricule

class EleveAutocompleteView\(generics\.ListAPIView\):

    """Recherche élève par matricule OU nom/prénom pour auto\-remplissage\."""

    serializer\_class = EleveAutoSerializer

    def get\_queryset\(self\):

        q = self\.request\.query\_params\.get\('q', ''\)

        return Eleve\.objects\.filter\(

            actif=True

        \)\.filter\(

            models\.Q\(matricule\_\_icontains=q\) |

            models\.Q\(nom\_\_icontains=q\) |

            models\.Q\(prenom\_\_icontains=q\)

        \)\[:20\]

\#\#\# Template HTMX — Sélection matricule à l'inscription

<\!\-\- Champ de recherche matricule \-\->

<input hx\-get='/api/eleves/autocomplete/?q='

       hx\-trigger='keyup changed delay:300ms'

       hx\-target='\#resultats\-matricule'

       hx\-swap='innerHTML'

       placeholder='Matricule ou Nom\.\.\.'>

<\!\-\- Champs auto\-remplis : TOUS readonly \+ disabled \-\->

<\!\-\- Date naissance : readonly \-\->

<\!\-\- Âge affiché : readonly, fond grisé, calculé côté backend \-\->

<\!\-\- Nom, Prénom, Sexe, Photo : readonly \-\->

<\!\-\- Seuls modifiables : Classe, Année scolaire, Statut élève \-\->

\#\# RÈGLE 3 : STATISTIQUES DE CLASSE

\# Âge dans BLOC 2 des listes de classe = calculé au 31 décembre

\# de l'année civile de fin de l'AnneeScolaire \(pas la date du jour\)

date\_ref = date\(annee\_scolaire\.date\_fin\.year, 12, 31\)

age\_eleve = date\_ref\.year \- eleve\.date\_naissance\.year

\# Ajustement si anniversaire non encore passé au 31/12

## ⭐ Skill 10 — Personnel & Vacations Expert \(NOUVEAU v2\.0\)

▌ skills/10\-personnel\-vacations\.md

\# SKILL : Personnel & Vacations Expert — YELEN SCHOOL v2\.0

\# ⭐ NOUVEAU — Règles issues du Prompt v3\.3 sections 9ter et 9bis

\#\# MODULE PERSONNEL — app Django : personnel/

\#\#\# Règle fondamentale

\# Un membre du personnel est enregistré UNE SEULE FOIS\.

\# Chaque année scolaire → InscriptionPersonnel pour être actif\.

\# Sans InscriptionPersonnel validée : ne pas apparaître dans

\# emplois du temps, présences, vacations, listes actives\.

\#\#\# Format matricule personnel — DISTINCT du matricule élève

\# PERS\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

\# ex : PERS\-YSK\-2026\-0001

\# Préfixe PERS\- toujours présent — non modifiable après création

\#\#\# Modèles clés

class MembrePersonnel\(BaseModel\):

    matricule\_personnel = models\.CharField\(max\_length=30, unique=True, editable=False\)

    nom = models\.CharField\(max\_length=100\)

    prenom = models\.CharField\(max\_length=100\)

    sexe = models\.CharField\(max\_length=1, choices=\[\('M','Masculin'\),\('F','Féminin'\)\]\)

    poste = models\.ForeignKey\('parametres\.Poste', on\_delete=models\.PROTECT\)

    actif = models\.BooleanField\(default=True\)

    \# Signal post\_save → génération matricule PERS\-

class InscriptionPersonnel\(BaseModel\):

    membre = models\.ForeignKey\(MembrePersonnel, on\_delete=models\.CASCADE\)

    annee\_scolaire = models\.ForeignKey\('parametres\.AnneeScolaire', on\_delete=models\.PROTECT\)

    poste\_occupe = models\.ForeignKey\('parametres\.Poste', on\_delete=models\.PROTECT\)

    statut = models\.CharField\(choices=\[\('validee','Validée'\),\('en\_attente','En attente'\)\]\)

    class Meta:

        unique\_together = \[\('membre', 'annee\_scolaire'\)\]

\#\#\# Liste du personnel — totaux obligatoires

\# À la fin de chaque liste : total général \+ nb femmes \+ nb hommes

\# \+ répartition par type \(enseignant / administratif / direction / technique\)

\# ventilée par genre

queryset = MembrePersonnel\.objects\.filter\(inscriptions\_\_annee\_scolaire=annee\)

total\_f = queryset\.filter\(sexe='F'\)\.count\(\)

total\_h = queryset\.filter\(sexe='M'\)\.count\(\)

\#\# MODULE VACATIONS — app Django : vacations/

\#\#\# Modèles clés

\# ProfesseurVacataire → MembrePersonnel \(lien\)

\# InscriptionVacation : \(professeur, annee\_scolaire\) — unique

\# AffectationVacation : discipline × classe × nb\_heures\_prevues\_semaine

\# HeuresRealisees     : affectation × mois → nb\_heures\_realisees

\# BilanMensuelVacation : agrège HeuresRealisees du mois

\#\#\# Règle bilan mensuel

\# Produit par la Comptabilité → validé par Directeur/Proviseur

\# Aucun paiement vacataire sans bilan validé

\# Contenu : heures prévues vs réalisées \+ écart \+ montant dû

\# ecart = nb\_heures\_realisees \- nb\_heures\_prevues\_mois

\#\#\# Intégration avec absences professeurs \(AVS\)

\# Si AbsenceProfesseur enregistrée par l'AVS pour une affectation :

\# → HeuresRealisees de ce mois décrémenté automatiquement via signal

from django\.db\.models\.signals import post\_save

@receiver\(post\_save, sender=AbsenceProfesseur\)

def deduire\_heures\_vacataire\(sender, instance, \*\*kwargs\):

    \# Vérifier si le professeur absent est un vacataire

    \# Si oui → mettre à jour HeuresRealisees du mois correspondant

    \.\.\.

\#\# STATISTIQUES LISTES CLASSES — app inscriptions/

\#\#\# BLOC 1 — Totaux filles/garçons

nb\_filles  = Inscription\.objects\.filter\(classe=cls, annee=annee, eleve\_\_sexe='F'\)\.count\(\)

nb\_garcons = Inscription\.objects\.filter\(classe=cls, annee=annee, eleve\_\_sexe='M'\)\.count\(\)

\#\#\# BLOC 2 — Tableau âges par genre \(âge au 31/12 de l'année de fin\)

from django\.db\.models import Count

date\_ref = date\(annee\.date\_fin\.year, 12, 31\)

\# Annotation age sur chaque élève puis regroupement \(age, sexe\)

\#\#\# BLOC 3 — Redoublants/non\-redoublants par genre

redoublants\_f = Inscription\.objects\.filter\(

    classe=cls, annee=annee, decision\_passage='redoublant', eleve\_\_sexe='F'\)\.count\(\)

\# Même logique pour garçons et non\-redoublants

# PARTIE 4 — WORKFLOWS SPRINT PAR SPRINT \(mis à jour v2\.0\)

## 4\.1 Phase 0 — Setup Architecture \(Sem\. 1\-2\)

🎯 Livrable : Repo GitHub \+ Docker dev opérationnel \+ structure Django 13 apps

Durée : 2 semaines | Agents : architect → coder → reviewer

__📋 Workflow Phase 0 — Création 13 apps__

Mode : Build | Agent : coder

/01\-django\-models

/05\-docker\-devops

Lis docs/PROMPT\_V3\_3\.md section Architecture\.

Crée la structure complète du projet YELEN SCHOOL avec les 13 apps :

core, accounts, licences, etablissements, parametres,

inscriptions, personnel, pedagogie, bulletins, presences,

vacations, examens, finances, documents

Pour chaque app, crée les fichiers : models\.py, views\.py, urls\.py,

admin\.py, apps\.py, tests/\_\_init\_\_\.py

Crée aussi core/models\.py avec BaseModel \(created\_at, updated\_at, abstract\)\.

## 4\.2 Phase 1 — Module Licences \(Sem\. 3\-4\)

🎯 Livrable : Module licences complet \+ Feature Flags v3\.3 | Durée : 2 semaines

__📋 Workflow Phase 1 — Module Licences__

Mode : Plan | Agent : architect

/07\-licence\-system

/08\-burkina\-context

Lis docs/PROMPT\_V3\_3\.md section 3 \(Module Licences\)\.

Planifie l'implémentation du module licences/ :

\- Modèles : Licence, LicenceActivation, LicenceAuditLog, LicenceAlert

\- Décorateur : @requires\_licence\_feature

\- ⭐ Feature Flags v3\.3 à ajouter : enregistrement\_eleves, carte\_identite\_scolaire,

  gestion\_personnel, vacations, statistiques\_listes

\- Tests coverage > 90%

## 4\.3 Phase 2 — MVP Core \(Sem\. 5\-8\) — MIS À JOUR v2\.0

🎯 Livrable : Paramètres \+ Enregistrement élèves \+ Inscription par matricule \+

              Personnel \+ AVS \+ Vacations \+ Notes \+ Bulletins MENA \+ Présences

Durée : 4 semaines \(sprints 3\-4\) | Agents : architect \+ coder \+ designer en parallèle

⭐ MISE À JOUR v2\.0 : 3 nouveaux sprints vs le guide v1\.0

__📋 Sprint 3 — Paramètres & Enregistrement__

\# ─── Sprint 3, Sem\. 5\-6 : Paramètres \+ Enregistrement ──────────────

\# AGENT 1 — Backend Paramètres

Mode : Build | Agent : coder

/01\-django\-models

/08\-burkina\-context

Lis docs/PROMPT\_V3\_3\.md section 4 \(Module Paramètres\)\.

Implémente parametres/models\.py avec les 12 modèles :

IdentiteEtablissement, Cycle, Classe, Poste, LocalisationPoste,

StatutEleve, RubriquePaiement, TarifScolarite,

AppreciationConduite, AnneeScolaire, Discipline, PeriodeEvaluation

\# AGENT 2 — Backend Enregistrement Élèves

Mode : Build | Agent : coder

/01\-django\-models

/09\-age\-matricule\-frontend

Lis docs/PROMPT\_V3\_3\.md section 5 \(Enregistrement Élèves\)\.

Implémente inscriptions/models\.py — modèle Eleve avec :

\- matricule BF\-\{REGION\}\-\{ANNEE\}\-\{SEQ:04d\} \(signal post\_save\)

\- actif \(BooleanField, True par défaut\)

\- exonere \(BooleanField, False par défaut\)

\- @property age \(JAMAIS stocker en base\)

\- photo \(ImageField MinIO\)

__📋 Sprint 3 — Frontend Enregistrement \+ calcul âge__

\# ─── Sprint 3, Sem\. 5\-6 \(suite\) : Frontend Enregistrement ──────────

Mode : Build | Agent : designer

/03\-htmx\-frontend

/09\-age\-matricule\-frontend

Lis docs/DESIGN\_SYSTEM\.md\.

Crée templates/inscriptions/enregistrement\_eleve\.html :

\- Formulaire 4 étapes \(onglets\)

\- Étape 1 : champ date\_naissance \+ champ AGE en lecture seule \(fond grisé\)

  Le champ âge se calcule automatiquement dès saisie date\_naissance

  \(pattern du Skill 09 : calcul JS onChange\)

\- Cases à cocher : ☑ Actif \(default\) | ☐ Exonéré

\- Upload photo obligatoire

Utilise uniquement les classes de static/css/yelen\.css\.

__📋 Sprint 4 — Personnel \+ Inscription par matricule__

\# ─── Sprint 4, Sem\. 7\-8 : Personnel \+ Inscription par matricule ─────

\# AGENT 1 — Module Personnel

Mode : Build | Agent : coder

/01\-django\-models

/10\-personnel\-vacations

Lis docs/PROMPT\_V3\_3\.md section 9ter \(Gestion du Personnel\)\.

Implémente personnel/models\.py :

\- MembrePersonnel avec matricule PERS\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

  Signal post\_save pour génération matricule PERS\-

\- InscriptionPersonnel \(unique\_together: membre \+ annee\_scolaire\)

Implémente les vues CRUD \+ vue liste personnel avec totaux H/F\.

\# AGENT 2 — Inscription par matricule avec auto\-remplissage

Mode : Build | Agent : coder

/02\-django\-views

/09\-age\-matricule\-frontend

Lis docs/PROMPT\_V3\_3\.md section 6 \(Inscription/Réinscription\)\.

Implémente inscriptions/views\.py :

\- Endpoint API : GET /api/eleves/autocomplete/?q= \(matricule \+ nom/prénom\)

\- Vue inscription : sélection matricule → auto\-remplissage

  Champs auto\-remplis : nom, prénom, date\_naissance, âge \(calculé\)

  Seuls modifiables : classe, année scolaire, statut élève

\- Modèle Inscription avec signal pour calcul auto frais \(TarifScolarite\)

__📋 Sprint 4 — Vacations \+ Agent de Vie Scolaire__

\# ─── Sprint 4 \(suite\) : Vacations \+ AVS ────────────────────────────

Mode : Build | Agent : coder

/01\-django\-models

/10\-personnel\-vacations

Lis docs/PROMPT\_V3\_3\.md section 9bis \(Gestion des Vacations\)\.

Implémente vacations/models\.py :

\- InscriptionVacation \(unique: professeur \+ annee\_scolaire\)

\- AffectationVacation \(discipline × classe × nb\_heures\_prevues\_semaine\)

\- HeuresRealisees \(unique: affectation \+ mois\)

\- BilanMensuelVacation avec statut \(en\_preparation/soumis/valide\)

Implémente le signal de déduction automatique :

\- Si AbsenceProfesseur créée pour un vacataire

  → déduire les heures de HeuresRealisees du mois

Lis docs/PROMPT\_V3\_3\.md section 7 \(AVS\)\.

Implémente presences/models\.py :

\- AbsenceEleve \+ AbsenceProfesseur \+ SanctionDisciplinaire

\- Tableau de bord AVS : vue du jour, file justificatifs

## 4\.4 Phase 3 — Module Documents \(Sem\. 9\-10\) — MIS À JOUR v2\.0

🎯 Livrable : 5 documents administratifs \+ carte d'identité scolaire

Certificat · Attestation · Cursus · Autorisation · ⭐ Carte d'Identité Scolaire

⭐ MISE À JOUR v2\.0 : ajout de la Carte d'Identité Scolaire \+ Bilan Vacations \+ Liste Personnel

Durée : 2 semaines \(sprint 5\)

__📋 Phase 3 — Architecture Documents__

Mode : Plan | Agent : architect

/04\-pdf\-generator

/07\-licence\-system

Lis docs/PROMPT\_V3\_3\.md section 8 \(Module Documents\)\.

⭐ Planifie l'implémentation de 8 générateurs PDF \(v3\.3\) :

1\. CertificatScolariteGenerator

2\. AttestationNonRedevabiliteGenerator

3\. CursusScolaireGenerator

4\. AutorisationAbsenceGenerator

5\. ⭐ CarteIdentiteScolaireGenerator \(format 85x54mm, 8/page A4 paysage\)

6\. ⭐ BilanVacationGenerator

7\. ⭐ ListePersonnelGenerator \(avec totaux H/F en pied de liste\)

8\. ⭐ ListeClasseStatistiquesGenerator \(BLOC 1 \+ BLOC 2 âges \+ BLOC 3 redoublants\)

__📋 Sprint 5 — Carte d'Identité Scolaire__

\# ─── Sprint 5, Jours 2\-4 : Carte d'Identité Scolaire ──────────────

Mode : Build | Agent : coder

/04\-pdf\-generator

/08\-burkina\-context

Lis docs/PROMPT\_V3\_3\.md section 8\.5 \(Carte d'Identité Scolaire\)\.

Implémente documents/generators/carte\_identite\.py :

\- Numérotation : CARTE\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}

\- Génération PAR CLASSE \(lot\_impression\)

\- Format HTML : grille CSS 4×2 = 8 cartes par page A4 paysage

\- Dimensions carte : 85mm × 54mm \(standard carte bancaire\)

\- Séparateurs pointillés pour découpe

\- Recto : logo, nom étab, photo élève, nom, date naissance, matricule, classe

\- Verso : QR Code authenticité, règlement intérieur résumé, signature directeur

\- Vérifie photo obligatoire avant génération \(blocage si absente\)

Mode : Build | Agent : designer

/04\-pdf\-generator

Crée templates/documents/carte\_identite\_scolaire\.html :

@page \{ size: A4 landscape; margin: 5mm; \}

\.grille\-cartes \{ display: grid; grid\-template\-columns: repeat\(4, 85mm\); gap: 2mm; \}

\.carte \{ width: 85mm; height: 54mm; border: 1px dashed \#aaa; font\-family: DejaVu Sans; \}

__📋 Sprint 5 — Statistiques listes \+ PDF__

\# ─── Sprint 5, Jours 5\-7 : Statistiques listes classes ────────────

Mode : Build | Agent : coder

/10\-personnel\-vacations

/08\-burkina\-context

Lis docs/PROMPT\_V3\_3\.md section 9quater \(Statistiques listes classes\)\.

Implémente inscriptions/services/statistiques\_classe\.py :

def get\_stats\_classe\(classe, annee\_scolaire\) \-> dict:

    \# BLOC 1 : totaux filles/garçons

    \# BLOC 2 : tableau âges par genre \(âge au 31/12 de l'année de fin\)

    \# BLOC 3 : redoublants/non\-redoublants par genre

    \# Utiliser Eleve\.date\_naissance — jamais un champ age stocké

Intègre les 3 blocs dans le template HTML liste\_classe\.html :

\- Les blocs apparaissent à la FIN de chaque liste de classe

\- Ils sont inclus dans TOUTES les impressions PDF de liste de classe

\- BLOC 2 : ne pas afficher les lignes d'âge avec 0 élève

\- Le total BLOC 3 doit correspondre au total BLOC 1

## 4\.5 Phase 4 — Finances \(Sem\. 11\-12\)

🎯 Livrable : Frais scolaires \(matrice TarifScolarite\) \+ Paiements \+ Reçus PDF \+ Bilan Vacations

Durée : 2 semaines \(sprint 6\)

__📋 Phase 4 — Finances \+ Paiements Vacataires__

Mode : Build | Agent : coder

/01\-django\-models

/08\-burkina\-context

Lis docs/PROMPT\_V3\_3\.md section 9\.3 \(Finances\) et section 9bis\.2 \(Bilan Vacations\)\.

Implémente finances/models\.py avec :

\- Paiement lié à Inscription et TarifScolarite

\- Calcul automatique frais selon matrice \(classe × statut\_eleve × rubrique\)

\- Exonéré = True → frais = 0 FCFA automatiquement

\- Reçu PDF \(ReçuGenerator\) numéroté

Implémente le module de paiement des vacataires :

\- Lien BilanMensuelVacation validé → ordre de paiement

\- Calcul : heures\_realisees × tarif\_horaire\_applicable

\- Aucun paiement sans bilan validé par le Directeur/Proviseur

# RÉCAPITULATIF — Commandes Antigravity à retenir

__Commande__

__Effet__

__Quand l'utiliser__

/skill\-name

Charge le skill en contexte

Avant chaque tâche spécialisée

/09\-age\-matricule

Règles âge calculé \+ matricule auto

Avant tout écran enregistrement/inscription

/10\-personnel\-vacations

Règles Personnel \+ Vacations

Avant tout module Personnel ou Vacations

@fichier\.py

Référence un fichier du projet

Pour cohérence avec l'existant

Tab

Bascule Plan ↔ Build

Avant de coder \(Plan\), pour coder \(Build\)

Ctrl\+Enter

Envoie le prompt

Après avoir rédigé ton prompt

Ouvre 2 onglets agents

Agents en parallèle

Backend \+ Frontend simultanément

# ANNEXES — Fichiers complémentaires

## Annexe A — conftest\.py \(mis à jour v2\.0\)

▌ tests/conftest\.py — ⭐ MIS À JOUR v2\.0

\# tests/conftest\.py — Configuration globale pytest YELEN SCHOOL v2\.0

import pytest

from django\.test import Client

from model\_bakery import baker

from datetime import date

@pytest\.fixture

def client\(\):

    return Client\(\)

@pytest\.fixture

def directeur\_proviseur\(db\):

    """Crée un utilisateur Directeur/Proviseur pour les tests\."""

    user = baker\.make\('accounts\.User', role='directeur\_proviseur'\)

    baker\.make\('licences\.Licence', etablissement\_\_directeur=user,

               type\_licence='premium', statut='active'\)

    return user

@pytest\.fixture

def annee\_scolaire\(db\):

    from parametres\.models import AnneeScolaire

    return baker\.make\(AnneeScolaire, libelle='2025\-2026', est\_courante=True\)

@pytest\.fixture

def eleve\_actif\(db\):

    """Crée un élève actif avec dossier complet\."""

    eleve = baker\.make\('inscriptions\.Eleve',

                       actif=True,

                       exonere=False,

                       date\_naissance=date\(2013, 5, 15\)\)

    \# Vérifie que le matricule BF\- a bien été généré

    assert eleve\.matricule\.startswith\('BF\-'\)

    \# Vérifie que l'âge est calculé \(non stocké\)

    assert eleve\.age is not None

    assert isinstance\(eleve\.age, int\)

    return eleve

@pytest\.fixture

def membre\_personnel\(db, annee\_scolaire\):

    """Crée un membre du personnel avec matricule PERS\-\."""

    membre = baker\.make\('personnel\.MembrePersonnel',

                        actif=True, sexe='M'\)

    \# Vérifie que le matricule PERS\- a été généré

    assert membre\.matricule\_personnel\.startswith\('PERS\-'\)

    \# Crée l'inscription annuelle

    baker\.make\('personnel\.InscriptionPersonnel',

               membre=membre, annee\_scolaire=annee\_scolaire,

               statut='validee'\)

    return membre

@pytest\.fixture

def eleve\_sans\_dettes\(db, eleve\_actif\):

    """Élève sans dettes financières\."""

    baker\.make\('finances\.Paiement', eleve=eleve\_actif, montant\_solde=0\)

    return eleve\_actif

## Annexe B — pytest\.ini \(inchangé\)

▌ pytest\.ini

\[pytest\]

DJANGO\_SETTINGS\_MODULE = yelen\_school\.settings\.test

python\_files = test\_\*\.py

python\_classes = Test\*

python\_functions = test\_\*

addopts =

    \-\-strict\-markers

    \-\-tb=short

    \-\-cov=\.

    \-\-cov\-report=html:htmlcov

    \-\-cov\-fail\-under=80

markers =

    slow: Tests lents \(génération PDF, etc\.\)

    integration: Tests d'intégration multi\-modules

    licence: Tests du module licences

    matricule: Tests de génération matricules BF\- et PERS\-

    age\_calcule: Tests du calcul dynamique de l'âge

## Annexe C — Checklist de démarrage rapide

__Étape__

__Action / Commande__

1\. Prérequis

Python 3\.11 \+ Git \+ Docker \+ Node\.js installés

2\. Antigravity

Installé, connecté Gmail, extension Claude ajoutée

3\. Règles Globales

Copiées dans Antigravity → Customizations → Global Rules

4\. Dossier projet

mkdir yelen\-school && cd yelen\-school

5\. docs/

PROMPT\_V3\_3\.md \+ DESIGN\_SYSTEM\.md copiés dans docs/

6\. config\.json

\.antigravity/config\.json créé \(réf\. PROMPT\_V3\_3\)

7\. 13 apps Django

python manage\.py startapp \[nom\] × 13 \(dont parametres, personnel, vacations\)

8\. Docker

docker\-compose \-f docker\-compose\.dev\.yml up \-d

9\. 10 Skills

skills/ créé avec les 10 fichiers \.md

10\. Premier prompt

/08\-burkina\-context \+ /01\-django\-models → core/models\.py BaseModel

*YELEN SCHOOL — Guide Développeur v2\.0 — © 2026 — Tous droits réservés*

__"Illuminer chaque parcours scolaire"__

