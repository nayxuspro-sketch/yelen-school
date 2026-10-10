"""Contrôles unitaires de l'audit ; les scénarios PostgreSQL sont séparés."""

import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from core.audit import record_audit
from core.models import AuditLog
from core.signals import _SENSITIVE_FIELDS, _snapshot
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
    # Seuls les champs réellement portés par le modèle Licence sont utilisés :
    # la signature HMAC est le secret à ne jamais retrouver dans l'audit.
    licence = Licence(
        cle_licence='YELEN-TEST-0001',
        signature_hmac='hmac-secret',
        notes_interne='note interne non sensible',
    )
    bulletin = Bulletin(token_signature='parent-response-token')

    licence_snapshot = _snapshot(licence)
    bulletin_snapshot = _snapshot(bulletin)

    assert 'hmac-secret' not in repr(licence_snapshot)
    assert 'signature_hmac' not in licence_snapshot
    assert licence_snapshot.get('cle_licence') == 'YELEN-TEST-0001'
    # Les noms de champs sensibles additionnels restent couverts par la liste noire.
    for name in ('signature_ed25519', 'signed_payload', 'private_key', 'totp_secret'):
        assert name in _SENSITIVE_FIELDS
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


# ── Entrées antérieures au chaînage (bases migrées depuis une version < 5.0) ──

def _entree_sans_hash():
    """Simule une entrée écrite avant core.0004 : hashes vides (écriture hors ORM métier)."""
    entree = record_audit(action='UPDATE', changes={}, source='SYSTEM', object_id='legacy',
                          app_label='finances', model_name='paiement', object_repr='ancien')
    AuditLog._base_manager.filter(pk=entree.pk).update(entry_hash='', previous_hash='')
    return entree


@pytest.mark.django_db(transaction=True)
def test_verification_tolere_les_entrees_anterieures_en_prefixe():
    from core.audit import verify_audit_chain
    for _ in range(3):
        _entree_sans_hash()
    record_audit(action='SECURITY', changes={'event': 'a'}, source='SYSTEM')
    record_audit(action='SECURITY', changes={'event': 'b'}, source='SYSTEM')

    resultat = verify_audit_chain()

    assert resultat['ok'] is True
    assert resultat['checked'] == 5
    assert resultat['legacy'] == 3
    assert resultat['invalid'] == []


@pytest.mark.django_db(transaction=True)
def test_entree_sans_hash_apres_le_debut_de_la_chaine_est_invalide():
    from core.audit import verify_audit_chain
    record_audit(action='SECURITY', changes={'event': 'a'}, source='SYSTEM')
    intruse = _entree_sans_hash()

    resultat = verify_audit_chain()

    assert resultat['ok'] is False
    assert resultat['legacy'] == 0
    assert str(intruse.pk) in resultat['invalid']


@pytest.mark.django_db(transaction=True)
def test_commande_signale_les_entrees_anterieures(capsys):
    from django.core.management import call_command
    _entree_sans_hash()
    record_audit(action='SECURITY', changes={'event': 'a'}, source='SYSTEM')

    call_command('verify_audit_chain')

    sortie = capsys.readouterr().out
    assert '1 entrée(s) chaînée(s)' in sortie
    assert '1 entrée(s) antérieure(s) au chaînage' in sortie
