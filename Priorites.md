# Fonctionnalités à développer — Priorités

> Dernière mise à jour : 2026-09-17 — toutes les fonctionnalités listées sont livrées.

---

## Effort faible (Quick wins)

### ~~2. Portail parent — Accès via le menu~~
- ~~La vue `portail_parent` et le rôle `PARENT` existent déjà~~
- ~~La vue `parent_create` (accounts) existe mais n'est pas liée dans la navigation~~
- ~~**À faire :** ajouter un lien dans la sidebar et documenter la création de compte parent~~
- ✅ **Terminé** — lien sidebar PARENT + section "Comptes Parents" pour SUPER_ADMIN/DIRECTEUR/SECRETAIRE

### ~~4. CoSignataires — Interface de gestion UI~~
- ~~Le modèle `CoSignataire` et la logique PDF via `signataire_tags.py` sont fonctionnels~~
- ~~Accessible uniquement via l'admin Django~~
- ~~**À faire :** créer une vue HTMX modale dans `parametres` pour gérer les co-signataires par document~~
- ✅ **Terminé** — CRUD HTMX intégré dans la page Signataires (bouton "Co-sign." par document)

### ~~5. LocalisationPoste — Interface de gestion~~
- ~~Le modèle `LocalisationPoste` existe, enregistré uniquement dans `admin.py`~~
- ~~**À faire :** ajouter CRUD dans le module `personnel` ou `parametres`~~
- ✅ **Terminé** — page dédiée dans Paramètres avec CRUD HTMX + carte sur la page index

### ~~7. IA décrochage — Déclenchement automatique~~
- ~~`calculer_risques` (management command) et `utils_ia.py` sont complets~~
- ~~Le déclenchement est uniquement manuel via `python manage.py calculer_risques`~~
- ~~**À faire :** configurer un cron (ex. `0 2 * * *`) + ajouter une alerte visible dans le tableau de bord quand des élèves sont en zone rouge~~
- ✅ **Terminé** — widget dashboard avec compteurs Critique/Élevé/Modéré, liste des élèves à risque et bouton "Analyser / Recalculer" (vue `core:risque_recalculer`)

---

## Effort moyen

### ~~3. Tableau de bord global des échéanciers + alertes~~
- ~~Création/modification/suppression d'échéanciers : ✅ fonctionnel~~
- ~~**À faire :**~~
  - ~~Vue globale listant toutes les tranches (en retard / à venir / payées) pour tous les élèves~~
  - ~~Alertes automatiques à l'approche des dates d'échéance (notification ou SMS)~~
  - ~~PDF du plan d'échéancier individuel (impression pour les parents)~~
- ✅ **Terminé** — vue `/finances/echeanciers/` avec filtres, compteurs, alertes retard/alerte et export Excel

### ~~6. Export Excel (`.xlsx`)~~
- ~~Seul l'export CSV existe (élèves, paiements)~~
- ~~`openpyxl` non installé~~
- ~~**À faire :** ajouter `openpyxl` aux dépendances + créer des vues d'export Excel pour finances, élèves et présences~~
- ✅ **Terminé** — `openpyxl` installé, `core/excel.py` (helper `ExcelExport` avec mise en forme YELEN), exports Excel ajoutés sur élèves, personnel et bilan encaissements

### ~~8. Génération de bulletins en masse (batch)~~
- ~~Génération par élève : ✅ fonctionnelle~~
- ~~**À faire :** vue de génération groupée (toute une classe ou tout l'établissement) avec téléchargement ZIP ou PDF multi-pages~~
- ✅ **Terminé** — `bulletin_classe_zip` (ZIP d'PDFs individuels par classe) + `bulletins_etab_zip` (ZIP de tous les batch-PDFs par trimestre) ; boutons ajoutés dans la page bulletins_classe et l'index bulletins

---

## Effort élevé

### ~~1. Transfert inter-établissements~~
- ~~Aucune base de données, aucune vue, aucun template~~
- ~~**À faire :**~~
  - ~~Modèle `TransfertEleve` (établissement origine, destination, date, statut)~~
  - ~~Génération du dossier de transfert (relevé, historique, situation financière)~~
  - ~~Marquer l'élève comme « transféré » dans l'établissement d'origine~~
  - ~~Intégration de l'élève dans l'établissement d'accueil avec matricule d'origine (Licence Réseau)~~
- ✅ **Terminé** — modèle `TransfertEleve` + migration, workflow EN_ATTENTE→APPROUVE/REFUSE, création `EvenementParcours(TRANSFERT_SORTANT)`, dossier PDF (cursus + situation financière), lien sidebar + bouton fiche élève

### ~~10. SMS automatiques planifiés~~
- ~~Infrastructure SMS (modem/HTTP) et envoi manuel : ✅ fonctionnels~~
- ~~**À faire :**~~
  - ~~Cron pour alertes absences (ex. J+1 si absent non justifié)~~
  - ~~Cron pour rappels d'échéanciers (ex. 3 jours avant la date limite)~~
  - ~~Cron pour diffusion des résultats (moyennes disponibles)~~
  - ~~Interface de configuration des déclencheurs automatiques dans `parametres`~~
- ✅ **Terminé** — modèle `DeclencheurSMS`, commande `sms_auto` (3 types : ABSENCE_J1, ECHEANCIER, RESULTATS), interface HTMX dans Paramètres avec toggle actif/inactif, édition jours_avant et exécution manuelle

---

## Effort très élevé

### ~~9. Multi-établissements / Réseau~~
- ~~Feature flag `multi_etablissements` et licence `RESEAU` existent dans `licences/models.py`~~
- ~~**À faire :**~~
  - ~~Dashboard consolidé (statistiques agrégées sur tous les établissements du réseau)~~
  - ~~Rapports croisés inter-établissements~~
  - ~~Gestion centralisée des cycles, classes et tarifs pour un réseau~~
  - ~~Transfert d'élèves entre établissements du même réseau (lié à #1)~~
  - ~~Rôle `DIRECTEUR_RESEAU` ou équivalent~~
- ✅ **Terminé** — modèle `GroupeEtablissements`, rôle `DIRECTEUR_RESEAU`, FK `Etablissement.groupe` + `User.groupe`, dashboard consolidé (nb élèves + encaissé par établissement), CRUD groupes + affectation, lien sidebar dédié

---

## Récapitulatif

| # | Fonctionnalité | Effort | Statut |
|---|----------------|--------|--------|
| 2 | Portail parent — accès via menu | Faible | ✅ Terminé |
| 4 | CoSignataires — UI | Faible | ✅ Terminé |
| 5 | LocalisationPoste — UI | Faible | ✅ Terminé |
| 7 | IA décrochage — déclenchement auto | Faible | ✅ Terminé |
| 3 | Tableau global échéanciers + alertes | Moyen | ✅ Terminé |
| 6 | Export Excel | Moyen | ✅ Terminé |
| 8 | Bulletins en masse (batch) | Moyen | ✅ Terminé |
| 1 | Transfert inter-établissements | Élevé | ✅ Terminé |
| 10 | SMS automatiques (cron) | Élevé | ✅ Terminé |
| 9 | Multi-établissements / Réseau | Très élevé | ✅ Terminé |
