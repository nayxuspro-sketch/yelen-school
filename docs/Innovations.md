# YELEN SCHOOL — Fonctionnalités Innovantes à Développer
> Rédigé le 03/05/2026 · Basé sur l'inventaire des 350+ fonctionnalités existantes

---

## Contexte

YELEN SCHOOL est un système de gestion scolaire complet pour les établissements privés du
Burkina Faso. Les fonctions de base sont matures (inscriptions, notes, bulletins, finances,
présences, vie scolaire, documents, API REST). Ce document recense les fonctionnalités à
fort potentiel de valeur ajoutée qui ne sont pas encore implémentées.

---

## 1. Intelligence Artificielle et Analyse Prédictive

### 1.1 Assistant IA conversationnel (Chatbot Directeur)

**Description :** Le directeur ou le proviseur pose des questions en langage naturel sur
les données de l'établissement et obtient des réponses contextualisées.

**Exemples de requêtes :**
- *"Quels élèves de Terminale A ont une moyenne en baisse depuis 2 trimestres ?"*
- *"Quel enseignant a le plus d'absences non justifiées ce mois ?"*
- *"Quel est le taux de recouvrement des frais de scolarité pour l'année en cours ?"*

**Stack technique :** Claude API (Anthropic) + function calling sur PostgreSQL · Django

**Valeur :** Transforme les données brutes en décisions actionnables sans maîtriser SQL.
Le directeur n'a plus besoin d'exporter des fichiers Excel pour analyser ses données.

---

### 1.2 Prédiction de réussite aux examens officiels (BEPC / BAC)

**Description :** Dès le deuxième trimestre, chaque élève du cycle secondaire reçoit un
score de probabilité de réussite à l'examen officiel de fin d'année, calculé à partir de
ses notes, de son taux d'assiduité et de la tendance de sa progression.

**Fonctionnalités :**
- Score de probabilité de réussite (0–100 %) affiché sur le profil élève
- Alerte automatique si un élève "à risque d'échec" est détecté
- Vue classe : classement des élèves par niveau de risque
- Rapport PDF imprimable pour le conseil de classe

**Différence avec l'existant :** Le module de décrochage actuel produit un indicateur
binaire (alerte/pas d'alerte). Ici, la prédiction cible un résultat chiffré à un examen
officiel avec un niveau de confiance.

---

### 1.3 Analyse automatique des corrélations pédagogiques

**Description :** Tableau de bord analytique qui détecte automatiquement les patterns
significatifs dans les données de l'établissement et les formule en insights lisibles.

**Exemples d'insights générés automatiquement :**
- *"Les absences du lundi matin corrèlent avec une baisse de moyenne en Mathématiques"*
- *"Les élèves ayant changé de classe en cours d'année redoublent 2× plus souvent"*
- *"La classe de 3ème B présente le plus fort taux de progression ce trimestre (+1,8 pts)"*

**Valeur :** Permet au directeur de prendre des décisions structurelles basées sur les
données réelles de son établissement.

---

## 2. Portail Parent et Communication

### 2.1 Application parent Progressive Web App (PWA)

**Description :** Transformer le portail parent existant en application installable sur
smartphone Android (sans passer par le Play Store) avec fonctionnement hors ligne.

**Fonctionnalités :**
- Installation sur l'écran d'accueil du téléphone en un clic
- Notifications push lors de la publication d'un bulletin ou d'une note
- Consultation des notes, absences et solde des frais en temps réel
- Mode hors ligne : les données de l'élève sont mises en cache localement
- Interface optimisée pour les petits écrans (mobile-first)

**Contexte BF :** Android représente 90 %+ du parc mobile au Burkina Faso.
La connexion internet est instable dans les zones péri-urbaines — le mode hors ligne
est indispensable.

---

### 2.2 Signature électronique parentale des bulletins

**Description :** À la publication du bulletin, le parent reçoit un SMS contenant un lien
sécurisé à usage unique (valable 15 jours). Il consulte le bulletin et appose une
signature numérique horodatée.

**Fonctionnalités :**
- Génération d'un jeton signé (JWT) par bulletin, valable 15 jours
- Page de consultation du bulletin accessible sans compte parent
- Bouton "Lu et signé" avec confirmation SMS de retour
- Statut "Signé le JJ/MM/AAAA" visible dans le tableau de bord de classe
- Rappel SMS automatique après 7 jours si non signé

**Valeur :** Supprime le cahier de correspondance physique et les bulletins perdus.
Preuve légale de communication avec les parents.

---

### 2.3 Communication bidirectionnelle établissement ↔ parent

**Description :** Canal de messagerie structurée permettant aux parents de répondre
aux communications de l'établissement, sans nécessiter de compte utilisateur.

**Types de messages pris en charge :**
- Convocation à un entretien (le parent choisit un créneau parmi ceux proposés)
- Avertissement de comportement (le parent accuse réception)
- Demande de justificatif d'absence (le parent télécharge un document)
- Relance de paiement (le parent indique une date de règlement prévisionnelle)

**Différence avec l'existant :** Les SMS actuels sont unidirectionnels. Ici, le parent
dispose d'un formulaire de réponse accessible via un lien SMS sécurisé.

---

## 3. Gestion Pédagogique Avancée

### 3.1 Cahier de textes numérique

**Description :** Après chaque cours, l'enseignant renseigne en quelques secondes :
la matière traitée, les devoirs donnés et leur date de rendu.

**Fonctionnalités :**
- Saisie rapide par l'enseignant (HTMX, sans rechargement)
- Vue directeur : avancement du programme par classe et par matière
- Vue parent : devoirs de l'élève du jour, à venir, en retard
- Alertes automatiques si un cours n'a pas été renseigné depuis N jours
- Export PDF du cahier de textes mensuel (pour les inspections)

**Contexte :** Fonctionnalité absente du système et fortement demandée par les
établissements privés du Burkina Faso.

---

### 3.2 Bulletins de compétences (Préscolaire / Primaire)

**Description :** Pour les petits cycles, remplacer les notes chiffrées sur 20 par un
système d'évaluation par compétences, plus adapté au développement de l'enfant.

**Niveaux d'acquisition :**
- ✅ **Acquis** — L'élève maîtrise la compétence
- 🔄 **En cours d'acquisition** — Des progrès sont visibles
- ❌ **Non acquis** — Un accompagnement est nécessaire

**Fonctionnalités :**
- Référentiel de compétences configurable par cycle et par matière
- Saisie par l'enseignant avec pictogrammes (interface tactile-friendly)
- Bulletin PDF spécifique avec mise en page adaptée aux jeunes enfants
- Compatible avec le modèle de bulletin existant (extension, pas remplacement)

---

### 3.3 Gestion des manuels scolaires

**Description :** Inventaire et traçabilité nominative des manuels scolaires de
l'établissement, du stock à l'élève et retour.

**Fonctionnalités :**
- Catalogue de manuels par niveau, matière et année
- Attribution nominative d'un manuel à un élève (avec QR code unique par exemplaire)
- Suivi de l'état de conservation (Neuf / Bon / Usagé / Détérioré)
- Alerte en fin d'année scolaire pour les manuels non rendus
- Facturation automatique du manuel non rendu dans les frais de l'élève
- Export PDF de l'inventaire par classe

---

### 3.4 Génération automatique de l'emploi du temps

**Description :** À partir des contraintes de l'établissement (enseignants, classes,
matières, salles, volumes horaires), générer automatiquement un emploi du temps
sans conflits.

**Contraintes gérées :**
- Un enseignant ne peut pas être dans deux classes simultanément
- Une salle ne peut pas accueillir deux classes en même temps
- Respect des volumes horaires hebdomadaires par matière
- Préférences horaires des enseignants (optionnel)

**Approche technique :** Algorithme de backtracking avec contraintes ou coloration
de graphe. Interface de validation manuelle avec détection des conflits en temps réel.

---

## 4. Finances Avancées

### 4.1 Intégration paiement Mobile Money

**Description :** Permettre aux parents de payer les frais scolaires directement depuis
leur téléphone via Orange Money ou Moov Money Burkina Faso.

**Fonctionnement :**
1. Le comptable crée une demande de paiement depuis YELEN SCHOOL
2. Le parent reçoit un SMS avec le montant et un code de référence
3. Le parent effectue le paiement sur son application Mobile Money
4. Un webhook notifie YELEN SCHOOL : le paiement est enregistré automatiquement
5. Le reçu PDF est généré et envoyé par SMS au parent

**Impact :** Le Mobile Money est le mode de paiement dominant au Burkina Faso pour
les transactions du quotidien. Cette intégration élimine les déplacements à l'école
pour régler les frais.

---

### 4.2 Budget prévisionnel et suivi des dépenses

**Description :** Module comptabilité complet intégrant les dépenses de l'établissement
pour produire un compte de résultat et un tableau de trésorerie.

**Fonctionnalités :**
- Saisie des dépenses par catégorie (salaires, fournitures, maintenance, utilities...)
- Budget annuel prévisionnel par poste de dépense
- Tableau de bord trésorerie : recettes réelles vs dépenses réelles vs budget
- Compte de résultat mensuel et annuel
- Export PDF et XLSX des états financiers
- Alertes si un poste de dépense dépasse le budget prévu

**Différence avec l'existant :** Le module finances actuel ne gère que les encaissements
(recettes). Les dépenses sont totalement absentes.

---

### 4.3 Tableau de bord financier réseau multi-établissements

**Description :** Pour les groupes scolaires, consolider et comparer les performances
financières de tous les établissements du réseau dans une vue unique.

**Indicateurs consolidés :**
- Taux de recouvrement par établissement et global
- Volume total encaissé ce mois / cette année
- Établissements en retard de recouvrement (alerte rouge)
- Comparaison du coût par élève entre établissements
- Projection de fin d'année basée sur la tendance actuelle

---

## 5. Vie Scolaire Étendue

### 5.1 Module infirmerie et santé des élèves

**Description :** Dossier médical allégé et journal de l'infirmerie pour chaque élève.

**Données du dossier médical :**
- Groupe sanguin, allergies connues, traitements en cours
- Contacts d'urgence (différents des contacts parents)
- Carnet de vaccination (avec dates et rappels)
- Antécédents médicaux importants

**Journal infirmerie :**
- Enregistrement de chaque passage (date, motif, soin apporté, suite donnée)
- Notification automatique aux parents si l'enfant est renvoyé chez lui
- Rapport mensuel des passages par classe

---

### 5.2 Gestion du transport scolaire

**Description :** Gérer les circuits de bus, les élèves transportés et le pointage
embarquement / débarquement.

**Fonctionnalités :**
- Création de circuits (itinéraires, arrêts, horaires)
- Affectation des élèves à un circuit
- Pointage par QR code à l'embarquement et au débarquement
- Notification SMS aux parents à l'arrivée de l'enfant à l'école
- Alerte si un élève attendu n'a pas été pointé après l'heure d'arrivée
- Gestion de la facturation du service transport

---

### 5.3 Gestion des stages (Secondaire technique et professionnel)

**Description :** Module dédié à la gestion des stages en entreprise pour les filières
techniques et professionnelles du secondaire.

**Fonctionnalités :**
- Base de données des entreprises partenaires de stage
- Demande de stage : formulaire élève + validation établissement
- Génération automatique de la convention de stage (PDF)
- Fiche de suivi hebdomadaire remplie par le maître de stage (accessible en ligne)
- Grille d'évaluation de fin de stage
- Note de stage intégrée automatiquement au bulletin trimestriel

---

## 6. Infrastructure et Accessibilité

### 6.1 Mode hors ligne complet (Progressive Enhancement)

**Description :** Permettre la saisie des notes et des présences même sans connexion
internet, avec synchronisation automatique au retour du réseau.

**Fonctionnement technique :**
- Service Worker intercepte les requêtes réseau
- Les formulaires de saisie fonctionnent en local (IndexedDB)
- Indicateur visuel "Mode hors ligne — X saisies en attente de synchronisation"
- Synchronisation automatique silencieuse dès la reconnexion
- Résolution des conflits si deux utilisateurs ont modifié la même donnée

**Contexte BF :** Les coupures d'électricité et de réseau sont fréquentes. Cette
fonctionnalité est critique pour la fiabilité du système dans les zones péri-urbaines.

---

### 6.2 Intégration examens nationaux (BEPC / BAC)

**Description :** Import automatique des résultats officiels des examens nationaux
publiés par le Ministère de l'Éducation Nationale du Burkina Faso.

**Fonctionnement :**
- Import du fichier officiel MESRI (format CSV ou Excel fourni par le ministère)
- Rapprochement automatique par numéro de candidat avec les élèves de l'établissement
- Mise à jour du statut d'examen dans le dossier de chaque élève
- Tableau de bord du taux de réussite par classe, par matière et par enseignant
- Envoi automatique de SMS aux parents avec le résultat de leur enfant

---

### 6.3 QR Code dossier élève (accès contrôle instantané)

**Description :** Le QR code imprimé sur la carte scolaire ouvre un profil élève
simplifié, accessible sans connexion à un compte utilisateur.

**Données visibles en lecture seule :**
- Photo, nom, prénom, classe, année scolaire
- Statut de l'inscription (actif / suspendu)
- Statut financier simplifié (à jour / en retard)

**Sécurité :**
- Jeton JWT signé avec expiration annuelle (renouvelé à chaque rentrée)
- Aucune donnée sensible (notes, adresse, contacts) exposée
- Journal des scans consultable par le directeur

---

## Tableau de Priorités

| # | Fonctionnalité | Impact métier | Faisabilité | Priorité |
|---|---|---|---|---|
| 4.1 | Paiement Mobile Money | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 🔴 P1 |
| 2.1 | PWA Portail Parent | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🔴 P1 |
| 3.1 | Cahier de textes numérique | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🔴 P1 |
| 2.2 | Signature électronique bulletin | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🟠 P2 |
| 1.2 | Prédiction réussite examens | ⭐⭐⭐⭐ | ⭐⭐⭐ | 🟠 P2 |
| 3.2 | Bulletins de compétences | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🟠 P2 |
| 1.1 | Assistant IA conversationnel | ⭐⭐⭐⭐ | ⭐⭐⭐ | 🟠 P2 |
| 4.2 | Budget et dépenses | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 🟠 P2 |
| 3.3 | Gestion des manuels | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 🟡 P3 |
| 6.1 | Mode hors ligne complet | ⭐⭐⭐⭐⭐ | ⭐⭐ | 🟡 P3 |
| 5.1 | Module infirmerie / santé | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🟡 P3 |
| 6.2 | Import examens nationaux | ⭐⭐⭐⭐ | ⭐⭐⭐ | 🟡 P3 |
| 5.2 | Transport scolaire | ⭐⭐⭐ | ⭐⭐⭐ | 🟠 P2 |
| 2.3 | Communication bidirectionnelle | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🟡 P3 |
| 3.4 | Génération automatique EDT | ⭐⭐⭐ | ⭐⭐ | 🔵 P4 |
| 1.3 | Corrélations pédagogiques | ⭐⭐⭐ | ⭐⭐⭐ | 🔵 P4 |
| 4.3 | Dashboard financier réseau | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🔵 P4 |
| 5.3 | Gestion des stages | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🔵 P4 |
| 6.3 | QR Code dossier élève | ⭐⭐ | ⭐⭐⭐⭐⭐ | 🔵 P4 |

---

## Légende

| Symbole | Signification |
|---|---|
| 🔴 P1 | Priorité maximale — fort impact, faisable rapidement |
| 🟠 P2 | Haute priorité — impact élevé ou faisabilité bonne |
| 🟡 P3 | Priorité moyenne — valeur réelle mais effort significatif |
| 🔵 P4 | Long terme — innovation structurelle ou complexité élevée |
| ⭐⭐⭐⭐⭐ | Très élevé(e) |
| ⭐⭐⭐⭐ | Élevé(e) |
| ⭐⭐⭐ | Moyen(ne) |
| ⭐⭐ | Faible |

---

*Document rédigé le 03/05/2026 — YELEN SCHOOL Innovation Roadmap*
