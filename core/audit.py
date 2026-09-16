"""Service d'écriture d'audit utilisé par HTTP, commandes et tâches."""

from __future__ import annotations

import uuid


def _establishment_from_instance(instance):
    """Déduit l'établissement sans supposer un seul nom de relation."""
    for attr in ('etablissement', 'classe', 'personnel', 'inscription', 'user'):
        try:
            related = getattr(instance, attr)
        except Exception:
            continue
        if attr == 'etablissement':
            return related
        try:
            etab = getattr(related, 'etablissement', None)
            if etab is not None:
                return etab
        except Exception:
            continue
    return None


def record_audit(
    *,
    instance=None,
    action: str,
    changes: dict | None = None,
    user=None,
    request=None,
    reason: str = '',
    source: str | None = None,
    object_id=None,
    object_repr: str | None = None,
    app_label: str | None = None,
    model_name: str | None = None,
):
    """Ajoute une trace append-only avec contexte complet.

    Cette fonction est volontairement le point d'entrée commun. Elle fonctionne
    en HTTP comme depuis une commande de gestion ou une tâche Celery, avec
    ``source='SYSTEM'`` lorsqu'aucune requête n'existe.
    """
    from core.models import AuditLog

    request_user = getattr(request, 'user', None) if request else None
    if user is None and getattr(request_user, 'is_authenticated', False):
        user = request_user
    if user is None:
        user = getattr(instance, '_current_user', None)

    etab = _establishment_from_instance(instance) if instance is not None else None
    if etab is None and user is not None:
        etab = getattr(user, 'etablissement', None)

    ip_address = None
    user_agent = ''
    request_id = ''
    if request is not None:
        from yelen_school.audit_middleware import get_client_ip
        ip_address = get_client_ip(request)
        user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:500]
        request_id = str(getattr(request, 'audit_request_id', '') or '')

    pk = object_id if object_id is not None else getattr(instance, 'pk', None)
    if pk is None:
        pk = 'system'
    meta = getattr(instance, '_meta', None)
    resolved_app_label = app_label or getattr(meta, 'app_label', 'system')
    resolved_model_name = model_name or getattr(meta, 'model_name', 'event')

    return AuditLog.objects.create(
        user=user,
        etablissement=etab,
        action=action,
        app_label=resolved_app_label,
        model_name=resolved_model_name,
        object_id=str(pk),
        object_repr=(object_repr or str(instance) if instance is not None else object_repr or 'Événement système')[:200],
        changes=changes or {},
        reason=reason[:5000],
        ip_address=ip_address,
        user_agent=user_agent,
        source=source or ('HTTP' if request is not None else 'SYSTEM'),
        request_id=request_id or str(uuid.uuid4()),
    )


def verify_audit_chain(limit: int | None = None) -> dict:
    """Vérifie la chaîne et retourne les entrées corrompues."""
    from core.models import AuditLog

    queryset = AuditLog.objects.order_by('id')
    if limit:
        queryset = queryset[:limit]
    previous = ''
    invalid = []
    for entry in queryset:
        if entry.previous_hash != previous or not entry.verifier_chaine():
            invalid.append(str(entry.pk))
        previous = entry.entry_hash
    return {'ok': not invalid, 'checked': queryset.count(), 'invalid': invalid}
