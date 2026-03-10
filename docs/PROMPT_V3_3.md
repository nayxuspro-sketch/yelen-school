🎓

__YELEN SCHOOL__

*Système de Gestion Scolaire — Burkina Faso*

*"Illuminer chaque parcours scolaire"*

__PROMPT FINAL OPTIMISÉ — VERSION COMMERCIALE v3\.3__

*Incluant : Modules Enregistrement · Inscription/Réinscription \(par matricule\) · Agent de Vie Scolaire*

*Paramètres · Documents · Carte d'Identité · Vacations · ⭐ Personnel · ⭐ Statistiques Listes Classes*

__Élément__

__Détail__

__Statut__

Version

v3\.3 — Mars 2026

Mis à jour

Nouveautés v3\.3

Calcul automatique âge à l'enregistrement · Affichage date naissance \+ âge calculé à l'inscription \(lecture seule\)

⭐ Nouveau

Nouveautés v3\.2

Gestion Personnel \(matricule PERS\-, inscription annuelle, liste H/F\) · Statistiques listes élèves

Confirmé

Nouveautés v3\.1

Matricule élève unique · Inscription par matricule · Directeur/Proviseur · Vacations

Confirmé

Nouveautés v3\.0

Enregistrement, Inscription, AVS, Paramètres enrichis, Carte ID

Confirmé

Cycles

Préscolaire · Primaire · Post\-primaire · Secondaire

MVP

Stack

Django 4\.2 · DRF · PostgreSQL · Redis · Docker

Inchangé

Modèle commercial

Open\-Source \+ Licences vendables

Inchangé

Deadline

1er Août 2026 — avant inscriptions de septembre

Non négociable

# 1\. CONTRAINTES ABSOLUES DU PROJET

⚠️  Non négociables

Ces 4 contraintes guident chaque décision architecturale, technologique et organisationnelle du projet YELEN SCHOOL\.

## 1\.1 Deadline — Déploiement avant septembre

- Date cible de mise en production : 1er Août 2026 au plus tard
- Période de tests et formation utilisateurs : 2 premières semaines d'août
- Prioriser un MVP fonctionnel sur une solution parfaite mais tardive
- Sprints de 2 semaines avec livrables testables à chaque fin de sprint
- Distinction claire : fonctionnalités MVP obligatoires vs V2 reportables

## 1\.2 Projet 100% Open\-Source & Zéro Budget

- Aucun service payant, aucune licence commerciale
- Toutes les bibliothèques et outils doivent être gratuits et open\-source
- Solutions auto\-hébergées \(self\-hosted\) privilégiées
- Alternatives open\-source explicitement nommées pour chaque composant

## 1\.3 Déploiement Docker optimisé

- Intégralité de l'application conteneurisée avec Docker
- Déploiement en une seule commande : docker\-compose up \-d
- Images multi\-stage build \(cible < 200 MB par image\)
- Configurations séparées : docker\-compose\.dev\.yml et docker\-compose\.prod\.yml
- Pipeline CI/CD gratuit avec GitHub Actions

## 1\.4 Modèle Commercial — Vente de licences

- Application open\-source avec licence d'utilisation commercialement vendable
- Système de licences robuste, infalsifiable et auditable
- 4 niveaux de licences adaptés aux différentes tailles d'établissements
- Module de gestion des licences totalement indépendant du reste de l'application

# 2\. ARCHITECTURE TECHNIQUE

## 2\.1 Structure des applications Django — mise à jour v3\.1

__App Django__

__Responsabilité__

__Priorité__

core

Modèles de base, utilitaires partagés, middleware global

MVP

accounts

Authentification, rôles, permissions RBAC

MVP

licences

Gestion complète des licences commerciales

MVP — CRITIQUE

etablissements

Multi\-établissements, configuration, cycles scolaires

MVP

parametres

⭐ NOUVEAU : Identité étab\., cycles, classes, postes, statuts, rubriques, appréciations, périodes, disciplines

MVP

inscriptions

⭐ MIS À JOUR : Enregistrement élèves, inscription, réinscription, matricules, transferts

MVP

personnel

⭐ NOUVEAU v3\.2 : Enregistrement personnel, inscription/réinscription annuelle, matricule unique, liste H/F

MVP

pedagogie

Classes, matières, emplois du temps, saisie des notes

MVP

bulletins

Génération bulletins MENA, moyennes, coefficients officiels

MVP

presences

⭐ MIS À JOUR : Pointage, absences élèves et professeurs, discipline via AVS

MVP

vacations

⭐ NOUVEAU v3\.1 : Inscription vacataires, affectations, heures réalisées, bilan mensuel

MVP

examens

CEP, BEPC, BAC, listes candidats, PV officiels

MVP

finances

Frais scolaires, paiements, reçus PDF, comptabilité

MVP

documents

Certificats, attestations, cursus, autorisations, carte ID scolaire

MVP

parents

Portail parents, messagerie, notifications

V2

rh

Dossiers enseignants, salaires, congés

V2

ressources

Salles, bibliothèque, inventaire, cantine

V2

reporting

Tableaux de bord, exports PDF/Excel, statistiques MENA

V2

## 2\.2 Rôles et permissions — mise à jour v3\.1

__Rôle__

__Accès__

__Description__

Super Admin Éditeur

Global

Gestion licences, portail éditeur, accès tous établissements

Directeur

Établissement

Vue 360°, tous modules, rapports, signature documents

Censeur / Proviseur

Établissement

Discipline, présences, autorisations d'absence

Agent de Vie Scolaire

Établissement

⭐ NOUVEAU : Absences élèves & professeurs, discipline, registres

Enseignant

Ses classes

Notes, présences, bulletins de ses élèves

Comptable

Finances

Frais, paiements, attestations de non\-redevabilité

Secrétaire

Administratif

Enregistrement élèves, délivrance documents officiels

Parent

Son enfant

Notes, bulletins, absences, demande documents

Élève

Son dossier

Consultation notes, emploi du temps, demande documents

# 3\. MODULE LICENCES — PRIORITÉ MAXIMALE

🔐 Ce module est le cœur commercial du projet\.

Développé en Phase 1 \(semaines 3\-4\) avant tout autre module métier\.

Sans lui, le modèle économique ne tient pas\.

## 3\.1 Niveaux de licences

__Niveau__

__Cible__

__Élèves max / Prix/an__

🥉 Starter — Licence Découverte

Petites écoles maternelles/primaires

< 150 élèves — 50 000 FCFA

🥈 Standard — Licence Essentielle

Écoles primaires moyennes

150–500 élèves — 150 000 FCFA

🥇 Premium — Licence Intégrale

Lycées et grands établissements

500–2000 élèves — 350 000 FCFA

🏆 Réseau — Licence Groupe

Groupes scolaires privés multi\-sites

> 2000 élèves — Sur devis

## 3\.2 Feature Flags par niveau

__Feature__

__Starter / Standard__

__Premium / Réseau__

Inscriptions & dossiers

✅ / ✅

✅ / ✅

⭐ Enregistrement élèves

✅ / ✅

✅ / ✅

⭐ Carte d'identité scolaire

✅ / ✅

✅ / ✅

Notes & bulletins MENA

✅ / ✅

✅ / ✅

Présences & discipline \(AVS\)

✅ / ✅

✅ / ✅

Finances de base

✅ / ✅

✅ / ✅

Certificats de scolarité

✅ / ✅

✅ / ✅

Attestations non\-redevabilité

✅ / ✅

✅ / ✅

Autorisations d'absence

✅ / ✅

✅ / ✅

Cursus scolaire complet

❌ / ✅

✅ / ✅

Examens officiels CEP/BEPC/BAC

❌ / ✅

✅ / ✅

Portail parents

❌ / ✅

✅ / ✅

IA pédagogique prédictive

❌ / ❌

✅ / ✅

Multi\-établissements

❌ / ❌

❌ / ✅

# 4\. ⭐ MODULE PARAMÈTRES — NOUVEAU v3\.0

📋 App Django : parametres — Ajout v3\.0

Ce module centralise toute la configuration de l'établissement scolaire\.

Il doit être configuré en premier, avant tout autre module, car tous les autres modules en dépendent\.

Accessible uniquement par le Directeur et le Super Admin Éditeur\.

## 4\.1 Identité de l'Établissement

### Modèle Django — IdentiteEtablissement

parametres/models\.py — IdentiteEtablissement

id · nom\_etablissement · sigle \(optionnel\) · type\_etablissement \(public/prive/confessionnel\)

· numero\_agrement\_mena · date\_agrement · adresse\_complete · ville · province · region

· telephone · email · site\_web \(optionnel\) · logo \(ImageField MinIO\)

· nom\_directeur · signature\_directeur \(ImageField — signature numérique pour les documents officiels\)

· cachet\_etablissement \(ImageField — image du cachet pour PDF\) · devise \(texte libre optionnel\)

· statut\_actif \(BooleanField\) · created\_at · updated\_at

Fonctionnalités :

- Un seul enregistrement par établissement \(singleton pattern\)
- Logo et signature utilisés automatiquement dans tous les documents PDF générés
- Numéro d'agrément MENA affiché sur bulletins, certificats et tous documents officiels
- Interface d'administration dédiée avec aperçu visuel en\-tête PDF

## 4\.2 Cycles Scolaires

### Modèle Django — Cycle

parametres/models\.py — Cycle

id · nom \(Préscolaire / Primaire / Post\-primaire / Secondaire\) · code \(PRES/PRIM/POST/SEC\)

· ordre\_affichage · actif \(BooleanField\) · etablissement \(FK\) · created\_at

Cycles standards Burkina Faso :

- Préscolaire : Crèche, Petite Section \(PS\), Moyenne Section \(MS\), Grande Section \(GS\)
- Primaire : CP1, CP2, CE1, CE2, CM1, CM2
- Post\-primaire : 6ème, 5ème, 4ème, 3ème
- Secondaire : Seconde, Première, Terminale \(séries A, B, C, D\)

## 4\.3 Classes

### Modèle Django — Classe

parametres/models\.py — Classe

id · nom \(ex: 6ème A, CM2 B\) · code \(ex: 6A, CM2B\) · cycle \(FK Cycle\) · niveau

· capacite\_max \(IntegerField — nombre max d'élèves autorisés dans la classe\)

· est\_classe\_examen \(BooleanField — True si CEP / BEPC / BAC cette année\)

· type\_examen \(CharField nullable : CEP / BEPC / BAC\_A / BAC\_B / BAC\_C / BAC\_D\)

· annee\_scolaire \(FK AnneeScolaire\) · salle\_principale \(FK Salle optionnel\)

· actif \(BooleanField\) · created\_at

Règles métier :

- Capacité maximale : alerte si inscription dépasse la capacité configurée
- Classe d'examen : active automatiquement les modules CEP/BEPC/BAC correspondants
- Une classe appartient obligatoirement à un cycle et à une année scolaire

## 4\.4 Postes du Personnel

### Modèle Django — Poste

parametres/models\.py — Poste

id · intitule \(ex: Directeur, Censeur, Enseignant, Comptable, Secrétaire, AVS\)

· code · type\_poste \(administratif / pedagogique / support\) · description

· localisation \(FK LocalisationPoste — bureau ou salle de classe\)

· actif \(BooleanField\) · created\_at

### Modèle Django — LocalisationPoste

parametres/models\.py — LocalisationPoste

id · nom \(ex: Bureau Direction, Salle des professeurs, Salle 12B\)

· type\_localisation \(bureau / salle\_classe / laboratoire / autre\)

· batiment \(optionnel\) · etage \(optionnel\) · actif \(BooleanField\) · created\_at

## 4\.5 Statuts de l'Élève

### Modèle Django — StatutEleve

parametres/models\.py — StatutEleve

id · libelle \(ex: Affecté par l'État, Non affecté, Boursier, Exonéré, Redoublant\)

· code \(ex: AFFECTE / NON\_AFFECTE / BOURS / EXON / REDOUB\)

· description · couleur\_affichage \(CharField hexadécimal — pour badges UI\)

· actif \(BooleanField\) · ordre\_affichage · created\_at

Note : Ce statut détermine directement le montant de scolarité applicable \(voir 4\.6\)\.

Statuts standards Burkina Faso :

- Affecté par l'État : élève orienté/affecté dans un établissement privé par les services de l'État
- Non affecté : élève inscrit librement, sans affectation officielle de l'État
- Boursier : élève bénéficiaire d'une bourse \(état ou privée\)
- Exonéré : élève dispensé totalement ou partiellement des frais de scolarité
- Redoublant : élève qui reprend la même classe

## 4\.6 Rubriques de Paiement — Logique Avancée

💰 Règle métier critique : le montant de scolarité varie selon \(classe × statut élève\)\.

Exemple : En 6ème, un élève Affecté par l'État paie 45 000 FCFA,

         un élève Non affecté paie 120 000 FCFA pour la même classe\.

Cette matrice classe × statut doit être entièrement configurable\.

### Modèle Django — RubriquePaiement

parametres/models\.py — RubriquePaiement

id · libelle \(ex: Frais inscription, Scolarité, Cantine, Transport, APE, Sport\)

· code · type\_rubrique \(inscription / scolarite / cantine / transport / autre\)

· periodicite \(annuel / trimestriel / mensuel / unique\) · obligatoire \(BooleanField\)

· actif \(BooleanField\) · created\_at

### Modèle Django — TarifScolarite \(matrice classe × statut\)

parametres/models\.py — TarifScolarite

id · classe \(FK Classe\) · statut\_eleve \(FK StatutEleve\) · rubrique \(FK RubriquePaiement\)

· montant \(DecimalField 12,2\) · annee\_scolaire \(FK AnneeScolaire\)

· actif \(BooleanField\) · created\_at

Contrainte unique : \(classe, statut\_eleve, rubrique, annee\_scolaire\) — un seul tarif par combinaison\.

Méthode : TarifScolarite\.get\_montant\(classe, statut\_eleve, rubrique, annee\) → Decimal

Exemple de configuration tarifaire :

__Classe__

__Statut Élève__

__Montant Scolarité annuel__

6ème A

Affecté par l'État

45 000 FCFA

6ème A

Non affecté

120 000 FCFA

6ème A

Boursier

30 000 FCFA

6ème A

Exonéré

0 FCFA

Terminale C

Affecté par l'État

60 000 FCFA

Terminale C

Non affecté

180 000 FCFA

## 4\.7 Appréciations de Conduite

### Modèle Django — AppreciationConduite

parametres/models\.py — AppreciationConduite

id · libelle \(ex: Très Bien, Bien, Assez Bien, Passable, Insuffisant, Mauvais\)

· code · note\_min \(Decimal\) · note\_max \(Decimal\) · couleur \(hex\)

· actif \(BooleanField\) · ordre\_affichage · created\_at

Usage : Affichée dans les bulletins scolaires, registres discipline AVS et documents officiels\.

## 4\.8 Années Scolaires

### Modèle Django — AnneeScolaire

parametres/models\.py — AnneeScolaire

id · libelle \(ex: 2025\-2026\) · date\_debut · date\_fin · est\_courante \(BooleanField unique True\)

· statut \(en\_preparation / en\_cours / cloturee\) · etablissement \(FK\) · created\_at

Signal : quand est\_courante passe à True, les autres années passent automatiquement à False\.

## 4\.9 Disciplines Enseignées

### Modèle Django — Discipline

parametres/models\.py — Discipline

id · nom \(ex: Mathématiques, Français, SVT, Histoire\-Géographie, EPS\)

· code · cycles \(ManyToMany Cycle — dans quels cycles cette discipline est enseignée\)

· coefficient\_default \(DecimalField — coefficient par défaut, surchargeable par classe\)

· est\_evaluee \(BooleanField — si False : enseignée mais non notée ex: orientation\)

· type\_discipline \(litteraire / scientifique / artistique / sportif / autre\)

· actif \(BooleanField\) · ordre\_affichage · created\_at

## 4\.10 Périodes d'Évaluation

### Modèle Django — PeriodeEvaluation

parametres/models\.py — PeriodeEvaluation

id · libelle \(ex: 1er Trimestre, 2ème Trimestre, 3ème Trimestre — ou 1er Semestre, 2ème Semestre\)

· code \(T1/T2/T3 ou S1/S2\) · type\_periode \(trimestriel / semestriel\)

· ordre \(IntegerField — 1, 2, 3\.\.\.\)

· date\_debut · date\_fin · annee\_scolaire \(FK AnneeScolaire\)

· actif \(BooleanField\) · created\_at

Règle : Le système accepte aussi bien 3 trimestres que 2 semestres selon la configuration de l'établissement\.

Les bulletins et calculs de moyennes s'adaptent automatiquement au type de période configuré\.

Exemples de configuration :

- 3 Trimestres : T1 \(Oct\-Déc\), T2 \(Jan\-Mar\), T3 \(Avr\-Juin\) — le plus courant au Burkina Faso
- 2 Semestres : S1 \(Oct\-Fév\), S2 \(Fév\-Juin\) — certains lycées techniques

## 4\.11 Résumé des modèles du module Paramètres

__Modèle__

__Description courte__

IdentiteEtablissement

Logo, coordonnées, signature directeur, cachet officiel

Cycle

Préscolaire, Primaire, Post\-primaire, Secondaire

Classe

Nom, capacité max, classe d'examen \(CEP/BEPC/BAC\), cycle

Poste

Titre du personnel \(Directeur, AVS, etc\.\)

LocalisationPoste

Bureau ou salle de classe pour localiser le personnel

StatutEleve

Affecté, Non affecté, Boursier, Exonéré, Redoublant…

RubriquePaiement

Types de frais : scolarité, inscription, cantine…

TarifScolarite

Matrice \(classe × statut × rubrique\) → montant FCFA

AppreciationConduite

Grille d'appréciation comportementale pour bulletins

AnneeScolaire

Année courante, dates début/fin, statut

Discipline

Matières par cycle, coefficient, évaluée ou non

PeriodeEvaluation

Trimestres ou semestres selon l'établissement

# 5\. ⭐ ENREGISTREMENT DES ÉLÈVES — MISE À JOUR v3\.1

📋 App Django : inscriptions — Module Enregistrement

L'enregistrement est la première étape du parcours d'un élève dans le système\.

Il collecte toutes les informations personnelles et administratives de l'élève

et les enregistre dans la base de données AVANT toute inscription dans une classe\.

Un élève enregistré n'est pas encore inscrit dans une classe\.

⭐ RÈGLE FONDAMENTALE v3\.1 — LE MATRICULE EST LA CLÉ UNIQUE DE L'ÉLÈVE :

À partir du moment où un élève est enregistré, son MATRICULE devient sa référence unique

dans TOUT le système\. Toute recherche, sélection ou opération ultérieure \(inscription,

paiement, bulletins, documents, absences, discipline…\) se fait par matricule\.

Le matricule est généré automatiquement et non modifiable après création\.

## 5\.1 Modèle Django — Eleve \(enrichi\)

inscriptions/models\.py — Eleve

── Identification ──

id · matricule \(unique, auto\-généré : BF\-\{REGION\}\-\{ANNEE\}\-\{SEQ:04d\}\)

numero\_extrait\_naissance · date\_etablissement\_extrait · commune\_etablissement

· nom · prenom · date\_naissance · lieu\_naissance · sexe \(M/F\)

· nationalite \(default: Burkinabè\) · langue\_maternelle \(optionnel\)

── État ──

· actif \(BooleanField — case à cocher : actif / inactif dans l'établissement\)

· exonere \(BooleanField — case à cocher : exonération totale des frais\)

· statut\_eleve \(FK StatutEleve : Affecté/Non affecté/Boursier…\)

· motif\_inactivite \(CharField nullable : exclusion / départ / décès / transfert…\)

· date\_inactivite \(DateField nullable\)

── Famille ──

· nom\_pere · prenom\_pere · profession\_pere · telephone\_pere

· nom\_mere · prenom\_mere · profession\_mere · telephone\_mere

· nom\_tuteur · prenom\_tuteur · lien\_tuteur · telephone\_tuteur

· adresse\_famille · quartier · ville\_residence

── Documents ──

· photo \(ImageField MinIO — photo d'identité pour carte scolaire\)

· acte\_naissance \(FileField MinIO\) · carnet\_vaccination \(FileField MinIO\)

· jugement\_suppletif \(FileField MinIO — si pas d'acte de naissance\)

· certificat\_medical \(FileField MinIO — optionnel\)

── Métadonnées ──

· etablissement \(FK Etablissement\) · enregistre\_par \(FK User\)

· created\_at · updated\_at

## 5\.2 Interface d'Enregistrement

### Formulaire secrétariat — Écran Enregistrement Nouvel Élève

Le formulaire d'enregistrement est organisé en 4 onglets / étapes :

- Étape 1 — Identité civile : nom, prénom, date/lieu naissance, sexe, nationalité, extrait de naissance
- Étape 2 — Famille et contact : père, mère, tuteur, adresse, quartier
- Étape 3 — Documents : upload photo, acte naissance, carnet vaccination, pièces jointes
- Étape 4 — Statut et paramètres :
- ☐ Actif \(coché par défaut à la création\)
- ☐ Exonéré \(décoché par défaut — cocher si l'élève est exonéré de frais\)
- Statut élève : liste déroulante \(Affecté / Non affecté / Boursier…\)

### ⭐ Calcul automatique de l'âge à l'Enregistrement — v3\.3

Comportement UX — Champ Âge à l'enregistrement :

• Dès que l'opérateur saisit \(ou sélectionne\) la DATE DE NAISSANCE dans l'Étape 1,

  le système calcule immédiatement l'âge de l'élève et l'affiche dans un champ

  en LECTURE SEULE \(non saisie\) juste à côté ou en dessous de la date de naissance\.

• Le champ âge est automatiquement recalculé si la date de naissance est modifiée\.

• L'âge affiché est calculé par rapport à la DATE DU JOUR \(date de l'enregistrement\)\.

  Formule : âge = aujourd'hui \- date\_naissance \(en années entières révolues\)

• Le champ âge est visuel uniquement — il n'est PAS stocké en base de données\.

  L'âge est toujours recalculé dynamiquement à partir de la date de naissance\.

Exemple d'affichage dans l'Étape 1 :

  Date de naissance : \[ 15 / 03 / 2014 \]   Âge : \[ 11 ans \]  \(lecture seule, fond grisé\)

__Aspect technique__

__Détail d'implémentation__

Déclencheur

Événement onChange sur le champ date\_naissance \(frontend JS/React\)

Calcul JS frontend

const age = differenceInYears\(new Date\(\), new Date\(dateNaissance\)\) — librairie date\-fns

Calcul backend

Property Python sur le modèle Eleve : @property def age\(self\): return \(date\.today\(\) \- self\.date\_naissance\)\.days // 365

Stockage

Non stocké en base — calculé dynamiquement à chaque affichage

Style du champ

Champ désactivé \(disabled\), fond grisé \(\#F5F5F5\), bordure pointillée — différenciation visuelle claire avec les champs saisie

Libellé affiché

'X an\(s\)' — ex : '11 ans', '6 ans', '17 ans'

Règles de validation :

- Photo obligatoire \(nécessaire pour la carte d'identité scolaire\)
- Soit acte de naissance SOIT jugement supplétif obligatoire
- Numéro matricule généré automatiquement à la sauvegarde
- L'enregistrement ne déclenche PAS d'inscription automatique

## 5\.3 Champs Actif / Exonéré — Comportement

__Champ__

__Comportement système__

☑ Actif = True \(défaut\)

Élève visible dans toutes les listes, éligible à l'inscription, inclus dans les statistiques courantes

☐ Actif = False

Élève masqué des listes actives, non éligible à l'inscription, conservé en base pour historique\. Motif et date d'inactivité requis\.

☑ Exonéré = True

Frais de scolarité = 0 FCFA automatiquement\. Mention 'Exonéré' sur les reçus et attestations\. Justificatif requis\.

☐ Exonéré = False \(défaut\)

Calcul normal des frais selon la matrice TarifScolarite \(classe × statut\)\.

# 6\. ⭐ INSCRIPTION ET RÉINSCRIPTION — MISE À JOUR v3\.1

📋 App Django : inscriptions — Module Inscription/Réinscription

Distinction fondamentale :

• INSCRIPTION : 1ère fois qu'un élève est affecté à une classe \(après enregistrement\)

• RÉINSCRIPTION : l'élève, déjà enregistré, est affecté à une classe pour une nouvelle année scolaire

Un élève peut être enregistré sans être inscrit\. Une inscription requiert un enregistrement préalable\.

⭐ RÈGLE v3\.1 — MATRICULE COMME RÉFÉRENCE UNIQUE :

Partout où un élève est sollicité après son enregistrement, son MATRICULE est la référence unique\.

L'opérateur saisit ou sélectionne le matricule dans une liste déroulante :

toutes les informations personnelles de l'élève se remplissent automatiquement\.

Aucune ressaisie manuelle des données déjà enregistrées n'est tolérée\.

## 6\.1 Modèle Django — Inscription

inscriptions/models\.py — Inscription

id · eleve \(FK Eleve\) · classe \(FK Classe\) · annee\_scolaire \(FK AnneeScolaire\)

· type\_inscription \(premiere\_inscription / reinscription\)

· date\_inscription · numero\_inscription \(unique, auto\-généré\)

· statut \(en\_attente / validee / annulee\) · validee\_par \(FK User nullable\)

· date\_validation · motif\_annulation \(nullable\)

· rang\_precedent \(IntegerField nullable — rang de l'élève l'année précédente\)

· decision\_passage \(admis / redoublant / exclu — depuis le conseil de classe\)

· created\_at · updated\_at

Contrainte unique : \(eleve, annee\_scolaire\) — un élève ne peut être inscrit qu'une fois par année\.

## 6\.2 Workflow Inscription — par Matricule

⭐ UX Inscription v3\.3 — Fonctionnement liste déroulante matricule

1\. L'opérateur \(Secrétaire\) ouvre l'écran 'Nouvelle Inscription'

2\. Un champ de recherche/liste déroulante affiche les matricules des élèves enregistrés et actifs

   — Recherche rapide par matricule OU par nom/prénom \(les deux modes acceptés\)

3\. Dès la sélection du matricule, tous les champs se remplissent automatiquement :

   Nom, Prénom, Date de naissance, Âge calculé \(lecture seule\), Sexe, Photo, Statut élève, Exonéré…

4\. L'opérateur ne saisit que les informations propres à l'inscription :

   Classe choisie, Année scolaire, éventuellement mise à jour du statut élève

5\. Validation → Inscription créée

### ⭐ Affichage de la Date de Naissance et de l'Âge à l'Inscription — v3\.3

Comportement UX — Champ Âge à l'écran d'inscription :

• Dès que les informations de l'élève s'affichent \(après sélection du matricule\),

  la DATE DE NAISSANCE est affichée en lecture seule \(non modifiable à cet écran\)\.

• Immédiatement à côté ou en dessous, l'ÂGE est calculé automatiquement et affiché

  en lecture seule \(non saisie — fond grisé, visuel distinctif identique à l'enregistrement\)\.

• L'âge affiché à l'inscription est calculé par rapport à la DATE DU JOUR

  de la saisie de l'inscription \(et non par rapport à l'année scolaire\)\.

• Ces deux champs \(date de naissance \+ âge\) sont en CONSULTATION UNIQUEMENT\.

  Toute modification de la date de naissance doit se faire depuis l'écran d'enregistrement\.

Exemple d'affichage dans la fiche inscription :

  Nom           : \[ SAWADOGO Aminata \]    \(lecture seule\)

  Date naissance: \[ 15/03/2014 \]           \(lecture seule\)

  Âge           : \[ 11 ans \]               \(calculé, lecture seule, fond grisé\)

  Sexe          : \[ F \]                    \(lecture seule\)

  Classe        : \[ Sélectionner\.\.\. \]       \(saisie opérateur — seul champ modifiable\)

__Champ affiché à l'inscription__

__Mode / Comportement__

Matricule

Lecture seule — référence unique de l'élève

Nom et Prénom

Lecture seule — rempli automatiquement depuis le dossier

Date de naissance

Lecture seule — remplie automatiquement depuis le dossier

Âge

⭐ Calculé automatiquement — lecture seule, fond grisé — formule : aujourd'hui \- date\_naissance

Sexe

Lecture seule — rempli automatiquement depuis le dossier

Photo

Lecture seule — affichée en miniature depuis le dossier

Statut élève

Modifiable — peut être mis à jour lors de l'inscription \(ex: passage de Non affecté à Affecté\)

Classe

Saisie obligatoire par l'opérateur — seul champ vraiment libre

Année scolaire

Pré\-remplie avec l'année courante — modifiable si nécessaire

__Étape__

__Acteur__

__Action__

1\. Sélection matricule

Secrétaire

Recherche et sélectionne le matricule dans la liste déroulante — les infos personnelles s'affichent automatiquement

2\. Vérification

Système

Vérifie que l'élève est actif et non déjà inscrit pour cette année scolaire

3\. Sélection classe

Secrétaire

Choisit la classe — alerte affichée si capacité maximale atteinte

4\. Calcul frais

Système

Calcule automatiquement les frais selon TarifScolarite \(classe × statut élève\)

5\. Génération

Système

Génère le numéro d'inscription et crée les rubriques de paiement de l'élève

6\. Validation

Directeur/Proviseur

Valide l'inscription — statut passe à 'validee'

7\. Notification

Système

Email/SMS de confirmation à la famille \(si portail parents actif\)

## 6\.3 Workflow Réinscription

La réinscription est initiée en début de chaque année scolaire\. Deux modes possibles :

- Mode individuel : sélection d'un élève, choix de la nouvelle classe, confirmation
- Mode en masse \(Réinscription Automatique\) :
- Sélection d'une classe source \(ex: 5ème A, année 2024\-2025\)
- Sélection de la classe de destination \(ex: 4ème A, année 2025\-2026\)
- Le système propose automatiquement tous les élèves 'Admis' de la classe source
- L'opérateur peut décocher des élèves individuellement
- Confirmation → réinscriptions créées en masse en un clic

Règles métier réinscription :

- Un élève 'Redoublant' peut être réinscrit dans la même classe
- Un élève 'Exclus' ne peut pas être réinscrit — message d'erreur explicite
- Un élève inactif ne peut pas être réinscrit — réactivation préalable requise
- Le statut élève \(Affecté/Non affecté\) peut être mis à jour lors de la réinscription

## 6\.4 Transferts Inter\-Établissements

inscriptions/models\.py — TransfertEleve

id · eleve \(FK Eleve\) · etablissement\_origine \(FK\) · etablissement\_destination \(FK\)

· classe\_origine \(FK Classe\) · classe\_destination \(FK Classe nullable\)

· annee\_scolaire \(FK\) · date\_demande · date\_transfert

· motif · statut \(en\_attente/approuve/rejete\) · approuve\_par \(FK User\)

· certificat\_scolarite\_joint \(BooleanField\) · attestation\_non\_redev\_jointe \(BooleanField\)

· created\_at

# 7\. ⭐ AGENT DE VIE SCOLAIRE \(AVS\) — NOUVEAU v3\.0

📋 App Django : presences — Module Agent de Vie Scolaire

L'Agent de Vie Scolaire \(AVS\) est le responsable de la discipline et du suivi des absences\.

Il gère les absences des ÉLÈVES et des PROFESSEURS, les sanctions disciplinaires

et produit les rapports hebdomadaires/mensuels transmis au directeur\.

Rôle distinct du Censeur : l'AVS opère sur le terrain \(saisie\), le Censeur supervise et valide\.

## 7\.1 Gestion des Absences des Élèves

### Modèle Django — AbsenceEleve

presences/models\.py — AbsenceEleve

id · eleve \(FK Eleve\) · classe \(FK Classe\) · date\_absence · heure\_debut · heure\_fin

· nb\_heures \(DecimalField\) · matiere \(FK Discipline nullable\)

· type\_absence \(injustifiee / justifiee\_avs / justifiee\_autorisation\)

· motif\_declare \(texte libre\) · piece\_justificative \(FileField nullable\)

· statut\_justification \(non\_justifiee / en\_attente / justifiee / rejetee\)

· saisie\_par \(FK User — AVS\) · validee\_par \(FK User nullable — Censeur/Directeur\)

· annee\_scolaire \(FK\) · created\_at · updated\_at

Fonctionnalités absences élèves :

- Saisie rapide par l'AVS : sélection classe → liste élèves → cocher absents
- Saisie par plage horaire \(heure de début et fin\) pour comptage en heures
- Intégration avec AutorisationAbsence : absences de la période marquées automatiquement
- Alerte automatique parents dès 2 absences injustifiées consécutives \(email/SMS\)
- Quota annuel configurable : alerte si dépassement du nombre d'heures autorisées
- Rapport hebdomadaire automatique des absences par classe à destination du Censeur

## 7\.2 Gestion des Absences des Professeurs

### Modèle Django — AbsenceProfesseur

presences/models\.py — AbsenceProfesseur

id · professeur \(FK User — rôle Enseignant\) · date\_absence · heure\_debut · heure\_fin

· nb\_heures \(DecimalField\) · matiere\_concernee \(FK Discipline nullable\)

· classes\_concernees \(ManyToMany Classe — quelles classes n'ont pas eu cours\)

· type\_absence \(injustifiee / maladie / formation / mission / conge\)

· piece\_justificative \(FileField nullable\) · cours\_rattrape \(BooleanField\)

· date\_rattrapage \(DateField nullable\) · saisie\_par \(FK User — AVS\)

· validee\_par \(FK User nullable — Directeur\) · annee\_scolaire \(FK\)

· created\_at · updated\_at

Fonctionnalités absences professeurs :

- Saisie par l'AVS dès constat d'absence du professeur en classe
- Notification automatique aux élèves concernés \(si portail actif\)
- Suivi du rattrapage des cours manqués
- Rapport mensuel des absences professeurs transmis à la Direction
- Statistiques : taux d'assiduité par professeur et par matière

## 7\.3 Registre Disciplinaire

### Modèle Django — SanctionDisciplinaire

presences/models\.py — SanctionDisciplinaire

id · eleve \(FK Eleve\) · type\_sanction \(avertissement / blame / exclusion\_temp / exclusion\_def\)

· motif\_detaille · date\_sanction · nb\_jours\_exclusion \(IntegerField nullable\)

· date\_retour \(DateField nullable\) · saisie\_par \(FK User — AVS ou Censeur\)

· validee\_par \(FK User — Censeur ou Directeur\) · statut \(en\_cours / levee / archivee\)

· appreciation\_conduite \(FK AppreciationConduite\) · annee\_scolaire \(FK\)

· created\_at

Règles métier discipline :

- Avertissement : saisi par AVS, validé automatiquement
- Blâme : saisi par AVS, validé par Censeur
- Exclusion temporaire : saisi par Censeur, validé par Directeur
- Exclusion définitive : validée uniquement par Directeur — blocage réinscription automatique
- Un élève sous sanction active ne peut pas obtenir d'autorisation d'absence

## 7\.4 Tableau de Bord AVS

Interface dédiée à l'Agent de Vie Scolaire :

- Vue du jour : liste des absents élèves et professeurs enregistrés aujourd'hui
- File des justificatifs en attente de traitement
- Alertes : élèves dépassant le quota d'absences
- Bouton rapide 'Saisir absences du jour' par classe
- Rapport hebdomadaire générable en un clic \(PDF WeasyPrint\)

# 8\. ⭐ MODULE DOCUMENTS ADMINISTRATIFS — ENRICHI v3\.0

📄 App Django : documents — Version enrichie v3\.0

Nouveauté v3\.0 : ajout de la Carte d'Identité Scolaire en plus des 4 documents existants\.

Tous les documents sont générés en PDF/A via WeasyPrint, archivés sur MinIO,

vérifiables par QR Code et traçables dans un registre immuable\.

## 8\.1 Certificat de Scolarité

*Document officiel attestant l'inscription régulière de l'élève\. Demandé pour bourses, allocations familiales, réductions transport\.*

- Numérotation : CERT\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}
- QR Code d'authenticité intégré → lien vérification en ligne
- Délai configurable avec notification email/SMS à disponibilité
- Demande en ligne via portail parents avec validation secrétariat

## 8\.2 Attestation de Non\-Redevabilité

*Certifie que l'élève est à jour de tous ses paiements\. Indispensable pour les transferts et remises de diplômes\.*

- Vérification automatique du solde dans le module finances avant génération
- Si solde > 0 FCFA : génération bloquée avec affichage du détail des impayés
- Double validation : secrétariat \+ comptable
- Validité : 30 jours après émission \(mention dans le document\)

## 8\.3 Cursus Scolaire

*Relevé cumulatif de tout le parcours scolaire dans l'établissement : classes, moyennes, mentions, examens, redoublements\.*

- Disponible uniquement si l'élève a au moins 1 année complète dans l'établissement
- Données consolidées automatiquement depuis les modules pedagogie et bulletins
- Format bilingue optionnel : Français \+ résumé en anglais \(V2\)

## 8\.4 Autorisation d'Absence

*Permission officielle d'absence pour une durée et un motif précis\. Initié par parents ou par l'établissement\.*

- Workflow 6 étapes : demande → instruction AVS/Censeur → validation Directeur → PDF → notification enseignants → retour
- Blocage si l'élève a une sanction disciplinaire active
- Intégration avec module presences : absences marquées automatiquement comme 'autorisées'

## 8\.5 ⭐ Carte d'Identité Scolaire — NOUVEAU v3\.0

📋 Définition

Document officiel plastifié \(ou papier\) remis à chaque élève à chaque rentrée scolaire\.

Permet l'identification de l'élève au sein de l'établissement et lors des examens officiels\.

L'impression est organisée par classe pour faciliter la distribution\.

### Modèle Django — CarteIdentiteScolaire

documents/models\.py — CarteIdentiteScolaire

id · eleve \(FK Eleve\) · inscription \(FK Inscription — lien à l'année scolaire en cours\)

· annee\_scolaire \(FK AnneeScolaire\) · classe \(FK Classe\)

· numero\_carte \(unique, auto\-généré : CARTE\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}\)

· date\_emission · validite\_fin \(= date\_fin de l'annee\_scolaire courante\)

· statut \(brouillon / imprimee / invalidee\)

· delivree\_par \(FK User\) · fichier\_pdf \(FileField MinIO\)

· hash\_document \(SHA256\) · lot\_impression \(IntegerField — numéro de lot par classe\)

· created\_at

### Contenu de la Carte d'Identité Scolaire

__Zone Recto__

__Zone Verso__

Logo de l'établissement

Code QR d'authenticité \(lien vérification\)

Nom de l'établissement \+ n° agrément MENA

Règlement intérieur résumé \(3\-4 règles clés\)

Année scolaire \(ex : 2025\-2026\)

Numéro d'urgence de l'établissement

Photo d'identité de l'élève \(depuis dossier\)

Mention : Valable uniquement pour l'année scolaire indiquée

Nom et Prénom de l'élève

Signature du Directeur \+ Cachet

Date et lieu de naissance

Numéro matricule de l'élève

Classe

Numéro de carte unique

### Génération par Classe — Workflow d'Impression

__Étape__

__Acteur__

__Action__

1\. Sélection

Secrétaire

Sélectionne la classe et l'année scolaire

2\. Vérification

Système

Vérifie que tous les élèves de la classe ont une photo dans leur dossier

3\. Alerte

Système

Liste les élèves sans photo \(bloquants\) pour que la secrétaire puisse les compléter

4\. Génération

Système

Génère un PDF multi\-pages \(2 cartes par élève : recto \+ verso\) format carte de visite \(85×54mm\)

5\. Aperçu

Secrétaire

Prévisualise le PDF dans le navigateur avant lancement impression

6\. Impression

Secrétaire

Impression directe depuis l'interface — format A4 avec 8 cartes par page \(4×2\)

7\. Archivage

Système

Enregistre le lot d'impression avec numéro de lot, classe, date

8\. Remise

AVS/Secrétaire

Remet les cartes aux élèves — marque statut 'imprimee'

### Règles métier — Carte d'Identité Scolaire

- Une carte est générée par élève par année scolaire \(unicité inscription × annee\_scolaire\)
- Photo obligatoire dans le dossier de l'élève avant génération
- Impression organisée par classe \(lot\_impression\) pour faciliter la distribution en salle
- En cas de perte : génération d'un duplicata avec mention 'DUPLICATA' \+ nouveau numéro
- La carte invalide automatiquement à la fin de l'année scolaire
- QR Code → page de vérification publique /verifier\-document/\{hash\}/ sans connexion

### Format PDF — Disposition 8 cartes par page A4

Template : documents/templates/documents/carte\_identite\_scolaire\.html

Disposition : grille 4 colonnes × 2 lignes = 8 cartes par page A4 paysage

Format carte individuelle : 85 mm × 54 mm \(standard carte bancaire/identité\)

Séparateurs de découpe : traits pointillés pour faciliter la coupe

Impression recto\-verso : page 1 = tous les rectos | page 2 = tous les versos

\(alignés pour que le recto et le verso correspondent après découpe\)

Police : DejaVu Sans \(compatible WeasyPrint, supporte les caractères spéciaux\)

Photo élève : miniature 25mm × 30mm, encadrée, centrée à gauche du recto

QR Code : 20mm × 20mm, coin inférieur droit du verso

## 8\.6 DocumentAuditLog — Registre immuable

documents/models\.py — DocumentAuditLog

type\_document \(certificat/attestation/cursus/autorisation/carte\_id\)

· numero\_document · eleve \(FK\) · action \(demande/generation/impression/emission/annulation/telechargement\)

· acteur \(FK User\) · date\_action · ip\_address · hash\_avant · hash\_apres · details\_json

→ Append\-only : aucune modification possible même par un admin

→ Exportable en PDF pour audit externe

→ Consultable par le Directeur et le Super Admin Éditeur

## 8\.7 Stack technique — Module Documents

__Composant__

__Technologie / Rôle__

Génération PDF

WeasyPrint 60\+ — Conversion HTML→PDF/A haute qualité

QR Codes

qrcode \(open\-source\) — Intégration dans les PDFs

Stockage PDF

MinIO \(auto\-hébergé\) — Archivage sécurisé

Génération async

Celery \+ Redis — Génération en arrière\-plan

Notifications

Postfix \+ django\-mail — Emails disponibilité document

Authenticité

hashlib SHA256 — Hash intégré dans le QR Code du PDF

Cartes ID format

CSS @page size: 85mm 54mm — Format carte standard

Interface admin

Django Admin custom — Registre documents, statistiques

# 9\. FONCTIONNALITÉS MÉTIER EXISTANTES — v2\.0 Confirmées

## 9\.1 Gestion pédagogique \[MVP\]

- Emplois du temps dynamiques par classe, enseignant et salle
- Saisie des notes : devoirs \(coeff\. 1\), compositions \(coeff\. 2\), examens \(coeff\. 3\)
- Calcul automatique des moyennes selon coefficients officiels MENA Burkina Faso
- Génération bulletins de notes aux formats officiels MENA : trimestriel et annuel
- Palmarès de classe avec rang, mention et appréciation du directeur

## 9\.2 Examens officiels \[MVP\]

- CEP \(CM2\) : listes candidats, PV, statistiques, taux de réussite
- BEPC \(3ème\) : numéros candidats, tableaux résultats, archives
- BAC séries A/B/C/D \(Terminale\) : listes par série, PV officiels

## 9\.3 Finances et comptabilité \[MVP\]

- Frais scolaires basés sur la matrice TarifScolarite \(classe × statut élève\) — v3\.0
- Suivi paiements : payé, partiel, impayé, exonéré, boursier
- Génération reçus PDF numérotés et sécurisés via WeasyPrint
- Tableau de bord financier : recettes, dépenses, solde, taux de recouvrement
- Gestion des bourses et exonérations avec justificatifs numérisés

# 9bis\. ⭐ GESTION DES VACATIONS — NOUVEAU v3\.1

📋 App Django : vacations \(nouvelle app\) — Gestion des professeurs vacataires

Définition : Un professeur vacataire est un enseignant non\-permanent qui s'inscrit

chaque année scolaire pour assurer des cours dans l'établissement\.

Il peut enseigner plusieurs disciplines dans la même classe ou dans plusieurs classes\.

Sa rémunération est calculée sur la base du nombre d'heures réellement effectuées\.

Acteurs : Professeur \(saisie et inscription\) · Comptabilité \(bilan mensuel\) · Directeur/Proviseur \(validation\)

## 9bis\.1 Modèles Django — App Vacations

### Modèle — ProfesseurVacataire

vacations/models\.py — ProfesseurVacataire

id · user \(FK User — compte du professeur dans le système\)

· nom · prenom · telephone · email

· numero\_identite \(CNI ou passeport\) · specialite\_principale

· diplome\_le\_plus\_eleve · etablissement\_formation

· tarif\_horaire \(DecimalField FCFA/heure — peut varier par discipline\)

· statut \(actif / inactif / suspendu\) · etablissement \(FK Etablissement\)

· created\_at · updated\_at

### Modèle — InscriptionVacation \(par année scolaire\)

vacations/models\.py — InscriptionVacation

id · professeur \(FK ProfesseurVacataire\) · annee\_scolaire \(FK AnneeScolaire\)

· date\_inscription · statut \(en\_attente / validee / annulee\)

· validee\_par \(FK User — Directeur/Proviseur\) · date\_validation

· observations \(TextField nullable\)

· created\_at

Contrainte unique : \(professeur, annee\_scolaire\) — un vacataire s'inscrit une fois par an\.

Un vacataire doit avoir une InscriptionVacation validée avant toute affectation de cours\.

### Modèle — AffectationVacation \(discipline × classe × volume horaire prévu\)

vacations/models\.py — AffectationVacation

id · inscription\_vacation \(FK InscriptionVacation\)

· discipline \(FK Discipline\) · classe \(FK Classe\) · annee\_scolaire \(FK AnneeScolaire\)

· nb\_heures\_prevues\_semaine \(DecimalField — volume hebdomadaire contractualisé\)

· nb\_semaines \(IntegerField — nombre de semaines de la période\)

· nb\_heures\_prevues\_total \(Property calculée : semaine × nb\_semaines\)

· tarif\_horaire\_applicable \(DecimalField — copié à la création, permet historique\)

· statut \(active / suspendue / terminee\)

· created\_at

Règle : Un vacataire peut avoir plusieurs AffectationVacation par année scolaire :

  • Mathématiques en 4ème A \+ Mathématiques en 3ème B \+ Physique en Terminale C = 3 affectations

### Modèle — HeuresRealisees \(saisie mensuelle des heures effectuées\)

vacations/models\.py — HeuresRealisees

id · affectation \(FK AffectationVacation\) · mois \(DateField — 1er du mois concerné\)

· nb\_heures\_realisees \(DecimalField — heures effectivement assurées ce mois\)

· nb\_heures\_prevues\_mois \(DecimalField — calculé depuis AffectationVacation\)

· ecart \(Property : realisees \- prevues — positif=heures sup, négatif=heures manquantes\)

· saisie\_par \(FK User — AVS ou Secrétariat\) · validee\_par \(FK User nullable — Comptabilité\)

· statut \(brouillon / soumise / validee / rejetee\) · motif\_ecart \(TextField nullable\)

· created\_at · updated\_at

Contrainte unique : \(affectation, mois\) — une saisie par affectation et par mois\.

## 9bis\.2 Bilan Mensuel des Vacations

📊 Le bilan mensuel est le document central de la gestion des vacations\.

Il est produit par la Comptabilité à la fin de chaque mois et validé par le Directeur/Proviseur\.

Il sert de base au calcul de la rémunération des vacataires\.

### Modèle — BilanMensuelVacation

vacations/models\.py — BilanMensuelVacation

id · mois \(DateField — 1er du mois\) · annee\_scolaire \(FK AnneeScolaire\)

· etablissement \(FK Etablissement\)

· statut \(en\_preparation / soumis / valide / rejete\)

· genere\_par \(FK User — Comptabilité\) · valide\_par \(FK User nullable — Directeur/Proviseur\)

· date\_generation · date\_validation · observations\_directeur \(TextField nullable\)

· fichier\_pdf \(FileField MinIO — bilan PDF généré\) · created\_at

Relations : un bilan mensuel agrège toutes les HeuresRealisees du mois concerné\.

### Structure du Bilan Mensuel — Contenu du PDF

Le bilan mensuel produit par la comptabilité et validé par le Directeur/Proviseur contient :

__Section__

__Contenu__

__Source données__

En\-tête

Logo, nom établissement, mois/année, n° bilan

IdentiteEtablissement

Tableau par professeur

Nom · Discipline · Classe · H\. prévues · H\. réalisées · Écart · Montant dû

AffectationVacation \+ HeuresRealisees

Synthèse par classe

Total heures prévues vs réalisées par classe

Agrégation SQL

Synthèse par discipline

Total heures prévues vs réalisées par matière

Agrégation SQL

Récapitulatif financier

Montant total à payer aux vacataires ce mois

Somme tarif × heures réalisées

Signature

Établi par \(Comptabilité\) \+ Validé par \(Directeur/Proviseur\)

Champ signature

## 9bis\.3 Workflow complet — Vacations

__Étape__

__Acteur__

__Description__

1\. Inscription annuelle

Professeur / Secrétariat

Le professeur vacataire s'inscrit pour l'année scolaire en cours — InscriptionVacation créée

2\. Validation inscription

Directeur/Proviseur

Valide ou rejette l'inscription du vacataire pour cette année

3\. Affectation cours

Directeur/Secrétariat

Affecte le vacataire à une ou plusieurs disciplines/classes avec volume horaire hebdomadaire prévu

4\. Saisie mensuelle

AVS / Secrétariat

À la fin de chaque mois, saisit les heures réellement effectuées par affectation — HeuresRealisees

5\. Génération bilan

Comptabilité

Génère le BilanMensuelVacation : tableau heures prévues vs réalisées \+ écarts \+ montants dus

6\. Validation bilan

Directeur/Proviseur

Valide le bilan mensuel — déclenche la mise en paiement

7\. Paiement

Comptabilité

Effectue les virements/paiements selon le bilan validé — lié au module Finances

8\. Archivage

Système

Le bilan PDF est archivé sur MinIO et accessible dans l'historique

## 9bis\.4 Règles Métier — Vacations

- Un vacataire peut enseigner plusieurs disciplines dans la même classe ou dans des classes différentes
- L'écart mensuel = heures réalisées − heures prévues \(peut être positif ou négatif\)
- Écart positif \(heures supplémentaires\) : rémunéré selon le tarif horaire applicable
- Écart négatif \(heures manquantes\) : notifié dans le bilan, motif requis \(maladie, absence…\)
- Le bilan est produit par la Comptabilité et doit être validé par le Directeur/Proviseur avant paiement
- Aucun paiement vacataire n'est possible sans bilan validé par le Directeur/Proviseur
- Les HeuresRealisees sont liées à l'AbsenceProfesseur \(module AVS\) : cohérence garantie
- Un vacataire dont l'InscriptionVacation n'est pas validée ne peut pas avoir d'affectation

## 9bis\.5 Interface — Tableau de Bord Vacations

__Vue__

__Contenu__

Vue Comptabilité

Liste des vacataires actifs · Statut saisie du mois · Bouton 'Générer bilan mensuel' · Historique des bilans

Vue Directeur/Proviseur

Bilans en attente de validation · Comparatif heures prévues/réalisées par classe · Alerte si écart > seuil configurable

Vue Professeur vacataire

Mes affectations · Mon volume horaire prévu vs réalisé · Mes bilans historiques · Mon solde à payer

Vue Secrétariat/AVS

Saisie mensuelle des heures effectuées par vacataire et par affectation

## 9bis\.6 Intégrations avec les autres modules

__Module lié__

__Intégration__

presences \(AVS\)

AbsenceProfesseur → déduite automatiquement des HeuresRealisees si absence enregistrée par l'AVS

pedagogie

Emploi du temps → source des heures prévues par semaine \(cohérence planifié vs réalisé\)

finances

BilanMensuelVacation validé → déclenche les ordres de paiement vacataires

parametres

Discipline, Classe, AnneeScolaire, PeriodeEvaluation → utilisés pour les affectations

documents

Bilan mensuel généré en PDF/A WeasyPrint · archivé MinIO · QR Code authenticité

# 9ter\. ⭐ GESTION DU PERSONNEL — NOUVEAU v3\.2

📋 App Django : personnel \(nouvelle app\) — Gestion de tout le personnel de l'établissement

Principe fondamental identique à celui des élèves :

• Chaque membre du personnel est ENREGISTRÉ UNE SEULE FOIS dans le système\.

• À l'enregistrement, un MATRICULE UNIQUE est automatiquement généré\.

  Ce matricule est différent de celui des élèves \(préfixe distinct\) et reste

  l'unique référence pour identifier ce membre du personnel dans tout le système\.

• Chaque année scolaire, le membre du personnel effectue une INSCRIPTION \(première fois\)

  ou une RÉINSCRIPTION pour être pris en compte dans le fonctionnement de l'année\.

  Sans inscription/réinscription validée pour l'année en cours, le personnel n'est

  pas actif dans les modules de l'application \(emplois du temps, présences, etc\.\)\.

Acteurs : Secrétariat \(enregistrement \+ inscription\) · Directeur/Proviseur \(validation\)

## 9ter\.1 Modèle Django — MembrePersonnel

personnel/models\.py — MembrePersonnel

── Identification ──

id · matricule\_personnel \(unique, auto\-généré : PERS\-\{ETAB\}\-\{ANNEE\}\-\{SEQ:04d\}\)

  Préfixe PERS\- distingue explicitement des matricules élèves \(BF\-\.\.\.\)

· nom · prenom · date\_naissance · lieu\_naissance · sexe \(M/F\)

· nationalite \(default: Burkinabè\) · numero\_cni \(carte nationale d'identité\)

── Poste et qualification ──

· poste \(FK Poste — depuis module Paramètres : Directeur, Censeur, AVS, Enseignant…\)

· localisation \(FK LocalisationPoste — bureau ou salle de classe\)

· type\_personnel \(enseignant / administratif / technique / direction\)

· specialite \(pour les enseignants — lien Discipline optionnel\)

· diplome\_le\_plus\_eleve · etablissement\_formation · annee\_obtention\_diplome

── Contact ──

· telephone · email · adresse · quartier · ville

── État ──

· actif \(BooleanField — case à cocher : actif / inactif dans l'établissement\)

· motif\_inactivite \(CharField nullable : départ / mutation / retraite / décès…\)

· date\_inactivite \(DateField nullable\)

── Documents ──

· photo \(ImageField MinIO — photo d'identité\)

· copie\_diplome \(FileField MinIO\) · copie\_cni \(FileField MinIO\)

· arrete\_nomination \(FileField MinIO — pour le personnel nommé par l'État\)

── Métadonnées ──

· etablissement \(FK Etablissement\) · enregistre\_par \(FK User\)

· created\_at · updated\_at

## 9ter\.2 Modèle Django — InscriptionPersonnel \(par année scolaire\)

personnel/models\.py — InscriptionPersonnel

id · membre \(FK MembrePersonnel\) · annee\_scolaire \(FK AnneeScolaire\)

· type\_inscription \(premiere\_inscription / reinscription\)

· poste\_occupe \(FK Poste — peut changer d'une année à l'autre\)

· localisation\_affectee \(FK LocalisationPoste nullable\)

· date\_inscription · numero\_inscription \(unique, auto\-généré\)

· statut \(en\_attente / validee / annulee\) · validee\_par \(FK User — Directeur/Proviseur\)

· date\_validation · observations \(TextField nullable\)

· created\_at · updated\_at

Contrainte unique : \(membre, annee\_scolaire\) — un membre ne peut être inscrit qu'une fois par an\.

Un membre du personnel sans InscriptionPersonnel validée pour l'année courante

n'apparaît pas dans les listes actives \(emploi du temps, présences, vacations, etc\.\)\.

## 9ter\.3 Matricule Personnel — Format et Unicité

__Caractéristique__

__Détail__

Format

PERS\-\{CODE\_ETAB\}\-\{ANNEE\_ENREGISTREMENT\}\-\{SEQUENCE:04d\}

Exemple

PERS\-YSK\-2026\-0001, PERS\-YSK\-2026\-0002, PERS\-YSK\-2026\-0045…

Préfixe

PERS\- \(toujours présent — distinction immédiate avec BF\- des élèves\)

Génération

Automatique à la première sauvegarde de l'enregistrement — non modifiable

Unicité

Unique dans tout l'établissement, tous membres confondus

Utilisation

Référence unique dans tous les modules : emplois du temps, présences, vacations, RH, paie

Recherche

Tous les écrans où un membre du personnel est sélectionné utilisent le matricule comme référence principale \(liste déroulante avec auto\-remplissage, identique à la logique élève\)

## 9ter\.4 Workflow Enregistrement et Inscription du Personnel

__Étape__

__Acteur__

__Action__

1\. Enregistrement

Secrétariat

Saisit toutes les informations personnelles et professionnelles — matricule généré automatiquement

2\. Upload documents

Secrétariat

Ajoute photo, copie CNI, diplôme, arrêté de nomination si applicable

3\. Inscription annuelle

Secrétariat

Sélectionne le membre par matricule \(liste déroulante\) → choisit le poste occupé et la localisation pour l'année en cours

4\. Vérification

Système

Vérifie que le membre est actif et non déjà inscrit pour cette année scolaire

5\. Validation

Directeur/Proviseur

Valide l'inscription — le membre devient actif dans l'application pour l'année en cours

6\. Activation modules

Système

Le membre apparaît désormais dans les emplois du temps, présences, vacations \(si vacataire\), etc\.

## 9ter\.5 Liste du Personnel — Format et Statistiques

📋 La liste officielle du personnel est générée pour une année scolaire donnée\.

Elle est organisée alphabétiquement et se termine par les totaux femmes/hommes\.

Elle peut être filtrée par : année scolaire · poste · type de personnel · genre\.

### Contenu de la Liste du Personnel

__Colonne__

__Contenu__

__Source__

N°

Numéro d'ordre dans la liste \(1, 2, 3…\)

Auto

Matricule

PERS\-\{ETAB\}\-\{ANNEE\}\-\{SEQ\}

MembrePersonnel

Nom et Prénom

NOM Prénom \(trié alphabétiquement par nom\)

MembrePersonnel

Sexe

M ou F

MembrePersonnel

Date de naissance

JJ/MM/AAAA

MembrePersonnel

Poste occupé

Intitulé du poste pour l'année en cours

InscriptionPersonnel

Localisation

Bureau ou salle affectée

InscriptionPersonnel

Type

Enseignant / Administratif / Direction / Technique

MembrePersonnel

Diplôme

Diplôme le plus élevé

MembrePersonnel

### Pied de la Liste du Personnel — Totaux obligatoires

À la fin de chaque liste du personnel, les éléments suivants sont OBLIGATOIREMENT affichés :

┌─────────────────────────────────────────────────────┐

│  RÉCAPITULATIF                                       │

│  Total membres du personnel inscrits : XX           │

│  Nombre de femmes \(F\)               : XX            │

│  Nombre d'hommes \(M\)                : XX            │

│                                                      │

│  Répartition par type :                             │

│    • Enseignants         : XX \(dont F: XX | H: XX\)  │

│    • Administratifs      : XX \(dont F: XX | H: XX\)  │

│    • Direction           : XX \(dont F: XX | H: XX\)  │

│    • Techniques          : XX \(dont F: XX | H: XX\)  │

└─────────────────────────────────────────────────────┘

Signataires : Établi par \(Secrétariat\) \+ Approuvé par \(Directeur/Proviseur\)

## 9ter\.6 Règles métier — Personnel

- Un membre du personnel est enregistré une seule fois, quelle que soit sa durée de service
- Le matricule PERS\- est généré à l'enregistrement et ne peut jamais être modifié ni réutilisé
- Chaque année scolaire, une nouvelle InscriptionPersonnel est créée — même si le poste ne change pas
- Un membre inactif \(actif = False\) ne peut pas être inscrit — réactivation préalable requise
- Un enseignant doit avoir une InscriptionPersonnel validée pour apparaître dans les emplois du temps
- Un vacataire \(voir Section 9bis\) est un sous\-type de personnel — il a un MembrePersonnel et une InscriptionVacation en plus
- La liste du personnel doit toujours afficher le total femmes / hommes en fin de document

# 9quater\. ⭐ STATISTIQUES LISTES ALPHABÉTIQUES PAR CLASSE — NOUVEAU v3\.2

📋 App Django : inscriptions / pedagogie — Enrichissement des listes élèves par classe

Chaque liste alphabétique des élèves par classe doit se terminer par trois blocs statistiques :

  BLOC 1 — Totaux filles / garçons

  BLOC 2 — Tableau statistique des âges par genre

  BLOC 3 — Répartition redoublants / non\-redoublants par genre

Ces statistiques sont générées automatiquement à partir des données de la base\.

Elles figurent sur toutes les versions imprimées de la liste de classe\.

Elles peuvent aussi être consultées directement dans l'interface web\.

## 9quater\.1 BLOC 1 — Totaux Filles / Garçons

À la fin de chaque liste alphabétique d'une classe, afficher OBLIGATOIREMENT :

  Total élèves inscrits dans la classe  :  XX

  Nombre de filles \(F\)                  :  XX

  Nombre de garçons \(G\)                 :  XX

Source : Eleve\.sexe \('F' ou 'M'\) filtré par Inscription\.classe et Inscription\.annee\_scolaire

## 9quater\.2 BLOC 2 — Tableau Statistique des Âges par Genre

Ce tableau répartit les élèves de la classe selon leur âge \(calculé au 31 décembre de l'année scolaire en cours\) et leur genre\. Chaque âge constitue une ligne du tableau\.

Format du tableau statistique des âges :

┌────────────────────────────────────────────────────────────┐

│   Âge      │  Filles \(F\)  │  Garçons \(G\)  │  Total        │

├────────────────────────────────────────────────────────────┤

│   10 ans   │      2       │       3        │     5         │

│   11 ans   │      5       │       4        │     9         │

│   12 ans   │      8       │       7        │    15         │

│   13 ans   │      3       │       5        │     8         │

│   14 ans   │      1       │       2        │     3         │

│   \.\.\.      │     \.\.\.      │      \.\.\.       │    \.\.\.        │

├────────────────────────────────────────────────────────────┤

│   TOTAL    │     19       │      21        │    40         │

└────────────────────────────────────────────────────────────┘

Calcul de l'âge : date\_reference = 31 décembre de l'année de fin de l'AnneeScolaire

age = date\_reference\.year \- eleve\.date\_naissance\.year

     \(ajusté si l'anniversaire n'est pas encore passé au 31/12\)

Les âges sont triés par ordre croissant\.

Les âges sans élèves ne sont pas affichés \(ligne masquée si effectif = 0\)\.

### Modèle de requête Django — StatistiqueAgeClasse

Pas de modèle dédié — calcul dynamique à la génération de la liste\.

\# Calcul des âges au 31 décembre de l'année scolaire

from django\.db\.models import Count, Case, When, IntegerField

from datetime import date

date\_ref = date\(annee\_fin, 12, 31\)

\# Annotation de l'âge sur chaque élève de la classe

inscriptions = Inscription\.objects\.filter\(

    classe=classe, annee\_scolaire=annee\_scolaire

\)\.select\_related\('eleve'\)\.annotate\(

    age=ExpressionWrapper\(

        date\_ref\.year \- ExtractYear\('eleve\_\_date\_naissance'\),

        output\_field=IntegerField\(\)

    \)

\)

\# Regroupement par \(age, sexe\) pour construire le tableau

stats = inscriptions\.values\('age', 'eleve\_\_sexe'\)\.annotate\(nb=Count\('id'\)\)

## 9quater\.3 BLOC 3 — Répartition Redoublants / Non\-Redoublants par Genre

Ce tableau affiche, pour la classe et l'année scolaire concernées, le nombre de redoublants et de non\-redoublants ventilé par genre\.

Format du tableau redoublants / non\-redoublants :

┌──────────────────────────────────────────────────────────────┐

│   Catégorie         │  Filles \(F\)  │  Garçons \(G\)  │  Total  │

├──────────────────────────────────────────────────────────────┤

│   Redoublants       │      4       │       6        │   10    │

│   Non\-redoublants   │     15       │      15        │   30    │

├──────────────────────────────────────────────────────────────┤

│   TOTAL             │     19       │      21        │   40    │

└──────────────────────────────────────────────────────────────┘

Source : Inscription\.decision\_passage = 'redoublant' → redoublant

         Inscription\.decision\_passage = 'admis'      → non\-redoublant

         Croisé avec Eleve\.sexe pour la ventilation par genre\.

Note : Un élève est 'redoublant' s'il est réinscrit dans la même classe qu'il

occupait l'année précédente suite à une décision de redoublement du conseil de classe\.

Cette information vient du champ decision\_passage de l'Inscription précédente\.

## 9quater\.4 Modèle Django — StatistiqueListeClasse \(optionnel, mis en cache\)

inscriptions/models\.py — StatistiqueListeClasse \(table de cache optionnelle\)

Pour les établissements avec beaucoup d'élèves, les statistiques peuvent être

pré\-calculées et mises en cache plutôt que recalculées à chaque impression\.

id · classe \(FK Classe\) · annee\_scolaire \(FK AnneeScolaire\)

· nb\_total · nb\_filles · nb\_garcons

· stats\_ages\_json \(JSONField — sérialisation du tableau âges\)

· nb\_redoublants\_filles · nb\_redoublants\_garcons · nb\_redoublants\_total

· nb\_non\_redoublants\_filles · nb\_non\_redoublants\_garcons · nb\_non\_redoublants\_total

· derniere\_mise\_a\_jour · created\_at

Signal : recalcul automatique à chaque inscription/désinscription dans la classe\.

Contrainte unique : \(classe, annee\_scolaire\)

## 9quater\.5 Format complet de la Liste Alphabétique par Classe

Structure complète d'une liste de classe imprimée \(PDF WeasyPrint\) :

__Zone__

__Contenu__

__Source__

En\-tête

Logo étab\. \+ Nom étab\. \+ Année scolaire \+ Classe \+ N° agrément MENA

IdentiteEtablissement \+ Classe

Corps — tableau

N° · Matricule élève · Nom · Prénom · Sexe · Date naissance · Statut élève

Inscription \+ Eleve

BLOC 1

Total inscrits · Nombre de filles · Nombre de garçons

Calcul dynamique

BLOC 2

Tableau statistique des âges \(Âge | F | G | Total\)

Calcul dynamique

BLOC 3

Tableau redoublants/non\-redoublants \(Catégorie | F | G | Total\)

Calcul dynamique

Pied de page

Date d'édition · Établi par · Signature Directeur/Proviseur · Cachet

IdentiteEtablissement

## 9quater\.6 Règles métier — Statistiques listes

- Les 3 blocs statistiques sont obligatoires sur toute liste alphabétique de classe imprimée
- L'âge est calculé par rapport au 31 décembre de l'année civile de fin de l'année scolaire
- Un élève dont la date de naissance est inconnue est comptabilisé dans une ligne 'Âge non renseigné'
- Les blocs sont aussi accessibles en consultation directe depuis l'interface web \(sans impression\)
- La ventilation par genre utilise toujours les valeurs M \(garçon\) et F \(fille\) du champ Eleve\.sexe
- Le tableau des âges n'affiche que les lignes avec au moins un élève — les âges à zéro sont masqués
- Le total du BLOC 3 doit toujours être cohérent avec le total du BLOC 1

# 10\. ROADMAP MISE À JOUR — 16 SEMAINES v3\.3

🗓️  Calendrier global : Avril 2026 → 1er Août 2026

Les modules Paramètres, Enregistrement, AVS et Carte ID sont intégrés dans la Phase 2 MVP Core\.

Leur priorité est justifiée : sans Paramètres configurés, aucun autre module ne fonctionne\.

__Phase / Période__

__Contenu__

__Livrables__

Phase 0 — Sem\. 1\-2 Avril

Architecture & Environnement

Repo GitHub, Docker dev, modèles BDD, CI/CD

Phase 1 — Sem\. 3\-4 Avril\-Mai

Module Licences COMPLET

Clés HMAC, activation online/offline, portail éditeur, Feature Flags

Phase 2 — Sem\. 5\-8 Mai\-Juin

⭐ Paramètres \+ Enregistrement élèves \(matricule\) \+ Inscription/Réinscription \+ Personnel \(matricule PERS\-\) \+ AVS \+ Vacations \+ Statistiques listes classes \+ Modules métier essentiels

Paramètres, Enregistrement élèves, Enregistrement personnel, Inscriptions par matricule, AVS, Vacations, Notes, Bulletins MENA, Présences, Statistiques listes

Phase 3 — Sem\. 9\-10 Juin

Module Documents COMPLET

Certificats, Attestations, Cursus, Autorisations, Carte ID scolaire \+ PDF WeasyPrint

Phase 4 — Sem\. 11\-12 Juillet

Module financier

Frais \(matrice TarifScolarite\), Paiements, Reçus PDF, Tableau de bord comptable

Phase 5 — Sem\. 13\-14 Juillet

Qualité & Utilisabilité

Tests > 80% coverage, tests utilisateurs, corrections UX

Phase 6 — Sem\. 15\-16 1er Août

Déploiement & Go\-Live

Docker prod, SSL, monitoring Grafana, formation, mise en production

## 10\.1 Priorisation MVP vs V2 — Mise à jour v3\.3

__Module__

__MVP \(avant sept\. 2026\)__

__V2 \(après sept\. 2026\)__

Licences

✅ Complet

—

⭐ Paramètres établissement

✅ Complet

—

⭐ Enregistrement élèves

✅ Complet

—

⭐ Inscription / Réinscription

✅ Complet

—

⭐ Agent de Vie Scolaire \(AVS\)

✅ Essentiel

Tableau de bord avancé

Notes & Bulletins MENA

✅ Complet

—

Présences & Discipline

✅ Essentiel

QR Code avancé, RFID

Examens CEP/BEPC/BAC

✅ Complet

BEP/CAP technique

Certificats de scolarité

✅ Complet

—

Attestations non\-redevabilité

✅ Complet

—

Cursus scolaire

✅ Complet

Format bilingue FR/EN

Autorisations d'absence

✅ Complet

—

⭐ Carte d'identité scolaire

✅ Complet

—

⭐ Gestion des Vacations

✅ Complet

Tableau de bord avancé

⭐ Gestion du Personnel \(v3\.2\)

✅ Complet

Module RH avancé

⭐ Statistiques listes classes

✅ Complet

—

Finances

✅ Base

Mobile Money, comptabilité avancée

Portail parents

❌

✅ Complet avec demande documents

IA pédagogique

❌

✅ Modèle prédictif scikit\-learn

Multilingue Mooré/Dioula

❌

✅ Complet

# 11\. NOM ET IDENTITÉ — YELEN SCHOOL

__Critère__

__Analyse__

Nom retenu

YELEN SCHOOL

Étymologie

"Yelen" = Lumière en Dioula — parlé par des millions de Burkinabè

Symbolique

Lumière = connaissance, éveil, espoir — valeurs fondamentales de l'éducation

Slogan

"Illuminer chaque parcours scolaire"

Mémorabilité

Court, percutant, prononçable en Français, Mooré, Dioula et Fulfuldé

# CONCLUSION — CE QUI A CHANGÉ EN v3\.3

✅ Résumé des ajouts v3\.3 \(par rapport à v3\.2\)

1\. ⭐ CALCUL AUTOMATIQUE DE L'ÂGE À L'ENREGISTREMENT :

   Dès la saisie de la date de naissance dans l'Étape 1 du formulaire d'enregistrement,

   l'âge de l'élève est calculé et affiché immédiatement dans un champ en LECTURE SEULE

   \(fond grisé, non saisie\)\. L'âge est calculé par rapport à la date du jour\.

   Il n'est pas stocké en base — toujours recalculé dynamiquement depuis la date de naissance\.

   Formule : aujourd'hui \- date\_naissance \(en années entières révolues\)\.

   Implémentation : property Python côté modèle \+ calcul JS côté frontend \(date\-fns\)\.

2\. ⭐ AFFICHAGE DATE DE NAISSANCE \+ ÂGE CALCULÉ À L'INSCRIPTION :

   Lors de l'affichage automatique des informations de l'élève après sélection du matricule

   à l'écran d'inscription, la date de naissance et l'âge calculé sont tous deux affichés

   en LECTURE SEULE \(non modifiables à cet écran\)\.

   Tous les champs personnels de l'élève sont en consultation uniquement\.

   Seuls la classe, l'année scolaire et le statut élève sont modifiables à l'inscription\.

   Toute correction de la date de naissance doit passer par l'écran d'enregistrement\.

Confirmés de v3\.2 : Gestion Personnel \(MembrePersonnel, InscriptionPersonnel, matricule PERS\-\)

· Statistiques listes classes \(BLOC 1 filles/garçons · BLOC 2 âges · BLOC 3 redoublants\)\.

Confirmés de v3\.1 : Matricule élève · Inscription par matricule · Directeur/Proviseur · Vacations\.

Confirmés de v3\.0 : Paramètres · Enregistrement · AVS · Carte d'Identité Scolaire\.

## Prochaines étapes

- Valider la spec v3\.3 avec les directeurs et proviseurs d'école partenaires
- Implémenter le calcul dynamique de l'âge côté frontend \(onChange date\_naissance → calcul JS avec date\-fns\)
- Ajouter la property Python age sur le modèle Eleve \(calcul serveur\)
- Exposer le champ age en lecture seule dans les serializers DRF \(age = SerializerMethodField\)
- Intégrer l'affichage date de naissance \+ âge calculé dans l'écran d'inscription \(readonly\)
- Tester les cas limites : anniversaire aujourd'hui, date de naissance dans le futur \(validation\), date inconnue
- Créer l'app Django personnel/ avec MembrePersonnel et InscriptionPersonnel
- Développer les statistiques de classe \(BLOC 1, 2, 3\) et les intégrer dans les listes PDF

