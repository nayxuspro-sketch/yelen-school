# A7 — Sécurisation logs Nginx : tokens API

**Date :** 2026-09-17  
**Priorité :** P1 (hérité VUL-HERITEE-02)  
**Statut :** ✅ Corrigé (doc + config)

## Problème initial

Les tokens DRF transitent dans l'en-tête `Authorization: Token <valeur>`.  
Si Nginx enregistre les en-têtes HTTP (`$http_authorization` dans `log_format`), les tokens apparaissent en clair dans `access.log`.

CVSS 2.6 — Token exposé dans logs d'accès.

## Solution implémentée

### 1. Config Nginx (`nginx/default.conf`)

- `log_format yelen_combined` custom **sans** `$http_authorization`
- Format utilisé : `$remote_addr - $remote_user [$time_local] "$request" $status ...` + temps de réponse, **pas de headers sensibles**
- `access_log` explicite avec ce format
- Commentaire A7 dans le fichier pour traçabilité

```nginx
log_format yelen_combined '$remote_addr - $remote_user [$time_local] '
                          '"$request" $status $body_bytes_sent '
                          '"$http_referer" "$http_user_agent" '
                          'rt=$request_time ...';

access_log /var/log/nginx/access.log yelen_combined;
```

- Optionnel : `map $http_authorization $loggable` pour désactiver complètement le log des requêtes avec token (commenté par défaut, à activer si besoin de confidentialité maximale)

### 2. Backend Django

- `settings.py` LOGGING ne log jamais `HTTP_AUTHORIZATION`
- `api/authentication.py` : `ExpiringTokenAuthentication` ne log pas le token en clair (seulement hash ou 8 premiers caractères pour debug)
- Vérifié : aucun `logger.info(request.META)` qui exposerait les headers

### 3. Bonnes pratiques déploiement

- **Ne jamais** ajouter `$http_authorization` ou `$http_cookie` dans `log_format`
- **Ne jamais** logger `request.headers` en clair côté Django
- Rotation des logs : `logrotate` avec permissions 640
- Accès logs limité à `root` et groupe `adm`
- Si besoin d'audit API, logger seulement `hash(token)` ou `user_id`, pas la valeur

### 4. Vérification

```bash
# Vérifier que access.log ne contient pas de token
grep -i "Token" /var/log/nginx/access.log
# Doit retourner vide

# Vérifier format
nginx -T | grep log_format
```

### 5. Références

- OWASP Logging Cheat Sheet : ne jamais logger secrets, tokens, passwords
- Django docs : `SECURE_PROXY_SSL_HEADER` déjà configuré, pas de log des headers sensibles

## Checklist A7

- [x] `nginx/default.conf` : log_format sans Authorization
- [x] Doc `SECURITE_NGINX_TOKENS.md` créée
- [x] Vérifié que Django LOGGING ne log pas Authorization
- [x] Mention dans `AUDIT_SECURITE.md` VUL-HERITEE-02 → résolu

## Déploiement

Après modification `nginx/default.conf`, redéployer :

```bash
docker-compose -f docker-compose.prod.yml up -d nginx
# ou
docker compose -f docker-compose.prod.yml restart nginx
```
