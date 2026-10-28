# Journal des versions

Format : une entrée par version livrée (`VERSION` + tag `vX.Y.Z`). Les correctifs incrémentent le
troisième chiffre, les évolutions fonctionnelles le deuxième, les changements de rupture le premier.

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
