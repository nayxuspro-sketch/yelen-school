"""Configuration pytest globale — désactive l'audit log et le redirect HTTPS pendant les tests."""
import pytest


@pytest.fixture(autouse=True)
def disable_ssl_redirect(settings):
    """Empêche Django de rediriger HTTP → HTTPS pendant les tests."""
    settings.SECURE_SSL_REDIRECT = False
    settings.SECURE_HSTS_SECONDS = 0


@pytest.fixture(autouse=True)
def disable_audit_for_tests():
    """Désactive le signal d'audit pendant tous les tests."""
    from core.signals import disable_audit
    disable_audit()
    yield
    from core.signals import enable_audit
    enable_audit()


@pytest.fixture(autouse=True)
def cache_des_droits_isole():
    """La matrice des droits est mise en cache sous une clé unique : avec un cache qui survit à la transaction du
    test (Redis en mode serveur), un refus posé par un test contaminerait les suivants. Le cache en base, lui, est
    annulé avec la transaction et n'est pas touché (les tests sans base ne doivent pas l'ouvrir)."""
    yield
    from django.conf import settings as reglages
    if 'DatabaseCache' not in reglages.CACHES['default']['BACKEND']:
        from parametres import droits
        droits.invalider_cache()


@pytest.fixture(autouse=True)
def two_factor_non_obligatoire(settings):
    """Les tests existants connectent des Super Admin/Directeurs sans TOTP ; les tests dédiés réactivent l'obligation."""
    settings.TWO_FACTOR_REQUIRED = False
