# Audit de sécurité de suivi — YELEN SCHOOL

**Date :** 14 septembre 2026
**Périmètre :** code Django, API REST, templates, webhook SMS, Nginx et scripts d'installation
**Nature :** revue statique de suivi
**Branche :** `arena/01a06c5a-yelen-school`

> Cet audit remplace les conclusions contradictoires des anciens rapports. Aucun score numérique n'est attribué tant que la suite de tests PostgreSQL et les essais Windows n'ont pas été exécutés dans leur environnement réel. L'analyse locale `pip-audit` du 14 septembre 2026 ne signale aucune vulnérabilité connue ; la CI la rejoue à chaque changement.

## 1. Résumé

Les protections principales sont présentes : authentification Django, CSRF, rôles, filtrage par établissement, limitation du login API, expiration des tokens API, validation des fichiers par Pillow, limites d'upload, CSP par nonce et journal d'audit.

Les corrections de cette révision portent sur :

- signature et expiration du défi intermédiaire 2FA ;
- authentification obligatoire du webhook SMS en production ;
- limitation de fréquence du webhook SMS ;
- possibilité de signature HMAC-SHA256 du webhook ;
- format de logs Nginx n'enregistrant pas l'en-tête `Authorization` ;
- contrôle automatique des dépendances par `pip-audit` dans la CI.

## 2. Éléments vérifiés dans le code

| Domaine | État | Vérification |
|---|---|---|
| CSRF des formulaires | En place | `CsrfViewMiddleware`, formulaires POST protégés |
| Déconnexion | Corrigée | `logout_view` accepte POST uniquement |
| Sessions | Renforcées | `SESSION_COOKIE_AGE=3600`, renouvellement à chaque requête |
| 2FA | Renforcée | `_2fa_user_pk` signé par `TimestampSigner`, expiration de 5 minutes |
| CSP | En place | nonce par requête, absence de `unsafe-inline` dans le middleware actuel |
| API | En place | authentification par token expirant et throttling du login |
| IDOR | Contrôles présents | filtrage par établissement dans les vues sensibles auditées |
| Uploads | Renforcés | extension, taille et contenu réel contrôlés par Pillow |
| Webhook SMS | Renforcé | token ou HMAC obligatoire hors DEBUG, IP optionnelles et rate limit |
| Logs Nginx | Durcis | format explicite sans `Authorization` ni query string |
| Dépendances | Corrigées statiquement | `pip-audit -r requirements/base.txt` : aucune vulnérabilité connue le 14/09/2026 ; Django 5.2.17, DRF 3.17.2, Pillow 12.3.0 et autres correctifs ; contrôle conservé dans la CI |
| PostgreSQL/Redis | Non exposés par Compose client | services accessibles uniquement dans le réseau Docker |

## 3. Webhook SMS

Le webhook reste exempté de CSRF parce qu'il est appelé par une passerelle externe. Il doit cependant présenter au moins une preuve d'authentification :

- `X-SMS-Token` ou paramètre `token` correspondant à `SMS_WEBHOOK_TOKEN` ; ou
- `X-SMS-Signature` contenant le HMAC-SHA256 du corps de la requête avec `SMS_WEBHOOK_HMAC_SECRET`.

En dehors de `DEBUG=True`, une configuration sans secret renvoie HTTP 503. Les requêtes sont limitées par adresse source avec `SMS_WEBHOOK_RATE_LIMIT` (60 par minute par défaut).

Les installateurs Windows et Linux génèrent maintenant automatiquement `SMS_WEBHOOK_TOKEN` lors d'une nouvelle installation. Le token ne doit pas être copié dans un ticket, un log ou une URL publique.

## 4. Points restant à valider

Ces points ne peuvent pas être clôturés par une simple revue statique :

1. exécuter toute la suite pytest contre PostgreSQL 15 et Redis 7 ;
2. laisser la CI rejouer `pip-audit -r requirements/base.txt` à chaque changement et traiter toute nouvelle vulnérabilité signalée ;
3. tester le webhook avec token valide, token invalide, absence de token, dépassement de limite et passerelle réellement configurée ;
4. vérifier les en-têtes CSP sur une réponse HTML réelle ;
5. vérifier les logs Nginx dans le conteneur ;
6. effectuer le test complet de sauvegarde/restauration sous Windows ;
7. vérifier les secrets générés et le remplacement du mot de passe initial `admin123` sur une installation client ;
8. décider si les middlewares de licence commentés doivent être activés pour l'offre commerciale.

## 5. Règles de déploiement

- Ne jamais activer `DEBUG=True` chez un client.
- Ne jamais exposer PostgreSQL `5432` ou Redis `6379`.
- Ne jamais publier directement les ports HTTP YELEN `8000` à `8005` sur Internet.
- Conserver `.env` hors du dépôt et hors des archives de distribution.
- Générer un token différent pour chaque établissement.
- Changer le mot de passe initial dès la première connexion.
- Copier les sauvegardes sur un support différent du serveur.
- Utiliser le VPN pour l'accès distant plutôt qu'une redirection publique vers YELEN.

## 6. Documents historiques

- `Rapport_Securite.md` est conservé comme rapport historique du 11 avril 2026 ; son score de 10/10 ne constitue pas l'état actuel.
- `SECURITY_FAILLES.md` est conservé comme inventaire historique du 9 avril 2026 ; ses volumes de failles ne constituent pas un décompte actuel.
- Les affirmations contradictoires des anciens rapports ont été remplacées par le présent audit de suivi.

## 7. Limites de la présente révision

L'environnement de développement utilisé pour cette revue ne contient pas Docker, Django installé ni PowerShell Windows. La validation runtime, le test réel du pare-feu, le test de restauration et l'exécution de la CI doivent donc être réalisés sur GitHub ou sur une machine de déploiement contrôlée.
