# 🌟 Propositions d'Innovations Technologiques — YELEN SCHOOL

Ce document présente une analyse de l'état actuel de **YELEN SCHOOL** et propose une série de fonctionnalités hautement innovantes, spécifiquement adaptées au contexte socio-économique et infrastructurel des établissements scolaires privés au **Burkina Faso**.

---

## 🔍 1. État des Lieux et Diagnostic de l'Existant

Après exploration du codebase de YELEN SCHOOL, voici les modules clés déjà en place ou initiés :
- **Prédictions IA de réussite aux examens (`pedagogie/predictions.py`)** : Algorithme heuristique pondérant la moyenne générale trimestrielle (70 %), la tendance inter-trimestrielle (±10 pts) et un malus d'assiduité.
- **Scoring de risque de décrochage (`pedagogie/utils_ia.py`)** : Système basé sur 5 signaux (absences non justifiées, tendance des moyennes, notes critiques < 8/20, sanctions disciplinaires, retards de paiement de scolarité).
- **Communication Bidirectionnelle (`communication/models.py`)** : Gestion de messages parents (convocations, avertissements, demandes de justificatifs d'absence, relances) avec un jeton sécurisé (`UUID`) permettant aux parents de répondre en ligne via formulaires légers.
- **Paiements Mobile Money (`finances/`)** : Intégrations Orange Money / Moov Money pour le règlement des frais de scolarité en **FCFA**.
- **Cahier de Textes Numérique (`pedagogie/`)** : Saisie HTMX des cours et devoirs avec impression de rapports optimisés.
- **Signataires configurables (`parametres/`)** : Attribution de signataires officiels par cycle et type de document.

---

## 💡 2. Propositions de Fonctionnalités Innovantes (v5.0)

Voici 6 propositions majeures conçues pour maximiser la résilience, l'accessibilité et la valeur ajoutée pédagogique du système au Burkina Faso.

### 2.1 Système d'Interrogation Interactive par SMS Hors-Ligne (Parent-SMS Direct)
> **Problématique** : L'accès à Internet mobile reste coûteux ou instable dans les zones péri-urbaines et rurales, et de nombreux parents possèdent des téléphones basiques (dumbphones).

*   **Concept** : Permettre aux parents d'interroger le serveur YELEN SCHOOL de l'école directement par SMS sans connexion internet.
*   **Fonctionnement** :
    1. Le parent envoie un code SMS structuré à un numéro court ou à la passerelle locale (ex : `NOTE 01-2026-00123 T1`).
    2. La passerelle Android locale (SMS Gateway) ou le modem USB reçoit le message et transmet la requête à l'instance locale Django.
    3. Le système vérifie le numéro de téléphone émetteur (pour s'assurer qu'il correspond à un parent enregistré) et extrait les données.
    4. YELEN SCHOOL génère et renvoie un SMS automatique récapitulant les moyennes de l'élève ou son solde financier actuel (ex : `SOLDE 01-2026-00123`).
*   **Innovation** : 100 % accessible hors-ligne pour la famille, coût minime, immédiateté de l'information.

---

### 2.2 Marché de Remplacement & Gestion Proactive des Vacataires (Yelen-Vacations Express)
> **Problématique** : La gestion des enseignants vacataires et le suivi de leurs heures de cours est un casse-tête pour les censeurs et directeurs d'études dans le privé. Une absence non remplacée pénalise le volume horaire du cycle.

*   **Concept** : Un outil d'affectation automatique et de bourse aux remplacements pour les cours vacants.
*   **Fonctionnement** :
    1. Lorsqu'un enseignant signale une absence ou un congé via `personnel`, le système calcule les heures de cours perdues.
    2. Le système cherche dans le vivier d'enseignants du réseau multi-établissements (ou de la base de données interne) les professeurs de la même discipline disponibles sur ces créneaux.
    3. Une notification SMS/In-App leur est envoyée : *"Cours de Mathématiques 3ème A libre ce jeudi 08h-10h. Rémunération : X FCFA. Accepter ?"*.
    4. Le premier enseignant qui accepte est automatiquement affecté sur l'emploi du temps temporaire, et la vacation est calculée à la fin du mois dans le module `vacations` (calcul auto des tarifs en FCFA).

---

### 2.3 Aide à l'Orientation Scolaire & Post-Bac par IA (Orientation Burkina)
> **Problématique** : Le manque de conseillers d'orientation au Burkina Faso laisse beaucoup d'élèves indécis ou mal orientés après le BEPC et le BAC.

*   **Concept** : Générer une recommandation d'orientation personnalisée en fonction du profil académique, des forces détectées et des filières locales.
*   **Fonctionnement** :
    1. En analysant l'historique complet des notes sur 20, le profil de compétences, les points forts et la tendance sur les 3 cycles précédents.
    2. Le moteur d'IA locale croise ces données avec un référentiel d'orientation burkinabè (filières universitaires classiques comme l'Université de Ouagadougou, filières professionnelles en forte demande : agronomie, mines, génie civil, énergies renouvelables, informatique).
    3. Le système produit une **Fiche Conseil d'Orientation** (format A4 WeasyPrint, signée par le proviseur) suggérant 3 filières d'avenir adaptées aux capacités de l'élève.

---

### 2.4 Monitoring et Résilience Énergétique (Yelen-Solar Guard)
> **Problématique** : Les coupures d'électricité (délestages) sont fréquentes au Burkina Faso. De nombreuses écoles fonctionnent sur panneaux solaires et batteries. Un arrêt soudain du serveur peut corrompre la base de données PostgreSQL.

*   **Concept** : Rendre YELEN SCHOOL "conscient" de son état énergétique pour adapter sa consommation et sécuriser les données.
*   **Fonctionnement** :
    1. Connexion (via API locale ou ping réseau) à l'onduleur ou au système de gestion de la batterie de l'école.
    2. Si le niveau de batterie descend sous les 20 % (ou en cas de passage prolongé sur batterie solaire) :
        - Le système bascule automatiquement en **Mode Éco-Énergétique** (mise en veille des tâches de fond lourdes, suspension temporaire de WeasyPrint pour les exports massifs, compression renforcée des requêtes).
        - Une alerte visuelle prévient les utilisateurs : *"Serveur sur batterie. Saisie autorisée, génération de PDF désactivée pour préserver l'autonomie"*.
        - Lancement d'une sauvegarde PostgreSQL sécurisée automatique avant coupure totale.

---

### 2.5 Carnet Épidémiologique d'Infirmerie (Yelen-Health Tracker)
> **Problématique** : L'infirmerie scolaire accumule des fiches de passage papier sans exploitation statistique, alors que les écoles sont des foyers de propagation de maladies saisonnières (paludisme, dengue, méningite).

*   **Concept** : Transformer le journal d'infirmerie en outil de prévention épidémiologique locale.
*   **Fonctionnement** :
    1. Lors d'un passage à l'infirmerie, l'agent renseigne les symptômes via un formulaire HTMX rapide (sélection tactile des symptômes fréquents : fièvre, courbatures, toux).
    2. Un algorithme anonymisé calcule le taux d'incidence par classe ou par dortoir.
    3. Si le nombre de cas suspects de dengue ou de paludisme dépasse un seuil d'alerte dans une classe sur une période de 7 jours, le système envoie une alerte automatique au Directeur : *"Alerte sanitaire : 4 cas suspects de Dengue en 5ème B. Action suggérée : pulvérisation d'insecticide et sensibilisation des parents"*.

---

### 2.6 Bulletin de Compétences Sahélien (Approche Par Compétences)
> **Problématique** : Bien que le système traditionnel burkinabè évalue sur 20, l'Approche Par Compétences (APC) est obligatoire pour les cycles Préscolaire et Primaire.

*   **Concept** : Intégration d'un carnet d'évaluation des compétences pratiques adaptées au milieu local.
*   **Fonctionnement** :
    1. Configuration d'un référentiel de compétences (Savoirs académiques + Compétences pratiques de vie : hygiène collective, sensibilisation à la désertification, projets potagers scolaires, respect du patrimoine).
    2. L'enseignant évalue par feux tricolores (Acquis, En cours, Non acquis) via une interface HTMX mobile-friendly.
    3. Le bulletin PDF généré affiche un tableau visuel de ces compétences et un graphique d'acquisition sous forme de radar stylisé en CSS natif.

---

## 📊 3. Matrice de Priorisation et Impact

| Innovation | Impact Métier | Complexité Technique | Score Priorité | Recommandation |
| :--- | :---: | :---: | :---: | :---: |
| **2.1 Parent-SMS Direct** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | **🔴 P1** | **Prioritaire** (Zéro internet requis) |
| **2.5 Yelen-Health Tracker** | ⭐⭐⭐⭐ | ⭐⭐ | **🔴 P1** | **Quick Win** (Impact santé publique) |
| **2.6 Carnet APC Sahélien** | ⭐⭐⭐⭐ | ⭐⭐⭐ | **🟠 P2** | **Haute valeur** pour le Primaire |
| **2.2 Yelen-Vacations Express**| ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **🟠 P2** | Fort intérêt pour les grands lycées |
| **2.3 Orientation Post-Bac** | ⭐⭐⭐ | ⭐⭐⭐ | **🟡 P3** | Idéal pour valoriser les élèves |
| **2.4 Yelen-Solar Guard** | ⭐⭐⭐ | ⭐⭐⭐⭐ | **🟡 P3** | Résilience technique et matérielle |

---

## 🛠 4. Directives d'Intégration Stack Technique

Toutes ces innovations respectent rigoureusement les contraintes techniques imposées dans le projet :
1.  **Champs & Modèles** : Extension systématique de `BaseModel` (UUID, traçabilité `created_by`, `updated_by`).
2.  **Interface HTMX** : Aucun framework JS (pas de React/Vue), utilisation exclusive de requêtes HTMX pour une réactivité optimale et légère.
3.  **Monnaie & Notation** : Tarifs de vacation exclusivement en **FCFA**, notes du carnet d'orientation ou d'APC toujours sur **20** ou par feux tricolores discrets.
4.  **Aesthetics & Palette** : Respect strict du thème sombre :
    - Fond de page : `#0A1628`
    - Surfaces & Cartes : `#111E35`
    - Accent principal : `#00A86B`
    - Typographie : `Outfit` pour l'interface courante.
