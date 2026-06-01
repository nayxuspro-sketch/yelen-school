# ════════════════════════════════════════════════════════════════

# 🚨 INSTRUCTION PRIORITAIRE — À LIRE AVANT TOUTE EXÉCUTION 🚨

# YELEN SCHOOL — Guide d'utilisation vivant

# ════════════════════════════════════════════════════════════════

## ⚠️ CE DOCUMENT EST OBLIGATOIRE

Avant d'exécuter **toute instruction** dans ce projet, tu dois
intégrer et respecter la directive suivante sans exception.

---

## 🎯 TA MISSION PARALLÈLE : RÉDIGER ET MAINTENIR LE GUIDE D'UTILISATION

En plus de développer les fonctionnalités de YELEN SCHOOL, tu as
la responsabilité **permanente et continue** de rédiger et mettre
à jour le fichier :

📄 `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md`

Ce guide est destiné aux **utilisateurs finaux** du logiciel :
directeurs d'établissement, secrétaires, enseignants, agents de
vie scolaire, comptables et parents d'élèves au Burkina Faso.

---

## 📋 RÈGLES ABSOLUES DE RÉDACTION DU GUIDE

### 1. MISE À JOUR SYSTÉMATIQUE

À chaque fois que tu :

- Crées un nouveau module ou une nouvelle fonctionnalité
- Modifies un formulaire, un flux ou un comportement existant
- Corriges un bug qui changeait un comportement visible
- Ajoutes un nouveau rôle ou une nouvelle permission

→ Tu **DOIS immédiatement** mettre à jour le guide d'utilisation
en conséquence. Jamais après. Immédiatement.

### 2. NIVEAU DE DÉTAIL REQUIS

Chaque fonctionnalité documentée doit inclure :

- **Titre clair** de la fonctionnalité
- **Rôle(s) concerné(s)** : qui peut accéder à cette fonction ?
- **Accès** : comment y accéder dans le menu (chemin exact)
- **Description** : à quoi ça sert, en langage simple et accessible
- **Étapes numérotées** : comment l'utiliser pas à pas
- **Illustrations** : captures d'écran simulées en ASCII ou
  descriptions visuelles précises des interfaces (formulaires,
  boutons, tableaux, messages d'erreur/succès)
- **Cas d'usage concret** : exemple réel basé sur le contexte
  scolaire burkinabè
- **Points d'attention** : erreurs fréquentes, règles métier
  importantes, champs obligatoires
- **Messages système** : ce que voit l'utilisateur en cas de
  succès ou d'erreur

### 3. STRUCTURE DU GUIDE À RESPECTER

```
# Guide d'Utilisation — YELEN SCHOOL
## Version : X.X — Mis à jour le : JJ/MM/AAAA

## Table des matières (mise à jour automatique)

## 0. Introduction
   - Présentation de YELEN SCHOOL
   - Qui utilise ce logiciel ?
   - Comment naviguer dans ce guide

## 1. Connexion & Tableau de bord
## 2. Gestion des Paramètres de l'Établissement
## 3. Module Enregistrement des Élèves
## 4. Module Inscription / Réinscription
## 5. Gestion du Personnel
## 6. Agent de Vie Scolaire (AVS)
## 7. Documents Administratifs
   - Certificats de scolarité
   - Attestations
   - Cursus scolaire
   - Autorisations d'absence
   - Carte d'identité scolaire
## 8. Module Licences (Super Admin)
## 9. Statistiques et Rapports
## 10. Gestion des Comptes Utilisateurs
## 11. Questions Fréquentes (FAQ)
## 12. Glossaire
```

### 4. QUALITÉ DE LANGUE

- Rédiger en **français clair, simple et accessible**
- Éviter le jargon technique (pas de "endpoint", "payload",
  "debug", etc.)
- Utiliser les termes du contexte scolaire burkinabè :
  "élève" (pas "étudiant" au primaire), "établissement",
  "directeur", "censeur", "bulletin trimestriel", etc.
- Tutoyer l'utilisateur : "Clique sur...", "Remplis le champ..."
- Chaque action doit commencer par un **verbe à l'impératif**

### 5. FORMAT DES ILLUSTRATIONS

Puisque le guide est en Markdown, utilise ce format pour illustrer :

**Exemple de représentation d'un formulaire :**

```
┌─────────────────────────────────────────────────┐
│  📋 Enregistrement d'un Nouvel Élève             │
├─────────────────────────────────────────────────┤
│  Nom *          : [_________________________]   │
│  Prénom *       : [_________________________]   │
│  Date naissance : [JJ/MM/AAAA]  Âge : [--]      │
│  Sexe *         : ( ) Masculin  ( ) Féminin      │
│  Cycle *        : [▼ Sélectionner un cycle   ]   │
│                                                 │
│         [ Annuler ]    [ ✅ Enregistrer ]        │
└─────────────────────────────────────────────────┘
  * Champ obligatoire
```

**Exemple de message de succès :**

```
╔══════════════════════════════════════════╗
║  ✅ Succès                               ║
║  L'élève a été enregistré avec succès.  ║
║  Matricule attribué : EL-2526-00142     ║
╚══════════════════════════════════════════╝
```

---

## 🔄 CYCLE DE MISE À JOUR OBLIGATOIRE

Pour chaque tâche de développement, applique ce cycle :

```
1. Tu reçois une instruction de développement
        ↓
2. Tu développes la fonctionnalité (code)
        ↓
3. Tu mets à jour docs/GUIDE_UTILISATION_YELEN_SCHOOL.md
        ↓
4. Tu indiques dans ta réponse : "📘 Guide mis à jour — Section X"
        ↓
5. Seulement alors, ta tâche est considérée comme TERMINÉE
```

Ne considère **jamais** une tâche comme terminée si le guide
n'a pas été mis à jour en conséquence.

---

## 📊 EN-TÊTE OBLIGATOIRE DU GUIDE

Le fichier `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` doit toujours
commencer par ce bloc de métadonnées :

```markdown
---
titre: Guide d'Utilisation — YELEN SCHOOL
version_logiciel: X.X
version_guide: X.X
date_mise_a_jour: JJ/MM/AAAA
modules_documentés: [liste des modules couverts]
modules_en_attente: [liste des modules pas encore documentés]
redige_par: Agent IA — Développement YELEN SCHOOL
---
```

---

## 🏁 RAPPEL FINAL

> Ce guide d'utilisation est un livrable du projet au même titre
> que le code source. Un logiciel sans documentation accessible
> est un logiciel inutilisable pour les écoles du Burkina Faso.
>
> **Qualité du code + Qualité du guide = Livrable complet.**

# ════════════════════════════════════════════════════════════════

```


```
