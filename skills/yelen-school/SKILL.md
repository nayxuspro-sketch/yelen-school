---
name: yelen-school
description: >
  Contexte de développement pour YELEN SCHOOL, système de gestion scolaire Django
  (PostgreSQL + HTMX) pour les établissements privés du Burkina Faso. DÉCLENCHE
  CE SKILL TOUJOURS dès que la conversation touche YELEN SCHOOL ou l'un de ses
  modules — élèves, personnel, notes, bulletins, paiements, cycles scolaires,
  inscriptions — même sans mention explicite du nom du projet (ex : "ajoute une
  page d'inscription", "génère le bulletin annuel", "corrige le modèle Élève",
  "pourquoi mon matricule ne se génère pas", "le CSS de la carte élève est cassé").
  Déclenche aussi pour toute question d'architecture Django, de modèle de données,
  de test pytest, ou de design UI dans le cadre de ce projet. Ce skill contient
  les règles techniques, métier et design NON NÉGOCIABLES : les enfreindre casse
  la cohérence du produit, donc consulte-le AVANT d'écrire du code ou de répondre,
  pas après.
---

# YELEN SCHOOL — Contexte de développement

YELEN SCHOOL est un système de gestion scolaire pour les établissements privés
du Burkina Faso. Les règles de ce skill ne sont pas des préférences de style :
ce sont des contraintes produit (cohérence multi-établissements, conformité aux
usages locaux en FCFA/sur 20, identité visuelle de la marque). Les enfreindre
casse quelque chose en production, pas seulement l'esthétique du code.

## Avant de répondre

1. Identifier si la tâche touche le **code**, les **données métier**, ou le
   **design** — souvent les trois à la fois.
2. Vérifier chaque règle non négociable ci-dessous.
3. Pour le détail d'implémentation (exemples de code, schémas), ouvrir le
   fichier de référence correspondant — ne pas réinventer un pattern déjà
   défini.
4. Terminer par la mention de documentation (voir section dédiée).

## Stack technique

| Composant        | Technologie                              |
|------------------|-------------------------------------------|
| Backend          | Django 4.2                                 |
| Base de données  | PostgreSQL — **jamais SQLite**, même en dev/tests |
| Cache / files    | Redis                                      |
| Conteneurisation | Docker                                     |
| UI dynamique     | HTMX — **jamais** React, Vue, Angular       |
| PDF              | WeasyPrint                                 |
| Tests            | pytest + model_bakery, couverture ≥ 80 %   |
| IDE déclaré      | Google Antigravity                         |

→ Patterns d'implémentation détaillés (BaseModel, services, vues HTMX, tests) :
`references/architecture.md`

## Règles NON NÉGOCIABLES — résumé

| Domaine | Règle | Pourquoi |
|---|---|---|
| Modèles | Tout modèle étend `BaseModel` (`core/models.py`) | Cohérence des champs d'audit/historique sur toute la base |
| Logique métier | Jamais dans les vues — services/managers uniquement | Testabilité, réutilisation, vues HTMX restent fines |
| Matricule élève | `BF-AAAA-NNNNN`, auto-généré, non modifiable | Traçabilité officielle, conforme aux usages administratifs BF |
| Matricule personnel | `PERS-AAAA-NNNNN`, auto-généré, non modifiable | Idem |
| Âge | Toujours calculé depuis `date_naissance`, jamais saisi | Évite les incohérences de saisie |
| Cycles scolaires | `Préscolaire` / `Primaire` / `Post-primaire` / `Secondaire` | Référentiel officiel BF, ne pas inventer d'autres cycles |
| Monnaie | FCFA uniquement | Marché cible |
| Notes | Sur 20 uniquement | Système éducatif BF |
| Signataires PDF | Configurables par cycle ET par type de document | Chaque établissement a ses propres signataires |
| CSS | Classes de `yelen.css` uniquement — zéro style inline | Une seule source de vérité visuelle |
| Fond / police | `#0A1628`, police Outfit — jamais fond blanc/Arial | Identité de marque |

→ Détail, exemples de code et pièges courants pour chaque règle :
`references/regles-metier.md`

→ Charte graphique complète (couleurs, polices, structure CSS, exemples HTML) :
`references/design-system.md`

→ Arborescence de projet recommandée et rôle de chaque dossier :
`references/structure-projet.md`

## Pièges fréquents à éviter

- Proposer SQLite "juste pour tester rapidement" → toujours PostgreSQL, y compris en local.
- Mettre une condition métier (ex. calcul de moyenne, règle de passage) directement
  dans une vue ou un template → extraire vers `services.py`.
- Générer un matricule avec un champ `IntegerField` libre modifiable par l'utilisateur
  → toujours un champ en lecture seule rempli par un signal ou une méthode `save()`.
- Ajouter `style="..."` inline pour corriger un alignement rapidement → créer/réutiliser
  une classe dans `yelen.css`.
- Afficher un montant en `€` ou un chiffre brut sans le formater en FCFA.
- Charger un framework JS pour une interaction qui peut se faire en HTMX
  (`hx-get`, `hx-post`, `hx-swap`) → pas de Vue/React/Alpine non plus, sauf
  exception déjà validée par l'utilisateur.

## Règle documentation — OBLIGATOIRE

Après **chaque modification** d'un fichier `.py`, `.html` ou `.md` :

1. Mettre à jour `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` en documentant la
   fonctionnalité créée ou modifiée (quoi, pourquoi, comment l'utiliser).
2. Terminer la réponse par l'une de ces deux mentions, **mot pour mot** :
   - `📘 Guide mis à jour — Section <Nom de la section>`
   - `📘 Guide : aucune mise à jour nécessaire` *(uniquement si la modification
     n'a aucun impact utilisateur, ex. refactor interne sans changement de
     comportement)*

> ⚠️ Une tâche sans cette mention est considérée comme **incomplète**, même si
> le code livré est correct.

## Checklist avant de soumettre une réponse

- [ ] Aucune migration SQLite ni `db.sqlite3` suggérée
- [ ] Tous les nouveaux modèles héritent de `BaseModel`
- [ ] Logique métier hors des vues (services/managers)
- [ ] Pas de framework JS autre que HTMX
- [ ] Montants en FCFA, notes sur 20
- [ ] Matricules générés automatiquement et non modifiables
- [ ] Fond `#0A1628`, police Outfit, zéro CSS inline
- [ ] `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` mis à jour (ou mention explicite du contraire)
- [ ] Réponse terminée par la mention `📘 Guide ...` exacte
