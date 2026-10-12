"""
Format de sérialisation ``jsonl_us`` : JSON Lines conservant les microsecondes.

Le sérialiseur ``jsonl`` de Django tronque les datetimes à la milliseconde
(``DjangoJSONEncoder``, compatibilité ECMA-262). Or le journal d'audit hache
``timestamp.isoformat()`` et la signature HMAC des licences couvre
``date_activation`` à la microseconde : un transfert en ``jsonl`` romprait la
chaîne d'audit et invaliderait les licences. Déclaré dans
``settings.SERIALIZATION_MODULES`` ; utilisé par ``exporter_donnees`` /
``importer_donnees`` et lisible par ``loaddata`` (extension ``.jsonl_us``).
"""
import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers.jsonl import Deserializer  # noqa: F401 — désérialisation inchangée
from django.core.serializers.jsonl import Serializer as JsonlSerializer


class EncodeurMicrosecondes(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.time)):
            return o.isoformat()
        return super().default(o)


class Serializer(JsonlSerializer):
    def _init_options(self):
        super()._init_options()
        self.json_kwargs['cls'] = EncodeurMicrosecondes
        self._cles_naturelles = {}

    def handle_fk_field(self, obj, field):
        """Clé naturelle mémorisée par objet lié : une requête par utilisateur
        au lieu d'une par ligne exportée (created_by, updated_by, encaisse_par…)."""
        modele = field.remote_field.model
        if not (self.use_natural_foreign_keys and hasattr(modele, 'natural_key')):
            return super().handle_fk_field(obj, field)
        pk = getattr(obj, field.attname)
        cle = (modele, pk)
        if cle not in self._cles_naturelles:
            self._cles_naturelles[cle] = None if pk is None else modele._default_manager.get(pk=pk).natural_key()
        self._current[field.name] = self._cles_naturelles[cle]
