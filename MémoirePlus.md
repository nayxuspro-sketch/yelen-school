# MémoirePlus — Guide de reprise YELEN SCHOOL (sécurité & licences)

> **Objectif :** Ce fichier sert de mémoire vive pour tout agent qui reprend le chantier sur un nouveau chat. Il doit être mis à jour à chaque commit significatif. Raisonnement en français obligatoire.

---

## 1. Contexte projet

- **Projet :** YELEN SCHOOL v5.0 — Gestion scolaire (Burkina Faso), Django 4.2, DRF, PostgreSQL (prod) / SQLite (mode autonome), Redis (prod) / DB cache (autonome).
- **Dépôt :** `nayxuspro-sketch/yelen-school`
- **Branche de travail session actuelle :** `arena/01a0af14-yelen-school` (basée sur `main` = `848aeb9`, qui contient PR #3 + PR #4 mergées)
- **Branches arena historiques :**
  - `arena/01a0aaaf-yelen-school` → PR #3 (P0 licences + RBAC API + S2), 4 commits : `199fd81 fix(pdf)`, `8c7c8b3 feat(licences) P0`, `ad797cb feat(api) RBAC`, `fa204bf feat(api) refresh`
  - `arena/01a0aebf-yelen-school` → PR #4 (suite PR #3 + S3/S4/A1/A4/A6), commits : `a501e63` (S3/S4/A1/A4), `613c90f` (A6 CSP)
- **PR :**
  - PR #3 — **MERGÉE** — P0 + RBAC + S2
  - PR #4 — **MERGÉE** — S3/S4/A1/A4/A6 + A7 + P1 + P2
  - PR #2 (`arena/01a06c5a`, "Validation complète PostgreSQL et Redis") — **OUVERTE mais NON MERGEABLE** : historique sans ancêtre commun avec `main` (181 conflits). Contient des éléments intéressants absents de main : `installer/` (scripts Windows/Linux, sauvegardes, tâches planifiées), `core/audit.py` + `verify_audit_chain`, triggers financiers PostgreSQL (`finances/migrations/0016`), `docs/LICENCE_ED25519.md`, `docker-compose.client.yml`. Décision requise : **fermer** et re-porter manuellement les éléments utiles, ou abandonner.

---

## 2. État réel — par ordre de priorité (référence initiale du 17/09/2026)

### 🔴 A. Immédiat
- [x] CI rouge sur `main` (848aeb9) : `cryptography` absent de `requirements/base.txt` → `ModuleNotFoundError` — **corrigé** session 01a0af14
- [x] `LICENSE_ENFORCEMENT` : désormais **actif par défaut** dès que `DEBUG=False` (variable absente → true), warning au boot si explicitement `false` en prod. Un `.env` prod n'a plus besoin de la ligne, mais `LICENSE_ENFORCEMENT=true` reste recommandé explicitement.

### 🟠 B. Chantier sécurité — 4 axes + audit v6.0

| # | Chantier | État au 17/09/2026 18h |
|---|----------|------------------------|
| S2 | Renouvellement tokens API | **Fait** PR #3 `fa204bf` : `POST /api/auth/token/refresh/` rotation, old token supprimé, throttled `login` 5/min, tests 4 |
| S3 | Expiration liens publics | **Fait** `a501e63` : bulletin guard `token_valide` + MessageParent `date_expiration` 30j + migration 0003 + templates |
| S4 | Justificatifs parentaux | **Fait** `a501e63` : `/media/communication/justificatifs/` public → vue `justificatif_download` @login_required + filtre etablissement + FileResponse + template fix |
| A1 | Webhook SMS VUL-2026-02 HAUTE | **Fait** `a501e63` : IP whitelist + token + **HMAC SHA256** (`SMS_WEBHOOK_SECRET`, header `X-SMS-Signature`) + rate limiting 30/min/IP via cache |
| A2 | Sessions VUL-2026-04 | **Déjà fait** dans main : `SESSION_COOKIE_AGE=3600` + `SESSION_SAVE_EVERY_REQUEST=True` |
| A3 | Logout par GET VUL-2026-05 | **Déjà fait** : `@require_POST` sur `logout_view` |
| A4 | 2FA VUL-HERITEE-01 | **Fait** `a501e63` : pk 2FA en clair → signé `Signer().sign()` / `unsign()` avec `BadSignature` |
| A5 | Logging VUL-2026-06 | **Déjà fait** : `LOGGING` avec `security.log`/`django.log` RotatingFileHandler |
| A6 | 15 handlers JS inline → CSP bloque | **Fait complet** `613c90f` : 126 onclick/onsubmit → 0 via `data-csp-*` + `static/js/csp_handlers.js` (delegation, nonce) |
| A7 | Nginx tokens API en clair | **À faire côté déploiement** : config nginx rewrite headers, pas code |

Vérifié résolus : VUL-2026-01 Anthropic, VUL-2026-03 CSP unsafe-inline (déjà corrigée), scripts debug racine supprimés.

### 🟡 C. P1 licences — architecture anti-fraude définitive (gros morceau)
- [ ] Signature asymétrique Ed25519 : clé privée éditeur, publique dans app (faille structurelle actuelle : lire .env/base = forger licence)
- [ ] Phone-home : heartbeat signé, révocation à distance, bail hors-ligne fenêtre décroissante
- [ ] Binding machine réel : `LicenceActivation` (MAC/hostname) existe mais jamais utilisé → empreinte multi-attributs signée, 1 active/licence
- [ ] ENSURE_ADMIN → compte staff : supprimer superuser école qui renouvelle sa propre licence
- [ ] `LICENCE_SIGNING_KEY` dédiée (au lieu de `SECRET_KEY` Django)
- [ ] Anti-tamper : contrôle intégrité modules licences au boot + `check_licences --strict` qui arrête app (actuellement dégradation gracieuse = rien bloqué)

### 🟢 D. Détection & dissuasion (P2)
- [ ] Centralisation `LicenceAuditLog` côté éditeur + alerte SMS immédiate `TENTATIVE_FRAUDE`
- [ ] Filigrane/métadonnées PDF (établissement + clé licence) pour tracer fuite
- [ ] API REST non soumise au contrôle licence : middleware ne voit pas auth token DRF → ajouter permission `IsLicenseActive` (trou réel : licence expirée peut passer par API)
- [x] Couverture tests ≥80% : licences **84 %** (`test_p2_coverage_suite.py`, 35 tests) ; nettoyage doublons morts fait

### ⚠️ E. À clarifier
- Commits `5b85d3e`/`ea9bafa` cités n'existent pas (vérifié reflog) — s'ils vivent ailleurs, synchroniser
- `LICENSE_ENFORCEMENT` doit être `true` en prod

---

## 3. Détail technique des fix déjà réalisés

### S2 — `POST /api/auth/token/refresh/`
- Fichiers : `api/views.py` (`RenouvelerTokenView`), `api/urls.py`, `api/tests.py`
- Logique : token valide (pas expiré) + auth `ExpiringTokenAuthentication` → `Token.objects.filter(user).delete()` + `Token.objects.create()` → retourne nouveau token. Token expiré (supprimé par auth) → 401, doit repasser par `/api/auth/token/` username/password.
- Throttle : `LoginRateThrottle` (5/min) réutilisé.

### S3a — Bulletin
- `bulletins/views.py` : `bulletin_parent_consulter` vérifie `if not bulletin.token_valide` **avant** `est_publie` → erreur "lien plus valide" sans divulguer données.
- `bulletin_parent_signer` vérifiait déjà `token_valide`.
- Tests : `bulletins/tests/test_expiration.py` (5 tests)

### S3b — MessageParent
- `communication/models.py` : ajout `date_expiration = DateTimeField(null=True, blank=True)` + `@property est_valide` (None = True rétrocompat, sinon `now <= expiration`)
- `communication/views.py` : `message_create` pose `now+30j`, `repondre()` check `est_valide` en tête (GET+POST) → `lien_expire`
- Template `repondre.html` : bloc `lien_expire` avec alert danger
- Migration : `communication/migrations/0003_ajout_expiration_lien_parent.py` (portable PG/SQLite)
- Tests : `communication/tests/test_expiration.py` (5 tests)

### S4 — Justificatifs
- `communication/views.py` : `justificatif_download` @login_required, `_get_etab`, `get_object_or_404(ReponseParent, pk, message__etablissement=etab)`, `FileResponse`
- `communication/urls.py` : `justificatif/<uuid:pk>/`
- Template `message_detail.html` : `{{ justificatif.url }}` → `{% url 'justificatif_download' %}`
- Tests : 4 (anon 302, sans fichier 404, autre etab 404, template utilise vue sécurisée)

### A1 — Webhook SMS
- `yelen_school/settings.py` : `SMS_WEBHOOK_SECRET`, `SMS_WEBHOOK_RATE_LIMIT=30`
- `communication/views.py` : 
  - Rate limiting via `cache.get/set` clé `sms_webhook_rl:{ip}` 60s, 429 si > limit
  - IP whitelist `SMS_ALLOWED_IPS` conservée
  - Token `SMS_WEBHOOK_TOKEN` conservé
  - HMAC : si `SMS_WEBHOOK_SECRET` défini, exige header `X-SMS-Signature` = hex HMAC-SHA256(body, secret), `compare_digest`, 403 si manquant/invalide
- Tests SMS : 6 verts

### A4 — 2FA
- `accounts/views.py` : `login_view` signe pk via `Signer().sign(str(pk))`, `login_2fa` unsign avec try `BadSignature` → pop session + redirect login

### A6 — CSP inline handlers
- Problème : `CSPNonceMiddleware` pose `script-src-attr 'none'` → bloque `onclick=`/`onsubmit=`
- Fix : 4 scripts Python `/tmp/fix_csp*.py` ont remplacé 126 occurrences par `data-csp-*`
- Fichier central : `static/js/csp_handlers.js` (event delegation, gère dismiss/show/remove/trigger-click/confirm/action/quick-email/toggle-all/modal-open/href/etc.)
- Inclusion : `core/base.html` avec nonce + 5 templates standalone (login, offline, portail_parent, sms_configuration, bulletin_parent, repondre)
- Résultat : `grep onclick = 0`

### P0 licences (PR #3)
- `yelen_school/settings.py` : `LICENSE_ENFORCEMENT = env('LICENSE_ENFORCEMENT')=='true'`, middlewares conditionnels `LicenceCheckMiddleware`, `LicenceLimitsMiddleware`, `LicenceContextMiddleware` uniquement si flag true
- `licences/models.py`, `services.py`, `middleware.py`, `decorators.py` : activation effective, signature intégrité, feature flags, limites
- Suppression `licences/licences_models.py` (doublon)
- `django.contrib.humanize` ajouté (templates l'utilisaient)
- Tests : `licences/tests/test_*.py` (56 tests)

### RBAC API (PR #3)
- `api/permissions.py` : permissions par rôle (`IsDirecteurOrSuperAdmin`, etc.)
- `api/views.py` : cloisonnement endpoints élèves par rôle + etablissement
- `api/urls.py` : `<uuid:pk>` fix
- `api/serializers.py` : `genre` fix
- Tests : `api/tests.py` (15 tests dont 4 refresh)

---

## 4. Commandes & pièges

### Environnement
- **Venv disparaît entre sessions** (sandbox Arena) : recréer à chaque reprise
  ```bash
  cd /home/user/yelen-school
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements/base.txt
  ```
- **DB par défaut = PostgreSQL** qui n'est pas dispo en sandbox → utiliser SQLite pour tests :
  ```bash
  DB_ENGINE=sqlite .venv/bin/python -m pytest ...
  DB_ENGINE=sqlite .venv/bin/python manage.py collectstatic --noinput
  DB_ENGINE=sqlite .venv/bin/python manage.py makemigrations ...
  ```
- **collectstatic obligatoire** avant tests licences (sinon `Missing staticfiles manifest entry for 'css/yelen.css'`) :
  ```bash
  DB_ENGINE=sqlite .venv/bin/python manage.py collectstatic --noinput
  ```
- **pytest config** : `pytest.ini` a `DJANGO_SETTINGS_MODULE=yelen_school.settings`, `--reuse-db`, `testpaths` inclut toutes apps. `conftest.py` global désactive `SECURE_SSL_REDIRECT` (autouse fixture) → sinon 301 redirect HTTP→HTTPS en tests.

### Tests
- Ciblés rapides (91 tests) :
  ```bash
  DB_ENGINE=sqlite .venv/bin/python -m pytest api/tests.py licences/tests/ bulletins/tests/test_expiration.py communication/tests/test_expiration.py communication/tests/test_incoming_sms.py -q
  ```
- Tous :
  ```bash
  DB_ENGINE=sqlite .venv/bin/python -m pytest -q
  ```
- Un fichier :
  ```bash
  DB_ENGINE=sqlite .venv/bin/python -m pytest bulletins/tests/test_expiration.py -vv
  ```

### Git
- Branche session : `arena/01a0aebf-yelen-school` (ne jamais switcher, Arena track cette branche)
- Push : `git push origin arena/01a0aebf-yelen-school`
- PR : `gh pr create --base main --head arena/01a0aebf-yelen-school --title "..." --body "..."`
- Si .git recréé (reflog montre clone) : refetch PR #3
  ```bash
  git fetch origin arena/01a0aaaf-yelen-school:refs/heads/tmp-pr3
  git merge tmp-pr3 --no-edit
  ```
- Vérifier état : `git log --oneline -10`, `git status --porcelain`, `gh pr list --state all`

### Settings importants
- `LICENSE_ENFORCEMENT` : false = démo, true = prod (bloque si licence expirée/révoquée/absente)
- `SMS_*` : `SMS_WEBHOOK_TOKEN`, `SMS_ALLOWED_IPS`, `SMS_WEBHOOK_SECRET`, `SMS_WEBHOOK_RATE_LIMIT`
- `TOKEN_EXPIRY_HOURS` : 24h défaut
- `SESSION_COOKIE_AGE` : 3600 (1h)
- `CACHE_BACKEND` : `database` en SQLite, `redis` en PG

---

## 5. Architecture & conventions

- **Core** : `core/models.py` BaseModel (UUID pk, created_at, updated_at, is_active, created_by/updated_by)
- **Licences** : `Licence` (etablissement FK, type, statut ACTIVE/EXPIREE/REVOQUEE, dates), `LicenceActivation` (inutilisé, à utiliser pour binding machine), `LicenceAuditLog`
- **API** : `api/authentication.py` `ExpiringTokenAuthentication` (supprime token si `created < now - TOKEN_EXPIRY_HOURS`), `api/permissions.py` RBAC, `api/views.py` eleves_list/detail avec filtre etablissement
- **Bulletins** : `Bulletin` (inscription, trimestre, est_publie, token_signature, token_expire_le 15j, signe_le)
- **Communication** : `MessageParent` (etablissement, eleve, type, token UUID, date_expiration 30j), `ReponseParent` (OneToOne MessageParent, justificatif FileField)
- **CSP** : `yelen_school/csp_middleware.py` génère nonce par requête, header `script-src 'self' 'nonce-{nonce}'`, `style-src 'self' 'nonce-{nonce}'`, `script-src-attr 'none'`
- **Templates** : `core/base.html` base principale avec sidebar, HTMX, PWA. Partials HTMX dans `*/templates/*/partials/`. Standalone : login, bulletin_parent, repondre, offline, portail_parent
- **Static** : `static/js/htmx.min.js`, `static/js/csp_handlers.js`, `static/css/yelen.css`, `static/js/pwa.js`

---

## 6. Reste à faire — guide pour prochain agent

### Immédiat (avant merge prod)
1. Vérifier CI verte sur PR #4 (job PostgreSQL) — le job SQLite existe, mais PG peut échouer si migration 0003 non appliquée en PG
2. Mettre `LICENSE_ENFORCEMENT=true` dans `.env` prod (point qui transforme PR en protection réelle)

### A7 — Nginx (VUL-HERITEE-02)
- Tokens API en clair dans logs d'accès nginx → config nginx : `log_format` sans `http_authorization` ou rewrite headers. Pas code Django, mais documenter dans `docs/DEPLOIEMENT.md` ou `README`.

### P1 licences — anti-fraude définitive (gros morceau, ~5-6 commits)
1. **Ed25519** : générer paire clés, clé privée chez éditeur (hors dépôt), publique dans `yelen_school/settings.py` ou fichier `licences/public_key.pem`, signer licences via `licences/services.py` (actuellement HMAC avec SECRET_KEY → faille si .env lu)
2. **LICENCE_SIGNING_KEY** dédiée (env var) au lieu de SECRET_KEY
3. **Binding machine** : utiliser `LicenceActivation` — empreinte multi-attributs (MAC, hostname, CPU id, disque) signée, 1 active par licence, vérifiée au boot
4. **Phone-home** : heartbeat signé vers serveur éditeur (si dispo), révocation à distance, bail hors-ligne fenêtre décroissante (ex: 7j, puis 3j, puis 1j si pas de heartbeat)
5. **ENSURE_ADMIN → staff** : actuellement superuser école peut renouveler sa propre licence (superuser = créateur/renouveleur local) → créer rôle staff éditeur distinct
6. **Anti-tamper** : check intégrité modules licences au boot (hash fichiers `licences/*.py`) + `check_licences --strict` qui arrête app si tamper (actuellement dégradation gracieuse = rien bloqué)

### P2 — Détection & dissuasion
1. Centralisation `LicenceAuditLog` côté éditeur (API éditeur) + alerte SMS immédiate sur `TENTATIVE_FRAUDE`
2. Filigrane PDF : ajouter métadonnées (établissement + clé licence) dans `documents/` et `bulletins/` PDF (WeasyPrint) pour tracer fuite
3. **API REST** : middleware licence ne voit pas auth token DRF → ajouter permission `IsLicenseActive` dans `api/permissions.py` et l'appliquer à toutes vues API (trou réel : licence expirée peut passer par API)
4. Couverture tests ≥80% (règle projet) sur apps faibles ; nettoyage doublons morts

### E — Clarifications
- Commits `5b85d3e`/`ea9bafa` n'existent pas — si sur autre machine, synchroniser
- Vérifier `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` à jour (section 19.1.1 API REST ajoutée pour S2)

### Conseils reprise
- Toujours partir de `arena/01a0aebf-yelen-school` qui contient tout (P0+RBAC+S2+S3+S4+A1/A4/A6)
- Si nouveau chat Arena crée nouvelle branche `arena/XXXX`, merger `arena/01a0aebf` dedans immédiatement :
  ```bash
  git fetch origin arena/01a0aebf-yelen-school:refs/heads/tmp-memoire
  git merge tmp-memoire --no-edit
  ```
- Mettre à jour ce fichier `MémoirePlus.md` à chaque commit (ajouter ligne dans section 2 + 3)
- Raisonner en français, pas de diversion, focus S→A→P1→P2
- Tests : toujours `DB_ENGINE=sqlite` + `collectstatic` avant
- Ne jamais commit `.venv`, `staticfiles`, `media`, `logs`

---

## 7. Historique des sessions

- **2026-09-17 00:23 UTC** : PR #3 créée (`arena/01a0aaaf`) — P0 licences + RBAC API + S2 (fa204bf), 260 tests verts annoncés, 71 vérifiés en SQLite
- **2026-09-17 09:43 UTC** : Session `arena/01a0aebf` démarre sur `1ed8433` (sans PR #3) → merge PR #3, puis S3/S4/A1/A4/A6
  - `a501e63` : S3/S4/A1/A4
  - `613c90f` : A6 CSP complet (126→0)
  - PR #4 créée
- **2026-09-17 10:30 UTC** : Création `MémoirePlus.md` (ce fichier)

---

## 8. Liens utiles

- PR #3 : https://github.com/nayxuspro-sketch/yelen-school/pull/3
- PR #4 : https://github.com/nayxuspro-sketch/yelen-school/pull/4
- Rapport sécurité : `Rapport_Securite.md`, `SECURITY_FAILLES.md`, `Priorites.md`
- Guide : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` (section 19 Sécurité, 19.1.1 API REST)
- CI : `.github/workflows/ci.yml` (job SQLite ajouté en 1ed8433)

---

### A7 — Nginx tokens logs
- Fait `dce9c94` : `docs/SECURITE_NGINX_TOKENS.md` + `nginx/nginx.conf.example` avec `log_format securise` sans Authorization, doc déploiement.

### P1 licences — anti-fraude définitive
- Fait `57216fa` (77 tests verts licences → 90 avec P2) :
  - Ed25519 asymétrique : `LICENCE_PRIVATE_KEY` (éditeur hors dépôt) / `LICENCE_PUBLIC_KEY` (app), `signature_ed25519` field, `_load_private_key/_load_public_key`, `verifier_signature_ed25519` prioritaire + anti-downgrade, `generate_licence_keys` management command
  - `LICENCE_SIGNING_KEY` dédiée (fallback SECRET_KEY)
  - Phone-home : `heartbeat.py` avec `urllib.request` (pas requests), payload signé HMAC+Ed25519, `LICENCE_HEARTBEAT_URL`, `LICENCE_HEARTBEAT_INTERVAL_HOURS`, `LICENCE_OFFLINE_MAX_DAYS`/`GRACE_DAYS`, `record_heartbeat_success/failure`, fenêtre décroissante, `bail_offline_expire_le`, `is_bail_offline_expired`, `is_heartbeat_required`, `verify_heartbeat_response`
  - Binding machine multi-attributs : `LicenceActivation` avec `cpu_id`, `disk_serial`, `system_uuid`, `os_info`, `platform_data`, `machine_fingerprint` SHA256 canonique, `fingerprint_signature` HMAC + `fingerprint_signature_ed25519`, `generate_fingerprint`, `build_attrs_dict`, `compute_and_sign_fingerprint`, `verify_fingerprint`, `get_empreinte_serveur`, contrainte DB `unique_active_activation_per_licence` (partial unique index), `binding.py` `get_machine_attrs`/`collect_machine_fingerprint`
  - ENSURE_ADMIN→staff : `LICENCE_ADMIN_STAFF_ONLY` setting, vérif `is_staff` dans `LicenceAuditLogCentralView`/`VerifyView`
  - Anti-tamper : `boot_check.py` `_check_antitamper()` vérifie `verifier_signature` source, settings critiques, fichiers critiques, contrainte unique, middlewares, `run_boot_check(strict)` avec `RuntimeError` arrêt app si `LICENCE_ANTITAMPER_ENABLED`+`LICENSE_ENFORCEMENT`+strict, `check_licences` management command avec `--strict`

### P2 — LicenceAuditLog + filigrane PDF + IsLicenseActive API
- Fait partiel (en cours session) :
  - `licences/api.py` : `IsLicenseActiveView` `/api/licences/active/` + `LicenceStatusView` `/licences/api/status/` + `LicenceAuditLogCentralView` `/licences/api/audit/` (staff only, filtres licence_id/etab_id/action, pagination, stats) + `LicenceAuditLogVerifyView` `/licences/api/audit/verify/` (vérif chaîne hash)
  - `licences/pdf_utils.py` : `get_licence_info_for_pdf` (réutilise `_get_licence_for_user` api) + `inject_licence_filigrane_context`
  - `documents/templates/documents/pdf/partials/filigrane_licence.html` : partial réutilisable avec filigrane diagonal + bandeau bas traçabilité
  - `documents/templates/documents/pdf/*.html` : 6 templates patchés (attestation_non_redevabilite, certificat_scolarite, circulaire, convocation, liste_classe, liste_personnel) via `{% include "documents/pdf/partials/filigrane_licence.html" %}`
  - `pedagogie/templates/pedagogie/pdf/*.html` : 13 templates patchés (bulletin_base + 10 via sed + bilan/releve via héritage)
  - `documents/views.py` : injection `licence_info` dans 6 vues PDF via `inject_licence_filigrane_context`
  - `pedagogie/views.py` : ajout import `inject_licence_filigrane_context/get_licence_info_for_pdf` + `_pdf_licence_info` helper + injection dans `_build_bulletin_context`/`_build_bulletin_annuel_context` + `bilan_pdf`, `releve_moyenne_classe_pdf`, `bulletin_classe_batch_pdf`, `moyennes_disciplines_pdf`, `releve_notes_pdf`, `fiche_discipline_pdf`, `risque_decrochage_pdf`, `palmares_annuel_pdf`, `bulletin_annuel_classe_batch_pdf`, `prediction_classe_pdf`, `competences_bulletin_pdf` (14 vues)
  - `bulletins/views.py` : patch `BulletinAnnuelPDFView`/`Batch` avec `licence_info`
  - Fix bug critique `LicenceAuditLog.save()` : `self.pk is not None` toujours vrai à cause de `default=uuid.uuid4` → remplacé par `not self._state.adding`
  - Tests P2 : `licences/tests/test_p2_api_filigrane.py` 13 tests (IsLicenseActive API, AuditLog centralisation, filigrane) → 90 tests verts totaux (77+13)

### E — commits 5b85d3e/ea9bafa
- Vérifié : `git log --all`, `git show-ref`, `fetch --all depth 200` → introuvables. Probablement squashés/rebasés ou dans autre repo. Documenté ici.

## 8. Liens utiles

- PR #3 : https://github.com/nayxuspro-sketch/yelen-school/pull/3
- PR #4 : https://github.com/nayxuspro-sketch/yelen-school/pull/4
- Rapport sécurité : `Rapport_Securite.md`, `SECURITY_FAILLES.md`, `Priorites.md`
- Guide : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` (section 19 Sécurité, 19.1.1 API REST)
- CI : `.github/workflows/ci.yml` (job SQLite ajouté en 1ed8433)

---

### P2 suite — couverture + nettoyage
- `1b1098e` : nettoyage doublons morts `settings01.py`, `settings--.py`, `models0.py`, `admin0.py`, `licences/tests.py`, `test_bulletin_old.py` (398 lignes supprimées)
- `110bfb3` : tests couverture `test_p2_coverage.py` 10 tests (binding collect, heartbeat payload/success/failure/verify/send_no_url/send_failure_mock, activation fingerprint, boot_check, check_licences, generate_keys) → 100 tests verts licences, couverture 74% (api 85%, models 78%, binding 59%, heartbeat 37%, generate_keys 80%)

---

### Session arena/01a0af14 (17/09/2026 après-midi) — clôture des points restants
- `fix(deps)` : `cryptography==50.0.1` dans `requirements/base.txt` (cause CI rouge main)
- `sec(licences)` : `LICENSE_ENFORCEMENT` par défaut = `not DEBUG` (sauf sous pytest), warning si désactivé hors DEBUG ; CI fixe `LICENSE_ENFORCEMENT=false` explicitement
- `chore` : suppression 27 fichiers parasites racine (exports source 13 Mo, `~$…docx`, `structure.txt`, scratch, polices Playfair non référencées, `.claude/worktrees`) + règles `.gitignore`
- `refactor` : `STORAGES` (remplace `STATICFILES_STORAGE`), `datetime.timezone.utc` → **0 warning de dépréciation** restant sur nos fichiers
- `test(licences)` : couverture 74 → **84 %** ; `decorators.py` 100 %, `heartbeat.py` 90 %, `binding.py` 84 %
- **Fix sécurité** : `LicenceActivation.verify_fingerprint()` retournait quand même True si l'empreinte stockée ne correspondait plus aux attributs (le `pass` laissait passer un enregistrement cloné/modifié) → retourne `False`
- Suite complète : **344 tests verts** (SQLite)
- Reste ouvert : décision sur PR #2 (voir section 1)

*Dernière mise à jour : 2026-09-17 par agent arena/01a0af14 — voir ci-dessus. Précédente : 2026-09-17 11:30 UTC par agent arena/01a0aebf — 100 tests verts licences (77 P1 + 23 P2), couverture 74%, P1 terminé 57216fa, A7 dce9c94, P2 terminé 3b39e1d+1b1098e+110bfb3 (IsLicenseActive API, audit centralisation+verify, filigrane 16 templates+20 vues, fix AuditLog _state.adding, pdf_utils factorisé, nettoyage doublons, E commits introuvables documenté).*

