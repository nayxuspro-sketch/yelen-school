GUIDE D'UTILISATION DE LA TROUSSE D'OUTILS ANTI-COPIE (ÉDITEUR)
========================================================================

Ce dossier contient les outils d'enrôlement et de verrouillage matériel à conserver
SUR VOTRE CLÉ USB TECHNIQUE D'INSTALLATEUR, et à NE PAS LAISSER sur le PC du client.

FICHIERS INCLUS :
-----------------
1. activer-binding-materiel.bat
   - À exécuter en tant qu'administrateur chez le client lors du déploiement.
   - Lit l'UUID de la carte mère, le processeur et le disque système.
   - Injecte ces valeurs dans le fichier .env du client avec LICENSE_ENFORCEMENT=true.
   - Rend le serveur incapable de tourner sur un autre ordinateur.

2. verrouiller-dossier-anti-copie.bat
   - À exécuter en tant qu'administrateur après l'installation.
   - Supprime les droits de lecture/copie pour les utilisateurs standards, invités et tout le monde.
   - Réserve l'accès exclusivement au groupe "Administrateurs" et au "Système" Windows.
   - Masque et surprotège le fichier .env (attrib +h +s).

PROCÉDURE CHEZ LE CLIENT :
--------------------------
1. Branchez votre clé USB contenant ce dossier "outils-editeur".
2. Clic droit sur "activer-binding-materiel.bat" > Exécuter en tant qu'administrateur.
3. Clic droit sur "verrouiller-dossier-anti-copie.bat" > Exécuter en tant qu'administrateur.
4. Lancez "demarrage.bat" pour tester le bon fonctionnement de l'application.
5. Débranchez votre clé USB : la machine cliente est sécurisée sans qu'aucun script
   d'enrôlement ne reste accessible localement.
