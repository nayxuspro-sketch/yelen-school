"""Contrôles unitaires de l'audit ; les scénarios PostgreSQL sont séparés."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from core.audit import record_audit
from core.models import AuditLog
from core.signals import _snapshot
from accounts.models import User
from bulletins.models import Bulletin
from licences.models import Licence
from yelen_school.audit_middleware import get_client_ip


def test_client_ip_does_not_trust_forwarded_header_by_default(rf):
    request = rf.get('/', HTTP_X_FORWARDED_FOR='203.0.113.99')
    request.META['REMOTE_ADDR'] = '192.0.2.20'
    assert get_client_ip(request) == '192.0.2.20'


def test_record_audit_carries_request_context_and_old_new_payload(rf):
    request = rf.post('/', HTTP_USER_AGENT='Test browser')
    request.META['REMOTE_ADDR'] = '192.0.2.20'
    request.user = SimpleNamespace(is_authenticated=True, pk='user-1', etablissement=None)
    request.audit_request_id = 'request-1'
    instance = SimpleNamespace(
        pk='object-1',
        _meta=SimpleNamespace(app_label='tests', model_name='object'),
    )

    with patch('core.models.AuditLog.objects.create') as create:
        record_audit(
            instance=instance,
            action='UPDATE',
            changes={'name': {'old': 'A', 'new': 'B'}},
            request=request,
            reason='Correction validée',
        )

    kwargs = create.call_args.kwargs
    assert kwargs['object_id'] == 'object-1'
    assert kwargs['changes']['name']['old'] == 'A'
    assert kwargs['changes']['name']['new'] == 'B'
    assert kwargs['ip_address'] == '192.0.2.20'
    assert kwargs['user_agent'] == 'Test browser'
    assert kwargs['request_id'] == 'request-1'
    assert kwargs['reason'] == 'Correction validée'


def test_audit_snapshot_never_stores_password_or_totp_secret():
    user = User(password='raw-password', totp_secret='BASE32-SECRET')
    snapshot = _snapshot(user)
    assert 'password' not in snapshot
    assert 'totp_secret' not in snapshot
    assert 'raw-password' not in repr(snapshot)
    assert 'BASE32-SECRET' not in repr(snapshot)


def test_audit_snapshot_never_stores_license_signatures_or_response_tokens():
    licence = Licence(
        signature_hmac='hmac-secret',
        signature_ed25519='ed25519-secret',
        signed_payload={'max_eleves': 500, 'private_key': 'must-not-leak'},
    )
    bulletin = Bulletin(token_signature='parent-response-token')

    licence_snapshot = _snapshot(licence)
    bulletin_snapshot = _snapshot(bulletin)

    for value in ('hmac-secret', 'ed25519-secret', 'must-not-leak'):
        assert value not in repr(licence_snapshot)
    assert 'signature_hmac' not in licence_snapshot
    assert 'signature_ed25519' not in licence_snapshot
    assert 'signed_payload' not in licence_snapshot
    assert 'parent-response-token' not in repr(bulletin_snapshot)
    assert 'token_signature' not in bulletin_snapshot


def test_audit_hash_is_deterministic_for_same_payload():
    entry = AuditLog(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        action='SECURITY',
        app_label='accounts',
        model_name='user',
        object_id='1',
        object_repr='user',
        changes={'old': {'x': 1}, 'new': {'x': 2}},
        previous_hash='abc',
    )
    first = entry._hash_content()
    second = entry._hash_content()
    assert first == second
