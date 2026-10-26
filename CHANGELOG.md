# Journal des versions

Format : une entrée par version livrée (`VERSION` + tag `vX.Y.Z`). Les correctifs incrémentent le
troisième chiffre, les évolutions fonctionnelles le deuxième, les changements de rupture le premier.

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
