# DESIGN SYSTEM — YELEN SCHOOL v3.4
> Source de vérité visuelle · Réf. Prompt v3.4 · Mars 2026  
> **Règle absolue : tout template HTML doit être conforme à ce document.**

---

## 0. PHILOSOPHIE DESIGN

YELEN SCHOOL est une application de gestion scolaire au Burkina Faso.
Son interface doit inspirer **confiance, sérieux et modernité** tout en restant
accessible sur des connexions lentes et des écrans variés.

- **Dark mode permanent** — fond profond #0A1628, jamais de fond blanc
- **Minimalisme fonctionnel** — chaque élément a une raison d'être
- **Cohérence absolue** — les mêmes composants partout, jamais de CSS inline
- **Performance** — animations légères, pas de librairies inutiles
- **Accessibilité** — contrastes suffisants, tailles de police lisibles

---

## 1. TOKENS DE COULEUR

```css
/* ─── Fonds ──────────────────────────────────────────── */
--color-bg-app:        #0A1628;   /* Fond global de l'application */
--color-bg-card:       #111E35;   /* Surface des cartes et panneaux */
--color-bg-input:      #0D1B2E;   /* Fond des champs de saisie */
--color-bg-hover:      #162238;   /* Survol sur éléments interactifs */
--color-bg-selected:   #1A2A42;   /* Élément sélectionné / actif */
--color-bg-overlay:    rgba(0,0,0,0.55);  /* Modales / overlays */

/* ─── Bordures ────────────────────────────────────────── */
--color-border:        rgba(255,255,255,0.06);  /* Bordure standard */
--color-border-focus:  rgba(0,168,107,0.60);    /* Bordure focus (vert) */
--color-border-error:  rgba(220,53,69,0.70);    /* Bordure erreur */

/* ─── Palette principale ──────────────────────────────── */
--color-primary:       #00A86B;   /* Vert principal — actions, succès */
--color-primary-dark:  #007A4D;   /* Vert foncé — hover bouton */
--color-primary-glow:  rgba(0,168,107,0.35);  /* Halo vert boutons */

--color-gold:          #F5A623;   /* Or — avertissements, highlights */
--color-gold-dark:     #C27D00;   /* Or foncé */

--color-danger:        #DC3545;   /* Rouge — erreurs, suppressions */
--color-info:          #17A2B8;   /* Bleu info */

/* ─── Texte ────────────────────────────────────────────── */
--color-text-primary:  #E8EDF5;   /* Texte principal */
--color-text-secondary:#9AAEC4;   /* Texte secondaire / libellés */
--color-text-muted:    #5A7A9A;   /* Texte atténué / placeholders */
--color-text-inverse:  #0A1628;   /* Texte sur fond clair (badges) */

/* ─── Notes scolaires (BF) ────────────────────────────── */
--color-note-excellent: #00A86B;  /* >= 16/20 — vert */
--color-note-bien:      #F5A623;  /* >= 12/20 — or */
--color-note-insuffisant:#DC3545; /* < 12/20  — rouge */
```

---

## 2. TYPOGRAPHIE

```css
/* ─── Polices ─────────────────────────────────────────── */
/* Interface & corps de texte */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
/* Logo & titres décoratifs */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&display=swap');

--font-interface: 'Outfit', sans-serif;      /* TOUTE l'interface */
--font-logo:      'Playfair Display', serif; /* Logo YELEN uniquement */
--font-mono:      'DejaVu Sans Mono', monospace; /* Matricules, codes */

/* ─── Tailles ─────────────────────────────────────────── */
--text-xs:   0.75rem;   /* 12px — badges, légendes */
--text-sm:   0.875rem;  /* 14px — texte secondaire */
--text-base: 1rem;      /* 16px — corps de texte */
--text-lg:   1.125rem;  /* 18px — titres de section */
--text-xl:   1.25rem;   /* 20px — titres de page */
--text-2xl:  1.5rem;    /* 24px — grands titres */
--text-3xl:  1.875rem;  /* 30px — dashboard stats */

/* ─── Poids ────────────────────────────────────────────── */
--font-light:   300;
--font-regular: 400;
--font-medium:  500;
--font-semibold:600;
--font-bold:    700;
```

**Règles typographiques :**
- `font-family: var(--font-interface)` sur **TOUT** le body et templates
- `font-family: var(--font-logo)` **uniquement** pour le nom "YELEN SCHOOL"
- `font-family: var(--font-mono)` pour les matricules (BF-..., PERS-...) et codes documents
- JAMAIS Arial, Inter, ou autre police non listée ici

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

--radius-sm: 6px;
--radius-md: 10px;
--radius-lg: 16px;
--radius-xl: 24px;
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
      <a class="menu-item active" href="..."><!-- Item actif --></a>
      <a class="menu-item" href="..."><!-- Item standard --></a>
    </nav>
    <div class="sidebar-footer"><!-- Infos utilisateur --></div>
  </aside>

  <!-- Zone principale -->
  <div class="main-wrapper">

    <!-- Topbar -->
    <header class="topbar">
      <div class="topbar-title"><!-- Titre de la page --></div>
      <div class="topbar-actions"><!-- Boutons d'action globaux --></div>
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

.sidebar {
  width: 260px;
  min-height: 100vh;
  background: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
}

.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  height: 64px;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  position: sticky;
  top: 0;
  z-index: 10;
}

.content {
  padding: var(--space-6);
  flex: 1;
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
  padding: var(--space-6);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}
```

### 5.2 Carte statistique (`.stat-card`)

```css
.stat-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}

.stat-card .stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.stat-card .stat-value {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  line-height: 1;
}

.stat-card .stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-top: var(--space-1);
}
```

### 5.3 Boutons

```css
/* Bouton principal (vert avec halo) */
.btn-primary {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-6);
  font-family: var(--font-interface);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px var(--color-primary-glow);
}

.btn-primary:hover {
  background: linear-gradient(135deg, #00C07A, var(--color-primary));
  box-shadow: 0 6px 20px var(--color-primary-glow);
  transform: translateY(-1px);
}

/* Bouton secondaire (outline) */
.btn-secondary {
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
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(0,168,107,0.08);
}

/* Bouton danger */
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
}

/* Bouton petit */
.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
}
```

### 5.4 Badges (`.badge`)

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge-success  { background: rgba(0,168,107,0.20); color: #00C07A; }
.badge-warning  { background: rgba(245,166,35,0.20); color: #F5A623; }
.badge-danger   { background: rgba(220,53,69,0.20);  color: #FF6B7A; }
.badge-info     { background: rgba(23,162,184,0.20); color: #17A2B8; }
.badge-neutral  { background: rgba(154,174,196,0.15); color: var(--color-text-secondary); }

/* Couleurs personnalisées (statuts élèves) */
.badge-affecte   { background: rgba(0,168,107,0.20); color: #00C07A; }
.badge-non-affecte { background: rgba(245,166,35,0.20); color: #F5A623; }
.badge-boursier  { background: rgba(23,162,184,0.20); color: #17A2B8; }
.badge-exonere   { background: rgba(154,174,196,0.15); color: var(--color-text-secondary); }
.badge-redoublant{ background: rgba(220,53,69,0.20); color: #FF6B7A; }
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

.input::placeholder {
  color: var(--color-text-muted);
}

.input:disabled,
.input-readonly {
  background: #0D1525;
  color: var(--color-text-muted);
  border-style: dashed;
  cursor: not-allowed;
  opacity: 0.7;
}

/* Champ âge calculé automatiquement (lecture seule) */
.input-age-readonly {
  background: #0D1525;
  color: var(--color-text-secondary);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-interface);
  cursor: not-allowed;
}

/* Libellé de champ */
.input-label {
  display: block;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-1);
}

/* Message d'erreur */
.input-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
  margin-top: var(--space-1);
}

/* Groupe champ */
.form-group {
  margin-bottom: var(--space-4);
}

/* Select */
.select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%239AAEC4'%3E%3Cpath d='M6 8L1 3h10z'/%3E%3C/svg%3E");
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
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-app);
}

.data-table td {
  padding: var(--space-3) var(--space-4);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.data-table tr:hover td {
  background: var(--color-bg-hover);
}

/* Colonne matricule */
.data-table .col-matricule {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}
```

### 5.7 Avatar (`.avatar`)

```css
.avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  object-fit: cover;
  border: 2px solid var(--color-border);
}

.avatar-sm { width: 28px; height: 28px; }
.avatar-lg { width: 48px; height: 48px; }

/* Avatar initiales (fallback sans photo) */
.avatar-initials {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: white;
}
```

### 5.8 Item de menu sidebar (`.menu-item`)

```css
.menu-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all 0.15s ease;
  margin: 2px var(--space-2);
}

.menu-item:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.menu-item.active {
  background: rgba(0,168,107,0.15);
  color: var(--color-primary);
  border-left: 3px solid var(--color-primary);
}

.menu-item .menu-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}
```

### 5.9 Barre de progression (`.progress-track`)

```css
.progress-track {
  width: 100%;
  height: 6px;
  background: var(--color-bg-app);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, var(--color-primary), #00E096);
  transition: width 0.4s ease;
}
```

### 5.10 Formulaire multi-onglets (`.tab-container`) ⭐ v3.4

Utilisé pour : enregistrement élève (4 étapes), **configuration signataires par cycle**.

```css
/* Conteneur des onglets */
.tab-container {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* Barre d'onglets */
.tab-bar {
  display: flex;
  background: var(--color-bg-app);
  border-bottom: 1px solid var(--color-border);
  overflow-x: auto;
  scrollbar-width: none;
}

.tab-bar::-webkit-scrollbar { display: none; }

/* Onglet individuel */
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
  background: transparent;
}

/* Panneau de contenu d'un onglet */
.tab-panel {
  padding: var(--space-6);
  display: none;
}

.tab-panel.active {
  display: block;
  animation: fadeUp 0.2s ease;
}

/* Compteur / indicateur dans un onglet (ex: nb de signataires configurés) */
.tab-item .tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: white;
  font-size: 10px;
  font-weight: var(--font-bold);
  margin-left: var(--space-2);
}

.tab-item .tab-badge-empty {
  background: var(--color-text-muted);
}
```

**Structure HTML — Onglets cycles (signataires) :** ⭐ NOUVEAU v3.4

```html
<!-- templates/parametres/signataires.html -->
<div class="tab-container">

  <!-- Barre d'onglets — un par cycle actif -->
  <div class="tab-bar" role="tablist">
    {% for cycle in cycles_actifs %}
    <button
      class="tab-item {% if forloop.first %}active{% endif %}"
      role="tab"
      data-tab="cycle-{{ cycle.id }}"
      hx-get="/api/parametres/signataires/?cycle={{ cycle.id }}&annee={{ annee_courante.id }}"
      hx-target="#panel-cycle-{{ cycle.id }}"
      hx-trigger="click"
    >
      {{ cycle.nom }}
      {% with nb=cycle.signataires_configures %}
        <span class="tab-badge {% if nb == 0 %}tab-badge-empty{% endif %}">{{ nb }}</span>
      {% endwith %}
    </button>
    {% endfor %}
  </div>

  <!-- Panneaux de contenu — un par cycle -->
  {% for cycle in cycles_actifs %}
  <div
    id="panel-cycle-{{ cycle.id }}"
    class="tab-panel {% if forloop.first %}active{% endif %}"
    role="tabpanel"
  >
    <!-- Tableau des types de documents + dropdown signataire -->
    <table class="data-table">
      <thead>
        <tr>
          <th>Type de document</th>
          <th>Signataire</th>
          <th>Titre honorifique</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {% for type_doc in types_documents %}
        <tr>
          <td>{{ type_doc.libelle }}</td>
          <td>
            <select class="select input"
              name="membre_{{ cycle.id }}_{{ type_doc.code }}"
              hx-post="/api/parametres/signataires/"
              hx-trigger="change"
              hx-include="closest tr"
            >
              <option value="">— Sélectionner —</option>
              {% for membre in cycle.personnel_disponible %}
              <option value="{{ membre.id }}"
                {% if membre.est_signataire_pour type_doc cycle %}selected{% endif %}>
                {{ membre.nom }} {{ membre.prenom }} ({{ membre.poste_actuel }})
              </option>
              {% endfor %}
            </select>
            {% if not cycle.personnel_disponible %}
              <p class="input-error">⚠ Aucun personnel inscrit dans ce cycle</p>
            {% endif %}
          </td>
          <td>
            <input
              class="input"
              type="text"
              name="titre_{{ cycle.id }}_{{ type_doc.code }}"
              placeholder="ex: M. le Directeur"
              value="{{ cycle|get_titre_signataire:type_doc }}"
              hx-post="/api/parametres/signataires/"
              hx-trigger="change delay:800ms"
              hx-include="closest tr"
            >
          </td>
          <td>
            <span class="badge {% if cycle|has_signataire:type_doc %}badge-success{% else %}badge-neutral{% endif %}">
              {% if cycle|has_signataire:type_doc %}✓ Configuré{% else %}Non configuré{% endif %}
            </span>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endfor %}

</div>
```

### 5.11 Zone de signature PDF ⭐ NOUVEAU v3.4

**Composant WeasyPrint — bas de TOUS les documents officiels.**

```html
<!-- À inclure dans TOUS les templates documents PDF -->
<!-- Contexte requis : signataire_titre, signataire_nom, signataire_prenom,
     signataire_poste, etablissement.ville, date_generation -->

{% block signature %}
<div class="signature-zone">
  <div class="signature-city-date">
    {{ etablissement.ville }}, le {{ date_generation }}
  </div>
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

```css
/* CSS WeasyPrint — à inclure dans le <style> des templates PDF */
.signature-zone {
  margin-top: 40px;
  text-align: right;
  page-break-inside: avoid;
}

.signature-city-date {
  font-size: 10pt;
  color: #333;
  margin-bottom: 16px;
}

.signature-identity {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  margin-bottom: 32px;
}

.signature-identity strong {
  font-size: 11pt;
  font-weight: bold;
  color: #000;
}

.signature-poste {
  font-size: 10pt;
  color: #444;
  font-style: italic;
}

.signature-blank {
  width: 160px;
  height: 1px;
  border-bottom: 1px solid #333;
  margin-left: auto;
  margin-bottom: 4px;
}

.signature-legend {
  font-size: 9pt;
  color: #666;
}
```

---

## 6. ANIMATIONS

```css
/* ─── Déclarations ───────────────────────────────────── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0);    }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.5; }
}

@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position:  200% 0; }
}

/* ─── Classes utilitaires ────────────────────────────── */
.animate-fade-up { animation: fadeUp 0.35s ease both; }

.delay-1 { animation-delay: 0.05s; }
.delay-2 { animation-delay: 0.10s; }
.delay-3 { animation-delay: 0.15s; }
.delay-4 { animation-delay: 0.20s; }

/* Skeleton loader (chargement) */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-bg-card) 25%,
    var(--color-bg-hover) 50%,
    var(--color-bg-card) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.4s ease infinite;
  border-radius: var(--radius-sm);
  color: transparent;
  user-select: none;
}
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
/* PDF — structure obligatoire */
@page {
  size: A4;
  margin: 2cm;
}
body {
  font-family: "DejaVu Sans", sans-serif;
  font-size: 11pt;
  color: #1A1A1A;
}

.pdf-entete {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.pdf-logo    { width: 60px; height: 60px; object-fit: contain; }
.pdf-qr      { width: 60px; height: 60px; }
.pdf-etab-nom  { font-size: 13pt; font-weight: bold; margin: 0 0 4px 0; }
.pdf-etab-info { font-size: 9pt; color: #444; margin: 2px 0; }
.pdf-doc-numero { font-size: 9pt; font-family: monospace; color: #333; text-align: center; margin-top: 4px; }
.pdf-separateur { border: none; border-top: 2px solid #1B5E20; margin: 12px 0 20px 0; }

/* Titre du document */
.pdf-titre {
  text-align: center;
  font-size: 16pt;
  font-weight: bold;
  text-decoration: underline;
  text-transform: uppercase;
  margin: 20px 0 24px 0;
  color: #1B5E20;
}

/* Corps */
.pdf-corps { font-size: 11pt; line-height: 1.7; text-align: justify; }
.pdf-corps .nom-eleve { font-weight: bold; text-decoration: underline; }
.pdf-corps .matricule { font-family: monospace; font-size: 10pt; }

/* Cachet */
.pdf-cachet {
  border: 2px solid #1B5E20;
  padding: 10px;
  width: 120px;
  height: 80px;
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

.carte {
  width: 85mm;
  height: 54mm;
  border: 1px dashed #aaa; /* Trait de découpe */
  overflow: hidden;
  position: relative;
}

.carte-recto, .carte-verso {
  width: 100%;
  height: 100%;
  padding: 4mm;
  box-sizing: border-box;
}
```

---

## 8. FORMULAIRES MULTI-ÉTAPES

### Pattern enregistrement élève (4 étapes)

```html
<!-- Indicateur d'étapes -->
<div class="steps-indicator">
  <div class="step completed">
    <div class="step-circle">✓</div>
    <span class="step-label">Identité</span>
  </div>
  <div class="step-line"></div>
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
  margin-bottom: var(--space-8);
}
.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
}
.step-circle {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--color-text-muted);
  background: var(--color-bg-card);
}
.step.active .step-circle {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.step.completed .step-circle {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: white;
}
.step-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}
.step.active .step-label { color: var(--color-primary); }
.step-line {
  flex: 1;
  height: 2px;
  background: var(--color-border);
  margin-bottom: 18px;
}
```

---

## 9. MESSAGES & ALERTES

```css
.alert {
  padding: var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  border-left: 4px solid;
  margin-bottom: var(--space-4);
}
.alert-success { background: rgba(0,168,107,0.10); border-color: var(--color-primary); color: #00C07A; }
.alert-warning { background: rgba(245,166,35,0.10); border-color: var(--color-gold); color: var(--color-gold); }
.alert-danger  { background: rgba(220,53,69,0.10);  border-color: var(--color-danger); color: #FF6B7A; }
.alert-info    { background: rgba(23,162,184,0.10); border-color: var(--color-info); color: var(--color-info); }
```

---

## 10. CHECKLIST DE VALIDATION

Avant de livrer **tout** template HTML, vérifie :

- [ ] `background: var(--color-bg-app)` sur le `<body>` ?
- [ ] Cartes en `var(--color-bg-card)` avec `border: 1px solid var(--color-border)` ?
- [ ] `font-family: var(--font-interface)` sur tout le texte ?
- [ ] `font-family: var(--font-mono)` sur les matricules et numéros de documents ?
- [ ] Boutons avec dégradé vert + halo (`.btn-primary`) ?
- [ ] `.animate-fade-up` appliqué sur les cartes ?
- [ ] Montants en **FCFA** (jamais €, $) ?
- [ ] Notes sur **20** (jamais sur 100) ?
- [ ] Couleurs de note : vert ≥16, or ≥12, rouge <12 ?
- [ ] **Onglets par cycle** pour la configuration des signataires ?
- [ ] Zone `{% block signature %}` présente dans tous les templates PDF ?
- [ ] `SignataireDocument.get_signataire()` appelé côté Python avant tout rendu PDF ?
- [ ] Texte `signataire_titre signataire_nom signataire_prenom` dans la zone signature ?
- [ ] JAMAIS un nom de signataire hardcodé dans un template ?

---

## 11. CHANGELOG DESIGN SYSTEM

| Version | Date      | Changements |
|---------|-----------|-------------|
| v1.0    | Mars 2026 | Version initiale — tokens, layout, composants de base |
| v2.0    | Mars 2026 | Ajout `.input-age-readonly`, pattern sélection matricule HTMX |
| v3.0    | Mars 2026 | Ajout `.tab-container` (onglets cycles), zone signature PDF (`.signature-zone`), checklist mise à jour — Réf. Prompt v3.4 |

---

*YELEN SCHOOL DESIGN_SYSTEM.md v3.0 — © 2026 — "Illuminer chaque parcours scolaire"*
