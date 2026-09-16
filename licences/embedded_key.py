"""Clé publique de vérification des licences YELEN SCHOOL.

Cette valeur est volontairement embarquée dans le code distribué. Elle doit être
remplacée par la clé publique Ed25519 officielle avant de construire une version
commerciale. La clé privée correspondante ne doit jamais être incluse dans le
projet, l'installateur, le conteneur ou la machine cliente.

Le contenu de ce module fait partie de la racine de confiance de l'application.
Toute modification de ce fichier doit donc être couverte par la signature de la
version distribuée.
"""

# Base64 standard de 32 octets. Valeur vide = aucune version commerciale
# configurée : toutes les licences signées sont alors refusées par défaut.
ED25519_PUBLIC_KEY_B64 = ""
