"""Configuration pytest globale — désactive l'audit log et le redirect HTTPS pendant les tests."""
import pytest


@pytest.fixture(autouse=True)
def disable_ssl_redirect(settings):
    """Empêche Django de rediriger HTTP → HTTPS pendant les tests."""
    settings.SECURE_SSL_REDIRECT = False
    settings.SECURE_HSTS_SECONDS = 0


@pytest.fixture(autouse=True)
def disable_license_enforcement_for_tests(settings):
    """Les tests fonctionnels historiques n'ont pas de licence émise."""
    settings.LICENSE_ENFORCEMENT_ENABLED = False


@pytest.fixture(autouse=True)
def disable_audit_for_tests():
    """Désactive le signal d'audit pendant tous les tests."""
    from core.signals import disable_audit
    disable_audit()
    yield
    from core.signals import enable_audit
    enable_audit()
