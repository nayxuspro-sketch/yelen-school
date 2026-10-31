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
def quota_api_isole():
    """Le quota des connexions à l'API (5 par minute, scope « login ») est tenu par le cache : sous Redis, il
    survit d'un test à l'autre et un test d'authentification réussie finit en 429. Vidé avant chaque test quand
    le cache n'est pas transactionnel (en base, il est annulé avec la transaction du test)."""
    from django.conf import settings as reglages
    if 'DatabaseCache' in reglages.CACHES['default']['BACKEND']:
        yield
        return
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def veille_exploitation_inactive(monkeypatch):
    """La veille d'exploitation (core.veille) part de la première requête du jour dans un fil d'arrière-plan :
    neutralisée pour les tests, qui l'appellent explicitement."""
    from datetime import date
    from core import veille
    monkeypatch.setattr(veille, '_verifie_le', date.today())


@pytest.fixture(autouse=True)
def two_factor_non_obligatoire(settings):
    """Les tests existants connectent des Super Admin/Directeurs sans TOTP ; les tests dédiés réactivent l'obligation."""
    settings.TWO_FACTOR_REQUIRED = False
