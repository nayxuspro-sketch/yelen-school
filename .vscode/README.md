# Configuration VSCode — YELEN SCHOOL

Configuration globale VSCode optimisée pour le projet **Yelen School**, une application de gestion scolaire pour le Burkina Faso.

---

## 📋 Table des Matières

1. [Stack Technique](#-stack-technique)
2. [Installation](#-installation)
3. [Extensions Obligatoires](#-extensions-obligatoires)
4. [Fichiers de Configuration](#-fichiers-de-configuration)
5. [Raccourcis Clavier](#-raccourcis-clavier)
6. [Snippets Disponibles](#-snippets-disponibles)
7. [Tâches Automatisées](#-tâches-automatisées)
8. [Debug](#-debug)
9. [Règles de Code](#-règles-de-code)

---

## 🛠 Stack Technique

- **Backend** : Django 4.2 LTS + Django REST Framework
- **Frontend** : HTMX + Alpine.js + Tailwind CSS
- **BDD** : PostgreSQL 15
- **Cache** : Redis 7
- **PDF** : WeasyPrint 60+
- **Async** : Celery + Redis
- **Conteneurisation** : Docker + Docker Compose
- **Stockage** : MinIO (self-hosted)

---

## 📥 Installation

### 1. Copier les fichiers de configuration

```bash
# Créer le dossier .vscode à la racine du projet
mkdir -p .vscode

# Copier tous les fichiers de configuration
cp /path/to/config/.vscode/* .vscode/
```

### 2. Installer les extensions

Ouvrir VSCode et exécuter :

```
Cmd/Ctrl + Shift + P → "Extensions: Show Recommended Extensions"
```

Cliquer sur "Install All" pour installer toutes les extensions recommandées.

**Ou installer manuellement** :

```bash
# Extensions Python & Django
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension batisteo.vscode-django
code --install-extension ms-python.black-formatter

# Extensions Frontend
code --install-extension bradlc.vscode-tailwindcss
code --install-extension otovo-oss.htmx-tags
code --install-extension adrianwilczynski.alpine-js-intellisense

# Extensions Docker
code --install-extension ms-azuretools.vscode-docker

# Extensions Base de données
code --install-extension mtxr.sqltools
code --install-extension mtxr.sqltools-driver-pg

# Extensions Git
code --install-extension eamodio.gitlens
code --install-extension mhutchie.git-graph

# Thème recommandé
code --install-extension zhuangtongfa.material-theme
code --install-extension pkief.material-icon-theme
```

### 3. Configurer l'environnement Python

```bash
# Créer l'environnement virtuel
python -m venv .venv

# Activer l'environnement
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 4. Redémarrer VSCode

```
Cmd/Ctrl + Shift + P → "Developer: Reload Window"
```

---

## 🔌 Extensions Obligatoires

### Python & Django

| Extension | Description |
|-----------|-------------|
| `ms-python.python` | Support Python officiel |
| `ms-python.vscode-pylance` | IntelliSense ultra-rapide |
| `batisteo.vscode-django` | Support Django templates |
| `ms-python.black-formatter` | Formatage Black |
| `ms-python.flake8` | Linting Flake8 |

### Frontend

| Extension | Description |
|-----------|-------------|
| `bradlc.vscode-tailwindcss` | Autocomplete Tailwind CSS |
| `otovo-oss.htmx-tags` | Support HTMX |
| `adrianwilczynski.alpine-js-intellisense` | IntelliSense Alpine.js |

### Infrastructure

| Extension | Description |
|-----------|-------------|
| `ms-azuretools.vscode-docker` | Support Docker |
| `mtxr.sqltools` | Client SQL |
| `eamodio.gitlens` | GitLens |

---

## 📁 Fichiers de Configuration

```
.vscode/
├── settings.json              # Configuration globale VSCode
├── extensions.json            # Extensions recommandées
├── tasks.json                 # Tâches automatisées
├── launch.json                # Configurations debug
├── python.code-snippets       # Snippets Python/Django
└── django-html.code-snippets  # Snippets HTML/HTMX/Alpine
```

---

## ⌨️ Raccourcis Clavier

### Tâches Docker

| Raccourci | Action |
|-----------|--------|
| `Cmd/Ctrl + Shift + B` | Build & Start tous les services |
| `Cmd/Ctrl + Shift + P → Tasks: Run Task → Docker: View Logs` | Voir les logs |

### Django

| Raccourci | Action |
|-----------|--------|
| `Cmd/Ctrl + Shift + P → Tasks: Run Task → Django: Make & Migrate` | Migrations |
| `Cmd/Ctrl + Shift + P → Tasks: Run Task → Django: Python Shell` | Shell Python |

### Tests

| Raccourci | Action |
|-----------|--------|
| `Cmd/Ctrl + Shift + P → Tasks: Run Task → Tests: With Coverage` | Tests avec coverage |
| `F5` | Lancer le debugger |

### Formatage

| Raccourci | Action |
|-----------|--------|
| `Shift + Alt + F` | Formater le fichier (Black pour Python) |
| `Cmd/Ctrl + S` | Sauvegarder et formater automatiquement |

---

## 🎯 Snippets Disponibles

### Python/Django

| Préfixe | Description |
|---------|-------------|
| `yelen-model` | Modèle Django complet |
| `yelen-listview` | ListView Django |
| `yelen-createview` | CreateView Django |
| `yelen-form` | ModelForm Django |
| `yelen-test` | Classe de tests pytest |
| `yelen-def` | Fonction avec type hints |
| `yelen-signal-save` | Signal post_save |
| `yelen-pdf` | Génération PDF WeasyPrint |
| `yelen-htmx` | Vue partielle HTMX |
| `yelen-qs` | Queryset optimisé |

### HTML/Templates

| Préfixe | Description |
|---------|-------------|
| `yelen-base` | Template de base |
| `yelen-card` | Carte Design System |
| `yelen-btn-primary` | Bouton primaire |
| `yelen-badge` | Badge |
| `yelen-input` | Champ de formulaire |
| `yelen-table` | Tableau de données |
| `yelen-htmx-form` | Formulaire HTMX |
| `yelen-htmx-delete` | Bouton suppression HTMX |
| `yelen-alpine` | Composant Alpine.js |
| `yelen-alpine-modal` | Modal Alpine.js |
| `yelen-multistep` | Formulaire multi-étapes |
| `yelen-age` | Calcul âge dynamique |

**Utilisation** :

1. Taper le préfixe (ex: `yelen-model`)
2. Appuyer sur `Tab` ou `Enter`
3. Naviguer entre les champs avec `Tab`

---

## ⚙️ Tâches Automatisées

### Lancer une tâche

```
Cmd/Ctrl + Shift + P → Tasks: Run Task → [Nom de la tâche]
```

### Tâches principales

#### Docker

- `🐳 Docker: Build & Start All` — Build et démarrer tous les services
- `🐳 Docker: Start All Services` — Démarrer les services
- `🐳 Docker: Stop All Services` — Arrêter les services
- `🐳 Docker: Restart Django` — Redémarrer Django uniquement
- `🐳 Docker: View Logs` — Voir les logs en temps réel

#### Django

- `🚀 Django: Run Server` — Démarrer le serveur Django
- `📦 Django: Make Migrations` — Créer les migrations
- `📦 Django: Migrate` — Appliquer les migrations
- `👤 Django: Create Superuser` — Créer un superuser
- `🐚 Django: Python Shell` — Ouvrir le shell Python
- `🎨 Django: Collect Static` — Collecter les fichiers statiques

#### Tests

- `🧪 Tests: Run All (pytest)` — Lancer tous les tests
- `📊 Tests: With Coverage` — Tests avec rapport coverage
- `⚡ Tests: Failed Only` — Relancer uniquement les tests échoués
- `🔍 Lint: Flake8` — Vérification Flake8
- `🎨 Format: Black Apply` — Formater avec Black

#### Base de données

- `🗄️ DB: Backup` — Sauvegarder la base
- `🗄️ DB: Load Fixtures` — Charger les fixtures

---

## 🐛 Debug

### Configurations disponibles

| Configuration | Description |
|--------------|-------------|
| `🚀 Django: Debug Server` | Debugger le serveur Django |
| `🧪 Pytest: Debug Current File` | Debugger le fichier de test actuel |
| `🧪 Pytest: Debug All Tests` | Debugger tous les tests |
| `🎯 Django: Debug Command` | Debugger une commande Django |
| `📄 Debug: Bulletin MENA` | Debugger génération bulletin |

### Lancer le debug

1. Ouvrir le fichier à debugger
2. Placer des breakpoints (clic sur la marge gauche)
3. Appuyer sur `F5` ou aller dans l'onglet Debug
4. Sélectionner la configuration
5. Cliquer sur le bouton Play vert

### Raccourcis Debug

| Raccourci | Action |
|-----------|--------|
| `F5` | Démarrer/Continuer |
| `F9` | Toggle breakpoint |
| `F10` | Step over |
| `F11` | Step into |
| `Shift + F11` | Step out |
| `Shift + F5` | Stop debugging |

---

## 📏 Règles de Code

### Python (NON NÉGOCIABLES)

✅ **OBLIGATOIRE** :

- Type hints sur toutes les fonctions
- Docstrings sur toutes les classes Django
- Commentaires en français
- Tests unitaires (coverage > 80%)
- Black pour le formatage (ligne max 120)
- Flake8 pour le linting
- Aucune dépendance payante

❌ **INTERDIT** :

- SQLite en développement (PostgreSQL obligatoire)
- Dépendances non open-source
- Code sans tests
- Coverage < 80%

### Frontend

✅ **OBLIGATOIRE** :

- Toujours lire `docs/DESIGN_SYSTEM.md` avant HTML/CSS
- Classes Tailwind CSS uniquement (pas de CSS custom)
- HTMX pour les interactions
- Alpine.js pour l'interactivité légère

❌ **INTERDIT** :

- jQuery ou autres librairies JS lourdes
- CSS custom (utiliser Tailwind)
- Framework frontend lourd (React, Vue)

### Base de données

✅ **OBLIGATOIRE** :

- PostgreSQL 15 en développement et production
- Migrations testées avant commit
- Indexes sur les clés étrangères
- Contraintes de base de données

❌ **INTERDIT** :

- SQLite (même en dev)
- Requêtes N+1 (utiliser `select_related` et `prefetch_related`)

---

## 🔧 Résolution de Problèmes

### L'environnement Python n'est pas détecté

```bash
# Vérifier que .venv existe
ls -la .venv/

# Si absent, le créer
python -m venv .venv

# Redémarrer VSCode
Cmd/Ctrl + Shift + P → Developer: Reload Window
```

### Les imports Django ne sont pas reconnus

1. Vérifier que l'environnement virtuel est activé
2. Vérifier `python.defaultInterpreterPath` dans settings.json
3. Installer Django : `pip install django`
4. Redémarrer Pylance : `Cmd/Ctrl + Shift + P → Python: Restart Language Server`

### Tailwind CSS autocomplete ne fonctionne pas

1. Vérifier que l'extension `bradlc.vscode-tailwindcss` est installée
2. S'assurer que le fichier est reconnu comme HTML ou Django HTML
3. Vérifier `files.associations` dans settings.json

### Les tests pytest ne se lancent pas

```bash
# Installer pytest et dépendances
pip install pytest pytest-django pytest-cov

# Vérifier la configuration
cat pytest.ini

# Lancer manuellement
pytest -v
```

---

## 📚 Ressources

- [Documentation Django](https://docs.djangoproject.com/)
- [Documentation HTMX](https://htmx.org/)
- [Documentation Alpine.js](https://alpinejs.dev/)
- [Documentation Tailwind CSS](https://tailwindcss.com/)
- [Design System Yelen](../docs/DESIGN_SYSTEM.md)
- [Guide Développeur Yelen](../docs/YELEN_SCHOOL_Guide_Complet_Developpeur.docx)

---

## 🆘 Support

En cas de problème avec la configuration VSCode :

1. Vérifier les logs : `Cmd/Ctrl + Shift + P → Developer: Toggle Developer Tools`
2. Redémarrer VSCode : `Cmd/Ctrl + Shift + P → Developer: Reload Window`
3. Réinitialiser la configuration : supprimer `.vscode/` et réinstaller

---

**Version** : 1.0  
**Dernière mise à jour** : Mars 2026  
**Projet** : YELEN SCHOOL — Gestion Scolaire pour le Burkina Faso
