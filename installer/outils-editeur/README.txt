OUTILS ÉDITEUR — VERROUILLAGE DU SERVEUR CLIENT
========================================================================

Couche « système » de la protection anti-copie. La protection principale est la
licence signée par l'éditeur et liée au serveur (docs/GUIDE_DEPLOIEMENT_WINDOWS.md
§3.5) : sans elle, verrouiller le dossier ne sert qu'à gêner la copie.

FICHIERS :
----------
1. verrouiller-serveur.bat / verrouiller-serveur.ps1
   - Clic droit > Exécuter en tant qu'administrateur, après activation de la licence.
   - Permissions NTFS : héritage supprimé, contrôle total réservé à SYSTEM, aux
     Administrateurs et au compte qui exécute le script (celui qui démarre Docker
     Desktop) ; option -ComptesAutorises "PC\compte" pour en ajouter.
   - Fichier .env protégé explicitement.
   - Partages réseau exposant le dossier supprimés.
   - Audit NTFS : accès refusés au dossier et lectures du .env journalisés
     (Observateur d'événements > Sécurité, événement 4663).
   - État BitLocker vérifié (recommandation, pas d'activation automatique).
   - Liste des administrateurs locaux affichée : le personnel doit utiliser des
     comptes Windows standards.
   - Groupes désignés par SID : fonctionne sur Windows en français et en anglais.

2. deverrouiller-serveur.bat / deverrouiller-serveur.ps1
   - Pour une maintenance sur site : rétablit l'héritage des permissions et
     retire les règles d'audit. Ré-exécuter verrouiller-serveur.bat avant de partir.

3. emettre-licence.ps1
   - Outil de l'éditeur (poste ou environnement de test, jamais sur un serveur client).
   - Lit LICENCE_PRIVATE_KEY dans le fichier des clés (C:\YELEN-EDITEUR\cles-editeur.txt,
     créé par creer-environnement-test.bat ; -FichierCles pour un autre emplacement) et
     exécute manage.py emettre_licence (image Docker du dossier ou .venv autonome).
   - powershell -NoProfile -ExecutionPolicy Bypass -File installer\outils-editeur\emettre-licence.ps1
       -Etablissement <uuid> -Type STARTER|STANDARD|PREMIUM|RESEAU -Expiration AAAA-MM-JJ
       [-Empreinte <64 hex>] [-Cle YELEN-XXXX-XXXX-XXXX] [-Activation AAAA-MM-JJ]
   - Affiche le code YELEN3.… à coller dans Licences > Activer ; n'écrit rien en base.

ESSAI AVANT LA PRODUCTION :
---------------------------
creer-environnement-test.bat (dossier de production) crée C:\YELEN-TEST : même version, copie de
la dernière sauvegarde, contrôle des licences actif, bandeau « ENVIRONNEMENT DE TEST »
(docs/GUIDE_DEPLOIEMENT_WINDOWS.md §3.5.7).

PROCÉDURE CHEZ LE CLIENT (résumé) :
-----------------------------------
1. Licence : LICENCE_PUBLIC_KEY dans .env, démarrage par demarrage.bat ou
   installer\start-local.ps1, identifiants relevés sur Licences > Activer, code
   YELEN3 émis par l'éditeur (manage.py emettre_licence) et collé par le Super Admin.
2. .env : LICENSE_ENFORCEMENT=true, LICENCE_BINDING_ENABLED=true
   (+ LICENCE_ANTITAMPER_ENABLED=true), redémarrage par start-local.ps1.
3. verrouiller-serveur.bat en administrateur.

Ces scripts peuvent rester sur le serveur : ils n'ont d'effet qu'avec des droits
d'administrateur, qui permettent de toute façon de modifier les permissions.
