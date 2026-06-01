---
name: yelen-school
description: >
  Contexte de développement pour YELEN SCHOOL, un système de gestion scolaire Django
  destiné aux établissements privés du Burkina Faso. Utilise TOUJOURS ce skill dès
  que la conversation porte sur YELEN SCHOOL, sur l'un de ses modules (élèves,
  personnel, notes, bulletins, paiements, cycles scolaires), ou dès que l'utilisateur
  mentionne ce projet — même implicitement (ex : "ajoute une page d'inscription",
  "génère le bulletin", "corrige le modèle Élève"). Ce skill contient les règles
  techniques, métier et design qui ne doivent JAMAIS être enfreintes.
---

# YELEN SCHOOL — Contexte de développement

## Vue d'ensemble
YELEN SCHOOL est un système de gestion scolaire pour les établissements privés
du Burkina Faso. Toutes les décisions techniques et fonctionnelles doivent respecter
les règles ci-dessous **sans exception**.

---

## Stack technique

| Composant        | Technologie                             |
|------------------|-----------------------------------------|
| Backend          | Django 4.2                              |
| Base de données  | PostgreSQL (jamais SQLite, même en dev) |
| Cache / files    | Redis                                   |
| Conteneurisation | Docker                                  |
| UI dynamique     | HTMX (jamais React, Vue, Angular)       |
| PDF              | WeasyPrint                              |
| Tests            | pytest + model_bakery (coverage ≥ 80 %) |
| Icônes           | Lucide Icons (jamais FontAwesome, Bootstrap Icons ou autre) |

---

## Règles techniques — NON NÉGOCIABLES

1. **HTMX uniquement** pour toutes les interactions UI. Aucun framework JS frontend.
2. **Tous les modèles étendent `BaseModel`** défini dans `core/models.py`.
3. **PostgreSQL obligatoire** — ne jamais proposer SQLite, y compris pour les tests.
4. **Tests** : pytest + model_bakery, couverture minimale **80 %**.
5. Aucune logique métier dans les vues : utiliser des services ou managers.
6. **Jamais de `db.sqlite3`** créé ou référencé, même pour un exemple ou un test rapide.

---

## Règles métier — NON NÉGOCIABLES

### Matricules
| Type       | Format            | Comportement                              |
|------------|-------------------|-------------------------------------------|
| Élève      | `BF-AAAA-NNNNN`   | Généré automatiquement, jamais modifiable |
| Personnel  | `PERS-AAAA-NNNNN` | Idem                                      |

*AAAA = année courante, NNNNN = séquence sur 5 chiffres.*

### Champs calculés
- **Âge** : toujours calculé depuis `date_naissance` (champ `readonly`, jamais saisi manuellement).

### Cycles scolaires
`Préscolaire` · `Primaire` · `Post-primaire` · `Secondaire`

### Monnaie
Toujours en **FCFA** — jamais `€`, `$` ou autre devise.

### Notes
Toujours **sur 20** — jamais sur 100 ni autre base.

### PDF / Signataires
Les signataires des documents PDF sont **configurables par cycle et par type de document**.

---

## Règles design — NON NÉGOCIABLES

> ⚠️ Toutes les valeurs ci-dessous sont **déjà implémentées dans `static/css/yelen.css`**.
> Ne jamais les réécrire ou les redéfinir — utiliser **uniquement les classes correspondantes**.

### Palette de couleurs

| Élément              | Valeur                                               |
|----------------------|------------------------------------------------------|
| Fond application     | `#0A1628` — **jamais fond blanc**                    |
| Fond des cartes      | `#111E35`                                            |
| Fond des inputs      | `#0D1B2E`                                            |
| Couleur principale   | `#00A86B` (vert)                                     |
| Texte principal      | `#E2E8F0`                                            |
| Texte secondaire     | `#A0AEC0`                                            |
| Texte labels         | `#CBD5E0`                                            |
| Danger               | `#E53E3E`                                            |
| Alerte texte         | `#FC8181`                                            |

### Typographie

| Usage               | Police             | Taille | Poids | Couleur   | Autre      |
|---------------------|--------------------|--------|-------|-----------|------------|
| Titres de page      | Outfit             | 24px   | 600   | `#FFFFFF` |            |
| Sous-titres         | Outfit             | 18px   | 500   | `#A0AEC0` |            |
| Labels formulaires  | Outfit             | 13px   | 500   | `#CBD5E0` | MAJUSCULES |
| Texte courant       | Outfit             | 14px   | 400   | `#E2E8F0` |            |
| Logo "YELEN SCHOOL" | Playfair Display   | —      | —     | —         | Uniquement pour le logo |
| Matricules          | DejaVu Sans Mono   | 13px   | —     | `#00A86B` |            |

**Règle absolue :** jamais Arial, Inter, Roboto ou toute autre police non listée ci-dessus.

### CSS — Règle absolue

- **JAMAIS** de CSS inline (`style="..."`)
- **JAMAIS** de balise `<style>` dans les templates HTML
- **JAMAIS** créer de nouvelles classes CSS de son propre chef
- Utiliser **exclusivement** les classes définies dans `static/css/yelen.css`
- Si un besoin visuel ne peut pas être couvert par une classe existante :
  **le signaler explicitement** et attendre confirmation avant toute création

### Cards & Surfaces

- Border         : `1px solid rgba(255,255,255,0.06)`
- Border-radius  : `12px`
- Box-shadow     : `0 4px 24px rgba(0,0,0,0.3)`
- Padding        : `24px`

### Espacements

- Gap entre sections  : `32px`
- Gap entre champs    : `16px`

### Boutons

| Type        | Background                  | Texte    | Border                      | Radius |
|-------------|-----------------------------|----------|-----------------------------|--------|
| Primaire    | `#00A86B`                   | blanc    | —                           | 8px    |
| Secondaire  | transparent                 | `#00A86B`| `1px solid #00A86B`         | 8px    |
| Danger      | `#E53E3E`                   | blanc    | —                           | 8px    |

- Padding : `10px 20px`
- Hover   : luminosité +10%, `transition: 200ms ease`

### Formulaires

- Input border        : `1px solid rgba(255,255,255,0.1)`
- Input focus border  : `#00A86B`
- Input border-radius : `8px`
- Input padding       : `10px 14px`

### Tableaux

- Header background   : `#0D1B2E`
- Row hover           : `rgba(0,168,107,0.06)`
- Séparateur de lignes: `1px solid rgba(255,255,255,0.04)`

### Badges / Statuts

| Statut   | Background                     | Texte     |
|----------|--------------------------------|-----------|
| Actif    | `rgba(0,168,107,0.15)`         | `#00A86B` |
| Inactif  | `rgba(160,174,192,0.15)`       | `#A0AEC0` |
| Alerte   | `rgba(229,62,62,0.15)`         | `#FC8181` |

### Icônes

- Bibliothèque : **Lucide Icons uniquement**
- Taille standard : `16px` (inline), `20px` (boutons), `24px` (titres)
- Couleur : hérite du texte parent — jamais de couleur hardcodée sur une icône
- Jamais FontAwesome, Bootstrap Icons, Material Icons ou SVG inline inventé

---

## Règle documentation — OBLIGATOIRE

Après **chaque modification** d'un fichier `.py`, `.html` ou `.md` :

1. Mettre à jour `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` en documentant la
   fonctionnalité créée ou modifiée.
2. Terminer la réponse par l'une de ces deux mentions :
   - `📘 Guide mis à jour — Section <Nom de la section>`
   - `📘 Guide : aucune mise à jour nécessaire` *(si vraiment non applicable)*

> ⚠️ **Une tâche sans cette mention est considérée comme INCOMPLÈTE.**

---

## Fichiers de référence — À lire avant de générer du code

| Fichier                                      | Quand le lire                                  |
|----------------------------------------------|------------------------------------------------|
| `static/css/yelen.css`                       | Avant tout fichier HTML / template             |
| `docs/DESIGN_SYSTEM_v4.md`                   | Avant tout travail sur l'UI ou le design       |
| `docs/GUIDE_DEV_V2.md`                       | Avant tout nouveau module ou refactoring       |
| `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md`     | Avant toute mise à jour de documentation       |
| `core/models.py`                             | Avant tout nouveau modèle Django               |

---

## Structure de projet

```
yelen_school/
├── core/
│   └── models.py              # BaseModel à étendre partout
├── eleves/
├── personnel/
├── notes/
├── bulletins/
├── paiements/
├── static/
│   └── css/
│       └── yelen.css          # Source UNIQUE de toutes les classes CSS
├── templates/
├── docs/
│   ├── GUIDE_UTILISATION_YELEN_SCHOOL.md
│   ├── DESIGN_SYSTEM_v4.md
│   └── GUIDE_DEV_V2.md
└── tests/
```

---

## Checklist avant de soumettre une réponse

- [ ] Aucune migration SQLite ni `db.sqlite3` suggérée
- [ ] Tous les nouveaux modèles héritent de `BaseModel`
- [ ] Pas de framework JS autre que HTMX
- [ ] Montants en FCFA, notes sur 20
- [ ] Matricules générés auto et non modifiables
- [ ] Fond `#0A1628`, police Outfit, zéro CSS inline, zéro `<style>`
- [ ] Icônes Lucide uniquement
- [ ] Aucune classe CSS créée sans signalement préalable
- [ ] `static/css/yelen.css` consulté avant tout template HTML
- [ ] `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` mis à jour
- [ ] Réponse terminée par `📘 Guide mis à jour — Section X` ou mention équivalente
