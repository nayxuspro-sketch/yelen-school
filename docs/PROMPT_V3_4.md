🎓

__YELEN SCHOOL__

*Système de Gestion Scolaire — Burkina Faso*

*"Illuminer chaque parcours scolaire"*

__PROMPT FINAL OPTIMISÉ — VERSION COMMERCIALE v3\.4__

*Incluant : Modules Enregistrement · Inscription/Réinscription \(par matricule\) · Agent de Vie Scolaire*

*Paramètres · Documents · Carte d'Identité · Vacations · Personnel · Statistiques Listes Classes*

__*⭐ Signataires Paramétrables par Cycle et par Document*__

__Élément__

__Détail__

__Statut__

Version

__v3\.4 — Mars 2026__

Mis à jour

__⭐ Nouveautés v3\.4__

Signataires Paramétrables par Cycle et par Document : TypeDocument, SignataireDocument, fenêtre de config par cycle, rendu PDF

__⭐ Nouveau__

Confirmé v3\.3

Calcul automatique âge à l'enregistrement · Affichage date naissance \+ âge calculé à l'inscription \(lecture seule\)

Confirmé

Confirmé v3\.2

Gestion Personnel \(matricule PERS\-, inscription annuelle, liste H/F\) · Statistiques listes élèves

Confirmé

Confirmé v3\.1

Matricule élève unique · Inscription par matricule · Directeur/Proviseur · Vacations

Confirmé

Confirmé v3\.0

Enregistrement, Inscription, AVS, Paramètres enrichis, Carte ID

Confirmé

Cycles

Préscolaire · Primaire · Post\-primaire · Secondaire

MVP

Stack

Django 4\.2 · DRF · PostgreSQL · Redis · Docker

Inchangé

Deadline

__1er Août 2026 — avant inscriptions de septembre__

__Non négociable__

📌 NOTE SUR CE DOCUMENT v3\.4

Ce document est la mise à jour incrémentale du PROMPT v3\.3\.

Il ajoute la fonctionnalité de Signataires Paramétrables par Cycle et par Document

au Module Paramètres \(Section 4\), avec :

  • Un nouveau modèle TypeDocument \(Section 4\.12\)

  • Un nouveau modèle SignataireDocument \(Section 4\.12\)

  • Une interface de configuration par cycle \(onglets\)

  • Le rendu automatique sur tous les documents PDF

  • La mise à jour du tableau récapitulatif Section 4\.11

  • La mise à jour de la conclusion et des prochaines étapes

Toutes les autres sections \(1 à 9quater, roadmap\) restent inchangées par rapport à v3\.3\.

# __4\. ⭐ MODULE PARAMÈTRES — MISE À JOUR v3\.4__

📋 App Django : parametres — Ajout v3\.0, enrichi v3\.4

Ce module centralise toute la configuration de l'établissement scolaire\.

Il doit être configuré en premier, avant tout autre module, car tous les autres modules en dépendent\.

Accessible uniquement par le Directeur et le Super Admin Éditeur\.

⭐ v3\.4 : Ajout du paramétrage des Signataires par Cycle et par Document \(Section 4\.12\)\.

*Les sections 4\.1 à 4\.10 sont inchangées par rapport à la version v3\.3\.*

*La section 4\.11 est mise à jour pour inclure les nouveaux modèles TypeDocument et SignataireDocument\.*

__*La section 4\.12 est entièrement nouvelle\.*__

## __4\.11 Résumé des modèles du module Paramètres__

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

Affecté, Non affecté, Boursier, Exonéré, Redoublant\.\.\.

RubriquePaiement

Types de frais : scolarité, inscription, cantine\.\.\.

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

__⭐ TypeDocument__

Types de documents pouvant porter une signature \(v3\.4\)

__⭐ SignataireDocument__

Signataire par cycle × type document × année scolaire \(v3\.4\)

## __4\.12 ⭐ Signataires Paramétrables par Cycle et par Document \-\-\- NOUVEAU v3\.4__

📋 Contexte métier : Dans un établissement multi\-cycles, chaque cycle \(Préscolaire, Primaire,

Post\-primaire, Secondaire\) a son propre personnel de direction et d'encadrement\.

Chaque type de document officiel \(certificat de scolarité, bulletin de notes, reçu de paiement,

autorisation d'absence, attestation, cursus, carte d'identité scolaire\.\.\.\) doit porter la signature

du responsable désigné POUR CE CYCLE, et non une signature unique pour tout l'établissement\.

Ce module permet de configurer, pour chaque cycle, quel membre du personnel signe quel document\.

Le nom, le prénom et le titre honorifique du signataire s'affichent automatiquement en bas du document\.

### __Modèle Django \-\-\- TypeDocument__

__parametres/models\.py \-\-\- TypeDocument__

id

code           \(ex: CERT\_SCOL / BULLETIN / RECU\_PAIEMENT / AUTORISATION /

                ATTESTATION / CURSUS / CARTE\_ID / LISTE\_CLASSE / LISTE\_PERSONNEL\)

libelle        \(ex: Certificat de Scolarité, Bulletin de Notes, Reçu de Paiement\.\.\.\)

description    \(CharField optionnel\)

actif          \(BooleanField\)

ordre\_affichage \(IntegerField\)

created\_at

__Types de documents standards pré\-configurés :__

__Code__

__Libellé du document__

CERT\_SCOL

Certificat de Scolarité

BULLETIN

Bulletin de Notes Trimestriel / Semestriel

RECU\_PAIEMENT

Reçu de Paiement \(Scolarité, Inscription, etc\.\)

AUTORISATION

Autorisation d'Absence

ATTESTATION

Attestation de Non\-Redevabilité

CURSUS

Cursus Scolaire Complet

CARTE\_ID

Carte d'Identité Scolaire

LISTE\_CLASSE

Liste Alphabétique de Classe

LISTE\_PERSONNEL

Liste du Personnel

### __Modèle Django \-\-\- SignataireDocument__

__parametres/models\.py \-\-\- SignataireDocument__

id

cycle              \(FK Cycle \-\-\- fenêtre de paramétrage par cycle\)

type\_document      \(FK TypeDocument \-\-\- le type de document à signer\)

membre\_personnel   \(FK MembrePersonnel \-\-\- le signataire sélectionné\)

titre\_honorifique  \(CharField optionnel \-\-\- ex: M\., Mme, Dr, Prof\., M\. le Directeur\)

actif              \(BooleanField \-\-\- permet de désactiver sans supprimer\)

annee\_scolaire     \(FK AnneeScolaire \-\-\- signataire valide pour cette année\)

created\_at · updated\_at

Contrainte unique : \(cycle, type\_document, annee\_scolaire\)

→ Un seul signataire actif par \(cycle × type de document × année scolaire\)\.

Méthode : SignataireDocument\.get\_signataire\(cycle, type\_doc, annee\) → SignataireDocument | None

### __Interface de Paramétrage \-\-\- UX par Cycle__

🖥️ Principe d'affichage : Le paramétrage des signataires est accessible depuis

Paramètres → Signataires des Documents\.

L'interface est organisée en ONGLETS : un onglet par cycle actif de l'établissement\.

Ex : \[Préscolaire\] \[Primaire\] \[Post\-primaire\] \[Secondaire\]

Chaque onglet affiche la configuration des signataires propre à ce cycle\.

Le personnel disponible dans chaque onglet est FILTRÉ : seuls les membres du

personnel inscrits dans ce cycle \(via InscriptionPersonnel\) sont proposés à la sélection\.

__Contenu de chaque onglet cycle :__

__Type de Document__

__Signataire sélectionné__

__Titre Honorifique__

Certificat de Scolarité

Liste déroulante → personnel du cycle

Champ texte libre \(ex: M\. le Directeur\)

Bulletin de Notes

Liste déroulante → personnel du cycle

Champ texte libre

Reçu de Paiement

Liste déroulante → personnel du cycle

Champ texte libre

\.\.\. \(tous les types actifs\)

\.\.\.

\.\.\.

__Comportement de la liste déroulante :__

- Affiche : TITRE NOM Prénom \(Poste\) \-\-\- ex : M\. OUEDRAOGO Boureima \(Directeur\)
- Filtré par cycle ET par année scolaire courante
- Seuls les membres avec InscriptionPersonnel\.actif = True sont proposés
- Si aucun membre n'est disponible pour le cycle, un message d'alerte s'affiche

### __Rendu sur les Documents PDF__

📄 Sur chaque document généré \(PDF/A via WeasyPrint\), la zone de signature en bas du

document affiche automatiquement les informations du signataire configuré pour ce cycle :

┌─────────────────────────────────────────────────────────────┐

│                                                             │

│   \[Ville\], le \[Date de génération\]                         │

│                                                             │

│   \[Titre Honorifique\] \[NOM\] \[Prénom\]                       │

│   \[Intitulé du Poste\]                                       │

│                                                             │

│   \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_                                   │

│   \(Signature et Cachet\)                                     │

│                                                             │

└─────────────────────────────────────────────────────────────┘

Si aucun signataire n'est configuré pour ce cycle \+ type de document,

le système utilise par défaut le Directeur/Proviseur de l'IdentiteEtablissement\.

__Données affichées dans la zone signature :__

__Donnée affichée__

__Source__

__Exemple__

Titre honorifique

SignataireDocument\.titre\_honorifique

M\. le Directeur

Nom en MAJUSCULES

MembrePersonnel\.nom\.upper\(\)

OUEDRAOGO

Prénom

MembrePersonnel\.prenom

Boureima

Intitulé du poste

InscriptionPersonnel → Poste\.intitule

Directeur

Ville

IdentiteEtablissement\.ville

Ouagadougou

Date

Date de génération du document

10 Mars 2026

### __Modèle Django \-\-\- Mise à jour IdentiteEtablissement__

⚠️ Impact sur l'IdentiteEtablissement :

Le champ signature\_directeur \(ImageField\) existant dans IdentiteEtablissement

reste utilisé comme signature par défaut globale \(ex : en\-tête PDF, cachet\)\.

Il n'est PAS remplacé par SignataireDocument \-\-\- les deux coexistent\.

SignataireDocument détermine QUI signe \(nom/prénom/titre affiché en bas\)\.

signature\_directeur détermine L'IMAGE de signature numérique \(optionnelle\)\.

### __Règles Métier \-\-\- Signataires__

- Un seul signataire actif par triplet \(cycle × type\_document × annee\_scolaire\)
- Le changement de signataire en cours d'année n'invalide pas les documents déjà générés
- Si un membre du personnel quitte le cycle, son SignataireDocument passe à actif = False \-\-\- le système force la reconfiguration avant toute nouvelle génération
- La fenêtre de paramétrage n'est accessible que pour les cycles actifs de l'établissement
- Un même membre du personnel peut être signataire de plusieurs types de documents dans un même cycle
- Un même membre peut être signataire dans plusieurs cycles s'il y est inscrit \(ex : Directeur supervisant deux cycles\)
- Le titre honorifique est libre \-\-\- ex : M\., Mme, Dr\., Prof\., M\. le Directeur, Mme la Directrice, M\. le Proviseur

### __API DRF \-\-\- Endpoints SignataireDocument__

__parametres/serializers\.py \+ views\.py \-\-\- SignataireDocument__

GET    /api/parametres/signataires/?cycle=\{id\}&annee=\{id\}

       → Liste des signataires configurés pour un cycle et une année

POST   /api/parametres/signataires/

       → Créer ou mettre à jour un signataire pour \(cycle × type\_document × annee\)

PATCH  /api/parametres/signataires/\{id\}/

       → Modifier titre\_honorifique ou changer le membre\_personnel

GET    /api/parametres/signataires/resolve/

       ?cycle=\{id\}&type\_document=\{code\}&annee=\{id\}

       → Résoudre le signataire pour un document spécifique \(utilisé par WeasyPrint\)

GET    /api/parametres/personnel\-disponible/?cycle=\{id\}&annee=\{id\}

       → Liste du personnel disponible pour sélection dans un cycle donné

### __Intégration dans la Génération PDF__

🔗 Intégration dans le module Documents \(Section 8\) :

Chaque générateur de document PDF \(certificat, bulletin, reçu, etc\.\) appelle :

  signataire = SignataireDocument\.get\_signataire\(

      cycle=inscription\.classe\.cycle,

      type\_doc=TypeDocument\.objects\.get\(code='CERT\_SCOL'\),

      annee=annee\_courante

  \)

Si signataire is None → fallback sur IdentiteEtablissement\.nom\_directeur\.

Le template WeasyPrint reçoit le contexte : signataire\_nom, signataire\_prenom,

signataire\_titre, signataire\_poste pour remplir la zone de signature\.

# __CONCLUSION — CE QUI A CHANGÉ EN v3\.4__

✅ Résumé des ajouts v3\.4 \(par rapport à v3\.3\)

1\. ⭐ SIGNATAIRES PARAMÉTRABLES PAR CYCLE ET PAR DOCUMENT :

Nouveau modèle TypeDocument : répertorie tous les types de documents pouvant

porter une signature \(certificat de scolarité, bulletin, reçu, autorisation, etc\.\)\.

Nouveau modèle SignataireDocument : lie un membre du personnel à un type de document

pour un cycle donné et une année scolaire donnée\.

Contrainte unique \(cycle × type\_document × annee\_scolaire\) : un seul signataire actif\.

Interface de configuration en ONGLETS par cycle : chaque cycle a sa propre fenêtre

de paramétrage\. Le personnel disponible est filtré par cycle et par année scolaire\.

Rendu sur le document PDF : le nom, prénom et titre honorifique du signataire

s'affichent automatiquement en bas de chaque document généré\.

Fallback sur IdentiteEtablissement\.nom\_directeur si aucun signataire n'est configuré\.

API DRF dédiée : endpoints pour lister, créer, modifier et résoudre les signataires\.

Confirmés de v3\.3 : Calcul automatique âge · Affichage date naissance \+ âge à l'inscription\.

Confirmés de v3\.2 : Gestion Personnel \(MembrePersonnel, InscriptionPersonnel, matricule PERS\-\)

· Statistiques listes classes \(BLOC 1 filles/garçons · BLOC 2 âges · BLOC 3 redoublants\)\.

Confirmés de v3\.1 : Matricule élève · Inscription par matricule · Directeur/Proviseur · Vacations\.

Confirmés de v3\.0 : Paramètres · Enregistrement · AVS · Carte d'Identité Scolaire\.

## __Prochaines étapes__

- Valider la spec v3\.4 avec les directeurs et proviseurs d'école partenaires
- Créer le modèle TypeDocument avec les 9 codes standards \(migration Django\)
- Créer le modèle SignataireDocument avec contrainte unique \(cycle, type\_document, annee\_scolaire\)
- Implémenter l'interface de configuration en onglets par cycle \(Vue\.js / React\)
- Implémenter le filtrage du personnel disponible par cycle et par année scolaire
- Mettre à jour tous les générateurs PDF WeasyPrint pour appeler SignataireDocument\.get\_signataire\(\)
- Tester le fallback sur IdentiteEtablissement si aucun signataire configuré
- Mettre à jour les templates WeasyPrint \(certificat, bulletin, reçu, autorisation, attestation, cursus, carte ID\)

*YELEN SCHOOL v3\.4 — © 2026 — Tous droits réservés*

__"Illuminer chaque parcours scolaire"__

