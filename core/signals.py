"""Signaux d'audit pour les modèles métier.

Les changements sont capturés avant l'écriture afin de conserver réellement
l'ancien et le nouveau contenu. Les signaux fonctionnent aussi hors HTTP : une
commande ou une tâche est alors marquée ``source=SYSTEM``.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID
import hashlib

from django.db.models.signals import post_save, pre_delete, pre_save

from core.audit import record_audit
from yelen_school.audit_middleware import get_request


_audit_disabled = False
_SENSITIVE_FIELDS = frozenset({
    'password', 'totp_secret', 'token', 'secret', 'private_key',
    'signature_ed25519', 'signed_payload', 'api_key', 'access_token',
})


def _fingerprint(value):
    if value is None:
        return ''
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


def disable_audit():
    global _audit_disabled
    _audit_disabled = True


def enable_audit():
    global _audit_disabled
    _audit_disabled = False


def _serialise(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return str(value)


def _snapshot(instance):
    values = {}
    for field in instance._meta.concrete_fields:
        if field.name in {'created_at', 'updated_at'} or field.name in _SENSITIVE_FIELDS:
            continue
        values[field.name] = _serialise(getattr(instance, field.attname, None))
    return values


def _sensitive_fingerprints(instance):
    return {
        field.name: _fingerprint(getattr(instance, field.attname, None))
        for field in instance._meta.concrete_fields
        if field.name in _SENSITIVE_FIELDS
    }


def _changes(old, new):
    keys = sorted(set(old) | set(new))
    return {
        key: {'old': old.get(key), 'new': new.get(key)}
        for key in keys
        if old.get(key) != new.get(key)
    }


def _eligible(sender):
    from core.models import AuditLog
    return sender is not AuditLog and hasattr(sender, '_meta') and hasattr(sender, 'created_at')


def _capture_before_save(sender, instance, **kwargs):
    if _audit_disabled or not _eligible(sender) or not instance.pk:
        instance._audit_old_values = {}
        instance._audit_old_sensitive = {}
        return
    try:
        old = sender.objects.get(pk=instance.pk)
        instance._audit_old_values = _snapshot(old)
        instance._audit_old_sensitive = _sensitive_fingerprints(old)
    except sender.DoesNotExist:
        instance._audit_old_values = {}
        instance._audit_old_sensitive = {}


def _audit_saved(sender, instance, created, **kwargs):
    if _audit_disabled or not _eligible(sender):
        return
    new = _snapshot(instance)
    old = getattr(instance, '_audit_old_values', {})
    old_sensitive = getattr(instance, '_audit_old_sensitive', {})
    new_sensitive = _sensitive_fingerprints(instance)
    sensitive_changed = sorted(
        name for name in set(old_sensitive) | set(new_sensitive)
        if old_sensitive.get(name) != new_sensitive.get(name)
    )
    action = 'CREATE' if created else 'UPDATE'
    changes = {'new': new} if created else _changes(old, new)
    if sensitive_changed:
        changes['sensitive_fields_changed'] = sensitive_changed
    elif created and any(new_sensitive.values()):
        changes['sensitive_fields_present'] = sorted(
            name for name, fingerprint in new_sensitive.items() if fingerprint
        )
    record_audit(
        instance=instance,
        action=action,
        changes=changes,
        request=get_request(),
        reason=getattr(instance, '_audit_reason', ''),
    )
    instance._audit_old_values = {}


def _audit_deleted(sender, instance, **kwargs):
    if _audit_disabled or not _eligible(sender):
        return
    record_audit(
        instance=instance,
        action='DELETE',
        changes={'old': _snapshot(instance)},
        request=get_request(),
        reason=getattr(instance, '_audit_reason', ''),
    )


def setup_audit_signals():
    """Branche l'audit aux modèles métier BaseModel, une seule fois par label."""
    from django.apps import apps

    for model in apps.get_models():
        if model._meta.proxy or not hasattr(model, 'created_at'):
            continue
        label = model._meta.label
        pre_save.connect(_capture_before_save, sender=model, dispatch_uid=f'audit_before_{label}')
        post_save.connect(_audit_saved, sender=model, dispatch_uid=f'audit_save_{label}')
        pre_delete.connect(_audit_deleted, sender=model, dispatch_uid=f'audit_delete_{label}')


setup_audit_signals()
