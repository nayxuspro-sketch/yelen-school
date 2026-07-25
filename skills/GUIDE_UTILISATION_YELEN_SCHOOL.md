---
titre: Guide d'Utilisation — YELEN SCHOOL
version_logiciel: 4.2
version_guide: 2.6
date_mise_a_jour: 14/04/2026
modules_documentés: [accounts, parametres, inscriptions, pedagogie, finances, examens, personnel, presences, vacations, viescolaire, licences, documents, design_system, 2fa, discipline_points, convocations, circulaires, emploi_du_temps, appels_decision, qr_presences, bourses, notifications, audit_log, calendrier, modeles_sms, reunion_parents, salaires_personnel, conges_personnel, config_sms, compte_parent]
modules_en_attente: [portail_parent, transferts, api_rest]
redige_par: Agent IA — Développement YELEN SCHOOL
---

# 🎓 Guide d'Utilisation — YELEN SCHOOL
### *"Illuminer chaque parcours scolaire"*
### Version 4.2 — Avril 2026 (Guide v2.6)

---

## TABLE DES MATIÈRES

- [0. Introduction](#0-introduction)
- [1. Connexion et Tableau de Bord](#1-connexion-et-tableau-de-bord)
  - [1.6 Gestion des Comptes Utilisateurs](#16-gestion-des-comptes-utilisateurs)
  - [1.7 Double Authentification (2FA) — Activer la Sécurité Renforcée](#17-double-authentification-2fa--activer-la-sécurité-renforcée)
  - [1.8 Se Connecter avec la 2FA Activée](#18-se-connecter-avec-la-2fa-activée)
  - [1.9 Désactiver la 2FA](#19-désactiver-la-2fa)
- [2. Paramètres de l'Établissement](#2-paramètres-de-létablissement)
  - [2.17 Configuration SMS](#217-configuration-sms)
  - [2.7 Appréciations et Moyennes (Secondaire)](#27-appréciations-et-moyennes)
  - [2.10 Signataires des Documents PDF](#210-signataires-des-documents-pdf)
  - [2.11 Appréciations — Cycle Primaire](#211-appréciations-de-moyenne--cycle-primaire)
  - [2.14 Types d'Évaluation](#214-types-dévaluation)
  - [2.15 Calendrier Scolaire](#215-calendrier-scolaire)
  - [2.16 Modèles de Messages SMS](#216-modèles-de-messages-sms)
- [3. Enregistrement des Élèves](#3-enregistrement-des-élèves)
- [4. Inscription et Réinscription](#4-inscription-et-réinscription)
  - [4.5 Carte Scolaire de l'Élève](#45-carte-scolaire-de-lélève)
  - [4.7 Marquer Abandon / Annuler l'Abandon](#47-marquer-abandon--annuler-labandon)
- [5. Gestion du Personnel](#5-gestion-du-personnel)
  - [5.5 Désactiver / Réactiver un membre](#55-désactiver--réactiver-un-membre-du-personnel)
  - [5.7 Badge Personnel](#57-badge-personnel)
  - [5.9 Gestion des Salaires du Personnel](#59-gestion-des-salaires-du-personnel)
  - [5.10 Gestion des Congés du Personnel](#510-gestion-des-congés-du-personnel)
    - [Autorisation de Jouissance de Congé PDF](#autorisation-de-jouissance-de-congé-pdf)
  - [5.8 Contrat de Travail](#58-contrat-de-travail)
- [6. Scolarité et Notes](#6-scolarité-et-notes)
  - [6.1 Matières et Enseignements (regroupés par classe)](#61-configurer-les-matières-et-enseignements)
  - [6.6 Conseil de Classe](#66-conseil-de-classe)
  - [6.7 Bulletins Trimestriels PDF](#67-bulletins-trimestriels-pdf)
  - [6.8 Moyennes par Discipline](#68-moyennes-par-discipline)
- [7. Présences et Absences](#7-présences-et-absences)
  - [7.3 Justifications d'absences](#73-justifications-dabsences)
  - [7.4 Bilan des présences par élève](#74-bilan-des-présences-par-élève)
  - [7.5 Pointage par QR Code](#75-pointage-par-qr-code)
- [8. Vie Scolaire](#8-vie-scolaire)
  - [8.2 Activités Parascolaires](#82-activités-parascolaires)
  - [8.3 Participation des Élèves](#83-participation-des-élèves-aux-activités)
  - [8.4 Capital de Points Discipline](#84-capital-de-points-discipline)
  - [8.5 Configuration du Système de Points](#85-configuration-du-système-de-points)
  - [8.6 Appels de Décision du Conseil de Classe](#86-appels-de-décision-du-conseil-de-classe)
- [9. Finances et Scolarité](#9-finances-et-scolarité)
  - [9.2 Tableau de bord financier](#92-tableau-de-bord-financier)
  - [9.4 Échéancier de Paiement](#94-gérer-un-échéancier-de-paiement)
  - [9.6 Reçu de paiement PDF](#96-imprimer-un-reçu-de-paiement-pdf)
  - [9.7 Historique des versements PDF](#97-historique-des-versements-pdf)
  - [9.8 Liste des Élèves Redevables](#98-liste-des-élèves-redevables)
  - [9.9 Bilan des Encaissements](#99-bilan-des-encaissements)
  - [9.10 Certificat de Non-Redevabilité](#910-certificat-de-non-redevabilité)
  - [9.11 Relances de Paiement PDF](#911-relances-de-paiement-pdf)
  - [9.12 Élèves Exonérés de Paiement](#912-élèves-exonérés-de-paiement)
  - [9.13 Bourses et Aides Financières](#913-bourses-et-aides-financières)
- [10. Examens](#10-examens)
  - [10.5 Liste des Candidats — Filtre par Centre](#105-liste-des-candidats--filtre-par-centre)
- [11. Vacations](#11-vacations)
  - [11.3 Générer un Bulletin de Vacation](#113-générer-un-bulletin-de-vacation)
- [12. Documents Administratifs](#12-documents-administratifs)
  - [12.1 Certificat de Scolarité](#121-certificat-de-scolarité)
  - [12.2 Attestation de Fréquentation](#122-attestation-de-fréquentation)
  - [12.3 Relevé de Notes / Cursus Scolaire](#123-relevé-de-notes--cursus-scolaire)
  - [12.4 Autorisation d'Absence](#124-autorisation-dabsence)
  - [12.5 Carte d'Identité Scolaire](#125-carte-didentité-scolaire)
  - [12.6 Liste Alphabétique d'une Classe](#126-liste-alphabétique-dune-classe-pdf)
  - [12.7 Liste du Personnel](#127-liste-du-personnel-pdf)
  - [12.8 Accès aux Documents Archivés](#128-accès-aux-documents-archivés)
  - [12.9 Archivage et Consultation](#129-archivage-et-consultation-des-documents-générés)
  - [12.10 Codes QR dans les documents](#1210-codes-qr-dans-les-documents-générés)
  - [12.11 Convocations](#1211-convocations)
  - [12.12 Circulaires](#1212-circulaires)
  - [12.13 Attestation de Non-Redevabilité](#1213-attestation-de-non-redevabilité)
- [13. Gestion des Licences](#13-gestion-des-licences-super-admin-uniquement)
- [14. Statistiques et Rapports](#14-statistiques-et-rapports)
  - [14.4 Emploi du Temps](#144-emploi-du-temps)
- [15. Fonctionnalités à Venir](#15-fonctionnalités-à-venir-)
- [16. Questions Fréquentes (FAQ)](#16-questions-fréquentes-faq)
- [17. Glossaire](#17-glossaire)
- [18. Design System et Interface](#18-design-system-et-interface)
  - [18.1 Principes de Design YELEN SCHOOL](#181-principes-de-design-yelen-school)
  - [18.2 Fonctionnement Hors Ligne](#182-fonctionnement-hors-ligne-complet)
  - [18.3 Design System v4 — Refonte Aura](#183-design-system-v4--refonte-aura)
  - [18.4 Guide Administrateur Technique](#184-guide-administrateur-technique)
  - [18.5 Système de Notifications](#185-système-de-notifications)
  - [18.6 Journal d'Audit (Traçabilité)](#186-journal-daudit-traçabilité)
  - [18.7 Réunion de Parents](#187-réunion-de-parents)

---

## 0. INTRODUCTION

### 0.1 Présentation de YELEN SCHOOL

YELEN SCHOOL est un logiciel de gestion scolaire conçu spécifiquement pour les établissements d'enseignement du **Burkina Faso**. Le mot « Yelen » signifie *lumière* en bambara — une métaphore du savoir qui éclaire chaque élève.

Ce logiciel te permet de gérer, depuis un seul endroit :

- L'enregistrement et le suivi des élèves
- Les inscriptions et réinscriptions annuelles
- Les notes, évaluations et moyennes
- Les paiements de scolarité en FCFA
- Les présences et absences
- Le personnel enseignant et administratif
- Les documents officiels (certificats, attestations, bulletins)
- La vie scolaire (disciplines, sanctions, activités)

YELEN SCHOOL est développé par et pour le contexte burkinabè. Il respecte les cycles scolaires, les nomenclatures et les pratiques administratives en vigueur au Burkina Faso.

---

### 0.2 Les 4 Cycles Scolaires Couverts

| Cycle | Niveaux | Diplôme visé |
|-------|---------|--------------|
| **Préscolaire** | Petite Section, Moyenne Section, Grande Section | — |
| **Primaire** | CP1, CP2, CE1, CE2, CM1, CM2 | CEP |
| **Post-primaire** | 6ème, 5ème, 4ème, 3ème | BEPC |
| **Secondaire** | 2nde, 1ère, Terminale | BAC |

---

### 0.3 Les 9 Profils Utilisateurs

| Profil | Rôle | Accès principal |
|--------|------|-----------------|
| **Super Admin** | Administrateur technique de la plateforme | Tout + gestion des licences |
| **Directeur** | Directeur d'établissement (Primaire/Post-primaire) | Tous les modules |
| **Proviseur** | Proviseur de lycée (Secondaire) | Tous les modules |
| **Censeur** | Censeur de lycée | Vie scolaire, emploi du temps |
| **Secrétaire** | Secrétariat de l'établissement | Inscriptions, documents, finances |
| **Enseignant** | Professeur | Ses matières, notes, présences |
| **Comptable** | Gestionnaire financier | Finances uniquement |
| **Agent de Vie Scolaire (AVS)** | Surveillance et discipline | Présences, vie scolaire |
| **Parent** | Père ou mère d'élève | Consultation uniquement *(à venir)* |

---

### 0.4 Comment Lire et Naviguer dans ce Guide

Ce guide est organisé **par module**. Chaque section suit le même schéma :

1. **À quoi ça sert** — l'objectif du module en une phrase
2. **Qui peut l'utiliser** — les rôles autorisés
3. **Comment y accéder** — le chemin dans le menu
4. **Les étapes** — numérotées et détaillées
5. **Une illustration** — représentation de l'écran en ASCII
6. **Un cas concret** — exemple burkinabè réel
7. **Les messages système** — ce que tu vois si tout va bien, et si ça ne va pas

> **Astuce :** Si tu cherches une fonction précise, utilise la table des matières ci-dessus pour aller directement à la bonne section.

---

### 0.5 Lexique des Termes Utilisés

| Terme | Définition |
|-------|-----------|
| **Matricule** | Identifiant unique d'un élève ou d'un agent, attribué automatiquement |
| **Rubrique** | Catégorie de frais (scolarité, inscription, cantine…) |
| **Tarif** | Montant en FCFA associé à une rubrique, selon la classe et le statut |
| **Cycle** | Niveau d'enseignement (Préscolaire, Primaire, Post-primaire, Secondaire) |
| **Année scolaire** | Période officielle d'enseignement (ex : 2025-2026) |
| **Inscription** | Acte d'enregistrement d'un élève dans une classe pour une année scolaire |
| **Réinscription** | Reconducton d'un élève dans l'établissement pour une nouvelle année |
| **AVS** | Agent de Vie Scolaire — surveille la discipline et les présences |
| **FCFA** | Franc CFA — monnaie officielle du Burkina Faso |
| **CEP** | Certificat d'Études Primaires |
| **BEPC** | Brevet d'Études du Premier Cycle |
| **BAC** | Baccalauréat |
| **Feature flag** | Option activée ou désactivée selon le niveau de licence de l'établissement |
| **PDF/A** | Format PDF archivable et non modifiable utilisé pour les documents officiels |
| **Relance** | Coupon A5 imprimable rappelant à une famille qu'un reste à payer est dû sur une rubrique donnée |

---

## 1. CONNEXION ET TABLEAU DE BORD

### 1.1 Accès à l'Application

YELEN SCHOOL fonctionne dans ton navigateur web. L'adresse dépend de ton installation :

- **Réseau local** : `http://192.168.X.X:8000` (adresse fournie par ton administrateur)
- **Internet** : `https://[nom-etablissement].yelenscnool.bf` *(si hébergé)*

> YELEN SCHOOL est conçu pour fonctionner **hors ligne** sur un réseau local. Tu n'as pas besoin d'une connexion internet si le serveur est installé dans ton établissement.

---

### 1.2 Écran de Connexion

Ouvre ton navigateur et saisis l'adresse du logiciel. Tu arrives sur la page de connexion :

```
╔════════════════════════════════════════════════════════════════════════╗
║  ┌──────────────────────────────────────────────────────────────────┐ ║
║  │  🎓  YELEN SCHOOL                                               │ ║
║  │                                                                  │ ║
║  │  Gérez votre établissement                                       │ ║
║  │  en toute simplicité                                            │ ║
║  │                                                                  │ ║
║  │  ✓ Notes & Bulletins    ✓ Paiements & Finances                 │ ║
║  │  ✓ Présences & Discipline ✓ Documents & Certificats              │ ║
║  │                                                                  │ ║
║  │  ──────── Cycles ──────── Profils ──────── Hors ligne ───────   │ ║
║  │       4                 9                100%                   │ ║
║  └──────────────────────────────────────────────────────────────────┘ ║
║                                                                        ║
║                        Bon retour                                      ║
║              Entrez vos identifiants pour continuer                    ║
║                                                                        ║
║    ┌────────────────────────────────────────────────────────────┐     ║
║    │  📧  exemple@ecole.bf                                     │     ║
║    └────────────────────────────────────────────────────────────┘     ║
║                                                                        ║
║    ┌────────────────────────────────────────────────────────────┐     ║
║    │  🔒  ••••••••••                                   👁       │     ║
║    └────────────────────────────────────────────────────────────┘     ║
║                                                                        ║
║    □ Se souvenir de moi          Mot de passe oublié ?                 ║
║                                                                        ║
║    ┌────────────────────────────────────────────────────────────┐     ║
║    │              Se connecter                          →        │     ║
║    └────────────────────────────────────────────────────────────┘     ║
║                                                                        ║
║              ───────── Accès rapide ─────────                         ║
║    ┌──────────┐  ┌──────────┐  ┌──────────┐                          ║
║    │ 👤       │  │ 📄       │  │ 🎓       │                          ║
║    │Directeur │  │Secrétaire│  │Enseignant│                          ║
║    └──────────┘  └──────────┘  └──────────┘                          ║
║                                                                        ║
║                    Burkina Faso · v4.2                                 ║
╚════════════════════════════════════════════════════════════════════════╝
```

**Design Clean :**
- Layout deux panneaux : branding à gauche, formulaire à droite
- Palette professionnelle : fond `#0A1628`, accent vert `#00A86B`
- Icônes SVG inline (aucune dépendance externe)
- Champs avec feedback visuel au focus
- Bouton avec animation de survol
- Accès rapides pour tester les profils

**Étapes :**

1. Saisis ton **adresse e-mail** (fournie par l'administrateur)
2. Saisis ton **mot de passe**
3. Clique sur **Se connecter**
4. Option : utilise les **accès rapides** en bas pour tester

---

### 1.3 Tableau de Bord selon le Rôle

Une fois connecté, le tableau de bord s'adapte à ton rôle :

**Tableau de bord — Directeur / Proviseur**

```
╔══════════════════════════════════════════════════════════════════╗
║  🎓 YELEN SCHOOL              Lycée Zinda — Ouagadougou          ║
║  Année scolaire : 2025-2026   Bienvenue, M. KONÉ Seydou          ║
╠═══════════════╦═══════════════╦══════════════╦═══════════════════╣
║  👨‍🎓 Élèves    ║  👥 Personnel  ║  💰 Finances  ║  📋 Documents     ║
║     847        ║      42        ║   2 415 000  ║      156          ║
║  inscrits      ║  membres       ║  FCFA perçus ║  générés          ║
╠═══════════════╩═══════════════╩══════════════╩═══════════════════╣
║  Menu principal :                                                ║
║  [Paramètres] [Élèves] [Inscriptions] [Notes] [Présences]        ║
║  [Finances]   [Examens] [Personnel]   [Documents] [Licences]     ║
╚══════════════════════════════════════════════════════════════════╝
```

**Tableau de bord — Enseignant**

```
╔══════════════════════════════════════════════════════════════════╗
║  🎓 YELEN SCHOOL              Bienvenue, M. TRAORÉ Ibrahim        ║
╠══════════════════════════════════════════════════════════════════╣
║  Mes classes aujourd'hui :   Terminale A · 1ère C · 2nde B       ║
║  Mes notes à saisir :        18 élèves en attente (3ème B)       ║
║  Prochain cours :            Mathématiques — 08h00 — Salle 4     ║
╠══════════════════════════════════════════════════════════════════╣
║  [Mes Classes] [Saisir Notes] [Présences] [Mon Profil]           ║
╚══════════════════════════════════════════════════════════════════╝
```

---

### 1.4 Changer de Mot de Passe

1. Clique sur ton **nom** en haut à droite du tableau de bord
2. Sélectionne **Mon Profil**
3. Clique sur **Changer le mot de passe**
4. Saisis ton ancien mot de passe, puis le nouveau (deux fois)
5. Clique sur **Enregistrer**

> **Règle de sécurité :** Choisis un mot de passe d'au moins 8 caractères mélangeant lettres et chiffres. Ne le communique à personne.

---

### 1.5 Se Déconnecter

Clique sur ton **nom** en haut à droite, puis sur **Se déconnecter**.

> **Attention :** Déconnecte-toi toujours avant de quitter ton poste, surtout sur un ordinateur partagé.

### 1.6 Gestion des Comptes Utilisateurs

#### Créer un Compte Parent

**À quoi ça sert :** Crée un compte pour un parent ou tuteur d'élève. Ce compte permet au parent de recevoir les notifications d'absence, de bulletin, et d'accéder au portail parent.

**Qui peut accéder :** Super Admin, Directeur

**Accès :** `Menu → Utilisateurs → Compte parent`

**Étapes :**

1. Clique sur **Utilisateurs** dans le menu
2. Clique sur le bouton **Compte parent** (à côté de "Nouvel utilisateur")
3. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  👤 Créer un compte parent                                    │
├──────────────────────────────────────────────────────────────┤
│  Nom *                 : [TRAORÉ_________________________]  │
│  Prénom *              : [Aïcha____________________________] │
│  Email *               : [aicha.traore@email.bf___________] │
│  Téléphone              : [+226 70 XX XX XX________________] │
│                                                              │
│  ───────────────────── Mot de passe ─────────────────────    │
│  Mot de passe *        : [••••••••••••••••••••••••]          │
│  Confirmer *           : [••••••••••••••••••••••••]          │
│                                                              │
│  ─────────────────── Élèves liés ────────────────────       │
│  Cochez les enfants de ce parent :                           │
│  ☑ SAWADOGO Aminata — Terminale A                           │
│  ☐ OUÉDRAOGO Boureima — Terminale C                         │
│                                                              │
│          [ Annuler ]    [ Créer le compte parent ]           │
└──────────────────────────────────────────────────────────────┘
```

4. Clique sur **Créer le compte parent**

**Important :** Pour que le parent reçoive les notifications d'absence, cochez impérativement ses enfants dans la section "Élèves liés". Sans cette liaison, les notifications ne seront pas envoyées.

#### Gérer les Utilisateurs

1. Liste des utilisateurs : `Menu → Utilisateurs`
2. Filtrer par rôle (Directeur, Enseignant, Parent, etc.)
3. Modifier un utilisateur : cliquer sur son nom
4. Désactiver/Activer : icône à côté du nom

---

### 1.7 Double Authentification (2FA) — Activer la Sécurité Renforcée

**À quoi ça sert :** La double authentification ajoute une deuxième vérification à la connexion. En plus de ton mot de passe, le système te demande un code à 6 chiffres généré par une application sur ton téléphone. Même si quelqu'un connaît ton mot de passe, il ne peut pas accéder à ton compte sans ton téléphone.

**Qui peut l'utiliser :** Tous les profils

**Accès :** `Mon Profil → Double authentification (2FA)`

#### Étape 1 — Installer une application d'authentification

Installe l'une de ces applications sur ton téléphone (disponibles gratuitement) :
- **Google Authenticator** (Android / iPhone)
- **Authy** (Android / iPhone)
- **Microsoft Authenticator** (Android / iPhone)

#### Étape 2 — Activer la 2FA depuis ton profil

1. Connecte-toi à YELEN SCHOOL normalement
2. Clique sur ton **nom** en haut à droite → **Mon Profil**
3. Fais défiler jusqu'à la section **Double authentification (2FA)**
4. Clique sur **Activer la 2FA**

```
┌──────────────────────────────────────────────────────────────┐
│  🔐 Double authentification (2FA)              [Désactivée]  │
├──────────────────────────────────────────────────────────────┤
│  La double authentification ajoute une couche de sécurité.  │
│  Un code temporaire te sera demandé à chaque connexion.      │
│                                                              │
│                   [ Activer la 2FA ]                         │
└──────────────────────────────────────────────────────────────┘
```

5. La page **Configuration 2FA** s'ouvre avec un QR code

#### Étape 3 — Scanner le QR code

```
┌──────────────────────────────────────────────────────────────┐
│  Configuration de l'application d'authentification           │
├──────────────────────────────────────────────────────────────┤
│  ① Installe Google Authenticator ou Authy                    │
│                                                              │
│  ② Scanne ce QR code avec ton application :                  │
│                                                              │
│              ┌─────────────────────┐                         │
│              │  ▓▓▓ ░░ ▓▓▓ ░ ▓▓▓  │                         │
│              │  ▓ ░ ▓░░░░▓▓░▓▓ ░  │                         │
│              │  ▓▓▓ ░ ▓░░░▓ ░░ ▓  │  ← QR code              │
│              │  ░ ▓░▓▓▓░░▓░▓▓▓▓▓  │                         │
│              │  ▓▓▓ ░ ░▓▓▓░░ ▓▓▓  │                         │
│              └─────────────────────┘                         │
│                                                              │
│  Ou saisis ce code manuellement :  JBSWY3DPEHPK3PXP          │
│                                                              │
│  ③ Saisis le code à 6 chiffres affiché par l'application :   │
│  Code *  : [______]                                          │
│                                                              │
│         [ Annuler ]    [ ✅ Activer la 2FA ]                  │
└──────────────────────────────────────────────────────────────┘
```

6. Ouvre ton application d'authentification
7. Appuie sur **+** ou **Scanner un QR code**
8. Pointe l'appareil photo sur le QR code affiché
9. L'application ajoute un compte **YELEN SCHOOL** et affiche un code à 6 chiffres renouvelé toutes les 30 secondes
10. Saisis ce code dans le champ **Code à 6 chiffres**
11. Clique sur **Activer la 2FA**

**Message succès :**
```
╔══════════════════════════════════════════════════╗
║  ✅ Double authentification activée avec succès  ║
║  Ta connexion est désormais protégée par 2FA.    ║
╚══════════════════════════════════════════════════╝
```

> **Important :** Note ou photographie le code manuel (`JBSWY3D...`) affiché lors de la configuration. Si tu perds ton téléphone, c'est le seul moyen de reconfigurer l'accès. Conserve-le dans un endroit sûr.

---

### 1.7 Se Connecter avec la 2FA Activée

Une fois la 2FA activée, chaque connexion se déroule en deux étapes :

**Étape 1 — Email et mot de passe (inchangé)**

```
╔══════════════════════════════════════════════════════╗
║              🎓  YELEN SCHOOL                        ║
╠══════════════════════════════════════════════════════╣
║  Adresse email  : [directeur@lyceezinda.bf________]  ║
║  Mot de passe   : [••••••••••••••••••••••]            ║
║           [ 🔐  Se connecter ]                       ║
╚══════════════════════════════════════════════════════╝
```

**Étape 2 — Code de vérification**

Après validation de l'email et du mot de passe, tu arrives sur un deuxième écran :

```
╔══════════════════════════════════════════════════════╗
║              🎓  YELEN SCHOOL                        ║
╠══════════════════════════════════════════════════════╣
║          🔒  Double authentification                 ║
║                                                      ║
║  Ouvre ton application (Google Authenticator…)       ║
║  et saisis le code affiché pour YELEN SCHOOL :       ║
║                                                      ║
║  Code de vérification *  : [______]                  ║
║                    (code valable 30 secondes)        ║
║                                                      ║
║              [ ✅ Vérifier ]                          ║
║                                                      ║
║              ← Revenir à la connexion                ║
╚══════════════════════════════════════════════════════╝
```

1. Ouvre **Google Authenticator** (ou Authy) sur ton téléphone
2. Trouve le compte **YELEN SCHOOL**
3. Saisis les **6 chiffres** affichés (exemple : `482 917`)
4. Clique sur **Vérifier**

> **Délai :** Le code change toutes les 30 secondes. Si le code expire pendant ta saisie, attends le prochain code.

**En cas d'erreur :**
```
╔══════════════════════════════════════════════════════╗
║  ❌ Erreur                                           ║
║  Code incorrect ou expiré. Réessayez.                ║
╚══════════════════════════════════════════════════════╝
```

---

### 1.8 Désactiver la 2FA

Si tu n'utilises plus la double authentification (ex : changement de téléphone) :

1. Connecte-toi à YELEN SCHOOL (avec la 2FA si elle est active)
2. Va dans **Mon Profil → Double authentification (2FA)**
3. La section indique **[Activée]** avec un badge vert

```
┌──────────────────────────────────────────────────────────────┐
│  🔐 Double authentification (2FA)              [Activée ✓]   │
├──────────────────────────────────────────────────────────────┤
│  Ton compte est protégé par une application TOTP.            │
│  Un code à 6 chiffres est demandé à chaque connexion.        │
│                                                              │
│  Code de confirmation  : [______]  [ Désactiver ]            │
└──────────────────────────────────────────────────────────────┘
```

4. Saisis le code actuel de ton application dans le champ
5. Clique sur **Désactiver**
6. Confirme dans la boîte de dialogue

> **Attention :** Après désactivation, seul ton mot de passe protège ton compte. Réactive la 2FA dès que possible si tu changes de téléphone.

---

## 2. PARAMÈTRES DE L'ÉTABLISSEMENT

> **Qui peut accéder :** Directeur, Proviseur, Super Admin
>
> **Accès menu :** `Menu principal → Paramètres`
>
> **À configurer en premier**, avant tout autre module. Tous les autres modules dépendent de ces paramètres.

---

### 2.1 Identité de l'Établissement

**À quoi ça sert :** Enregistre les informations officielles de ton école (nom, adresse, logo, signature du directeur). Ces informations apparaissent sur tous les documents officiels générés.

**Accès :** `Paramètres → Identité de l'établissement`

**Étapes :**

1. Clique sur **Paramètres** dans le menu principal
2. Clique sur **Identité de l'établissement**
3. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  🏫 Identité de l'Établissement                              │
├──────────────────────────────────────────────────────────────┤
│  Nom officiel *        : [Lycée Zinda__________________]     │
│  Sigle                 : [LZ_____________________________]   │
│  Type d'établissement  : [▼ Lycée d'Enseignement Général]    │
│  Région *              : [▼ Centre________________________]  │
│  Province              : [Kadiogo________________________]   │
│  Ville *               : [Ouagadougou___________________]    │
│  Quartier              : [Zogona_________________________]   │
│  Boîte postale         : [BP 1234________________________]   │
│  Téléphone *           : [+226 25 XX XX XX_______________]   │
│  Email                 : [contact@lyceezinda.bf__________]   │
│  Ministère de tutelle  : [▼ MENA_________________________]   │
│                                                              │
│  Nom du directeur *    : [KONÉ Seydou_____________________]  │
│  Logo (image)          : [📎 Choisir un fichier]             │
│  Signature directeur   : [📎 Choisir un fichier]             │
│  Cachet officiel       : [📎 Choisir un fichier]             │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
  * Champ obligatoire
```

4. Clique sur **Enregistrer**

**Cas concret :** Le Lycée Zinda de Ouagadougou saisit son nom complet « Lycée Zinda », sa ville « Ouagadougou », son directeur « M. KONÉ Seydou » et importe son logo en format PNG.

**Message succès :**
```
╔══════════════════════════════════════════════════════╗
║  ✅ Identité de l'établissement enregistrée          ║
║  Lycée Zinda — Ouagadougou                           ║
║  Ces informations apparaîtront sur vos documents.    ║
╚══════════════════════════════════════════════════════╝
```

---

### 2.2 Gestion des Cycles et Classes

**À quoi ça sert :** Définit les cycles et les classes de ton établissement.

**Accès :** `Paramètres → Cycles et Classes`

#### Créer un Cycle

1. Clique sur **Paramètres → Cycles**
2. Clique sur **+ Nouveau cycle**
3. Choisis dans la liste : Préscolaire, Primaire, Post-primaire ou Secondaire
4. Indique si ce cycle est **actif** dans ton établissement
5. Clique sur **Enregistrer**

#### Créer une Classe

1. Clique sur **Paramètres → Classes**
2. Clique sur **+ Nouvelle classe**

```
┌──────────────────────────────────────────────────────────────┐
│  📚 Nouvelle Classe                                          │
├──────────────────────────────────────────────────────────────┤
│  Nom de la classe *     : [Terminale A_____________________] │
│  Cycle *                : [▼ Secondaire____________________] │
│  Capacité maximale      : [60______________________________] │
│  Classe d'examen ?      : (●) Oui — BAC  ( ) Non            │
│  Actif                  : (●) Oui  ( ) Non                   │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

3. Clique sur **Enregistrer**

**Exemples de classes à créer :**

| Cycle | Classes |
|-------|---------|
| Primaire | CP1, CP2, CE1, CE2, CM1, CM2 |
| Post-primaire | 6ème A, 6ème B, 5ème A, 4ème A, 3ème A |
| Secondaire | 2nde A, 2nde B, 1ère A, 1ère C, Tle A, Tle C |

---

### 2.3 Postes et Fonctions

**À quoi ça sert :** Liste les postes occupés par le personnel de l'établissement (Directeur, Censeur, Enseignant, AVS, Comptable…).

**Accès :** `Paramètres → Postes`

**Étapes :**

1. Clique sur **+ Nouveau poste**

```
┌──────────────────────────────────────────────────────────────┐
│  👔 Nouveau Poste                                            │
├──────────────────────────────────────────────────────────────┤
│  Intitulé du poste *    : [Censeur_________________________] │
│  Catégorie              : [▼ Administration________________]  │
│  Description            : [Chargé de la discipline...____]   │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

2. Clique sur **Enregistrer**

**Postes à créer pour un lycée type :**
- Proviseur, Censeur, Directeur des études
- Enseignant, Professeur principal
- Secrétaire principal, Comptable
- Agent de Vie Scolaire (AVS), Surveillant
- Bibliothécaire, Infirmier

---

### 2.4 Statuts des Élèves

**À quoi ça sert :** Définit les différents statuts qu'un élève peut avoir (Affecté, Non affecté, Boursier, Exonéré, Redoublant, Nouveau…). Ces statuts déterminent les tarifs de scolarité applicables.

**Accès :** `Paramètres → Statuts des élèves`

**Étapes :**

1. Clique sur **+ Nouveau statut**

```
┌──────────────────────────────────────────────────────────────┐
│  🏷️ Nouveau Statut Élève                                     │
├──────────────────────────────────────────────────────────────┤
│  Libellé *              : [Boursier_______________________]  │
│  Code                   : [BOURSIER_______________________]  │
│  Description            : [Élève bénéficiant d'une bourse]   │
│  Actif                  : (●) Oui  ( ) Non                   │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

2. Clique sur **Enregistrer**

**Statuts standards :**
- Nouveau élève
- Redoublant
- Affecté (par le MENA)
- Non affecté
- Boursier
- Exonéré

---

### 2.5 Rubriques et Tarifs de Scolarité (FCFA)

**À quoi ça sert :** Définit les types de frais perçus par l'établissement et leurs montants selon la classe et le statut de l'élève. Tous les montants sont en **FCFA**.

**Accès :** `Paramètres → Rubriques et Tarifs`

#### Créer une Rubrique de Paiement

1. Clique sur **+ Nouvelle rubrique**

```
┌──────────────────────────────────────────────────────────────┐
│  💰 Nouvelle Rubrique de Paiement                            │
├──────────────────────────────────────────────────────────────┤
│  Libellé *              : [Frais de scolarité______________] │
│  Code                   : [SCOLARITE______________________]  │
│  Obligatoire            : (●) Oui  ( ) Non                   │
│  Description            : [Frais annuels de scolarité____]   │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Rubriques courantes :**
- Frais de scolarité (SCOLARITE)
- Frais d'inscription (INSCRIPTION)
- Frais de cantine (CANTINE)
- Frais de transport (TRANSPORT)
- Association des parents (APE)
- Frais d'examen (EXAMEN)

#### Définir un Tarif

Les tarifs sont définis par **niveau** (5ème, 6ème…) et par **statut d'élève**. Un tarif configuré pour le niveau « 5ème » s'applique automatiquement à **toutes les classes de ce niveau** (5ème A, 5ème B, etc.).

1. Clique sur **Tarifs de scolarité**
2. Clique sur **+ Nouveau tarif**

```
┌──────────────────────────────────────────────────────────────┐
│  💵 Nouveau Tarif                                            │
├──────────────────────────────────────────────────────────────┤
│  Année scolaire *       : [▼ 2025-2026____________________] │
│  Cycle                 : [▼ Post-primaire__________________]  │
│  Niveau *              : [▼ 5ème__________________________]  │
│  Statut élève *        : [▼ Non affecté__________________]   │
│  Rubrique *            : [▼ Frais de scolarité___________]   │
│  Montant (FCFA) *      : [45 000_________________________]  │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Points clés :**

- **Par niveau** : Le tarif s'applique à toutes les classes du même niveau (5ème A, 5ème B → même tarif « 5ème »)
- **Par statut** : Affecté, Non affecté, Boursier, Exonéré peuvent avoir des montants différents
- **La liste des tarifs est regroupée par niveau** pour faciliter la lecture
- **Montant à saisir manuellement** : Le champ Montant est vide à la création — saisis la valeur en FCFA. Il n'est pas pré-rempli automatiquement depuis la rubrique.

**Cas concret — Lycée Zinda :**

| Cycle | Niveau | Statut | Rubrique | Montant |
|-------|--------|--------|----------|---------|
| Post-primaire | 6ème | Non affecté | Scolarité | 40 000 FCFA |
| Post-primaire | 6ème | Affecté | Scolarité | 25 000 FCFA |
| Post-primaire | 5ème | Non affecté | Scolarité | 45 000 FCFA |
| Secondaire | Terminale | Non affecté | Scolarité | 75 000 FCFA |
| Secondaire | Terminale | Boursier | Scolarité | 0 FCFA |

---

### 2.6 Année Scolaire (Ouverture / Fermeture)

**À quoi ça sert :** Gère l'année scolaire en cours et les périodes d'évaluation associées.

**Accès :** `Paramètres → Année scolaire`

#### Ouvrir une Nouvelle Année Scolaire

1. Clique sur **+ Nouvelle année scolaire**

```
┌──────────────────────────────────────────────────────────────┐
│  📅 Nouvelle Année Scolaire                                  │
├──────────────────────────────────────────────────────────────┤
│  Libellé *              : [2025-2026______________________]  │
│  Date de début *        : [01/10/2025]                       │
│  Date de fin prévue *   : [30/06/2026]                       │
│  Statut                 : (●) En cours  ( ) Fermée           │
│                                                              │
│          [ Annuler ]    [ ✅ Ouvrir l'année ]                │
└──────────────────────────────────────────────────────────────┘
```

> **Attention :** Une seule année scolaire peut être **En cours** à la fois. Avant d'ouvrir une nouvelle année, assure-toi de clore l'année précédente.

#### Fermer une Année Scolaire

1. Clique sur l'année en cours
2. Clique sur **Fermer l'année scolaire**
3. Confirme la fermeture

```
╔══════════════════════════════════════════════════════════╗
║  ⚠️  Confirmation de Fermeture                           ║
║  Tu vas fermer l'année scolaire 2024-2025.               ║
║  Cette action est irréversible.                          ║
║                                                          ║
║       [ Annuler ]    [ ✅ Confirmer la fermeture ]       ║
╚══════════════════════════════════════════════════════════╝
```

---

### 2.7 Appréciations et Moyennes

**À quoi ça sert :** Configure les grilles d'appréciations (Excellent, Très Bien, Bien, Assez Bien, Passable, Insuffisant) associées aux intervalles de moyennes. Ces appréciations s'affichent sur les bulletins.

**Accès :** `Paramètres → Appréciations`

**Étapes :**

1. Clique sur **+ Nouvelle appréciation**

```
┌──────────────────────────────────────────────────────────────┐
│  🌟 Nouvelle Appréciation                                    │
├──────────────────────────────────────────────────────────────┤
│  Libellé *              : [Excellent______________________]  │
│  Moyenne minimale *     : [16.00]                            │
│  Moyenne maximale *     : [20.00]                            │
│  Cycle *                : [▼ Secondaire____________________] │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Grille d'appréciations standard (Secondaire) :**

| Intervalle | Appréciation |
|-----------|--------------|
| 16 – 20 | Excellent |
| 14 – 15.99 | Très Bien |
| 12 – 13.99 | Bien |
| 10 – 11.99 | Assez Bien |
| 8 – 9.99 | Passable |
| 0 – 7.99 | Insuffisant |

---

### 2.8 Types de Documents Officiels

**À quoi ça sert :** Configure les types de documents que l'établissement peut générer. Chaque type est identifié par un code.

**Accès :** `Paramètres → Types de documents`

**Documents pré-configurés dans YELEN SCHOOL :**

| Code | Document |
|------|----------|
| CERT_SCOL | Certificat de Scolarité |
| BULLETIN | Bulletin de Notes Trimestriel |
| RECU_PAIEMENT | Reçu de Paiement |
| AUTORISATION | Autorisation d'Absence |
| ATTESTATION | Attestation de Fréquentation |
| CURSUS | Cursus Scolaire Complet |
| CARTE_ID | Carte d'Identité Scolaire |
| LISTE_CLASSE | Liste Alphabétique de Classe |
| LISTE_PERSONNEL | Liste du Personnel |

> Ces codes sont pré-configurés. Tu peux en ajouter de nouveaux si ton établissement a des besoins spécifiques.

---

### 2.9 Types de Sanctions Disciplinaires

**À quoi ça sert :** Définit les sanctions pouvant être appliquées à un élève (Avertissement, Blâme, Exclusion temporaire, Exclusion définitive…).

**Accès :** `Paramètres → Types de sanctions`

**Étapes :**

1. Clique sur **+ Nouveau type de sanction**

```
┌──────────────────────────────────────────────────────────────┐
│  ⚠️ Nouveau Type de Sanction                                 │
├──────────────────────────────────────────────────────────────┤
│  Libellé *              : [Exclusion temporaire____________] │
│  Gravité                : [▼ Grave_______________________]   │
│  Durée maximale (jours) : [8]                                │
│  Nécessite convocation  : (●) Oui  ( ) Non                   │
│  Description            : [Exclusion du 1 à 8 jours______]   │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Sanctions courantes au Burkina Faso :**
- Avertissement (Mineur)
- Blâme (Mineur)
- Convocation des parents (Modéré)
- Travaux d'intérêt général (Modéré)
- Exclusion temporaire — 1 à 3 jours (Grave)
- Exclusion temporaire — 4 à 8 jours (Grave)
- Exclusion définitive (Très grave)

---

### 2.10 Signataires des Documents PDF

**À quoi ça sert :** Configure, pour chaque cycle et chaque type de document, quel membre du personnel signe les documents officiels. Dans un établissement multi-cycles, le Directeur du primaire signe les certificats du primaire, et le Proviseur signe ceux du secondaire.

**Accès :** `Paramètres → Signataires des documents`

**L'interface est organisée en onglets par cycle :**

```
┌──────────────────────────────────────────────────────────────┐
│  📝 Signataires des Documents                                │
├───────────────┬─────────────┬────────────────┬──────────────┤
│  [Préscolaire]│   [Primaire]│[Post-primaire] │[Secondaire ✓]│
├───────────────┴─────────────┴────────────────┴──────────────┤
│  Type de Document        │ Signataire          │ Titre       │
├──────────────────────────┼─────────────────────┼────────────┤
│  Certificat de Scolarité │ [▼ KONÉ Seydou    ] │ [M. le Pro]│
│  Bulletin de Notes       │ [▼ KONÉ Seydou    ] │ [M. le Pro]│
│  Reçu de Paiement        │ [▼ OUÉDRAOGO Aïcha] │ [Mme la Co]│
│  Autorisation d'Absence  │ [▼ TRAORÉ Moumouni] │ [M. le Cen]│
│  Attestation             │ [▼ KONÉ Seydou    ] │ [M. le Pro]│
│  Cursus Scolaire         │ [▼ KONÉ Seydou    ] │ [M. le Pro]│
│  Carte d'Identité Scol.  │ [▼ KONÉ Seydou    ] │ [M. le Pro]│
├──────────────────────────┴─────────────────────┴────────────┤
│                      [ ✅ Enregistrer les signataires ]      │
└──────────────────────────────────────────────────────────────┘
```

**Étapes :**

1. Clique sur l'onglet du cycle à configurer (ex : **Secondaire**)
2. Pour chaque type de document, sélectionne le **signataire** dans la liste déroulante
   - La liste affiche uniquement le personnel inscrit dans ce cycle pour l'année en cours
3. Remplis le **titre honorifique** (ex : M. le Proviseur, Mme la Directrice, M. le Censeur)
4. Clique sur **Enregistrer les signataires**

> **Important :** Le signataire apparaît **automatiquement sur tous les PDFs** (bulletins, certificats, listes, reçus, relances…) dès qu'il est configuré — aucune action supplémentaire n'est requise à la génération. Si aucun signataire n'est configuré pour un type de document et un cycle donnés, le bloc de signature est simplement omis du PDF.

**Rendu sur les documents PDF :**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Ouagadougou, le 10 Mars 2026                          │
│                                                         │
│   M. le Proviseur KONÉ Seydou                           │
│   Proviseur                                             │
│                                                         │
│   _____________________                                 │
│   (Signature et Cachet)                                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

### 2.11 Appréciations de Moyenne — Cycle Primaire

**À quoi ça sert :** Configure les appréciations textuelles affichées sur les bulletins du cycle Primaire (Préscolaire, Primaire), distinctes de celles du secondaire. Ex : *Excellent*, *Bien*, *Assez Bien*, *Passable*, *Insuffisant*.

**Accès :** `Paramètres → Appréciations primaire`

> **Différence avec les appréciations secondaire :** Les barèmes et libellés peuvent être différents selon le cycle. Les bulletins du primaire utilisent automatiquement ces appréciations si le cycle de la classe est Préscolaire ou Primaire.

**Champs du formulaire :**

| Champ | Description | Exemple |
|-------|-------------|---------|
| Libellé | Texte affiché sur le bulletin | Excellent |
| Moyenne min | Note minimale (sur 20) | 16.00 |
| Moyenne max | Note maximale (sur 20) | 20.00 |
| Couleur | Couleur d'affichage (hex) | #00C07A (vert) |
| Ordre | Position dans la liste | 1 |

**Barème recommandé pour le Primaire :**

| Appréciation | Moy. min | Moy. max |
|-------------|---------|----------|
| Excellent | 16.00 | 20.00 |
| Très Bien | 14.00 | 15.99 |
| Bien | 12.00 | 13.99 |
| Assez Bien | 10.00 | 11.99 |
| Passable | 8.00 | 9.99 |
| Insuffisant | 0.00 | 7.99 |

---

### 2.12 Catégories de Disciplines et Disciplines

#### 2.12.1 Catégories de Disciplines

**À quoi ça sert :** Regroupe les manquements disciplinaires par catégorie (Ex : Comportement, Assiduité, Tenue, Incivilité). Ces catégories sont utilisées dans le module Vie Scolaire lors de la saisie d'une sanction.

**Accès :** `Paramètres → Catégories de disciplines`

**Champs du formulaire :**

| Champ | Description |
|-------|-------------|
| Nom | Nom de la catégorie (ex : Comportement) |
| Code | Code court (ex : COMP) |
| Couleur | Couleur d'affichage hex pour l'interface |
| Ordre | Ordre d'affichage |

#### 2.12.2 Disciplines (Fautes Disciplinaires)

**À quoi ça sert :** Liste les fautes spécifiques pouvant être sanctionnées (Ex : Retard répété, Insolence, Fraude aux examens, Port de téléphone portable). Chaque discipline est liée à un **cycle** et une **catégorie**.

**Accès :** `Paramètres → Disciplines`

**Champs du formulaire :**

| Champ | Description |
|-------|-------------|
| Nom | Libellé de la faute (ex : Retard répété) |
| Code | Code court (ex : RETARD) |
| Cycle | Cycle concerné (Primaire, Secondaire…) |
| Catégorie | Catégorie de discipline parente |
| Est évaluée | Si coché, la discipline peut générer une note de conduite |
| Couleur | Couleur d'affichage |

> **Exemple de configuration :**
>
> | Code | Faute | Cycle | Catégorie |
> |------|-------|-------|-----------|
> | RETARD | Retard répété (≥ 3 fois) | Secondaire | Assiduité |
> | TEL | Port de téléphone en classe | Secondaire | Comportement |
> | FRAUDE | Tentative de fraude | Primaire + Secondaire | Incivilité |
> | INSOLENCE | Insolence envers un enseignant | Secondaire | Comportement |

---

### 2.13 Périodes d'Évaluation (Trimestres / Semestres)

**À quoi ça sert :** Configure le découpage de l'année scolaire en périodes d'évaluation (trimestres ou semestres). Ces périodes sont utilisées dans le module Pédagogie pour la saisie des notes et la génération des bulletins.

**Accès :** `Paramètres → Périodes d'évaluation`

**Champs du formulaire :**

| Champ | Description | Exemple |
|-------|-------------|---------|
| Nom | Libellé de la période | 1er Trimestre |
| Type de période | Trimestre ou Semestre | Trimestre |
| Numéro | Position dans l'année (1, 2, 3) | 1 |
| Année scolaire | Année scolaire concernée | 2025-2026 |
| Date de début | Début de la période | 15/09/2025 |
| Date de fin | Fin de la période | 20/12/2025 |
| Est en cours | Indique la période active | ✅ Coché |

> **Important :** La période marquée *Est en cours* est automatiquement sélectionnée lors de la saisie des notes. Il ne peut y avoir qu'une seule période en cours à la fois par année scolaire.

**Configuration typique pour un lycée burkinabè :**

| Période | Début | Fin |
|---------|-------|-----|
| 1er Trimestre | 15 Sept. | 20 Déc. |
| 2ème Trimestre | 05 Jan. | 28 Mars |
| 3ème Trimestre | 07 Avr. | 30 Juin |

---

### 2.14 Types d'Évaluation

**À quoi ça sert :** Définit les types de contrôles pratiqués dans l'établissement (Devoir sur table, Interrogation, Devoir maison, Composition trimestrielle…). Ces types sont ensuite sélectionnables lors de la planification d'une évaluation.

**Accès :** `Paramètres → Types d'évaluation`

#### Créer un Type d'Évaluation

1. Clique sur **+ Nouveau type**

```
┌──────────────────────────────────────────────────────────────┐
│  📝 Nouveau Type d'Évaluation                                │
├──────────────────────────────────────────────────────────────┤
│  Nom *                  : [Devoir sur table_______________]  │
│  Code                   : [DST__________________________]    │
│  Coefficient            : [1.00________________________]     │
│  Pondération            : [100%_________________________]    │
│  Ordre d'affichage      : [1____________________________]    │
│  Nb meilleures notes    : [— (toutes)__________________]    │
│  Visible dans bulletin  : (●) Oui  ( ) Non                   │
│  Description            : [___________________________]      │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Types courants :**

| Code | Nom | Usage |
|------|-----|-------|
| DST | Devoir sur table | Devoir surveillé en classe |
| INTERRO | Interrogation orale | Interrogation rapide |
| DM | Devoir maison | Travail à la maison |
| COMPO | Composition | Épreuve trimestrielle |
| TP | Travaux pratiques | Séances de laboratoire |

> **Lien avec Pédagogie :** Les types configurés ici sont disponibles dans le menu déroulant lors de la **planification d'une évaluation** (`Pédagogie → Planifier une évaluation → Type d'évaluation`).

---

### 2.15 Calendrier Scolaire

**À quoi ça sert :** Enregistre les événements officiels de l'année scolaire (rentrée, vacances, examens, jours fériés, réunions). Ces événements sont visibles sur le tableau de bord et permettent d'organiser l'agenda de l'établissement.

**Qui peut accéder :** Directeur, Proviseur, Secrétaire

**Accès :** `Paramètres → Calendrier scolaire`

#### Ajouter un Événement

1. Clique sur **Paramètres → Calendrier scolaire**
2. Clique sur **+ Nouvel événement** ou clique directement sur une date dans le calendrier
3. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  📅 Nouvel Événement Scolaire                                │
├──────────────────────────────────────────────────────────────┤
│  Titre *             : [Rentrée scolaire 2025-2026_________] │
│  Type *              : [▼ Événement institutionnel_________] │
│  Date de début *     : [01/10/2025]                          │
│  Date de fin         : [01/10/2025]                          │
│  Toute la journée    : (●) Oui  ( ) Non                      │
│  Description         : [Rentrée officielle des classes_____] │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

4. Clique sur **Enregistrer**

**Types d'événements :**

| Type | Exemples |
|------|----------|
| Institutionnel | Rentrée scolaire, Fête de l'indépendance |
| Vacances | Vacances de Noël, Vacances de Pâques |
| Examen | Début des compositions, Baccalauréat |
| Réunion | Conseil de classe, Réunion de parents |
| Autre | Sortie scolaire, Compétition sportive |

#### Modifier ou Supprimer un Événement

1. Clique sur l'événement dans le calendrier
2. Clique sur **Modifier** ou **Supprimer**
3. Confirme la suppression si demandé

**Cas concret :** En début d'année, la secrétaire du Lycée Zinda saisit toutes les dates importantes : rentrée (1er octobre), vacances de Noël (22 décembre au 5 janvier), compositions du 1er trimestre (15-20 janvier). Ces dates sont ensuite visibles par tous les utilisateurs connectés.

---

### 2.16 Modèles de Messages SMS

**À quoi ça sert :** Crée et gère des modèles de messages SMS réutilisables. Ces modèles servent à envoyer rapidement des messages standardisés aux parents (absence de l'enfant, retard de paiement, convocation…) sans avoir à rédiger chaque fois le texte depuis zéro.

**Qui peut accéder :** Directeur, Proviseur, Secrétaire

**Accès :** `Paramètres → Modèles de messages`

#### Créer un Modèle

1. Clique sur **Paramètres → Modèles de messages**
2. Clique sur **+ Nouveau modèle**
3. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  📱 Nouveau Modèle de Message                                │
├──────────────────────────────────────────────────────────────┤
│  Nom du modèle *      : [Absence non justifiée_____________] │
│  Type *               : [▼ Absence_______________________]   │
│  Contenu *            :                                      │
│  [Votre enfant {prenom_eleve} {nom_eleve} était absent(e)   ]│
│  [le {date_absence} au {nom_etablissement}. Veuillez vous   ]│
│  [rapprocher de l'établissement. Tél: {telephone_etab}      ]│
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Variables disponibles dans les modèles :**

| Variable | Contenu inséré |
|----------|----------------|
| `{nom_eleve}` | Nom de l'élève |
| `{prenom_eleve}` | Prénom de l'élève |
| `{nom_etablissement}` | Nom de ton école |
| `{telephone_etab}` | Téléphone de l'établissement |
| `{date_absence}` | Date de l'absence |
| `{montant_du}` | Montant restant à payer |

#### Utiliser un Modèle

Une fois créé, le modèle est disponible lors des actions nécessitant un SMS (relances de paiement, notifications d'absence). Sélectionne le modèle dans la liste déroulante et personnalise-le si besoin avant envoi.

> **Astuce :** Crée des modèles pour chaque situation courante. Le temps de rédaction est réduit et la communication devient plus professionnelle et cohérente.

### 2.17 Configuration SMS

**À quoi ça sert :** Configure la connexion à la passerelle SMS pour envoyer des notifications par SMS aux parents (absences, bulletins, relances de paiement).

**Qui peut accéder :** Super Admin, Directeur

**Accès :** `Menu → Configuration SMS`

#### Configurer la Connexion

```
┌──────────────────────────────────────────────────────────────┐
│  📱 Configuration SMS                                        │
├──────────────────────────────────────────────────────────────┤
│  Activer les SMS :    [▼ Oui — Activé / Non — Désactivé]    │
│  Backend :           [▼ HTTP — Passerelle WiFi / Série]      │
│                                                              │
│  [Configuration HTTP — Passerelle WiFi]                     │
│  URL de la passerelle : [http://192.168.1.100:8080/message] │
│  Utilisateur :         [admin______________________________]  │
│  Mot de passe :       [•••••••••••••••••••••••••]          │
│  Timeout :            [10] secondes                         │
│                                                              │
│            [ Enregistrer la configuration ]                 │
└──────────────────────────────────────────────────────────────┘
```

#### Choix du Backend

- **HTTP (WiFi)** : Utilise l'application Android "SMS Gateway" sur un téléphone连接到 le réseau WiFi local. Le téléphone doit avoir une carte SIM avec des crédits SMS.
- **Série** : Utilise un modem GSM USB连接到 le serveur.

#### Installer SMS Gateway (Android)

1. Télécharge l'application "SMS Gateway" sur un téléphone Android
2. Lance l'application — elle doit rester démarrée
3. Note l'adresse IP affichée dans Settings → Server → IP Address
4. Saisie cette IP dans le champ "URL de la passerelle" ci-dessus

#### Tester la Connexion

1. Après enregistrement, clique sur **Tester la connexion**
2. Le résultat affiche si la passerelle est joignable

#### Envoyer un SMS de Test

1. Saisie un numéro de téléphone (format : +22670123456 ou 70123456)
2. Clique sur **Envoyer**
3. Le parent reçoit un SMS de test

> **Important :** Après modification de la configuration, redémarre le serveur pour appliquer les changements.

> **Note :** Les SMS utilisent les crédits de la carte SIM du téléphone Android ou du modem GSM. Aucun frais supplémentaire n'est facturé par YELEN SCHOOL.

---

## 3. ENREGISTREMENT DES ÉLÈVES

> **Qui peut accéder :** Directeur, Proviseur, Secrétaire
>
> **Accès menu :** `Menu principal → Élèves → Enregistrement`

---

### 3.1 Créer le Dossier d'un Nouvel Élève

**À quoi ça sert :** Enregistre un élève dans le système pour la première fois. Un matricule unique lui est attribué automatiquement.

**Accès :** `Élèves → + Nouvel élève`

**Étapes :**

1. Clique sur **Élèves** dans le menu principal
2. Clique sur **+ Nouvel élève**
3. Remplis le formulaire d'enregistrement :

```
┌──────────────────────────────────────────────────────────────┐
│  📋 Enregistrement d'un Nouvel Élève                         │
├──────────────────────────────────────────────────────────────┤
│  NOM (en majuscules) *  : [SAWADOGO_______________________]  │
│  Prénom *               : [Aminata_______________________]   │
│  Date de naissance *    : [12/03/2012]   Âge : [14 ans]      │
│  Lieu de naissance *    : [Ouagadougou___________________]   │
│  Sexe *                 : (●) Féminin   ( ) Masculin         │
│                                                              │
│  ─── Informations Famille ───────────────────────────────   │
│  Nom du père            : [SAWADOGO Oumarou______________]   │
│  Profession du père     : [Commerçant____________________]   │
│  Téléphone père         : [+226 70 XX XX XX_______________]  │
│  Nom de la mère         : [SAWADOGO/KABORÉ Mariam________]   │
│  Profession de la mère  : [Ménagère______________________]   │
│  Téléphone mère         : [+226 76 XX XX XX_______________]  │
│                                                              │
│  ─── Adresse ────────────────────────────────────────────   │
│  Ville / Village *      : [Ouagadougou___________________]   │
│  Quartier               : [Pissy__________________________]  │
│  Région                 : [▼ Centre_____________________]    │
│                                                              │
│  ─── Documents ──────────────────────────────────────────   │
│  Acte de naissance      : (●) Fourni   ( ) Non fourni        │
│  Certificat médical     : ( ) Fourni   (●) Non fourni        │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
  * Champ obligatoire
```

4. Clique sur **Enregistrer**

**Message succès :**
```
╔══════════════════════════════════════════════════════╗
║  ✅ Élève enregistré avec succès                     ║
║  Matricule attribué : BF-CEN-2526-0047               ║
║  SAWADOGO Aminata — née le 12/03/2012 (14 ans)       ║
║  Lycée Zinda, Ouagadougou                            ║
╚══════════════════════════════════════════════════════╝
```

---

### 3.2 Comprendre le Matricule Élève

Le matricule est attribué **automatiquement** par le système. Il est unique pour chaque élève.

**Format : `{CODE_ETAB}-{ANNEE}-{SEQ}`**

| Partie | Signification | Exemple |
|--------|---------------|---------|
| `{CODE_ETAB}` | Code de l'établissement | 01, YSK, LYCB |
| `{ANNEE}` | Année d'enregistrement sur 4 chiffres | 2026 |
| `{SEQ}` | Numéro séquentiel sur 2 chiffres | 01, 02, ..., 99 |

**Exemples :**

| Matricule | Interprétation |
|-----------|----------------|
| `01-2026-01` | 1er élève enregistré, établissement 01, année 2026 |
| `YSK-2026-05` | 5ème élève enregistré, école YSK, année 2026 |
| `LYCB-2026-12` | 12ème élève, Lycée Bobo, année 2026 |

> **Note :** Le matricule est définitif. Il ne change pas si l'élève change de classe ou d'établissement.

---

### 3.3 Calcul Automatique de l'Âge

Quand tu saisis la date de naissance d'un élève, le système calcule et affiche **automatiquement** son âge actuel.

**Exemple :** SAWADOGO Aminata, née le 12/03/2012 → Le système affiche « **14 ans** » en temps réel.

---

### 3.4 Documents à Fournir

Selon les établissements, les documents suivants peuvent être demandés :

| Document | Primaire | Post-primaire | Secondaire |
|----------|----------|---------------|------------|
| Acte de naissance | Obligatoire | Obligatoire | Obligatoire |
| Certificat médical | Recommandé | Recommandé | Non requis |
| Photo d'identité | Recommandé | Obligatoire | Obligatoire |
| Certificat de scolarité précédent | — | Obligatoire | Obligatoire |
| Bulletins de l'année précédente | — | Recommandé | Recommandé |

---

### 3.5 Rechercher un Élève Existant

1. Clique sur **Élèves** dans le menu
2. Dans la barre de recherche, tape :
   - Le **matricule** (ex : `BF-CEN-2526-0047`)
   - Le **nom** (ex : `SAWADOGO`)
   - Le **prénom** (ex : `Aminata`)
3. Appuie sur **Entrée** ou clique sur la **loupe**

```
┌──────────────────────────────────────────────────────────────┐
│  🔍 Rechercher un élève                                      │
├──────────────────────────────────────────────────────────────┤
│  [SAWADOGO________________________________] [ 🔍 Rechercher ] │
├──────────────────────────────────────────────────────────────┤
│  Résultats (3 élèves trouvés) :                              │
│                                                              │
│  BF-CEN-2526-0047  SAWADOGO Aminata    Tle A   F  14 ans     │
│  BF-CEN-2526-0103  SAWADOGO Moussa     3ème B  M  16 ans     │
│  BF-CEN-2425-0892  SAWADOGO Fatoumata  CM2     F  12 ans     │
│                                                              │
│  [ Voir le dossier ] [ Inscrire ] pour chaque élève          │
└──────────────────────────────────────────────────────────────┘
```

---

### 3.6 Modifier le Dossier d'un Élève

1. Recherche l'élève (voir section 3.5)
2. Clique sur **Voir le dossier**
3. Clique sur **Modifier**
4. Effectue les corrections nécessaires
5. Clique sur **Enregistrer les modifications**

> **Note :** Le matricule ne peut **jamais** être modifié. Les autres champs sont modifiables par le Directeur ou la Secrétaire. La **date de naissance** est pré-remplie avec la valeur enregistrée — tu n'as pas besoin de la ressaisir sauf en cas de correction. Si tu laisses le champ tel quel, la date d'origine est conservée.

---

### 3.7 Transférer un Élève

*Interface en cours de développement.* La fonctionnalité est disponible via l'administration.

---

## 4. INSCRIPTION ET RÉINSCRIPTION

> **Qui peut accéder :** Directeur, Proviseur, Secrétaire
>
> **Accès menu :** `Menu principal → Inscriptions`

---

### 4.1 Inscrire un Élève par Matricule

**À quoi ça sert :** Rattache un élève à une classe pour l'année scolaire en cours. Le code paiement est généré automatiquement.

**Accès :** `Inscriptions → + Nouvelle inscription` (ou "Finaliser l'Inscription")

**Étapes :**

1. Clique sur **Inscriptions** dans le menu
2. Clique sur **+ Nouvelle inscription** (ou "Finaliser l'Inscription")
3. Saisis le **matricule** de l'élève :

```
┌──────────────────────────────────────────────────────────────┐
│  📝 Finaliser l'Inscription                                   │
├──────────────────────────────────────────────────────────────┤
│  Matricule élève *      : [BF-CEN-2526-0047_____________]    │
│                  → SAWADOGO Aminata — née le 12/03/2012       │
│                    Âge : 14 ans                               │
│                                                              │
│  Année scolaire *       : [▼ 2025-2026____________________] │
│  Classe *               : [▼ Terminale A__________________] │
│  Niveau                 : Terminale A    (auto)              │
│  Cycle                  : Secondaire     (auto)               │
│  Statut élève *        : [▼ Non affecté__________________] │
│  Code paiement          : Terminale A-Non affecté-Secondaire (auto) │
│  Redoublant(e) ?        : ( ) Oui  (●) Non                   │
│  Classe redoublée       : [________________________________] │
│                                                              │
│  Date de naissance      : 12/03/2012  (lecture seule)        │
│  Âge calculé            : 14 ans     (lecture seule)         │
│                                                              │
│          [ Annuler ]    [ ✅ Confirmer l'Inscription ]          │
└──────────────────────────────────────────────────────────────┘
```

4. Clique sur **Confirmer l'Inscription**

> **Fonctionnement du Code Paiement :** Le code est généré automatiquement lors de la sélection de la classe et du statut élève. Il suit le format : **Niveau-Statut_eleve-Cycle** (ex : "6eme-Non affecté-Secondaire"). Ce code permet d'identifier rapidement le tarif applicable.

> **Astuce :** Après avoir saisi le matricule, le système affiche automatiquement le nom, prénom, date de naissance et âge de l'élève. Après avoir sélectionné la classe, les champs Niveau et Cycle se remplissent automatiquement.

**Message succès :**
```
╔══════════════════════════════════════════════════════════════╗
║  ✅ Inscription enregistrée                          ║
║  SAWADOGO Aminata → Terminale A                      ║
║  Année 2025-2026 · Statut : Non affecté              ║
║  Code paiement : Terminale A-Non affecté-Secondaire  ║
╚══════════════════════════════════════════════════════════════╝
```

**Message erreur — matricule invalide :**
```
╔══════════════════════════════════════════════════════════════╗
║  ❌ Élève introuvable                                ║
║  Le matricule BF-CEN-2526-9999 n'existe pas.         ║
║  Vérifie le matricule ou enregistre d'abord l'élève. ║
╚══════════════════════════════════════════════════════════════╝
```

---

### 4.2 Réinscrire un Élève pour la Nouvelle Année

**À quoi ça sert :** Reconduit un élève déjà connu dans le système pour une nouvelle année scolaire.

**Étapes :**

1. Recherche l'élève par matricule ou nom
2. Dans son dossier, clique sur **Réinscrire**
3. Sélectionne la **nouvelle année scolaire**
4. Sélectionne la **nouvelle classe** (ou la même en cas de redoublement)
5. Indique si l'élève **redouble** et quelle classe il redouble
6. Clique sur **Réinscrire**

> **Important :** La réinscription crée un nouveau dossier d'inscription lié à l'élève existant. L'historique complet est conservé.

---

### 4.3 Affecter à une Classe

Cette étape est incluse dans le formulaire d'inscription (champ **Classe**). Il suffit de sélectionner la classe dans la liste déroulante.

---

### 4.4 Consulter la Liste des Inscrits par Classe

1. Clique sur **Inscriptions** dans le menu
2. Clique sur **Liste par classe**
3. Sélectionne la **classe** et l'**année scolaire**

```
┌──────────────────────────────────────────────────────────────────────────┐
│  📋 Liste des Élèves — Terminale A — Lycée Zinda — 2025-2026             │
├──────────────────────────────────────────────────────────────────────────┤
│  N°  │ Matricule          │ NOM Prénom          │ Sexe │ Âge │ Statut   │
├──────┼────────────────────┼─────────────────────┼──────┼─────┼──────────┤
│   1  │ BF-CEN-2526-0047   │ SAWADOGO Aminata    │  F   │ 14  │ Non aff. │
│   2  │ BF-CEN-2526-0048   │ OUÉDRAOGO Boureima  │  M   │ 17  │ Affecté  │
│   3  │ BF-CEN-2425-0892   │ TRAORÉ Fatoumata    │  F   │ 16  │ Boursier │
│  ... │ ...                │ ...                 │  ... │ ... │ ...      │
├──────────────────────────────────────────────────────────────────────────┤
│  Total : 58 élèves · 29 Filles · 29 Garçons                              │
│  [ 📄 Exporter PDF ]  [ 📊 Statistiques ]                                │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 4.5 Carte Scolaire de l'Élève

**À quoi ça sert :** Génère la carte scolaire individuelle d'un élève (format carte), imprimable et plastifiable. La carte affiche le nom, le matricule, la classe, l'établissement et un QR code d'authenticité.

**Accès :** `Inscriptions → [fiche de l'élève] → Carte scolaire`

**Étapes :**

1. Clique sur **Inscriptions** dans le menu
2. Recherche l'élève par nom ou matricule
3. Clique sur son nom pour ouvrir sa fiche
4. Clique sur **Carte scolaire** (ou icône carte en haut de la fiche)

```
┌─────────────────────────────────────────────────────────────────┐
│  Aperçu de la carte scolaire                                    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ LYCÉE ZINDA — OUAGADOUGOU                                 │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ [Photo]  SAWADOGO Aminata                                 │  │
│  │          Matricule : BF-CEN-2526-0047                     │  │
│  │          Classe    : Terminale A                          │  │
│  │          Année     : 2025-2026                            │  │
│  │                                     [QR]                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [ ⬇ Télécharger PDF ]                                         │
└─────────────────────────────────────────────────────────────────┘
```

4. Clique sur **Télécharger PDF** pour générer la carte
5. Imprime sur papier cartonné et plastifie

**Générer les cartes de toute une classe :**

**Accès :** `Inscriptions → [fiche d'une classe] → Cartes PDF`

Pour imprimer toutes les cartes d'une classe en un seul fichier :

1. Clique sur la classe dans la liste des classes inscrites
2. Clique sur **Cartes PDF**
3. Le système génère un PDF avec toutes les cartes, prêt à imprimer et découper

**Points d'attention :**

- Si l'élève n'a pas de photo, ses initiales s'affichent à la place
- Le QR code embarqué permet de vérifier l'authenticité sans connexion internet

---

### 4.7 Marquer Abandon / Annuler l'Abandon

**À quoi ça sert :** Signale qu'un élève a abandonné l'établissement en cours d'année, ou annule cet abandon si l'élève reprend sa scolarité. Une inscription en « Abandon » est exclue de toutes les listes de classe (notes, présences, examens) mais reste visible dans la liste des élèves.

**Qui peut accéder :** Directeur, Proviseur, Secrétaire

**Accès :** Via la fiche de l'élève ou directement depuis la liste des élèves

---

#### Marquer un élève en Abandon

**Depuis la liste des élèves :**

1. Clique sur **Inscriptions** dans le menu
2. Recherche l'élève
3. Dans la colonne Actions, clique sur le bouton rouge ⛔ « Marquer Abandon »

**Depuis la fiche de l'élève :**

1. Ouvre la fiche de l'élève
2. Dans le tableau des inscriptions, repère la ligne de l'année en cours
3. Clique sur le bouton ⛔ (Marquer Abandon) en bout de ligne
4. Confirme l'action dans la boîte de dialogue

```
╔══════════════════════════════════════════════════════╗
║  ⚠️ Marquer Abandon                                   ║
║  TRAORÉ Moussa — Abandon pour 2025-2026               ║
║  Cet élève sera retiré de toutes les listes classe.  ║
╚══════════════════════════════════════════════════════╝
```

**Effet dans la liste des élèves :**

```
┌────┬────────────────────┬──────────┬────────────────┬──────────────────────┐
│ N° │ Nom & Prénom       │Matricule │ Dernière Classe│ Actions              │
├────┼────────────────────┼──────────┼────────────────┼──────────────────────┤
│  1 │ TRAORÉ Moussa      │01-...    │ 🔴 Abandon     │ [👁] [✅]            │
│  2 │ SAWADOGO Aminata   │01-...    │ Terminale A    │ [👁] [📋] [✏] [💰]  │
└────┴────────────────────┴──────────┴────────────────┴──────────────────────┘
```

- La ligne de l'élève est **grisée** (opacité réduite)
- La colonne classe affiche le badge rouge **Abandon**
- Seul le bouton ✅ « Annuler l'abandon » est disponible (pas de paiement ni de modification)

---

#### Annuler l'Abandon (reprendre la scolarité)

**Depuis la liste des élèves :**

1. Repère l'élève (ligne grisée avec badge rouge « Abandon »)
2. Clique sur le bouton ✅ dans la colonne Actions
3. L'élève est immédiatement réactivé

**Depuis la fiche de l'élève :**

1. Ouvre la fiche de l'élève
2. Dans le tableau des inscriptions, la ligne ABANDON est affichée en opacité réduite
3. Clique sur le bouton ✅ « Annuler l'abandon »

```
╔══════════════════════════════════════════════════════╗
║  ✅ Abandon annulé                                   ║
║  TRAORÉ Moussa — Statut remis à Affecté              ║
║  L'élève est de nouveau visible dans les listes.     ║
╚══════════════════════════════════════════════════════╝
```

**Après annulation :**
- La ligne redevient normale dans la liste
- L'élève réapparaît dans les listes de classe (notes, présences, examens)
- Les boutons d'action habituels (Modifier, Payer, Bilan présences) sont restaurés

**Points d'attention :**

- L'annulation remet le statut à **Affecté** — modifie l'inscription si un statut différent est nécessaire (Boursier, Non affecté…)
- Les notes et données déjà saisies avant l'abandon sont **conservées**
- Un élève en Abandon n'apparaît pas dans les relances de paiement ni dans les redevables

---

### 4.6 Statistiques d'Inscription

1. Clique sur **Inscriptions → Statistiques**
2. Sélectionne l'année scolaire
3. Consulte les statistiques automatiques :

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Statistiques d'Inscription — 2025-2026                   │
├──────────────────────────────────────────────────────────────┤
│  BLOC 1 — Genre                                              │
│  ████████████████ 421 Garçons (49.7%)                        │
│  ████████████████ 426 Filles  (50.3%)                        │
│  Total : 847 élèves                                          │
├──────────────────────────────────────────────────────────────┤
│  BLOC 2 — Tranches d'âge                                     │
│  6-10 ans   : 187 élèves (Primaire)                          │
│  11-15 ans  : 312 élèves (Post-primaire)                     │
│  16-20 ans  : 298 élèves (Secondaire)                        │
│  21 ans +   :  50 élèves                                     │
├──────────────────────────────────────────────────────────────┤
│  BLOC 3 — Redoublants                                        │
│  Redoublants : 94 élèves (11.1%)                             │
│  Nouveaux    : 753 élèves (88.9%)                            │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. GESTION DU PERSONNEL

> **Qui peut accéder :** Directeur, Proviseur, Super Admin
>
> **Accès menu :** `Menu principal → Personnel`

---

### 5.1 Enregistrer un Membre du Personnel

**À quoi ça sert :** Enregistre un enseignant, un administratif ou tout autre agent de l'établissement.

**Accès :** `Personnel → + Nouveau membre`

**Étapes :**

1. Clique sur **Personnel** dans le menu
2. Clique sur **+ Nouveau membre**

```
┌──────────────────────────────────────────────────────────────┐
│  👤 Enregistrement d'un Membre du Personnel                  │
├──────────────────────────────────────────────────────────────┤
│  NOM (en majuscules) *  : [OUÉDRAOGO______________________]  │
│  Prénom *               : [Boureima_______________________]  │
│  Date de naissance      : [15/07/1980]   Âge : [46 ans]      │
│  Sexe *                 : (●) Masculin   ( ) Féminin         │
│                                                              │
│  Téléphone *            : [+226 70 XX XX XX_______________]  │
│  Email                  : [b.ouedraogo@lyceezinda.bf______]  │
│  Diplôme principal      : [▼ CAPES / Licence + DU________]   │
│  Spécialité             : [Mathématiques__________________]  │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

3. Clique sur **Enregistrer**

**Message succès :**
```
╔══════════════════════════════════════════════════════╗
║  ✅ Membre du personnel enregistré                   ║
║  Matricule attribué : PERS-LYCB-2526-0012            ║
║  OUÉDRAOGO Boureima — Enseignant de Mathématiques    ║
╚══════════════════════════════════════════════════════╝
```

---

### 5.2 Comprendre le Matricule Personnel

**Format : `{CODE_ETAB}-P-{ANNEE}-{SEQ}`**

| Partie | Signification | Exemple |
|--------|---------------|---------|
| `{CODE_ETAB}` | Code de l'établissement | LYCB (Lycée Zinda Bobo), COLK (Collège Koudougou) |
| `P` | Personnel | P |
| `{ANNEE}` | Année d'embauche | 2026 |
| `{SEQ}` | Numéro d'enregistrement | 1, 2, ..., N |

**Exemples :**

| Matricule | Interprétation |
|-----------|----------------|
| `LYCB-P-2026-12` | 12ème agent enregistré au Lycée Bobo, 2026 |
| `COLZ-P-2025-03` | 3ème agent au Collège de Zogona, 2025 |

---

### 5.3 Inscription Annuelle du Personnel

Chaque année, les membres du personnel doivent être réaffectés à leur poste pour l'année scolaire en cours.

**Accès :** `Personnel → Inscriptions annuelles → + Nouvelle inscription`

```
┌──────────────────────────────────────────────────────────────┐
│  📋 Inscription Annuelle du Personnel                        │
├──────────────────────────────────────────────────────────────┤
│  Membre du personnel *  : [▼ OUÉDRAOGO Boureima — PERS-...] │
│  Année scolaire *       : [▼ 2025-2026____________________]  │
│  Poste *                : [▼ Enseignant___________________]  │
│  Cycle(s) concerné(s)   : [▼ Secondaire____________________] │
│  Type de contrat        : [▼ Fonctionnaire________________]  │
│  Actif                  : (●) Oui  ( ) Non                   │
│                                                              │
│          [ Annuler ]    [ ✅ Inscrire ]                      │
└──────────────────────────────────────────────────────────────┘
```

---

### 5.4 Liste du Personnel

**Accès :** `Personnel → Liste du personnel`

```
┌──────────────────────────────────────────────────────────────────────────┐
│  👥 Personnel — Lycée Zinda — 2025-2026                                  │
├───────┬──────────────────────┬────────────────────┬──────┬───────────────┤
│  N°   │ Matricule            │ NOM Prénom         │ Sexe │ Poste         │
├───────┼──────────────────────┼────────────────────┼──────┼───────────────┤
│   1   │ PERS-LYCZ-2122-0001  │ KONÉ Seydou        │  M   │ Proviseur     │
│   2   │ PERS-LYCZ-2324-0005  │ TRAORÉ Ibrahim     │  M   │ Enseignant    │
│   3   │ PERS-LYCZ-2526-0012  │ OUÉDRAOGO Boureima │  M   │ Enseignant    │
│   4   │ PERS-LYCZ-2425-0008  │ SAWADOGO/KABORÉ A. │  F   │ Secrétaire    │
│  ...  │ ...                  │ ...                │ ...  │ ...           │
├──────────────────────────────────────────────────────────────────────────┤
│  Total : 42 agents · 28 Hommes · 14 Femmes                               │
│  [ ⊘ Désactiver ]  [ 📄 Exporter PDF ]  [ Ajouter ]                     │
└──────────────────────────────────────────────────────────────────────────┘
```

> **Membres inactifs :** par défaut, seuls les membres actifs s'affichent. Clique sur **Voir les membres inactifs** pour les inclure dans la liste.

#### Export PDF par cycle

**Accès :** `Documents → Liste du personnel → Sélectionner un cycle`

1. Clique sur **Documents → Liste du personnel**
2. Sélectionne le cycle souhaité (Primaire, Post-primaire, Secondaire…)
3. Clique sur **Générer PDF**

Le PDF contient la liste alphabétique du personnel du cycle, le récapitulatif Hommes/Femmes/Total, et un **QR code de l'établissement** en bas de page (lisible sans connexion internet).

---

### 5.5 Désactiver / Réactiver un Membre du Personnel

**À quoi ça sert :** Un agent qui quitte l'établissement ou prend un congé long terme peut être **désactivé**. Il n'apparaît plus dans aucune liste de sélection du système (inscriptions, matières, présences…) mais son dossier est conservé.

**Accès :** `Personnel → [nom de l'agent] → Désactiver`

**Étapes :**

1. Clique sur le nom de l'agent dans la liste
2. Clique sur le bouton **Désactiver** (icône cercle barré)
3. Confirme l'action

**Message :**

```
╔══════════════════════════════════════════════════════╗
║  ✅ OUÉDRAOGO Boureima a été désactivé.              ║
║  Il n'est plus disponible dans le système.           ║
╚══════════════════════════════════════════════════════╝
```

Pour **réactiver** un agent, accède à sa fiche et clique sur **Réactiver** (icône cercle coché).

> **Bon à savoir :** Les données historiques (notes, présences, paiements) liées à un agent désactivé sont conservées intactes.

---

### 5.6 Modifier le Dossier d'un Agent

1. Recherche l'agent dans la liste
2. Clique sur son nom
3. Clique sur **Modifier**
4. Effectue les corrections
5. Clique sur **Enregistrer**

---

### 5.7 Badge Personnel

> **Qui peut accéder :** Directeur, Proviseur, Secrétaire
>
> **Accès :** `Personnel → [nom de l'agent] → Badge Personnel`

**À quoi ça sert :** Génère un badge d'identification au format carte bancaire (85,6 × 54 mm) pour chaque membre du personnel. Le badge peut être imprimé et plastifié.

**Étapes :**

1. Clique sur le nom de l'agent dans la liste du personnel
2. Sur la fiche de l'agent, clique sur la carte **Badge Personnel**
3. Une page d'aperçu s'affiche avec le badge en taille réelle

```
┌─────────────────────────────────────────────────┐
│  Aperçu du badge (85,6 × 54 mm)                │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ █ LYCÉE ZINDA — OUAGADOUGOU               │  │
│  │   ÉTABLISSEMENT SECONDAIRE PRIVÉ          │  │
│  ├───────────────────────────────────────────┤  │
│  │ [Photo] OUÉDRAOGO                         │  │
│  │         Boureima                          │  │
│  │ ▌ ENSEIGNANT DE MATHÉMATIQUES             │  │
│  │         Poste : Titulaire                 │  │
│  ├───────────────────────────────────────────┤  │
│  │ Matricule : PERS-LYCZ-2526-0012 2025-2026 │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  [ ⬇ Télécharger PDF ]                         │
└─────────────────────────────────────────────────┘
```

4. Clique sur **Télécharger PDF** pour générer le badge en PDF
5. Imprime le PDF (de préférence sur papier cartonné, format carte)

**Points d'attention :**

- Si l'agent n'a pas de **photo**, ses initiales s'affichent à la place — ajoute une photo depuis **Modifier le profil** pour un badge plus professionnel
- Le badge affiche la **fonction principale** de l'agent et son **poste de l'année en cours** (si une inscription annuelle existe)
- Le badge porte le **logo de l'établissement** si celui-ci est configuré dans Paramètres → Identité

**Messages système :**

```
╔═══════════════════════════════════════════════╗
║  ℹ️ Aucune photo — les initiales seront       ║
║  affichées. Ajoute une photo depuis           ║
║  le profil pour un badge plus complet.        ║
╚═══════════════════════════════════════════════╝
```

**Cas concret :** Le censeur du Lycée Zinda veut équiper tous les nouveaux enseignants de badges avant la rentrée. Il accède à la fiche de chaque agent, clique sur **Badge Personnel**, télécharge le PDF, et envoie le fichier à l'imprimeur.

---

### 5.8 Contrat de Travail

> **Qui peut accéder :** Directeur, Proviseur
>
> **Disponibilité :** Uniquement pour les établissements **privés** et **confessionnels** — non disponible pour les établissements publics
>
> **Accès :** `Personnel → [nom de l'agent] → Contrat de travail`

**À quoi ça sert :** Génère un contrat de travail officiel en PDF pour un membre du personnel, pré-rempli avec ses informations personnelles et son poste. Le contrat comporte 6 articles et une zone de signature pour les deux parties.

**Étapes :**

1. Clique sur le nom de l'agent dans la liste du personnel
2. Sur la fiche de l'agent, clique sur la carte **Contrat de travail**

> Si l'établissement est **public**, cette carte est grisée et non cliquable avec la mention *"Non disponible (établissement public)"*.

3. La page d'aperçu s'affiche avec un résumé du contrat :

```
┌────────────────────────────────────────────────────┐
│  📄 Contrat de Travail                             │
│  Réf. : CT-PERS-LYCZ-2526-0012-2025-2026          │
│  Établi le 20/03/2026                              │
├────────────────────────────────────────────────────┤
│  Entre les soussignés :                            │
│  • L'Employeur : Lycée Zinda — Ouagadougou         │
│  • L'Agent : OUÉDRAOGO Boureima, né le 15/07/1980  │
│    CNI N° BF-123456789                             │
│                                                    │
│  Article 1 — Engagement et Fonction                │
│    Enseignant de Mathématiques · Titulaire         │
│  Article 2 — Durée                                 │
│    CDI · Prise de fonction : 01/10/2025            │
│  Article 3 — Rémunération                         │
│    Selon grille salariale interne                  │
│  Article 4 — Obligations de l'Agent               │
│  Article 5 — Résiliation (préavis 1 mois)         │
│  Article 6 — Droit applicable                     │
│                                                    │
│  ─────────────────────────────────────────────     │
│  Signature Établissement   |   Signature Agent     │
│  [              ]          |   [             ]     │
├────────────────────────────────────────────────────┤
│  [ ⬇ Télécharger le contrat PDF ]                 │
└────────────────────────────────────────────────────┘
```

4. Vérifie les informations dans la fiche récapitulative à droite
5. Clique sur **Télécharger le contrat PDF**
6. Imprime le PDF en **deux exemplaires** — un pour l'établissement, un pour l'agent
7. Fais signer les deux parties dans les zones prévues

**Contenu du contrat PDF :**

| Article | Contenu |
|---------|---------|
| Article 1 | Engagement, fonction et poste de l'agent |
| Article 2 | Durée du contrat (CDI, CDD ou Vacation) et dates |
| Article 3 | Rémunération (mensuelle ou à l'heure pour les vacataires) |
| Article 4 | Obligations de l'agent envers l'établissement |
| Article 5 | Modalités de résiliation (préavis d'1 mois) |
| Article 6 | Droit applicable et juridiction compétente |

**Points d'attention :**

- Le contrat se génère automatiquement comme **CDI** si l'agent n'est ni contractuel ni vacataire
- Si l'agent est **vacataire**, le contrat mentionne le nombre d'heures hebdomadaires prévu
- La **référence du contrat** est unique : `CT-{matricule}-{année scolaire}`
- Le document est établi en deux exemplaires — précise-le lors de l'impression

**Cas concret :** La directrice du Collège Sainte-Famille recrute une nouvelle secrétaire. Elle crée le dossier de l'agent dans Personnel, puis génère le contrat de travail depuis sa fiche. Elle imprime 2 copies, les signe avec la nouvelle recrue, et classe l'original au secrétariat.

---

### 5.9 Gestion des Salaires du Personnel

**Rôle(s) concerné(s) :** Directeur, Comptable  
**Accès :** `Personnel → [nom de l'agent] → Nouveau bulletin de salaire`  
ou `Personnel → Salaires` pour la vue globale

**Description :** Ce module permet de saisir et de suivre les bulletins de salaire mensuels de chaque membre du personnel permanent ou contractuel. Chaque bulletin détaille les éléments de rémunération (salaire de base, primes, indemnités) et les retenues (CNSS, IUTS), et calcule automatiquement le net à payer. Un PDF imprimable est disponible pour chaque bulletin.

#### Composition du salaire

| Élément | Description |
|---|---|
| Salaire de base | Montant fixe défini dans le contrat |
| Prime d'ancienneté | Calculée automatiquement selon l'ancienneté (voir tableau ci-dessous) |
| Indemnité de transport | Compensation pour les frais de déplacement |
| Indemnité de logement | Avantage logement éventuel |
| Autres primes | Primes exceptionnelles ou avantages divers |
| **TOTAL BRUT** | Somme de tous les éléments |
| − Retenue CNSS | Cotisation salariale sécurité sociale |
| − Retenue IUTS | Impôt Unique sur les Traitements et Salaires |
| − Autres retenues | Avances, acomptes, etc. |
| **= NET À PAYER** | Montant versé à l'agent |

#### Tableau de la prime d'ancienneté (calculée automatiquement)

| Ancienneté | Taux appliqué |
|---|---|
| 0 à 2 ans | 0 % |
| 2 à 5 ans | 5 % du salaire de base |
| 5 à 10 ans | 10 % du salaire de base |
| 10 à 15 ans | 15 % du salaire de base |
| 15 à 20 ans | 20 % du salaire de base |
| 20 ans et plus | 25 % du salaire de base |

#### Créer un bulletin de salaire

1. Ouvre la fiche du membre du personnel
2. Clique sur **Nouveau bulletin de salaire** (icône jaune)
3. Remplis le formulaire :

```
┌─────────────────────────────────────────────────────────┐
│  💰 Bulletin de Salaire Mensuel                          │
├─────────────────────────────────────────────────────────┤
│  Membre du personnel *  : [▼ SAWADOGO Moussa        ]   │
│  Mois *                 : [▼ Avril              ]       │
│  Année *                : [2026]                        │
│                                                         │
│  ── Rémunération ──                                     │
│  Salaire de base *      : [85 000]  FCFA                │
│  Prime d'ancienneté     : [4 250]   FCFA  (calculée)    │
│  Indemnité de transport : [10 000]  FCFA                │
│  Indemnité de logement  : [0]       FCFA                │
│  Autres primes          : [0]       FCFA                │
│                                                         │
│  ── Retenues ──                                         │
│  Retenue CNSS           : [2 975]   FCFA  (3,5 % brut)  │
│  Retenue IUTS           : [1 800]   FCFA                │
│  Autres retenues        : [0]       FCFA                │
│                                                         │
│  Statut : [▼ Brouillon ]                                │
│                                                         │
│         [ Annuler ]    [ ✅ Enregistrer ]               │
└─────────────────────────────────────────────────────────┘
```

4. Clique sur **Enregistrer**
5. Le bulletin est créé en statut **Brouillon**

#### Cycle de vie d'un bulletin

```
Brouillon  →  [Valider]  →  Validé  →  [Marquer payé]  →  Payé
```

- **Brouillon** : modifiable et supprimable
- **Validé** : verrouillé, prêt pour le paiement
- **Payé** : archivé avec date et référence de paiement

#### Imprimer le bulletin de salaire (PDF)

Depuis la page de détail du bulletin, clique sur **Imprimer PDF**. Le document généré comprend :
- En-tête de l'établissement (logo, nom, ville)
- Identité du salarié (nom, matricule, fonction, date d'embauche)
- Tableau des éléments de rémunération et du brut
- Tableau des retenues et du net à payer
- Zones de signature employeur / salarié

```
╔══════════════════════════════════════════════════════╗
║  ✅ Bulletin généré                                  ║
║  Net à payer : 94 475 FCFA                           ║
║  Mois : Avril 2026 — SAWADOGO Moussa                 ║
╚══════════════════════════════════════════════════════╝
```

**Cas concret :** La comptable du Lycée Zinda prépare les salaires du mois d'avril. Elle ouvre chaque fiche de personnel, clique sur **Nouveau bulletin**, vérifie les montants pré-remplis (le système recopie les valeurs du mois précédent), ajuste si nécessaire, puis valide. Une fois tous les bulletins validés, elle marque chacun comme « Payé » après virement bancaire.

**Points d'attention :**
- Un seul bulletin par agent et par mois est autorisé
- La prime d'ancienneté est calculée automatiquement mais reste modifiable
- Seuls les bulletins en **Brouillon** peuvent être modifiés ou supprimés
- Le CNSS employé est habituellement 3,5 % du salaire brut — l'application ne le calcule pas automatiquement, saisis le montant manuellement

---

### 5.10 Gestion des Congés du Personnel

**Rôle(s) concerné(s) :** Directeur, Secrétaire  
**Accès :** `Personnel → [nom de l'agent] → Demande de congé`  
ou `Personnel → Congés` pour la vue globale

**Description :** Ce module permet d'enregistrer et de suivre les demandes de congé du personnel. Le directeur peut approuver ou refuser une demande directement depuis l'interface. Le solde de congés annuels est suivi automatiquement.

#### Droits à congé (norme Burkina Faso)

> **30 jours ouvrables** par année de service (2,5 jours par mois travaillé).
> Les dimanches ne sont pas comptés. Les samedis sont comptés comme jours ouvrables.

#### Types de congés

| Type | Description |
|---|---|
| Congé annuel | Congé payé légal (30 j/an) |
| Congé maladie | Sur présentation d'un certificat médical |
| Congé de maternité | 14 semaines légales (loi burkinabè) |
| Congé de paternité | Naissance d'un enfant |
| Événement familial | Mariage, décès d'un proche, naissance |
| Congé sans solde | Sur accord de la direction |

#### Enregistrer une demande de congé

1. Ouvre la fiche du membre du personnel
2. Clique sur **Demande de congé** (icône violette)
3. Remplis le formulaire :

```
┌─────────────────────────────────────────────────────────┐
│  📅 Demande de Congé                                     │
├─────────────────────────────────────────────────────────┤
│  Membre du personnel *  : [▼ KABORE Aminata         ]   │
│  Type de congé *        : [▼ Congé annuel           ]   │
│  Date de début *        : [14/04/2026]                  │
│  Date de fin *          : [25/04/2026]                  │
│  Motif                  : [Vacances familiales]          │
│                                                         │
│  ┌──────────────────────────────────────┐               │
│  │  Solde congés 2026                   │               │
│  │  Droits annuels : 30 j.              │               │
│  │  Jours pris     : 5 j.               │               │
│  │  Solde restant  : 25 j.              │               │
│  └──────────────────────────────────────┘               │
│                                                         │
│         [ Annuler ]    [ ✅ Enregistrer ]               │
└─────────────────────────────────────────────────────────┘
```

4. Le nombre de jours ouvrables est calculé automatiquement
5. La demande est créée avec le statut **En attente**

#### Approuver ou refuser une demande

Depuis la fiche du personnel ou la liste des congés, clique sur **Approuver** ou **Refuser** :

```
╔══════════════════════════════════════════════════════╗
║  ✅ Congé approuvé                                   ║
║  KABORE Aminata — 10 jours ouvrables                 ║
║  Du 14/04/2026 au 25/04/2026                         ║
╚══════════════════════════════════════════════════════╝
```

#### Statuts d'une demande de congé

| Statut | Signification |
|---|---|
| En attente | Demande soumise, en attente de décision |
| Approuvé | Congé accordé par la direction |
| Refusé | Congé refusé (motif dans les observations) |
| Annulé | Demande annulée par l'agent |

**Points d'attention :**
- Le solde affiché ne prend en compte que les congés **annuels approuvés**
- Les congés maladie, maternité, etc. ne déduisent pas du solde annuel
- Seuls les dimanches sont exclus du calcul — les samedis comptent

**Cas concret :** En fin mars, Mme KABORE dépose une demande de congé annuel du 14 au 25 avril. La directrice consulte la liste des congés en attente, vérifie le solde (25 jours restants), et clique **Approuver**. Le système décompte automatiquement 10 jours ouvrables du solde.

#### Autorisation de Jouissance de Congé (PDF)

Une fois un congé **approuvé**, un document officiel peut être généré et imprimé depuis la liste des congés.

**Accès :** `Personnel → Congés` → colonne Actions → **Autorisation PDF**

Le document généré comprend :
- En-tête de l'établissement (logo, nom, adresse, téléphone)
- Mention de la République du Burkina Faso
- Identité du bénéficiaire (nom, matricule, fonction, date d'embauche)
- Détails du congé (type, dates de départ et de retour, durée en jours ouvrables)
- Motif du congé (si renseigné)
- Mention légale sur l'obligation de reprise
- Ampliation (Intéressé(e) + Archives)
- Bloc de signature du directeur / signataire configuré : fonction, espace de **2 cm** pour la signature manuscrite, nom imprimé

```
╔══════════════════════════════════════════════════════╗
║  📄 Autorisation de Jouissance de Congé              ║
║  N° ___ / 2026 / LYCÉE ZINDA                         ║
║  KABORE Aminata — 10 jours ouvrables                 ║
║  Du 14/04/2026 au 25/04/2026                         ║
╚══════════════════════════════════════════════════════╝
```

> **Signataire configurable :** Le nom et la fonction du signataire sont issus de `Paramètres → Signataires des documents`, type de document **CONGE_PERSONNEL**. Si aucun signataire n'est configuré pour ce type, le nom du directeur renseigné dans l'identité de l'établissement est utilisé en repli.  
> Le document ne contient aucune signature numérique — un espace blanc de 2 cm est réservé entre le titre de fonction et le nom imprimé pour permettre la signature manuscrite.

---

## 6. SCOLARITÉ ET NOTES

> **Qui peut accéder :** Directeur, Proviseur, Enseignant (pour ses matières)
>
> **Accès menu :** `Menu principal → Pédagogie`

---

### 6.1 Configurer les Matières et Enseignements

**À quoi ça sert :** Crée les matières enseignées et les assigne aux enseignants par classe.

**Accès :** `Pédagogie → Matières`

**Étapes — Créer une matière :**

1. Clique sur **Pédagogie → Matières**
2. Clique sur **+ Nouvelle matière**

```
┌──────────────────────────────────────────────────────────────┐
│  📚 Nouvelle Matière                                         │
├──────────────────────────────────────────────────────────────┤
│  Libellé *              : [Mathématiques__________________]  │
│  Code                   : [MATH___________________________]  │
│  Cycle *                : [▼ Secondaire____________________] │
│  Coefficient            : [5]                                │
│  Évaluée (notes) ?      : (●) Oui  ( ) Non                   │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Étapes — Créer un enseignement (assigner la matière à un cours) :**

1. Clique sur **Pédagogie → Enseignements**
2. Clique sur **+ Nouvel enseignement**

```
┌──────────────────────────────────────────────────────────────┐
│  🎓 Nouvel Enseignement                                      │
├──────────────────────────────────────────────────────────────┤
│  Matière *              : [▼ Mathématiques________________]  │
│  Classe *               : [▼ Terminale A__________________]  │
│  Enseignant *           : [▼ OUÉDRAOGO Boureima___________]  │
│  Année scolaire *       : [▼ 2025-2026____________________]  │
│  Volume horaire/semaine : [6 heures]                         │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Consulter la liste des enseignements :**

**Accès :** `Pédagogie → Enseignements`

La liste des enseignements est **regroupée par classe**. Pour chaque classe, tu vois toutes les matières affectées avec l'enseignant responsable. Le nombre de matières est affiché en bas de chaque groupe de classe.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🎓 Enseignements — Lycée Zinda — 2025-2026                              │
├──────────────────────────────────────────────────────────────────────────┤
│  ▼ Terminale A                                                           │
│    Mathématiques      · Coeff 5 · OUÉDRAOGO Boureima                     │
│    Sciences Physiques · Coeff 4 · TRAORÉ Ibrahim                         │
│    Français           · Coeff 4 · KABORÉ Aïssata                         │
│    …                                                                     │
│    ── 6 matières affectées ──                                            │
├──────────────────────────────────────────────────────────────────────────┤
│  ▼ 1ère C                                                                │
│    …                                                                     │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 6.2 Planifier une Évaluation

**À quoi ça sert :** Crée le calendrier des devoirs et épreuves pour chaque classe. Chaque évaluation est ensuite liée à une saisie de notes.

**Accès :** `Pédagogie → Évaluations → Planifier une évaluation`

**Étapes :**

1. Clique sur **+ Planifier une évaluation**
2. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  📅 Planifier une Évaluation                                 │
├──────────────────────────────────────────────────────────────┤
│  Enseignement *         : [▼ Mathématiques — 5ème A_______]  │
│  Type d'évaluation *    : [▼ Devoir sur table n°1_________]  │
│  Trimestre / Période *  : [▼ 1er Trimestre — 2025-2026____]  │
│  Date planifiée         : [15/10/2025]                       │
│  Coefficient            : [1.00]                             │
│  Barème                 : [20.00]                            │
│  Description            : [Chapitres 1 à 3_______________]   │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

> **Note :** Le champ **Type d'évaluation** est alimenté par les types configurés dans `Paramètres → Types d'évaluation`. Le champ **Trimestre** est alimenté par les périodes configurées dans `Paramètres → Périodes d'évaluation`.

---

### 6.3 Saisir les Notes

**À quoi ça sert :** Enregistre les notes des élèves pour chaque évaluation.

**Accès :** `Pédagogie → Évaluations → (cliquer sur l'évaluation) → Saisir les notes`

**Étapes :**

1. Dans la liste des évaluations, clique sur **Saisir les notes** pour l'évaluation concernée
2. Le tableau de saisie s'affiche avec tous les élèves de la classe :

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  📝 Saisie — Mathématiques — 5ème A — DS N°1 — 1er Trimestre 2025-2026          │
├──────┬────────────────────────┬────────────┬──────┬───────────┬──────────────────┤
│  N°  │ NOM Prénom             │ Note /20   │ ABS  │ Dispensé  │ Observation      │
├──────┼────────────────────────┼────────────┼──────┼───────────┼──────────────────┤
│   1  │ SAWADOGO Aminata       │ [14.50]    │ [ ]  │ [ ]       │ [______________] │
│   2  │ OUÉDRAOGO Boureima     │ [09.75]    │ [ ]  │ [ ]       │ [______________] │
│   3  │ TRAORÉ Fatoumata       │ [  — ]     │ [✓]  │ [ ]       │ [ABS___________] │
│   4  │ KABORÉ Ibrahim         │ [  — ]     │ [ ]  │ [✓]       │ [______________] │
├──────────────────────────────────────────────────────────────────────────────────┤
│   Saisies : 2/4  ·  Moy. : 12.13  ·  Min : 9.75  ·  Max : 14.50               │
├──────────────────────────────────────────────────────────────────────────────────┤
│                              [ Annuler ]   [ ✅ Enregistrer les notes ]          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Les cases spéciales :**

| Case | Effet |
|------|-------|
| **ABS** | Marque l'élève absent. La zone note est grisée. L'observation se remplit automatiquement avec « ABS ». |
| **Dispensé** | Utilisé pour les élèves dispensés d'une matière (ex : EPS). La zone note est **grisée** (saisie impossible). La matière est **exclue du calcul de la moyenne générale** de cet élève. |

> **Règle absolue :** Les notes sont saisies selon le barème défini pour l'évaluation. Une note ne peut pas être négative ni dépasser le barème.

**Barre de statistiques en temps réel :**
Le pied de page affiche en direct le nombre de notes saisies, la moyenne, la note minimale et maximale de la classe.

---

### 6.4 Consulter les Résultats d'un Élève

**Accès :** `Pédagogie → Résultats élèves`

1. Recherche l'élève par matricule ou nom
2. Sélectionne l'année scolaire et la période

```
┌──────────────────────────────────────────────────────────────────────────┐
│  📊 Résultats — SAWADOGO Aminata — Terminale A — 1er Trimestre 2025-2026 │
├──────────────────────┬──────────┬────────────┬──────────────────────────┤
│  Matière             │ Coeff.   │ Moyenne    │ Appréciation             │
├──────────────────────┼──────────┼────────────┼──────────────────────────┤
│  Mathématiques       │   5      │ 14.25/20   │ Bien                     │
│  Sciences Physiques  │   4      │ 12.50/20   │ Assez Bien               │
│  Français            │   4      │ 15.00/20   │ Très Bien                │
│  Histoire-Géo        │   3      │ 13.75/20   │ Bien                     │
│  Anglais             │   3      │ 11.25/20   │ Assez Bien               │
│  SVT                 │   3      │ 16.00/20   │ Excellent                │
├──────────────────────┼──────────┼────────────┼──────────────────────────┤
│  MOYENNE GÉNÉRALE    │          │ 14.02/20   │ Bien                     │
│  RANG                │          │ 3ème /58   │                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 6.5 Calculer et Consulter les Moyennes

**Accès :** `Pédagogie → Résultats`

#### Calculer les moyennes d'une classe

1. Sélectionne la **classe** dans la liste
2. Sélectionne le **trimestre**
3. Clique sur **Calculer les moyennes**

Le système calcule pour chaque élève :
- La **moyenne par matière** (pondérée par les coefficients)
- La **moyenne générale** (somme des notes × coeff / total coefficients)
- Le **rang** dans la classe
- Les élèves **dispensés** d'une matière sont automatiquement exclus du calcul de leur moyenne générale pour cette matière

#### Consulter le relevé de notes par discipline

**Accès :** `Pédagogie → Relevé de notes`

Permet d'afficher un tableau croisé de toutes les notes d'une matière par élève et par évaluation.

1. Sélectionne l'**année scolaire**
2. Sélectionne la **classe**
3. Sélectionne l'**enseignement** (matière)
4. Sélectionne le **trimestre**
5. Le tableau s'affiche avec les notes de chaque élève pour chaque évaluation

**Impression PDF :** Clique sur **Imprimer le relevé** pour générer un PDF paysage avec le tableau et les statistiques de la matière.

#### Bilan des périodes

**Accès :** `Pédagogie → Bilan des périodes`

Affiche un tableau récapitulatif des moyennes par classe et par trimestre. Bouton **Analyser avec l'IA** disponible pour générer automatiquement des commentaires pédagogiques.

---

### 6.6 Conseil de Classe

**À quoi ça sert :** Organise et documente le conseil de classe trimestriel. Permet de saisir les décisions individuelles (passage, redoublement, réorientation, exclusion) et les mentions collectives (Félicitations, Encouragements, Mention d'honneur) pour chaque élève.

**Qui peut accéder :** Directeur, Proviseur, Censeur

**Accès :** `Pédagogie → Conseils de classe`

---

#### Créer un Conseil de Classe

1. Clique sur **Pédagogie → Conseils de classe**
2. Clique sur **+ Nouveau conseil**

```
┌──────────────────────────────────────────────────────────────┐
│  📋 Nouveau Conseil de Classe                                │
├──────────────────────────────────────────────────────────────┤
│  Classe *               : [▼ Terminale A__________________]  │
│  Trimestre *            : [▼ 1er Trimestre________________]  │
│  Année scolaire *       : [▼ 2025-2026____________________]  │
│  Date du conseil *      : [14/12/2025]                       │
│  Président du conseil   : [▼ KONÉ Seydou — Proviseur______]  │
│                                                              │
│          [ Annuler ]    [ ✅ Créer le conseil ]              │
└──────────────────────────────────────────────────────────────┘
```

1. Clique sur **Créer le conseil**

---

#### Saisir les Décisions Individuelles

Après avoir créé le conseil, tu accèdes au tableau de saisie pour chaque élève de la classe :

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│  📋 Conseil de Classe — Terminale A — 1er Trimestre — 14/12/2025                         │
├──────────────────────────┬────────────┬────────────────────────┬────────────────────────┤
│  Élève                   │ Moyenne    │ Décision               │ Mentions               │
├──────────────────────────┼────────────┼────────────────────────┼────────────────────────┤
│  SAWADOGO Aminata        │ 14.02/20   │ [▼ Passage]            │ [x] Encouragements     │
│  OUÉDRAOGO Boureima      │  8.75/20   │ [▼ Redoublement]       │ [ ] Félicitations      │
│  TRAORÉ Fatoumata        │ 16.50/20   │ [▼ Passage]            │ [x] Félicitations      │
│  KABORÉ Ibrahim          │  5.20/20   │ [▼ Réorientation]      │ [ ] Mention d'honneur  │
│  …                       │ …          │ …                      │ …                      │
├──────────────────────────┴────────────┴────────────────────────┴────────────────────────┤
│  [ Appréciation générale de la classe : [Classe sérieuse avec des résultats encourageants] ]│
│                                        [ ✅ Enregistrer les décisions ]                  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**Décisions disponibles :**

- **Passage** — L'élève passe dans la classe supérieure
- **Redoublement** — L'élève refait l'année
- **Réorientation** — L'élève est orienté vers une autre filière
- **Exclusion** — L'élève est exclu de l'établissement

**Mentions disponibles :**

- **Félicitations** — Résultats excellents
- **Encouragements** — Résultats satisfaisants, progrès notable
- **Mention d'honneur** — Distinction particulière

**Appréciation générale :** Un commentaire collectif sur la classe peut être saisi et apparaîtra sur le procès-verbal.

---

#### Consulter un Conseil Existant

1. Clique sur **Pédagogie → Conseils de classe**
2. Filtre par classe, trimestre ou année
3. Clique sur le conseil pour voir le détail

```
┌──────────────────────────────────────────────────────────────┐
│  📋 Conseils de Classe — Terminale A — 2025-2026             │
├──────────────────────────────────────────────────────────────┤
│  1er Trimestre  │ 14/12/2025 │ 58 élèves │ Pres. : KONÉ S.  │
│  2ème Trimestre │ 21/03/2026 │ 57 élèves │ Pres. : KONÉ S.  │
│  3ème Trimestre │ —          │ —         │ À planifier       │
└──────────────────────────────────────────────────────────────┘
```

**Cas concret :** Après les compositions de décembre, le Proviseur du Lycée Zinda crée les conseils de classe pour toutes les classes du secondaire. Pour chaque élève, la décision de passage ou de redoublement est enregistrée. Les félicitations pour TRAORÉ Fatoumata (16.50/20) apparaîtront automatiquement sur son bulletin.

> **À venir :** L'export PDF du procès-verbal du conseil de classe (compte-rendu officiel) sera disponible dans une prochaine mise à jour.

---

### 6.7 Bulletins Trimestriels PDF

**À quoi ça sert :** Génère le bulletin de notes officiel d'un élève pour un trimestre donné, ou les bulletins de toute une classe en un seul PDF.

**Qui peut accéder :** Directeur, Proviseur, Enseignant (pour ses classes)

**Accès :** `Pédagogie → Bulletins`

> **Pré-requis :** Les notes de toutes les matières du trimestre doivent être saisies et les moyennes calculées avant de générer les bulletins.

---

#### Générer le Bulletin d'un Élève

1. Clique sur **Pédagogie → Bulletins**
2. Sélectionne la **classe**, l'**année scolaire** et le **trimestre**
3. Clique sur le nom de l'élève
4. Clique sur **Générer le bulletin PDF**

**Contenu du bulletin généré :**

```
╔══════════════════════════════════════════════════════════════════╗
║          LYCÉE ZINDA — OUAGADOUGOU                               ║
║     BULLETIN DE NOTES — 1er TRIMESTRE 2025-2026                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Élève    : SAWADOGO Aminata     Matricule : BF-CEN-2526-0047    ║
║  Classe   : Terminale A          Rang      : 3ème / 58           ║
╠═══════════════╦═══════╦════════════╦══════╦══════════════╦═══════╣
║  Matière      ║ Coeff ║ Moyenne/20 ║ Rang ║ Appréciation ║ Prof. ║
╠═══════════════╬═══════╬════════════╬══════╬══════════════╬═══════╣
║  Mathématiq.  ║   5   ║   14.25    ║  3   ║ Bien         ║ KONE  ║
║  Sciences Ph. ║   4   ║   12.50    ║  7   ║ Assez Bien   ║ OUÉDR ║
║  Français     ║   4   ║   15.00    ║  2   ║ Très Bien    ║ TRAORÉ║
║  Histoire-Géo ║   3   ║   13.75    ║  5   ║ Bien         ║ SAWAD ║
║  EPS          ║   2   ║   Dispensé ║  —   ║ —            ║ KABORÉ║
╠═══════════════╩═══════╩════════════╩══════╩══════════════╩═══════╣
║  MOYENNE GÉNÉRALE    :  14.02/20   ·  Rang : 3ème / 58           ║
║  Plus forte moyenne  :  16.50/20   (TRAORÉ Fatoumata)            ║
║  Moyenne de la classe:  13.18/20                                 ║
║  Plus faible moyenne :  09.25/20   (ZONGO Adama)                 ║
║  Appréciation        :  Bien                                     ║
╠══════════════════════════════════════════════════════════════════╣
║  Ouagadougou, le 15/12/2025                                      ║
║  M. le Proviseur KONÉ Seydou                                     ║
╚══════════════════════════════════════════════════════════════════╝
```

**Nouveautés du bulletin :**

- **Colonne Appréciation** : Appréciation individuelle par matière, issue des grilles configurées dans `Paramètres → Appréciations`
- **Colonne Professeur** : Nom du professeur responsable de la matière
- **Dispensé** : Les élèves dispensés d'une matière (ex : EPS) voient « Dispensé » dans la colonne moyenne ; la matière n'est pas comptée dans leur moyenne générale
- **Récapitulatif** : Plus forte moyenne, moyenne de la classe et plus faible moyenne de la classe s'affichent sous la moyenne générale

---

#### Générer les Bulletins de Toute une Classe (Lot)

Pour imprimer tous les bulletins d'une classe en un seul fichier PDF :

1. Clique sur **Pédagogie → Bulletins**
2. Sélectionne la **classe** et le **trimestre**
3. Clique sur **Générer tous les bulletins (PDF)**

Le système produit un seul fichier PDF contenant les bulletins de tous les élèves de la classe, prêt à imprimer.

> **Astuce :** La génération lot peut prendre quelques secondes selon la taille de la classe. Ne ferme pas la page pendant la génération.

**Messages système :**

```
╔══════════════════════════════════════════════════════╗
║  ✅ Bulletin généré                                  ║
║  SAWADOGO Aminata — Terminale A — 1er Trimestre      ║
║  Rang : 3ème / 58 · Moyenne : 14.02/20               ║
╚══════════════════════════════════════════════════════╝
```

```
╔══════════════════════════════════════════════════════╗
║  ❌ Bulletins incomplets                             ║
║  18 élèves ont des notes manquantes en Mathématiques. ║
║  Saisis toutes les notes avant de générer les        ║
║  bulletins.                                          ║
╚══════════════════════════════════════════════════════╝
```

---

### 6.8 Moyennes par Discipline

**À quoi ça sert :** Affiche, pour une classe et une période donnée, le tableau complet des moyennes de chaque élève dans chaque matière, avec la moyenne générale et le rang. Permet d'imprimer ce tableau en PDF.

**Qui peut accéder :** Directeur, Proviseur, Censeur, Enseignant

**Accès :** `Pédagogie → Moyennes par discipline`

**Étapes :**

1. Clique sur **Pédagogie** dans le menu
2. Clique sur **Moyennes par discipline**
3. Sélectionne les paramètres :

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Moyennes par Discipline                                  │
├──────────────────────────────────────────────────────────────┤
│  Année scolaire *    : [▼ 2025-2026 ▼]                      │
│  Période *           : [▼ 1er Trimestre ▼]                  │
│  Classe *            : [▼ Terminale A ▼]                    │
│                                                              │
│                                     [ 🖨 Imprimer PDF ]     │
└──────────────────────────────────────────────────────────────┘
```

4. Le tableau s'affiche automatiquement avec code couleur :
   - **Vert** : Moyenne ≥ 14
   - **Orange** : Moyenne entre 10 et 13
   - **Rouge** : Moyenne < 10
   - **Disp.** : Dispensé

5. L'en-tête du tableau reste fixe lors du défilement horizontal

6. Clique sur **Imprimer PDF** pour exporter en PDF paysage (A4)

**Lecture du tableau :**

```
┌────┬────────────────────┬──────────┬──────────┬──────┬──────┬──────┐
│ N° │ Nom & Prénom       │ Maths    │ Français │  …   │ Moy. │ Rang │
│    │                    │ c.3      │ c.4      │      │ Gén. │      │
├────┼────────────────────┼──────────┼──────────┼──────┼──────┼──────┤
│  1 │ SAWADOGO Aminata   │  16.50   │  13.00   │ …    │14.02 │  3e  │
│  2 │ TRAORÉ Moussa      │   8.00   │  11.50   │ …    │ 9.75 │ 28e  │
└────┴────────────────────┴──────────┴──────────┴──────┴──────┴──────┘
```

> **Prérequis :** Les moyennes doivent avoir été calculées pour la classe et la période sélectionnées. Si le tableau est vide, recalcule les moyennes depuis `Pédagogie → Résultats de la classe`.

---

## 7. PRÉSENCES ET ABSENCES

> **Qui peut accéder :** AVS (pour la saisie), Directeur, Proviseur, Censeur (pour la consultation)
>
> **Accès menu :** `Menu principal → Présences`

---

### 7.1 Faire l'Appel

**À quoi ça sert :** Enregistre les présences et absences des élèves pour chaque séance de cours.

**Accès :** `Présences → Faire l'appel`

**Étapes :**

1. Clique sur **Présences → Faire l'appel**
2. Sélectionne la **classe**, la **date** et l'**heure**

```
┌──────────────────────────────────────────────────────────────────────────┐
│  📋 Appel — Terminale A — 14/03/2026 — 08h00                             │
├──────┬──────────────────────┬──────────────────────────────────────────  ┤
│  N°  │ NOM Prénom           │ Présence                                   │
├──────┼──────────────────────┼────────────────────────────────────────────┤
│   1  │ SAWADOGO Aminata     │ (●) Présent  ( ) Absent  ( ) Retard        │
│   2  │ OUÉDRAOGO Boureima   │ ( ) Présent  (●) Absent  ( ) Retard        │
│   3  │ TRAORÉ Fatoumata     │ (●) Présent  ( ) Absent  ( ) Retard        │
│  ... │ ...                  │ ...                                        │
├──────────────────────────────────────────────────────────────────────────┤
│  Présents : 52 · Absents : 5 · Retards : 1                               │
│                     [ ✅ Valider l'appel ]                               │
└──────────────────────────────────────────────────────────────────────────┘
```

3. Coche la présence de chaque élève
4. Clique sur **Valider l'appel**

---

### 7.2 Enregistrer une Absence

Si un élève est absent, tu peux enregistrer son absence même en dehors d'un appel :

1. Clique sur **Présences → Enregistrer une absence**
2. Saisis le matricule de l'élève
3. Indique la date, le début et la fin de l'absence
4. Clique sur **Enregistrer**

---

### 7.3 Justifications d'Absences

> **Qui peut accéder :** AVS, Censeur, Directeur, Proviseur
>
> **Accès :** `Présences → Justifications`

**À quoi ça sert :** Le module de justifications permet de gérer les demandes de justification soumises par les parents ou tuteurs pour les absences de leurs enfants. Une absence justifiée passe du statut **Absent** à **Excusé** dans le système.

**Flux complet d'une justification :**

```
Parent apporte un document
        ↓
AVS crée une justification (motif + document + période)
        ↓
La justification est "En attente" de traitement
        ↓
Censeur/Directeur examine et statue : Acceptée ou Refusée
        ↓
Si Acceptée → les absences de la période passent à "Excusé"
```

**Consulter la liste des justifications**

**Accès :** `Présences → Justifications`

```
┌────────────────────────────────────────────────────────────────────┐
│  📋 Justifications d'Absences                                      │
├──────────────┬───────────────┬──────────────┬──────────────────────┤
│  Total       │  En attente   │  Acceptées   │  Refusées            │
│    24        │      7        │     15       │      2               │
├──────────────┴───────────────┴──────────────┴──────────────────────┤
│  Filtrer : [▼ Statut]  [▼ Classe]  [🔍 Nom de l'élève]            │
├────────┬────────────────────┬────────────┬────────────┬────────────┤
│ Élève  │ Période            │ Motif      │ Statut     │ Actions    │
├────────┼────────────────────┼────────────┼────────────┼────────────┤
│ SAWAD. │ 10/03 → 12/03/2026 │ Maladie    │ En attente │ [Traiter] │
│ TRAORÉ │ 14/03 → 14/03/2026 │ Décès fam. │ Acceptée   │ [Voir]    │
└────────┴────────────────────┴────────────┴────────────┴────────────┘
```

**Créer une justification**

**Accès :** `Présences → Justifications → + Nouvelle justification`

1. Clique sur **+ Nouvelle justification**
2. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  📄 Nouvelle Justification d'Absence                         │
├──────────────────────────────────────────────────────────────┤
│  Élève *        : [▼ Rechercher un élève________________]    │
│  Motif *        : [Certificat médical — Dr TRAORÉ_______]    │
│  Date de début* : [10/03/2026]                               │
│  Date de fin *  : [12/03/2026]                               │
│  Document joint : [📎 Choisir un fichier  (PDF, image)]      │
│                                                              │
│         [ Annuler ]    [ ✅ Soumettre la justification ]     │
└──────────────────────────────────────────────────────────────┘
  * Champ obligatoire
```

3. Clique sur **Soumettre la justification**

> **Règle :** La date de fin doit être supérieure ou égale à la date de début — sinon le système affiche une erreur de validation.

**Traiter une justification (Accepter ou Refuser)**

**Accès :** `Présences → Justifications → [En attente] → Traiter`

1. Clique sur **Traiter** sur une justification *En attente*
2. La page affiche le détail + la liste des absences concernées :

```
┌──────────────────────────────────────────────────────────────────┐
│  🔎 Traiter — SAWADOGO Aminata  |  10/03 → 12/03/2026           │
│  Motif : Certificat médical                                      │
├──────────────────────────────────────────────────────────────────┤
│  Absences sur la période :                                       │
│  ┌──────────────┬────────────────────┬────────────────────────┐  │
│  │ 10/03/2026   │ Mathématiques      │ Absent                 │  │
│  │ 10/03/2026   │ Français           │ Absent                 │  │
│  │ 12/03/2026   │ Physique-Chimie    │ Absent                 │  │
│  └──────────────┴────────────────────┴────────────────────────┘  │
│  3 absence(s) seront excusée(s) si tu acceptes.                  │
├──────────────────────────────────────────────────────────────────┤
│       [ ✅ Accepter ]              [ ❌ Refuser ]                │
└──────────────────────────────────────────────────────────────────┘
```

3. Clique sur **Accepter** ou **Refuser**

**Message si acceptée :**

```
╔══════════════════════════════════════════════════════════╗
║  ✅ Justification acceptée                              ║
║  3 absence(s) marquée(s) comme excusée(s)               ║
╚══════════════════════════════════════════════════════════╝
```

> **Bon à savoir :** Une justification déjà traitée ne peut plus être modifiée. Elle reste visible avec son statut final.

**Cas concret :** La mère de SAWADOGO Aminata (Terminale A) apporte un certificat médical pour une hospitalisation du 10 au 12 mars. L'AVS crée la justification. Le lendemain, le censeur clique sur **Traiter**, vérifie les 3 absences listées, et clique **Accepter**. Les absences passent automatiquement en *Excusée*.

---

### 7.4 Bilan des Présences par Élève

> **Qui peut accéder :** AVS, Censeur, Directeur, Proviseur
>
> **Accès :** Via la liste d'appel (clic sur le nom d'un élève) ou `Élèves → [fiche élève] → Bilan présences`

**À quoi ça sert :** Affiche le récapitulatif complet des présences, absences et retards d'un élève sur toute l'année scolaire, ainsi que l'historique de ses justifications.

```
┌───────────────────────────────────────────────────────────────────┐
│  📊 Bilan des Présences — SAWADOGO Aminata — Terminale A          │
│  Année scolaire 2025-2026                                         │
├──────────────┬────────────────┬──────────────┬────────────────────┤
│  Présences   │  Absences      │  Retards     │  Excusées          │
│     142      │     12         │     3        │     8              │
├──────────────┴────────────────┴──────────────┴────────────────────┤
│  Détail des absences :                                            │
│  ┌──────────────┬─────────────────────┬────────────────────────┐  │
│  │ 10/03/2026   │ Mathématiques       │ ✅ Excusée             │  │
│  │ 20/02/2026   │ Histoire-Géo        │ ⚠️ Non justifiée       │  │
│  └──────────────┴─────────────────────┴────────────────────────┘  │
├───────────────────────────────────────────────────────────────────┤
│  Justifications :                                                 │
│  ┌──────────────┬─────────────────────┬────────────────────────┐  │
│  │ 10/03→12/03  │ Certificat médical  │ ✅ Acceptée [Voir]     │  │
│  └──────────────┴─────────────────────┴────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

- Les absences **excusées** ✅ ont fait l'objet d'une justification acceptée
- Les absences **non justifiées** ⚠️ peuvent encore faire l'objet d'une justification

**Cas concret :** Avant de convoquer les parents de SAWADOGO Aminata, l'AVS consulte son bilan depuis la liste d'appel pour connaître le nombre exact d'absences non justifiées.

---

### 7.5 Pointage par QR Code

**À quoi ça sert :** Permet de marquer la présence d'un élève en scannant le QR code imprimé sur sa carte d'identité scolaire. Plus rapide que l'appel nominal, ce système est particulièrement utile lors des entrées et sorties de classe.

**Qui peut accéder :** AVS, Enseignant, Censeur, Directeur

**Accès :** `Présences → Scanner QR Code`

#### Générer les Cartes QR des Élèves

Avant de pouvoir utiliser le pointage QR, chaque élève doit disposer de sa carte avec QR code.

1. Va dans `Présences → Cartes QR par classe`
2. Sélectionne la classe
3. Clique sur **Générer les cartes QR (PDF)**

```
┌──────────────────────────────────────────────────────────────┐
│  🔲 Cartes QR — Terminale A — 2025-2026                      │
├──────────────────────────────────────────────────────────────┤
│  Classe : [▼ Terminale A]                                    │
│                                                              │
│  32 élèves — Cartes prêtes à imprimer                        │
│                                                              │
│  [ 🔲 Générer cartes QR PDF ]    [ 🖼 QR individuel ]        │
└──────────────────────────────────────────────────────────────┘
```

4. Imprime le PDF et découpe les cartes (format carte de visite)
5. Distribue une carte à chaque élève — ils la conservent toute l'année

Chaque carte contient :
- Le nom et prénom de l'élève
- Sa classe et son matricule
- Un QR code unique encodant son identifiant

#### Scanner un QR Code à l'Entrée

1. Va dans `Présences → Scanner QR Code`
2. Une interface apparaît avec la caméra de l'appareil (tablette ou PC avec webcam)
3. Pointe l'appareil vers le QR code de la carte de l'élève

```
╔══════════════════════════════════════════════════════╗
║  🔲  Pointage QR Code                                ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║       ┌─────────────────────────────────┐            ║
║       │  [ Vue de la caméra / scanner ] │            ║
║       └─────────────────────────────────┘            ║
║                                                      ║
║  Dernier pointage :                                  ║
║  ✅ SAWADOGO Aminata — Terminale A — 07h52           ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
```

4. Dès le scan, le système enregistre la présence et affiche le nom de l'élève

**Cas concret :** L'AVS du Lycée Zinda se poste à l'entrée du portail avec une tablette. Chaque élève qui entre présente sa carte, l'AVS scanne et la présence est enregistrée instantanément — sans feuilles papier ni appel vocal.

> **Sans réseau :** Le pointage QR nécessite que le serveur soit accessible (réseau local). Il ne fonctionne pas hors ligne.

---

## 8. VIE SCOLAIRE

> **Qui peut accéder :** AVS, Censeur, Directeur, Proviseur
>
> **Accès menu :** `Menu principal → Vie Scolaire`

---

### 8.1 Enregistrer une Sanction Disciplinaire

**À quoi ça sert :** Documente officiellement une sanction appliquée à un élève.

**Accès :** `Vie Scolaire → Sanctions → + Nouvelle sanction`

**Étapes :**

1. Clique sur **Vie Scolaire → Sanctions**
2. Clique sur **+ Nouvelle sanction**

```
┌──────────────────────────────────────────────────────────────┐
│  ⚠️ Nouvelle Sanction Disciplinaire                          │
├──────────────────────────────────────────────────────────────┤
│  Élève *                : [BF-CEN-2526-0048_______________]  │
│                  → OUÉDRAOGO Boureima — Terminale A          │
│  Type de sanction *     : [▼ Exclusion temporaire — 3j___]   │
│  Date de la faute *     : [14/03/2026]                       │
│  Début de sanction *    : [15/03/2026]                       │
│  Fin de sanction *      : [17/03/2026]                       │
│  Motif *                : [Bagarre dans la cour___________]  │
│  Décidé par *           : [▼ Censeur TRAORÉ Moumouni_____]   │
│  Convocation parents    : (●) Oui  ( ) Non                   │
│  Date convocation       : [16/03/2026]                       │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

3. Clique sur **Enregistrer**

---

### 8.2 Activités Parascolaires

**À quoi ça sert :** Enregistre et gère les clubs, associations et activités extrascolaires de l'établissement. Chaque activité a une capacité maximale et un type.

**Qui peut accéder :** AVS, Censeur, Directeur, Proviseur

**Accès :** `Vie Scolaire → Activités`

#### Créer une Activité

1. Clique sur **Vie Scolaire → Activités**
2. Clique sur **+ Nouvelle activité**

```
┌──────────────────────────────────────────────────────────────┐
│  🎭 Nouvelle Activité Parascolaire                           │
├──────────────────────────────────────────────────────────────┤
│  Nom de l'activité *    : [Club de Mathématiques___________] │
│  Type *                 : [▼ Académique___________________]  │
│  Description            : [Préparation aux olympiades_____]  │
│  Responsable            : [▼ OUÉDRAOGO Boureima___________]  │
│  Capacité maximale      : [25 élèves]                        │
│  Année scolaire *       : [▼ 2025-2026____________________]  │
│  Actif                  : (●) Oui  ( ) Non                   │
│                                                              │
│          [ Annuler ]    [ ✅ Créer l'activité ]              │
└──────────────────────────────────────────────────────────────┘
```

**Types d'activités disponibles :**

- **Sportif** — Football, Basketball, Athlétisme, Volleyball…
- **Culturel et Artistique** — Théâtre, Musique, Danse, Arts plastiques…
- **Académique** — Club de Mathématiques, Concours scientifiques, Débat…
- **Associatif** — Association des élèves, Comité de santé, Environnement…

#### Consulter la Liste des Activités

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🎭 Activités Parascolaires — Lycée Zinda — 2025-2026                    │
├────┬──────────────────────────────┬────────────┬────────────┬────────────┤
│ N° │ Activité                     │ Type       │ Inscrits   │ Capacité   │
├────┼──────────────────────────────┼────────────┼────────────┼────────────┤
│  1 │ Club de Mathématiques        │ Académique │     18     │     25     │
│  2 │ Équipe de Football           │ Sportif    │     22     │     22     │
│  3 │ Troupe de Théâtre            │ Culturel   │     15     │     20     │
│  4 │ Association des Élèves       │ Associatif │     12     │     15     │
└────┴──────────────────────────────┴────────────┴────────────┴────────────┘
```

---

### 8.3 Participation des Élèves aux Activités

**À quoi ça sert :** Inscrit des élèves dans une activité parascolaire et consulte la liste des participants.

**Qui peut accéder :** AVS, Censeur, Directeur, Proviseur

**Accès :** `Vie Scolaire → Activités → [Nom de l'activité] → Participants`

#### Inscrire un Élève dans une Activité

1. Clique sur **Vie Scolaire → Activités**
2. Clique sur le nom d'une activité (ex : « Club de Mathématiques »)
3. Clique sur **+ Ajouter un participant**
4. Saisis le matricule ou le nom de l'élève
5. Clique sur **Inscrire**

```
┌──────────────────────────────────────────────────────────────┐
│  🎓 Inscrire un élève — Club de Mathématiques                │
├──────────────────────────────────────────────────────────────┤
│  Élève (matricule) *    : [BF-CEN-2526-0047_______________]  │
│                  → SAWADOGO Aminata — Terminale A            │
│                                                              │
│          [ Annuler ]    [ ✅ Inscrire ]                      │
└──────────────────────────────────────────────────────────────┘
```

> **Capacité maximale :** Si l'activité a atteint sa capacité maximale, le système bloque l'inscription et affiche un message d'avertissement.

#### Retirer un Élève d'une Activité

1. Clique sur l'activité concernée
2. Dans la liste des participants, clique sur **Retirer** à côté du nom de l'élève
3. Confirme l'action

**Cas concret :** Le club de Mathématiques du Lycée Zinda prépare des élèves pour les olympiades nationales. L'AVS inscrit 18 volontaires après la sélection en début d'année. La liste est consultable à tout moment par le responsable du club.

---

### 8.4 Capital de Points Discipline

**À quoi ça sert :** YELEN SCHOOL attribue à chaque élève un **capital de points** qui évolue au fil de l'année selon les sanctions reçues. Chaque sanction confirmée déduit des points. Quand le solde atteint certains seuils, le système déclenche automatiquement une alerte.

**Qui peut accéder :** AVS, Censeur, Directeur, Proviseur

**Accès :** `Vie Scolaire → Capital points discipline`

#### Lire le Tableau du Capital de Points

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  ⚖️ Capital de Points Discipline — Lycée Zinda — 2025-2026                    │
├─────────────────────┬───────────────────────────────────────────────────────  │
│  🔴 En exclusion : 3  │  🟠 Conseil de discipline : 7  │  🟡 En alerte : 12   │
├────────┬────────────────────────────┬─────────┬──────────────────────────────┤
│ Classe │ Élève                      │  Solde  │ Statut                       │
├────────┼────────────────────────────┼─────────┼──────────────────────────────┤
│ Tle A  │ OUÉDRAOGO Boureima         │   42 pt │ 🔴 EXCLUSION                 │
│ 1ère C │ SAWADOGO Hamidou           │   58 pt │ 🟠 CONSEIL                   │
│ 2nde B │ KABORÉ Fatimata            │   72 pt │ 🟡 ALERTE                    │
│ Tle B  │ TRAORÉ Awa                 │   88 pt │ 🟢 NORMAL                    │
└────────┴────────────────────────────┴─────────┴──────────────────────────────┘
```

#### Signification des Statuts

| Statut | Couleur | Signification |
|--------|---------|---------------|
| **NORMAL** | 🟢 Vert | L'élève n'a pas de problème disciplinaire notable |
| **ALERTE** | 🟡 Jaune | Attention requise — l'élève approche d'un seuil critique |
| **CONSEIL** | 🟠 Orange | Le dossier doit être examiné en conseil de discipline |
| **EXCLUSION** | 🔴 Rouge | Le seuil d'exclusion est atteint — action immédiate nécessaire |

#### Consulter la Fiche d'un Élève

Dans le tableau, clique sur le nom d'un élève pour accéder à sa **fiche de suivi** complète. En bas de la fiche apparaît le widget **Capital Discipline** :

```
┌─────────────────────────────────────┐
│  Capital discipline                 │
│                                     │
│         42 / 100                    │
│    🔴 EXCLUSION                     │
│                                     │
│  Points perdus : −58 pts            │
│  Seuil d'exclusion atteint.         │
│  Convoquer les parents et saisir    │
│  le conseil de discipline.          │
└─────────────────────────────────────┘
```

**Filtres disponibles :**
- Filtrer par **année scolaire**
- Filtrer par **classe**
- Le tableau se trie automatiquement du cas le plus grave (EXCLUSION) au plus léger (NORMAL)

---

### 8.5 Configuration du Système de Points

**À quoi ça sert :** Le Directeur ou le Proviseur définit les règles du capital de points : le nombre de points de départ, les seuils d'alerte, et les messages affichés aux surveillants.

**Qui peut accéder :** Directeur, Proviseur uniquement

**Accès :** `Vie Scolaire → Configuration discipline`

```
┌──────────────────────────────────────────────────────────────┐
│  ⚙️ Configuration du Capital de Points Discipline            │
├──────────────────────────────────────────────────────────────┤
│  Capital de départ *        : [100 points______________]     │
│  Seuil d'alerte *           : [80 pts — en dessous = ALERTE] │
│  Seuil conseil discipline * : [60 pts — en dessous = CONSEIL]│
│  Seuil d'exclusion *        : [50 pts — en dessous = EXCLUSION│
│                                                              │
│  Message d'alerte           :                                │
│  [Cet élève a accumulé plusieurs sanctions. Contacter       ]│
│  [les parents et renforcer le suivi disciplinaire.          ]│
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

#### Points Déduits par Type de Sanction

Les points déduits sont définis pour chaque **type de sanction** dans `Paramètres → Types de sanctions`. Lors de la saisie d'une sanction, le champ **Points** est pré-rempli automatiquement avec la valeur par défaut du type choisi.

```
┌──────────────────────────────────────────────────────────────────┐
│  Types de sanctions — Points par défaut                          │
├──────────────────────────────────────────────────────────────────┤
│  Avertissement oral         : −2 pts  (modifiable à la saisie)   │
│  Avertissement écrit        : −5 pts                             │
│  Exclusion temporaire (1j)  : −10 pts                            │
│  Exclusion temporaire (3j)  : −15 pts                            │
│  Blâme                      : −8 pts                             │
└──────────────────────────────────────────────────────────────────┘
```

> **Règle :** Seules les sanctions au statut **CONFIRMÉ** sont comptabilisées dans le capital. Une sanction en attente ou annulée n'affecte pas le solde.

**Cas concret :** Le Censeur du Lycée Zinda configure un capital de départ de 100 points. Après 3 exclusions temporaires (−30 pts) et 2 avertissements écrits (−10 pts), l'élève OUÉDRAOGO Boureima se retrouve à 60 points — statut CONSEIL. Le système affiche le message d'alerte configuré et recommande de convoquer les parents.

---

### 8.6 Appels de Décision du Conseil de Classe

**À quoi ça sert :** Permet à un parent ou à un élève de contester officiellement une décision prise en conseil de classe (passage en classe supérieure refusé, redoublement imposé, orientation…). Le directeur ou le censeur traite ensuite l'appel en le confirmant ou en le révisant.

**Qui peut accéder :**
- **Saisir un appel :** AVS, Censeur, Secrétaire, Directeur (au nom du parent)
- **Traiter un appel :** Directeur, Proviseur, Censeur

**Accès :** `Vie Scolaire → Appels de décision`

#### Enregistrer un Appel

1. Clique sur **Vie Scolaire → Appels de décision**
2. Clique sur **+ Nouvel appel**

```
┌──────────────────────────────────────────────────────────────┐
│  📋 Appel de Décision du Conseil de Classe                   │
├──────────────────────────────────────────────────────────────┤
│  Décision contestée *   : [▼ Redoublement — KONÉ Issa____ ] │
│  Demandeur *            : [▼ Parent / Tuteur_____________ ]  │
│  Date de l'appel *      : [28/03/2026]                       │
│  Motif de l'appel *     :                                    │
│  [L'élève a eu une moyenne de 11/20 au 3ème trimestre après ]│
│  [une maladie prolongée. Nous demandons le réexamen du      ]│
│  [dossier en tenant compte de ces circonstances.            ]│
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

3. Clique sur **Enregistrer** — l'appel est enregistré avec le statut **EN ATTENTE**

#### Liste des Appels en Cours

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ⚖️ Appels de Décision — Lycée Zinda — 2025-2026                        │
├────────────────────────────┬──────────────┬────────────┬────────────────┤
│  Élève                     │  Décision    │  Date      │  Statut        │
├────────────────────────────┼──────────────┼────────────┼────────────────┤
│  KONÉ Issa — Terminale A   │  Redoublement│ 28/03/2026 │ ⏳ En attente  │
│  BARRY Fatou — 3ème B      │  Orientation │ 25/03/2026 │ ✅ Accepté     │
│  OUÉD. Boureima — 2nde C   │  Redoublement│ 20/03/2026 │ ❌ Rejeté      │
└────────────────────────────┴──────────────┴────────────┴────────────────┘
```

#### Traiter un Appel

1. Clique sur l'appel à traiter
2. Clique sur **Traiter**

```
┌──────────────────────────────────────────────────────────────┐
│  ⚖️ Traitement de l'Appel — KONÉ Issa                        │
├──────────────────────────────────────────────────────────────┤
│  Décision initiale : Redoublement                            │
│  Motif de l'appel  : Maladie prolongée au 3ème trimestre     │
│                                                              │
│  Décision finale * : (●) Appel accepté — décision révisée   │
│                      ( ) Appel rejeté — décision maintenue   │
│                                                              │
│  Commentaire *      :                                        │
│  [Au vu des circonstances médicales, le conseil accepte le  ]│
│  [passage conditionnel en classe supérieure.                ]│
│                                                              │
│          [ Annuler ]    [ ✅ Valider la décision ]           │
└──────────────────────────────────────────────────────────────┘
```

3. Choisis la décision finale et rédige un commentaire
4. Clique sur **Valider**

**Cas concret :** Les parents de KONÉ Issa demandent un appel après que leur fils a été retenu en Terminale A. Le directeur du Lycée Zinda examine le dossier médical joint, accepte l'appel et valide le passage conditionnel. La décision est archivée et consultable.

---

## 9. FINANCES ET SCOLARITÉ

> **Qui peut accéder :** Comptable, Secrétaire, Directeur, Proviseur
>
> **Accès menu :** `Menu principal → Finances`
>
> **Tous les montants sont en FCFA.**

---

### 9.1 Enregistrer un Paiement

**À quoi ça sert :** Enregistre le paiement de frais de scolarité d'un élève.

**Accès :** `Finances → + Nouveau paiement`

**Étapes :**

1. Clique sur **Finances** dans le menu
2. Clique sur **+ Nouveau paiement**

```
┌──────────────────────────────────────────────────────────────┐
│  💰 Enregistrement d'un Paiement                             │
├──────────────────────────────────────────────────────────────┤
│  Élève (matricule) *    : [BF-CEN-2526-0047_______________]  │
│                  → SAWADOGO Aminata — Terminale A            │
│                                                              │
│  Rubrique *             : [▼ Frais de scolarité___________]  │
│  Montant dû             : 75 000 FCFA (calculé auto)         │
│  Montant payé (FCFA) *  : [25 000_________________________]  │
│  Date du paiement *     : [14/03/2026]                       │
│  Mode de paiement *     : [▼ Espèces____________________]    │
│  Référence reçu         : [REC-2526-001247________________]  │
│  Écheance               : [▼ 1er versement — Octobre_____]   │
│                                                              │
│  Solde restant          : 50 000 FCFA (calculé auto)         │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

3. Clique sur **Enregistrer le paiement**

> **Validation automatique :** Si le montant saisi dans **Montant Versé** dépasse le **Reste à payer** de la rubrique, une alerte rouge s'affiche et l'enregistrement est bloqué jusqu'à correction.
>
> **Montant zéro accepté :** Il est possible de saisir **0 FCFA** dans le champ Montant Versé (ex : pour enregistrer une promesse de paiement, une exonération partielle ou une trace administrative).
>
> **Référence obligatoire :** Pour tout mode autre qu'Espèces (Mobile Money, Chèque, Virement), la référence de transaction est obligatoire.

**Message succès :**

```
╔══════════════════════════════════════════════════════╗
║  ✅ 2 paiement(s) enregistré(s)                      ║
║  SAWADOGO Aminata — Total : 35 000 FCFA              ║
╚══════════════════════════════════════════════════════╝
```

---

### 9.2 Tableau de Bord Financier

**Accès :** `Finances`

La page d'accueil des finances affiche la **dernière transaction** de chaque élève inscrit pour l'année en cours.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  💰 Finances & Scolarité — 2025-2026                                     │
│  Total encaissé : 12 450 000 FCFA · 847 transactions                    │
├──────────────────┬───────────────┬───────────────┬──────────────────────┤
│  Élève           │ Classe        │ Dernière rubr.│ Date · Montant        │
├──────────────────┼───────────────┼───────────────┼──────────────────────┤
│  KONÉ Fatou      │ CM2 A         │ Scolarité     │ 10/03/2026 · 15 000  │
│  SAWADOGO A.     │ Terminale A   │ Inscription   │ 08/03/2026 · 10 000  │
│  …               │ …             │ …             │ …                    │
└──────────────────┴───────────────┴───────────────┴──────────────────────┘
```

Clique sur un élève pour accéder à sa **situation financière complète**.

---

### 9.3 Consulter les Frais d'un Élève

**Accès :** `Finances → [nom de l'élève] → Situation financière`

1. Clique sur le nom de l'élève dans la liste
2. Consulte l'état des frais :

```
┌──────────────────────────────────────────────────────────────────────────┐
│  💵 Situation Financière — SAWADOGO Aminata — BF-CEN-2526-0047           │
│  Terminale A — Année 2025-2026                                           │
├──────────────────────┬──────────────────┬───────────────┬───────────────┤
│  Rubrique            │ Montant Total    │ Versé (FCFA)  │ Reste à payer │
├──────────────────────┼──────────────────┼───────────────┼───────────────┤
│  Frais de scolarité  │   75 000 FCFA    │   25 000      │   50 000 FCFA │
│  Frais d'inscription │   10 000 FCFA    │   10 000      │        0 FCFA │
│  Association parents │    5 000 FCFA    │        0      │    5 000 FCFA │
├──────────────────────┼──────────────────┼───────────────┼───────────────┤
│  TOTAL               │   90 000 FCFA    │   35 000 FCFA │   55 000 FCFA │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 9.4 Gérer un Échéancier de Paiement

**À quoi ça sert :** Permet de créer un plan de paiement fractionné pour un élève — définir les tranches, les montants et les dates limites. Le champ **Échéance** lors d'un paiement permet ensuite d'associer chaque versement à la bonne tranche.

**Qui peut accéder :** Comptable, Secrétaire, Directeur, Proviseur

**Accès :** `Finances → [Situation de l'élève] → Créer un échéancier`

#### Créer un Échéancier pour un Élève

1. Clique sur **Finances** dans le menu
2. Clique sur le nom de l'élève pour accéder à sa situation financière
3. Clique sur **+ Créer un échéancier**
4. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  📅 Nouvel Échéancier de Paiement                            │
├──────────────────────────────────────────────────────────────┤
│  Libellé *              : [1er versement — Octobre_________] │
│  Montant prévu (FCFA) * : [30 000_________________________]  │
│  Date limite *          : [31/10/2025]                       │
│  Rubrique               : [▼ Frais de scolarité___________]  │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

Clique sur **Enregistrer**, puis répète pour chaque tranche (2ème versement, 3ème versement…).

> **Modification / Suppression :** Chaque tranche d'échéancier peut être modifiée ou supprimée individuellement depuis la situation financière de l'élève.

---

#### Échéancier Standard au Burkina Faso

Les établissements burkinabè pratiquent couramment un paiement en 3 tranches :

| Versement       | Période habituelle        | Pourcentage recommandé |
|-----------------|---------------------------|------------------------|
| 1er versement   | Octobre (début d'année)   | 40 %                   |
| 2ème versement  | Janvier (2ème trimestre)  | 35 %                   |
| 3ème versement  | Mars (3ème trimestre)     | 25 %                   |

**Exemple pour un élève dont la scolarité est de 75 000 FCFA :**

| Versement | Montant | Date limite |
|-----------|---------|-------------|
| 1er versement | 30 000 FCFA | 31 octobre 2025 |
| 2ème versement | 26 250 FCFA | 31 janvier 2026 |
| 3ème versement | 18 750 FCFA | 31 mars 2026 |

---

#### Associer un Versement à une Échéance

Lors de l'enregistrement d'un paiement (section 9.1), le champ **Échéance** permet de préciser à quelle tranche correspond ce versement :

```
┌──────────────────────────────────────────────────────────────┐
│  💰 Enregistrement d'un Paiement                             │
├──────────────────────────────────────────────────────────────┤
│  …                                                           │
│  Montant payé (FCFA) *  : [30 000________________________]   │
│  Échéance               : [▼ 1er versement — Octobre_____]   │
│  …                                                           │
└──────────────────────────────────────────────────────────────┘
```

Ce champ est visible dans l'historique des versements de l'élève et sur le reçu PDF, permettant au comptable de vérifier d'un coup d'œil quelle tranche a été réglée.

---

### 14.4 Emploi du Temps

**À quoi ça sert :** Permet de créer, consulter et imprimer l'emploi du temps hebdomadaire des classes. Chaque séance indique la matière, l'enseignant, la salle et le créneau horaire.

**Qui peut accéder :** Directeur, Proviseur, Censeur

**Accès :** `Vie Scolaire → Emploi du temps`

#### Consulter l'Emploi du Temps d'une Classe

1. Clique sur **Vie Scolaire → Emploi du temps**
2. Sélectionne l'**année scolaire** dans le menu déroulant
3. L'emploi du temps hebdomadaire s'affiche sous forme de grille moderne

**Interface :**
- Grille à 6 colonnes (lundi au samedi)
- Cards jours avec header vert subtil
- Séances affichées en lignes propres (heure · matière · salle · prof)
- Design premium et épuré

#### Ajouter une Séance

1. Remplis le formulaire "Ajouter une séance" en bas de page :
   - **Matière / Enseignant** : sélection parmi les enseignements configurés
   - **Jour** : lundi au samedi
   - **Heure début / fin** : créneau horaire
   - **Salle** : optionnel

2. Clique sur **Ajouter** pour enregistrer

#### Supprimer une Séance

1. Survole la séance dans la grille
2. Clique sur le bouton **×** qui apparaît
3. Confirme la suppression

#### Imprimer l'Emploi du Temps en PDF (par Classe)

1. Affiche l'emploi du temps de la classe souhaitée
2. Clique sur **Imprimer PDF**
3. Le PDF s'ouvre dans un nouvel onglet — imprime ou enregistre

---

#### 14.4.1 Emploi du Temps par Professeur

**À quoi ça sert :** Génère l'emploi du temps personnel d'un enseignant sur toute la semaine. Montre toutes ses classes, matières, créneaux et salles regroupés dans une grille hebdomadaire. Le PDF inclut un récapitulatif des enseignements et le total d'heures hebdomadaires.

**Qui peut accéder :** Directeur, Proviseur, Censeur

**Accès :** `Vie Scolaire → Emploi du temps → Par professeur`

##### Consulter la Liste des Professeurs

1. Clique sur **Vie Scolaire → Emploi du temps**
2. Clique sur le lien **Par professeur** dans l'en-tête
3. La liste de tous les enseignants actifs cette année s'affiche :

```
╔══════════════════════════════════════════════════════════════════╗
║  👨‍🏫 Emplois du temps par professeur         [2025-2026 ▼]       ║
╠══════════════════════════════════════════════════════════════════╣
║  Liste des professeurs                               12 profs    ║
╠═══════════════╦══════════════════╦══════════════════════════════╣
║  ┌────────────┐  ┌─────────────────┐  ┌──────────────────────┐  ║
║  │ 👤         │  │ 👤              │  │ 👤                   │  ║
║  │ KABORÉ Ali │  │ TRAORÉ Mariam   │  │ OUÉDRAOGO Jean       │  ║
║  │ 3 matières │  │ 2 matières      │  │ 4 matières           │  ║
║  │ enseignées │  │ enseignées      │  │ enseignées           │  ║
║  └────────────┘  └─────────────────┘  └──────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════╝
```

4. Clique sur la **carte d'un professeur** pour voir son emploi du temps

##### Consulter l'Emploi du Temps d'un Professeur

Une fois sur la page du professeur, tu vois :

```
╔══════════════════════════════════════════════════════════════════════╗
║  ← Emploi du temps — KABORÉ ALIMATA         [2025-2026 ▼]  [PDF]   ║
║  Enseignante de Mathématiques                                        ║
╠════════════╦══════════════╦════════════════════════════════════════╣
║  3 matières║  12h/semaine ║  Maths — Tle A · Maths — 1ère C · … ║
╠════════════╩══════════════╩════════════════════════════════════════╣
║  Lundi         Mardi         Mercredi     Jeudi     Vendredi  Sam   ║
╠══════════════════════════════════════════════════════════════════════╣
║  ┌──────────┐               ┌──────────┐                            ║
║  │ Maths    │               │ Maths    │                            ║
║  │ 07h00–   │               │ 08h00–   │                            ║
║  │   09h00  │               │   10h00  │                            ║
║  │ Tle A    │               │ 1ère C   │                            ║
║  │ Salle 3  │               │ Salle 5  │                            ║
║  └──────────┘               └──────────┘                            ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Informations affichées par séance :**
- Nom de la matière
- Créneau horaire (ex : 07h00 – 09h00)
- Classe concernée (ex : Terminale A)
- Salle (si renseignée)

**Statistiques en en-tête :**
- Nombre de matières enseignées
- Total d'heures hebdomadaires calculé automatiquement
- Résumé par matière avec le nombre de séances

##### Imprimer l'Emploi du Temps en PDF

1. Clique sur le bouton **Imprimer PDF** en haut à droite
2. Le PDF s'ouvre dans un nouvel onglet
3. Imprime ou enregistre le fichier

**Contenu du PDF :**

```
╔══════════════════════════════════════════════════════════════════╗
║  LYCEE ZINDA          Emploi du temps — Professeur               ║
║  ─────────────────────  KABORÉ ALIMATA                           ║
║  Année 2025-2026        Enseignante de Mathématiques             ║
║ ──────────────────────────────────────────────────────────────── ║
║  3 matières     12h/sem.     PERS-LZ-2025-0042                   ║
╠══════════════════════════════════════════════════════════════════╣
║  LUNDI     MARDI   MERCREDI   JEUDI   VENDREDI   SAMEDI          ║
╠══════════════════════════════════════════════════════════════════╣
║  ┌──────┐          ┌───────┐                                     ║
║  │Maths │          │Maths  │                                     ║
║  │07h00 │          │08h00  │                                     ║
║  │ Tle A│          │1ère C │                                     ║
║  └──────┘          └───────┘                                     ║
╠══════════════════════════════════════════════════════════════════╣
║  Récapitulatif des enseignements                                  ║
║  Matière        Classe   Coeff.  H/sem.                          ║
║  Mathématiques  Tle A    3,00    3h                              ║
║  Mathématiques  1ère C   3,00    3h                              ║
╠══════════════════════════════════════════════════════════════════╣
║  Ouagadougou, le 21 avril 2026       Le Directeur               ║
║                                       NOM Prénom                 ║
╚══════════════════════════════════════════════════════════════════╝
```

**Caractéristiques du PDF :**
- Format **A4 paysage** pour une lecture optimale
- En-tête avec nom de l'établissement, matricule du professeur et année scolaire
- Barre de statistiques (nombre de matières, total heures / semaine, matricule)
- Grille à 6 colonnes (Lundi → Samedi)
- Tableau récapitulatif des enseignements avec coefficients
- Signature configurable (selon la configuration Signataires)
- Pied de page avec date et heure de génération

##### Pré-requis

Pour que l'emploi du temps d'un professeur soit visible :

| Condition | Où configurer |
|-----------|--------------|
| Le professeur doit avoir une inscription active pour l'année | `Personnel → Inscriptions` |
| Des enseignements doivent lui être assignés | `Pédagogie → Enseignements` |
| Des séances doivent être saisies pour ses enseignements | `Vie Scolaire → Emploi du temps → [Classe]` |

**Cas concret :** En début d'année, le Censeur du Lycée Zinda saisit les séances de cours pour chaque classe. Il imprime ensuite les emplois du temps de toutes les classes et les affiche dans les couloirs. Chaque enseignant reçoit son emploi du temps personnel imprimé et signé par le Directeur.

---

### 9.5 Rapport des Paiements

**Accès :** `Finances → Rapports`

Sélectionne la période pour obtenir le rapport de tous les paiements :

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Rapport des Paiements — Lycée Zinda — Mars 2026          │
├──────────────────────────────────────────────────────────────┤
│  Total encaissé ce mois   : 2 415 000 FCFA                   │
│  Nombre de paiements      : 247                              │
│  Élèves en règle          : 623 (73.6%)                      │
│  Élèves avec solde        : 224 (26.4%)                      │
│  Rubrique principale      : Scolarité — 1 850 000 FCFA       │
├──────────────────────────────────────────────────────────────┤
│  [ 📄 Exporter PDF ]  [ 📊 Exporter Excel ]                  │
└──────────────────────────────────────────────────────────────┘

---

### 9.6 Imprimer un Reçu de Paiement (PDF)

**À quoi ça sert :** Génère un reçu officiel en PDF récapitulant toutes les rubriques payées pour l'inscription de l'élève.

**Accès :** `Finances → [nom de l'élève] → Imprimer le reçu`

Le reçu PDF contient :
- En-tête de l'établissement (logo, nom, adresse, téléphone)
- Informations de l'élève (nom, matricule, classe, année scolaire)
- **QR code de l'élève** dans le bloc d'informations (lisible sans connexion internet) — contient : matricule, nom/prénom, établissement, ville, téléphone, adresse
- Tableau des rubriques : montant dû, versé, reste par rubrique
- Résumé financier : Total Dû / Total Versé / Reste à payer
- Zone de signature du caissier/responsable

---

### 9.7 Historique des Versements (PDF)

**À quoi ça sert :** Génère le détail de tous les versements effectués pour un élève, versement par versement.

**Accès :** `Finances → [nom de l'élève] → Historique des versements`

Le document contient :
- Tableau chronologique : date, rubrique, mode de paiement, référence, montant
- Résumé : Total Dû / Total Payé / Reste à payer
- **QR code de l'élève** (identique au reçu, offline)

---

### 9.8 Liste des Élèves Redevables

**À quoi ça sert :** Affiche la liste des élèves ayant un reste à payer (dette scolaire). Les élèves sont regroupés par cycle puis par classe.

**Accès :** `Finances → Redevables`

**Étapes :**

1. Clique sur **Finances** dans le menu
2. Clique sur **Redevables**

```
┌──────────────────────────────────────────────────────────────────────────┐
│  💰 Élèves Redevables — Lycée Zinda — 2025-2026                       │
│  Total Redevable : 5 450 000 FCA                                       │
├──────────────────────────────────────────────────────────────────────────┤
│  ▼ Secondaire — 3 200 000 FCA                                         │
│    ▼ Terminale A — 1 200 000 FCA                                     │
│      BF-CEN-2526-0047  SAWADOGO Aminata     75 000 FCA              │
│      BF-CEN-2526-0051  OUÉDRAOGO Boureima   50 000 FCA              │
│    ▼ 1ère C — 800 000 FCA                                            │
│      ...                                                              │
│  ▼ Post-primaire — 2 250 000 FCA                                     │
│    ...                                                                │
├──────────────────────────────────────────────────────────────────────────┤
│  [ 📄 Imprimer PDF ]  [ 🔍 Rechercher ]                                │
└──────────────────────────────────────────────────────────────────────────┘
```

**Fonctionnalités :**

- **Regroupement** : Les élèves sont triés par cycle, puis par classe, puis par ordre alphabétique
- **Totaux** : Chaque classe et chaque cycle affiche son total
- **Actions** : Bouton "Payer" pour enregistrer un paiement, "Situation" pour voir les détails
- **Recherche** : Barre de recherche par nom, prénom, matricule ou classe
- **Impression PDF** : Génère un document PDF imprimable de la liste

---

### 9.9 Bilan des Encaissements

**À quoi ça sert :** Tableau de bord complet des paiements reçus, filtrable par année scolaire, période (date début/fin) et rubrique. Présente les statistiques par mode de paiement et par jour.

**Accès :** `Finances → Bilan Encaissements`

**Étapes :**

1. Clique sur **Finances** dans le menu
2. Clique sur **Bilan Encaissements**
3. Utilise les filtres :
   - **Année scolaire** : Sélectionne l'année (ou "Toutes")
   - **Rubrique** : Filtre par type de frais (scolarité, inscription...)
   - **Date début / Date fin** : Filtre par période
4. Clique sur **Filtrer**

```
┌──────────────────────────────────────────────────────────────────────────┐
│  📊 Bilan des Encaissements                                            │
│  [2025-2026 ▼] [Toutes ▼] [14/01/2026] → [31/03/2026] [Filtrer]     │
├──────────────────────────────────────────────────────────────────────────┤
│  Total Encaissé : 8 450 000 FCA │ 247 transactions                   │
├────────────────────────────┬────────────────────────────┤
│  Par Mode de Paiement     │  Par Jour                │
│  Espèces      : 5 200 000│  15/03 : 450 000       │
│  Mobile Money : 2 150 000 │  14/03 : 380 000       │
│  Chèque       : 1 100 000│  13/03 : 520 000       │
├────────────────────────────┴────────────────────────────┤
│  ▼ Secondaire — 5 200 000 FCA                                      │
│    ▼ Terminale A — 2 100 000 FCA                                  │
│      Date       │ Élève         │ Montant                        │
│      15/03     │ SAWADOGO A.   │ 25 000                         │
│      14/03     │ OUÉDRAOGO B.  │ 50 000                         │
├──────────────────────────────────────────────────────────────────────────┤
│  [ 📄 Imprimer PDF ]                                                │
└──────────────────────────────────────────────────────────────────────────┘
```

**Fonctionnalités :**

- **Filtres multiples** : Année scolaire, Rubrique, Date début, Date fin
- **Statistiques globales** : Total encaissé et nombre de transactions
- **Par mode de paiement** : Répartition par Espèces, Mobile Money, Chèque, Virement
- **Par jour** : Évolution quotidienne des encaissements
- **Regroupement** : Liste des paiements groupée par cycle et classe
- **Impression PDF** : Génère un rapport complet imprimable

---

### 9.10 Certificat de Non-Redevabilité

**À quoi ça sert :** Génère un document PDF officiel attestant qu'un élève n'a **aucune dette financière** envers l'établissement. Ce certificat est exigé lors des inscriptions aux examens officiels (BEPC, BAC) ou pour les transferts.

**Accès :** `Finances → [Situation de l'élève] → Certificat de non-redevabilité`

**Conditions pour générer le certificat :**

| Condition | Vérification |
|-----------|---------------|
| Toutes les rubriques obligatoires soldées | Reste à payer = 0 FCFA |
| Élève inscrit pour l'année en cours | Inscription active |

> **Attention :** Si l'élève a encore un solde impayé (même 1 FCFA), le système refusera de générer le certificat et affichera le montant restant dû.

**Contenu du document PDF généré :**

```
┌────────────────────────────────────────────────────────────────┐
│  LYCES ZINDA — OUAGADOUGOU                                   │
│                                                              │
│            CERTIFICAT DE NON-REDEVABILITÉ                   │
│                                                              │
│  Je soussigné(e), Proviseur du Lycée Zinda,                 │
│  certifie que l'élève :                                       │
│                                                              │
│    NOM, Prénom : SAWADOGO Aminata                            │
│    Matricule  : BF-CEN-2526-0047                             │
│    Classe     : Terminale A — Année 2025-2026               │
│                                                              │
│  ne doit AUCUNE somme d'argent à l'établissement             │
│  à la date du 18 Mars 2026.                                  │
│                                                              │
│  Ouagadougou, le 18 Mars 2026                                │
│                          M. le Proviseur KONÉ Seydou         │
│                          ____________________                │
│                          (Signature et Cachet)               │
└────────────────────────────────────────────────────────────────┘
```

> Le document inclut un **code QR** vérifiable hors ligne et un **numéro de référence**. Le signataire est celui configuré dans les paramètres de l'établissement pour le type de document correspondant.

---

### 9.11 Relances de Paiement PDF

**À quoi ça sert :** Génère un document PDF de relances destiné aux élèves ayant un reste à payer sur une rubrique donnée. Chaque relance est un coupon A5 compact (3 par page) à distribuer aux familles concernées.

**Qui peut accéder :** Comptable, Secrétaire, Directeur, Proviseur

**Accès :** `Finances → Relances`

**Prérequis :**

- Un signataire de type **RELANCE** doit être configuré dans `Paramètres → Signataires des documents`
- Des tarifs de scolarité doivent être définis pour les niveaux concernés

**Étapes :**

1. Clique sur **Finances** dans le menu
2. Clique sur **Relances**
3. Sélectionne les paramètres de génération :

```
┌──────────────────────────────────────────────────────────────┐
│  📨 Relances de Paiement                                     │
├──────────────────────────────────────────────────────────────┤
│  Année scolaire *    : [▼ 2025-2026______________________]   │
│  Classe *            : [▼ 5ème A__________________________]  │
│  Rubrique *          : [▼ Frais de scolarité_____________]   │
│                                                              │
│  Date limite *       : [31/03/2026]                         │
│                                                              │
│  ── Aperçu ──────────────────────────────────────────────── │
│  → 12 élèves redevables identifiés                           │
│                                                              │
│          [ Générer les relances PDF ]                        │
└──────────────────────────────────────────────────────────────┘
```

4. Le nombre d'élèves concernés s'affiche **automatiquement** après la sélection de la classe et de la rubrique
5. Clique sur **Générer les relances PDF**

**Format du document PDF généré :**

```
┌─────────────────────────────────── A5 ─────────────────────────────────────┐
│  LYCÉE ZINDA — ANNÉE 2025-2026                         27/03/2026          │
│                                                                            │
│  Madame, Monsieur,                                                         │
│                                                                            │
│  Nous vous prions de bien vouloir régler les frais de                      │
│  SCOLARITÉ pour l'élève :                                                  │
│                                                                            │
│    NOM, Prénom  : SAWADOGO Aminata                                         │
│    Classe       : 5ème A                                                   │
│    Reste à payer: 50 000 FCFA                                              │
│                                                                            │
│  Date limite : 31/03/2026                                                  │
│                                                                            │
│                                     L'Intendant                           │
│                                     DIANDE Pierre                          │
│- - - - - - - - - - - - - - - ✂ - - - - - - - - - - - - - - - - - - - -  │
│  LYCÉE ZINDA — ANNÉE 2025-2026                         27/03/2026          │
│  [relance suivante…]                                                       │
│- - - - - - - - - - - - - - - ✂ - - - - - - - - - - - - - - - - - - - -  │
│  [3ème relance sur cette page A5]                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

**Fonctionnalités :**

- **Comptage préalable** : Avant de générer, le système affiche le nombre d'élèves redevables pour la sélection choisie
- **3 relances par page A5** : Optimisation de l'impression pour réduire la consommation de papier
- **Trait de découpe** : Séparateur visuel entre les coupons pour faciliter la distribution
- **Signataire automatique** : Le nom, la fonction et les titres du signataire sont issus des paramètres (`type = RELANCE`, `cycle = cycle de la classe`)
- **Date limite obligatoire** : La date limite de paiement est requise pour générer les relances

> **Configurer le signataire des relances :** Va dans `Paramètres → Signataires des documents`, sélectionne le type de document **RELANCE**, le cycle concerné et l'année scolaire, puis associe le membre du personnel signataire.

---

### 9.12 Élèves Exonérés de Paiement

**À quoi ça sert :** Affiche la liste de tous les élèves exonérés de paiement pour l'année scolaire, regroupés par classe, avec la raison d'exonération. Permet d'imprimer cette liste en PDF.

**Qui peut accéder :** Comptable, Secrétaire, Directeur, Proviseur

**Accès :** `Finances → Exonérés`

**Étapes :**

1. Clique sur **Finances** dans le menu
2. Clique sur **Exonérés**
3. Sélectionne l'**année scolaire** dans le filtre en haut
4. Utilise la barre de recherche pour filtrer par nom si besoin

```
┌──────────────────────────────────────────────────────────────┐
│  🟢 Élèves Exonérés de Paiement                              │
├──────────────────────────────────────────────────────────────┤
│  Année scolaire : [▼ 2025-2026]   🔍 [Rechercher…]          │
│                                                              │
│  ┌─ 5ème A ──────────────────────────────── 3 élève(s) ─┐  │
│  │  N°  Nom & Prénom          Matricule  Date inscr.     │  │
│  │  1   TRAORÉ Moussa         TRA-001    12/10/2025      │  │
│  │      Raison : Boursier national                       │  │
│  │  2   KONÉ Aïcha            KON-042    15/10/2025      │  │
│  │      Raison : Non précisée                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ 6ème B ──────────────────────────────── 1 élève(s) ─┐  │
│  │  ...                                                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  Total : 4 élèves exonérés — 2 classes concernées           │
│                                            [ 🖨 Imprimer PDF]│
└──────────────────────────────────────────────────────────────┘
```

Clique sur **Imprimer PDF** pour générer la liste complète en PDF.

**Le PDF généré contient :**

- En-tête établissement (logo, nom, coordonnées)
- Statistiques (nombre total d'élèves exonérés, nombre de classes)
- Un tableau par classe avec : N°, Nom & Prénom, Matricule, Date d'inscription, Raison d'exonération
- Total général en pied de liste
- Signataire automatique si configuré (type `LISTE_REDEVABLES`)

> **Marquer un élève comme exonéré :** Va dans `Inscriptions → Détail de l'élève → Modifier l'inscription` et coche le champ **Exonéré**. Tu peux saisir une raison dans le champ **Raison d'exonération**.
> **Différence avec les redevables :** Les élèves exonérés n'apparaissent pas dans la liste des redevables ni dans les relances. Leur situation financière affiche un reste à payer nul.

---

### 9.13 Bourses et Aides Financières

**À quoi ça sert :** Gère les bourses accordées aux élèves (bourses nationales, aides de l'établissement, subventions…). Une bourse réduit automatiquement le montant dû par l'élève sur les rubriques concernées.

**Qui peut accéder :** Comptable, Secrétaire, Directeur, Proviseur

**Accès :** `Finances → Bourses`

#### Créer un Type de Bourse

Avant d'attribuer une bourse, il faut configurer les types disponibles.

1. Clique sur **Finances → Types de bourses**
2. Clique sur **+ Nouveau type**

```
┌──────────────────────────────────────────────────────────────┐
│  🎓 Nouveau Type de Bourse                                   │
├──────────────────────────────────────────────────────────────┤
│  Nom *               : [Bourse nationale MENA______________] │
│  Source *            : [▼ État / Gouvernement______________] │
│  Montant par défaut  : [25 000 FCFA / an___________________] │
│  Rubrique concernée  : [▼ Frais de scolarité_______________] │
│  Description         : [Bourse du ministère de l'Education ]│
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Sources de bourses :**

| Source | Exemples |
|--------|---------|
| **État** | Bourse nationale MENA, Bourse d'excellence |
| **Établissement** | Aide sociale de l'école, Tarif préférentiel |
| **ONG / Association** | Bourse d'une ONG locale ou internationale |
| **Autre** | Don d'un particulier, aide communautaire |

#### Attribuer une Bourse à un Élève

1. Clique sur **Finances → Bourses**
2. Clique sur **+ Attribuer une bourse**

```
┌──────────────────────────────────────────────────────────────┐
│  🎓 Attribution d'une Bourse                                 │
├──────────────────────────────────────────────────────────────┤
│  Élève *              : [BF-CEN-2526-0048 — OUÉD. Boureima ] │
│  Type de bourse *     : [▼ Bourse nationale MENA___________] │
│  Année scolaire *     : [▼ 2025-2026______________________]  │
│  Montant *            : [25 000 FCFA_______________________] │
│  Date attribution *   : [15/10/2025]                         │
│  Numéro de référence  : [BN-2526-00187____________________]  │
│  Observations         : [Bourse accordée par arrêté n°042  ] │
│                                                              │
│          [ Annuler ]    [ ✅ Attribuer ]                     │
└──────────────────────────────────────────────────────────────┘
```

3. Clique sur **Attribuer** — la bourse est déduite du montant dû de l'élève

#### Liste des Boursiers

```
┌──────────────────────────────────────────────────────────────────────┐
│  🎓 Boursiers — Lycée Zinda — 2025-2026                              │
├─────────────────────────┬─────────────────────┬────────────┬─────────┤
│  Élève                  │  Type de bourse     │  Montant   │  Statut │
├─────────────────────────┼─────────────────────┼────────────┼─────────┤
│  OUÉDRAOGO Boureima     │  Bourse nationale   │ 25 000 F   │ ✅ Actif│
│  SAWADOGO Hawa          │  Aide établissement │ 15 000 F   │ ✅ Actif│
│  TRAORÉ Issouf          │  Bourse ONG Sahel   │ 30 000 F   │ ✅ Actif│
│                         │                     │            │         │
│  Total : 3 boursiers    │                     │ 70 000 F   │         │
└─────────────────────────┴─────────────────────┴────────────┴─────────┘
│                              [ 🖨 Imprimer liste PDF ]               │
└──────────────────────────────────────────────────────────────────────┘
```

> **Lien avec la situation financière :** Le montant de la bourse apparaît automatiquement dans la situation financière de l'élève comme une **réduction appliquée**, venant en déduction du montant total dû.

**Cas concret :** La comptable du Lycée Zinda reçoit la liste des 3 boursiers nationaux pour l'année 2025-2026. Elle crée les attributions dans le système. Les familles concernées n'ont plus qu'à payer le solde restant (frais totaux moins la bourse).

---

## 10. EXAMENS

> **Qui peut accéder :** Directeur, Proviseur, Secrétaire
>
> **Accès menu :** `Menu principal → Examens`

---

### 10.1 Créer une Session d'Examen

**À quoi ça sert :** Organise une session officielle (CEP, BEPC, BAC) ou un examen interne.

**Accès :** `Examens → + Nouvelle session`

**Étapes :**

1. Clique sur **Examens → + Nouvelle session**

```
┌──────────────────────────────────────────────────────────────┐
│  📋 Nouvelle Session d'Examen                                │
├──────────────────────────────────────────────────────────────┤
│  Nom de la session *    : [BAC 2026 — Session normale_____]  │
│  Type d'examen *        : [▼ BAC_________________________]   │
│  Année scolaire *       : [▼ 2025-2026____________________]  │
│  Date début *           : [01/06/2026]                       │
│  Date fin *             : [15/06/2026]                       │
│  Statut                 : [▼ Préparation________________]    │
│                                                              │
│          [ Annuler ]    [ ✅ Créer la session ]              │
└──────────────────────────────────────────────────────────────┘
```

2. Clique sur **Créer la session**

---

### 10.2 Configurer les Centres et Salles

**Accès :** `Examens → Centres → + Nouveau centre`

1. Crée un centre d'examen (ex : « Lycée Zinda — Centre BAC 2026 »)
2. Ajoute les salles disponibles avec leur capacité

```
┌──────────────────────────────────────────────────────────────┐
│  🏫 Nouvelle Salle d'Examen                                  │
├──────────────────────────────────────────────────────────────┤
│  Centre *               : [▼ Lycée Zinda — Centre BAC 2026]  │
│  Numéro de salle *      : [Salle 04_______________________]  │
│  Capacité *             : [40 candidats]                     │
│                                                              │
│          [ Annuler ]    [ ✅ Enregistrer ]                   │
└──────────────────────────────────────────────────────────────┘
```

---

### 10.3 Inscrire les Élèves aux Examens

**Accès :** `Examens → Inscriptions → + Inscrire des candidats`

1. Sélectionne la session d'examen
2. Clique sur **Inscrire par classe** pour inscrire tous les élèves d'une classe d'un coup
3. Ou clique sur **+ Inscrire un candidat** pour une inscription individuelle
4. Assigne chaque candidat à une salle

---

### 10.4 Saisir les Résultats d'un Examen Officiel

**À quoi ça sert :** Enregistre les résultats (admis / ajourné / absent) des candidate dans une session d'examen officielle. Ces données permettent de générer les statistiques de succès et de suivre les parcours des élèves.

**Accès :** `Examens → [session] → Saisir les résultats`

**Étapes :**

1. Clique sur **Examens** dans le menu
2. Clique sur la session concernée (ex : BAC 2025-2026)
3. Clique sur **Saisir les résultats**

```
┌────────────────────────────────────────────────────────────────┐
│  📝 Saisie des Résultats — BAC Série A — 2025-2026            │
├──────────────────────┼───────────────┼─────────┐
│  NOM Prénom            │ N° candidature  │ Résultat  │
├──────────────────────┼───────────────┼─────────┤
│  SAWADOGO Aminata     │   2526-BAC-0047  │ [Admis ▼]  │
│  OUEDRAOGO Boureima   │   2526-BAC-0048  │ [Ajourné▼]│
│  TRAORE Fatimata      │   2526-BAC-0049  │ [Absent ▼] │
└──────────────────────┴───────────────┴─────────┘
     [Enregistrer les résultats]
```

4. Pour chaque candidat, sélectionne le résultat dans la liste déroulante :
   - **Admis** — L'élève a obtenu l'examen
   - **Ajourné** — L'élève n'a pas obtenu l'examen
   - **Absent** — L'élève était absent
5. Clique sur **Enregistrer les résultats**

**Statistiques automatiques :**

Après la saisie, le système calcule automatiquement :

| Indicateur | Calcul |
|------------|--------|
| Taux de succès | (Admis / Inscrits) × 100 |
| Nombre d'admis | Candidats avec résultat = Admis |
| Nombre d'ajournés | Candidats avec résultat = Ajourné |
| Nombre d'absents | Candidats avec résultat = Absent |

---

### 10.5 Liste des Candidats — Filtre par Centre

**À quoi ça sert :** Affiche et filtre la liste des candidats d'une session d'examen par centre. Très utile pour les sessions avec plusieurs centres d'examen (ex : BAC avec 3 centres différents à Ouagadougou).

**Accès :** `Examens → [session] → Liste des candidats`

**Interface du filtre :**

```
┌───────────────────────────────────────────────────────────────────────┐
│  🔽 Filtrer par centre   [▼ Tous les centres (124 candidats)        ] │
│                           [✓ C2026-001]   [✕ Tout afficher]          │
└───────────────────────────────────────────────────────────────────────┘
```

**Éléments du filtre :**

| Élément | Description |
|---------|-------------|
| **Icône entonnoir** (🔽) | Indique visuellement que c'est une barre de filtre |
| **Liste déroulante** | Affiche tous les centres avec leur code et le nombre de candidats |
| **Badge vert** (✓ CODE) | Apparaît uniquement quand un filtre est actif — affiche le code du centre sélectionné |
| **Bouton "Tout afficher"** | Réinitialise le filtre — revient à la liste complète |

**Comment filtrer :**

1. Ouvre la liste des candidats d'une session
2. Dans la barre de filtre, sélectionne un centre dans la liste déroulante
3. La page se recharge automatiquement et n'affiche que les candidats du centre sélectionné
4. Le **badge vert** (ex : `✓ C2026-001`) confirme que le filtre est actif
5. Pour tout réafficher, clique sur **✕ Tout afficher**

**Export PDF filtré :** Le bouton **PDF** (en haut à droite) génère la liste en tenant compte du filtre actif — si un centre est sélectionné, seul ce centre apparaît dans le PDF.

**Cas concret :** Le BAC 2026 a 3 centres (C2026-001 Lycée Zinda, C2026-002 Lycée Philippe Zinda Kaboré, C2026-003 Lycée Bogodogo). Le secrétaire sélectionne « C2026-002 » pour imprimer uniquement la liste des candidats du Lycée Philippe Zinda Kaboré — le PDF généré ne contient que ces élèves.

---

## 11. VACATIONS

> **Qui peut accéder :** Directeur, Proviseur, Comptable
>
> **Accès menu :** `Menu principal → Vacations`

---

### 11.1 Créer un Contrat de Vacation

**À quoi ça sert :** Enregistre un contrat de prestation pour un enseignant vacataire (non fonctionnaire, payé à l'heure).

**Accès :** `Vacations → + Nouveau contrat`

**Étapes :**

1. Clique sur **Vacations → + Nouveau contrat**

```
┌──────────────────────────────────────────────────────────────┐
│  📄 Nouveau Contrat de Vacation                              │
├──────────────────────────────────────────────────────────────┤
│  Personnel *            : [▼ KABORÉ Idrissa — Vacataire___] │
│  Matière *              : [▼ Informatique_________________]  │
│  Classe(s)              : [Tle A, Tle C_________________]    │
│  Année scolaire *       : [▼ 2025-2026____________________]  │
│  Taux horaire (FCFA) *  : [3 500__________________________]  │
│  Volume d'heures prévu  : [80 heures]                        │
│                                                              │
│          [ Annuler ]    [ ✅ Créer le contrat ]              │
└──────────────────────────────────────────────────────────────┘
```

2. Clique sur **Créer le contrat**

---

### 11.2 Saisir les Heures Effectuées

**Accès :** `Vacations → [contrat] → Saisir les heures`

Chaque mois, saisis les heures réellement effectuées par le vacataire.

---

### 11.3 Générer un Bulletin de Vacation

**Accès :** `Vacations → [contrat] → Générer le bulletin`

Le bulletin récapitule les heures effectuées et le montant dû :

```
BULLETIN DE VACATION — LYCÉE ZINDA — 2025-2026
Enseignant : M. KABORÉ Idrissa
Matière    : Informatique
Période    : Octobre 2025 — Mars 2026

Heures effectuées : 68h sur 80h prévues
Taux horaire      : 3 500 FCFA/h
MONTANT DÛ        : 238 000 FCFA

Ouagadougou, le 14/03/2026
M. le Proviseur KONÉ Seydou
```

---

## 12. DOCUMENTS ADMINISTRATIFS

> **Qui peut accéder :** Secrétaire, Directeur, Proviseur
>
> **Accès menu :** `Menu principal → Documents`
>
> **Interface en cours de finalisation — les formulaires sont fonctionnels.**

---

### 12.1 Certificat de Scolarité

**À quoi ça sert :** Atteste qu'un élève est bien inscrit dans l'établissement pour l'année en cours.

**Accès :** `Documents → Certificat de scolarité → + Générer`

**Étapes :**

1. Clique sur **Documents → Certificat de scolarité**
2. Saisis le matricule de l'élève
3. Vérifie les informations pré-remplies
4. Clique sur **Générer le certificat**

Le système génère automatiquement un PDF signé par le responsable configuré pour ce cycle.

**Exemple de certificat généré :**

```
╔══════════════════════════════════════════════════════════╗
║           LYCÉE ZINDA — OUAGADOUGOU                      ║
║        Année scolaire 2025-2026                          ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║             CERTIFICAT DE SCOLARITÉ                      ║
║                                                          ║
║  Nous soussigné(e), M. le Proviseur du Lycée Zinda,      ║
║  certifions que l'élève :                                ║
║                                                          ║
║  NOM & Prénom  : SAWADOGO Aminata                        ║
║  Né(e) le      : 12/03/2012 à Ouagadougou (14 ans)       ║
║  Matricule     : BF-CEN-2526-0047                        ║
║  Classe        : Terminale A                             ║
║                                                          ║
║  est régulièrement inscrit(e) dans notre établissement.  ║
║                                                          ║
║  Ouagadougou, le 14/03/2026                              ║
║                                                          ║
║  M. le Proviseur KONÉ Seydou                             ║
║  ___________________________                             ║
║  (Signature et Cachet)                                   ║
╚══════════════════════════════════════════════════════════╝
```

---

### 12.2 Attestation de Fréquentation

**À quoi ça sert :** Atteste que l'élève a fréquenté l'établissement pendant une période donnée (utile pour les bourses, les transferts, les administrations).

**Accès :** `Documents → Attestation de fréquentation`

**Étapes similaires au certificat de scolarité** (sections 12.1).

---

### 12.3 Relevé de Notes / Cursus Scolaire

**À quoi ça sert :** Récapitule toutes les notes et moyennes d'un élève sur une ou plusieurs années scolaires.

**Accès :** `Documents → Cursus scolaire`

1. Saisis le matricule
2. Sélectionne la période (une année ou tout le cursus)
3. Clique sur **Générer**

---

### 12.4 Autorisation d'Absence

**À quoi ça sert :** Autorise officiellement un élève à s'absenter pour une période donnée.

**Accès :** `Documents → Autorisation d'absence`

**Étapes :**

1. Saisis le matricule de l'élève
2. Indique la date de début et de fin de l'absence autorisée
3. Saisis le motif
4. Clique sur **Générer l'autorisation**

---

### 12.5 Carte d'Identité Scolaire

**À quoi ça sert :** Génère une carte scolaire individuelle (format carte plastifiable) pour l'élève, avec son nom, sa classe, son matricule et un QR code d'authenticité.

**Accès :** `Inscriptions → [fiche de l'élève] → Carte scolaire`

> **Note :** La carte scolaire se génère depuis le module **Inscriptions**, pas depuis le module Documents. Consulte la section 4.5 pour les étapes complètes.

**Étapes rapides :**

1. Va dans **Inscriptions**
2. Clique sur l'élève concerné
3. Clique sur **Carte scolaire**
4. Clique sur **Télécharger PDF**
5. Imprime sur papier cartonné et plastifie

**Générer les cartes de toute une classe :** Depuis la fiche de la classe, clique sur **Cartes PDF** pour obtenir un seul fichier avec toutes les cartes.

La carte générée contient : nom, prénom, photo (ou initiales si absente), classe, établissement, QR code d'authenticité lisible hors ligne.

---

### 12.6 Liste Alphabétique d'une Classe (PDF)

**À quoi ça sert :** Génère la liste officielle de tous les élèves inscrits dans une classe, triés alphabétiquement. Utilisée pour les appels, les compositions et les remises de bulletin.

**Accès :** `Documents → Listes de classe → Sélectionner une classe`

**Étapes :**

1. Clique sur **Documents** dans le menu
2. Clique sur **Listes de classe**
3. Sélectionne la classe souhaitée dans le sélecteur
4. Clique sur **Générer PDF**

Le document contient : en-tête de l'établissement, numéro d'ordre, matricule, nom et prénom de chaque élève, sexe, date de naissance, statut, un QR code de l'établissement en bas de page.

---

### 12.7 Liste du Personnel (PDF)

**À quoi ça sert :** Génère la liste officielle du personnel d'un cycle, triée alphabétiquement. Utilisée pour les états nominatifs transmis au Ministère.

**Accès :** `Documents → Liste du personnel → Sélectionner un cycle`

**Étapes :**

1. Clique sur **Documents** dans le menu
2. Clique sur **Liste du personnel**
3. Sélectionne le cycle souhaité (Primaire, Post-primaire, Secondaire…)
4. Clique sur **Générer PDF**

Le document contient : en-tête de l'établissement, numéro d'ordre, matricule, nom et prénom, sexe, poste, récapitulatif Hommes/Femmes/Total, QR code de l'établissement.

---

### 12.8 Accès aux Documents Archivés

**À quoi ça sert :** Affiche la liste de tous les documents officiels générés par le système (certificats, listes, reçus…), avec la possibilité de les retrouver par élève, type ou date.

**Accès :** `Documents` (page d'accueil du module)

**Informations affichées pour chaque document :**

| Colonne | Description |
|---------|-------------|
| Type | Certificat, Reçu, Liste classe, Liste personnel… |
| Élève / Classe | Le destinataire du document |
| Année scolaire | L'année de génération |
| Date | Date et heure de génération |
| Généré par | Nom de l'utilisateur qui a déclenché la génération |

> Les documents sont triés par date de génération décroissante (les plus récents en premier). Les 100 derniers documents sont affichés.

---

### 12.9 Archivage et Consultation des Documents Générés

Tous les documents générés sont **archivés automatiquement** dans le système. Tu peux les retrouver à tout moment.

**Accès :** `Documents → Archives`

1. Filtre par élève, type de document ou date
2. Clique sur le document pour le **consulter ou le télécharger**

> **Important :** Les documents archivés contiennent un **snapshot** du signataire au moment de la génération. Même si le signataire change ensuite, le document reste authentique.

---

### 12.10 Codes QR dans les Documents Générés

Tous les documents PDF générés par YELEN SCHOOL contiennent un **code QR** lisible **sans connexion internet**.

#### Contenu selon le type de document

| Document | Emplacement du QR | Contenu encodé |
|----------|-------------------|----------------|
| Certificat de scolarité | Bas de page | Matricule, Nom/Prénom élève, Établissement, Ville, Tél, Adresse |
| Reçu de paiement | Section infos élève | Matricule, Nom/Prénom élève, Établissement, Ville, Tél, Adresse |
| Historique de versements | Section infos élève | Matricule, Nom/Prénom élève, Établissement, Ville, Tél, Adresse |
| Liste alphabétique (élèves) | Bas de page (1 seul QR) | Nom établissement, Ville, Téléphone, Adresse |
| Liste du personnel | Bas de page (1 seul QR) | Nom établissement, Ville, Téléphone, Adresse |

#### Utilisation

- **Vérification d'identité** : scanner le QR d'un certificat ou reçu permet de confirmer l'appartenance du document à l'élève concerné
- **Identification de l'établissement** : les listes portent le QR de l'établissement pour authentifier leur origine
- **Aucune connexion nécessaire** : toutes les informations sont embarquées directement dans le QR code

---

### 12.11 Convocations

**À quoi ça sert :** Génère des lettres de convocation officielles à destination des parents d'élèves. Une convocation peut concerner un ou plusieurs élèves à la fois, pour différents motifs : conseil de classe, sanction disciplinaire, réunion parents-professeurs, ou autre.

**Qui peut accéder :** Directeur, Proviseur, Censeur, Secrétaire

**Accès :** `Documents → Convocations`

#### Créer une Convocation

1. Clique sur **Documents** dans le menu
2. Clique sur **Convocations**
3. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  📨 Nouvelle Convocation                                     │
├──────────────────────────────────────────────────────────────┤
│  Type de convocation *  : [▼ Sanction disciplinaire______]   │
│                           Conseil de classe                  │
│                           Réunion parents-professeurs        │
│                           Autre                              │
│                                                              │
│  Date de la convocation *: [22/04/2026]                      │
│  Heure *                 : [09:00]                           │
│  Lieu *                  : [Salle de réunion — bâtiment A]   │
│  Objet *                 : [Exclusion temporaire 3 jours___] │
│  Corps du message        :                                   │
│  [Nous vous prions de bien vouloir vous présenter afin de   ]│
│  [discuter du comportement de votre enfant.                 ]│
│                                                              │
│  Filtrer par classe : [▼ Terminale A___________________]     │
│  Élèves sélectionnés :                                       │
│  ☑ OUÉDRAOGO Boureima — Terminale A — BF-CEN-2526-0048      │
│  ☐ SAWADOGO Aminata — Terminale A — BF-CEN-2526-0047        │
│  ☑ KABORÉ Seydou — Terminale A — BF-CEN-2526-0051           │
│                                                              │
│  Format :  (●) Aperçu HTML    ( ) Générer PDF                │
│                                                              │
│        [ Annuler ]    [ ✅ Générer ]                         │
└──────────────────────────────────────────────────────────────┘
```

4. Sélectionne un ou plusieurs élèves dans la liste
5. Clique sur **Aperçu HTML** pour vérifier avant impression, ou directement sur **Générer PDF**

#### Contenu du PDF Généré

Le PDF de convocation contient pour chaque élève :
- En-tête officiel de l'établissement (logo, nom, adresse)
- Bandeau **CONVOCATION** avec référence du document
- Adresse de l'émetteur (établissement) et cadre destinataire (parent/tuteur)
- Encart avec date, heure, lieu et motif de la convocation
- Corps du message personnalisé
- Zone de signature du directeur / censeur
- **Récépissé détachable** : coupon à retourner signé par le parent

> **Multi-élèves :** Si tu sélectionnes plusieurs élèves, le PDF contient autant de pages que d'élèves — une lettre individuelle par élève, prête à découper et distribuer.

**Cas concret :** Après une bagarre dans la cour, le Censeur du Lycée Zinda convoque les parents de 2 élèves impliqués. Il génère un PDF unique avec 2 lettres distinctes, les imprime et les remet aux élèves concernés.

**Message succès :**
```
╔══════════════════════════════════════════════════════════╗
║  ✅ PDF généré — 2 convocation(s)                        ║
║  Le fichier s'ouvre dans un nouvel onglet.               ║
╚══════════════════════════════════════════════════════════╝
```

---

### 12.12 Circulaires

**À quoi ça sert :** Rédige et imprime des circulaires officielles destinées aux familles ou au personnel. Une circulaire est un document de communication générale (réunion, information, rappel de règlement…) diffusé à tout l'établissement ou à des classes spécifiques.

**Qui peut accéder :** Directeur, Proviseur, Secrétaire

**Accès :** `Documents → Circulaires`

#### Rédiger une Circulaire

1. Clique sur **Documents → Circulaires**
2. Remplis le formulaire :

```
┌──────────────────────────────────────────────────────────────┐
│  📋 Nouvelle Circulaire                                      │
├──────────────────────────────────────────────────────────────┤
│  Titre *         : [Réunion de parents du 1er trimestre____] │
│  Objet *         : [Organisation de la réunion trimestrielle]│
│  Date *          : [15/04/2026]                              │
│                                                              │
│  Destinataires :                                             │
│  ( ) Tout l'établissement                                    │
│  (●) Classes sélectionnées :                                 │
│      ☑ Terminale A   ☑ Terminale B   ☐ 1ère A               │
│                                                              │
│  Corps du message * :                                        │
│  [Mesdames, Messieurs les parents d'élèves,                 ]│
│  [Nous avons l'honneur de vous convier à une réunion        ]│
│  [de parents qui se tiendra le vendredi 18 avril 2026       ]│
│  [à 15h00 dans la salle de conférences.                     ]│
│                                                              │
│  Format :  (●) Aperçu    ( ) Générer PDF                    │
│                                                              │
│        [ Annuler ]    [ ✅ Générer ]                         │
└──────────────────────────────────────────────────────────────┘
```

3. Choisis si la circulaire s'adresse à **tout l'établissement** ou à des **classes spécifiques**
4. Rédige le corps du message dans la zone de texte
5. Clique sur **Aperçu** pour vérifier la mise en page, puis **Générer PDF**

#### Contenu du PDF Généré

La circulaire PDF contient :
- En-tête officiel de l'établissement
- Bandeau **CIRCULAIRE** avec numéro de référence automatique (ex : `CIRC-2026-00003`)
- Bloc méta : destinataires, année scolaire, date, numéro
- Zone objet en évidence (bandeau gris avec accent noir)
- Titre de la circulaire en majuscules
- Corps du message
- Signature du directeur / signataire configuré

**Numérotation automatique :** Chaque circulaire reçoit un numéro unique au format `CIRC-AAAA-NNNNN`. Ce numéro apparaît dans le bandeau, le bloc méta et le pied de page.

**Cas concret :** La Directrice de l'École Primaire Sainte-Famille envoie une circulaire à tous les parents pour les informer de la date des examens de fin de trimestre. Elle sélectionne « Tout l'établissement », rédige le message en 3 paragraphes, génère le PDF et en imprime 250 exemplaires.

---

### 12.13 Attestation de Non-Redevabilité

**À quoi ça sert :** Génère une attestation officielle certifiant qu'un élève est à jour de ses paiements de scolarité. Ce document est souvent exigé en fin d'année pour le retrait des bulletins, les transferts ou les inscriptions aux examens officiels.

**Qui peut accéder :** Comptable, Secrétaire, Directeur, Proviseur

**Accès :** `Finances → Situation élève → Attestation non-redevabilité`
ou `Documents → [depuis la liste des documents de l'élève]`

#### Générer l'Attestation

1. Va dans **Finances → Situation d'un élève**
2. Recherche l'élève par matricule ou nom
3. Vérifie que la situation financière est à jour
4. Clique sur **Attestation non-redevabilité**

```
┌──────────────────────────────────────────────────────────────┐
│  💳 Attestation de Non-Redevabilité                          │
├──────────────────────────────────────────────────────────────┤
│  Élève    : TRAORÉ Awa                                       │
│  Classe   : Terminale B — Lycée Zinda                        │
│  Année    : 2025-2026                                        │
│                                                              │
│  Récapitulatif des paiements :                               │
│  ┌────────────────────┬───────────┬───────────┬──────────┐   │
│  │ Rubrique           │ Total dû  │ Versé     │ Reste    │   │
│  ├────────────────────┼───────────┼───────────┼──────────┤   │
│  │ Frais scolarité    │ 75 000 F  │ 75 000 F  │    0 F ✅│   │
│  │ Frais inscription  │ 10 000 F  │ 10 000 F  │    0 F ✅│   │
│  └────────────────────┴───────────┴───────────┴──────────┘   │
│                                                              │
│  Solde total restant : 0 FCFA ✅                             │
│                                                              │
│         [ Aperçu ]    [ 📄 Générer PDF ]                     │
└──────────────────────────────────────────────────────────────┘
```

Le PDF généré certifie que l'élève **ne doit rien** à l'établissement. Si un reste à payer existe, l'attestation l'indique clairement et ne certifie **pas** la non-redevabilité.

> **Point d'attention :** Cette attestation ne peut être délivrée que si **toutes les rubriques** de l'année scolaire sont soldées à zéro. En cas de reste à payer, le document indique le montant restant dû sans valeur certificatrice.

**Cas concret :** En fin d'année, Mme SAWADOGO se présente au secrétariat du Lycée Zinda pour récupérer le bulletin de sa fille. La secrétaire vérifie la situation financière, constate que tout est réglé, génère l'attestation en PDF et la remet à la famille.

---

## 13. GESTION DES LICENCES (Super Admin Uniquement)

> **Qui peut accéder :** Super Admin uniquement
>
> **Accès menu :** `Menu principal → Licences`

---

### 13.1 Les 4 Niveaux de Licence

YELEN SCHOOL propose 4 niveaux de licence adaptés à chaque type d'établissement :

#### 🥉 Starter — Fonctionnalités de Base

Pour les petites écoles primaires et les établissements débutants.

| Fonctionnalité | Inclus ? |
|----------------|----------|
| Enregistrement des élèves | ✅ |
| Inscriptions et réinscriptions | ✅ |
| Gestion du personnel | ✅ |
| Notes et moyennes | ✅ |
| Présences de base | ✅ |
| Documents simples (certificat, attestation) | ✅ |
| 1 établissement | ✅ |
| Portail parent | ❌ |
| Documents avancés (carte ID, cursus) | ❌ |
| Statistiques avancées | ❌ |
| IA prédictive | ❌ |
| Multi-établissements | ❌ |

#### 🥈 Standard — Pour les Collèges et Lycées

Pour les établissements post-primaires et secondaires.

| Fonctionnalité ajoutée | Inclus ? |
|------------------------|----------|
| Toutes les fonctionnalités Starter | ✅ |
| Portail parent (consultation notes/absences) | ✅ *(à venir)* |
| Documents avancés (carte ID, cursus, autorisation) | ✅ |
| Examens et centres | ✅ |
| Vacations | ✅ |
| Vie scolaire complète | ✅ |

#### 🥇 Premium — Pour les Grandes Institutions

Pour les grands lycées et établissements exigeants.

| Fonctionnalité ajoutée | Inclus ? |
|------------------------|----------|
| Toutes les fonctionnalités Standard | ✅ |
| Statistiques avancées | ✅ |
| IA prédictive (risques de décrochage) | ✅ *(à venir)* |
| Génération automatique de bulletins | ✅ *(à venir)* |
| Rapports personnalisés | ✅ |

#### 🏆 Réseau — Pour les Réseaux d'Établissements

Pour les congrégations religieuses, les fondations et les réseaux d'écoles.

| Fonctionnalité ajoutée | Inclus ? |
|------------------------|----------|
| Toutes les fonctionnalités Premium | ✅ |
| Multi-établissements (tableau de bord consolidé) | ✅ |
| Transferts inter-établissements | ✅ |
| Statistiques consolidées réseau | ✅ |

---

### 13.2 Activer une Licence

**Accès :** `Licences → Activer une licence`

**Étapes :**

1. Clique sur **Licences** dans le menu
2. Clique sur **Activer une nouvelle licence**
3. Saisis la **clé de licence** fournie par l'éditeur
4. Clique sur **Valider**

```
┌──────────────────────────────────────────────────────────────┐
│  🔑 Activation de Licence                                    │
├──────────────────────────────────────────────────────────────┤
│  Clé de licence *       : [YELEN-PREM-2026-XXXXX-XXXXX____] │
│  Établissement *        : [▼ Lycée Zinda — Ouagadougou____]  │
│                                                              │
│              [ Annuler ]    [ ✅ Activer ]                   │
└──────────────────────────────────────────────────────────────┘
```

**Message succès :**
```
╔══════════════════════════════════════════════════════╗
║  ✅ Licence activée avec succès                      ║
║  Niveau : PREMIUM                                    ║
║  Établissement : Lycée Zinda — Ouagadougou           ║
║  Valide jusqu'au : 31/08/2027                        ║
╚══════════════════════════════════════════════════════╝
```

---

### 13.3 Consulter les Alertes de Licence

Le système envoie des alertes automatiques quand :

- La licence **expire dans moins de 30 jours**
- Une fonctionnalité demandée n'est **pas incluse** dans la licence actuelle
- La licence a **expiré**

**Accès :** `Licences → Alertes`

---

### 13.4 Historique des Activations

**Accès :** `Licences → Historique`

Consulte l'historique complet de toutes les activations de licence de l'établissement.

---

## 14. STATISTIQUES ET RAPPORTS

> **Qui peut accéder :** Directeur, Proviseur, Super Admin
>
> **Accès menu :** `Menu principal → Statistiques`

---

### 14.1 Statistiques des Élèves

**Accès :** `Statistiques → Élèves`

**BLOC 1 — Répartition par Genre :**

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Répartition par Genre — 2025-2026                        │
├──────────────────────────────────────────────────────────────┤
│  ████████████████████  421 Garçons  (49.7%)                  │
│  █████████████████████ 426 Filles   (50.3%)                  │
│  ─────────────────────────────────────────                   │
│  Total : 847 élèves inscrits                                 │
└──────────────────────────────────────────────────────────────┘
```

**BLOC 2 — Répartition par Âge :**

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Répartition par Tranche d'Âge — 2025-2026                │
├──────────────────────────────────────────────────────────────┤
│   6 –  8 ans  :  ██  45 élèves  (Préscolaire/CP)             │
│   9 – 10 ans  :  ████████ 142 élèves  (Primaire)             │
│  11 – 13 ans  :  █████████████ 228 élèves  (Post-primaire)   │
│  14 – 16 ans  :  ████████████████ 287 élèves  (Secondaire)   │
│  17 – 20 ans  :  ██████ 118 élèves                           │
│  21 ans et +  :  ██  27 élèves                               │
└──────────────────────────────────────────────────────────────┘
```

**BLOC 3 — Redoublants :**

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Redoublants — 2025-2026                                  │
├──────────────────────────────────────────────────────────────┤
│  Redoublants  :  ██  94 élèves  (11.1%)                      │
│  Nouveaux     :  ████████████████████ 753 élèves  (88.9%)    │
│                                                              │
│  Classe avec le + de redoublants : 3ème A (8 élèves)         │
└──────────────────────────────────────────────────────────────┘
```

---

### 14.2 Rapports de Présences

**Accès :** `Statistiques → Présences`

Sélectionne la période et obtiens :
- Taux de présence par classe
- Élèves avec le plus d'absences
- Évolution des absences sur l'année

---

### 14.3 Rapports Financiers

**Accès :** `Statistiques → Finances`

- Total encaissé par mois
- Élèves en retard de paiement
- Répartition des paiements par rubrique

---

### 14.4 Emploi du Temps

**À quoi ça sert :** Permet de créer, consulter et imprimer l'emploi du temps hebdomadaire des classes. Chaque séance indique la matière, l'enseignant, la salle et le créneau horaire.

**Qui peut accéder :** Directeur, Proviseur, Censeur

**Accès :** `Vie Scolaire → Emploi du temps`

#### Consulter l'Emploi du Temps d'une Classe

1. Clique sur **Vie Scolaire → Emploi du temps**
2. Sélectionne l'**année scolaire** dans le menu déroulant
3. L'emploi du temps hebdomadaire s'affiche sous forme de grille moderne

**Interface :**
- Grille à 6 colonnes (lundi au samedi)
- Cards jours avec header vert subtil
- Séances affichées en lignes propres (heure · matière · salle · prof)
- Design premium et épuré

#### Ajouter une Séance

1. Remplis le formulaire "Ajouter une séance" en bas de page :
   - **Matière / Enseignant** : sélection parmi les enseignements configurés
   - **Jour** : lundi au samedi
   - **Heure début / fin** : créneau horaire
   - **Salle** : optionnel

2. Clique sur **Ajouter** pour enregistrer

#### Supprimer une Séance

1. Survole la séance dans la grille
2. Clique sur le bouton **×** qui apparaît
3. Confirme la suppression

#### Imprimer l'Emploi du Temps en PDF

1. Affiche l'emploi du temps de la classe souhaitée
2. Clique sur **Imprimer PDF**
3. Le PDF s'ouvre dans un nouvel onglet — imprime ou enregistre

**Cas concret :** En début d'année, le Censeur du Lycée Zinda saisit les séances de cours pour chaque classe. Il imprime ensuite les emplois du temps de toutes les classes et les affiche dans les couloirs. Les enseignants peuvent consulter leur planning personnel depuis leur tableau de bord.

---

## 15. FONCTIONNALITÉS À VENIR 🔜

Cette section recense honnêtement les fonctionnalités **non encore disponibles** dans l'interface utilisateur, classées par priorité de développement.

---

### État Global du Développement

| Module | État actuel | Disponible dans |
|--------|-------------|-----------------|
| Finances, Pédagogie, Inscriptions, Présences | ✅ Fonctionnel | Version actuelle |
| Bulletins PDF par élève et par classe | ✅ Fonctionnel | Version actuelle |
| Conseils de classe, Sanctions, Activités | ✅ Fonctionnel | Version actuelle |
| Vacations (contrats, heures, bulletins) | ✅ Fonctionnel | Version actuelle |
| Documents (certificats, listes PDF) | ✅ Fonctionnel | Version actuelle |
| **Bilan Encaissements** (dashboard financier) | ✅ Fonctionnel | Version actuelle |
| **Liste Redevables** par cycle/classe | ✅ Fonctionnel | Version actuelle |
| **Signataires configurables** par cycle et doc | ✅ Fonctionnel | Version actuelle |
| **Design System v4 / Aura** (interface premium) | ✅ Fonctionnel | Version actuelle |
| **Conformité hors ligne complète** (polices locales) | ✅ Fonctionnel | Version actuelle |
| **Tests automatisés** (coverage ≥ 80 %) | ✅ Fonctionnel | Version actuelle |
| **Emploi du temps** (interface complète) | ✅ Fonctionnel | Version actuelle |
| **Échéanciers** (création, modification, suppression) | ✅ Fonctionnel | Version actuelle |
| **Transfert inter-établissements** | 🔧 En développement | Version 4.2 |
| **Procès-verbal du conseil de classe PDF** | ✅ Fonctionnel | Version actuelle |
| **Bulletin de vacation PDF** | ✅ Fonctionnel | Version actuelle |
| **Relevé de notes par discipline** | ✅ Disponible | Version actuelle |
| **Bilan des périodes** | ✅ Disponible | Version actuelle |
| **Portail Parent** | 📌 Planifié | Version 4.2 |
| **Exports Excel / CSV** | 📌 Planifié | Version 4.2 |
| **IA prédictive (décrochage)** | 📌 Planifié | Version 4.x |
| **Multi-établissements (Réseau)** | 📌 Planifié | Version 4.x |
| **Gestion des licences** (interface) | ✅ Fonctionnel | Version actuelle |

---

### 15.1 Emploi du Temps — Interface Complète

> ✅ **Disponible** — Voir la section [14.4 Emploi du Temps](#144-emploi-du-temps)

---

### 15.2 Transfert Inter-Établissements

> **Disponible dans :** Version 4.0

Un élève qui quitte l'établissement pourra faire l'objet d'une demande de transfert officielle. La fonctionnalité permettra de :

- Générer un **dossier de transfert** (relevé de notes, historique, situation financière)
- Marquer l'élève comme « transféré » dans l'établissement d'origine
- Intégrer un élève transféré avec son matricule d'origine (Licence Réseau uniquement)

> Pour l'instant : l'historique complet d'un élève reste dans l'établissement d'origine. Un nouvel établissement peut créer une inscription avec le matricule existant pour assurer la continuité.

---

### 15.3 Gestion des Échéanciers

> **✅ Disponible dans la version actuelle**

La création et la gestion des échéanciers de paiement sont fonctionnelles. Depuis la situation financière d'un élève, tu peux :

- Créer un plan d'échéancier personnalisé par élève (libellé, montant, date limite, rubrique)
- Modifier ou supprimer chaque tranche individuellement
- Associer chaque versement enregistré à une tranche lors du paiement

Consulte la **section 9.4** pour les étapes détaillées.

Les fonctionnalités suivantes restent planifiées pour une version ultérieure :

- Tableau de bord global des tranches : payées, en attente, en retard
- Alertes automatiques à l'approche des dates d'échéance
- Impression du plan d'échéancier individuel pour remise aux parents

---

### 15.4 Procès-verbal du Conseil de Classe (PDF)

> **✅ Disponible dans la version actuelle** — Voir la section [6.6 Conseil de Classe](#66-conseil-de-classe)

Après la saisie des décisions du conseil de classe (section 6.6), le système génère automatiquement un **procès-verbal officiel** en PDF, incluant :

- La liste des élèves avec décision, mention et appréciation individuelle
- L'appréciation générale de la classe
- La date, le président du conseil et la signature
- La liste des enseignants présents

> **Note technique :** La génération PDF nécessite WeasyPrint. Si WeasyPrint n'est pas installé sur le serveur, le système affiche un message d'erreur explicite au lieu de planter.

---

### 15.5 Bulletin de Vacation (PDF)

> **✅ Disponible dans la version actuelle**

Le bulletin de vacation saisi dans le module Vacations (section 11.3) peut être exporté en PDF officiel, incluant :

- L'entête de l'établissement
- Le tableau des heures effectuées par mois
- Le montant total dû
- La signature du responsable

---

### 15.6 Portail Parent

> **Disponible dans :** Version Standard et supérieure — Version 4.1

Les parents ou tuteurs légaux pourront se connecter depuis un téléphone ou un ordinateur pour consulter :

- Les notes et moyennes de leur enfant par trimestre
- Le calendrier des absences et retards
- La situation financière (montants payés, solde restant)
- Les sanctions disciplinaires et convocations
- Les activités parascolaires auxquelles l'enfant est inscrit

> L'accès sera sécurisé par un code parent attribué lors de l'inscription.

---

### 15.7 Exports Excel / CSV

> **Disponible dans :** Version 4.1

En complément des exports PDF existants, les exports Excel permettront de :

- Exporter la liste des élèves avec toutes leurs informations
- Exporter les résultats d'une classe pour traitement externe
- Exporter l'historique des paiements pour la comptabilité
- Exporter les présences pour analyse statistique

---

### 15.8 Gestion des Licences — Interface Complète

> **Disponible dans :** Version 4.0

L'interface de gestion des licences (section 13) est actuellement en cours de finalisation. Les fonctionnalités d'activation, de renouvellement et de suivi des alertes seront pleinement opérationnelles dans la version 4.0.

---

### 15.9 Prédiction des Risques de Décrochage Scolaire (IA)

> **Disponible dans :** Version Premium — Version 4.x

Un module d'intelligence artificielle analysera automatiquement les données de chaque élève (notes en baisse, absences fréquentes, sanctions répétées) pour établir un **score de risque de décrochage**. Le Directeur ou le Proviseur recevra une alerte et pourra engager une action préventive (entretien, conseil aux parents, suivi renforcé).

---

### 15.10 Multi-Établissements — Tableau de Bord Réseau

> **Disponible dans :** Licence Réseau — Version 4.x

Pour les congrégations, fondations et réseaux d'écoles, un tableau de bord consolidé permettra de visualiser :

- Les effectifs de chaque établissement du réseau
- Les encaissements globaux par établissement
- Les performances académiques comparées
- Les transferts d'élèves entre établissements du réseau

---

## 16. QUESTIONS FRÉQUENTES (FAQ)

### Q1. J'ai oublié mon mot de passe. Que faire ?

Contacte ton administrateur système. Il peut réinitialiser ton mot de passe depuis le panneau d'administration. Tu ne peux pas réinitialiser ton mot de passe toi-même par email (le logiciel fonctionne hors ligne).

---

### Q2. Le matricule d'un élève s'affiche « BF-CEN-2526-0001 » — est-ce normal pour le premier élève ?

Oui, c'est parfaitement normal. Le séquenceur repart de 0001 au début de chaque année scolaire. Le matricule est unique grâce à la combinaison région + année + numéro.

---

### Q3. Je veux inscrire un élève mais son matricule n'est pas reconnu. Que faire ?

Cela signifie que l'élève n'a pas encore été **enregistré** dans le système. Va d'abord dans **Élèves → + Nouvel élève** pour créer son dossier, puis reviens dans **Inscriptions** pour l'inscrire.

---

### Q4. J'ai saisi une note incorrecte. Puis-je la modifier ?

Oui. Va dans **Pédagogie → Saisie des notes**, retrouve la classe et l'évaluation concernées, puis modifie la note. Seul l'enseignant concerné, le Directeur ou le Proviseur peuvent modifier une note.

---

### Q5. Un parent veut un certificat de scolarité. Comment le générer ?

Va dans **Documents → Certificat de scolarité**, saisis le matricule de l'élève et clique sur **Générer le certificat**. Le PDF est prêt en quelques secondes, signé par le responsable configuré.

---

### Q6. Plusieurs établissements partagent le même logiciel. Est-ce possible ?

Oui, avec la **Licence Réseau**. Chaque établissement a ses propres données, mais un administrateur réseau peut consulter les statistiques consolidées de tous les établissements.

---

### Q7. Un élève change d'établissement. Son dossier peut-il être transféré ?

La fonctionnalité de transfert inter-établissements est en cours de développement. Pour le moment, l'historique de l'élève (notes, présences, paiements) reste consultable dans l'établissement d'origine. Le nouvel établissement devra créer un nouveau dossier en saisissant le matricule existant.

---

### Q8. Les paiements peuvent-ils être annulés ?

Non directement. En cas d'erreur de saisie, contacte le Directeur ou le Comptable qui peut effectuer une correction avec une justification. Tous les mouvements financiers sont tracés.

---

### Q9. Comment sauvegarder les données ?

Les sauvegardes sont automatiques et gérées par l'administrateur technique. Si le logiciel est installé sur un serveur local, l'administrateur doit configurer les sauvegardes régulières. Contacte ton prestataire technique.

---

### Q10. L'application est lente. Que faire ?

YELEN SCHOOL est conçu pour fonctionner sur des réseaux lents. Si tu constates des lenteurs :
1. Vérifie que tu es bien connecté au réseau local de l'école
2. Ferme les autres onglets de ton navigateur
3. Redémarre ton navigateur
4. Si le problème persiste, contacte l'administrateur technique — le serveur a peut-être besoin d'être redémarré

---

## 17. GLOSSAIRE

| Terme | Définition |
|-------|-----------|
| **Acte de naissance** | Document officiel de l'état civil attestant la naissance d'un enfant |
| **Affecté** | Élève placé dans l'établissement par une décision du Ministère de l'Éducation |
| **Appréciation** | Mention qualitative attribuée à une moyenne (Excellent, Très Bien, etc.) |
| **Archivage PDF** | Sauvegarde automatique et définitive d'un document généré |
| **AVS** | Agent de Vie Scolaire — agent chargé de la surveillance, de la discipline et des présences |
| **BAC** | Baccalauréat — diplôme de fin du cycle secondaire |
| **BEPC** | Brevet d'Études du Premier Cycle — diplôme de fin du cycle post-primaire |
| **Boursier** | Élève bénéficiant d'une aide financière (bourse d'État ou privée) |
| **Bulletin** | Document trimestriel récapitulant les notes et appréciations d'un élève |
| **CEP** | Certificat d'Études Primaires — diplôme de fin du cycle primaire |
| **Censeur** | Responsable de la discipline et de la vie scolaire dans un lycée |
| **Certificat de scolarité** | Document attestant qu'un élève est inscrit dans l'établissement |
| **Coefficient** | Facteur multiplicateur appliqué à la moyenne d'une matière pour calculer la moyenne générale |
| **Conseil de classe** | Réunion trimestrielle des enseignants d'une classe pour évaluer les élèves |
| **Cursus scolaire** | Historique complet des années d'études d'un élève |
| **FCFA** | Franc CFA — monnaie officielle du Burkina Faso et de plusieurs pays d'Afrique de l'Ouest |
| **Feature flag** | Option activée ou non selon le niveau de licence souscrit |
| **Inscription** | Acte officiel d'enregistrement d'un élève dans une classe pour une année scolaire |
| **Licences** | Abonnement au logiciel donnant accès à différents niveaux de fonctionnalités |
| **Matricule** | Identifiant unique et définitif d'un élève ou d'un agent |
| **MENA** | Ministère de l'Éducation Nationale et de l'Alphabétisation (Burkina Faso) |
| **Moyenne générale** | Moyenne pondérée de toutes les matières, tenant compte des coefficients |
| **Non affecté** | Élève inscrit librement, sans affectation du Ministère |
| **PDF/A** | Format de fichier PDF archivable, non modifiable, utilisé pour les documents officiels |
| **Période d'évaluation** | Trimestre ou semestre pendant lequel les notes sont saisies |
| **Poste** | Titre du poste occupé par un agent (Directeur, Enseignant, AVS…) |
| **Post-primaire** | Cycle d'enseignement de la 6ème à la 3ème (après le primaire) |
| **Préscolaire** | Cycle d'enseignement avant le primaire (Petite Section, Moyenne Section, Grande Section) |
| **Proviseur** | Directeur d'un lycée (cycle secondaire) |
| **QR code** | Code graphique scannable permettant de vérifier l'authenticité d'un document |
| **Rang** | Position d'un élève dans le classement de sa classe |
| **Réinscription** | Acte de reconduction d'un élève dans l'établissement pour une nouvelle année scolaire |
| **Redoublant** | Élève qui refait une année après un échec ou une décision du conseil de classe |
| **Rubrique** | Catégorie de frais perçus par l'établissement (scolarité, inscription, cantine…) |
| **Session d'examen** | Période officielle d'organisation d'un examen (CEP, BEPC, BAC) |
| **Signataire** | Membre du personnel désigné pour signer un type de document officiel |
| **Snapshot** | Copie figée des informations (nom, titre du signataire) au moment de la génération d'un document |
| **Statut élève** | Catégorie de l'élève déterminant les tarifs applicables (Nouveau, Affecté, Boursier…) |
| **Super Admin** | Administrateur technique de la plateforme ayant accès à toutes les fonctionnalités |
| **Tarif** | Montant en FCFA correspondant à une rubrique de paiement pour une classe et un statut donnés |
| **Vacation** | Prestation d'enseignement effectuée par un enseignant non fonctionnaire, payé à l'heure |
| **Vacataire** | Enseignant recruté sous contrat de vacation (non fonctionnaire) |

---

*Guide d'utilisation YELEN SCHOOL — Version 3.9 (Guide v1.6) — Mars 2026*

*"Illuminer chaque parcours scolaire"*

*Ce document est mis à jour à chaque nouvelle version du logiciel.*
*Pour toute question, contacte le support technique YELEN SCHOOL.*

---

## 18. DESIGN SYSTEM ET INTERFACE

> **À qui s'adresse cette section :** Administrateurs techniques, développeurs, référents informatiques de l'établissement
>
> **Accès :** Cette section est technique et ne requiert pas d'action de la part des utilisateurs finaux.

---

### 18.1 Principes de Design YELEN SCHOOL

L'interface de YELEN SCHOOL repose sur un système de design cohérent et premium pensé pour les établissements burkinabè.

**Les 5 principes fondamentaux :**

| Principe | Description |
|----------|-------------|
| **Dark mode permanent** | Fond profond `#06101E` (jamais de fond blanc) — repose les yeux et économise l'énergie |
| **Minimalisme premium** | Chaque détail est intentionnel et raffiné — pas d'éléments inutiles |
| **Cohérence absolue** | Les mêmes composants visuels partout — jamais de styles CSS inline dans les templates |
| **Performance** | Animations légères, zéro bibliothèque JavaScript tierce pour les styles |
| **Accessibilité** | Contrastes conformes WCAG, tailles de police lisibles sur écrans BF |

**Palette de couleurs officielle :**

| Rôle | Couleur | Code |
|------|---------|------|
| Fond application | Bleu nuit profond | `#06101E` |
| Surface des cartes | Bleu marine | `#0D1A2D` |
| Couleur principale | Vert Burkina | `#00A86B` |
| Texte principal | Blanc doux | `#E8EDF5` |
| Or (alertes, highlights) | Or chaud | `#F5A623` |
| Erreurs / suppressions | Rouge vif | `#DC3545` |

**Polices utilisées :**

| Usage | Police | Disponibilité |
|-------|--------|---------------|
| Interface (tout le texte) | Segoe UI, Ubuntu, system-ui | Installée sur Windows / Linux |
| Logo « YELEN SCHOOL » uniquement | Playfair Display | Fichier `.woff2` auto-hébergé |
| Matricules et codes | Consolas (Windows) / DejaVu Sans Mono (Linux) | Installée nativement |

> **Règle absolue :** Arial, Inter et Outfit ne doivent jamais apparaître dans les templates. Outfit était utilisé dans les versions antérieures — il a été remplacé par Segoe UI / system-ui pour garantir le fonctionnement hors ligne.

---

### 18.2 Fonctionnement Hors Ligne Complet

> **Depuis la version 3.7, YELEN SCHOOL fonctionne intégralement sans connexion internet.**
>
> Toutes les ressources sont auto-hébergées dans le projet Django, y compris les polices, les icônes et les bibliothèques JavaScript.

**Ressources interdites (bloquées sans réseau) :**

| Ressource | Pourquoi interdite | Alternative dans YELEN SCHOOL |
|-----------|-------------------|-------------------------------|
| `fonts.googleapis.com` | Requête HTTP externe bloquée | Polices `.woff2` dans `static/fonts/` |
| CDN JS/CSS (cdnjs, unpkg, jsdelivr) | Inaccessible sans réseau | Copies locales dans `static/js/` / `static/css/` |
| Images externes (`https://...`) | Indisponibles hors ligne | Images dans `static/img/` |
| APIs externes (météo, maps, analytics) | Aucune pertinence offline | Non intégrées |

**Ce que l'administrateur technique doit vérifier :**

1. **Polices Playfair Display** : fichier `static/fonts/PlayfairDisplay-Bold.woff2` doit exister
2. **HTMX** : fichier `static/js/htmx.min.js` doit être une copie locale (pas un CDN)
3. **Aucun `@import` CDN** dans `yelen.css` ou tout autre fichier CSS
4. **Aucun `<script src="https://...">`** dans les templates HTML

**Comment vérifier la conformité hors ligne :**

```
1. Coupe ton accès internet ou active le mode avion
2. Lance le serveur Django : python manage.py runserver
3. Ouvre YELEN SCHOOL dans le navigateur
4. Vérifie que — la page se charge complètement
                — les polices s'affichent correctement
                — les icônes/symboles sont visibles
                — HTMX fonctionne (formulaires dynamiques)
5. Si une ressource manque → elle apparaît en erreur 404 dans la console du navigateur
```

> **Contexte burkinabè :** Les coupures de réseau sont fréquentes au Burkina Faso. Cette conformité hors ligne est une exigence absolue pour la fiabilité du logiciel dans les établissements.

---

### 18.3 Design System v4 — Refonte Aura

**Nouveautés de la version 4.0 du design system (mars 2026) :**

#### Interface Premium « Aura »

La refonte Aura introduit des effets visuels avancés tout en restant compatible avec les postes burkinabè :

| Composant | Avant (v3) | Après (v4 — Aura) |
|-----------|-----------|-------------------|
| Fond global | `#0A1628` | `#06101E` (plus profond) |
| Sidebar | Fond uni | Dégradé vertical sombre + indicateur actif lumineux |
| Stat-cards | Fond uni | Accent coloré ambiant en coin (glow radial) |
| Badges | Fond coloré plein | Style « cristal » : fond semi-transparent + bordure fine |
| Topbar | Fond opaque | Glassmorphisme (`backdrop-filter: blur`) |
| Ombres | Légères | Ombres élevées premium |

#### Sidebar avec Indicateur Actif Lumineux

La sidebar affiche une **barre verte lumineuse** à gauche de l'item de menu actif, avec un halo (`box-shadow`) pour un rendu premium. Les items inactifs ont un effet de survol avec fond légèrement coloré.

#### Stat-Cards avec Accent Ambiant

Les 4 cartes statistiques du tableau de bord affichent chacune une **lueur colorée radiale** dans le coin supérieur droit — effet « ambient light » :

- 🟢 **Élèves inscrit** → Vert `#00A86B`
- 🔵 **Classes actives** → Bleu `#17A2B8`
- 🟡 **Personnel** → Or `#F5A623`
- 🔴 **Finances** → Rouge `#DC3545`

Chaque carte affiche aussi une mini-barre de progression en bas et un indicateur de tendance (↑ hausse / ↓ baisse).

#### Badges Cristal

Les badges d'état (statut élève, rôle utilisateur, état de paiement) adoptent un style « cristal » v4 :

- Fond semi-transparent (15% d'opacité de la couleur)
- Bordure fine colorée (25% d'opacité)
- Texte lumineux correspondant à la couleur du badge

**Correspondance des couleurs de badges :**

| Badge | Couleur |
|-------|---------|
| Affecté / Succès / Actif | Vert cristal |
| Non affecté / Avertissement | Or cristal |
| Redoublant / Erreur / Inactif | Rouge cristal |
| Boursier / Info | Bleu cristal |
| Rôle technique (Super Admin) | Violet cristal |

---

### 18.4 Guide Administrateur Technique

#### Préparer les Polices Hors Ligne (Une Seule Fois)

Si les polices Playfair Display ne sont pas encore dans le projet :

```bash
# 1. Télécharger les polices (connexion internet requise une seule fois)
#    https://fonts.google.com/specimen/Playfair+Display
# 2. Installer les outils de conversion
pip install fonttools brotli
# 3. Convertir en woff2
python -c "
from fontTools.ttLib.woff2 import compress
compress('PlayfairDisplay-VariableFont_wght.ttf', 'PlayfairDisplay-Bold.woff2')
"
# 4. Copier dans le projet Django
mkdir -p e:/yelen-school/static/fonts
cp PlayfairDisplay-Bold.woff2 e:/yelen-school/static/fonts/
```

#### Collecte des Fichiers Statiques (Déploiement)

Avant de déployer en production, exécute la collecte des fichiers statiques :

```bash
python manage.py collectstatic --noinput
```

Cela copie tous les fichiers de `static/` vers `STATIC_ROOT` configuré dans `settings.py`.

#### Redémarrage du Serveur après Mise à Jour

```bash
# Arrêter le serveur Django
Ctrl + C

# Appliquer les migrations si nécessaire
python manage.py migrate

# Relancer le serveur
python manage.py runserver 0.0.0.0:8000
```

#### Variables d'Environnement Obligatoires

Le fichier `.env` à la racine du projet doit contenir :

```
DATABASE_URL=postgresql://user:password@host:5432/yelen_school
SECRET_KEY=...valeur-secrète...
DEBUG=False
ALLOWED_HOSTS=192.168.X.X,localhost
```

> **Règle absolue :** PostgreSQL est obligatoire. L'utilisation de SQLite (même en développement) est interdit. Utilise Docker Compose pour démarrer PostgreSQL en local.

#### Démarrer l'Environnement de Développement avec Docker

```bash
# Démarrer PostgreSQL et Redis en arrière-plan
docker-compose -f docker-compose.dev.yml up -d

# Lancer le serveur Django
python manage.py runserver
```

---

### 18.5 Système de Notifications

**À quoi ça sert :** YELEN SCHOOL envoie des notifications dans l'application pour informer les utilisateurs des événements importants qui les concernent : absence signalée, bulletin publié, paiement reçu, sanction disciplinaire…

**Qui peut accéder :** Tous les profils (chaque utilisateur voit ses propres notifications)

**Accès :** Cloche 🔔 en haut à droite de l'écran, ou `Menu → Notifications`

#### Types de Notifications

| Type | Déclencheur |
|------|-------------|
| ABSENCE | Enregistrement d'une absence (appel) |
| BULLETIN | Publication d'un bulletin trimestriel |
| SANCTION | Enregistrement d'une sanction disciplinaire |
| GENERAL | Relance de paiement, convocation,等信息 |

#### Consulter les Notifications

```
╔══════════════════════════════════════════════════════════════╗
║  🔔  Notifications (3)                                       ║
╠══════════════════════════════════════════════════════════════╣
║  🔴 Absence signalée — 08/04/2026            il y a 10 min   ║
║     SAWADOGO Aminata était absente en Mathématiques.         ║
║  🔵 Bulletin de KONÉ Issa publié            il y a 1h        ║
║  ○ Paiement de 25 000 F reçu — OUÉDRAOGO   il y a 3h         ║
║                                                              ║
║  [ Tout marquer comme lu ]                                   ║
╚══════════════════════════════════════════════════════════════╝
```

- **Point rouge 🔴** = notification non lue (ABSENCE)
- **Point bleu 🔵** = notification non lue (autres)
- **Point vide ○** = notification déjà lue

#### Marquer comme Lu

- Clique sur le bouton ✅ pour marquer une notification comme lue
- Clique sur **Tout marquer comme lu** pour effacer le compteur du badge

> **Badge numérique :** Le chiffre rouge sur la cloche indique le nombre de notifications non lues. Il disparaît quand toutes les notifications ont été consultées.

#### Notifications des Absences aux Parents

Pour que les parents reçoivent les notifications d'absence :

1. **Créer un compte parent** : Menu → Utilisateurs → Compte parent
2. **Lier le parent à l'élève** : Cocher les enfants du parent lors de la création
3. **Numéro de téléphone** : Le SMS est envoyé au numéro enregistré (téléphone_parent, tuteur_telephone, ou telephone_urgence)

> **Important :** Sans compte parent lié, les notifications d'absence sont envoyées par SMS uniquement (si configuré).

---

### 18.6 Journal d'Audit (Traçabilité)

**À quoi ça sert :** Enregistre automatiquement toutes les actions importantes effectuées dans YELEN SCHOOL (création, modification, suppression de données, connexions…). Ce journal permet de savoir qui a fait quoi et quand, pour garantir la sécurité et la traçabilité des opérations.

**Qui peut accéder :** Directeur, Proviseur, Super Admin

**Accès :** `Paramètres → Journal d'audit` ou `Menu → Journal d'audit`

#### Consulter le Journal

```
┌──────────────────────────────────────────────────────────────────────────┐
│  📋 Journal d'Audit — Lycée Zinda                                        │
├──────────────┬────────────────┬─────────────────────────────────────────┤
│  Date/Heure  │ Utilisateur    │ Action                                   │
├──────────────┼────────────────┼─────────────────────────────────────────┤
│  06/04 08h32 │ KONÉ Seydou    │ Modification inscription — OUÉD. B.      │
│  06/04 08h15 │ BARRY Fatou    │ Paiement enregistré — 25 000 F           │
│  06/04 07h58 │ TRAORÉ Ibrahim │ Connexion depuis 192.168.1.14            │
│  05/04 17h22 │ KONÉ Seydou    │ Génération PDF bulletin — Terminale A    │
│  05/04 16h44 │ SAWADOGO Hawa  │ Suppression évaluation — Maths 3ème B   │
└──────────────┴────────────────┴─────────────────────────────────────────┘
│  Filtres : [Date] [Utilisateur] [Type d'action]   [ 🖨 Exporter PDF ]   │
└──────────────────────────────────────────────────────────────────────────┘
```

#### Filtrer et Exporter

- **Filtre par date** : consulte les actions d'une journée, semaine ou période précise
- **Filtre par utilisateur** : vois toutes les actions d'un membre du personnel spécifique
- **Filtre par type** : connexions, modifications, suppressions, générations de documents…
- **Exporter PDF** : génère un rapport imprimable de la période sélectionnée

> **Cas d'usage :** Un directeur remarque qu'une note a été modifiée. Il consulte le journal d'audit, filtre par type « modification de note », et identifie immédiatement quel enseignant a effectué la modification, à quelle heure et depuis quelle adresse réseau.

> **Conservation :** Les entrées du journal sont conservées indéfiniment. Elles ne peuvent pas être supprimées par les utilisateurs normaux.

---

### 18.7 Réunion de Parents

**À quoi ça sert :** Affiche les informations pratiques relatives à la prochaine réunion de parents organisée par l'établissement (date, heure, lieu, ordre du jour). Cette page est accessible aux enseignants et au personnel pour se rappeler les détails.

**Qui peut accéder :** Tous les profils connectés

**Accès :** `Menu principal → Réunion de parents` ou via le tableau de bord

```
╔══════════════════════════════════════════════════════════════╗
║  👨‍👩‍👧 Réunion de Parents — Lycée Zinda                        ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  📅 Date    : Vendredi 18 avril 2026                         ║
║  🕒 Heure   : 15h00 – 18h00                                  ║
║  📍 Lieu    : Salle de conférences (bâtiment A)               ║
║                                                              ║
║  Ordre du jour :                                             ║
║  1. Résultats du 2ème trimestre                              ║
║  2. Comportement et assiduité                                ║
║  3. Préparation des examens de fin d'année                   ║
║  4. Questions diverses                                       ║
║                                                              ║
║  Contact : secrétariat@lyceezinda.bf — +226 25 30 10 10      ║
╚══════════════════════════════════════════════════════════════╝
```

> **Note :** Cette page est gérée par l'administrateur de l'établissement. Pour mettre à jour les informations de réunion, contacte le Directeur ou le Secrétariat.

---

### 18.8 Navigation Moderne — Sidebar v5.0

**À quoi ça sert :** La nouvelle sidebar moderne offre une expérience utilisateur premium avec une navigation simplifiée, une recherche instantanée et des menus accordéon pour regrouper les fonctionnalités par thématique (Scolarité, Pédagogie, Gestion, Système).

**Nouveautés de la v5.0 :**
- **Recherche Instantanée** : Filtre les menus en temps réel au fur et à mesure de la saisie.
- **Menus Accordéon Premium** : Organisation élégante avec animations fluides, indicateurs lumineux et effets de survol sophistiqués.
  - Animation d'ouverture avec transition `scaleY` et `translateY`
  - Effet de barre lumineuse sur les items actifs
  - Points lumineux animés sur les items de sous-menu
  - Stagger animation pour un effet d'entrée élégant
  - Indicateur de rotation du chevron avec easing cubic-bezier
- **Design Premium** : Utilisation de la police interface **Outfit**, icônes SVG raffinées et effets de survol dynamiques.
- **Feedback Actuel** : Le menu s'ouvre automatiquement sur la section active.

```
╔══════════════════════════════════╗
║  🎓 YELEN SCHOOL                 ║
║  Burkina Faso · v4.2             ║
╠══════════════════════════════════╣
║  🔍 [ Rechercher...            ] ║
╠══════════════════════════════════╣
║  🏠 Tableau de bord              ║
║                                  ║
║  SCOLARITÉ                       ║
║  > 👤 Élèves & Inscriptions      ║
║    - Liste des élèves            ║
║    - Nouvelle inscription        ║
║                                  ║
║  PÉDAGOGIE                       ║
║  📄 Notes & Bulletins            ║
║  > 🛡️ Vie Scolaire               ║
║                                  ║
║  GESTION                         ║
║  > 💼 Finances                   ║
║    - Paiements / Scolarité       ║
║    - Échéanciers                 ║
╚══════════════════════════════════╝
```

---

### 18.9 Journal des Modifications

> **À qui s'adresse cette section :** Administrateurs techniques et développeurs souhaitant suivre l'évolution du code.

---

#### Version 4.2 — 14 Avril 2026

**Refonte Navigation & Design System**
- **Sidebar v5.0** : Implémentation d'une sidebar moderne (HTML5/CSS3) avec recherche dynamique et accordéons.
- **Sidebar Accordéons Premium** : Refonte complète des menus déroulants avec :
  - Animation d'ouverture fluide avec `scaleY` et `translateY`
  - Barre lumineuse verticale sur les items actifs avec effet `box-shadow` vert
  - Points lumineux animés sur les items de sous-menu avec `box-shadow` pulsant
  - Stagger animation (décalage progressif) sur l'apparition des items
  - Chevrons avec rotation élégante et easing `cubic-bezier`
  - Hover effect avec gradient overlay et scale de l'icône
- **Icônes modernisées** : Remplacement des icônes par des designs SVG Lucide-style plus fins (`stroke-width="1.5"`).
- **Page Suivi des Appels Premium** : Refonte complète avec :
  - Header avec icône梯形 et stats cards
  - Timeline élégante avec regroupement par date
  - Cards de session avec badge de statut
  - Tableaux modernes avec indicateurs colorés
  - États vides élégants
- **Police Outfit** : Adoption de la police *Outfit* comme standard d'interface (100% offline).
- **Design Premium** : Ajustement des contrastes (fond `#0A1628`), suppression des bordures rigides au profit de micro-shadows et glassmorphism.
- **Optimisation JS** : Scripts de navigation natifs (zéro dépendance) avec protection contre la double-soumission et auto-hide des messages.

**Stabilité & Correction**
- Restauration des fermetures de tags HTML dans `base.html`.
- Correction de la logique de recherche sidebar pour gérer les remontées de parents d'accordéons.

---

*Guide d'utilisation YELEN SCHOOL — Version 4.2 (Guide v2.7) — 14 Avril 2026*

*"Illuminer chaque parcours scolaire"*

*Ce document est mis à jour à chaque nouvelle version du logiciel.*
*Pour toute question, contacte le support technique YELEN SCHOOL.*
