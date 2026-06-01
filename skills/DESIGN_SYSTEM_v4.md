# DESIGN SYSTEM — YELEN SCHOOL v4.0
> Source de vérité visuelle · Réf. Prompt v4.0 · Mars 2026  
> **Règle absolue : tout template HTML doit être conforme à ce document.**

---

## 0. PHILOSOPHIE DESIGN

YELEN SCHOOL est une application de gestion scolaire au Burkina Faso.
Son interface doit inspirer **confiance, sérieux et modernité** tout en restant
accessible sur des connexions lentes et des écrans variés.

- **Dark mode permanent** — fond profond `#06101E`, jamais de fond blanc
- **Minimalisme premium** — chaque détail est intentionnel et raffiné
- **Cohérence absolue** — les mêmes composants partout, jamais de CSS inline
- **Performance** — animations légères, pas de librairies inutiles
- **Accessibilité** — contrastes suffisants, tailles de police lisibles

> ⭐ **v4.0** : Refonte premium — fond plus profond, sidebar avec indicateur actif lumineux,
> stat-cards avec accent coloré ambiant, badges cristal, topbar glassmorphe, ombres élevées.
> ✈️ **v4.0** : Conformité hors ligne complète — polices auto-hébergées, zéro CDN externe.

---

## 0.1 CONTRAINTES MODE HORS LIGNE ✈️

> **L'application YELEN SCHOOL fonctionne sans connexion internet.**
> Toute ressource externe est **strictement interdite** dans les templates et le CSS.

### Ce qui est INTERDIT

| Ressource externe | Interdit car… | Alternative obligatoire |
|---|---|---|
| `fonts.googleapis.com` | Requête HTTP bloquée hors ligne | Polices `.woff2` dans `static/fonts/` via `@font-face` |
| CDN JS/CSS (`cdnjs`, `unpkg`, `jsdelivr`, `esm.sh`) | Inaccessible sans réseau | Copie locale dans `static/js/` ou `static/css/` |
| `<img src="https://...">` | Image externe indisponible | Images dans `static/img/` ou encodées base64 |
| APIs externes (météo, maps, analytics…) | Pas de réseau | Ne pas intégrer |
| `backdrop-filter: blur()` | Lourd sur ancien matériel BF | Usage avec parcimonie — tester sur poste cible |

### Ce qui est AUTORISÉ

- **Django staticfiles** : `{% static "..." %}` pour toutes les ressources
- **HTMX** : copie locale dans `static/js/htmx.min.js`
- **CSS pur** avec variables CSS — zéro dépendance JS tierce pour les styles
- **Animations CSS** uniquement (`@keyframes`, `transition`)
- **WeasyPrint** pour PDF serveur — `DejaVu Sans` fourni nativement
- **SQLite / PostgreSQL local** pour toutes les données

### Préparer les polices (une seule fois, avec connexion)

```bash
mkdir -p static/fonts
# 1. Télécharger les ZIP depuis Google Fonts :
#    https://fonts.google.com/specimen/Outfit
#    https://fonts.google.com/specimen/Playfair+Display
# 2. Extraire et convertir en .woff2 :
pip install fonttools brotli
python -c "from fontTools.ttLib.woff2 import compress; compress('Outfit-Regular.ttf', 'static/fonts/Outfit-Regular.woff2')"
# Répéter pour chaque graisse (300, 400, 500, 600, 700) et pour PlayfairDisplay-Bold
```

---

## 1. TOKENS DE COULEUR

```css
/* ─── Fonds ──────────────────────────────────────────── */
--color-bg-app:        #06101E;   /* Fond global — plus profond (ex #0A1628) */
--color-bg-sidebar:    linear-gradient(180deg, #0B1727 0%, #081220 100%); /* Sidebar dégradé */
--color-bg-card:       #0D1A2D;   /* Surface des cartes et panneaux */
--color-bg-input:      #080F1C;   /* Fond des champs de saisie */
--color-bg-hover:      #12223A;   /* Survol sur éléments interactifs */
--color-bg-selected:   #172845;   /* Élément sélectionné / actif */
--color-bg-overlay:    rgba(0,0,0,0.60);  /* Modales / overlays */
--color-bg-topbar:     linear-gradient(180deg, rgba(13,26,45,0.98) 0%, rgba(8,12,22,0.95) 100%);

/* ─── Bordures ────────────────────────────────────────── */
--color-border:        rgba(255,255,255,0.07);  /* Bordure standard (ex 0.06) */
--color-border-focus:  rgba(0,168,107,0.60);    /* Bordure focus (vert) */
--color-border-error:  rgba(220,53,69,0.70);    /* Bordure erreur */
--color-border-active: rgba(0,168,107,0.22);    /* Bordure item actif sidebar */

/* ─── Palette principale ──────────────────────────────── */
--color-primary:       #00A86B;   /* Vert principal — actions, succès */
--color-primary-dark:  #007A4D;   /* Vert foncé — hover bouton */
--color-primary-light: #00C07A;   /* Vert clair — texte sur fond sombre */
--color-primary-glow:  rgba(0,168,107,0.35);   /* Halo vert boutons */
--color-primary-ambient: rgba(0,168,107,0.18); /* Fond doux item actif */

--color-gold:          #F5A623;   /* Or — avertissements, highlights */
--color-gold-dark:     #C27D00;   /* Or foncé */

--color-danger:        #DC3545;   /* Rouge — erreurs, suppressions */
--color-info:          #17A2B8;   /* Bleu info */
--color-purple:        #A259FF;   /* Violet — rôles techniques */

/* ─── Texte ────────────────────────────────────────────── */
--color-text-primary:  #E8EDF5;   /* Texte principal */
--color-text-secondary:#8CA5C0;   /* Texte secondaire / libellés (ex #9AAEC4) */
--color-text-muted:    #4A6880;   /* Texte atténué / placeholders (ex #5A7A9A) */
--color-text-inverse:  #06101E;   /* Texte sur fond clair (badges) */

/* ─── Ombres premium ──────────────────────────────────── */
--shadow-card:         0 2px 20px rgba(0,0,0,0.40);   /* Ombre carte standard */
--shadow-card-hover:   0 12px 32px rgba(0,0,0,0.50);  /* Ombre carte au survol */
--shadow-sidebar:      4px 0 32px rgba(0,0,0,0.35);   /* Ombre sidebar */
--shadow-topbar:       0 1px 32px rgba(0,0,0,0.25);   /* Ombre topbar */
--shadow-btn-primary:  0 4px 16px rgba(0,168,107,0.35); /* Ombre bouton vert */
--shadow-btn-hover:    0 6px 20px rgba(0,168,107,0.45); /* Ombre bouton vert hover */
--glow-primary:        0 0 20px rgba(0,168,107,0.30); /* Lueur verte (badges, dots) */
--glow-active-bar:     0 0 8px #00A86B;               /* Lueur barre indicateur actif */

/* ─── Notes scolaires (BF) ────────────────────────────── */
--color-note-excellent: #00C07A;  /* >= 16/20 — vert clair */
--color-note-bien:      #F5A623;  /* >= 12/20 — or */
--color-note-insuffisant:#FF6B7A; /* < 12/20  — rouge clair */
```

---

## 2. TYPOGRAPHIE

> ✈️ **Mode hors ligne — polices 100% système, zéro téléchargement.**
> Aucun `@font-face`, aucun `@import` CDN. Les polices ci-dessous sont **déjà installées**
> sur Windows (postes BF), Linux et macOS — elles fonctionnent immédiatement sans rien copier.

### 2.0 Stratégie polices hors ligne

| Rôle | Police choisie | Disponible sur |
|------|---------------|----------------|
| Interface (toute l'UI) | `Segoe UI` | Windows Vista+ (tous les postes BF Windows) |
| Interface fallback | `Ubuntu` | Ubuntu Linux (serveur / postes Linux) |
| Interface fallback final | `system-ui` | Tout OS moderne |
| Logo YELEN SCHOOL | `Playfair Display` (auto-hébergée) | À copier depuis le ZIP téléchargé |
| Logo fallback | `Georgia` | Windows / macOS / Linux natif |
| Matricules & codes | `Consolas` | Windows Vista+ |
| Mono fallback | `DejaVu Sans Mono` | Linux / WeasyPrint natif |

### 2.1 Playfair Display — seule police à auto-héberger

Playfair Display est **uniquement** pour le logo YELEN SCHOOL (un seul endroit).
Tu l'as déjà téléchargée — voici comment la préparer :

```bash
# Convertir le fichier variable en woff2 (une seule fois, avec connexion)
pip install fonttools brotli
python -c "
from fontTools.ttLib.woff2 import compress
compress('PlayfairDisplay-VariableFont_wght.ttf', 'PlayfairDisplay-Bold.woff2')
"
# Copier dans le projet :
# static/fonts/PlayfairDisplay-Bold.woff2
```

Déclarer dans le CSS global (`base.css`) :

```css
/* ─── Playfair Display — logo YELEN uniquement ────────── */
@font-face {
  font-family: 'Playfair Display';
  src: url('{% static "fonts/PlayfairDisplay.woff2" %}') format('woff2');
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}
```

```css
/* ─── Tokens polices (100% hors ligne) ───────────────── */
--font-interface: 'Segoe UI', Ubuntu, system-ui, sans-serif;
/* → Segoe UI sur tous les postes Windows BF              */
/* → Ubuntu sur Linux, system-ui en fallback final        */

--font-logo: 'Playfair Display', Georgia, serif;
/* → Playfair Display si woff2 présent, sinon Georgia     */
/* → Usage EXCLUSIF : le nom "YELEN SCHOOL" dans sidebar  */

--font-mono: Consolas, 'DejaVu Sans Mono', 'Courier New', monospace;
/* → Consolas sur Windows, DejaVu sur Linux/WeasyPrint    */

/* ─── Tailles ─────────────────────────────────────────── */
--text-xs:   0.75rem;    /* 12px — badges, légendes */
--text-sm:   0.875rem;   /* 14px — texte secondaire */
--text-base: 1rem;       /* 16px — corps de texte */
--text-lg:   1.125rem;   /* 18px — titres de section */
--text-xl:   1.25rem;    /* 20px — titres de page */
--text-2xl:  1.5rem;     /* 24px — grands titres */
--text-3xl:  1.875rem;   /* 30px — dashboard stats */

/* ─── Poids ────────────────────────────────────────────── */
--font-light:    300;
--font-regular:  400;
--font-medium:   500;
--font-semibold: 600;
--font-bold:     700;
```

**Règles typographiques :**
- `font-family: var(--font-interface)` sur **TOUT** le body et templates → `Segoe UI` sur Windows BF
- `font-family: var(--font-logo)` **uniquement** pour le nom "YELEN SCHOOL" dans la sidebar
- `font-family: var(--font-mono)` pour les matricules (BF-..., PERS-...) et codes documents → `Consolas` sur Windows
- JAMAIS `Arial`, `Inter`, `Outfit` (nécessite téléchargement), ou autre police non listée ici
- JAMAIS `@import url('https://fonts.googleapis.com/...')` — bloqué hors ligne
- Titres de page : `font-size: var(--text-2xl); font-weight: var(--font-bold); letter-spacing: -0.02em`

---

## 3. ESPACEMENT & RAYONS

```css
--space-1: 0.25rem;   /*  4px */
--space-2: 0.5rem;    /*  8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */

--radius-sm:   6px;
--radius-md:   10px;
--radius-lg:   16px;
--radius-xl:   24px;
--radius-full: 9999px;  /* badges arrondis */
```

---

## 4. LAYOUT PRINCIPAL

```html
<!-- Structure de base de toutes les pages authentifiées -->
<body class="app-layout">

  <!-- Sidebar gauche — navigation principale -->
  <aside class="sidebar">
    <div class="sidebar-logo"><!-- Logo YELEN SCHOOL --></div>
    <nav class="sidebar-nav">
      <div class="sidebar-section">Principal</div>
      <a class="menu-item active" href="..."><!-- Item actif --></a>
      <a class="menu-item" href="..."><!-- Item standard --></a>
    </nav>
    <div class="sidebar-footer"><!-- User card --></div>
  </aside>

  <!-- Zone principale -->
  <div class="main-wrapper">

    <!-- Topbar -->
    <header class="topbar">
      <div class="topbar-left">
        <div class="topbar-crumb"><!-- Fil d'Ariane --></div>
        <div class="topbar-title"><!-- Titre de la page --></div>
      </div>
      <div class="topbar-right"><!-- Recherche + boutons --></div>
    </header>

    <!-- Contenu -->
    <main class="content">
      {% block content %}{% endblock %}
    </main>

  </div>
</body>
```

```css
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg-app);
  font-family: var(--font-interface);
  color: var(--color-text-primary);
}

/* ─── SIDEBAR PREMIUM ─────────────────────────────────── */
.sidebar {
  width: 252px;
  min-height: 100vh;
  background: linear-gradient(180deg, #0B1727 0%, #081220 100%);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  box-shadow: var(--shadow-sidebar);
  z-index: 20;
  flex-shrink: 0;
}

/* Logo zone */
.sidebar-logo {
  padding: 26px 22px 20px;
  border-bottom: 1px solid var(--color-border);
}

.logo-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  box-shadow: 0 4px 16px rgba(0,168,107,0.40);
  flex-shrink: 0;
}

.logo-text {
  font-family: var(--font-logo);
  font-size: 17px;
  color: var(--color-text-primary);
  line-height: 1.1;
}

.logo-sub {
  font-size: 10px;
  color: var(--color-text-muted);
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 2px;
}

/* Section label */
.sidebar-section {
  padding: 18px 16px 6px;
  font-size: 9.5px;
  color: var(--color-text-muted);
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sidebar-nav {
  flex: 1;
  padding: 8px 12px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.08) transparent;
}

/* ─── TOPBAR PREMIUM ──────────────────────────────────── */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  height: 62px;
  background: linear-gradient(180deg, rgba(13,26,45,0.98) 0%, rgba(8,12,22,0.95) 100%);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  position: sticky;
  top: 0;
  z-index: 10;
  backdrop-filter: blur(12px);
  box-shadow: var(--shadow-topbar);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.topbar-crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.topbar-crumb-sep {
  color: var(--color-border);
}

.topbar-crumb-page {
  color: var(--color-text-secondary);
}

.topbar-divider {
  width: 1px;
  height: 16px;
  background: var(--color-border);
}

.topbar-title {
  font-size: 14.5px;
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-bg-input);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  padding: 7px 16px;
  font-size: 12.5px;
  color: var(--color-text-muted);
  min-width: 200px;
  cursor: text;
  transition: border-color 0.2s;
}

.topbar-search:hover {
  border-color: rgba(255,255,255,0.12);
}

.topbar-icon-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-secondary);
  font-size: 16px;
}

.topbar-icon-btn:hover {
  background: var(--color-bg-selected);
  color: var(--color-text-primary);
}

/* Badge notification */
.has-notif {
  position: relative;
}
.has-notif::after {
  content: '';
  position: absolute;
  top: 7px; right: 7px;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--color-danger);
  border: 2px solid var(--color-bg-app);
}

/* ─── CONTENU ─────────────────────────────────────────── */
.content {
  padding: var(--space-6) 28px;
  flex: 1;
}

/* Page header */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--space-6);
}

.page-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.page-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-top: var(--space-1);
  font-weight: var(--font-regular);
}

.page-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-shrink: 0;
}
```

---

## 5. COMPOSANTS

### 5.1 Carte (`.card`)

```css
.card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  /* Ne pas mettre de padding ici — le mettre sur .card-body ou .card-header */
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-body {
  padding: var(--space-6);
}

/* Effet shimmer intérieur (optionnel, hover) */
.card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 60%, rgba(255,255,255,0.02));
  pointer-events: none;
  border-radius: inherit;
}
```

### 5.2 Carte statistique (`.stat-card`) — ⭐ Refonte premium v4.0

```css
.stat-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

/* Accent ambiant coloré en coin — appliqué inline avec la couleur thématique */
/* Exemple : style="--accent-color: #00A86B" */
.stat-card-accent {
  position: absolute;
  top: -20px; right: -20px;
  width: 100px; height: 100px;
  border-radius: 50%;
  background: var(--accent-color, var(--color-primary));
  filter: blur(32px);
  pointer-events: none;
  opacity: 0.35;
}

/* Reflet subtil intérieur */
.stat-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 60%, rgba(255,255,255,0.025));
  pointer-events: none;
}

.stat-icon-wrap {
  width: 44px; height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-bottom: var(--space-4);
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  line-height: 1;
  letter-spacing: -0.03em;
  margin-bottom: var(--space-1);
  position: relative;
  z-index: 1;
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--font-medium);
  position: relative;
  z-index: 1;
}

/* Indicateur de tendance */
.stat-trend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: var(--font-semibold);
  margin-top: var(--space-2);
  position: relative;
  z-index: 1;
}

.stat-trend-up   { color: var(--color-primary-light); }
.stat-trend-down { color: #FF6B7A; }

/* Mini progress bar en bas de stat-card */
.stat-progress {
  height: 4px;
  background: rgba(255,255,255,0.07);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-top: var(--space-2);
  position: relative;
  z-index: 1;
}

.stat-progress-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.6s ease;
}
```

**Exemple HTML stat-card :**

```html
<div class="stat-card animate-fade-up delay-1">
  <div class="stat-card-accent" style="--accent-color: #00A86B"></div>
  <div class="stat-icon-wrap" style="background: rgba(0,168,107,0.15); color: #00C07A;">👤</div>
  <div class="stat-value">1 247</div>
  <div class="stat-label">Élèves inscrits</div>
  <div class="stat-trend stat-trend-up">↑ 8.3% vs 2024–25</div>
  <div class="stat-progress">
    <div class="stat-progress-fill" style="width: 83%; background: linear-gradient(90deg, #00A86B, #00C07A);"></div>
  </div>
</div>
```

**Couleurs thématiques des 4 stat-cards dashboard :**

| Carte          | `--accent-color` | icon bg                      | progress gradient            |
|----------------|------------------|------------------------------|------------------------------|
| Élèves         | `#00A86B`        | `rgba(0,168,107,0.15)`       | `#00A86B → #00C07A`          |
| Classes        | `#17A2B8`        | `rgba(23,162,184,0.15)`      | `#17A2B8 → #0dcaf0`          |
| Personnel      | `#F5A623`        | `rgba(245,166,35,0.15)`      | `#F5A623 → #f7c04a`          |
| Finances       | `#DC3545`        | `rgba(220,53,69,0.15)`       | `#DC3545 → #ff6b7a`          |

### 5.3 Boutons

```css
/* ─── Bouton principal (vert dégradé + halo) ──────────── */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-6);
  font-family: var(--font-interface);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all 0.22s ease;
  box-shadow: var(--shadow-btn-primary);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-btn-hover);
  filter: brightness(1.07);
}

/* ─── Bouton secondaire (outline) ─────────────────────── */
.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: transparent;
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-6);
  font-family: var(--font-interface);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: var(--color-bg-hover);
  border-color: rgba(255,255,255,0.12);
}

/* ─── Bouton fantôme (navigation, liens) ──────────────── */
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-interface);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: color 0.2s;
}

.btn-ghost:hover { color: var(--color-text-primary); }

/* ─── Bouton danger ────────────────────────────────────── */
.btn-danger {
  background: var(--color-danger);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-6);
  font-family: var(--font-interface);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(220,53,69,0.3);
}

.btn-danger:hover { filter: brightness(1.1); transform: translateY(-1px); }

/* ─── Modificateurs de taille ─────────────────────────── */
.btn-sm { padding: 6px 14px; font-size: var(--text-xs); }
.btn-lg { padding: 12px 28px; font-size: var(--text-base); }
```

### 5.4 Badges (`.badge`) — ⭐ Style cristal v4.0

Les badges ont désormais une **bordure fine colorée** en plus du fond — effet "cristal premium".

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: var(--radius-full);
  font-size: 10.5px;
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Cristal — fond semi-transparent + bordure fine */
.badge-success { background: rgba(0,168,107,0.15);   color: #00C07A; border: 1px solid rgba(0,168,107,0.25); }
.badge-warning { background: rgba(245,166,35,0.15);  color: #F5A623; border: 1px solid rgba(245,166,35,0.25); }
.badge-danger  { background: rgba(220,53,69,0.15);   color: #FF6B7A; border: 1px solid rgba(220,53,69,0.25); }
.badge-info    { background: rgba(23,162,184,0.15);  color: #17A2B8; border: 1px solid rgba(23,162,184,0.25); }
.badge-neutral { background: rgba(154,174,196,0.10); color: var(--color-text-secondary); border: 1px solid var(--color-border); }
.badge-purple  { background: rgba(162,89,255,0.15);  color: #C084FC; border: 1px solid rgba(162,89,255,0.25); }

/* Statuts élèves */
.badge-affecte     { background: rgba(0,168,107,0.15);   color: #00C07A; border: 1px solid rgba(0,168,107,0.25); }
.badge-non-affecte { background: rgba(245,166,35,0.15);  color: #F5A623; border: 1px solid rgba(245,166,35,0.25); }
.badge-boursier    { background: rgba(23,162,184,0.15);  color: #17A2B8; border: 1px solid rgba(23,162,184,0.25); }
.badge-exonere     { background: rgba(154,174,196,0.10); color: var(--color-text-secondary); border: 1px solid var(--color-border); }
.badge-redoublant  { background: rgba(220,53,69,0.15);   color: #FF6B7A; border: 1px solid rgba(220,53,69,0.25); }
```

### 5.5 Champs de saisie (`.input`)

```css
.input {
  width: 100%;
  background: var(--color-bg-input);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  color: var(--color-text-primary);
  font-family: var(--font-interface);
  font-size: var(--text-base);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  outline: none;
}

.input:focus {
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 3px rgba(0,168,107,0.12);
}

.input::placeholder { color: var(--color-text-muted); }

.input:disabled,
.input-readonly {
  background: #080F18;
  color: var(--color-text-muted);
  border-style: dashed;
  cursor: not-allowed;
  opacity: 0.7;
}

/* Champ âge calculé automatiquement (lecture seule) */
.input-age-readonly {
  background: #080F18;
  color: var(--color-text-secondary);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-interface);
  cursor: not-allowed;
}

.input-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-1);
}

.input-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
  margin-top: var(--space-1);
}

.form-group { margin-bottom: var(--space-4); }

.select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%238CA5C0'%3E%3Cpath d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right var(--space-3) center;
  padding-right: var(--space-8);
}
```

### 5.6 Tableau de données (`.data-table`)

```css
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.data-table th {
  text-align: left;
  padding: 10px 22px;
  font-size: 10.5px;
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--color-border);
  background: rgba(0,0,0,0.15);
}

.data-table td {
  padding: 13px 22px;
  color: var(--color-text-primary);
  border-bottom: 1px solid rgba(255,255,255,0.04);
  vertical-align: middle;
}

.data-table tr:last-child td { border-bottom: none; }

.data-table tr:hover td { background: rgba(255,255,255,0.025); }

/* Colonne matricule */
.data-table .col-matricule {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* Colonne nom (principal) */
.data-table .col-name {
  font-weight: var(--font-semibold);
  font-size: var(--text-sm);
}

/* Sous-ligne info secondaire dans une cellule */
.td-sub {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
}
```

### 5.7 Avatar (`.avatar`)

```css
.avatar {
  width: 36px; height: 36px;
  border-radius: var(--radius-full);
  object-fit: cover;
  border: 2px solid var(--color-border);
}

.avatar-sm { width: 28px; height: 28px; }
.avatar-lg { width: 48px; height: 48px; }

/* Avatar initiales (fallback sans photo) */
.avatar-initials {
  width: 36px; height: 36px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--color-primary), var(--color-info));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: white;
  box-shadow: 0 2px 8px rgba(0,168,107,0.30);
}
```

### 5.8 Item de menu sidebar (`.menu-item`) — ⭐ Indicateur actif lumineux v4.0

```css
.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 13.5px;
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 3px;
  border: 1px solid transparent;
  position: relative;
}

.menu-item:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

/* ⭐ Item actif — style premium avec barre lumineuse */
.menu-item.active {
  background: linear-gradient(135deg, rgba(0,168,107,0.18), rgba(0,122,77,0.10));
  color: var(--color-primary);
  border: 1px solid var(--color-border-active);
  box-shadow: 0 2px 12px rgba(0,168,107,0.12),
              inset 0 0 0 0.5px rgba(0,168,107,0.15);
}

/* Barre indicateur gauche avec lueur */
.menu-item.active::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--color-primary);
  border-radius: 0 3px 3px 0;
  box-shadow: var(--glow-active-bar);
}

.menu-icon {
  font-size: 16px;
  width: 22px;
  text-align: center;
  flex-shrink: 0;
}

/* Badge compteur dans menu */
.menu-badge {
  margin-left: auto;
  font-size: 10px;
  font-weight: var(--font-bold);
  background: rgba(0,168,107,0.20);
  color: var(--color-primary);
  padding: 2px 7px;
  border-radius: var(--radius-full);
  letter-spacing: 0.03em;
}
```

### 5.9 User card sidebar (`.user-card`)

```css
.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all 0.2s;
}

.user-card:hover { border-color: rgba(255,255,255,0.12); }

.user-name  { font-size: 12.5px; font-weight: var(--font-semibold); color: var(--color-text-primary); }
.user-role  { font-size: 10px; color: var(--color-text-muted); margin-top: 1px; }
.user-chevron { margin-left: auto; color: var(--color-text-muted); font-size: 11px; }
```

### 5.10 Barre de progression (`.progress-track`)

```css
.progress-track {
  width: 100%;
  height: 5px;
  background: rgba(255,255,255,0.07);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light));
  transition: width 0.6s ease;
}
```

### 5.11 Actions rapides (`.quick-grid`)

```css
.quick-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: var(--space-4);
}

.quick-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  padding: var(--space-4) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all 0.2s;
}

.quick-btn:hover {
  background: var(--color-bg-selected);
  border-color: rgba(255,255,255,0.10);
  transform: translateY(-1px);
}

.quick-btn-icon  { font-size: 20px; }
.quick-btn-label { font-size: 11.5px; font-weight: var(--font-medium); color: var(--color-text-secondary); text-align: center; }
```

### 5.12 Fil d'activité (`.activity-feed`)

```css
.activity-feed { padding: 12px 0; }

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 11px 18px;
  transition: background 0.15s;
}

.activity-item:hover { background: rgba(255,255,255,0.025); }

/* Dot coloré avec lueur */
.activity-dot {
  width: 9px; height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 4px;
  box-shadow: 0 0 6px currentColor;
}

.activity-title { font-size: 12.5px; color: var(--color-text-primary); font-weight: var(--font-medium); line-height: 1.4; }
.activity-time  { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; }
.activity-divider { height: 1px; background: var(--color-border); margin: 0 18px; }
```

### 5.13 Formulaire multi-onglets (`.tab-container`) ⭐ v3.4

```css
.tab-container {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.tab-bar {
  display: flex;
  background: rgba(0,0,0,0.15);
  border-bottom: 1px solid var(--color-border);
  overflow-x: auto;
  scrollbar-width: none;
}

.tab-bar::-webkit-scrollbar { display: none; }

.tab-item {
  flex-shrink: 0;
  padding: var(--space-3) var(--space-6);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.tab-item:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-hover);
}

.tab-item.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  background: rgba(0,168,107,0.07);
}

.tab-panel        { padding: var(--space-6); display: none; }
.tab-panel.active { display: block; animation: fadeUp 0.2s ease; }

.tab-item .tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px; height: 18px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: white;
  font-size: 10px;
  font-weight: var(--font-bold);
  margin-left: var(--space-2);
}

.tab-item .tab-badge-empty { background: var(--color-text-muted); }
```

### 5.14 Zone de signature PDF ⭐ v3.4

```html
{% block signature %}
<div class="signature-zone">
  <div class="signature-city-date">{{ etablissement.ville }}, le {{ date_generation }}</div>
  <div class="signature-identity">
    <strong>{{ signataire_titre }} {{ signataire_nom }} {{ signataire_prenom }}</strong>
    <span class="signature-poste">{{ signataire_poste }}</span>
  </div>
  <div class="signature-line">
    <div class="signature-blank"></div>
    <span class="signature-legend">(Signature et Cachet)</span>
  </div>
</div>
{% endblock %}
```

### 5.15 Accordéons Sidebar Premium ⭐ v4.2

**Structure HTML :**
```html
<button class="accordion-toggle" id="pedagogie-toggle" type="button">
  <span class="accordion-label">
    <svg class="accordion-icon"><!-- icône --></svg>
    Pédagogie
  </span>
  <svg class="sb-chevron"><!-- chevron bas --></svg>
</button>
<div id="pedagogie-submenu" class="sb-submenu-modern">
  <a href="/matieres/" class="sb-item-submodern">
    <span class="sub-item-dot"></span>Matières
  </a>
  <!-- autres items -->
</div>
```

**CSS - Bouton accordéon :**
```css
.accordion-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 11px 14px;
  margin: 3px 6px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 12px;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  font-family: var(--font-interface);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.accordion-toggle::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(0,168,107,0.08) 0%, transparent 100%);
  opacity: 0;
  transition: opacity 0.25s ease;
}

.accordion-toggle:hover {
  background: rgba(255,255,255,0.03);
  color: var(--color-text-primary);
  border-color: rgba(255,255,255,0.04);
}

.accordion-toggle.active {
  background: linear-gradient(135deg, rgba(0,168,107,0.15) 0%, rgba(0,168,107,0.05) 100%);
  color: var(--color-primary-light);
  border-color: rgba(0,168,107,0.2);
}

.accordion-toggle .sb-chevron {
  transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.25s ease, color 0.25s ease;
}

.accordion-toggle.open .sb-chevron {
  transform: rotate(180deg);
  color: var(--color-primary);
}
```

**CSS - Sous-menu :**
```css
.sb-submenu-modern {
  padding: 6px 10px 12px 48px;
  max-height: 0;
  opacity: 0;
  transform: translateY(-10px) scaleY(0.95);
  transform-origin: top;
  transition: max-height 0.45s cubic-bezier(0.4, 0, 0.2, 1), 
              opacity 0.35s ease, 
              transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.sb-submenu-modern.open {
  max-height: 1000px;
  opacity: 1;
  transform: translateY(0) scaleY(1);
}

.sb-item-submodern {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  margin: 3px 0;
  color: var(--color-text-muted);
  font-size: 0.83rem;
  font-weight: 500;
  border-radius: 10px;
  border: 1px solid transparent;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.sb-item-submodern::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%) scaleY(0);
  width: 3px;
  height: 0;
  background: linear-gradient(180deg, var(--color-primary), var(--color-primary-light));
  border-radius: 0 3px 3px 0;
  transition: transform 0.25s ease, height 0.25s ease;
  box-shadow: 0 0 8px var(--color-primary-glow);
}

.sb-item-submodern:hover,
.sb-item-submodern.active {
  background: rgba(0,168,107,0.08);
  color: var(--color-primary-light);
  border-color: rgba(0,168,107,0.15);
  padding-left: 20px;
}

.sb-item-submodern:hover::before,
.sb-item-submodern.active::before {
  transform: translateY(-50%) scaleY(1);
  height: 60%;
}

/* Animation stagger sur ouverture */
@keyframes slideInSubItem {
  from { opacity: 0; transform: translateX(-12px); }
  to   { opacity: 1; transform: translateX(0); }
}

.sb-submenu-modern.open .sb-item-submodern {
  animation: slideInSubItem 0.35s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
.sb-submenu-modern.open .sb-item-submodern:nth-child(1) { animation-delay: 0.05s; }
.sb-submenu-modern.open .sb-item-submodern:nth-child(2) { animation-delay: 0.08s; }
.sb-submenu-modern.open .sb-item-submodern:nth-child(3) { animation-delay: 0.11s; }
/* ... jusqu'à 10 items max */
```

```css
/* CSS WeasyPrint uniquement */
.signature-zone        { margin-top: 40px; text-align: right; page-break-inside: avoid; }
.signature-city-date   { font-size: 10pt; color: #333; margin-bottom: 16px; }
.signature-identity    { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; margin-bottom: 32px; }
.signature-identity strong { font-size: 11pt; font-weight: bold; color: #000; }
.signature-poste       { font-size: 10pt; color: #444; font-style: italic; }
.signature-blank       { width: 160px; height: 1px; border-bottom: 1px solid #333; margin-left: auto; margin-bottom: 4px; }
.signature-legend      { font-size: 9pt; color: #666; }
```

---

## 6. ANIMATIONS

```css
/* ─── Déclarations ───────────────────────────────────── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(14px); }
  to   { opacity: 1; transform: translateY(0);    }
}

@keyframes shimmer {
  0%   { background-position: -400% 0; }
  100% { background-position:  400% 0; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.45; }
}

@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0,168,107,0); }
  50%       { box-shadow: 0 0 20px 4px rgba(0,168,107,0.18); }
}

/* ─── Classes utilitaires ────────────────────────────── */
.animate-fade-up { animation: fadeUp 0.4s ease both; }

.delay-1 { animation-delay: 0.05s; }
.delay-2 { animation-delay: 0.10s; }
.delay-3 { animation-delay: 0.15s; }
.delay-4 { animation-delay: 0.20s; }

/* Skeleton loader */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-bg-card) 25%,
    var(--color-bg-hover) 50%,
    var(--color-bg-card) 75%
  );
  background-size: 400% 100%;
  animation: shimmer 1.6s ease infinite;
  border-radius: var(--radius-sm);
  color: transparent;
  user-select: none;
}

/* Scrollbar globale */
::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.10); border-radius: 99px; }
```

**Règle :** appliquer `.animate-fade-up` + `.delay-N` sur les `.card` et `.stat-card` dans les vues liste.

---

## 7. COMPOSANTS DOCUMENT PDF (WeasyPrint)

### 7.1 En-tête officiel (tous documents)

```html
<div class="pdf-entete">
  <div class="pdf-entete-gauche">
    <img src="data:image/png;base64,{{ logo_base64 }}" class="pdf-logo" alt="Logo">
    <div>
      <p class="pdf-etab-nom">{{ etablissement.nom_etablissement }}</p>
      <p class="pdf-etab-info">{{ etablissement.adresse_complete }}</p>
      <p class="pdf-etab-info">Tél : {{ etablissement.telephone }}</p>
      <p class="pdf-etab-info">N° Agrément MENA : {{ etablissement.numero_agrement_mena }}</p>
    </div>
  </div>
  <div class="pdf-entete-droit">
    <img src="data:image/png;base64,{{ qr_code_base64 }}" class="pdf-qr" alt="QR Code">
    <p class="pdf-doc-numero">{{ document.numero }}</p>
  </div>
</div>
<hr class="pdf-separateur">
```

```css
@page { size: A4; margin: 2cm; }

body {
  font-family: "DejaVu Sans", sans-serif;
  font-size: 11pt;
  color: #1A1A1A;
}

.pdf-entete          { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.pdf-logo            { width: 60px; height: 60px; object-fit: contain; }
.pdf-qr              { width: 60px; height: 60px; }
.pdf-etab-nom        { font-size: 13pt; font-weight: bold; margin: 0 0 4px 0; }
.pdf-etab-info       { font-size: 9pt; color: #444; margin: 2px 0; }
.pdf-doc-numero      { font-size: 9pt; font-family: monospace; color: #333; text-align: center; margin-top: 4px; }
.pdf-separateur      { border: none; border-top: 2px solid #1B5E20; margin: 12px 0 20px 0; }

.pdf-titre {
  text-align: center;
  font-size: 16pt;
  font-weight: bold;
  text-decoration: underline;
  text-transform: uppercase;
  margin: 20px 0 24px 0;
  color: #1B5E20;
}

.pdf-corps           { font-size: 11pt; line-height: 1.7; text-align: justify; }
.pdf-corps .nom-eleve { font-weight: bold; text-decoration: underline; }
.pdf-corps .matricule { font-family: monospace; font-size: 10pt; }

.pdf-cachet {
  border: 2px solid #1B5E20;
  padding: 10px;
  width: 120px; height: 80px;
  display: inline-block;
  vertical-align: top;
}
```

### 7.2 Grille cartes d'identité scolaire (8/page A4 paysage)

```css
@page { size: A4 landscape; margin: 5mm; }

.grille-cartes {
  display: grid;
  grid-template-columns: repeat(4, 85mm);
  grid-template-rows: repeat(2, 54mm);
  gap: 2mm;
}

.carte           { width: 85mm; height: 54mm; border: 1px dashed #aaa; overflow: hidden; position: relative; }
.carte-recto,
.carte-verso     { width: 100%; height: 100%; padding: 4mm; box-sizing: border-box; }
```

---

## 8. FORMULAIRES MULTI-ÉTAPES

### Pattern enregistrement élève (4 étapes)

```html
<div class="steps-indicator">
  <div class="step completed">
    <div class="step-circle">✓</div>
    <span class="step-label">Identité</span>
  </div>
  <div class="step-line completed"></div>
  <div class="step active">
    <div class="step-circle">2</div>
    <span class="step-label">Famille</span>
  </div>
  <div class="step-line"></div>
  <div class="step">
    <div class="step-circle">3</div>
    <span class="step-label">Documents</span>
  </div>
  <div class="step-line"></div>
  <div class="step">
    <div class="step-circle">4</div>
    <span class="step-label">Statut</span>
  </div>
</div>
```

```css
.steps-indicator {
  display: flex;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
}

.step { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); }

.step-circle {
  width: 30px; height: 30px;
  border-radius: var(--radius-full);
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--color-text-muted);
  background: var(--color-bg-input);
  transition: all 0.3s;
}

.step.active .step-circle {
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(0,168,107,0.15);
}

.step.completed .step-circle {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
  box-shadow: 0 0 12px rgba(0,168,107,0.40);
}

.step-label { font-size: var(--text-xs); color: var(--color-text-muted); font-weight: var(--font-medium); }
.step.active .step-label    { color: var(--color-primary); font-weight: var(--font-semibold); }
.step.completed .step-label { color: var(--color-primary); }

.step-line {
  flex: 1;
  height: 2px;
  background: var(--color-border);
  border-radius: 99px;
  margin-bottom: 18px;
}
.step-line.completed { background: rgba(0,168,107,0.40); }
```

---

## 9. MESSAGES & ALERTES

```css
.alert {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  border-left: 4px solid;
  margin-bottom: var(--space-4);
}

.alert-success { background: rgba(0,168,107,0.10);  border-color: var(--color-primary); color: #00C07A; }
.alert-warning { background: rgba(245,166,35,0.10); border-color: var(--color-gold);    color: var(--color-gold); }
.alert-danger  { background: rgba(220,53,69,0.10);  border-color: var(--color-danger);  color: #FF6B7A; }
.alert-info    { background: rgba(23,162,184,0.10); border-color: var(--color-info);    color: var(--color-info); }
```

---

## 10. NOTES SCOLAIRES — RENDU COULEUR

Règle de coloration des notes (sur 20) dans les tableaux et bulletins :

```css
/* Classes utilitaires pour les cellules de notes */
.note-excellent { color: var(--color-note-excellent); font-weight: var(--font-bold); } /* >= 16 */
.note-bien      { color: var(--color-note-bien);      font-weight: var(--font-bold); } /* >= 12 */
.note-insuffisant { color: var(--color-note-insuffisant); font-weight: var(--font-bold); } /* < 12 */
```

**Seuils Burkina Faso :**

| Plage    | Classe CSS          | Couleur   |
|----------|---------------------|-----------|
| ≥ 16/20  | `.note-excellent`   | `#00C07A` |
| ≥ 12/20  | `.note-bien`        | `#F5A623` |
| < 12/20  | `.note-insuffisant` | `#FF6B7A` |

---

## 11. CHECKLIST DE VALIDATION

Avant de livrer **tout** template HTML, vérifie :

**Hors ligne ✈️**
- [ ] Aucun `@import url('https://fonts.googleapis.com/...')` dans le CSS ?
- [ ] Aucun `<script src="https://cdn...">` ou `<link href="https://cdn...">` ?
- [ ] Aucune `<img src="https://...">` pointant vers un serveur externe ?
- [ ] Police interface = `'Segoe UI', Ubuntu, system-ui, sans-serif` (zéro téléchargement) ?
- [ ] Police logo = `'Playfair Display', Georgia, serif` (woff2 dans `static/fonts/` ou fallback Georgia) ?
- [ ] Police mono = `Consolas, 'DejaVu Sans Mono', monospace` (système + WeasyPrint) ?
- [ ] HTMX chargé depuis `{% static "js/htmx.min.js" %}` (copie locale) ?

**Design & composants**
- [ ] `background: var(--color-bg-app)` sur le `<body>` ? (`#06101E`)
- [ ] Sidebar avec `background: linear-gradient(180deg, #0B1727 0%, #081220 100%)` ?
- [ ] Cartes en `var(--color-bg-card)` avec `border: 1px solid var(--color-border)` ?
- [ ] `font-family: var(--font-interface)` sur tout le texte ?
- [ ] `font-family: var(--font-mono)` sur les matricules et numéros de documents ?
- [ ] Boutons avec dégradé vert + halo (`.btn-primary`) ?
- [ ] `.animate-fade-up` appliqué sur les cartes ?
- [ ] **Stat-cards** avec `.stat-card-accent` (accent coloré ambiant) ?
- [ ] **Badges** avec bordure fine colorée (style cristal) ?
- [ ] `.menu-item.active::before` (barre indicateur lumineuse) présent dans les templates layout ?
- [ ] Topbar avec `backdrop-filter: blur(12px)` ?
- [ ] Montants en **FCFA** (jamais €, $) ?
- [ ] Notes sur **20** (jamais sur 100) ?
- [ ] Couleurs de note : vert ≥16, or ≥12, rouge <12 ?
- [ ] **Onglets par cycle** pour la configuration des signataires ?
- [ ] Zone `{% block signature %}` présente dans tous les templates PDF ?
- [ ] `SignataireDocument.get_signataire()` appelé côté Python avant tout rendu PDF ?
- [ ] Texte `signataire_titre signataire_nom signataire_prenom` dans la zone signature ?
- [ ] JAMAIS un nom de signataire hardcodé dans un template ?

---

## 12. CHANGELOG DESIGN SYSTEM

| Version | Date      | Changements |
|---------|-----------|-------------|
| v1.0    | Mars 2026 | Version initiale — tokens, layout, composants de base |
| v2.0    | Mars 2026 | Ajout `.input-age-readonly`, pattern sélection matricule HTMX |
| v3.0    | Mars 2026 | Ajout `.tab-container` (onglets cycles), zone signature PDF (`.signature-zone`), checklist mise à jour — Réf. Prompt v3.4 |
| **v4.0** | **Mars 2026** | **Refonte premium + conformité hors ligne** — fond `#06101E`, sidebar dégradé + indicateur actif lumineux, stat-cards accent ambiant + progress + tendance, badges cristal, topbar glassmorphe, nouveaux tokens `--shadow-*`/`--glow-*`, `.btn-ghost`, `.activity-feed`, `.quick-grid`, `.user-card`, scrollbar affinée, §10 notes scolaires. **Polices auto-hébergées** (`@font-face` + `static/fonts/`), suppression de tout CDN externe, section §0.1 contraintes hors ligne, checklist hors ligne |
| **v4.2** | **Avril 2026** | **Icônes modernisées** : designs SVG Lucide-style (`stroke-width="1.5"`). **Sidebar accordéons premium** : animations fluides, barre lumineuse, points lumineux. **Page Suivi des Appels** : refonte complète avec header premium, stats cards, timeline élégante, session cards, tableaux modernes, états vides élégants. |

---

*YELEN SCHOOL DESIGN_SYSTEM.md v4.2 — © 2026 — "Illuminer chaque parcours scolaire"*
