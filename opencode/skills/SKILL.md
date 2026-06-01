---
name: yelen-design-system
description: >
  Système de design offline-first pour YELEN SCHOOL. Utilise ce skill à chaque fois
  qu'une page HTML, un template Django, un composant HTMX ou une feuille CSS doit
  être créé ou modifié. Garantit un rendu moderne, épuré, professionnel et 100 %
  sans dépendance externe (aucun CDN, aucune police distante, aucune librairie JS).
  Déclencher même si l'utilisateur dit juste "fais-moi une belle page", "améliore
  le design", "ajoute un formulaire", "crée un dashboard", "refais le style", etc.
---

# YELEN DESIGN SYSTEM — Guide de design offline-first

## Philosophie fondatrice

> **Une seule source de vérité : `yelen.css`.**
> Aucun CDN. Aucune font Google. Aucune librairie UI externe.
> Tout est auto-contenu, rapide, et fonctionne sans réseau.

Le style YELEN est **sombre, précis, vivant**. Il évoque la nuit africaine éclairée
de points lumineux — fond profond, accents verts vibrants, typographie nette.
Chaque page doit inspirer confiance et professionnalisme.

---

## 1. PALETTE DE COULEURS — IMMUABLE

```css
/* ──────────────────────────────────────────── */
/*  FONDATIONS                                  */
/* ──────────────────────────────────────────── */
--color-bg:          #0A1628;   /* fond global — JAMAIS modifié */
--color-surface:     #111E35;   /* cartes, panneaux, modales    */
--color-surface-2:   #162340;   /* hover de surface, imbriqués  */
--color-border:      #1E3055;   /* séparateurs, contours        */
--color-border-soft: #243660;   /* bordures subtiles            */

/* ──────────────────────────────────────────── */
/*  COULEUR PRINCIPALE                          */
/* ──────────────────────────────────────────── */
--color-primary:        #00A86B;  /* vert YELEN — boutons, liens actifs  */
--color-primary-hover:  #00C97F;  /* état hover                          */
--color-primary-muted:  #00A86B1A; /* fond teinté (badges, highlights)   */
--color-primary-border: #00A86B40; /* bordure accent                     */

/* ──────────────────────────────────────────── */
/*  COULEURS SÉMANTIQUES                        */
/* ──────────────────────────────────────────── */
--color-success:  #00A86B;
--color-warning:  #F59E0B;
--color-danger:   #EF4444;
--color-info:     #3B82F6;

/* ──────────────────────────────────────────── */
/*  TEXTE                                       */
/* ──────────────────────────────────────────── */
--color-text:          #E8EDF5;   /* corps principal        */
--color-text-muted:    #7A92B4;   /* labels, méta-infos     */
--color-text-faint:    #4A6180;   /* placeholders, disabled */
--color-text-inverse:  #0A1628;   /* texte sur fond clair   */
```

---

## 2. TYPOGRAPHIE — UNIQUEMENT DES FONTS LOCALES

### Règle absolue
**Jamais** de `@import url('https://fonts.googleapis.com/...')`.
Toutes les fonts sont déclarées en `@font-face` depuis `/static/fonts/`.

### Fonts du projet

| Rôle                  | Font               | Fichier                        |
|-----------------------|--------------------|--------------------------------|
| Interface principale  | Outfit             | `outfit-variable.woff2`        |
| Logo "YELEN SCHOOL"   | Playfair Display   | `playfair-display-bold.woff2`  |
| Matricules / codes    | DejaVu Sans Mono   | `dejavu-sans-mono.woff2`       |
| Titres de section     | Outfit (700–800)   | même fichier variable          |

### Déclaration @font-face type

```css
@font-face {
  font-family: 'Outfit';
  src: url('/static/fonts/outfit-variable.woff2') format('woff2');
  font-weight: 100 900;
  font-display: swap;
}

@font-face {
  font-family: 'Playfair Display';
  src: url('/static/fonts/playfair-display-bold.woff2') format('woff2');
  font-weight: 700;
  font-display: swap;
}

@font-face {
  font-family: 'DejaVu Sans Mono';
  src: url('/static/fonts/dejavu-sans-mono.woff2') format('woff2');
  font-weight: 400 700;
  font-display: swap;
}
```

### Échelle typographique

```css
--font-family-ui:    'Outfit', system-ui, sans-serif;
--font-family-logo:  'Playfair Display', Georgia, serif;
--font-family-mono:  'DejaVu Sans Mono', 'Courier New', monospace;

--text-xs:    0.75rem;   /* 12px  — méta, badges */
--text-sm:    0.875rem;  /* 14px  — secondaire   */
--text-base:  1rem;      /* 16px  — corps        */
--text-lg:    1.125rem;  /* 18px  — sous-titres  */
--text-xl:    1.25rem;   /* 20px  — titres carte */
--text-2xl:   1.5rem;    /* 24px  — h3           */
--text-3xl:   1.875rem;  /* 30px  — h2           */
--text-4xl:   2.25rem;   /* 36px  — h1           */
--text-5xl:   3rem;      /* 48px  — hero         */
```

---

## 3. ESPACEMENT & GRILLE

```css
--space-1:  0.25rem;   /*  4px */
--space-2:  0.5rem;    /*  8px */
--space-3:  0.75rem;   /* 12px */
--space-4:  1rem;      /* 16px */
--space-5:  1.25rem;   /* 20px */
--space-6:  1.5rem;    /* 24px */
--space-8:  2rem;      /* 32px */
--space-10: 2.5rem;    /* 40px */
--space-12: 3rem;      /* 48px */
--space-16: 4rem;      /* 64px */
--space-20: 5rem;      /* 80px */

--radius-sm:   4px;
--radius-md:   8px;
--radius-lg:   12px;
--radius-xl:   16px;
--radius-2xl:  24px;
--radius-full: 9999px;
```

---

## 4. OMBRES & EFFETS

```css
--shadow-sm:  0 1px 3px rgba(0,0,0,.4), 0 1px 2px rgba(0,0,0,.3);
--shadow-md:  0 4px 6px rgba(0,0,0,.4), 0 2px 4px rgba(0,0,0,.3);
--shadow-lg:  0 10px 15px rgba(0,0,0,.4), 0 4px 6px rgba(0,0,0,.3);
--shadow-xl:  0 20px 25px rgba(0,0,0,.45), 0 10px 10px rgba(0,0,0,.3);
--shadow-glow: 0 0 20px rgba(0,168,107,.25);   /* accent vert */
--shadow-card: 0 2px 8px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.04);
```

---

## 5. COMPOSANTS — CLASSES STANDARD

### 5.1 Layout de page

```html
<body class="yk-body">
  <aside class="yk-sidebar">...</aside>
  <div class="yk-main">
    <header class="yk-topbar">...</header>
    <main class="yk-content">
      <div class="yk-page-header">
        <h1 class="yk-page-title">Titre</h1>
        <div class="yk-page-actions">...</div>
      </div>
      <!-- contenu -->
    </main>
  </div>
</body>
```

### 5.2 Cartes

```html
<!-- Carte simple -->
<div class="yk-card">
  <div class="yk-card-header">
    <h3 class="yk-card-title">Titre</h3>
    <span class="yk-card-badge">Info</span>
  </div>
  <div class="yk-card-body">Contenu</div>
  <div class="yk-card-footer">Pied</div>
</div>

<!-- Carte statistique (dashboard) -->
<div class="yk-stat-card">
  <div class="yk-stat-icon yk-stat-icon--green">⬡</div>
  <div class="yk-stat-body">
    <span class="yk-stat-value">1 248</span>
    <span class="yk-stat-label">Élèves actifs</span>
  </div>
  <span class="yk-stat-delta yk-stat-delta--up">+12 %</span>
</div>
```

### 5.3 Tableaux

```html
<div class="yk-table-wrapper">
  <table class="yk-table">
    <thead>
      <tr>
        <th class="yk-th">Matricule</th>
        <th class="yk-th">Nom</th>
        <th class="yk-th yk-th--right">Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr class="yk-tr">
        <td class="yk-td"><code class="yk-mono">BF-2025-00001</code></td>
        <td class="yk-td">Kaboré Mamadou</td>
        <td class="yk-td yk-td--right">
          <button class="yk-btn yk-btn--ghost yk-btn--sm">Voir</button>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

### 5.4 Formulaires

```html
<form class="yk-form">
  <div class="yk-form-group">
    <label class="yk-label" for="nom">Nom complet <span class="yk-required">*</span></label>
    <input class="yk-input" type="text" id="nom" placeholder="Ex : Kaboré Mamadou">
    <span class="yk-hint">Tel qu'il figure sur l'acte de naissance</span>
  </div>

  <div class="yk-form-group yk-form-group--error">
    <label class="yk-label" for="email">Email</label>
    <input class="yk-input yk-input--error" type="email" id="email">
    <span class="yk-error-msg">Format invalide</span>
  </div>

  <div class="yk-form-row">
    <!-- deux champs côte-à-côte -->
    <div class="yk-form-group">...</div>
    <div class="yk-form-group">...</div>
  </div>

  <div class="yk-form-actions">
    <button type="button" class="yk-btn yk-btn--ghost">Annuler</button>
    <button type="submit" class="yk-btn yk-btn--primary">Enregistrer</button>
  </div>
</form>
```

### 5.5 Boutons

```css
/* Classes disponibles */
.yk-btn                   /* base — ne pas utiliser seul */
.yk-btn--primary          /* vert, action principale    */
.yk-btn--secondary        /* surface-2, action neutre   */
.yk-btn--danger           /* rouge, action destructrice */
.yk-btn--ghost            /* transparent, contour       */
.yk-btn--icon             /* carré, icône seul          */
.yk-btn--sm               /* petit                      */
.yk-btn--lg               /* grand                      */
.yk-btn--full             /* largeur 100 %              */
.yk-btn--loading          /* spinner inline             */
```

### 5.6 Badges & statuts

```html
<span class="yk-badge yk-badge--green">Actif</span>
<span class="yk-badge yk-badge--red">Exclu</span>
<span class="yk-badge yk-badge--yellow">Suspendu</span>
<span class="yk-badge yk-badge--blue">Nouveau</span>
<span class="yk-badge yk-badge--gray">Archivé</span>
```

### 5.7 Alertes & toasts

```html
<div class="yk-alert yk-alert--success">
  <span class="yk-alert-icon">✓</span>
  <span class="yk-alert-msg">Élève enregistré avec succès.</span>
</div>

<div class="yk-alert yk-alert--danger">
  <span class="yk-alert-icon">✕</span>
  <span class="yk-alert-msg">Erreur lors de la sauvegarde.</span>
</div>
```

### 5.8 Navigation latérale

```html
<aside class="yk-sidebar">
  <div class="yk-sidebar-brand">
    <span class="yk-logo">YELEN SCHOOL</span>
  </div>
  <nav class="yk-nav">
    <a href="#" class="yk-nav-item yk-nav-item--active">
      <span class="yk-nav-icon">⊞</span>
      <span class="yk-nav-label">Tableau de bord</span>
    </a>
    <a href="#" class="yk-nav-item">
      <span class="yk-nav-icon">◑</span>
      <span class="yk-nav-label">Élèves</span>
      <span class="yk-nav-count">248</span>
    </a>
  </nav>
</aside>
```

---

## 6. ANIMATIONS CSS — SANS JS

```css
/* Entrées de page */
@keyframes yk-fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes yk-fadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes yk-slideIn {
  from { opacity: 0; transform: translateX(-16px); }
  to   { opacity: 1; transform: translateX(0); }
}

/* Utilitaires d'animation */
.yk-animate-fade-up  { animation: yk-fadeUp  .35s ease both; }
.yk-animate-fade-in  { animation: yk-fadeIn  .25s ease both; }
.yk-animate-slide-in { animation: yk-slideIn .3s ease both;  }

/* Délais d'animation en cascade (stagger) */
.yk-stagger-1 { animation-delay: .05s; }
.yk-stagger-2 { animation-delay: .10s; }
.yk-stagger-3 { animation-delay: .15s; }
.yk-stagger-4 { animation-delay: .20s; }
.yk-stagger-5 { animation-delay: .25s; }

/* Spinner de chargement */
@keyframes yk-spin { to { transform: rotate(360deg); } }
.yk-spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: yk-spin .7s linear infinite;
}

/* Pulse pour indicateurs live */
@keyframes yk-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: .4; }
}
.yk-pulse { animation: yk-pulse 2s ease-in-out infinite; }
```

---

## 7. RÈGLES DE CONSTRUCTION — CHECKLIST OBLIGATOIRE

Avant de livrer **toute page ou composant**, vérifier chaque point :

### ✅ Zéro dépendance externe
- [ ] Aucun `<link>` vers un CDN (Bootstrap, Tailwind, etc.)
- [ ] Aucun `<script src="https://...">` externe
- [ ] Aucun `@import url('https://fonts.google...')` dans le CSS
- [ ] Toutes les fonts via `@font-face` local dans `yelen.css`
- [ ] Les icônes sont des caractères Unicode, SVG inline, ou sprite SVG local

### ✅ Conformité palette
- [ ] `background-color` racine = `#0A1628`
- [ ] Cartes/panneaux = `#111E35`
- [ ] Accent principal = `#00A86B`
- [ ] Aucune couleur hors palette sauf justification documentée
- [ ] Mode clair **interdit** — toujours dark

### ✅ Typographie
- [ ] Police UI = Outfit (jamais Inter, Arial, Roboto, system-ui seul)
- [ ] Logo = Playfair Display uniquement sur "YELEN SCHOOL"
- [ ] Matricules / codes = DejaVu Sans Mono dans `.yk-mono`

### ✅ CSS propre
- [ ] Zéro `style=""` inline dans le HTML
- [ ] Toutes les classes prefixées `yk-`
- [ ] Variables CSS utilisées (jamais de valeurs codées en dur)
- [ ] Pas de `!important` sauf exception documentée

### ✅ Structure HTML
- [ ] Hiérarchie sémantique (`header`, `main`, `nav`, `section`, `article`)
- [ ] Attributs ARIA de base (`aria-label`, `role`) sur les composants clés
- [ ] Classes d'animation `yk-animate-*` + `yk-stagger-*` sur les listes/cartes

### ✅ HTMX (si interaction dynamique)
- [ ] `hx-target` et `hx-swap` définis explicitement
- [ ] `hx-indicator` pointant vers un `.yk-spinner`
- [ ] Aucune logique JS non-HTMX sauf cas documenté

---

## 8. TEMPLATE DE BASE — PAGE DJANGO

```django
{% load static %}
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}YELEN SCHOOL{% endblock %}</title>
  <link rel="stylesheet" href="{% static 'css/yelen.css' %}">
  {% block extra_css %}{% endblock %}
</head>
<body class="yk-body">

  {% include "partials/_sidebar.html" %}

  <div class="yk-main">
    {% include "partials/_topbar.html" %}

    <main class="yk-content yk-animate-fade-in">

      <div class="yk-page-header">
        <div>
          <h1 class="yk-page-title">{% block page_title %}{% endblock %}</h1>
          <p class="yk-page-subtitle">{% block page_subtitle %}{% endblock %}</p>
        </div>
        <div class="yk-page-actions">
          {% block page_actions %}{% endblock %}
        </div>
      </div>

      {% if messages %}
        {% for message in messages %}
          <div class="yk-alert yk-alert--{{ message.tags }} yk-animate-fade-up">
            <span class="yk-alert-msg">{{ message }}</span>
          </div>
        {% endfor %}
      {% endif %}

      {% block content %}{% endblock %}

    </main>
  </div>

  <script src="{% static 'js/htmx.min.js' %}"></script>
  {% block extra_js %}{% endblock %}
</body>
</html>
```

---

## 9. PATTERNS VISUELS AVANCÉS

### 9.1 Fond texturé (grille subtile)
```css
.yk-body {
  background-color: var(--color-bg);
  background-image:
    linear-gradient(rgba(0,168,107,.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,168,107,.03) 1px, transparent 1px);
  background-size: 40px 40px;
}
```

### 9.2 Lueur de carte au hover
```css
.yk-card:hover {
  border-color: var(--color-primary-border);
  box-shadow: var(--shadow-card), var(--shadow-glow);
  transform: translateY(-2px);
  transition: all .2s ease;
}
```

### 9.3 Barre de progression
```html
<div class="yk-progress">
  <div class="yk-progress-bar" style="--progress: 72%"></div>
</div>
```
```css
.yk-progress { height: 6px; background: var(--color-border); border-radius: var(--radius-full); overflow: hidden; }
.yk-progress-bar { height: 100%; width: var(--progress); background: var(--color-primary); border-radius: inherit; transition: width .5s ease; }
```

### 9.4 Indicateur de statut live
```html
<span class="yk-dot yk-dot--green"></span>
```
```css
.yk-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.yk-dot--green { background: var(--color-primary); box-shadow: 0 0 0 3px rgba(0,168,107,.2); animation: yk-pulse 2s infinite; }
```

### 9.5 Séparateur de section élégant
```html
<div class="yk-divider"><span>Informations scolaires</span></div>
```
```css
.yk-divider { display: flex; align-items: center; gap: var(--space-4); color: var(--color-text-muted); font-size: var(--text-xs); text-transform: uppercase; letter-spacing: .1em; margin: var(--space-8) 0; }
.yk-divider::before, .yk-divider::after { content: ''; flex: 1; height: 1px; background: var(--color-border); }
```

---

## 10. ICÔNES — SANS LIBRAIRIE EXTERNE

Utiliser uniquement :
1. **Caractères Unicode** : `✓ ✕ ⊞ ◑ ⬡ ≡ ← → ↑ ↓ ⋯ ✎ ⊕ ⊗`
2. **SVG inline minimal** dans le HTML (< 5 lignes)
3. **Sprite SVG local** dans `/static/img/icons.svg`

```html
<!-- Exemple SVG inline -->
<svg class="yk-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M12 5v14M5 12h14"/>
</svg>
```
```css
.yk-icon { width: 1em; height: 1em; vertical-align: middle; }
```

---

## 11. RESPONSIVE — BREAKPOINTS

```css
/* Mobile first */
/* xs:   < 480px  — téléphone        */
/* sm:   ≥ 480px  — grand téléphone  */
/* md:   ≥ 768px  — tablette         */
/* lg:   ≥ 1024px — laptop           */
/* xl:   ≥ 1280px — desktop          */
/* 2xl:  ≥ 1536px — grand écran      */

@media (max-width: 1024px) {
  .yk-sidebar { transform: translateX(-100%); }
  .yk-sidebar.is-open { transform: translateX(0); }
  .yk-main { margin-left: 0; }
}
```

---

## 12. ACCESSIBILITÉ MINIMALE

```html
<!-- Focus visible -->
<style>
  :focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
    border-radius: var(--radius-sm);
  }
</style>

<!-- Skip link -->
<a href="#main-content" class="yk-skip-link">Aller au contenu</a>

<!-- Bouton avec label accessible -->
<button class="yk-btn yk-btn--icon" aria-label="Supprimer l'élève">
  <span aria-hidden="true">✕</span>
</button>
```

---

## 13. EXEMPLES DE PAGES TYPES

### Dashboard
- 4 `yk-stat-card` en grille (élèves, personnel, paiements, notes)
- 1 graphique SVG inline (progression scolaire)
- 1 tableau récent `yk-table` (dernières inscriptions)
- Chaque carte avec `yk-animate-fade-up` + `yk-stagger-N`

### Liste / CRUD
- `yk-page-header` avec bouton "Nouveau" à droite
- Barre de recherche + filtres en `yk-card` compact
- `yk-table-wrapper` avec pagination `yk-pagination`
- Modal de confirmation de suppression en HTMX

### Formulaire d'inscription
- `yk-card` centré, max-width 720px
- Sections séparées par `yk-divider`
- `yk-form-row` pour les champs pairs
- Boutons d'action en `yk-form-actions` alignés à droite
- Feedback HTMX avec `yk-alert` dynamique

### Bulletin / PDF
- Rendu WeasyPrint : fond blanc UNIQUEMENT pour l'impression
- En-tête avec logo YELEN SCHOOL en Playfair Display
- Tableau de notes avec colonnes colorées par matière
- Signature configurable par cycle

---

> **Rappel final** : Ce skill est actif sur TOUTES les pages de YELEN SCHOOL.
> Tout fichier `.html` ou `.css` produit doit respecter ces règles sans exception.
> Le résultat doit être beau offline, sur laptop, sur tablette, sans réseau.
