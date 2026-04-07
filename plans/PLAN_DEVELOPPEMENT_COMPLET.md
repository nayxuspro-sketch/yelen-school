# Plan de Développement Complet - YELEN SCHOOL v3.4

*Date: 11 Mars 2026*
*Deadline: 1er Août 2026*

---

## 📊 État Actuel du Projet

### Modules Implémentés ✅

| Module | État | Description |
|--------|------|-------------|
| **core** | ✅ Terminé | BaseModel, CycleChoices, RoleChoices |
| **accounts** | ✅ Terminé | User avec RBAC (9 rôles), authentification |
| **etablissements** | ✅ Terminé | Etablissement, Cycle, Classe |
| **parametres** | ✅ Terminé | 14 modèles + Signataires v3.4 |
| **licences** | ✅ Terminé | Système de licences, feature flags, middleware |

### Modules Partiellement Implémentés ⚠️

| Module | État | Description |
|--------|------|-------------|
| **personnel** | ⚠️ Partiel | MembrePersonnel basique (nom, prenom, fonction) |

### Modules Non Implémentés ❌

| Module | État | Priorité |
|--------|------|----------|
| **inscriptions** | ❌ À développer | HAUTE |
| **pedagogie** | ❌ À développer | HAUTE |
| **bulletins** | ❌ À développer | HAUTE |
| **documents** | ❌ À développer | HAUTE |
| **examens** | ❌ À développer | MOYENNE |
| **presences** | ❌ À développer | MOYENNE |
| **vacations** | ❌ À développer | MOYENNE |
| **finances** | ❌ À développer | MOYENNE |

---

## 🎯 Prochaines Étapes Prioritaires

### Phase 1: Foundation (Semaines 1-2)

#### 1.1 Enrichir le modèle Personnel
```
_PRIORITÉ HAUTE_

personnel/models.py doit inclure:
- MembrePersonnel (enrichi)
  - date_naissance
  - lieu_naissance
  - genre (M/F)
  - telephone
  - email
  - adresse
  - numero_cni
  - date_embauche
  - situation_matrimoniale
  - nombre_enfants
  - photo
  - etablissement (FK)
  - poste (FK vers parametres.Poste)
  - cycles (M2M vers Cycle)
  - est_directeur (BooleanField)
  - matricule (PERS-{ETAB}-{ANNEE}-{SEQ:04d})

- InscriptionPersonnel (nouveau)
  - personnel (FK)
  - annee_scolaire (FK)
  - poste (FK)
  - cycle (FK)
  - actif (BooleanField)
  - date_inscription
```

#### 1.2 Créer les modèles Inscriptions
```
_PRIORITÉ HAUTE_

inscriptions/models.py:
- Inscription
  - eleve (FK)
  - annee_scolaire (FK)
  - classe (FK)
  - date_inscription
  - statut (Affecté/Non affecté/Boursier/Exonéré)
  - numero_recu
  - montant_paye
  - parent_tuteur (FK)
  -_redoublant (BooleanField)
  - observations

- Eleve (nouveau - pourrait être dans accounts)
  - matricule (BF-{REGION}-{ANNEE}-{SEQ:04d})
  - nom
  - prenom
  - date_naissance
  - lieu_naissance
  - genre
  - nationalite
  - pays_residence
  - province
  - commune
  - village
  - telephone_urgence
  - email
  - photo
  - nom_pere
  - nom_mere
  - telephone_parent
  - profession_pere
  - profession_mere
  - tuteur_nom
  - tuteur_telephone
  - tuteur_adresse
  - etablissement_origine
  - last_classe (FK vers Classe)
  - last_annee (FK vers AnneeScolaire)

- InscriptionPersonnel (dans personnel)
```

---

### Phase 2: Modules Métier (Semaines 3-6)

#### 2.1 Pedagogie
```
inscriptions/models.py ou pedagogie/models.py:
- Enseignement
- Evaluation
- Note
- Composition
- Resultat
```

#### 2.2 Bulletins
```
bulletins/models.py:
- Bulletin
- Appreciation
- Moyenne
- Rang
- Hole
```

#### 2.3 Examens
```
examens/models.py:
- Examen (CEP/BEPC/BAC)
- InscriptionExamen
- Surveillance
- SalleExamen
```

---

### Phase 3: Modules Complémentaires (Semaines 7-10)

#### 3.1 Presences
```
presences/models.py:
- Presence
- Absence
- Retard
- Appel
-justification
```

#### 3.2 Vacations
```
vacations/models.py:
- Vacation
- HeureSupplementaire
- BulletinVacation
```

#### 3.3 Finances
```
finances/models.py:
- Paiement
- Recu
- Facture
- Rubrique
- Tarif
```

---

### Phase 4: Documents & Integration (Semaines 11-14)

#### 4.1 Module Documents
```
documents/models.py:
- Document
- TypeDocument (peut utiliser parametres.TypeDocument)
- ModeleDocument
- GenerationDocument

- Signatures (intégration avec parametres.SignataireDocument)
```

#### 4.2 Intégration PDF
```
Integration des signataires dans les documents:
- Certificat de scolarité
- Bulletin de notes
- Reçu de paiement
- Autorisation d'absence
- Attestation de non-redevabilité
- Cursus scolaire
- Carte d'identité scolaire
- Listes (classe, personnel)
```

---

## 📋 Checklist des Tâches par Module

### Module Personnel (Enrichissement)
- [ ] Ajouter les champs manquants à MembrePersonnel
- [ ] Créer le modèle InscriptionPersonnel
- [ ] Implémenter la gestion des cycles par personnel
- [ ] Ajouter la vue d'inscription annuelle du personnel
- [ ] Créer les templates CRUD personnel
- [ ] Ajouter les tests unitaires

### Module Inscriptions
- [ ] Créer le modèle Eleve avec toutes les infos
- [ ] Créer le modèle Inscription
- [ ] Implémenter la logique de matricule (BF-{REGION}-{ANNEE}-{SEQ})
- [ ] Créer le workflow inscription/réinscription
- [ ] Ajouter la logique d'âge calculé (non stocké)
- [ ] Créer les templates inscription
- [ ] Ajouter les tests unitaires

### Module Pedagogie
- [ ] Créer les modèles enseignements/evaluations
- [ ] Implémenter la gestion des notes
- [ ] Créer les calculs de moyennes
- [ ] Ajouter les templates saisies notes

### Module Bulletins
- [ ] Créer les modèles bulletins
- [ ] Implémenter la génération de bulletins PDF
- [ ] Intégrer les signataires dans les bulletins
- [ ] Ajouter les appreciation conduite

### Module Examens
- [ ] Créer les modèles examens
- [ ] Gérer les inscriptions aux examens (CEP/BEPC/BAC)
- [ ] Créer les templates gestion exams

### Module Documents
- [ ] Créer le système de génération PDF
- [ ] Intégrer les signataires paramétrables
- [ ] Créer les templates pour chaque type de document

### Module Presences
- [ ] Créer le modèle présence/absence
- [ ] Implémenter les pointages
- [ ] Créer les rapports de présence

### Module Vacations
- [ ] Créer le modèle vacation
- [ ] Implémenter le calcul des heures
- [ ] Créer les bulletins mensuels

### Module Finances
- [ ] Créer le modèle paiement
- [ ] Implémenter la gestion des reçus
- [ ] Créer les rapports financiers

---

## 🎨 Design System

Le projet utilise:
- **Backend**: Django 4.2 + DRF
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Base de données**: PostgreSQL 15
- **Cache**: Redis 7
- **PDF**: WeasyPrint
- **Conteneurisation**: Docker

### Palette de Couleurs
- Fond global: `#0A1628`
- Surface cartes: `#111E35`
- Vert principal: `#00A86B`
- Or: `#F5A623`

### Design Mobile-First
- Version responsive obligatoire
- Navigation mobile optimisée

---

## 🚀 Stratégie de Développement Recommandée

1. **Commencer par personnel et inscriptions** - Ce sont les fondations
2. **Implémenter pedagogie et bulletins** - Cœur métier de l'école
3. **Ajouter examens** - Important pour le calendrier scolaire
4. **Développer presences, vacations, finances** - Modules complémentaires
5. **Finaliser documents avec signataires** - Point d'aboutissement v3.4

---

*Ce plan sera mis à jour au fur et à mesure de l'avancement du projet.*
