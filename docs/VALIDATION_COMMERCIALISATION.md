# Rapport de validation de commercialisation

**Date du contrôle :** 16 septembre 2026 (UTC)
**Branche :** `arena/01a06c5a-yelen-school`
**Mise à jour :** contrôles hors base relancés après durcissement des limites, des montants financiers, des motifs d'audit, de la confidentialité des signatures/tokens et des migrations historiques.
**Règle de lecture :** `PASS` signifie qu'une preuve d'exécution est disponible ; `BLOCKED` signifie que la preuve n'a pas pu être obtenue dans l'environnement de contrôle ; `FAIL` signifie qu'un contrôle exécutable a échoué.

Ce rapport ne transforme pas une indisponibilité d'environnement en validation réussie. Les contrôles locaux ne basculent jamais vers SQLite : le projet et la suite officielle restent configurés pour PostgreSQL.

## Résumé

| Gate | Objet | Statut | Motif principal |
|---|---|---:|---|
| 1 | Tests Django avec PostgreSQL et Redis | `BLOCKED` | PostgreSQL et Redis ne sont pas disponibles dans le sandbox ; l'exécution pytest a confirmé le refus de connexion. |
| 2 | Installation réelle Windows | `BLOCKED` | Aucun Windows/Docker Desktop disponible dans le sandbox. |
| 3 | Port occupé, port de remplacement et pare-feu LAN | `BLOCKED` | Le contrôle nécessite Windows et un réseau local réel ; seuls les scripts et la configuration ont été relus statiquement. |
| 4 | Sauvegarde/restauration PostgreSQL + médias sur installation séparée | `BLOCKED` | Aucun moteur Docker/PostgreSQL disponible pour créer la paire et la restaurer. |
| 5 | Contrôles après restauration : connexion, élève, paiement, PDF, média | `BLOCKED` | Dépend du gate 4 et d'une installation fonctionnelle avec PostgreSQL, Redis et les bibliothèques PDF. |
| 6 | Changement obligatoire du mot de passe initial | `BLOCKED` | Implémentation et migration présentes ; tests PostgreSQL et parcours réel restent à exécuter. |
| 7 | Licences commerciales, contrats, confidentialité, support et go-live | `BLOCKED` | Revue juridique/commerciale et critères de mise en production non approuvés par un responsable identifié. |

## Preuves exécutées dans le sandbox

Environnement : Linux, Python 3.11.2 ; environnement Python `/tmp/yelen-security-venv` avec Django 5.2.17, pytest 9.0.3 et `psycopg2` 2.9.11. `docker`, `psql`, `redis-cli`, PowerShell et `pwsh` ne sont pas disponibles.

| Commande | Résultat |
|---|---|
| `git diff --check` | `PASS` |
| `python -m compileall -q finances manuels licences` | `PASS` |
| `/tmp/yelen-security-venv/bin/python manage.py makemigrations --check --dry-run` | `PASS` : `No changes detected` pour toutes les applications ; avertissement séparé car PostgreSQL local est indisponible |
| `/tmp/yelen-security-venv/bin/pytest licences/test_license_crypto.py licences/test_license_enforcement.py core/tests/test_audit_security.py finances/tests/test_security_controls.py` | `PASS` : 29 tests ciblés, dont limite signée nulle, binding serveur, non-divulgation d'audit des signatures/tokens, RBAC/IDOR financier et montants positifs |
| `/tmp/yelen-security-venv/bin/pytest finances/tests/test_postgres_constraints.py --collect-only` | `PASS` : 10 scénarios collectés pour les contraintes CHECK PostgreSQL ; exécution réelle encore bloquée par l'indisponibilité de PostgreSQL |
| `/tmp/yelen-security-venv/bin/pytest finances/tests/test_postgres_financial_security.py --collect-only` | `PASS` : 6 scénarios collectés pour IDOR, immutabilité/annulation auditée et concurrence ; exécution réelle encore bloquée par l'indisponibilité de PostgreSQL |
| `/tmp/yelen-security-venv/bin/python manage.py check` | `PASS` sans erreur système ; avertissements WeasyPrint non bloquants sur les bibliothèques natives absentes |
| tests Django nécessitant une base, migrations SQL et concurrence | `BLOCKED` : PostgreSQL refuse la connexion sur `localhost:5432` ; SQLite n'est pas utilisé |
| test de socket `localhost:5432` et `localhost:6379` | `BLOCKED` : les deux ports refusent la connexion |

## Renforcement de l'intégrité financière

- `finances/migrations/0015_bourseeleve_bourse_montant_positif_and_more.py` ajoute des contraintes `CHECK` PostgreSQL pour les montants positifs des frais, paiements, remboursements, échéances, bourses, relances, Mobile Money et dépenses, ainsi que pour les budgets non négatifs.
- `finances/tests/test_postgres_constraints.py` couvre les mises à jour directes par `QuerySet.update()` et vérifie la présence des neuf contraintes. Ces 10 tests sont collectés mais restent `BLOCKED` tant que PostgreSQL n'est pas démarré ; la migration n'a pas été appliquée dans ce sandbox.
- `finances/tests/test_postgres_financial_security.py` collecte six scénarios DB pour les IDOR inter-établissements, l'annulation auditée, les paiements/remboursements concurrents et la confirmation Mobile Money idempotente ; leur exécution reste `BLOCKED` par le même serveur indisponible.
- La règle `DIRECTEUR_RESEAU` est explicitement séparée des vues financières détaillées d'un établissement ; son périmètre financier est le dashboard réseau agrégé.
- Les scripts Windows vérifient désormais, avant de conserver une règle existante, le port TCP, l'action `Allow`, la direction entrante, les profils `Domain,Private`, l'absence de `Public`, `RemoteAddress=LocalSubnet` et `EdgeTraversalPolicy=Block`. L'exécution PowerShell sur un poste Windows réel reste à valider.

## Modifications contrôlables du gate 6

- `accounts/migrations/0007_user_must_change_password.py` ajoute le champ persistant `must_change_password` avec défaut `False`.
- `ForcePasswordChangeMiddleware` redirige un compte marqué vers `/accounts/profile/` et laisse accessibles le profil, la déconnexion, les médias, les statiques et le healthcheck.
- `ChangeOwnPasswordForm` vérifie l'ancien secret ; la vue efface le drapeau après une modification réussie.
- `ensure_admin` exige `INITIAL_ADMIN_PASSWORD` (au moins 12 caractères) à la création, ne réinitialise plus un compte existant implicitement et réserve la réinitialisation à `--reset`.
- Les installateurs Linux et Windows génèrent un secret aléatoire, l'utilisent pour le premier démarrage, l'affichent après succès puis le retirent de `.env`.
- Le démarrage Windows ne réapplique pas la règle pare-feu lorsqu'elle correspond déjà au port ; la tâche planifiée conserve le fallback `8000` à `8005` et ne sollicite l'UAC qu'en cas de synchronisation nécessaire.

## Conditions pour clore les gates

1. Exécuter la suite officielle dans l'image Docker/CI avec PostgreSQL 15 et Redis 7, puis conserver le journal et le résultat complet.
2. Exécuter une installation sur un Windows client propre, avec Docker Desktop, et conserver la sortie de `demarrage.bat` sans secret dans les journaux.
3. Rejouer le test avec le port 8000 occupé, vérifier le port choisi, la règle `YELEN_SCHOOL_LocalWeb`, `LocalPort`, `RemoteAddress=LocalSubnet`, profils `Private,Domain` et l'absence de règle active sur `Public`.
4. Créer une paire `.dump` + archive médias, la restaurer sur une installation séparée et conserver les checksums et logs.
5. Vérifier après restauration un compte, un élève, un paiement, un PDF et un média avec des identifiants de test non sensibles.
6. Effectuer le premier login avec le secret affiché par l'installateur, constater la redirection forcée, changer le mot de passe, puis confirmer l'accès normal et le retrait du secret de `.env`.
7. Faire approuver les licences, contrats, politique de confidentialité, support/SLA, responsabilité de sauvegarde et checklist de mise en production avant d'annoncer `PASS`.
