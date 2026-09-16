# Licence commerciale Ed25519

## Principe

YELEN SCHOOL ne doit pas utiliser `SECRET_KEY` pour fabriquer ou valider une
licence commerciale. Cette clé existe chez le client et peut donc être lue par
un administrateur de la machine.

Le mécanisme cible est :

1. le fournisseur conserve une clé privée Ed25519 hors du dépôt et hors des
   installations clientes ;
2. la clé publique est embarquée dans `licences/embedded_key.py` lors du build ;
3. le fournisseur émet un fichier JSON signé ;
4. le client importe ce fichier hors ligne ;
5. le payload est lié à l'établissement, aux limites, aux fonctionnalités, à la
   date d'expiration, à un nonce et, pour une activation commerciale, à
   l'empreinte du serveur ;
6. l'application vérifie la signature avant d'autoriser l'utilisation.

La clé publique n'est volontairement pas lue depuis `.env` en production : une
clé publique configurable par le client ne serait pas une racine de confiance.

## Commandes fournisseur

Dépendances installées depuis `requirements/base.txt` :

```text
cryptography>=42.0,<47.0
```

Générer une paire sur un poste fournisseur isolé :

```powershell
$env:YELEN_LICENSE_PRIVATE_KEY_PASSWORD = "mot-de-passe-géré-par-le-coffre"
python manage.py generate_license_keys `
  --private-output C:\coffre\yelen-license-private.pem `
  --public-output C:\coffre\yelen-license-public.b64
```

Le fichier privé ne doit jamais être copié dans le dépôt, l'installateur, le
serveur client, Docker ou une sauvegarde distribuée.

Avant le build commercial, intégrer la seule valeur publique dans
`licences/embedded_key.py`, puis signer le paquet de l'application. Une valeur
vide est volontairement refusée.

Émettre une licence liée à un serveur :

```powershell
$env:YELEN_LICENSE_PRIVATE_KEY_PASSWORD = "..."
python manage.py issue_license `
  --etablissement-id "UUID_ETABLISSEMENT" `
  --type STANDARD `
  --expires 2027-09-16 `
  --server-fingerprint "EMPREINTE_SHA256_64_HEX" `
  --private-key C:\coffre\yelen-license-private.pem `
  --output C:\livraison\licence.json
```

## Commande client

L'import vérifie la signature **avant toute écriture** :

```powershell
python manage.py import_license C:\livraison\licence.json --activate
```

`--server-fingerprint` est obligatoire à l'émission et doit être une empreinte
SHA-256 hexadécimale de 64 caractères ; l'import refuse aussi un payload non lié.
`--activate` exige ensuite que cette empreinte corresponde à la machine courante.
Un fichier altéré, expiré, destiné à un autre établissement ou signé pour un
autre serveur est refusé.

## Limites et concurrence

Les limites présentes dans le payload signé sont les seules limites
commerciales utilisées. Une valeur `0` signifie explicitement « aucune
ressource autorisée » ; elle n'est pas interprétée comme une absence de plafond.
Les profils sans limite utilisent une grande valeur explicite, jamais une
valeur nulle implicite.

Les créations qui consomment une capacité verrouillent la ligne PostgreSQL de
la licence, recomptent la ressource et effectuent la création dans la même
transaction. Cette protection doit être validée avec PostgreSQL avant une
release commerciale ; SQLite n'est pas un substitut accepté.

## Transition

Les licences historiques HMAC sont conservées pour permettre une migration
contrôlée, mais `ALLOW_LEGACY_HMAC_LICENSES` est `False` par défaut et ne doit
pas être activé dans une distribution commerciale. Le middleware de licence ne
doit être décommenté qu'après :

- intégration de la clé publique officielle ;
- émission/import d'une licence Ed25519 de test ;
- validation de l'expiration, de la copie sur une autre machine et de la
  falsification de chaque champ ;
- validation PostgreSQL sur Windows client.
