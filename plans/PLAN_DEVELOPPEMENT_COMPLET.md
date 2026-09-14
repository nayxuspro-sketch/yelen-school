# Plan de développement et d'exploitation — YELEN SCHOOL

**État de référence :** 14 septembre 2026
**Branche de travail :** `arena/01a06c5a-yelen-school`
**Base officielle :** PostgreSQL 15 géré localement par Docker
**Objectif :** installation autonome chez un établissement, utilisable sur le réseau local sans connexion Internet quotidienne.

> Ce document remplace l'ancien plan daté de mars 2026, qui déclarait à tort plusieurs modules déjà présents comme « non implémentés ». Il décrit uniquement ce qui est livré dans le dépôt et les validations encore ouvertes.

## 1. Socle livré

| Domaine | État réel | Périmètre livré |
|---|---|---|
| Comptes et accès | ✅ Livré | utilisateurs, rôles, sessions, réinitialisation de mot de passe, 2FA TOTP avec défi signé et expiration de cinq minutes |
| Établissements et paramètres | ✅ Livré | établissements, classes, cycles, années scolaires, identité, modèles et déclencheurs SMS |
| Élèves et inscriptions | ✅ Livré | fiches élèves, inscriptions, réinscriptions, matricules et cloisonnement par établissement |
| Pédagogie | ✅ Livré | matières, enseignements, évaluations, notes, moyennes et analyse du risque de décrochage |
| Bulletins et documents | ✅ Livré | bulletins trimestriels/annuels, PDF, documents administratifs, signataires et archivage |
| Présences et vie scolaire | ✅ Livré | appels, présences, justifications, QR, discipline, activités et convocations |
| Finances | ✅ Livré | tarifs, échéanciers, paiements, reçus, relances, bourses et états financiers |
| Examens et vacations | ✅ Livré | candidats, centres/salles, listes et bulletins de vacation |
| Communication | ✅ Livré | messages aux parents, SMS local, webhook entrant authentifié et journaux associés |
| Licences | ✅ Livré | licences, limitations et contrôle d'expiration ; l'activation commerciale doit encore être décidée |

« Livré » signifie que le code, les migrations et les parcours applicatifs sont présents. La validation runtime complète reste indiquée dans la section 5.

## 2. Automatisations locales livrées

### 2.1 Analyse du risque de décrochage

Commande :

```text
python manage.py calculer_risques
python manage.py calculer_risques --strict
```

La commande traite l'année courante, exclut les inscriptions abandonnées, met à jour `RisqueDecrochage` et peut retourner une erreur si une inscription échoue avec `--strict`.

Sous Windows :

```text
programmer-risques.bat [HH:MM]
```

La tâche `YELEN SCHOOL - Analyse du risque de décrochage` est quotidienne à 02:00 par défaut. Elle démarre les services Docker sans reconstruction, lance la commande en mode strict, écrit `logs\risques.log` et retourne un code d'échec exploitable par le Planificateur de tâches.

### 2.2 SMS automatiques

Configuration : `Paramètres → SMS automatiques`
Commande :

```text
python manage.py sms_auto
python manage.py sms_auto --dry-run
python manage.py sms_auto --etablissement <UUID>
```

Types livrés :

- `ABSENCE_J1` : absence non justifiée de la veille, un seul SMS par élève et par exécution ;
- `ECHEANCIER` : rappel à la date exacte calculée à partir de `jours_avant` ;
- `RESULTATS` : bulletin nouvellement publié depuis la dernière exécution.

La commande est désactivée tant que `SMS_ENABLED` n'est pas explicitement activé. `--dry-run` ne modifie pas `last_run` et n'appelle pas l'envoi SMS. Une garde quotidienne empêche les doublons après une exécution réussie.

Sous Windows :

```text
programmer-sms.bat [HH:MM]
```

La tâche est quotidienne à 07:00 par défaut et écrit `logs\sms-auto.log`. La passerelle SMS reste locale : aucune API Internet n'est requise par l'application.

## 3. Déploiement local et données

### 3.1 Installation

- `docker-compose.client.yml` fournit PostgreSQL 15, Redis 7 et le service web ;
- `.env` est généré ou complété par les installateurs ;
- `install-local.sh` et `install-windows.ps1` génèrent les secrets Django, PostgreSQL et `SMS_WEBHOOK_TOKEN` lors d'une nouvelle installation ;
- le port HTTP local est choisi et persisté dans `.env` ;
- Windows peut créer la règle pare-feu limitée au réseau local ;
- aucune ouverture Internet publique ni configuration WireGuard n'est activée par défaut.

### 3.2 Sauvegarde

Une sauvegarde complète est une paire :

```text
backups/yelen_school_YYYYMMDD_HHMMSS.dump
backups/yelen_school_YYYYMMDD_HHMMSS_media.tar.gz
```

Les scripts livrés sont `installer/backup-windows.ps1` et `installer/backup-local.sh`. Ils utilisent `pg_dump` au format custom, archivent les médias, suppriment les fichiers incomplets et appliquent une rétention locale. Les procédures Windows Task Scheduler et Linux cron sont documentées dans les guides de déploiement.

### 3.3 Restauration

Les scripts `installer/restore-windows.ps1` et `installer/restore-local.sh` :

1. demandent une confirmation explicite, sauf option documentée ;
2. arrêtent le web et recréent la base PostgreSQL ;
3. restaurent le dump avec `pg_restore` ;
4. restaurent l'archive médias associée ;
5. exécutent `manage.py check` et attendent un `/health/` avec base et cache opérationnels.

La recette doit ensuite vérifier la connexion, un élève, un paiement, un document PDF et un fichier média sur une installation de test. Cette recette n'est pas encore exécutée dans l'environnement courant, car Docker n'y est pas disponible.

## 4. Sécurité livrée

- le défi 2FA est signé par `TimestampSigner` et expire après cinq minutes ;
- le webhook SMS exige un token ou une signature HMAC hors `DEBUG`, vérifie éventuellement les IP et applique une limite par adresse ;
- les installateurs génèrent le token webhook ;
- le format de logs Nginx exclut l'en-tête `Authorization` et la query string ;
- la CI contient une étape `pip-audit` ;
- PostgreSQL et Redis restent internes au réseau Docker ;
- `docs/AUDIT_SECURITE.md` est le rapport de référence unique.

## 5. Validations restantes

Ces éléments sont explicitement ouverts et ne doivent pas être présentés comme exécutés :

- [ ] exécuter la CI complète avec PostgreSQL 15 et Redis 7 ;
- [x] mettre à niveau les dépendances signalées par `pip-audit` ; audit local du 14/09/2026 : aucune vulnérabilité connue ;
- [ ] laisser la CI rejouer `pip-audit` et traiter toute nouvelle alerte ;
- [ ] tester en runtime le webhook SMS : token valide/invalide, HMAC, rate limit, absence de secret et absence d'envoi réel ;
- [ ] exécuter les scripts PowerShell sur Windows avec Docker Desktop ;
- [ ] créer une sauvegarde réelle, restaurer la paire sur une installation de test et effectuer le contrôle fonctionnel post-restauration ;
- [ ] vérifier les règles pare-feu après un changement automatique de port ;
- [ ] décider l'activation des middlewares de licence pour l'offre commerciale.

## 6. Règles de mise en production client

1. conserver PostgreSQL, jamais SQLite, pour l'exécution et les tests officiels ;
2. configurer `DEBUG=False`, `ALLOWED_HOSTS` et les origines CSRF locales ;
3. changer le mot de passe administrateur initial ;
4. activer les SMS seulement après avoir testé la passerelle et les modèles ;
5. lancer `sms_auto --dry-run` avant la première tâche réelle ;
6. conserver `.env` hors du dépôt et les sauvegardes hors de la machine ;
7. ne jamais exposer `5432`, `6379` ou le port web directement sur Internet ;
8. documenter toute restauration et contrôler les données après celle-ci.

## 7. Documents de référence

- Installation et exploitation Windows : `docs/GUIDE_DEPLOIEMENT_WINDOWS.md` ;
- procédures utilisateurs et administrateurs : `docs/GUIDE_UTILISATION_YELEN_SCHOOL.md` ;
- sauvegarde/restauration : `installer/README.txt` et les scripts `installer/backup-*`, `installer/restore-*` ;
- état de sécurité : `docs/AUDIT_SECURITE.md` ;
- archive de test : `YELEN_SCHOOL_TEST.zip` lorsqu'elle est régénérée après une modification.
