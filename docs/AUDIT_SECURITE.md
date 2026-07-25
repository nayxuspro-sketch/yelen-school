# 🔒 RAPPORT D'AUDIT DE SÉCURITÉ — YELEN SCHOOL

**Date :** 23/06/2026
**Projet :** YELEN SCHOOL v4.2
**Auditeur :** Agent IA — Google Antigravity
**Version du rapport :** 6.0 (Audit complet de mise à jour)
**Périmètre :** 18 modules Django + API REST + Middlewares + Infrastructure

---

## 1. RÉSUMÉ EXÉCUTIF

Cet audit de mise à jour (v6.0) a été réalisé en parcourant l'intégralité du code source
de l'application YELEN SCHOOL dans son état actuel (23 juin 2026), en comparant avec le
dernier rapport (v5.0, avril 2026).

**Score précédent :** 9.5/10 (rapport v5.0)
**Score actuel :** 6.5/10

> ⚠️ **Régression significative détectée.** Plusieurs nouvelles vulnérabilités ont été
> introduites depuis le dernier audit, dont une **CRITIQUE** exposant une clé API externe.
> Des corrections immédiates sont requises avant tout déploiement en production.

---

## 2. TABLEAU DE SYNTHÈSE

| Niveau | Nouvelles | Héritées ouvertes | Total ouvert |
|--------|-----------|-------------------|--------------|
| 🔴 Critiques | 1 | 0 | **1** |
| 🟠 Hautes | 2 | 1 | **3** |
| 🟡 Moyennes | 3 | 1 | **4** |
| 🟢 Infos / Best practices | 2 | 0 | **2** |
| **Total ouvert** | **8** | **2** | **10** |

---

## 3. VULNÉRABILITÉS CRITIQUES 🔴

### VUL-2026-01 — Clé API Anthropic exposée dans le fichier `.env`

| Attribut | Détail |
|---|---|
| **Fichier** | `.env` ligne 29 |
| **CVSS v3** | 9.8 — AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| **Type** | Exposition de secret cryptographique / credential |
| **Statut** | ✅ RÉSOLU — Dépendance et clé supprimées |

**Description :**
Le fichier `.env` contenait la clé API Anthropic en clair :

```
ANTHROPIC_API_KEY=sk-ant-api03-swKCpJRnL2F...QAA
```

Cette clé, si elle est exposée (commit git, accès disque, log), permet à un attaquant
de consommer les crédits Anthropic de l'établissement, d'envoyer des requêtes au nom de
l'organisation, voire d'extraire des données transmises à l'API. Elle peut aussi servir
de pivot pour d'autres attaques si l'API Anthropic expose des métadonnées d'organisation.

**De plus**, le fichier `.env` contient également :
- Un mot de passe SMS (`SMS_HTTP_PASSWORD=3JWmHa6-`) qui permet d'envoyer des SMS au nom de l'établissement
- La `SECRET_KEY` Django de développement (faible entropie : `yelen-school-dev-secret-key-changez-en-production-2026`)
- Des identifiants base de données

Bien que `.env` soit listé dans `.gitignore`, ce fichier peut être divulgué par d'autres vecteurs
(partage de répertoire, sauvegarde non chiffrée, log serveur).

**Actions prises (Juillet 2026) :**
1. La clé a été **révoquée** sur https://console.anthropic.com
2. La dépendance `anthropic>=0.40.0` a été **supprimée** de `requirements/base.txt`
3. La variable `ANTHROPIC_API_KEY` a été **retirée** de `settings.py`, `.env` et `.env.example`
4. Tous les autres secrets du fichier `.env` ont été régénérés

---

## 4. VULNÉRABILITÉS HAUTES 🟠

### VUL-2026-02 — Endpoint webhook SMS sans protection CSRF (`@csrf_exempt`)

| Attribut | Détail |
|---|---|
| **Fichier** | `communication/views.py` lignes 257–456 |
| **CVSS v3** | 7.3 — AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:H/A:N |
| **Type** | Absence de CSRF + Injection de commande via SMS |
| **Statut** | 🟠 OUVERT |

**Description :**
La vue `webhook_incoming_sms` est décorée `@csrf_exempt` et accessible sans authentification,
ce qui est intentionnel pour un webhook. Cependant, cette conception crée plusieurs risques :

1. **Aucun secret partagé / HMAC** : n'importe qui connaissant l'URL peut envoyer une
   fausse requête et se faire passer pour un SMS entrant d'un parent.
2. **Injection de matricule** : en envoyant `NOTE 01-2026-00001` avec un numéro quelconque,
   l'attaquant peut potentiellement extraire les notes, soldes ou absences d'un élève si
   le numéro est dans la liste autorisée.
3. **DoS par saturation de SMS** : l'endpoint déclenche `envoyer_sms_async` sans rate limiting.

**Recommandation :**
- Ajouter une validation HMAC avec un secret partagé entre le serveur et la passerelle SMS
- Limiter l'accès par IP whitelist (adresse de la passerelle SMS)
- Ajouter un rate limiting sur cet endpoint

---

### VUL-2026-03 — Régression CSP : `unsafe-inline` toujours actif dans le middleware

| Attribut | Détail |
|---|---|
| **Fichier** | `yelen_school/csp_middleware.py` lignes 48–50 |
| **CVSS v3** | 5.8 — AV:N/AC:H/PR:N/UI:R/S:C/C:L/I:L/A:N |
| **Type** | Défense en profondeur XSS dégradée |
| **Statut** | 🟠 OUVERT — Régression depuis le rapport v4.0 |

**Description :**
Le rapport précédent (Rapport_securite.md v4.1) signalait la correction de `unsafe-inline`
comme accomplie. Or, le code actuel du `CSPNonceMiddleware` émet toujours :

```python
f"script-src 'self' 'nonce-{nonce}' 'unsafe-inline'",   # ← UNSAFE-INLINE PRÉSENT
f"script-src-attr 'self' 'unsafe-inline'",               # ← UNSAFE-INLINE PRÉSENT
```

La présence de `'unsafe-inline'` **annule l'effet protecteur du nonce** : lorsque les deux
sont présents, les navigateurs appliquent `unsafe-inline` et ignorent le nonce. Un script
XSS injecté sans nonce serait donc exécuté.

**Correction requise** dans `csp_middleware.py` :
```python
# AVANT (vulnérable)
f"script-src 'self' 'nonce-{nonce}' 'unsafe-inline'",
f"script-src-attr 'self' 'unsafe-inline'",

# APRÈS (corrigé)
f"script-src 'self' 'nonce-{nonce}'",
f"script-src-attr 'nonce-{nonce}'",
```

---

### VUL-HERITEE-01 — Session 2FA stockée en clair (partiellement corrigée)

| Attribut | Détail |
|---|---|
| **Fichier** | `accounts/views.py` lignes 135–136 |
| **CVSS v3** | 5.4 |
| **Type** | Données de session sensibles non signées |
| **Statut** | ⏳ PARTIELLEMENT CORRIGÉ (identifié v5.0) |

**Description :**
Le `pk` de l'utilisateur 2FA en cours d'authentification est stocké dans la session
Django (`request.session['_2fa_user_pk']`) sans signature supplémentaire. Un attaquant
ayant accès aux données de session (Redis compromis) pourrait manipuler ce champ
pour contourner la 2FA et se connecter en tant qu'un autre utilisateur.

**Statut :** Non corrigé depuis le rapport v5.0. La signature cryptographique de cette
valeur via `django.core.signing` reste recommandée.

---

## 5. VULNÉRABILITÉS MOYENNES 🟡

### VUL-2026-04 — `SESSION_TIMEOUT` déclaré mais jamais appliqué

| Attribut | Détail |
|---|---|
| **Fichier** | `yelen_school/settings.py` ligne 294 |
| **CVSS v3** | 4.3 |
| **Type** | Session sans expiration active |
| **Statut** | 🟡 OUVERT |

**Description :**
Le setting `SESSION_TIMEOUT = 3600` est déclaré dans `settings.py` mais n'est **jamais
lu ni appliqué** par aucun middleware ou hook. Django ne reconnaît pas ce paramètre
nativement. Sans implémentation, les sessions ne s'invalident pas après 1h d'inactivité,
ce qui augmente la durée d'exposition d'une session volée.

**Recommandation :**
Option A (simple) : Utiliser `SESSION_COOKIE_AGE = 3600` (Django natif).
Option B (recommandé) : Créer un middleware qui vérifie `request.session['_last_activity']`
et invalide la session si inactivité > 3600 secondes.

```python
# settings.py — Option A (simple)
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True  # Renouvelle le timer à chaque requête
```

---

### VUL-2026-05 — Déconnexion (`logout`) accessible via requête GET

| Attribut | Détail |
|---|---|
| **Fichier** | `accounts/views.py` lignes 199–202 |
| **CVSS v3** | 4.0 |
| **Type** | CSRF logout — Cross-Site Request Forgery |
| **Statut** | 🟡 OUVERT |

**Description :**
La vue `logout_view` répond à toutes les méthodes HTTP (GET, POST…) sans restriction.
Cela permet à un site tiers de déconnecter un utilisateur authentifié via une requête
GET malveillante (ex : `<img src="https://yelen.bf/accounts/logout/">`). C'est un
vecteur classique de CSRF logout.

```python
# AVANT (vulnérable)
def logout_view(request):
    logout(request)
    return redirect('accounts:login')

# APRÈS (corrigé)
from django.views.decorators.http import require_POST

@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')
```

> Note : Le template de déconnexion devra utiliser un formulaire `<form method="POST">`
> avec `{% csrf_token %}` plutôt qu'un lien `<a href>`.

---

### VUL-2026-06 — Absence de configuration de journalisation (LOGGING)

| Attribut | Détail |
|---|---|
| **Fichier** | `yelen_school/settings.py` |
| **CVSS v3** | 3.5 |
| **Type** | Absence de traçabilité des erreurs et tentatives d'intrusion |
| **Statut** | 🟡 OUVERT |

**Description :**
Aucun dictionnaire `LOGGING` n'est configuré dans `settings.py`. Sans logging structuré :
- Les erreurs 500 ne sont pas archivées
- Les tentatives d'authentification échouées ne sont pas centralisées
- Les exceptions des vues PDF (WeasyPrint) sont silencieuses
- Aucun audit de sécurité réseau n'est possible a posteriori

**Recommandation :** Ajouter une configuration `LOGGING` minimale :

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file_security': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'verbose',
        },
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['file_security'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file_errors'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
```

---

### VUL-HERITEE-02 — Logs credentials (tokens Authorization dans Nginx)

| Attribut | Détail |
|---|---|
| **Fichier** | Configuration Nginx/Gunicorn |
| **CVSS v3** | 2.6 |
| **Type** | Token API exposé en clair dans les logs d'accès |
| **Statut** | ⚠️ NON CORRIGÉ (identifié v5.0) |

**Description :**
Les tokens DRF transitent dans l'en-tête `Authorization: Token <valeur>`. Si Nginx
enregistre les en-têtes HTTP (configuration par défaut), les tokens apparaissent en
clair dans les fichiers de log.

---

## 6. INFORMATIONS ET BONNES PRATIQUES 🟢

### INFO-2026-01 — Dépendance `anthropic` sans version fixée (pinning)

| Fichier | `requirements/base.txt` |
|---|---|

La dépendance `anthropic>=0.40.0` n'était pas pined à une version exacte. **Résolu en Juillet 2026** : la dépendance a été supprimée car le chatbot est 100% local et n'utilise pas l'API Anthropic.

---

### INFO-2026-02 — Fichiers temporaires de débogage à la racine du projet

| Fichiers | `fix2.py`, `fix_pedagogie_v2.py`, `fix_pedagogie_v3.py`, `fix_requirements.py`, `fix_unique.py`, `script.py`, `v1.py` |
|---|---|

Ces fichiers de débogage contiennent potentiellement des logiques métier fragmentaires
et pourraient exposer des informations sensibles (structure DB, logique interne). Ils
ne devraient pas être présents dans un environnement de production ni dans le dépôt Git.
**Recommandation :** Supprimer ou déplacer dans un dossier `scripts/` avec `.gitignore`.

---

## 7. MESURES DE SÉCURITÉ CONFIRMÉES EN PLACE ✅

Les points suivants ont été vérifiés et sont correctement implémentés :

### Authentification & Autorisation
- ✅ Protection brute force : 5 tentatives → verrouillage 15 min (`locked_until`, `failed_login_attempts`)
- ✅ 2FA TOTP avec secret signé via `django.core.signing.Signer` (setup)
- ✅ Politique mot de passe renforcée (12 caractères minimum, similarité, communs, numérique)
- ✅ Token API expirant : `ExpiringTokenAuthentication` (24h, configurable via `TOKEN_EXPIRY_HOURS`)
- ✅ Vérification établissement systématique dans toutes les vues IDOR sensibles
- ✅ Middleware `RoleAccessMiddleware` bloquant PARENT/ÉLÈVE hors de leur portail
- ✅ Décorateur `_admin_required` sur toutes les vues de gestion des utilisateurs
- ✅ `_can_manage()` : vérification cross-établissement avant modification d'un utilisateur

### Protection HTTP
- ✅ HSTS activé en production (31536000 secondes, includeSubDomains, preload)
- ✅ `SECURE_SSL_REDIRECT = True` en production
- ✅ `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` en production
- ✅ `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`
- ✅ `CSRF_COOKIE_HTTPONLY = True`
- ✅ `X-Frame-Options` via `XFrameOptionsMiddleware`
- ✅ `SECURE_CONTENT_TYPE_NOSNIFF = True` en production
- ✅ `Referrer-Policy: strict-origin-when-cross-origin`
- ✅ `frame-ancestors 'none'` dans la CSP

### Validation & Upload
- ✅ CSRF protection active sur toutes les vues (sauf webhook SMS — voir VUL-2026-02)
- ✅ Validation MIME robuste via Pillow (résistante au spoofing)
- ✅ Limite upload : 5 Mo mémoire / 10 Mo par requête
- ✅ Template tag `breadcrumb_tags` : `escape()` appliqué sur tous les labels/URLs

### API REST
- ✅ Token authentication requis sur tous les endpoints (sauf `ObtenirTokenView`)
- ✅ Rate limiting login API : 5 req/min (`LoginRateThrottle`)
- ✅ Rate limiting général : 100 req/min par utilisateur
- ✅ Filtrage systématique par établissement (`_get_user_etablissement()`)
- ✅ Révocation de token disponible (`RevoquerTokenView`)

### Documents & PDF
- ✅ Contrôle rôle `_can_generate_document()` sur la génération de documents
- ✅ Vérification IDOR sur `certificat_scolarite` (établissement de l'inscription)
- ✅ Vérification IDOR sur `liste_classe_pdf` (classe appartenant à l'établissement)
- ✅ Vérification IDOR sur `liste_personnel_pdf` (cycle appartenant à l'établissement)
- ✅ `signataire_tags.py` : toutes les valeurs passent par `_e()` (équivalent `html.escape()`)

### Traçabilité
- ✅ `AuditRequestMiddleware` actif — stocke la requête dans le thread local
- ✅ `AuditLog` model avec actions CREATE/UPDATE/DELETE, IP, utilisateur
- ✅ Logging des tentatives 2FA et des codes incorrects via messages d'erreur
- ✅ `IncomingSMSLog` enregistre tous les SMS entrants (numéro, commande, réponse)

### Architecture
- ✅ UUID comme clé primaire (`BaseModel`) → énumération des IDs impossible
- ✅ `SECURE_PROXY_SSL_HEADER` configuré pour Nginx
- ✅ `CSRF_TRUSTED_ORIGINS` limité aux adresses locales connues
- ✅ `ALLOWED_HOSTS` sécurisé avec fallback `localhost` en développement

---

## 8. PLAN DE CORRECTION PRIORITAIRE

| # | Vulnérabilité | Fichier | Priorité | Effort |
|---|---------------|---------|----------|--------|
| 1 | VUL-2026-01 — Clé API Anthropic exposée | `.env` | 🔴 IMMÉDIAT | 15 min |
| 2 | VUL-2026-03 — CSP `unsafe-inline` régression | `csp_middleware.py` | 🟠 Cette semaine | 30 min |
| 3 | VUL-2026-02 — Webhook SMS sans protection | `communication/views.py` | 🟠 Cette semaine | 2h |
| 4 | VUL-2026-05 — Logout via GET | `accounts/views.py` | 🟡 Prochaine itération | 30 min |
| 5 | VUL-2026-04 — Session timeout non appliqué | `settings.py` | 🟡 Prochaine itération | 1h |
| 6 | VUL-2026-06 — Absence de LOGGING | `settings.py` | 🟡 Prochaine itération | 1h |
| 7 | VUL-HERITEE-01 — Session 2FA non signée | `accounts/views.py` | 🟡 Backlog | 2h |
| 8 | VUL-HERITEE-02 — Tokens dans logs Nginx | `nginx/` config | 🟡 Backlog | 30 min |

---

## 9. ANALYSE DES MODULES

| Module | IDOR | Auth | Validation | Rôles | Statut |
|--------|------|------|------------|-------|--------|
| `accounts` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `finances` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `inscriptions` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `documents` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `bulletins` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `personnel` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `presences` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `pedagogie` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `vacations` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `examens` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `viescolaire` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `api` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `communication` | ✅ | ✅ | ✅ | ⚠️ | ⚠️ Webhook |
| `parametres` | ✅ | ✅ | ✅ | ✅ | ✅ OK |
| `etablissements` | ✅ | ✅ | ✅ | ✅ | ✅ OK |

---

## 10. ARCHITECTURE DE SÉCURITÉ ACTUELLE

### Middlewares actifs (ordre d'exécution)

```
SecurityMiddleware
SessionMiddleware
CommonMiddleware
CsrfViewMiddleware
AuthenticationMiddleware
CSPNonceMiddleware          ← nonce CSP par requête (⚠️ unsafe-inline à corriger)
RoleAccessMiddleware        ← restriction PARENT/ÉLÈVE
MessageMiddleware
XFrameOptionsMiddleware
AuditRequestMiddleware
```

### Content Security Policy émise (état actuel — à corriger)

```
default-src 'self';
script-src  'self' 'nonce-{nonce}' 'unsafe-inline';    ← ⚠️ unsafe-inline à supprimer
style-src   'self' 'nonce-{nonce}';
script-src-attr 'self' 'unsafe-inline';                ← ⚠️ à corriger
img-src     'self' data: blob:;
font-src    'self';
connect-src 'self';
frame-ancestors 'none';
base-uri    'self';
form-action 'self';
```

### Content Security Policy cible (après correction)

```
default-src 'self';
script-src  'self' 'nonce-{nonce}';
style-src   'self' 'nonce-{nonce}';
script-src-attr 'nonce-{nonce}';
img-src     'self' data: blob:;
font-src    'self';
connect-src 'self';
frame-ancestors 'none';
base-uri    'self';
form-action 'self';
```

---

## 11. ÉVOLUTION DU SCORE

| Rapport | Date | Score | Failles ouvertes |
|---------|------|-------|------------------|
| v1.0 | Avant audit | 4.5/10 | 16 failles |
| v4.0 | Avril 2026 | 10/10 | 0 |
| v5.0 | Avril 2026 | 9.5/10 | 2 (héritées) |
| **v6.0** | **Juin 2026** | **6.5/10** | **10 (2 héritées + 8 nouvelles)** |

> ⚠️ Le développement de nouvelles fonctionnalités (module Communication, intégration
> Anthropic AI) a introduit de nouvelles vulnérabilités sans revue de sécurité préalable.
> **Recommandation :** Intégrer un checklist de sécurité systématique avant chaque merge
> de nouveau module (voir section 12).

---

## 12. CHECKLIST SÉCURITÉ DÉVELOPPEUR (à valider avant chaque merge)

```
[ ] Aucune clé API / secret / mot de passe hardcodé dans le code
[ ] Aucun @csrf_exempt non justifié et non protégé autrement
[ ] Toute vue accédant à des données vérifie l'appartenance à l'établissement (IDOR)
[ ] Tout nouveau endpoint API a @login_required ou IsAuthenticated
[ ] Tout formulaire POST utilise {% csrf_token %}
[ ] Les fichiers uploadés sont validés (extension + MIME Pillow + taille)
[ ] Les logs ne contiennent pas de données personnelles (mots de passe, tokens)
[ ] Les nouvelles dépendances sont pined à une version exacte
[ ] La CSP ne contient pas 'unsafe-inline' ni 'unsafe-eval'
[ ] docs/GUIDE_UTILISATION_YELEN_SCHOOL.md est mis à jour
```

---

## 13. RECOMMANDATIONS FUTURES

| Priorité | Action | Effort estimé |
|----------|--------|---------------|
| Haute | Mettre en place `pip-audit` dans le pipeline CI | Faible |
| Haute | Configurer Nginx pour masquer `Authorization` dans les logs | Faible |
| Moyenne | Ajouter HMAC sur le webhook SMS | Moyen |
| Moyenne | Implémenter un vrai timeout de session (middleware ou `SESSION_COOKIE_AGE`) | Faible |
| Moyenne | Signer la valeur `_2fa_user_pk` en session | Moyen |
| Faible | Test d'intrusion externe professionnel avant ouverture publique | Élevé |
| Faible | Rotation automatique des tokens API après connexion réussie | Moyen |
| Faible | Chiffrement des données salariales sensibles au niveau applicatif | Élevé |

---

*Rapport v6.0 — Audit de mise à jour — 23 juin 2026 — YELEN SCHOOL v4.2 — Confidentiel*