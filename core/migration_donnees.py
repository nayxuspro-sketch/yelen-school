"""
Transfert des données entre deux installations YELEN SCHOOL
(changement de serveur, passage du mode autonome SQLite à PostgreSQL).

Archive ZIP produite par ``exporter_donnees`` et lue par ``importer_donnees`` :

- ``donnees.jsonl_us`` : sortie de ``dumpdata --format jsonl_us --all
  --natural-foreign`` (JSON Lines avec microsecondes, voir ``core.serialisation`` ;
  rechargeable par ``loaddata``) ;
- ``manifeste.json`` : effectifs par modèle, migrations appliquées et empreinte
  des clés secrètes, contrôlés avant et après l'import.

``charger_fichier`` recharge le fichier de données par lots (équivalent rapide
de ``loaddata``).
"""
import hashlib
import json
from contextlib import contextmanager

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management.color import no_style
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder

VERSION_MANIFESTE = 1
FORMAT_DONNEES = 'jsonl_us'
MEMBRE_DONNEES = f'donnees.{FORMAT_DONNEES}'
MEMBRE_MANIFESTE = 'manifeste.json'

# Tables techniques recréées par `migrate` sur la base cible ; les références
# (permissions, types de contenu) sont exportées sous forme de clés naturelles.
# Les sessions sont transitoires.
EXCLUSIONS = ('contenttypes', 'auth.permission', 'sessions')

# Lignes créées par des migrations de données (parametres 0002, 0015, 0019) :
# présentes sur une base cible vierge, elles sont remplacées par celles de la source.
MODELES_INITIALISES_PAR_MIGRATE = frozenset({'parametres.typedocument'})


def fmt_nombre(n):
    """1234567 → '1 234 567' (séparateur de milliers lisible dans toute console)."""
    return f'{n:,}'.replace(',', ' ')


def empreinte_cles():
    """Empreinte non réversible des clés secrètes dont dépendent les données
    (chiffrement ``core.encryption``, signature HMAC des licences)."""
    secret = f"{settings.SECRET_KEY}\n{getattr(settings, 'LICENCE_SIGNING_KEY', '')}"
    return hashlib.sha256(secret.encode()).hexdigest()[:16]


def migrations_appliquees(using='default'):
    recorder = MigrationRecorder(connections[using])
    return sorted(f'{app}.{nom}' for app, nom in recorder.applied_migrations())


def effectifs_base(labels, using='default'):
    """Nombre de lignes par modèle (gestionnaire de base : aucun filtre)."""
    return {label: apps.get_model(label)._base_manager.using(using).count() for label in labels}


def effectifs_fichier(chemin):
    """Nombre d'objets par modèle dans un fichier JSONL produit par ``dumpdata``."""
    effectifs = {}
    with open(chemin, encoding='utf-8') as fh:
        for ligne in fh:
            if ligne.strip():
                label = json.loads(ligne)['model']
                effectifs[label] = effectifs.get(label, 0) + 1
    return dict(sorted(effectifs.items()))


@contextmanager
def _horodatages_preserves():
    """Suspend ``auto_now`` / ``auto_now_add`` le temps de l'import : ``bulk_create``
    appelle ``pre_save()``, qui écraserait les ``created_at`` / ``updated_at`` importés."""
    champs = [champ for modele in apps.get_models() for champ in modele._meta.fields
              if getattr(champ, 'auto_now', False) or getattr(champ, 'auto_now_add', False)]
    etats = [(champ, champ.auto_now, champ.auto_now_add) for champ in champs]
    for champ in champs:
        champ.auto_now = champ.auto_now_add = False
    try:
        yield
    finally:
        for champ, auto_now, auto_now_add in etats:
            champ.auto_now, champ.auto_now_add = auto_now, auto_now_add


def charger_fichier(chemin, using='default', taille_lot=1000):
    """Charge un fichier ``dumpdata`` par lots ``bulk_create`` (à appeler dans une transaction).

    Même désérialiseur, références en avant, many-to-many, contrôle des contraintes
    et remise à niveau des séquences que ``loaddata``, mais une requête par lot au
    lieu d'un UPDATE + INSERT par objet (≈ 10 fois plus rapide sur une grande base).
    Comme pour un chargement brut, ni ``save()`` ni les signaux ne sont appelés.
    Retourne les modèles chargés.
    """
    connection = connections[using]
    modeles, differes, lot = [], [], []

    def vider():
        if not lot:
            return
        type(lot[0].object)._base_manager.using(using).bulk_create(
            [objet.object for objet in lot], batch_size=taille_lot)
        for objet in lot:
            for champ, valeurs in (objet.m2m_data or {}).items():
                getattr(objet.object, champ).set(valeurs)
        lot.clear()

    with _horodatages_preserves(), open(chemin, encoding='utf-8') as fh:
        for objet in serializers.deserialize(FORMAT_DONNEES, fh, using=using, handle_forward_references=True):
            modele = type(objet.object)
            if lot and type(lot[0].object) is not modele:
                vider()
            if modele not in modeles:
                modeles.append(modele)
            lot.append(objet)
            if objet.deferred_fields:
                differes.append(objet)
            if len(lot) >= taille_lot:
                vider()
        vider()
        for objet in differes:
            objet.save_deferred_fields(using=using)
    connection.check_constraints()
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), modeles):
            cursor.execute(sql)
    return modeles
