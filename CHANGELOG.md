# Journal des versions

Format : une entrée par version livrée (`VERSION` + tag `vX.Y.Z`). Les correctifs incrémentent le
troisième chiffre, les évolutions fonctionnelles le deuxième, les changements de rupture le premier.

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
