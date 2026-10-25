# Journal des versions

Format : une entrée par version livrée (`VERSION` + tag `vX.Y.Z`). Les correctifs incrémentent le
troisième chiffre, les évolutions fonctionnelles le deuxième, les changements de rupture le premier.

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
