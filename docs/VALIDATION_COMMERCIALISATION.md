# Rapport de validation de commercialisation

**Date du contrôle :** 14 septembre 2026 (UTC)  
**Branche :** `arena/01a06c5a-yelen-school`  
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

Environnement : Linux, Python 3.11.2 ; environnement Python `/tmp/yelen-venv` avec Django 5.2.17, pytest 9.0.3 et `psycopg2` 2.9.11. `docker`, `psql`, `redis-cli`, PowerShell et `pwsh` ne sont pas disponibles.

| Commande | Résultat |
|---|---|
| `git diff --check` | `PASS` |
| `python -m compileall -q accounts yelen_school` | `PASS` |
| `bash -n installer/install-local.sh` | `PASS` |
| `/tmp/yelen-venv/bin/python manage.py makemigrations accounts --check --dry-run --skip-checks` | `PASS` : `No changes detected in app 'accounts'` ; avertissement séparé car PostgreSQL local est indisponible |
| `/tmp/yelen-venv/bin/python -m pytest accounts/tests/test_password_security.py --tb=short -q` | `BLOCKED` : 7 tests collectés, tous bloqués à la création de la base de test par `connection refused` sur `localhost:5432` |
| `/tmp/yelen-venv/bin/python manage.py check` | `BLOCKED` dans le sandbox : l'import d'une vue PDF nécessite `libpango-1.0-0`, absent ; l'image Docker CI installe cette bibliothèque |
| test de socket `localhost:5432` et `localhost:6379` | `BLOCKED` : les deux ports refusent la connexion |

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
