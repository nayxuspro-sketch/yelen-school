# Journal des versions

Format : une entrée par version livrée (`VERSION` + tag `vX.Y.Z`). Les correctifs incrémentent le
troisième chiffre, les évolutions fonctionnelles le deuxième, les changements de rupture le premier.

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
