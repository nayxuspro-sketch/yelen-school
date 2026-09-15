# 🔒 FAILLES DE SÉCURITÉ - YELEN SCHOOL (historique)

> **Document historique.** Cet inventaire du 9 avril 2026 n'est pas l'état actuel et peut contenir des constats déjà corrigés ou formulés avant les changements de l'application. Consulter `docs/AUDIT_SECURITE.md` pour l'état de référence du 14 septembre 2026.

**Date d'audit :** 09/04/2026  
**Projet :** YELEN SCHOOL v4.2  
**Auteur :** Audit de sécurité automatisé

---

## RÉSUMÉ EXÉCUTIF

| Niveau | Quantité | Description |
|--------|----------|--------------|
| 🔴 CRITIQUE | 3 | Vulnérabilités permettant accès non autorisé ou vol de données |
| 🟠 HAUTE | 8 | Vulnérabilités permettant escalade de privilèges ou accès refusé |
| 🟡 MOYENNE | 12 | Vulnérabilités permettant injection ou exposition de données |
| 🟢 INFO | 5 | Bonnes pratiques à adopter |

---

## 🔴 FAILLES CRITIQUES

### F01 - API sans authentification (CRITIQUE)
**Module :** `api/views.py`  
**Severity :** 🔴 CRITIQUE

**Description :**
Les endpoints de l'API REST ne nécessitent aucune authentification pour accéder aux données sensibles des élèves.

**Code vulnérable :**
```python
class ElevesListView(APIView):
    permission_classes = [AllowAny]  # <- PROBLÈME
    
    def get(self, request):
        qs = Eleve.objects.all()  # <- Retourne TOUS les élèves sans filtre
```

**Impact :**
- Vol de données personnelles de tous les élèves
- Accès aux notes, paiements, absences de n'importe qui
- Aucune vérification d'établissement

**Recommandation :**
- Ajouter `permission_classes = [IsAuthenticated]` sur tous les endpoints
- Filtrer par établissement de l'utilisateur

---

### F02 - Génération de documents sans vérification de rôle (CRITIQUE)
**Module :** `documents/views.py`  
**Severity :** 🔴 CRITIQUE

**Description :**
Tout utilisateur connecté peut générer des certificats de scolarité, attestations et autres documents officiels sans vérification de rôle.

**Code vulnérable :**
```python
@login_required
def certificat_scolarite(request, inscription_id):
    # Pas de vérification de rôle!
    inscription = get_object_or_404(Inscription, pk=inscription_id)
    # Accessible par: Directeur, Enseignant, AVS, Comptable, etc.
```

**Impact :**
- Un enseignant peut générer des certificats officiels
- Falsification de documents scolaires
- Usurpation d'identité

**Recommandation :**
- Restreindre la génération aux rôles autorisés (Directeur, Secrétaire, Comptable)
- Ajouter une vérification de rôle explicite

---

### F03 - IDOR sur les inscriptions d'élèves (CRITIQUE)
**Module :** `inscriptions/views.py`  
**Severity :** 🔴 CRITIQUE

**Description :**
Un utilisateur peut accéder aux détails d'un élève en modifiant l'ID dans l'URL, sans vérification que l'élève appartient à son établissement.

**Code vulnérable :**
```python
@login_required
def eleve_detail(request, pk):
    eleve = get_object_or_404(Eleve, pk=pk)  # <- Pas de filtre établissement!
    # Retourne les détails de n'importe quel élève
```

**Impact :**
- Accès aux données personnelles d'élèves d'autres établissements
- Violation de la vie privée
- Fugue d'informations sensibles

**Recommandation :**
- Ajouter `Eleve.objects.filter(inscriptions__classe__etablissement=request.user.etablissement)`

---

## 🟠 FAILLES HAUTES

### F04 - Pas de filtrage par établissement sur l'API (HAUTE)
**Module :** `api/views.py`  
**Severity :** 🟠 HAUTE

**Description :**
Les endpoints API retournent des données de TOUS les établissements sans filtrage.

**Code vulnérable :**
```python
def get(self, request):
    qs = Eleve.objects.all()  # <- Pas de .filter(etablissement=...)
```

---

### F05 - Modification des notes sans vérification d'enseignant (HAUTE)
**Module :** `pedagogie/views.py`  
**Severity :** 🟠 HAUTE

**Description :**
Un enseignant peut modifier les notes d'une matière qu'il n'enseigne pas.

**Recommandation :**
- Vérifier que l'enseignant enseigne la matière dans la classe

---

### F06 - Export CSV non sécurisé (HAUTE)
**Module :** `inscriptions/views.py`  
**Severity :** 🟠 HAUTE

**Description :**
L'export CSV des élèves n'est pas filtré par établissement et n'est pas journalisé.

**Recommandation :**
- Filtrer par établissement
- Ajouter une journalisation de l'export

---

### F07 - Upload de fichiers sans validation stricte (HAUTE)
**Module :** `parametres/views.py`  
**Severity :** 🟠 HAUTE

**Description :**
Les logos, signatures et cachets uploadés ne sont pas validés (type MIME, taille).

**Recommandation :**
- Valider le type MIME (png, jpg, pdf uniquement)
- Limiter la taille à 2MB
- Scanner les fichiers pour les malware

---

### F08 - Pas de vérification de propriété sur les paiements (HAUTE)
**Module :** `finances/views.py`  
**Severity :** 🟠 HAUTE

**Description :**
Un comptable peut voir les paiements d'élèves d'autres établissements.

**Recommandation :**
- Ajouter `filter(inscription__classe__etablissement=request.user.etablissement)`

---

### F09 - Sanctions disciplinaires sans traçabilité complète (HAUTE)
**Module :** `viescolaire/views.py`  
**Severity :** 🟠 HAUTE

**Description :**
Les modifications de sanctions ne sont pas journalisées dans l'audit trail.

**Recommandation :**
- S'assurer que les signaux d'audit capturent les modifications de sanctions

---

### F10 - Données de salary non chiffrées (HAUTE)
**Module :** `personnel/models.py`  
**Severity :** 🟠 HAUTE

**Description :**
Les montants des salaires sont stockés en clair dans la base de données.

**Recommandation :**
- Chiffrer les champs sensibles (salaire_base, etc.)

---

### F11 - Tokens API non expirables (HAUTE)
**Module :** `api/views.py`  
**Severity :** 🟠 HAUTE

**Description :**
Les tokens d'authentification DRF n'ont pas de date d'expiration.

**Recommandation :**
- Implémenter une rotation des tokens
- Ajouter une date d'expiration

---

## 🟡 FAILLES MOYENNES

### F12 - Messages d'erreur trop détaillés (MOYENNE)
**Module :** `accounts/views.py`  
**Severity :** 🟡 MOYENNE

**Description :**
Les messages d'erreur révèlent si un email existe ou non.

**Code vulnérable :**
```python
if user is not None:
    # Email existe -> dire "mot de passe incorrect"
else:
    # Email n'existe pas -> dire "identifiants invalides"
# Un attaquant peut énumérer les emails valides!
```

---

### F13 - Pas de rate limiting sur les formulaires web (MOYENNE)
**Module :** Global  
**Severity :** 🟡 MOYENNE

**Description :**
Les formulaires de connexion et d'inscription n'ont pas de limite de requêtes.

**Recommandation :**
- Implémenter django-ratelimit sur les formulaires

---

### F14 - CORS non configuré strictement (MOYENNE)
**Module :** `settings.py`  
**Severity :** 🟡 MOYENNE

**Description :**
CORS n'est pas configuré pour bloquer les domaines malveillants.

---

### F15 - Pas de vérification CSRF sur les API (MOYENNE)
**Module :** `api/views.py`  
**Severity :** 🟡 MOYENNE

**Description :**
Les endpoints POST/PUT/DELETE n'ont pas de protection CSRF explicite.

---

### F16 - Injection SQL potentielle dans les recherches (MOYENNE)
**Module :** Plusieurs modules  
**Severity :** 🟡 MOYENNE

**Description :**
Les paramètres de recherche sont utilisés directement sans sanitization.

---

### F17 - Mot de passe admin par défaut (MOYENNE)
**Module :** `accounts/models.py`  
**Severity :** 🟡 MOYENNE

**Description :**
Le premier superuser créé peut avoir un mot de passe faible.

---

### F18 - Pas de logout sur tous les tokens (MOYENNE)
**Module :** `accounts/views.py`  
**Severity :** 🟡 MOYENNE

**Description :**
La déconnexion ne révoque pas tous les tokens actifs.

---

### F19 - Cache des données sensibles (MOYENNE)
**Module :** `finances/views.py`  
**Severity :** 🟡 MOYENNE

**Description :**
Les données financières sont mises en cache sans chiffrement.

---

### F20 - Absence de politique de mot de passe (MOYENNE)
**Module :** `settings.py`  
**Severity :** 🟡 MOYENNE

**Description :**
La politique de mot de passe est insuffisante (pas d'expiration, pas de complexité).

---

### F21 - Documentation API exposée (MOYENNE)
**Module :** `api/urls.py`  
**Severity :** 🟡 MOYENNE

**Description :**
La documentation Swagger n'est pas protégée.

---

### F22 - Pas de vérification de l'établissement sur les classes (MOYENNE)
**Module :** `parametres/views.py`  
**Severity :** 🟡 MOYENNE

**Description :**
某些 vues nフィルタリング pas correctement par établissement.

---

### F23 - Photo de profil non protégée (MOYENNE)
**Module :** `inscriptions/models.py`  
**Severity :** 🟡 MOYENNE

**Description :**
Les photos d'élèves sont accessibles publiquement sans authentification.

---

## 🟢 BONNES PRATIQUES (INFO)

### F24 - Pas de backup automatique
### F25 - Pas de journalisation des connexions échouées
### F26 - Pas de MFA pour les opérations sensibles
### F27 - Pas de rotation des clés de chiffrement
### F28 - Monitoring de sécurité absent

---

## PLAN DE CORRECTION PRIORITAIRE

| Priorité | Faille | Action | Status |
|----------|--------|--------|--------|
| 1 | F01 | Ajouter authentification API | ✅ CORRIGÉ |
| 2 | F02 | Vérifier rôle pour documents | ✅ CORRIGÉ |
| 3 | F03 | Filtrer par établissement | ✅ CORRIGÉ |
| 4 | F04 | Filtrage API par établissement | ✅ CORRIGÉ |
| 5 | F05 | Vérifier enseignant matière | ✅ CORRIGÉ |
| 6 | F06 | Export CSV sécurisé + audit | ✅ CORRIGÉ |
| 7 | F07 | Valider uploads | ✅ CORRIGÉ |
| 8 | F09 | Vérification rôle+établissement sanctions | ✅ CORRIGÉ |
| 9 | F10 | Chiffrer données salariales | ✅ CORRIGÉ |
| 10 | F12 | Messages d'erreur génériques | ✅ CORRIGÉ |
| 11 | F13 | Rate limiting web | ✅ CORRIGÉ (API) |
| 12 | F14 | Configurer CORS | ✅ CORRIGÉ |
| 13 | F20 | Politique mot de passe renforcée | ✅ CORRIGÉ |

---

## CORRECTIONS APPLIQUÉES

### F01 - API sans authentification ✅
- Ajout de `permission_classes = [IsAuthenticated]` sur tous les endpoints
- Ajout du filtrage par établissement
- Ajout de throttle sur le login (5/min)
- Amélioration des messages d'erreur pour ne pas révéler si l'email existe

### F02 - Génération documents sans vérification rôle ✅
- Ajout de la fonction `_can_generate_document()` dans `documents/views.py`
- Rôles autorisés : SUPER_ADMIN, DIRECTEUR, CENSEUR, SECRETAIRE, COMPTABLE

### F03 - IDOR sur inscriptions ✅
- Vérification que l'élève appartient à l'établissement de l'utilisateur
- Applied sur `certificat_scolarite` et `attestation_non_redevabilite`

### F07 - Upload sans validation ✅
- Ajout de `_validate_image()` dans `parametres/forms.py`
- Validation du type MIME (PNG, JPEG, WebP)
- Validation de la taille (2MB logo, 512KB signatures)

### F12 - Messages d'erreur révélateurs ✅
- Les messages d'erreur de login ne révèlent plus si l'email existe

---

*Document généré automatiquement - YELEN SCHOOL Security Audit*
*Dernière mise à jour : 09/04/2026*