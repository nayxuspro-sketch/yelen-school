"""Tests ciblés des contrôles d'authentification sans base PostgreSQL."""

from types import SimpleNamespace

from django.core.cache.backends.locmem import LocMemCache
from django.test import RequestFactory, override_settings

from accounts.security import LoginRateLimiter
from yelen_school.two_factor_middleware import REQUIRED_2FA_ROLES, TwoFactorRequiredMiddleware


def _request(path='/', *, role='COMPTABLE', totp_enabled=False):
    request = RequestFactory().get(path)
    request.user = SimpleNamespace(
        is_authenticated=True,
        role=role,
        totp_enabled=totp_enabled,
    )
    request.session = {}
    request.META['REMOTE_ADDR'] = '192.0.2.10'
    return request


def test_privileged_roles_are_required_to_use_2fa():
    assert 'COMPTABLE' in REQUIRED_2FA_ROLES
    assert 'DIRECTEUR' in REQUIRED_2FA_ROLES
    assert 'SUPER_ADMIN' in REQUIRED_2FA_ROLES


def test_unenrolled_privileged_user_is_redirected_to_setup():
    request = _request('/finances/paiements/')
    response = TwoFactorRequiredMiddleware(lambda request: 'allowed')(request)

    assert response.status_code == 302
    assert response.url.endswith('/accounts/profile/2fa/activer/')


def test_enrolled_privileged_user_is_allowed():
    request = _request('/finances/paiements/', totp_enabled=True)
    assert TwoFactorRequiredMiddleware(lambda request: 'allowed')(request) == 'allowed'


def test_login_rate_limiter_binds_ip_and_account_without_plaintext_keys():
    limiter_cache = LocMemCache('test-login-rate-limit', {})
    request = _request('/accounts/login/', role='ENSEIGNANT')

    with override_settings():
        from unittest.mock import patch
        with patch('accounts.security.cache', limiter_cache):
            for _ in range(LoginRateLimiter.MAX_ATTEMPTS):
                LoginRateLimiter.register_failure(request, 'User@Example.com')
            assert LoginRateLimiter.is_blocked(request, 'user@example.com')
            assert all('user@example.com' not in key for key in limiter_cache._cache)
            LoginRateLimiter.clear_account(request, 'user@example.com')
            # Le compteur IP reste une défense active.
            assert LoginRateLimiter.is_blocked(request, 'another@example.com')
