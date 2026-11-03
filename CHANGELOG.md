# Journal des versions

Format : une entrée par version livrée (`VERSION` + tag `vX.Y.Z`). Les correctifs incrémentent le
troisième chiffre, les évolutions fonctionnelles le deuxième, les changements de rupture le premier.

## 5.47.5 — 2026-11-03

- **Bouton « Mise à jour » par archive `.zip` dans la rubrique Configuration.** La direction (*Directeur* /
  *Super Admin*) dispose désormais d'un bouton **Mise à jour** dans la rubrique **Configuration** du menu
  latéral (ainsi que d'une carte dans *Paramètres*). Au clic, la boîte de sélection de fichier s'ouvre
  immédiatement filtrée sur `.zip` ; après choix de `yelen-school-<version>.zip`, le serveur vérifie en
  mémoire/flux l'absence de traversée de chemin, le plafond de taille (300 Mo), l'en-tête Git bundle,
  l'empreinte **SHA-256** et la progression de version avant toute écriture, consigne l'acte dans `AuditLog`
  et dépose atomiquement le bundle vérifié + `demande.json` dans `mises-a-jour/`.
- **Exécution automatique côté hôte Windows sans exposer `docker.sock` et suivi en direct.** Le conteneur
  `web` monte uniquement `./mises-a-jour:/app/mises-a-jour` ; côté Windows, l'agent planifié silencieux
  `installer\appliquer-mise-a-jour-en-attente.ps1` (enregistré par `start-local.ps1` et relayé par
  `surveiller-yelen.ps1`) valide le nom du bundle et l'empreinte, exécute `mettre-a-jour.ps1 -DepuisArchive`
  (sauvegarde chiffrée, reconstruction, `/health/`, retour arrière automatique) et met à jour `demande.json`
  relu toutes les 5 s en HTMX sur `/mise-a-jour/`.
- **Outil éditeur et CLI unifiés `.zip` / `.bundle`.** `installer\outils-editeur\creer-archive-mise-a-jour.ps1`
  génère désormais `yelen-school-<version>.zip` en plus du couple `.bundle` + `.sha256`, et
  `mettre-a-jour.bat -DepuisArchive` accepte indifféremment `.zip` ou `.bundle`.
- Documentation : guide d'utilisation **§35.2** et guide de déploiement Windows **§8.2** mis à jour.
- Tests : 13 nouveaux tests dans `core/tests/test_mise_a_jour.py` + contrat PowerShell/Docker dans
  `core/tests/test_scripts_windows.py`.

## 5.47.4 — 2026-11-03

- **Clôture automatique des périodes en fin de trimestre.** Tant que personne ne cliquait sur « Clôturer »
  dans *Paramètres → Périodes*, un trimestre échu restait ouvert en écriture : un enseignant pouvait encore
  saisir ou corriger des notes après l'impression des bulletins. Désormais, la saisie reste ouverte jusqu'à
  **23 h 59 le jour de la date de fin** de la période, puis le verrou s'applique **automatiquement** dès le
  lendemain côté serveur — sans tâche planifiée ni action manuelle (saisie en ligne et hors réseau, création
  et modification d'évaluations, import Excel, appréciations, compétences APC et recalcul des moyennes).
  Consultation, conseils de classe, bulletins et exports ne changent pas ; la clôture anticipée par la
  direction reste possible.
- **Dérogation temporaire réservée à la direction, motif obligatoire et journal intégré.** Rouvrir une
  période verrouillée exige désormais un **motif** saisi dans la modale de réouverture ; la liste *Périodes*
  affiche un badge ambre **Dérogation ouverte** tant qu'elle n'est pas refermée, ainsi que le dernier acte
  enregistré (`[JJ/MM/AAAA HH:MM] Réouverture par … : motif`, puis `Clôture par …`), et la modale restitue
  l'historique complet en complément de `AuditLog`. Une réouverture accordée *avant* la date de fin laisse
  le verrou automatique agir normalement à l'échéance ; la clôture d'une année scolaire referme toute
  dérogation restée ouverte.
- **Défense en profondeur et formulaire de période.** Modifier la date de fin d'une période déjà verrouillée
  exige le droit de clôture de la direction, et toute mise à jour des dates dans *Paramètres → Périodes*
  synchronise le trimestre pédagogique correspondant ; correction au passage de l'affichage des dates ISO et
  du bandeau d'erreur dans la modale `periode_form.html`.
- Documentation : guide d'utilisation **§3.4** mis à jour (clôture automatique, dérogation motivée,
  refermeture).
- Tests : 5 nouveaux tests de parcours dans `pedagogie/tests/test_cloture_automatique.py` (ouverture jusqu'au
  dernier jour puis blocage automatique le lendemain sur toutes les écritures, modale et motif obligatoire,
  journalisation ouverture/refermeture, refus hors direction et blocage du contournement par `date_fin`,
  maintien de la clôture automatique après réouverture anticipée, refermeture lors de la clôture d'année).

## 5.47.3 — 2026-11-02

- **Mise à jour sans Internet.** L'école ne pouvait se mettre à jour que par GitHub : une coupure de
  l'opérateur ou une panne de DNS (`Could not resolve host: github.com`) bloquait tout, la production
  restant sur sa version du moment. `mettre-a-jour.bat -DepuisArchive <archive>` applique désormais une
  archive de version fournie par l'éditeur, **sans réseau**.
- L'archive est un bundle git : elle emprunte **exactement le même chemin** que GitHub (`fetch` puis
  avance rapide), donc la sauvegarde préalable, le contrôle `/health/` et le **retour arrière automatique**
  restent inchangés. Aucune nouvelle logique de copie de fichiers à maintenir.
- **Empreinte SHA-256 obligatoire**, vérifiée *avant* la sauvegarde et avant toute écriture : archive
  absente, incomplète, altérée ou mal formée → arrêt immédiat, « rien n'a été modifié ». Puis
  `git bundle verify` contrôle que l'archive est bien une mise à jour YELEN SCHOOL applicable sur la
  version installée.
- Panne réseau : le message d'erreur indique maintenant la solution hors ligne au lieu de laisser
  l'administrateur devant « GitHub injoignable ».
- Nouvel outil éditeur `installer\outils-editeur\creer-archive-mise-a-jour.ps1` : produit
  `yelen-school-<version>.bundle` (26 Mo environ) et son `.sha256`, refuse un dépôt modifié, ne livre rien
  si `git bundle verify` échoue, et affiche les commandes à communiquer.
- Guide de déploiement **§8.2** (nouvelle section) : ce que reçoit l'école, les cinq refus prévus avec la
  cause et la conduite à tenir ; anciens §8.2 et §8.3 deviennent §8.3 et §8.4.
- Éprouvé de bout en bout : archive d'une version publiée appliquée sur un clone en 5.47.2 → 5.47.3 sans
  réseau, second passage « déjà à jour » sans effet, et cinq cas de refus (archive absente, empreinte
  absente, mal formée, incorrecte, bundle étranger).
- Tests : 3 garde-fous dans `core/tests/test_scripts_windows.py` — l'empreinte est vérifiée avant la
  sauvegarde et avant la fusion, le bundle utilise `git -C`, le chemin GitHub reste intact, et l'archive
  éditeur porte une empreinte au format `sha256sum`.

## 5.47.2 — 2026-11-02

- **Une sauvegarde jamais restaurée n'est pas une sauvegarde.** Nouveau `installer\tester-restauration.ps1` :
  il importe la dernière sauvegarde (chiffrée ou non) dans une base temporaire `<DB_NAME>_test_restauration`,
  vérifie le nombre de tables et les effectifs (élèves, inscriptions, paiements), puis supprime cette base.
  **La production n'est pas touchée** — l'application reste en marche, aucune donnée n'est remplacée.
  Le résultat est consigné dans `backups\restauration.log` et apparaît dans *Exploitation*, nouvelle carte
  **Restauration testée** ; sans essai depuis plus de 120 jours, une alerte y figure et le relais quotidien la reprend.
- **Surveillance extérieure documentée** (guide de déploiement §9.6) : les alertes de la veille sont internes,
  elles ne peuvent pas prévenir si le serveur est éteint. Procédure complète, pas à pas, avec deux services
  gratuits — UptimeRobot sur `/health/` (le serveur répond-il ?) et Healthchecks.io sur la sauvegarde
  (a-t-elle eu lieu ?), avec la commande `&& curl` à ajouter à la tâche planifiée.
- **Mesures de référence** (guide de déploiement §9.4/§9.6, audit P1-9) : commande `manage.py mesure_reference`
  qui chronomètre les six écrans du quotidien, sur les données réelles, et peut servir de garde-fou planifié
  (`--seuil-ms`, `--json`). Mesuré sur 1 500 élèves (SQLite, 5 passes, médiane) :

  | Écran | Durée | Requêtes SQL | Page |
  |---|---|---|---|
  | Accueil | 28 ms | 25 | 66 Ko |
  | Élèves | 43 ms | 13 | 225 Ko |
  | Évaluations (saisie des notes) | 91 ms | 15 | 148 Ko |
  | Redevables | 325 à 402 ms | 16 | 2 161 Ko |
  | Paiements | 29 ms | 10 | 165 Ko |
  | Bulletins | 10 ms | 12 | 59 Ko |

  La liste des redevables (2,1 Mo de HTML pour 1 500 lignes) est la plus lente et la plus variable : elle reste
  sous le seuil de 2 000 ms, mais c'est la page à paginer en premier si l'effectif double.
- Documentation : guide d'utilisation §3.6 (carte « Restauration testée »), guide de déploiement §9.6 et §9.7
  (procédure d'essai trimestriel avec sortie attendue et consignation).
- Tests : 11 nouveaux (lecture du journal de restauration, alertes d'absence et d'ancienneté, lignes
  illisibles, sortie tableau et JSON de la commande, seuil, utilisateur inconnu).

## 5.47.1 — 2026-11-02

- **Couverture des modules sensibles.** Les écrans qui engagent une décision (conseil de classe, transfert,
  dépense, licence, prédiction) étaient les moins testés. Couverture des vues, mesurée module par module :

  | Module | Avant | Après |
  |---|---|---|
  | `pedagogie/views/predictions.py` | 25 % | **100 %** |
  | `viescolaire/views/conseils.py` | 36 % | **100 %** |
  | `finances/views/budget.py` | 39 % | **100 %** |
  | `inscriptions/views/transferts.py` | 40 % | **98 %** |
  | `licences/views.py` | 57 % | **100 %** |

- Nouveaux tests de parcours (77 tests) : risque de décrochage (filtres, recalcul unitaire, recalcul global,
  fragment htmx, PDF), prédictions (cycles à examen, pronostics, calcul POST, PDF), conseils de classe
  (création sans les abandons, décisions et mentions, PV PDF), appels de décision (contestabilité, instruction,
  modification de la décision, verrouillage), budget (catégories, dépenses, refus de dépassement, séparation
  saisie / approbation, trésorerie, export Excel), transferts (demande, approbation qui clôt le dossier et
  trace le parcours, refus, dossier PDF), licences (création, activation par jeton, renouvellement, révocation,
  outils de développement désactivés en production).
- **Aucun code de production modifié** : les seules lignes non couvertes sont les replis « WeasyPrint absent »
  des transferts (`import` en échec). Deux comportements réels ont été figés au passage : le saisisseur ne
  valide pas sa propre dépense, une échéance réglée n'apparaît plus dans le reste à payer d'un transfert.

## 5.47.0 — 2026-11-02

- **Listes lisibles sur téléphone.** Les tableaux de liste (élèves, paiements, personnel, classes, reçus,
  redevables, commandes, documents…) n'imposent plus de défilement horizontal : **sous 768 px**, chaque ligne
  devient une carte — nom en tête, informations avec leur libellé de colonne, actions en bas. Mesures sur la
  liste des élèves à 390 px : tableau de **809 px dans 356 px visibles avant**, **356 px sans débordement
  après** ; paiements 941 px → 356 px ; personnel 860 px → 356 px. Sur ordinateur, aucun changement.
- Mécanique unique et réversible : `static/js/tableaux_mobile.js` reprend les libellés du `<thead>` (aucun
  gabarit de liste modifié), `static/css/yelen.css` met la ligne en carte. Sans JavaScript, le tableau reste
  défilant — aucune régression possible.
- **Exclusions** : les matrices (`table-stats`, `edt-table`) et les tableaux marqués `data-cartes="non"` — la
  matrice des bulletins par classe et par trimestre reste un tableau. À l'impression, les listes reprennent
  leur forme tabulaire.
- Guide §18.9 ; tests : 4 garde-fous statiques et un parcours navigateur à 390 px (cartes, libellés, titre
  unique, absence de débordement, matrice préservée).
- Vérifié sans modification : la **saisie de notes sur téléphone** est déjà adaptée (champ de 88 × 52 px,
  police 22,4 px, clavier décimal, boutons Absent / Dispensé, enregistrement hors réseau).

## 5.46.9 — 2026-11-01

- **Guide §9.5 : inscription des enseignants détaillée.** La clé se saisit **dans l'application**
  (écran de connexion → menu ⋯ → « Use an auth key »), jamais dans la page web ; l'application Windows n'a
  pas de champ clé (`tailscale up --authkey`). Ajout de deux consignes qui évitent une réinstallation :
  **ne jamais cocher *Ephemeral*** (l'appareil est supprimé à la première déconnexion) et **désactiver
  l'expiration de clé** de chaque appareil (180 jours par défaut, sinon déconnexion en pleine année scolaire).
- Tableau de lecture de la liste *Machines* : pas de badge = durable, **Éphémère** = à refaire, **Cheminée** =
  Funnel actif (uniquement sur le serveur) ; piste des **tags** pour une traçabilité stricte des appareils.
  Dépannage : fenêtre « Choisir une clé d'accès » (passkey) et appareil qui disparaît de la liste.

## 5.46.8 — 2026-11-01

- **Consigne de redémarrage contradictoire dans `activer-acces-distance.bat`.** Le lanceur affichait
  « Redemarrez le serveur (`demarrer-autonome.bat`) » après avoir imprimé, une ligne plus haut, la consigne
  propre au mode d'installation (`demarrage.bat` en Docker). En production Docker, suivre la seconde relançait
  le serveur autonome. Le lanceur renvoie désormais à la consigne affichée par le script, qui seule connaît le
  mode. Exemple d'entrée Tailscale Serve ajouté à son en-tête.

## 5.46.7 — 2026-11-01

- **Accès du personnel par Tailscale Serve, avec port.** `activer-acces-distance.bat` accepte désormais
  `-Domaine <serveur>.<tailnet>.ts.net:8443 -EnvSeulement` : le nom part dans `ALLOWED_HOSTS` **sans** le port
  et l'origine complète, port compris, dans `CSRF_TRUSTED_ORIGINS` — sans quoi chaque enregistrement de notes
  était refusé (`403 CSRF verification failed`). Port hors limites ou non numérique : refusé avant toute
  écriture. `-Desactiver` avec port ne retire que l'origine avec port : une entrée Funnel sur le 443 du même
  nom reste utilisable.
- Cas d'usage : **saisie des notes de fin de trimestre** par les enseignants, sur un canal privé (réseau
  Tailscale), sans plafond de débit et sans exposition publique ; les parents gardent le Funnel sur le 443.
- Guide de déploiement **§9.5** : deux configurations (personnel seul / les deux en parallèle), inscription des
  enseignants (offre gratuite : 3 utilisateurs, 100 appareils — un compte « école » et une clé
  d'authentification), restriction du tailnet à la machine du serveur, charge attendue, dépannage.
- Tests PowerShell de `activer-acces-distance.ps1` : section « Port Tailscale Serve » (11 vérifications
  supplémentaires).

## 5.46.6 — 2026-11-01

- **Messages reçus : lisibles sur téléphone.** La boîte n'est plus un tableau de sept colonnes à défilement
  horizontal : chaque SMS occupe une carte pleine largeur (numéro et date en tête, famille identifiée,
  texte complet, badges compacts, actions sous le message). Sur téléphone la colonne « Message » tombait à
  **un caractère par ligne** (tableau de 934 px dans 356 px visibles, lignes de 235 px) ; le message occupe
  désormais 311 px de large et les cartes s'empilent sans défilement latéral. Sur ordinateur, le texte passe
  de 158 px à 1024 px, les trois actions de chaque message tiennent sur une ligne alignée à droite et le
  badge « Message libre » n'est plus répété quand la vue ne contient que des messages libres.
- Guide d'utilisation §32.6 : présentation en cartes décrite ; test de non-régression sur la structure de la
  liste (une carte par message, aucun tableau à défilement).

## 5.46.5 — 2026-11-01

- **Consigne de redémarrage corrigée** : `demarrer.bat` n'existe pas — le lanceur Docker est **`demarrage.bat`**
  (`demarrer-autonome.bat` ne concerne que le mode sans Docker). Corrigé dans le script d'accès à distance, les
  deux guides et le journal ; un test interdit désormais qu'un document cite un lanceur absent de la racine.
- Guide de déploiement §9.4 : Tailscale Funnel présenté comme **mode recommandé sans domaine**, avec les
  vérifications (`tailscale funnel status`, `/health/` local) et le rappel du redémarrage obligatoire après
  modification du `.env` (sinon `400 Bad Request`).
- Mise en service réelle le 01/11/2026 : portail parents joignable en 4G et en Wi-Fi via `https://<serveur>.<tailnet>.ts.net`.

## 5.46.4 — 2026-11-01

- **Accès à distance sans nom de domaine.** `activer-acces-distance.bat -Domaine <nom> -EnvSeulement` autorise
  seulement le nom public dans `.env` (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `ACCES_DISTANCE_DOMAINE`) sans
  installer de service Cloudflare : utilisable avec un accès assuré autrement — procédure **Tailscale Funnel**
  ajoutée au guide de déploiement §9.4, pour les cas où le domaine appartient à un compte Cloudflare
  inaccessible (zone « Serveurs de noms invalides »). Tests PowerShell : 36 vérifications.

## 5.46.3 — 2026-11-01

- **Parcours navigateur : plus d'échec intermittent « 500 » sur les pages lourdes.** La base de test d'un
  SQLite Django est `file:memorydb_default?mode=memory&cache=shared` : en mémoire **partagée**, SQLite verrouille
  au niveau de la **table** et non de la base. Deux requêtes simultanées — une page et les compteurs htmx
  qu'elle déclenche (`/notifications/badge/`, `/communication/messages-recus/compteur/`) — se bloquent donc sur
  `django_session`, avec `database table is locked` : `busy_timeout` n'y change rien (code SQLITE_LOCKED, pas
  SQLITE_BUSY). Reproduit hors navigateur : la même lecture réussit sur fichier + WAL, échoue en mémoire
  partagée. Les parcours utilisent désormais une base de test **sur fichier** (`core/tests/e2e/test_parcours.py`,
  via `django_db_modify_db_settings`), comme la production : trois exécutions consécutives vertes.
- **Sans effet en production** : une école utilise un fichier SQLite en WAL (`core/db_sqlite.py`) ; la mémoire
  partagée n'existe que dans les tests. Les 500 observés en CI n'ont jamais concerné les utilisateurs.

## 5.46.2 — 2026-11-01

- **Le contrôle de l'adresse publique ne confond plus un autre site avec YELEN.** `Test-PointDeSante` lisait
  le seul code HTTP : une page étrangère répondant 200 (page générique du domaine, `*.domaine`) était annoncée
  « [OK] ». Le script exige désormais le contenu de `/health/` (`"status"`) et distingue trois états : YELEN
  répond, **un autre site répond** (message rouge + consigne du tunnel), rien ne répond. Même exigence sur le
  port local, pour repérer un port occupé par une autre application. Tests PowerShell : 31 vérifications.

## 5.46.1 — 2026-11-01

- **Accès à distance sur une installation Docker.** `activer-acces-distance.ps1` reconnaît le mode de
  déploiement : si le conteneur `web` tourne (`docker compose … ps -q web`), il lit le port dans
  `YELEN_HTTP_PORT` et demande de relancer par **`demarrage.bat`** — les conteneurs doivent être recréés pour
  relire `.env`, un simple redémarrage ne suffit pas. En mode autonome, rien ne change (`PORT`,
  `demarrer-autonome.bat`). Guide de déploiement §9.4 complété (redémarrage selon le mode).

## 5.46.0 — 2026-11-01

- **Accès à distance du portail parents.** Nouveau `activer-acces-distance.bat` et
  `installer/activer-acces-distance.ps1` : le serveur publie le portail parents sur
  `https://yelenschoola.nayxus.com/` par un **tunnel Cloudflare sortant** — aucun port ouvert sur la box,
  HTTPS et certificat fournis, base de données jamais exposée. Le script installe `cloudflared` au besoin,
  autorise le nom public dans `.env` (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `ACCES_DISTANCE_DOMAINE`),
  installe le service Windows avec le jeton du tunnel (jamais écrit dans un fichier), puis contrôle
  `/health/` en local et sur l'adresse publique. `-Desactiver` referme l'accès ; relancer est sans effet
  de bord.
- **Correctif : le serveur autonome ignorait `.env`.** `demarrer-autonome.bat` lance `waitress-serve
  yelen_school.wsgi`, qui ne passe pas par `manage.py` : `SECRET_KEY`, `ALLOWED_HOSTS` et
  `CSRF_TRUSTED_ORIGINS` n'étaient pas lus (clé régénérée à chaque démarrage, donc sessions perdues ;
  nom public refusé en 400). Le lanceur charge désormais `.env` dans l'environnement du processus, comme
  `demarrer-autonome.sh` le faisait déjà, et ajoute l'adresse locale détectée aux hôtes autorisés.
  **Seule conséquence : les sessions ouvertes sont à renouveler une fois.**
- Guide de déploiement §9.4 (procédure, dépannage, sécurité) et guide d'utilisation §19.7.
- Tests : `installer/tests/test-acces-distance.ps1` (22 vérifications, exécuté dans l'intégration continue).

## 5.45.5 — 2026-10-31

- **Barre latérale : les sous-menus sont classés par ordre alphabétique.** Dans les treize menus
  (Inscriptions, Pédagogie, Bulletins, Présences, Examens, Vie scolaire, Personnel, Finances, Vacations,
  Communication, Manuels, Documents, Paramètres), les entrées de chaque sous-menu apparaissent désormais
  de A à Z, selon l'ordre alphabétique **français** : accents et casse sont ignorés (« Élèves » à E,
  « Évaluations » entre « Enseignements » et « Matières »), « & » compte comme séparateur (« Bourses &
  Aides » à Bourses).
- L'ordre des menus de premier niveau ne change pas ; aucun lien n'apparaît ni ne disparaît. Les entrées
  conditionnelles suivent la même règle : « Mes cours » (réservé aux enseignants) est sortie de l'imbrication
  « Appels » sans changer sa condition d'affichage, et « Paie du mois » (même droit que « Salaires ») a été
  séparée pour être triable.
- Vérifié : visibilité strictement identique pour les 8 comptes de démonstration (494 entrées), rendu réel
  contrôlé dans le navigateur ; nouveau test `core/tests/test_menu_alphabetique.py` (ordre lu sur la page
  rendue, les 13 sous-menus).

## 5.45.4 — 2026-10-31

- **Guide d'aide : cliquer une entrée du sommaire n'affichait pas la section.** Le script du sommaire appelait
  `scrollIntoView` sur le lien devenu actif ; cette méthode fait défiler **tous** les conteneurs de la page,
  y compris le document. Le guide mesurant ~255 000 px et le sommaire commençant à ~230 px, chaque titre
  observé ramenait la page en haut du sommaire : la section visée restait à 10 000 px et le clic semblait
  sans effet. Le sommaire fait désormais défiler son propre cadre (`scrollTop`), jamais la page.
- Sur cette page, les ancres amènent la section **immédiatement** (`html:has(.aide-layout) { scroll-behavior:
  auto }`) : le défilement « doux » parcourait des dizaines de milliers de pixels à chaque clic.
- Vérifié : ancre dans l'URL, clic dans le sommaire (305 entrées), liens de la table des matières du guide
  (301 liens, 0 cassé) ; défilement manuel stable. Nouveau parcours navigateur (6ᵉ) : il échoue sur le code
  d'origine, passe après correction.

## 5.45.3 — 2026-10-31

- **Disposition des boutons des en-têtes de page** (liste des élèves, et les 37 écrans qui partagent le même
  gabarit). Trois défauts corrigés, sans toucher aux gabarits :
  - sous 1 366 px, les cinq boutons du bandeau « Gestion des Élèves » sortaient de l'écran (633 px de large
    dans 480 px de place) : le bloc se replie désormais sous le titre, les boutons passant à la ligne ;
  - sur téléphone, le titre et les boutons débordaient horizontalement (page de 390 px élargie) : les actions
    occupent la largeur, les exports se rangent trois par ligne, l'action principale reste intacte à côté ;
  - une page dont l'en-tête ne contient que des boutons ne subit plus la largeur du bloc de titre.
- CSS seulement (`static/css/yelen.css`) : aucune modification de gabarit, aucun test modifié.

## 5.45.2 — 2026-10-31

- **Dossier documentaire d'un élève (page « Dossier documentaire ») : erreur 500 corrigée.** Le gabarit
  écrivait `{{ d.signataire_nom|default:d.signataire }}` ; Django évalue l'argument d'un filtre, et un
  `Document` n'a pas d'attribut `signataire` (le nom y est un instantané). La page échouait dès qu'un document
  généré — bulletin, reçu, certificat — figurait au dossier ; elle affiche désormais le tiret cadratin.
- Même défaut corrigé là où le gabarit citait un objet facultatif (`SET_NULL`) comme argument de `default:` :
  cahier de textes sans auteur, page d'un transfert sans demandeur. Les deux passent par `{% firstof %}`, qui
  tolère une variable absente ; les autres occurrences du projet (63 relevées) ne citent que des objets
  obligatoires. Couverture : un test par page, chacun vérifié en échec sur le gabarit d'origine.

## 5.45.1 — 2026-10-31

- `reinitialiser_demo` ne vide plus la base : la commande s'appuie sur `charger_demo --reset` et supprime en
  plus les élèves restés sans inscription (traces d'un visiteur). Sous PostgreSQL, un paiement comptabilisé
  est immuable : la commande s'arrête avec un message explicite au lieu d'échouer sur le vidage.
- `docker-compose.demo.yml` passe en SQLite (volume Docker), comme l'installation autonome : la remise à zéro
  nocturne redevient possible. Services `db`/`redis` retirés, `entrypoint.demo.sh` n'utilise plus
  `--sans-vidage` ; `.env.demo.example` et guide §39 alignés.

## 5.45.0 — 2026-10-31

### Offre hébergée et instance de démonstration (chantier B8)

Une instance d'essai publique peut désormais tourner sur un VPS avec **la même image que l'installation
d'école**, sans qu'aucune donnée ni message n'en sorte.

- `DEMO_MODE=true` (réglage, `.env.demo`) : commutateur unique, vérifié aux quatre points de sortie —
  `core.sms.sms_actifs()` (aucun SMS, rien n'est mis en file), `core.notifications` (e-mail retenu),
  `core.push.notifier()` (aucune poussée), `finances.paiements_mobiles.cinetpay_configure()` (demande Mobile
  Money réputée non configurée, aucun appel sortant). Détail : `core/mode_demo.py`.
- Bandeau **DÉMONSTRATION** fixe sur toutes les pages et sur l'écran de connexion, y compris à l'impression ;
  `/health/` expose `"demo": true`.
- Commande **`reinitialiser_demo`** : reconstruit l'établissement de démonstration (C4) et efface les traces
  des visiteurs ; refuse de s'exécuter hors mode démonstration, où elle effacerait les données d'une école.
- `docker-compose.demo.yml` + `entrypoint.demo.sh` + `.env.demo.example` : même image que l'école, base SQLite
  dans un volume, chargement du jeu au premier démarrage, service `reset` pour la remise à zéro nocturne.
- Garde-fou de configuration : `DEMO_MODE=true` avec `LICENSE_ENFORCEMENT=true` empêche le démarrage.
- Tests (14), guide §39.

## 5.44.2 — 2026-10-31

- Tests : le quota de connexion de l'API (5 tentatives par minute, tenu par le cache) n'était pas remis à zéro
  entre deux tests. Sous Redis — job CI « mode serveur » — les tentatives des tests d'API s'additionnaient et un
  test d'authentification réussie recevait 429. Le cache est vidé avant chaque test quand il n'est pas
  transactionnel (`conftest.py::quota_api_isole`).

## 5.44.1 — 2026-10-31

- `documents/test_signataires.py` : le cycle de test utilisait le code `PRIMAIRE` alors que
  `Cycle.code` est limité à 4 caractères (`PRES`, `PRIM`, `POST`, `SEC`). SQLite tolérait la valeur,
  PostgreSQL la refuse : la CI serveur échouait. Code corrigé en `PRIM`.

## 5.44.0 — 2026-10-31

### Découpage des gros fichiers et styles du gabarit (chantier C2)

Aucune ligne de code métier n'a été réécrite : les fichiers ont été répartis par domaine, chaque nom reste
importable à son ancienne adresse (réexport dans `__init__.py`).

| Avant | Après | Contenu |
|---|---|---|
| `parametres/models.py` (2 081 l.) | paquet `parametres/models/` — 8 modules | `etablissement`, `structure`, `annee`, `evaluation`, `tarifs`, `documents`, `vie_scolaire`, `droits` |
| `core/views.py` (1 766 l.) | paquet `core/views/` — 8 modules | `accueil`, `audit`, `notifications`, `portail`, `sms`, `exploitation`, `pwa`, `systeme` |
| `inscriptions/views.py` (1 634 l.) | paquet `inscriptions/views/` — 7 modules | `eleves`, `inscriptions`, `documents`, `rentree`, `parcours`, `transferts`, `preinscriptions` |
| `core/templates/core/base.html` | gabarit sans style en ligne ni bloc `<style>` | styles déplacés dans `static/css/yelen.css` (section « structure du gabarit de base ») |

- Chaque module ne reçoit que les imports qu'il utilise ; les dépendances internes au paquet sont explicites
  (`from .tarifs import RubriquePaiement`), les imports relatifs au module d'origine remontent d'un cran.
- `base.html` : les 15 attributs `style="…"` et le bloc `<style>` du sous-menu sont devenus des classes
  (`.sb-item-modern.is-info`, `.topbar-mobile`, `.app-footer`, `.sidebar-overlay`…). Le gabarit n'émet plus
  de CSS, la feuille reste mise en cache et soumise à la CSP.
- Tests : deux cibles de patch PDF suivent leur module (`inscriptions.views.eleves` / `.documents`) ; suite
  complète 1 530 tests, parcours navigateur 5/5, couverture 82,04 %.

## 5.43.0 — 2026-10-31

### Tests des modules transverses et deux défauts d'API corrigés (chantier C3)

- **Corrigés** — `api/urls.py` : `/api/annees/<id>/periodes/` était déclarée en `<int:annee_id>` alors que les
  clés de l'application sont des UUID : la route répondait 404 quelle que soit l'année demandée.
- **Corrigés** — `api/serializers.py` : `MoyenneGeneraleSerializer`, `PaiementSerializer` et
  `PresenceSerializer` déclaraient des champs inexistants (`nb_absences`, `nb_retards`, `statut`,
  `justifiee`) et une relation `inscription.resultats_trimestre` qui n'existe pas ; toute réponse contenant
  une moyenne, un paiement ou une présence levait une erreur 500. Les champs réels les remplacent
  (`moyenne_sur_20`, `nb_matieres_*`, `appreciation`, `mode_paiement`, `reference`, `minutes_retard`,
  `observations`).
- Tests (66) — vacations (validation des heures, bulletins mensuels et PDF, formulaire de contrat),
  établissements (fiche de configuration, périmètre du réseau, groupes, export XLSX), signataires de PDF
  (détection du cycle, replis, mono/multi-signataires, signature scannée), API (rotation et révocation des
  jetons, cloisonnement de chaque endpoint, permissions, licences absente/inactive) et manuels.
- Couverture des fichiers visés : `api/views.py` 78 → 98 %, `etablissements/views.py` 65 → 96 %,
  `vacations/views.py` 72 → 95 %, `manuels/views.py` 98 → 100 %, `signataire_tags.py` 77 → 92 %.
  Suite complète : 1 530 tests, couverture globale 81,90 %.

## 5.42.1 — 2026-10-31

- `charger_demo --reset` : sous PostgreSQL, la suppression de l'établissement cascade vers des paiements
  comptabilisés que le trigger d'immuabilité (`finances/0016`) refuse de supprimer. La commande traduit l'erreur
  SQL en message explicite (« choisissez un autre code ou une base d'essai SQLite ») ; sous SQLite (installation
  autonome) le comportement est inchangé. Tests (7), dont la traduction du garde-fou et le cas PostgreSQL.

## 5.42.0 — 2026-10-31

### Parcours navigateur vérifiés à chaque livraison (chantier C1)

- `core/tests/e2e/test_parcours.py` : cinq parcours dans un vrai navigateur (Chromium/Playwright) sur un
  serveur de test et le jeu de démonstration — connexion, encaissement avec reçu PDF, saisie de notes, bulletin
  PDF, portail parent. Balises `pytest.mark.e2e`, exclues de la suite ordinaire (`addopts`), ignorées sans
  Playwright.
- Job CI **`parcours`** : installation de Chromium (`python -m playwright install --with-deps chromium`),
  migrations, manifeste statique, puis `pytest -m e2e`.
- `requirements/dev.txt` : `playwright` ; `pytest.ini` : marqueur `e2e` et exclusion par défaut.
- `core/management/commands/charger_demo.py` : la fiche du personnel porte l'adresse du compte (l'enseignant
  titulaire est reconnu par son e-mail — `core.utils.get_membre_personnel`).
- Tests (5), guide §38.2.

## 5.41.0 — 2026-10-31

### Jeu de données de démonstration (chantier C4)

- `core/management/commands/charger_demo.py` : un établissement complet en une commande — identité et agrément
  (catégorie 2, zone 1), année en cours et année précédente, 3 cycles et 8 classes, statuts, 4 rubriques et tarifs
  conformes aux plafonds, 8 fiches de personnel et 10 comptes, élèves inscrits sur deux années, matières,
  enseignements, devoirs et compositions du 1er trimestre, notes, moyennes et rangs (via `CalculateurMoyenne`),
  paiements avec reçus, signataires des documents.
- Options `--eleves`, `--etablissement`, `--reset` ; commande **rejouable sans doublon**, limitée à l'établissement
  qu'elle crée.
- `core/demarrage.py` : l'étape « Signataires des documents » de l'assistant est désormais **calculée** (elle était
  toujours affichée comme non faite) ; un établissement de démonstration atteint 8/8.
- Tests (6), guide §3.13.

## 5.40.0 — 2026-10-31

### Export comptable SYSCOHADA

- `finances/export_comptable.py` : journal de caisse des recettes (571 Caisse / 521 Banques ↔ 706 Prestations de
  services, 707 Produits accessoires pour cantine, transport, internat) et journal des dépenses validées (661, 604,
  624, 605, 628, 625, 633, 658 → 571/521), récapitulatif débit/crédit/solde par compte ; comptes paramétrés dans
  `COMPTES_DEPENSES`.
- Vue `finances:export_comptable` (`/finances/export-comptable/`), fichier XLSX `ExcelExport`, bouton sur la page
  Dépenses, sélecteur d'année.
- Tests (2), guide §9.37.

## 5.39.0 — 2026-10-31

### Historisation pluriannuelle des indicateurs

- Modèle `core.IndicateurAnnee` (migration `core.0008`) : une ligne par établissement et par année — effectif
  (dont filles / garçons), moyenne générale, taux de réussite, de recouvrement et d'absentéisme, détails chiffrés,
  date de calcul.
- `core/indicateurs.py` : `calculer`, `mettre_a_jour` (idempotent) et `evolution` (écarts par rapport à l'année
  précédente) ; commande `historiser_indicateurs [--etablissement <uuid>]`.
- Page *Pilotage → Évolution pluriannuelle* (`core:indicateurs_evolution`, direction) : tableau des années, écarts
  colorés, bouton de recalcul ; lien depuis le tableau de bord direction.
- Tests (4), guide §3.12.

## 5.38.1 — 2026-10-31

- `core/demarrage.py` : `except NoReverseMatch` au lieu de `except Exception` (test « aucun except silencieux »).

## 5.38.0 — 2026-10-31

### Assistant de première configuration

- `core/demarrage.py` : les 8 étapes de mise en route (identité, année courante, cycles et classes, rubriques et
  tarifs, personnel, comptes de gestion, élèves, signataires) avec leur état **calculé dans la base** et le lien
  direct vers l'écran concerné ; fonction `avancement` (fait / total / pourcentage).
- Page `/demarrage/` (`core:demarrage`, réservée aux rôles accédant aux paramètres), barre de progression, état
  « Fait » / « À faire », carte d'accès dans *Paramètres*.
- Tests (2), guide §3.11.

## 5.37.1 — 2026-10-31

- Tests du dossier documentaire : import inutilisé retiré (ruff F401, job « Lint » de la CI).

## 5.37.0 — 2026-10-31

### Dossier documentaire par élève

- Modèle `inscriptions.PieceDossier` (migration `0023`) : type de pièce, précision, fichier PDF/image validé
  (`core.validators.validate_piece_jointe`, 5 Mo), inscription, déposant ; sous `media/eleves/dossier/`.
- Page *fiche élève → Dossier documentaire* (`inscriptions:eleve_dossier`) : **pièces déposées** (date, déposant,
  téléchargement, suppression) et **documents délivrés** (type, numéro, année, date d'émission, signataire, agent,
  PDF). Dépôt/téléchargement/suppression isolés par établissement.
- Export du dossier (§3.10) enrichi des pièces ; leurs fichiers sont supprimés à l'anonymisation.
- Tests (4), guide §4.4.

## 5.36.0 — 2026-10-31

### Portail élève au niveau du portail parent

- `/portail/eleve/` sert désormais les **mêmes vues et gabarits** que le portail parent (configuration `PORTAILS`
  dans `core/views.py`, navigation `core/partials/portail_nav.html`) : accueil, vie scolaire, cahier de textes,
  bulletins, notifications ; l'ancien gabarit `portail_eleve.html` est supprimé.
- **PWA élève** : manifeste `/manifest-eleve.json`, service worker `/sw-eleve.js` (cache `yelen-eleve-v1`),
  `static/js/pwa.js` lit `data-pwa-sw` / `data-pwa-scope` sur `<body>` ; notifications push via le partiel commun.
- **Bulletins** : consultation en lecture seule `portail_bulletin` (`/portail/{parent,eleve}/bulletins/<pk>/`) ;
  **Documents délivrés** (certificats, attestations…) listés sur la page Bulletins et téléchargeables par
  `portail_document` (`/portail/{parent,eleve}/documents/<pk>/`), restreints aux élèves liés au compte.
- Page Vie scolaire : sections **Notes récentes** et **Moyennes par matière** (parent et élève) ; le dépôt de
  justificatif reste réservé au parent.
- `notifier_bulletin_publie` notifie aussi le compte élève (lien `/portail/eleve/bulletins/`, sans SMS).
- Guide §19.6 (et §9.21 renvoyé).

## 5.35.0 — 2026-10-31

### Cycle de vie des données personnelles (loi n° 001-2021/AN)

- *Paramètres → Données personnelles* : **durée de conservation** (10 ans par défaut après la dernière année
  d'inscription), responsable du traitement, compte et aperçu des élèves sortis, bouton **Anonymiser** (confirmation,
  journal d'audit), **registre des traitements** (`parametres.PolitiqueDonnees`, migration 0044).
- Anonymisation (`core/donnees_personnelles.py`) : identité, contacts, parents/tuteur, santé, photo, justificatifs
  d'absence et PDF archivés (fichiers supprimés), payeur Mobile Money, pré-inscriptions expirées ; comptes parent/élève
  sans élève identifiable fermés ; inscriptions, notes et paiements conservés anonymes (`Eleve.anonymise_le`,
  migration `inscriptions.0022`).
- Fiche élève → **Exporter le dossier** (JSON complet, journalisé) : `inscriptions:eleve_export_donnees`.
- Commande `anonymiser_donnees [--dry-run]` pour une exécution planifiée.
- Guide §3.10.

## 5.34.1 — 2026-10-31

- Migration `parametres.0042` : le code du type de document « Attestation de conformité tarifaire » dépassait les
  20 caractères de `TypeDocument.code` (refusé par PostgreSQL, toléré par SQLite) → code `CONFORMITE_TARIFAIRE` ;
  migration `0043` corrige les installations SQLite déjà migrées.

## 5.34.0 — 2026-10-31

### Grille tarifaire réglementaire (décret n° 2026-0761)

- *Identité Établissement* : **catégorie réglementaire** (1 à 3) et **zone d'implantation** ; *Rubriques* : case
  **Frais plafonnés** (décochée pour cantine, transport, internat et frais autorisés par la tutelle).
- Grille des plafonds par cycle × catégorie × zone (`parametres/plafonds.py`, arrêté n° 2026-101 du 10/07/2026) ;
  **refus à la saisie** d'un tarif qui porterait le total plafonné d'une classe/statut au-delà du plafond, message
  explicite ; établissement non classé = aucun contrôle.
- Page *Tarifs → Conformité réglementaire* (total plafonné, plafond, écart, hors plafond par classe et statut) et
  **attestation de conformité tarifaire** PDF A4, délivrée seulement si tout est conforme, signée par le signataire
  du nouveau type de document (migration `parametres.0042`). Tests (5), guide §3.9.

## 5.33.1 — 2026-10-31

- CI : le paquet `libgdk-pixbuf-xlib-2.0-0` n'existe plus sur l'image `ubuntu-latest` (Ubuntu 26.04) et WeasyPrint 70
  ne l'utilise pas — retiré des deux jobs (`libpangoft2-1.0-0` ajouté). L'image Docker (Debian) est inchangée.

## 5.33.0 — 2026-10-31

### Remise en ordre du guide, guide de démarrage rapide, favicon

- **Numérotation continue** du guide d'utilisation : chapitres 1 à 37 et sections N.1…N.k dans l'ordre du
  document (plus de chapitre 3 manquant, de doublons « 10 » / « 14.4 » / « 27.7 », de « 6.0 », « 13.A » ou
  « 25.3b »). Table des matières régénérée (287 liens vérifiés), renvois internes `§ x.y` et ancres du plan
  contextuel de l'aide (`core/aide.py`) mis à jour ; copie égarée de « Emploi du temps » retirée du chapitre
  Finances. Un test impose désormais la continuité à chaque ajout. Les renvois des entrées antérieures de ce
  journal suivent l'ancienne numérotation.
- **Guide de démarrage rapide** (`docs/GUIDE_DEMARRAGE_RAPIDE.md`, dix pages) : premier jour, rentrée,
  quotidien, trimestre, fin d'année, communication, sécurité, dépannage, qui fait quoi, liste de contrôle —
  chaque étape renvoie au guide complet (75 renvois vérifiés par test). Rendu dans l'application à
  `/aide/demarrage/`, bouton **Démarrage rapide** ↔ **Guide complet** sur la page d'aide.
- **Favicon** : icône SVG `img/favicon.svg` déclarée dans l'application, la page de connexion et le portail
  parent ; route `/favicon.ico` (redirection vers l'icône PNG, cache 24 h, autorisée aux rôles Parent/Élève)
  pour toutes les autres pages — fin des 404 dans les journaux.

## 5.32.0 — 2026-10-31

### Thème clair au choix

- *Mon profil → Apparence* : **Sombre** (par défaut, inchangé), **Clair** ou **Selon l'appareil** (`prefers-color-scheme`,
  suivi en direct par `static/js/theme.js`). Préférence enregistrée sur le compte (`User.theme`, migration
  `accounts.0009`), rendue par l'attribut `data-theme` de `<html>` avant le premier affichage : aucun scintillement.
- Feuille de style : palette claire par surcharge des variables (`:root[data-theme="clair"]`), teintes blanches
  translucides exprimées via `--ink` (114 occurrences, identiques en sombre), fonds codés en dur du coffre de
  l'application (barre latérale, en-têtes de tableaux, champs, fenêtres modales) ramenés aux variables.
- Portail parent, page de connexion et PDF inchangés.

## 5.31.0 — 2026-10-31

### Cahier de textes et devoirs dans le portail parent

- Nouvelle page **Cahier de textes** (`/portail/parent/cahier/`), par enfant : tous les devoirs non échus (« pour
  aujourd'hui » signalé) puis les cours des 30 derniers jours — date, matière, horaire, contenu traité, devoirs donnés
  et date de remise.
- Accueil : la section « Travail à faire » est toujours affichée pour un enfant inscrit, avec le lien vers le cahier
  de textes et un état vide explicite ; sa requête réutilise `core.portail.devoirs_a_venir` (doublon supprimé).

## 5.30.0 — 2026-10-31

### Notifications push pour le personnel

- La carte « Notifications sur cet appareil » du portail parent est reprise en haut de la page Notifications de
  l'application : chaque membre du personnel peut recevoir sur son téléphone ou son PC, application fermée comprise,
  les notifications qui lui sont destinées — seuil d'absences atteint, alertes du serveur (5.29.0), rappels de
  licence. Toucher la notification ouvre la page concernée de l'application.
- Même mécanisme que pour les parents (`core/push.py`, clés VAPID de l'installation) : le service worker de
  l'application (`/app-sw.js`) affiche les notifications, le script `push.js` (ex-`push_parent.js`) pilote la carte
  pour les deux publics ; points d'abonnement déplacés sous `/notifications/push/…` et ouverts à tout utilisateur
  connecté. Aucune migration.

## 5.29.0 — 2026-10-31

### Alertes d'exploitation relayées à la direction

- Les alertes de la page Exploitation — aucune sauvegarde ou sauvegarde de plus de 36 h, espace disque faible, erreurs
  applicatives répétées, SMS en difficulté — ne sont plus seulement affichées : elles sont **relayées aux Directeurs /
  Proviseurs et Super Admin** par notification interne (+ e-mail si configuré) et, pour le niveau danger (sauvegarde,
  disque), par **SMS**. Une fois par jour tant que l'alerte dure ; registre = table des notifications (valable pour
  tous les processus, survit aux redémarrages).
- Sans planificateur ni configuration : `core/veille.py` (`VeilleMiddleware`) lance la vérification en arrière-plan à
  la première requête du jour de chaque processus (`/health/` de la surveillance compris). La surveillance Windows
  reste nécessaire pour le seul cas d'un serveur arrêté.
- Titre stable de l'alerte « Erreurs applicatives répétées » (le nombre passe dans le détail).

## 5.28.0 — 2026-10-31

### Rappels d'expiration de la licence

- **Bandeau** discret en tête de chaque page pour les administrateurs (Super Admin, Directeur / Proviseur, Directeur
  Réseau) dès **J-30** : « La licence expire dans N jours (date) », rouge à partir de J-7, puis « Licence expirée le … »
  tant qu'elle n'est pas renouvelée ; lien **Renouveler** pour le Super Admin.
- **Notification interne + SMS** (+ e-mail si configuré) au **Directeur / Proviseur** à **J-15** et à **J-7** — à défaut
  de compte Directeur, aux Super Admin de l'établissement. Un seul envoi par palier et par période de licence
  (alertes `J-30` / `J-15` / `J-7` / `J-1` de `Licences → Alertes`, marquées envoyées avec leurs destinataires).
- Sans planificateur ni configuration : la vérification part de la première page affichée chaque jour, et du contrôle
  des licences lorsqu'il est actif (`LicenceCheckMiddleware` délègue à `licences/rappels.py`, plus d'alertes
  silencieuses). Fonctionne quel que soit `LICENSE_ENFORCEMENT`.
- Connexion : les administrateurs ne reçoivent plus le message « Attention : la licence … expire » en double du
  bandeau (il reste affiché aux autres rôles). **Correctif** : licence expirée, le Super Admin — seul habilité à saisir
  le code de renouvellement — pouvait être refusé à la connexion comme tout le monde (impasse) ; il est désormais
  dirigé vers la page d'activation.

## 5.27.0 — 2026-10-30

### Notifications push du portail parent

- Le parent active, depuis la page Notifications du portail (ou l'invitation de l'accueil), les **notifications sur
  son téléphone** : chaque notification interne (absence, retard, bulletin publié, sanction, rappel de paiement,
  réunion) est poussée sur l'appareil, application fermée comprise ; **Tester** envoie une notification de test et
  rend compte du résultat ; **Désactiver** retire l'appareil. Toucher la notification ouvre la page du portail.
- Web Push standard (`core/push.py` : chiffrement aes128gcm, signature VAPID, remise HTTP) sans service tiers ni
  composant payant ; clés de l'installation générées à la première utilisation et conservées en base
  (`ClesWebPush`), abonnements par appareil (`AbonnementPush`, migration `core 0007`) ; un abonnement révoqué par le
  navigateur (404/410) est supprimé à l'envoi. Dépendances ajoutées : `py-vapid`, `http-ece`.
- Service worker du portail : affichage des notifications et ouverture de la page au toucher ; bannières
  d'installation et de mode hors ligne du portail de nouveau visibles (classe `pp-hidden`).
- Correctif : pour un parent connecté, le contrôle d'accès par rôle renvoyait `/sw.js`, `/manifest.json` et les icônes
  vers le portail — l'application ne pouvait ni s'installer ni recevoir de notifications ; ces ressources sont
  désormais autorisées (`RoleAccessMiddleware`).
- Mode autonome : les dépendances sont réinstallées quand `requirements/base.txt` change (`demarrer-autonome.bat`
  / `.sh`), au lieu d'une installation unique. Guide §20.3.

## 5.26.1 — 2026-10-30

### Un enseignant ne fait l'appel que de ses classes

- Module Présences : pour un compte **Enseignant**, les classes proposées (`Faire l'appel`), l'historique des appels,
  son export CSV et son impression se limitent aux classes de ses **enseignements actifs de l'année**
  (`Pédagogie › Enseignements`, fiche du personnel reliée par l'adresse e-mail) — même règle que la saisie des notes.
- La création d'un appel, sa saisie, le scanner QR, le pointage et les cartes QR d'une autre classe sont refusés avec
  un message explicite (classe non attribuée, ou fiche du personnel absente) ; la file hors réseau reçoit ce refus.
- Dans sa classe, la liste des matières se limite à celles qu'il y enseigne ; l'appel général reste possible.
- Direction, censeur, AVS, secrétariat : inchangé (toutes les classes). Guide §7.1.

## 5.26.0 — 2026-10-30

### Compte rendu quotidien du promoteur par SMS

- Nouveau déclencheur **Compte rendu quotidien du promoteur** (`Configuration → SMS automatiques`) : chaque jour à
  l'heure choisie, un SMS de 160 caractères au plus résume la journée — encaissements (total, nombre de reçus,
  remboursements, espèces en caisse), dépenses validées, arrêtés de caisse faits / caissiers et écart, absents et
  retards sur les appels saisis (`communication/compte_rendu.py`, mêmes calculs que le journal de caisse).
- Réglage sur la ligne du déclencheur : heure d'envoi (18:00 par défaut) et 1 à 5 numéros validés ; aperçu du
  message du jour avec son nombre de caractères ; **Tester** envoie immédiatement sans empêcher l'envoi du jour.
- Envoi par le service SMS existant (`sms_recus --boucle`, Docker `sms` / mode autonome), une seule fois par jour
  dès que l'heure est passée ; la tâche `sms_auto` du matin l'ignore (`--type COMPTE_RENDU` = envoi à la demande).
- Texte allégé automatiquement au-delà de 160 caractères (retards, puis nombre de reçus, puis espèces et écart),
  sans caractère hors du jeu GSM : un seul segment facturé.
- Migration `parametres 0041` (`heure_envoi`, `destinataires`). Guide §2.20.

## 5.25.0 — 2026-10-30

### Saisie hors réseau des notes et des appels (enseignants)

- Les pages **Saisie des notes** et **Appel** soumises alors que le serveur est injoignable sont conservées
  sur l'appareil par le Service Worker (`static/js/sw_saisies.js`, IndexedDB), puis **rejouées
  automatiquement** dès qu'une page de l'application est ouverte sur le réseau — par le même compte,
  avec le jeton CSRF courant (`static/js/saisies_hors_ligne.js`).
- Le rejeu porte l'en-tête `X-Saisie-Differee` : les vues répondent en JSON (`core.hors_ligne.saisie_differee`,
  session expirée → 401, saisie d'un autre compte → 403, droit retiré → 403 JSON par le middleware des rôles)
  et les messages de la vue sont restitués à l'enseignant au lieu de ressortir plus tard.
- Nouvelle page **Saisies hors réseau** (`/hors-ligne/saisies/`, pré-cachée, accessible sans serveur) :
  saisies en attente, nouvel essai d'une saisie refusée, retrait, transmission manuelle, pages de saisie
  consultables sans réseau, dernières transmissions. Pastille « N saisie(s) en attente » sur toutes les pages.
- Sur une page de saisie : mention « Disponible hors réseau » et **restauration des valeurs** d'une saisie
  en attente ou refusée (motif affiché).
- Titres des pages de saisie identifiables : `Notes — Devoir 1 — Mathématiques — 6e A`,
  `Appel — 5e B — Physique — 30/10/2026`.
- Page hors ligne : lien vers la file ; plus de boucle de rechargement quand l'appareil est connecté à un
  autre réseau que celui de l'établissement ; pré-cache des ressources par leur URL réelle (`static()`),
  donc page hors ligne stylée aussi en production.
- Correctif Service Worker : les pages et ressources visitées n'étaient en réalité jamais mises en cache
  (copie de la réponse faite après le début de sa lecture, erreur silencieuse) — copie immédiate et
  écriture garantie (`waitUntil`) ; les pages déjà ouvertes sont donc bien consultables sans réseau.
- Guide §28.6.

## 5.24.0 — 2026-10-30

### Lisibilité des nombres : séparateur de milliers
- Tous les montants affichés (écrans, PDF, confirmations) sont écrits « 150 000 » au lieu de « 150000 » : `floatformat:0` → `floatformat:"0g"` dans 65 gabarits (294 affichages), totaux de points des bulletins compris ; montants bruts de la situation élève, de la liste des paiements et de l'historique des versements alignés. Les champs de saisie numériques restent bruts.
- Effectifs du tableau de bord et du tableau de bord réseau groupés de même (« 1 250 élèves »).
- Messages et libellés calculés en Python : 24 montants passaient par le groupement anglais (« 150,000 FCFA », virgule lue comme décimale en français) → helper `core.utils.fcfa()` (« 150 000 FCFA »).
- Garde-fou : un test refuse tout nouveau `floatformat:0` hors attribut de saisie et tout `:,.0f` suivi de FCFA. 2 tests.

## 5.23.0 — 2026-10-30

### Liste alphabétique du personnel (Documents → Liste du personnel)
- Second tableau récapitulatif sous la liste, dans l'aperçu et le PDF : **personnel par titre de capacité et par genre** (Hommes / Femmes / Total, ligne TOTAL). Les titres sont regroupés sans tenir compte de la casse (graphie majoritaire affichée) ; les agents sans titre saisi figurent sur une ligne « Non renseigné », en dernier. En-têtes des récapitulatifs sur une seule ligne. 1 test.

## 5.22.1 — 2026-10-30
- Tests : isolation du cache de la matrice des droits entre les tests (fixture globale) — en mode serveur (Redis), un refus posé par un test survivait à sa transaction et faisait échouer le test suivant en CI. Aucun changement fonctionnel.

## 5.22.0 — 2026-10-30

### Suppression des messages envoyés aux parents
- Messages parents : bouton **Supprimer** sur chaque ligne de la liste (retour à la vue filtrée), cases à cocher avec case d'en-tête et **Supprimer la sélection** — en plus de la suppression par type / statut de 5.21.0. Même droit `Messages parents → supprimer`.
- Campagnes SMS : **Supprimer** sur la ligne de la campagne et sur sa page de suivi — la campagne et ses SMS sont effacés, les SMS encore en attente ne partent pas. Nouveau droit `Campagnes SMS → supprimer` (secrétariat et direction par défaut). 2 tests.

## 5.21.0 — 2026-10-30

### Communication bidirectionnelle : suppression par type et statut
- Liste des messages parents : avec un type et / ou un statut sélectionnés (recherche comprise), bouton **Supprimer les messages affichés** (nombre indiqué, confirmation) ; sans type ni statut, refus explicite. Fiche du message : **Supprimer**. Nouveau droit `Messages parents → supprimer` (secrétariat et direction par défaut).
- Suppression définitive : réponses du parent en cascade, fichiers justificatifs effacés du disque, SMS reçus conservés dans Messages reçus (détachés). Le compteur annoncé ne compte que les messages, pas les réponses supprimées en cascade.
- **Correction** : la page utilisait la clé de contexte `messages`, qui masquait les messages flash de Django (confirmation d'envoi, erreurs) sur la liste des messages parents et les rejouait sur la page suivante — clé renommée `messages_parents`. 2 tests.

## 5.20.0 — 2026-10-30

### Communication bidirectionnelle : renvoyer les messages non envoyés
- Liste des messages parents : colonne SMS avec l'état réel (*Non envoyé*, *En attente*, *Échec* avec motif, *Envoyé*) et bouton **Envoyer le SMS** / **Renvoyer** sur les lignes non envoyées ou en échec ; fiche du message : **Renvoyer le SMS** (confirmation si un SMS est déjà parti).
- `message_renvoyer_sms` recompose le SMS au format actuel (sigle, objet, contenu, consigne de réponse), relit le numéro sur la fiche élève (parent, sinon tuteur, sinon numéro d'origine), met en file une nouvelle ligne `SmsSortant` reliée au message ; refus explicite sans numéro, au-delà de 160 caractères ou SMS désactivés. Couvert par le droit existant *Messages parents → envoyer*. 2 tests.

## 5.19.0 — 2026-10-30

### Suppression des messages reçus
- `Communication → Messages reçus` : bouton **Supprimer** par ligne, cases à cocher (en-tête = toute la page) + **Supprimer la sélection**, et **Supprimer tous les lus** de la vue courante (libres / commandes / tous), chacun avec confirmation. Nouveau droit `Messages reçus → supprimer` (secrétariat et direction par défaut).
- Un message supprimé disparaît de la boîte, de la pastille du menu et du simulateur SMS Direct ; la ligne est conservée inactive (`is_active=False`) pour que la relève de la boîte du téléphone, qui dédoublonne par identifiant de SMS, ne le retraite pas (il réapparaîtrait sinon dans les 15 secondes avec une nouvelle réponse au parent). Aucune migration. 2 tests.

## 5.18.0 — 2026-10-30

### Communication bidirectionnelle par SMS, fin des « Commande invalide » en rafale
- **Cause** : le SMS envoyé au parent ne contenait que l'objet et un lien `https://<IP du réseau local>:8443/communication/repondre/…`, injoignable depuis le téléphone d'un parent (et l'envoi n'était pas coché par défaut) ; le parent répondait donc par SMS et chaque réponse recevait « Commande invalide. Envoyez AIDE… ». Un numéro de la SIM du téléphone passerelle présent sur une fiche élève faisait de plus boucler cette réponse sur elle-même toutes les 15 secondes.
- **Message en clair** : le SMS contient le sigle, l'objet, le contenu et la consigne de réponse selon le type (créneaux numérotés, « Repondez OK », date de règlement, motif) ; envoi coché par défaut ; refus explicite si le SMS dépasse 160 caractères ou si la fiche n'a aucun numéro ; `MessageParent.sms` (migration `communication 0007`) relie le message à sa ligne d'envoi — la fiche affiche le texte exact et l'état réel (en attente / envoyé le … / échec et motif).
- **Réponse du parent par SMS** (`communication/bidirectionnel.py`) : rattachée au dernier message envoyé à ce numéro depuis moins de 30 jours ; créneau (`2`, « je prends le 2 », libellé), accusé de réception, date de règlement (`15/11`) reconnus ; texte intégral conservé en commentaire horodaté ; message « Répondu » ; accusé « Reponse bien recue, merci… » ; journalisée `REPONSE` (`IncomingSMSLog.message_parent`) et affichée dans Messages reçus avec le lien vers le message.
- **Plus jamais de rafale** : un SMS libre reçoit « Votre message a bien ete recu par l'ecole… » au plus une fois par 24 h et par numéro ; une commande intégrée sans matricule (`NOTE`) reçoit le rappel du format ; un SMS identique à un SMS envoyé par l'école à ce même numéro depuis moins de 24 h est un écho : journalisé, jamais de réponse.
- 6 tests (`test_bidirectionnel.py`) ; guide §29, §10.3, §10.6.

## 5.17.1 — 2026-10-29

### Correctif de test
- `test_commandes_sms.py` : les mots-clés du test de troncature de `AIDE` dépassaient 20 caractères (accepté par SQLite, refusé par PostgreSQL en CI). Aucun changement applicatif.

## 5.17.0 — 2026-10-29

### Commandes SMS définies par l'école
- **Nouvelle page `Communication → Commandes SMS`** : l'école crée ses propres mots-clés avec réponse automatique (`HORAIRES`, `CONTACT`, `CANTINE`, `FRAIS`…), en plus de NOTE / SOLDE / ABS / AIDE. Mot-clé (2–20 lettres ou chiffres, mots intégrés réservés), synonymes acceptés, portée *générale* (mot seul, tout numéro) ou *élève* (mot + matricule, mêmes règles d'autorisation que les commandes intégrées), réponse ≤ 160 caractères avec compteur, activation / désactivation sans suppression, nombre d'utilisations.
- **Variables** remplacées à l'envoi : `{etablissement}` `{date}` `{annee}`, et en portée élève `{eleve}` `{prenom}` `{nom}` `{matricule}` `{classe}` `{moyenne}` `{rang}` `{trimestre}` `{absences}` `{excusees}` `{total_du}` `{total_paye}` `{reste}` ; seules les variables citées sont calculées. Variable inconnue, mot réservé, doublon ou réponse trop longue refusés à l'enregistrement.
- `AIDE` liste désormais les commandes intégrées puis celles de l'école (tronqué proprement à 160 caractères) ; le simulateur SMS Direct les affiche et les accepte ; Messages reçus les journalise (`PERSO`, lien vers la commande, `Count` des utilisations).
- Technique : modèle `communication.CommandeSms` + `IncomingSMSLog.commande` (migration `communication 0006`), module `communication/commandes.py` (`trouver`, `rendre`, `texte_aide`, `valider`), droit `Communication → Commandes SMS → gérer` (secrétariat par défaut), entrée de menu, admin. 7 tests (`test_commandes_sms.py`). Guide §10.2.

## 5.16.1 — 2026-10-29

### Relève des SMS reçus fiabilisée
- **Correction** : quand la boîte de l'app était vide à la première relève (app fraîchement installée), le tout premier SMS reçu ensuite était pris pour un SMS « antérieur à la mise en service » et ignoré sans réponse. Le plancher est maintenant posé même sur boîte vide.
- Relève : plancher initial fixe + dédoublonnage par identifiant (un SMS horodaté avant le dernier traité — deux SIM, horloges d'opérateurs — est traité quand même) ; dates comparées comme des instants (formats `…Z` / `…+01:00`) ; 100 derniers SMS relus à chaque passage.
- Carte « Réception des SMS des parents » : nombre de SMS présents dans la boîte de l'app et date du dernier reçu ; avertissement explicite quand l'app n'a enregistré aucun SMS (autorisation SMS de l'app, SIM du téléphone).
- Aucune réponse n'est envoyée aux codes courts et expéditeurs alphanumériques (SMS d'opérateurs) : journalisés dans Messages reçus, pas de SMS facturé. 3 tests ajoutés (14 au total pour la relève).

## 5.16.0 — 2026-10-29

### Réception des SMS des parents sans dépendre du webhook
- **Relève automatique de la boîte du téléphone** : nouveau service `sms` (`docker-compose.client.yml`, même image que `web`, démarré par `mettre-a-jour.bat`) qui exécute `python manage.py sms_recus --boucle` : toutes les 15 s, lecture de la boîte de réception de l'app SMS Gateway (`GET /inbox`, même adresse et mêmes identifiants que l'envoi) et traitement des SMS reçus (AIDE / NOTE / SOLDE / ABS, messages libres) exactement comme par le webhook — plus aucune condition côté téléphone (certificat, HTTPS, « Require Internet connection », webhook) pour que les parents reçoivent leur réponse. Le même passage renvoie les SMS sortants dont la reprise est due.
- **Un SMS, une réponse** : `IncomingSMSLog.message_id` (migration `communication 0005`) porte l'empreinte commune au webhook (`messageId`) et à la boîte (`id` « text:… ») ; un SMS arrivé par les deux chemins, ou un webhook rejoué par le téléphone, n'est traité qu'une fois (réponse `duplicate`). Première relève silencieuse : les SMS antérieurs à la mise en service ne reçoivent pas de réponse tardive.
- **Diagnostic** : carte « Réception des SMS des parents » en tête de `Paramètres → Configuration SMS` — dernière relève (verte / orange avec le motif : service non démarré, passerelle injoignable, SMS désactivés, app < 1.59), dernier SMS reçu et sort de la réponse (envoyée / en attente / échec et motif), bouton **Relever maintenant**. Le webhook devient le chemin instantané, facultatif.
- Technique : `communication/sms_recus.py` (`traiter_sms_recu` extrait du webhook, `relever_boite_reception`, `identifiant_message`) ; `core.sms.adresse_passerelle` / `requete_passerelle` partagés par l'envoi du webhook ; `restore-windows.ps1` / `restore-local.sh` arrêtent et relancent `sms` avec `web` (aucune session ouverte pendant la bascule de base). 11 tests.

## 5.15.1 — 2026-10-28

### Corrigé
- **Configuration SMS → Enregistrer sur le téléphone** : l'URL du webhook reprenait l'adresse de la page ouverte ; ouverte en `http://localhost:8000` sur le serveur (seul accès HTTP restant après `activer-https`), elle était refusée par l'app SMS Gateway (« url must start with https:// ») et, de toute façon, injoignable depuis le téléphone. L'URL est désormais toujours construite en HTTPS, sur le port du proxy (`YELEN_HTTPS_PORT`), avec l'adresse IP du serveur (`YELEN_HTTPS_HOSTS` quand la page est ouverte en localhost) ; un avertissement explicite bloque l'enregistrement si le HTTPS n'est pas activé ou si l'adresse n'est pas joignable. Guide §10.4.

## 5.15.0 — 2026-10-28

### Ajouté
- **Communication → Messages reçus** : boîte des SMS arrivés au numéro de l'école. Vue par défaut sur les **messages libres** des parents (réponses aux relances, questions…), filtre *Commandes automatiques* (NOTE / SOLDE / ABS / AIDE) et *Tous*, état lu / non lu ; famille identifiée d'après les numéros des fiches élèves quel que soit leur format ; **Marquer lu / non lu**, **Tout marquer comme lu**, **Répondre** par SMS (160 caractères, via la file SMS). Pastille du menu avec le nombre de messages libres non lus. Droit d'action *Marquer lu / non lu et répondre par SMS* dans la matrice des droits ; les requêtes du simulateur SMS Direct sont enregistrées déjà lues. Champs `lu_le` / `lu_par` sur le journal des SMS entrants (migration `communication 0004`). Guide §10.4, §10.6, §10.7.

## 5.14.3 — 2026-10-28

### Corrigé
- **Réception des SMS des parents (Parent-SMS Direct)** : le webhook `/communication/webhook/sms/` ne lisait que des champs à plat (`phoneNumber`, `message`) alors que l'app Android SMS Gateway envoie une enveloppe `{"event": "sms:received", "payload": {"sender", "message"}}` — tout SMS reçu était rejeté « Missing phoneNumber or message » et l'app réessayait 14 fois. L'enveloppe est comprise, les autres événements (`sms:sent`, `sms:delivered`, `system:ping`…) sont acquittés sans traitement, et la signature native de l'app (`X-Signature` = HMAC-SHA256(corps + `X-Timestamp`), ± 5 min) est acceptée quand un secret HMAC est configuré.

### Ajouté
- `Paramètres → Configuration SMS` : l'URL du webhook inclut le jeton (`?token=`, l'app ne sait pas ajouter d'en-tête) et le bouton **Enregistrer sur le téléphone** déclare cette URL à l'app SMS Gateway (`POST /webhooks`, événement `sms:received`, identifiant fixe, mêmes identifiants que l'envoi). Guide §2.17 et §10.4 (certificat YELEN sur le téléphone, « Require Internet connection » désactivé, vérification par `AIDE`).

## 5.14.2 — 2026-10-28

### Corrigé
- **SMS de relance** (`Finances → Relances → SMS`) : le montant partait d'un tarif pris au hasard (premier tarif de la rubrique, tous niveaux, statuts et années confondus, même inactif) et les élèves sans statut étaient relancés — des familles à jour recevaient un rappel, pour un montant faux, et la liste des SMS ne correspondait ni au compteur ni au PDF. Le compteur, le PDF et les SMS reposent désormais sur un calcul unique (`finances/redevables.py`), identique au formulaire de paiement : tarif du niveau × année × statut de l'élève, services et créances de la rubrique, bourses ciblées déduites, versements moins remboursements, plafonné au reste global de l'élève ; nombre de requêtes constant.
- **Modèles de messages** : un modèle citant une variable inconnue (`{eleve}`, `{reste}`…) était envoyé **tel quel** au parent, accolades comprises ; une accolade isolée faisait planter le rendu. Le rendu ne lève plus jamais d'exception, un modèle invalide est remplacé par le texte par défaut (signalé « Ignoré — variable inconnue » dans la liste) et l'enregistrement refuse variable inconnue, accolade isolée ou SMS de plus de 160 caractères (il serait tronqué). Les campagnes SMS partagent ce rendu.
- Relance SMS refusée (message explicite) quand l'envoi de SMS est désactivé, au lieu d'annoncer « N SMS envoyés » sans rien envoyer ; SMS mis en file par lot (un seul fil d'envoi) et tracés dans la file SMS au nom de l'élève et de la rubrique ; numéro de la fiche normalisé (`+226…`) dans l'historique ; résolution du numéro du parent (parent → tuteur → urgence) centralisée (`Eleve.telephone_parent_valide`) ; montant du rappel d'échéancier automatique formaté « 50 000 » et non « 50,000 ».

## 5.14.1 — 2026-10-28

### Ajouté
- **Environnement de test isolé** (`creer-environnement-test.bat` → `installer/creer-environnement-test.ps1`, guide de déploiement §3.5.7) : second YELEN SCHOOL complet à côté de la production (`C:\YELEN-TEST`, projet Docker `yelen-test`, image `yelen-school:test`, port 8001 sur 127.0.0.1, base et médias copiés de la dernière sauvegarde), `.env` dérivé de la production avec contrôle des licences actif (`LICENSE_ENFORCEMENT=true`, `LICENCE_BINDING_ENABLED=true`, `LICENCE_PUBLIC_KEY`), SMS, paiements mobiles, courriel et sauvegarde distante désactivés ; paire de clés de l'éditeur créée une seule fois dans `C:\YELEN-EDITEUR\cles-editeur.txt`. La production n'est jamais modifiée. Tests PowerShell `installer/tests/test-creer-environnement-test.ps1` (CI).
- **`installer/outils-editeur/emettre-licence.ps1`** : émission d'un code de licence `YELEN3` à partir du fichier des clés de l'éditeur (image Docker ou `.venv` autonome), sans afficher la clé privée.
- **Bandeau « ENVIRONNEMENT DE TEST »** (`YELEN_ENVIRONNEMENT=test`) sur la connexion, les pages de l'application et les pages licences.
- `docker-compose.client.yml` : nom de l'image paramétrable (`YELEN_IMAGE`, défaut `yelen-school:client`).

## 5.14.0 — 2026-10-28

### Ajouté
- **Absences du personnel** (`Personnel → Absences`, guide §9.33) : saisie (dates, motif, justifiée, retenue), bilan mensuel par agent, historique sur la fiche du membre ; la préparation de la paie propose une retenue de `salaire de base / 30 × jours non justifiés` dans « Autres retenues ». Modèle `AbsencePersonnel` (migration `personnel/0011`), droit « Absences du personnel ».
- **Sanction → parent** (guide §9.34) : case « Prévenir le parent » à la saisie d'une sanction (notification du portail parent + SMS, modèle `Sanction disciplinaire` avec `{nom_eleve} {classe} {date} {sanction} {motif} {etablissement}`), horodatage `parents_notifies_le` affiché dans la liste ; section « Sanctions disciplinaires » sur le portail parent (annulées exclues). Migrations `viescolaire/0009`, `parametres/0039`.
- **Fiche individuelle de l'élève** PDF A4 portrait signée (identité, photo, parents/tuteur, santé, personnes autorisées, parcours) depuis le dossier de l'élève (guide §9.35).
- **Attestation de travail** PDF A4 portrait signée (fonction, titre de capacité, date d'embauche, nature du contrat) depuis la fiche du membre (guide §9.36). Types de documents `FICHE_ELEVE` et `ATTESTATION_TRAVAIL` (migration `parametres/0040`, signataire repris de la catégorie).

### Corrigé
- **Examens** : les sessions, centres, salles et placements d'un autre établissement répondent désormais 404 (modification de session, inscription d'une classe, export CSV, PDF des candidats, centres, salles, placements) ; le formulaire de session ne propose que les années de l'établissement ; un centre d'une autre session ne peut plus être affecté.
- **Manuels** : le sélecteur d'élèves du formulaire d'attribution ignore une classe d'un autre établissement.
- **Sanctions** : l'ancien signal notifiait automatiquement chaque sanction créée (même importée) sans SMS ni trace — remplacé par la case à la saisie.
- Guide : front matter aligné (version 5.14.0, date, modules réels), variables des modèles SMS `Seuil d'absences` et `Sanction` listées dans l'écran des modèles.

### Tests
- 77 tests ajoutés : examens (35), manuels (15), personnel (13), vie scolaire (8), fiche élève (4), documents signés (2 : fiche élève, attestation de travail — 50 documents couverts). Suite : 1 293 tests, couverture 78,7 %.

## 5.13.1 — 2026-10-28

### Ajouté
- **Titre de capacité** sur la fiche du personnel (`Personnel → Nouveau membre`, volet « Carrière & Affectation », texte de 35 caractères, facultatif — ex. CAPES, CAP-CEG, Licence) ; affiché sur la fiche du membre. Champ `MembrePersonnel.titre_capacite` (migration `personnel/0010`).

## 5.13.0 — 2026-10-28

### Ajouté (audit — Lot I : confort)
- **Seuil d'absences** (`Présences → Alertes d'absences`) : la direction règle un seuil d'absences non justifiées (défaut 5, par trimestre ou par année, SMS au parent activable). À la **clôture de chaque appel**, tout élève absent qui atteint le seuil — puis chaque multiple (2×, 3×…) — déclenche une alerte : notification in-app du directeur et du censeur, SMS au parent (modèle `Seuil d'absences atteint`, modifiable dans `Paramètres → Modèles de messages`), message d'avertissement à l'enseignant qui clôture. La page liste les alertes à traiter (élève, classe, période, absences / seuil, SMS envoyé) ; « Traitée » enregistre la suite donnée (convocation, entretien) avec l'auteur et la date ; l'historique reste consultable. Une absence excusée par un justificatif accepté ne compte plus.
- **Santé et personnes autorisées** sur la fiche élève (section « Santé & personnes autorisées » du formulaire et de la fiche) : groupe sanguin, allergies, informations médicales (maladie chronique, traitement, consignes), médecin / centre de santé, **personnes autorisées à récupérer l'élève** (une par ligne : nom — lien — téléphone).
- **Référentiel des salles** (`Paramètres → Salles`) : nom, capacité, actif ; l'emploi du temps **propose les salles** à la saisie, **normalise** la casse (`salle 2` → `Salle 2`, donc les conflits de salle sont détectés quelle que soit la façon d'écrire) et **avertit** quand l'effectif de la classe dépasse la capacité de la salle. Page `Vie scolaire → Occupation des salles` : une ligne par salle, une colonne par jour, les séances de l'année dans chaque case (créneaux libres visibles), nombre de séances et heures par semaine, impression.
- **Pré-inscriptions** (`Inscriptions → Pré-inscriptions`) : dossier d'un nouvel élève **avant** l'inscription (année — par défaut l'année suivante dès qu'elle existe —, classe demandée, identité, origine scolaire, parent et téléphone), filtres année / classe / statut, **synthèse par classe** (en attente, acceptées, inscrites, effectif, capacité, places restantes, tension), décisions **Accepter / Refuser / Remettre en attente**, puis **Inscrire** : l'élève et son inscription (statut « Non affecté ») sont créés en un clic avec matricule, parent et téléphone repris, et le formulaire d'inscription s'ouvre pour compléter (statut, photo). Classe complète ou année clôturée refusées ; un dossier refusé ne peut pas être inscrit.
- **Sauvegarde depuis l'interface** (`Administration → Exploitation`, Super Admin / Directeur, mode autonome SQLite) : bouton **Sauvegarder maintenant** (base à chaud + archive ZIP des médias : photos, signatures, justificatifs), liste des sauvegardes disponibles (fichier, type, date, taille) avec **téléchargement** pour copie sur un support externe, rappel de la procédure de restauration. En mode serveur (PostgreSQL) la page renvoie vers `backup-windows.bat`.

### Technique
- `presences.SeuilAbsences` / `AlerteAbsences` (migration `presences/0007`), `presences/alertes.py` ; `inscriptions.Eleve` champs santé (migration `inscriptions/0020`) ; `parametres.Salle` + `Salle.canonique` (migration `parametres/0037`) ; `inscriptions.PreInscription` (migration `inscriptions/0021`), `inscriptions/preinscriptions.py` ; `ModeleMessage` type `SEUIL_ABSENCES` (migration `parametres/0038`) ; `core/sauvegarde.py` (`sauvegarder_maintenant`, `lister_sauvegardes`, `chemin_sauvegarde` — nom strictement validé, aucun chemin relatif), route `exploitation/sauvegardes/<nom>`. Heures d'occupation des salles affichées avec deux décimales.

## 5.12.0 — 2026-10-28

### Ajouté (audit — Lot H : communication, personnel, pilotage)
- **Campagnes SMS ciblées** (`Communication → Campagnes SMS`, direction / secrétariat / comptabilité) : public au choix — parents de tous les élèves inscrits, de classes cochées, des élèves ayant un reste à payer, des élèves absents un jour donné, ou membres du personnel — ; message à variables (`{eleve}`, `{classe}`, `{reste}`, `{etablissement}`, `{nom}`) ; **aperçu avant envoi** (nombre de destinataires joignables, élèves ou agents sans numéro valide, textes rendus, longueur du plus long message par rapport aux 160 caractères) ; un numéro partagé par plusieurs enfants reçoit **un seul SMS** qui les énumère ; les élèves partis (abandon) sont exclus. Les SMS sont mis en file en une fois et envoyés par **un seul fil d'arrière-plan** par paquets de 50. Historique des campagnes avec envoyés / échecs / en attente, détail par destinataire (statut, erreur) et **renvoi des échecs**.
- **Paie du mois** (`Personnel → Paie du mois`, bouton depuis `Salaires`) : tableau de bord du mois (bulletins par statut, totaux brut / retenues / net, agents permanents sans bulletin) ; **Préparer la paie** crée en une fois un brouillon pour chaque agent permanent (vacataires exclus) sans bulletin ce mois-ci, en reprenant salaire de base, indemnités et retenues CNSS / IUTS de son dernier bulletin, prime d'ancienneté recalculée, primes et retenues exceptionnelles à zéro (droit « Préparer la paie du mois en masse ») ; **Valider les brouillons** passe tout le mois en « Validé » (droit « Valider un salaire ») ; **Livre de paie** PDF (A4 paysage, une ligne par agent, totaux, signataire du bulletin de salaire) ; **Bulletins du mois** en un seul PDF (un bulletin par page, même gabarit que le bulletin unitaire).
- **Statistiques d'examen ventilées** (fiche de session → `Statistiques`, écran et PDF, droit « Statistiques de la session ») : inscrits, présents, admis, ajournés, absents, exclus et taux de réussite **garçons / filles / total**, par **classe d'origine**, par **centre**, par **mention**, répartition par **tranche de moyenne**, dix meilleures moyennes, candidats sans résultat saisi. Taux de réussite = admis / présents (les absents ne comptent pas au dénominateur).
- **Statistiques par enseignant** (`Pilotage → Statistiques par enseignant`, direction ; écran et PDF ; année ou période) : par enseignant puis par classe et discipline — nombre de classes et d'élèves, heures hebdomadaires (emploi du temps), évaluations terminées / créées (annulées exclues), **taux de saisie des notes** (notes saisies / élèves × évaluations, en rouge sous 80 %), moyenne et part d'élèves ≥ 10 (dispensés exclus), entrées du cahier de textes, appréciations rédigées. Les enseignements sans enseignant forment la ligne « Non attribué ».

### Technique
- `core.CampagneSms` + `SmsSortant.campagne` / `destinataire` (migration `core/0006`), `core.tasks.mettre_en_file_lot` / `_vider_file`, `communication/campagnes.py` ; `personnel/paie.py` ; `examens/statistiques.py` ; `pedagogie/statistiques_enseignants.py`. Quatre nouveaux PDF signés (`livre_paie`, `bulletins_salaire_lot`, `statistiques_session`, `statistiques_enseignants`).

## 5.11.0 — 2026-10-28

### Ajouté (audit — Lot G : portails)
- **Portail élève enrichi** : travail à faire (devoirs du cahier de textes à venir), quinze dernières notes, moyennes par matière et par période, emploi du temps de la semaine, absences et retards de l'année avec compteurs.
- **Portail parent — Vie scolaire** (`/portail/parent/vie-scolaire/`, barre de navigation commune Accueil · Vie scolaire · Bulletins · Frais · Notifications) : par enfant, emploi du temps, compteurs et dernières absences / retards, justificatifs déposés et leur statut.
- **Dépôt de justificatif d'absence par le parent** : période (au plus 30 jours, jamais à venir), motif, pièce jointe facultative (PDF, JPG ou PNG, 5 Mo, contenu vérifié). Le justificatif arrive « En attente » dans `Présences → Justifications` avec le badge **Portail parent** ; l'acceptation par le secrétariat excuse les absences comme aujourd'hui.
- **Appréciations par matière** (`Pédagogie → Appréciations par matière`, droit « Saisir les appréciations de ses disciplines ») : l'enseignant titulaire rédige, par période, l'appréciation de chaque élève pour sa discipline (200 caractères, suggestions, moyenne en regard) ; la direction voit toutes les disciplines. L'appréciation saisie est **imprimée sur le bulletin** en regard de la matière ; à défaut, la grille des moyennes s'applique comme avant. Une période clôturée est en lecture seule.
- **Comptes parents en masse** (`Utilisateurs → Comptes parents en masse`, direction) : les élèves de l'année sans compte parent sont regroupés par téléphone du parent ou du tuteur ; un compte par famille est créé (identifiant = numéro de téléphone, mot de passe provisoire de 12 caractères à changer à la première connexion), les enfants sont rattachés, un SMS d'accueil est mis en file si les SMS sont activés et un récapitulatif imprimable est affiché une seule fois. Les familles déjà équipées sont rattachées sans nouveau mot de passe ; les élèves sans téléphone sont listés.
- **Connexion par téléphone** : la page de connexion accepte l'e-mail ou le numéro de téléphone d'un compte parent créé en masse (toute mise en forme : espaces, +226, tirets).

### Corrigé
- Le recalcul des moyennes supprimait les lignes de résultat sans note : une appréciation saisie survit désormais au recalcul (ligne conservée sans moyenne).

### Technique
- `core/portail.py` (emploi du temps, assiduité, notes, devoirs, dépôt de justificatif), `core/validators.py::validate_piece_jointe`, `presences.Justification.deposee_par` (migration `presences/0006`), `pedagogie/views/appreciations.py`, `accounts/parents_masse.py`, `User.identifiant_connexion`. Le rôle PARENT accède aussi à `/bulletins/parent/` (consultation et signature du bulletin).

## 5.10.0 — 2026-10-28

### Ajouté (audit — Lot F : caisse et familles)
- **Journal de caisse par caissier** (`Finances → Journal de caisse`, PDF) : encaissements et remboursements d'une journée, totaux par mode de paiement, espèces théoriques en caisse (espèces − remboursements). Sans filtre, chaque utilisateur voit sa propre caisse ; « Toutes les caisses » pour la direction.
- **Arrêté de caisse** (droit « Arrêter sa caisse ») : le caissier saisit les espèces comptées ; l'écart est calculé et figé avec les totaux. Une caisse arrêtée refuse toute saisie de paiement ou de remboursement de ce caissier datée du jour arrêté ou d'un jour antérieur (« Votre caisse est arrêtée jusqu'au … »). Réouverture réservée à la direction (droit « Rouvrir une caisse »), historique des 15 derniers arrêtés.
- **Familles** (`Finances → Familles`) : fratries de l'année regroupées par compte parent, sinon par téléphone du parent ou du tuteur ; enfants (aîné d'abord), total dû, payé et reste à payer consolidés, recherche par nom / téléphone / enfant. La fiche financière de chaque élève affiche sa fratrie.
- **Remise fratrie automatique** (droit « Appliquer la remise fratrie ») : le type de bourse et le rang du premier enfant bénéficiaire (2e par défaut) se choisissent dans les paramètres financiers ; l'application attribue la bourse aux enfants de rang ≥ n qui ne l'ont pas encore (calcul sur le montant dû brut, pourcentage ou montant fixe), sans doublon à la ré-exécution.
- **Pénalités de retard** (`Échéanciers`, bandeau « Appliquer les pénalités », direction) : pour chaque échéance dépassée du délai de grâce, non cochée payée et non couverte par les versements (cumul des échéances dues à cette date > total payé), une créance « Pénalité de retard — <tranche> (échéance du …) » est émise sur la rubrique paramétrée (montant fixe ou % de la tranche). Une seule pénalité active par échéance ; annulable depuis la situation de l'élève.
- **Blocage des bulletins des élèves non à jour** (paramètre + seuil en % du montant dû) : portail parent, lien public de consultation / signature et API mobile n'affichent plus le bulletin tant que le seuil n'est pas atteint, avec le motif chiffré (« reste à payer … FCFA, x % requis »). La consultation interne (secrétariat, impression) n'est pas bloquée.
- **Paramètres financiers** (`Finances → Paramètres financiers`, droit d'approbation) : pénalités (mode, valeur, délai de grâce, rubrique), blocage des bulletins (seuil), remise fratrie (type de bourse, rang).
- **Portail parent** : vignette « Reste à payer » par enfant et section *Frais de scolarité* (montant dû net des bourses, versé net des remboursements, prochaine échéance, trois derniers reçus).

### Technique
- `finances.ParametresFinances` (un par établissement), `finances.ClotureCaisse`, `Creance.echeance` et origine `PENALITE` (migration `0023`) ; services `finances/caisse.py`, `familles.py`, `penalites.py`, `blocage.py` ; `_situations_financieres_en_lot` expose aussi `total_du_brut` et `total_reduction`. PDF « Journal de caisse » signé par le signataire du bilan des encaissements.


### Ajouté (audit — Lot E : rentrée et fin d'année)
- **Passage de classe en lot** (`Élèves → Réinscription`) : la page liste les élèves de l'année courante non encore inscrits pour l'année suivante, avec la dernière décision du conseil de classe et la classe de destination proposée (passage / rachat / sans décision → niveau supérieur, redoublement → même classe, exclusion / réorientation → aucune). Cases à cocher, classe modifiable ligne par ligne, inscription en un clic ; chaque refus (classe complète, déjà inscrit, année clôturée) est signalé nommément sans bloquer les autres. Filtre par classe, « Tout cocher », bouton **Détail** pour la réinscription individuelle.
- **Clôture d'année scolaire** (`Paramètres → Années scolaires`, boutons Clôturer / Rouvrir, droit « Clôturer / rouvrir une année scolaire ») : l'année courante ne se clôture pas ; la clôture verrouille les inscriptions de l'année (création, modification, transfert, abandon, réinscription vers cette année) et clôture toutes ses périodes d'évaluation ; une année clôturée ne peut plus être définie comme courante. La réouverture libère les inscriptions sans rouvrir les périodes.
- **Capacité des classes appliquée** : inscription, modification d'inscription et transfert refusent une classe pleine (« Classe 6e A complète : 50/50 places occupées pour 2025-2026 ») ; les abandons ne comptent pas.
- **Détection des homonymes** à la création d'un élève (nom + prénom + date de naissance, établissement courant) : bandeau listant les fiches existantes avec lien ; la création exige un second envoi de confirmation.

### Corrigé
- Réinscription : l'inscription était créée dans l'année **courante** (donc en double) au lieu de l'année suivante, sans statut élève ni marquage du redoublement ; l'année courante et l'année suivante étaient cherchées sans tenir compte de l'établissement (première année courante de la base). Désormais : année de l'établissement, inscription dans l'année suivante, statut élève repris, redoublant + classe redoublée renseignés, `last_classe` / `last_annee` de l'élève mis à jour.
- Formulaire d'inscription : la liste des années scolaires n'était pas limitée à l'établissement de l'utilisateur.

### Technique
- `inscriptions/services.py` (règles réinscription / capacité / clôture) ; `parametres/niveaux.py` (`cle_niveau`, `rang_niveau`, `niveau_suivant`) partagé avec les statistiques officielles.

## 5.8.1 — 2026-10-28

### Corrigé (audit — Lot D : dette technique)
- Assistant IA : les réponses ne sont plus calculées sur l'ensemble des établissements de la base mais sur celui de l'utilisateur connecté (effectifs, finances, absences, difficultés, moyennes, progression, recherche d'élève). Les montants attendus/encaissés reprennent le calcul du module Finances (tarifs + services + créances − bourses ; versements − remboursements) au lieu de l'ancienne table des frais. La page `/assistant/` est réservée à la Direction (Directeur, Censeur, Directeur réseau, Super Admin) ; une erreur interne affiche un message neutre et n'expose plus le détail technique. Reconnaissance de « Résumé des absences » et « Moyennes de la … » corrigée.
- Prédiction de réussite : le malus d'assiduité ne s'appliquait jamais (filtre sur un champ inexistant, masqué par un `except Exception` qui remplissait le journal). Les absences non justifiées (statut *Absent*) sont de nouveau comptées ; *Excusé* ne pénalise pas.
- SMS : modem série débranché ou port introuvable → échec propre consigné dans la file (au lieu d'une exception non rattrapée) ; `SMS_ENABLED` lu via `sms_actifs()` partout (notifications, convocation réunion, manuels, test de la passerelle).

### Technique
- Constante `StatutInscriptionChoices.ABANDON` à la place de 69 littéraux `'ABANDON'` dans 24 fichiers.
- `except Exception` : 93 → 75 (hors `licences/`, conçu pour ne jamais bloquer l'application : 39) ; les blocs restants journalisent la trace. Exceptions précises sur la 2FA, le chiffrement, les formulaires de paramétrage, la génération d'EDT, les modèles de SMS, la passerelle SMS.
- `parametres/views.py` (1 982 lignes) → paquet `parametres/views/` (scolarité, nomenclatures, tarifs, signataires, établissement, calendrier, messages/SMS) ; `viescolaire/views.py` (1 561 lignes) → paquet `viescolaire/views/` (conseils, sanctions, activités, EDT, suivi). Aucune URL ni nom de vue modifié.
- Tests : assistant IA (20), module SMS (40), prédictions (21) ; couverture mesurée 75 % (seuil CI 65 → 73).

## 5.8.0 — 2026-10-27

### Nouveau (audit — Lot C : exploitation)
- Emploi du temps : détection des conflits. Une séance est refusée si la classe a déjà cours, si l'enseignant est déjà en cours dans une autre classe ou si la salle est occupée au même moment (séances enchaînées autorisées) ; la génération automatique tient compte des cours des professeurs dans les autres classes et son application écarte les séances en conflit ; la grille d'une classe liste en tête les chevauchements déjà présents.
- SMS : file d'envoi persistante (`SmsSortant`). Chaque SMS est enregistré puis envoyé en arrière-plan ; les échecs passagers sont retentés (2 min, 10 min, 30 min, 2 h, abandon après 5 tentatives, immédiat pour un numéro invalide) par les envois suivants, la commande `sms_file`, la fin de `sms_auto` et le bouton « Réessayer maintenant ». Plus aucun message perdu au redémarrage. Administration Django.
- Exploitation : page `Administration → Exploitation` (Super Admin, Directeur) et bannière du tableau de bord : dernière sauvegarde (alerte au-delà de 36 h ou si aucune n'est visible), espace disque (alerte sous 5 Go ou 10 %), erreurs applicatives des dernières 24 h (journal `django.log`), état de la file SMS. Le dossier `backups\` du poste serveur est monté en lecture seule dans le conteneur (`docker-compose.client.yml`).

### Corrigé
- `SMS_ENABLED` enregistré à « False » depuis la page Configuration SMS était lu comme actif (chaîne non vide) : les envois étaient tentés puis échouaient. Lecture unifiée (`sms_actifs()`).

## 5.7.0 — 2026-10-27

### Nouveau (audit — Lot B, suite : créances individuelles)
- Finances : modèle **Créance** (dû individuel d'un élève, hors tarif et hors abonnement) compté dans le total dû au même titre qu'un service annexe : situation financière (carte *Créances individuelles*), reste à payer unitaire et en lot (redevables, relances, tableau de bord, certificats), formulaire de paiement (rubrique de la créance encaissable, plafond = tarif + services + créances de la rubrique). Action « Annuler une créance individuelle » (Direction) depuis la situation ; l'annulation ne touche pas aux versements encaissés. Administration Django.
- Manuels : `Non rendus → Facturer` émet une créance « Manuel non rendu » (prix de remplacement, rubrique MNR) au lieu d'un faux paiement ; le `Retour` du manuel annule automatiquement la créance. Colonne « Créance émise », messages et SMS reformulés (« frais à régler »).

### Corrigé
- Le faux paiement « Manuel non rendu » gonflait le total payé et bloquait tout encaissement réel sur la rubrique (plafond atteint). Migration de données : chaque attribution déjà facturée reçoit sa créance (annulée si le manuel a été rendu depuis) et le faux paiement, immuable comme tout paiement comptabilisé, est neutralisé par un remboursement de même montant. Le plafond d'encaissement par rubrique tient désormais compte des remboursements (une rubrique remboursée redevient payable).

## 5.6.0 — 2026-10-27

### Nouveau (audit — Lot B : intégrité des résultats)
- Clôture de période : `Paramètres → Périodes` propose « Clôturer » (cadenas) sur chaque période. Une période clôturée verrouille son trimestre : saisie des notes (formulaire désactivé), création et modification d'évaluations, import Excel de notes, saisie des compétences APC et calcul des moyennes sont refusés avec un message explicite ; moyennes, rangs et bulletins restent figés (une sanction prononcée après coup ne les modifie plus). « Rouvrir » lève le verrou ; chaque bascule est journalisée dans l'audit. Action « Clôturer / rouvrir une période » de la matrice des droits (Direction par défaut).
- Bulletins : absences justifiées (heures), non justifiées (heures) et retards sont relevés automatiquement dans **Présences** sur les dates du trimestre (absence excusée → justifiée ; séance sans horaire = 1 h). La fiche du conseil de classe s'ouvre pré-remplie et reste corrigeable ; sans fiche, liste, aperçu et PDF (unitaire et lot) impriment le relevé.

### Corrigé
- Calcul des moyennes : une note retirée ou une évaluation supprimée laissait une moyenne de discipline fantôme sur le bulletin ; ces résultats orphelins sont purgés au recalcul (les dispenses sont conservées) et un élève sans plus aucune note perd sa moyenne générale.
- Bulletins → « Publier tous » renvoyait une erreur 500 (variable `messages` masquée par un import local) : la publication en masse fonctionne de nouveau.

### Technique
- Bulletin annuel : un seul gabarit (`pedagogie/pdf/bulletin_annuel.html`) pour l'individuel et les lots de classe (`bulletin_annuel_batch.html` supprimé) ; `Trimestre.objects.pour_periode(periode)`, `Trimestre.verrouille`, `Bulletin.objects.obtenir(...)`, `bulletins.services.assiduite_depuis_presences(...)`.

## 5.5.22 — 2026-10-27

### Sécurité (audit — Lot A)
- Formulaire d'inscription : les trois points JSON (niveau et cycle d'une classe, code d'un statut) exigent désormais une session ouverte.
- Saisie des notes → sélection de la classe : limitée aux classes de l'établissement de l'utilisateur (elle listait toutes les classes de tous les établissements pour les non-enseignants).

### Qualité
- Module Manuels scolaires exécuté par la CI (`testpaths`) avec 13 tests : catalogue, cloisonnement par établissement, exemplaires, attribution/retour, non-rendus, PDF.
- Dépôt : l'outillage de développement IA (`.claude/`, `opencode/`, `skills/`, `plans/`, `yelen-school-bulletin-annuel/`, 70 fichiers) n'est plus versionné.

## 5.5.21 — 2026-10-27

### Corrigé
- Signature du directeur, cachet (Identité de l'établissement) et signature scannée des signataires : un scan de plus de 512 Ko était refusé (« L'image est trop volumineuse. Taille maximale : 0.5 Mo »). Ces images sont acceptées jusqu'à 5 Mo comme toute image de l'application, puis automatiquement ramenées à 800 px et ré-encodées (PNG si transparence, JPEG sinon) : fichiers légers dans les PDF, rien à redimensionner avant l'envoi.

## 5.5.20 — 2026-10-27

### Corrigé
- Bulletin de notes : une discipline dans laquelle l'élève n'avait aucune note disparaissait de son bulletin (seuls les élèves notés partout voyaient toutes les disciplines). Chaque bulletin liste désormais toutes les disciplines de la classe, dans le même ordre, avec « — » lorsque la moyenne n'existe pas ; la moyenne générale est inchangée.
- Les moyennes par discipline, les moyennes générales et les rangs sont recalculés automatiquement à chaque enregistrement de notes (saisie et import Excel) : les bulletins ne dépendent plus du dernier clic sur « Calculer les moyennes ».

## 5.5.19 — 2026-10-27

### Modifié
- Bulletins de notes (trimestriel et annuel) : un trait sépare désormais le titre de section (« Notes du trimestre », « Récapitulatif des moyennes ») de l'en-tête des colonnes du tableau.

## 5.5.18 — 2026-10-27

### Modifié
- Bulletin de notes trimestriel : l'en-tête des colonnes du tableau des notes (bandeau noir, texte blanc 7 pt) passe sur fond clair avec un texte sombre et net (7,5 pt, filet sous l'en-tête) ; même lisibilité appliquée au bulletin annuel. Le bulletin tient toujours sur une page A4.

## 5.5.17 — 2026-10-27

### Vérifié
- Les 43 documents PDF signés de l'application sont rendus réellement (WeasyPrint) avec le signataire configuré : fonction, NOM Prénom et signature scannée présents sur chacun (`core/tests/test_signataire_documents.py`). Tout nouveau document sans signataire fait échouer la suite.

### Corrigé
- Résolution du signataire : un signataire dont le membre du personnel a été supprimé laissait le document sans signature ; il est désormais ignoré au profit du candidat suivant (même document, même catégorie, même cycle, puis tout signataire actif).
- Circulaire : même résolution que les autres documents (signataire du cycle des classes destinataires) au lieu du premier signataire trouvé.

### Ajouté
- `python manage.py verifier_signataires` : affiche, par cycle et type de document, le signataire réellement imprimé, le repli utilisé et les anomalies (aucun signataire actif, membre supprimé, fichier de signature absent du disque, type référencé par un document mais absent du catalogue).

## 5.5.16 — 2026-10-26

### Corrigé
- `Paramètres → Signataires`, fenêtre « Modifier le signataire » : les listes Cycle, Catégorie de type de document et Nom et Prénom étaient vides (données jamais transmises au gabarit) — impossible de choisir un signataire ; elles sont renseignées et pré-sélectionnées.
- Fenêtre « Modifier le signataire » et page « Nouveau signataire » : la fonction choisie n'était pas enregistrée (champ posté sous un autre nom que celui lu par le formulaire) ; le document imprimait « Le Directeur » par défaut.

## 5.5.15 — 2026-10-26

### Corrigé
- Liste alphabétique du personnel d'un cycle : le bloc signataire restait vide alors que le directeur du cycle était configuré, dès lors que le type « Liste du Personnel » (`LISTE_PERSONNEL`) avait été désactivé, renommé ou supprimé dans `Paramètres → Types de documents` — le document s'arrêtait net. Tout document dont le type manque au catalogue se replie désormais sur le signataire configuré pour son cycle (puis sur le dernier signataire actif).
- `Configurer les Signataires` : un enregistrement refusé par le formulaire (titre honorifique trop long, membre hors établissement…) rechargeait la page sans un mot ; le motif est désormais affiché.

## 5.5.14 — 2026-10-26

### Corrigé
- Signataires : dix documents gardaient une case « Le Directeur » à signer à la main ou n'avaient aucune signature — le signataire configuré (fonction, signature scannée, NOM Prénom) ne pouvait pas y apparaître : contrat de travail, bulletin de salaire, bulletin de vacation, PV de conseil de classe, dossier de transfert, bulletin de compétences, liste des élèves (Inscriptions), liste des candidats, liste des boursiers, documents manuels scolaires (inventaire, attributions, non rendus). Tous l'impriment désormais ; la fiche de discipline porte la signature scannée de l'enseignant qui la certifie.
- Catalogue des types de documents : ajout de Dossier de Transfert, Liste des Candidats, Liste des Boursiers, Procès-Verbal de Conseil de Classe, Manuels Scolaires, Contrat de Travail, Bulletin de Salaire, Bulletin de Vacation (migration `parametres 0036`). Les types ajoutés reçoivent automatiquement, par cycle et année, le signataire déjà configuré pour leur catégorie ; à défaut de configuration, un document se replie sur le signataire de sa catégorie avant tout autre.
- Dossier de transfert : le PDF échouait (champ inexistant `nom_parent`) ; le parent/tuteur affiché est le tuteur, à défaut le père puis la mère.
- Garde-fou : la suite de tests refuse tout gabarit PDF sans signataire configuré (hors journal d'audit, avis Mobile Money, analyses indicatives et badge du personnel).

## 5.5.13 — 2026-10-26

### Corrigé
- Personnel › Exporter PDF (liste du personnel) : le document porte désormais le signataire configuré pour « Liste du Personnel » (fonction, signature scannée, NOM Prénom) ; ce gabarit n'avait aucun bloc signataire, contrairement à la liste du personnel du module Documents.

## 5.5.12 — 2026-10-26

### Corrigé
- Bulletins de vacation : « Valider » et « Marquer payé » provoquaient une erreur 500 pour tout utilisateur rattaché à un établissement (le contrôle d'établissement lisait un attribut inexistant du bulletin) ; le contrôle porte désormais sur l'année scolaire du bulletin. Les tests du module `vacations` sont ajoutés aux chemins de la suite (ils n'étaient exécutés ni en local ni en CI).

## 5.5.11 — 2026-10-26

### Corrigé
- PDF « Liste des élèves » (Élèves › Exporter PDF) : l'en-tête porte désormais le logo de l'établissement (et le cachet s'il est enregistré) ; la vue ne transmettait pas l'URL du logo au socle PDF.

## 5.5.10 — 2026-10-26

### Corrigé
- Plus aucun trait à l'emplacement de la signature du signataire : attestation de non-redevabilité, certificat de non-redevabilité (le libellé fixe « Le Responsable Financier » et son trait, en doublon du signataire configuré, sont retirés), emplois du temps de classe et de professeur, aperçu écran du certificat de scolarité (la signature scannée y remplace le trait). Les lignes à signer à la main par un tiers (récépissé du parent, contrat, bulletin de salaire, PV de conseil, dossier de transfert) sont conservées.

## 5.5.9 — 2026-10-26

### Corrigé
- Emplois du temps (classe et professeur) : le signataire imprimé (fonction, signature scannée, NOM Prénom) est celui configuré pour le type « Emploi du Temps » ; il n'existait pas et le dernier signataire enregistré sur le cycle, quel que soit son document, était utilisé.
- « Configurer les Signataires » propose dès l'installation tous les documents signés par l'application : Emploi du Temps, Convocation, Circulaire et Autorisation de Congé Personnel (auparavant absents jusqu'à la génération d'un premier document). Migration de données `parametres 0035`.

## 5.5.8 — 2026-10-26

### Corrigé
- Notes et moyennes toujours affichées avec deux décimales (16,00 et non 16 ou 16,0) : relevé de notes à l'écran (notes brutes, notes ramenées sur 20, moyennes de la classe, meilleure et plus basse moyenne, moyenne par évaluation), relevé de notes PDF, fiche discipline PDF et tableau des moyennes par discipline.

## 5.5.7 — 2026-10-26

### Corrigé
- Relevé de notes : un enseignant ne voit plus, dans la liste **Classe**, que les classes où il enseigne (année choisie) et, dans la liste **Discipline**, que ses propres disciplines ; un enseignement d'un collègue passé dans l'adresse est refusé (écran, PDF du relevé et fiche discipline). Direction et censeur conservent la vue complète.

## 5.5.6 — 2026-10-26

### Ajouté
- Carte scolaire (carte individuelle, cartes de classe et aperçu) : le **NOM** et le prénom du signataire sont imprimés sous sa signature, centrés sous la photo ; sans signature scannée, l'espace de 5 mm reste vierge au-dessus du nom. Mise en page de la carte inchangée.

## 5.5.5 — 2026-10-26

### Ajouté
- Carte scolaire (carte individuelle, cartes de classe et aperçu) : la signature scannée du signataire configuré pour la **Carte d'Identité Scolaire** (le directeur) est apposée sous la photo de l'élève, centrée, 5 mm de haut au plus ; la mise en page de la carte (85,6 × 54 mm) est inchangée et l'espace reste vierge sans signature enregistrée.

## 5.5.4 — 2026-10-26

### Corrigé
- Fenêtre « Nouveau type de document » / « Modifier le type de document » : la liste **Cycle** ne proposait que « Tous les cycles » (la vue ne transmettait pas les cycles au gabarit). Elle propose désormais les cycles de l'établissement, dans l'ordre configuré ; un cycle d'un autre établissement est refusé à l'enregistrement.

## 5.5.3 — 2026-10-26

### Corrigé
- Signature scannée du signataire absente de trois gabarits qui imprimaient sa fonction et son nom sans emplacement d'image : circulaire (partiel de signature partagé, également utilisé par la convocation sans bloc propre), emploi du temps de classe et emploi du temps du professeur. L'image occupe l'espace déjà réservé à la signature manuscrite (2 cm, 9 mm, 7 mm) : mise en page et nombre de pages inchangés.

## 5.5.2 — 2026-10-26

### Corrigé
- Signature scannée absente des documents de la catégorie Finance (reçu de paiement, certificat de non-redevabilité, historique des versements, listes et états, avis Mobile Money) ainsi que des PV de conseil, emplois du temps, listes de classe et du personnel, contrats et autorisations : ces PDF étaient rendus sans adresse de base et WeasyPrint ignorait l'URL relative de l'image (nom et fonction imprimés, signature manquante ; même cause pour le cachet de l'en-tête). `core.pdf.HTML` fournit désormais une base interne par défaut : les chemins `/media/` et `/static/` sont toujours résolus sur le disque.
- Relance de paiement : la signature scannée du signataire est apposée dans l'espace de 1 cm réservé entre sa fonction et son nom (mise en page et hauteur des coupons inchangées).

## 5.5.1 — 2026-10-26

### Corrigé
- Certificat de scolarité : le bloc QR code + signature et la barre du bas sont ancrés au bas de la page A5 (hors flux) ; le certificat ne peut plus déborder sur une deuxième page, quelle que soit la longueur de l'en-tête (nom de l'établissement, adresse, contacts), de la filiation ou de la fonction du signataire. Test de rendu réel en pire cas.

## 5.5.0 — 2026-10-26

### Ajouté
- Signataires des documents : champ facultatif **Signature scannée** dans la fenêtre « Configurer les Signataires » (PNG/JPEG, 512 Ko max., contrôle du contenu réel de l'image). L'image est enregistrée sur la fiche du membre du personnel et apposée automatiquement à l'emplacement de sa signature sur tous les documents PDF qu'il signe (bulletins trimestriels et annuels, duplicata, certificats de scolarité, attestations, convocations, autorisations de congé, reçus, listes…), sans changer la hauteur des blocs de signature ; case « Retirer la signature ». Migration `personnel 0009`.


### Corrigé
- Bulletins (trimestriel, duplicata, lot, annuel) : pied de page « Établissement — Généré le JJ/MM/AAAA HH:MM — Document officiel — Toute falsification expose à des poursuites » à gauche, pagination à droite.
- Duplicata du bulletin trimestriel : le bandeau gris est fondu dans le sous-titre (« Duplicata officiel délivré le … — Ce document est une reproduction du bulletin original ») ; le duplicata tient désormais sur une page dans les mêmes conditions que l'original (test étendu).


### Corrigé
- Documents PDF (bulletins, certificats, listes…) : suppression du bandeau de pied de page « Licence PREMIUM — clé — … — Nj restants — YELEN SCHOOL v3.4 — … ». Le filigrane diagonal discret est conservé.


### Corrigé
- Bulletin trimestriel PDF (individuel, duplicata, lot) : chaque bulletin tient sur une seule page A4, y compris avec 16 matières, des noms d'enseignants longs, des sanctions, l'assiduité, l'appréciation du conseil avec mentions et le signataire. Mise en page compactée sans retirer d'information : marges 8/12/10/12 mm, identité de l'élève sur deux lignes, Assiduité et Statistiques côte à côte, colonnes du tableau des notes 25/7/10/9/14/24/11 % (largeurs fixes), mode dense automatique au-delà de 12 matières, bloc signature resserré. Limite documentée : bulletin primaire APC garanti jusqu'à ≈ 10 compétences évaluées.


### Corrigé
- Textes générés automatiquement (appréciation du conseil proposée sur le bulletin, bilan de classe, facteurs de risque et de prédiction) : les nombres s'écrivent à la française — « 11,14/20 », « 66,7 % » — et non « 11.14/20 ».

## 5.3.8 — 2026-10-25

### Corrigé
- Impression par lot des bulletins (trimestriels et annuels) : chaque bulletin est paginé à part — « Page 1 / 1 » sur chaque bulletin, et non « Page 3 / 60 ». Le lot reste un seul fichier PDF (un document WeasyPrint par élève, pages assemblées par `core.pdf.HTML.lot`).

## 5.3.7 — 2026-10-25

### Modifié
- Bulletin trimestriel PDF : la colonne « Signature » du tableau des notes est vide (plus de ligne pointillée en face du nom de chaque professeur) ; l'en-tête de colonne est conservé.

## 5.3.6 — 2026-10-25

### Modifié
- Bulletin trimestriel PDF : colonne « Professeur » élargie (15 % → 21 %) aux dépens de la colonne « Appréciation » (19 % → 13 %) pour les noms et prénoms longs ; largeurs des autres colonnes inchangées, toujours une page par élève.

## 5.3.5 — 2026-10-25

### Corrigé
- Bulletin annuel : la moyenne annuelle est la moyenne des moyennes trimestrielles imprimées sur les bulletins, arrondie au centime supérieur comme elles (avec un seul trimestre saisi, l'annuel est identique au trimestre : 11,63 et non 11,62). Même règle pour le rang, les statistiques de classe et le palmarès annuel ; une moyenne trimestrielle de 0,00 s'imprime au lieu de « — ».

## 5.3.4 — 2026-10-25

- Bulletin trimestriel : légende du code QR supprimée ; « Mentions / distinctions » placées en dernière
  position de la carte « Appréciation du conseil de classe » (après l'appréciation) — idem aperçu écran
  et consultation parent.

## 5.3.3 — 2026-10-25

- Bulletin annuel (individuel et lot) : code QR dans la zone des signatures, sans légende — matricule,
  classe, année scolaire, moyenne annuelle (balise `qr_bulletin_annuel`).

## 5.3.2 — 2026-10-25

- Bulletins trimestriels (individuel, duplicata, classe) : code QR de vérification dans la zone des
  signatures — matricule, classe, trimestre + année, moyenne du trimestre (balise `qr_bulletin`).

## 5.3.1 — 2026-10-25

- Bulletin annuel (individuel et lot de classe) : le N° Agrément s'imprime sous le nom de l'établissement,
  comme sur les bulletins trimestriels.

## 5.3.0 — 2026-10-25

- Nouveau référentiel `Paramètres → Mentions / distinctions` (code, libellé, description, ordre, active ;
  droit d'accès dédié) amorcé avec Félicitations, Tableau d'honneur, Encouragements, Avertissement, Blâme.
- Saisie du bulletin : les mentions actives sont proposées en cases à cocher et enregistrées sur la fiche
  (élève × trimestre) ; badges dans le tableau de classe, impression sur les bulletins trimestriels
  (individuel, duplicata, classe), l'aperçu et la consultation parent.
- Migrations : `parametres 0034`, `bulletins 0006`.

## 5.2.9 — 2026-10-25

- Bulletins trimestriels (individuel, duplicata, classe, aperçu) : impression de la fiche saisie dans
  `Bulletins → Saisir` — carte « Assiduité du trimestre » (absences justifiées, absences non justifiées en
  heures, retards ; 0 sans fiche) et appréciation du conseil de classe saisie, prioritaire sur le commentaire
  généré automatiquement (conservé en repli). Libellé « Appréciation du conseil de classe » aligné sur la modale.

## 5.2.8 — 2026-10-25

### Modifié
- Bulletins trimestriels : le duplicata et le PDF de classe (un élève par page) reprennent exactement le modèle du bulletin individuel, désormais partagé (style et corps en `pedagogie/pdf/partials/`).
- En-tête des bulletins trimestriels : le N° Agrément de l'établissement apparaît sous son nom.

### Corrigé
- Sanctions disciplinaires : l'enregistrement échouait en production (journal d'audit) — représentation textuelle corrigée (`type_sanction` est une relation).

## 5.2.7 — 2026-10-24

### Corrigé
- Bulletins trimestriels (individuel, duplicata, classe) : dans le tableau des matières, la colonne « Rang » est remplacée par « Note pond. » = moyenne /20 × coefficient ; « — » si l'élève est dispensé. Le rang général de l'élève reste affiché dans le récapitulatif.
- Aperçu du bulletin à l'écran : la colonne « Points », restée vide, affiche désormais la même note pondérée.

## 5.2.6 — 2026-10-24

- Bulletins d'une classe : la colonne Actions (5 % de la largeur) rognait trois des quatre boutons ;
  largeurs de colonnes revues, les quatre boutons sont visibles dès 1280 px et passent à la ligne
  en dessous au lieu d'être coupés.

## 5.2.5 — 2026-10-24

- Bulletins trimestriels PDF : le total de points est rapporté au maximum possible (coefficients × 20),
  par exemple « 112,00 / 140 » ; le bulletin de classe affichait la somme des coefficients (« / 7,00 »).

## 5.2.4 — 2026-10-24

- `mettre-a-jour.bat` : la reconstruction de l'image échouait (« failed to get console: The handle is
  invalid ») car la progression interactive de Docker n'a pas de console quand la sortie est journalisée ;
  `--progress plain` sur les reconstructions (mise à jour et retour arrière).

## 5.2.3 — 2026-10-24

- Aperçu du bulletin : les boutons « Générer le PDF » / « Télécharger le PDF » renvoyaient une page
  introuvable (adresse écrite à la main) ; adresses désormais résolues par nom de route, retour de
  l'aperçu annuel corrigé.

## 5.2.2 — 2026-10-24

- Relance de paiement (PDF) : ligne « Contact parent » retirée du coupon.

## 5.2.1 — 2026-10-24

- Relance de paiement (PDF) : le signataire apparaît de nouveau — type de document « Relance de Paiement »
  (catégorie Finance) ajouté aux signataires configurables, signataires Finance existants repris
  (migration `parametres 0033`), résolution avec repli identique aux autres documents.

## 5.2.0 — 2026-10-24

- Performance : index de base de données sur les tables métier (appels et présences par date/statut,
  paiements par date, élèves par nom) — migrations `presences 0005`, `finances 0021`, `inscriptions 0019`.
- Accessibilité : lien d'évitement, états des menus (`aria-expanded`, `aria-current`), noms accessibles des
  boutons icône, étiquettes de champs, dialogues de confirmation au clavier, focus visible, animations
  réduites sur demande.
- Aide en ligne : le guide d'utilisation est consultable dans l'application (`/aide/`, sommaire latéral,
  captures d'écran, bouton **Aide** contextuel dans le menu) ; guide : blocs de code et structure du
  chapitre 6 corrigés.

## 5.1.0 — 2026-10-23

- Mise à jour en un clic : `mettre-a-jour.bat` (sauvegarde chiffrée, récupération GitHub, reconstruction,
  redémarrage, contrôle de `/health/`, retour arrière automatique ; journal `logs\mise-a-jour.log`).
- Version unique lue dans `VERSION` : menu latéral, page de connexion, `/health/`.
- Fin du Ctrl+F5 après mise à jour : cache du Service Worker nommé par version et rechargement
  automatique des pages ouvertes dès que le nouveau worker prend le contrôle.
- Gabarits PDF : socle commun (`templates/pdf/base.html`) et en-tête d'établissement unique.
- Qualité : seuil de couverture 65 %, exceptions journalisées, dépendances Dependabot alignées.

## 5.0 — versions antérieures

Historique dans `git log` et dans le guide d'utilisation (§33).
