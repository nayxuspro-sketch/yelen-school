"""Tests ciblés des garde-fous licence sans dépendre d'une base de test."""

from contextlib import nullcontext
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.contrib.messages.storage.cookie import CookieStorage
from django.test import RequestFactory, override_settings

from licences.limits import LicenceLimitExceeded, reserve_limit
from licences.middleware import LicenceCheckMiddleware
from licences.models import StatutLicence


@pytest.fixture
def request_factory():
    return RequestFactory()


def _request(request_factory, path="/", *, superuser=False):
    request = request_factory.get(path)
    request.user = SimpleNamespace(
        is_authenticated=True,
        is_superuser=superuser,
        etablissement=None,
    )
    request._messages = CookieStorage(request)
    return request


def _licence(**overrides):
    values = {
        "pk": "licence-1",
        "signature_ed25519": "signature",
        "signature_hmac": "legacy",
        "signed_payload": {"server_fingerprint": "fingerprint"},
        "statut": StatutLicence.ACTIVE,
        "date_expiration": date.today() + timedelta(days=30),
        "utilise_signature_forte": True,
    }
    values.update(overrides)
    licence = SimpleNamespace(**values)
    licence.utilise_signature_forte = bool(
        licence.signature_ed25519 and licence.signed_payload
    )
    licence.verifier_signature = Mock(return_value=True)
    licence.est_liee_au_serveur = Mock(return_value=True)
    licence.jours_restants = Mock(return_value=30)
    licence.etablissement = SimpleNamespace()
    return licence


def test_superuser_does_not_bypass_license_by_default(request_factory):
    request = _request(request_factory, superuser=True)
    request.user.etablissement = SimpleNamespace(licence=_licence(signature_ed25519=""))
    get_response = Mock(return_value="allowed")

    with override_settings(LICENSE_ENFORCEMENT_ENABLED=True, LICENSE_ALLOW_SUPERUSER_BYPASS=False):
        with patch("licences.middleware.cache") as cache:
            cache.get.return_value = None
            with patch("licences.middleware.LicenceAuditLog.objects.create"):
                response = LicenceCheckMiddleware(get_response)(request)

    assert response.status_code == 302
    get_response.assert_not_called()


def test_invalid_signature_is_refused(request_factory):
    request = _request(request_factory)
    licence = _licence()
    licence.verifier_signature.return_value = False
    request.user.etablissement = SimpleNamespace(licence=licence)
    get_response = Mock(return_value="allowed")

    with override_settings(LICENSE_ENFORCEMENT_ENABLED=True):
        with patch("licences.middleware.cache") as cache:
            cache.get.return_value = None
            with patch("licences.middleware.LicenceAuditLog.objects.create"):
                response = LicenceCheckMiddleware(get_response)(request)

    assert response.status_code == 302
    assert response.url.endswith("/licences/support/")
    get_response.assert_not_called()


def test_valid_bound_license_is_allowed(request_factory):
    request = _request(request_factory)
    request.user.etablissement = SimpleNamespace(licence=_licence())
    get_response = Mock(return_value="allowed")

    with override_settings(LICENSE_ENFORCEMENT_ENABLED=True):
        with patch("licences.middleware.cache") as cache:
            cache.get.return_value = None
            with patch("licences.middleware.LicenceAlert.objects.filter") as alerts:
                alerts.return_value.exists.return_value = True
                with patch("licences.middleware.Licence.objects.filter"):
                    response = LicenceCheckMiddleware(get_response)(request)

    assert response == "allowed"
    get_response.assert_called_once_with(request)


def test_cache_key_changes_when_signature_changes():
    first = _licence(signature_ed25519="signature-a")
    second = _licence(signature_ed25519="signature-b")

    first_key = LicenceCheckMiddleware._cache_key(first, "fingerprint")
    second_key = LicenceCheckMiddleware._cache_key(second, "fingerprint")

    assert first_key != second_key


def test_zero_signed_limit_rejects_the_first_resource():
    """Zéro signifie « aucune capacité », pas « limite désactivée »."""
    licence = Mock()
    licence.est_active.return_value = True
    licence.limites_effectives.return_value = {'max_classes': 0}
    manager = Mock()
    manager.select_for_update.return_value.select_related.return_value.get.return_value = licence

    with override_settings(LICENSE_ENFORCEMENT_ENABLED=True):
        with patch('licences.limits.Licence.objects', manager):
            with patch('licences.limits.transaction.atomic', return_value=nullcontext()):
                with patch('licences.limits._current_count', return_value=0):
                    with pytest.raises(LicenceLimitExceeded) as exc_info:
                        with reserve_limit(SimpleNamespace(), 'classes'):
                            raise AssertionError('la création ne devait pas être autorisée')

    assert exc_info.value.maximum == 0
    assert exc_info.value.current == 0
