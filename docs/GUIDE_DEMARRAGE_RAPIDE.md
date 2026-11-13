---
titre: Guide de démarrage rapide — YELEN SCHOOL
version_logiciel: 5.51.0
date_mise_a_jour: 04/11/2026
public: direction, secrétariat, comptabilité, enseignants d'un établissement qui démarre
---

# Guide de démarrage rapide — YELEN SCHOOL

Ce guide tient en dix pages. Il donne, dans l'ordre, ce qu'il faut faire pour qu'un établissement
soit opérationnel sur YELEN SCHOOL : **le premier jour** (paramétrage), **la rentrée** (élèves et
comptes), **le quotidien** (appel, paiements, notes), **chaque trimestre** (bulletins) et **la fin
d'année**. Chaque étape renvoie à la section détaillée du *Guide d'utilisation* complet
(`docs/GUIDE_UTILISATION_YELEN_SCHOOL.md`), consultable dans l'application : menu **Aide** —
le point d'interrogation en haut de chaque page ouvre directement la section du module en cours.

> Convention : `Menu → Sous-menu` désigne un chemin dans la barre latérale ; **§ 3.1** renvoie à la
> section 3.1 du guide complet.

---

## 1. Avant de commencer

**Ce qu'il faut**

- Le serveur de l'école allumé, avec YELEN SCHOOL démarré (mode serveur Docker `C:\YELEN-SCHOOL` :
  double-clic sur `demarrage.bat` ; mode autonome sans Docker : `demarrer-autonome.bat`). Détails : § 31 et § 34.3.
- L'adresse à saisir dans le navigateur des postes du réseau local, affichée au démarrage
  (`http://IP-DU-SERVEUR:8001` ou `https://IP-DU-SERVEUR:8443` quand le HTTPS local est activé), et,
  pour la **saisie à distance des enseignants hors de l'établissement**, l'accès sécurisé **Tailscale**
  configuré sur le serveur (*Guide de déploiement Windows*, section 9.5).
- Un navigateur récent : Chrome, Edge ou Firefox. L'application fonctionne entièrement sur le
  réseau local, sans Internet ; seuls les SMS, les e-mails et les notifications push sortent.
- Le compte **Super Admin** remis à l'installation. À la première connexion, l'application impose
  un **nouveau mot de passe** puis l'activation de la **double authentification** (Super Admin et
  Directeur) : une application type Google Authenticator ou FreeOTP suffit (§ 2.6).

**Trois règles pour toute l'année**

1. **Une seule base de données** : tout le monde travaille sur le serveur de l'école, jamais sur
   une copie locale.
2. **Un compte par personne**, jamais de compte partagé : le journal d'audit (§ 18.6) attribue
   chaque action à son auteur.
3. **Une sauvegarde par semaine sur un support externe** (clé USB, disque) en plus de la
   sauvegarde automatique du serveur (§ 9.32).

---

## 2. Jour 1 — Paramétrer l'établissement

L'ordre compte : chaque étape alimente la suivante. Comptez une demi-journée.

| # | Étape | Où | Guide |
|---|-------|----|-------|
| 1 | **Fiche unique de l'établissement** : nom, code, agrément, adresse, coordonnées, logo, cachet et devise. Ces données alimentent l'application et les PDF depuis un seul formulaire. | `Paramètres → Établissement` | § 3.1 |
| 2 | **Année scolaire** : libellé (`2026-2027`), dates, case **Année en cours**. | `Paramètres → Années scolaires` | § 3.3 |
| 3 | **Périodes d'évaluation** : trimestres (ou semestres) avec leurs dates ; elles pilotent la saisie des notes et les bulletins. | `Paramètres → Périodes` | § 3.4 |
| 4 | **Classes** : une classe par division (6e A, 6e B…), avec sa **capacité** — l'inscription dans une classe pleine est refusée. | `Paramètres → Classes` | § 4.2 |
| 5 | **Salles** (facultatif, utile pour l'emploi du temps). | `Paramètres → Salles` | § 9.30 |
| 6 | **Matières** et leur **configuration par cycle et par niveau** (coefficient, enseignée ou non). | `Pédagogie → Matières` | § 6.2 |
| 7 | **Enseignements** : pour chaque classe, la matière et l'enseignant qui l'assure. Sans enseignement, ni appel ni saisie de notes. | `Pédagogie → Enseignements` | § 6.2 |
| 8 | **Tarifs** : frais de scolarité par niveau et statut, tranches et échéances. | `Paramètres → Tarifs`, `Finances → Paramètres financiers` | § 9.3, § 9.4, § 9.17 |
| 9 | **Signataires des documents** : qui signe les bulletins, certificats, reçus (signature scannée facultative). | `Paramètres → Signataires des documents` | § 6.3, § 12.1 |
| 10 | **Appréciations et mentions** : barèmes des appréciations de moyenne (secondaire et primaire). | `Paramètres → Appréciations`, `Paramètres → Mentions` | § 6.3 |

**Vérification de fin de journée** : ouvrir `Pilotage` (tableau de bord direction, § 2.4) — les
compteurs *classes*, *enseignements* et *tarifs* ne doivent plus être à zéro.

---

## 3. Jour 2 — Les comptes du personnel

1. **Créer les comptes** : `Utilisateurs → Nouvel utilisateur` — rôle (Directeur, Censeur, AVS,
   Secrétaire, Comptable, Enseignant…), établissement, téléphone (§ 2.6). Le mot de passe
   provisoire est changé par l'intéressé à sa première connexion.
2. **Régler les droits d'accès** : `Paramètres → Droits d'accès` — une colonne par rôle, une ligne
   par fonctionnalité jusqu'au niveau de l'action (ex. *Clôturer une période*). Par défaut, tout
   est ouvert au personnel sauf les finances, réservées à la direction et à la comptabilité (§ 3.7).
3. **Rattacher les enseignants à leurs enseignements** (étape 7 du jour 1) : c'est ce qui limite
   leurs listes aux classes où ils interviennent.
4. **Thème et profil** : chaque utilisateur choisit dans `Mon profil` son apparence (sombre, clair
   ou selon l'appareil), sa photo et ses alertes (§ 2.6).

> Les enseignants peuvent faire l'appel et saisir les notes depuis un smartphone, même sans réseau
> momentanément (§ 7.8, § 27.6). Donnez-leur l'adresse de l'application et montrez-leur
> **Mes cours** sur le tableau de bord.

---

## 4. La rentrée — Élèves, inscriptions, parents

### 4.1 Deux façons de constituer le fichier élèves

- **Import depuis vos fichiers existants** (Excel/CSV d'un ancien logiciel ou d'un registre
  saisi) : `Élèves → Importer`. Le fichier est contrôlé ligne à ligne avant toute écriture ;
  les parents sont créés en même temps (§ 36.1).
- **Saisie fiche par fiche** : `Élèves → Nouvel élève` — nom, prénoms, date et lieu de naissance,
  sexe, parent/tuteur, téléphone. L'application détecte les **homonymes** (même nom, prénom et date
  de naissance) et demande confirmation avant de créer un doublon (§ 4.1).

### 4.2 Inscrire

Depuis la fiche de l'élève, bouton **Inscrire** : année, classe, statut (nouveau, redoublant,
transféré…). Le matricule est attribué automatiquement. Les classes pleines sont refusées, les
années clôturées sont verrouillées (§ 4.2). Pour les dossiers reçus avant la rentrée, utilisez les
**pré-inscriptions** (§ 9.31).

### 4.3 Documents de rentrée

- **Liste alphabétique** et **liste des appels** par classe (§ 12.7, § 7.7).
- **Cartes scolaires** avec photo et QR code (§ 12.6).
- **Certificats de scolarité** à la demande (§ 12.2).

### 4.4 Ouvrir le portail aux parents et aux élèves

1. `Utilisateurs → Comptes parents en masse` : création **en masse** des comptes parents à partir des
   numéros de téléphone des fiches ; identifiant = numéro de téléphone (§ 9.23).
2. `Utilisateurs → Comptes élèves en masse` : création **en masse** des comptes élèves ; identifiant =
   **matricule**, celui qui figure au dos de la carte scolaire (§ 9.23, § 19.6).
3. Communiquer l'adresse du portail et la procédure d'installation sur Android (§ 19.1).
4. Le parent voit : frais et paiements, absences et justificatifs, bulletins, devoirs et cahier de
   textes, documents délivrés, notifications (§ 19). L'élève voit son dossier, son bulletin en lecture,
   sa carte scolaire, ses documents et ses notifications (§ 19.6).

**Vérification** : `Pilotage` affiche l'effectif par classe, le taux de remplissage et le nombre de
comptes parents actifs.

---

## 5. Le quotidien

### 5.1 L'appel (vie scolaire, enseignants)

`Présences → Faire l'appel` : classe, séance, cases Présent / Absent / Retard, **Enregistrer**.
Depuis un smartphone : tableau de bord → **Mes cours** (§ 7.1, § 7.8). Un SMS d'absence peut
partir automatiquement vers le parent (§ 3.8). Les justificatifs se traitent dans
`Présences → Justifications` ; le parent peut en déposer depuis le portail (§ 7.3).

### 5.2 Les paiements (comptabilité)

1. `Finances → + Nouveau paiement` ou icône `$` sur la fiche élève : montant, mode (espèces,
   Mobile Money, virement), tranche concernée → **Enregistrer** (§ 9.1).
2. Le **reçu A5** s'imprime aussitôt ; il reste réimprimable depuis l'historique (§ 9.6).
3. Un paiement enregistré **ne se supprime pas** : en cas d'erreur, un **remboursement** ou une
   écriture corrective est saisi, et tout reste tracé (§ 9.1).
4. **Fin de journée** : `Finances → Journal de caisse` → arrêté de caisse (§ 9.16).
5. **Chaque semaine** : `Finances → Redevables` (paginé par 50 élèves et filtrable par classe, § 9.8) et,
   si besoin, `Finances → Relances` pour générer les lettres et les SMS de relance (§ 9.11).

Mobile Money (Orange Money, Moov Money) : encaissement, relevés et rapprochement, § 9.14 et § 9.15.

### 5.3 Les notes et le cahier de textes (enseignants)

- **Cahier de textes** : après chaque cours, `Pédagogie → Cahier de textes` — contenu de la séance
  et travail à faire ; les parents et les élèves le voient sur leur portail (§ 6.1, § 19.5).
- **Évaluations** : `Pédagogie → Évaluations` → créer le devoir ou la composition (type, date,
  coefficient), puis `Pédagogie → Saisie des notes` : une grille par classe, enregistrement note
  par note (§ 6.2, FAQ Q4). Hors réseau, la saisie est conservée sur l'appareil et envoyée au retour de la
  connexion (§ 27.6).

### 5.4 La discipline et le suivi

`Vie scolaire → Sanctions` pour enregistrer un avertissement, une exclusion temporaire…, avec
notification du parent (§ 8.2). La **fiche de suivi** de l'élève regroupe absences, sanctions,
notes et paiements (§ 8.1). Le **capital de points discipline** est optionnel (§ 8.5).

---

## 5 bis. Le personnel au quotidien

| Étape | Où | Guide |
|-------|----|-------|
| **Pointage du jour** : arrivées, départs, retards et absences (une ligne par agent, enregistrement en une passe) | `Personnel → Pointage` | § 5.5 |
| **Feuille de pointage du mois** : heures, retards, absences, PDF signé | `Personnel → Pointage du mois` | § 5.5 |

---

## 6. Chaque trimestre — Des notes aux bulletins

1. **Vérifier la saisie** : `Pilotage → Enseignants` indique, par enseignant, le taux de notes
   saisies — en rouge sous 80 % (§ 9.27).
2. **Appréciations par matière** : chaque enseignant renseigne les siennes (§ 9.22).
3. **Clôture de la période** : la période se verrouille **automatiquement** dès que sa date de fin est
   dépassée (ou manuellement via `Paramètres → Périodes` → **Clôturer**). Seule la **direction** peut
   rouvrir temporairement une période échue en saisissant un motif obligatoire, tracé au journal d'audit (§ 3.4).
4. **Conseil de classe** : `Bulletins → [Classe] → [Trimestre]` → bouton **Saisir** sur chaque
   élève (absences, mention, appréciation du conseil) ; décisions et procès-verbal (§ 6.3, § 8.7).
5. **Générer les bulletins** : bouton **PDF** de la classe — un bulletin A4 par élève, toutes les
   disciplines, moyennes à deux décimales, QR code de vérification, signature du signataire
   configuré (§ 6.3). Bulletins en retard de paiement : blocage paramétrable (§ 9.18).
6. **Remettre aux parents** : impression, ou publication sur le portail avec signature
   électronique du parent (§ 19.4, § 20).
7. **Relevés et analyses** : moyennes par discipline, relevé de notes, palmarès, élèves à risque de
   décrochage (§ 6.4 à § 6.6).

---

## 7. Fin d'année

| Étape | Où | Guide |
|-------|----|-------|
| Bulletin **annuel** et palmarès (moyenne des trimestres, décision finale) | `Bulletins → Annuel` | § 6.3.3, § 6.3.4 |
| **Statistiques officielles** de fin d'année (MENAPLN) et fichiers d'inscription aux examens | `Documents → Statistiques officielles`, `Examens` | § 12.15, § 10.6 |
| **Entretien annuel d'évaluation** de chaque agent (grille 0–5, bilan, objectifs, PDF signé) | `Personnel → Évaluations annuelles` | § 5.6 |
| **Prêts et retards** : relancer les familles (portail + SMS), imprimer la liste des retards | `Manuels → Prêts et retards` | § 26.5 bis |
| **Manuels non rendus** | `Manuels → Non rendus` | § 26.5 |
| **Clôturer l'année** : plus aucune inscription ni paiement modifiable sur cette année | `Paramètres → Années scolaires` | § 3.2 |
| Créer l'**année suivante** (sans la rendre courante tout de suite) | `Paramètres → Années scolaires` | § 3.3 |
| **Passage de classe** : réinscription en masse d'après les décisions du conseil | `Élèves → Passage de classe` | § 4.3 |
| Rendre la nouvelle année **courante** le jour de la rentrée | `Paramètres → Années scolaires` | § 3.2 |

Les données des années passées restent consultables (bulletins, paiements, archives, § 12.9).

---

## 8. Communiquer avec les parents

- **Configuration SMS** : `Paramètres → Configuration SMS` — un téléphone Android avec la
  passerelle SMS installée, ou un fournisseur en ligne ; bouton **Tester** (§ 3.5).
- **SMS automatiques** : absence du jour, retard de paiement, publication des bulletins, prêt
  d'ouvrage en retard (relance tous les 3 jours, § 26.5 bis), compte rendu quotidien à la direction
  — activables ligne par ligne (§ 3.8).
- **Campagnes ciblées** : une classe, les redevables, tous les parents (§ 9.24) ; **circulaires**
  et **convocations** PDF (§ 12.12, § 12.13).
- **Messages avec réponse** : le parent répond par un lien ou par SMS ; les réponses sont suivies
  dans `Communication` (§ 28, § 32).
- **Portail parent** et **notifications push** sur téléphone, sans SMS payant (§ 19.3) ; le personnel
  peut aussi recevoir les notifications de l'application sur son téléphone (§ 18.5).
- **Réunions de parents** : convocations, présences, compte rendu (§ 18.7).

---

## 9. Sécurité et sauvegardes (direction)

- **Exploitation** : `Administration → Exploitation` — santé du serveur, espace disque, file SMS,
  erreurs applicatives, sauvegardes, **restauration testée** et **usage anonyme des modules** sur 7 et
  30 jours (§ 3.6). Une alerte apparaît sur le tableau de bord dès qu'un point critique est en défaut.
- **Sauvegarder et tester la restauration** : bouton **Sauvegarder maintenant** puis **Télécharger** la
  sauvegarde sur un support externe chaque semaine (en plus de la sauvegarde automatique nocturne, § 9.32).
  **Une fois par trimestre**, double-cliquer sur `C:\YELEN-SCHOOL\tester-restauration.bat` : la dernière
  sauvegarde est vérifiée dans une base temporaire sans toucher aux données de l'école et le résultat
  s'affiche dans `Exploitation` (§ 3.6).
- **Mots de passe** : jamais partagés, changés au départ d'un agent ; compte **désactivé** (pas
  supprimé) quand une personne quitte l'établissement (§ 2.6).
- **Journal d'audit** : `Paramètres → Journal d'audit` — qui a fait quoi, quand (§ 18.6).
- **Mises à jour** : directement depuis le menu latéral **Configuration → Mise à jour en ligne** (ou
  **Configuration → Mise à jour** avec une archive `.zip` hors connexion), ou sur le serveur via
  `C:\YELEN-SCHOOL\mettre-a-jour.bat` hors heures de pointe ; l'application effectue une sauvegarde
  chiffrée préalable et revient en arrière seule en cas d'anomalie (§ 35.2).
- **Licence** : `Mon abonnement` indique l'échéance ; un bandeau prévient 30 jours avant (§ 13).

---

## 10. En cas de problème

| Symptôme | Que faire |
|----------|-----------|
| « Mot de passe oublié » | Lien sous le formulaire de connexion (e-mail) ou réinitialisation par la direction dans `Utilisateurs` (§ 16, Q1). |
| Un enseignant ne voit pas sa classe | Vérifier l'**enseignement** (classe × matière × enseignant) pour l'année en cours (§ 6.2). |
| Inscription refusée | Classe **pleine** (augmenter la capacité) ou année **clôturée** (§ 4.2). |
| Un bulletin manque une discipline | La matière n'est pas configurée pour ce niveau ou l'enseignement n'existe pas (§ 6.2). |
| SMS non envoyés | `Paramètres → Configuration SMS` → **Tester** ; état de la passerelle dans `Exploitation` (§ 3.5, § 3.6). |
| Application lente | `Exploitation` : espace disque, mémoire, nombre de postes ; FAQ Q10 (§ 16). |
| Page d'erreur ou comportement anormal | `Exploitation → Erreurs applicatives` donne le détail à transmettre au support (§ 3.6). |

**Aide dans l'application** : icône **?** en haut de chaque page (section du module en cours),
menu **Aide** pour le guide complet, et pour la direction l'**assistant** qui répond aux questions
sur les données et le fonctionnement (§ 24).

---

## Annexe A — Qui fait quoi

| Rôle | Au quotidien | Périodiquement |
|------|--------------|----------------|
| **Directeur / Proviseur** | Pilotage, validation des décisions, communication | Clôtures de période et d'année, droits d'accès, sauvegardes externes |
| **Censeur** | Emploi du temps, suivi des notes, conseils de classe | Bulletins, statistiques pédagogiques |
| **Secrétaire** | Fiches élèves, inscriptions, certificats, convocations | Cartes scolaires, statistiques officielles |
| **Comptable** | Paiements, reçus, arrêté de caisse | Redevables, relances, Mobile Money, paie |
| **AVS / Surveillant** | Appels, absences, justificatifs, sanctions | Bilans de présence |
| **Enseignant** | Appel de ses cours, cahier de textes, notes | Appréciations, conseils de classe |
| **Parent** | Portail : paiements, absences, devoirs, messages | Bulletins et signature électronique |

## Annexe B — Liste de contrôle de rentrée

- [ ] Fiche de l'établissement complète (logo, cachet, N° Agrément)
- [ ] Année scolaire courante et périodes d'évaluation créées
- [ ] Classes avec capacité, salles
- [ ] Matières configurées par niveau, enseignements de chaque classe
- [ ] Tarifs et échéances de l'année
- [ ] Signataires des documents désignés
- [ ] Comptes du personnel créés, droits d'accès vérifiés, 2FA de la direction activée
- [ ] Élèves importés ou saisis, inscrits dans leur classe
- [ ] Comptes parents créés, adresse du portail communiquée
- [ ] Configuration SMS testée, SMS automatiques choisis
- [ ] Première sauvegarde téléchargée sur un support externe et essai `tester-restauration.bat` validé
