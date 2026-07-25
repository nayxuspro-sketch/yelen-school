# YELEN SCHOOL — Contexte de développement

## Vue d'ensemble
YELEN SCHOOL est un système de gestion scolaire pour les établissements privés
du Burkina Faso. Toutes les décisions techniques et fonctionnelles doivent respecter
les règles ci-dessous **sans exception**.

---

## Stack technique

| Composant        | Technologie                          |
|------------------|--------------------------------------|
| Backend          | Django 4.2                           |
| Base de données  | PostgreSQL (jamais SQLite, même en dev) |
| Cache / files    | Redis                                |
| Conteneurisation | Docker                               |
| UI dynamique     | HTMX (jamais React, Vue, Angular)    |
| PDF              | WeasyPrint                           |
| Tests            | pytest + model_bakery (coverage ≥ 80 %) |
| IDE déclaré      | Google Antigravity                   |

---

## Règles techniques — NON NÉGOCIABLES

1. **HTMX uniquement** pour toutes les interactions UI. Aucun framework JS frontend.
2. **Tous les modèles étendent `BaseModel`** défini dans `core/models.py`.
3. **PostgreSQL obligatoire** — ne jamais proposer SQLite, y compris pour les tests.
4. **Tests** : pytest + model_bakery, couverture minimale **80 %**.
5. Aucune logique métier dans les vues : utiliser des services ou managers.

---

## Règles métier — NON NÉGOCIABLES

### Matricules
| Type       | Format                  | Comportement                        |
|------------|-------------------------|-------------------------------------|
| Élève      | `{CODE_ETAB}-AAAA-NN`   | Généré automatiquement, jamais modifiable |
| Personnel  | `{CODE_ETAB}-P-AAAA-NN`   | Idem                                |

*CODE_ETAB = code de l'établissement, AAAA = année courante, NN = numéro d'enregistrement.*

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

| Élément             | Valeur / Règle                                          |
|---------------------|---------------------------------------------------------|
| Fond application    | `#0A1628` — **jamais fond blanc**                       |
| Couleur des cartes  | `#111E35`                                               |
| Couleur principale  | `#00A86B` (vert)                                        |
| Police interface    | **Outfit** — jamais Arial, Inter ou autre               |
| Police logo         | **Playfair Display** — uniquement pour "YELEN SCHOOL"   |
| Police matricules   | **DejaVu Sans Mono**                                    |
| CSS                 | Uniquement des classes de `yelen.css` — **zéro CSS inline** |



## Règle impression N&B

L'établissement ne dispose pas d'imprimante couleur.
Tout document imprimable (bulletin, reçu, liste, convocation) 
doit respecter les règles du skill `print-noir` :
- Zéro couleur porteuse d'information
- Palette gris : #FFFFFF / #F0F0F0 / #CCCCCC / #000000
- Police Arial, taille min 11pt
- Bordures noires visibles
- Marges ≥ 1,5 cm

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

## Structure de projet recommandée

```
yelen_school/
├── core/
│   └── models.py          # BaseModel à étendre partout
├── eleves/
├── personnel/
├── notes/
├── bulletins/
├── paiements/
├── static/
│   └── css/
│       └── yelen.css      # Source unique de toutes les classes CSS
├── templates/
├── docs/
│   └── GUIDE_UTILISATION_YELEN_SCHOOL.md
└── tests/
```

---

## Checklist avant de soumettre une réponse

- [ ] Aucune migration SQLite ni `db.sqlite3` suggérée
- [ ] Tous les nouveaux modèles héritent de `BaseModel`
- [ ] Pas de framework JS autre que HTMX
- [ ] Montants en FCFA, notes sur 20
- [ ] Matricules générés auto et non modifiables
- [ ] Fond `#0A1628`, police Outfit, zéro CSS inline
- [ ] `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` mis à jour
- [ ] Réponse terminée par `📘 Guide mis à jour — Section X` ou mention équivalente