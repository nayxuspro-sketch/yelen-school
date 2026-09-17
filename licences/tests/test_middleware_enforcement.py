# licences/tests/test_middleware_enforcement.py
# ================================================================
# Tests du contrôle des licences (anti-fraude) — middlewares.
#
# Le flag LICENSE_ENFORCEMENT est un paramètre de settings évalué à
# l'import. Pour tester le mode forcé, le fixture ci-dessous reproduit
# exactement ce que fait yelen_school/settings.py quand
# LICENSE_ENFORCEMENT=true : il ajoute les 3 middlewares à MIDDLEWARE.
#
# Garanties vérifiées :
#   - Par défaut (LICENSE_ENFORCEMENT non actif), AUCUN middleware
#     licence n'est chargé → comportement identique à l'existant.
#   - En mode forcé : licence expirée/révooquée/absente = accès bloqué.
import datetime

import pytest
from django.urls import reverse
from model_bakery import baker

LICENCE_MIDDLEWARES = [
    'licences.middleware.LicenceCheckMiddleware',
    'licences.middleware.LicenceLimitsMiddleware',
    'licences.middleware.LicenceContextMiddleware',
]


@pytest.fixture
def licence_enforcement(settings):
    """Simule LICENSE_ENFORCEMENT=true comme le ferait settings.py."""
    settings.LICENSE_ENFORCEMENT = True
    middleware = list(settings.MIDDLEWARE)
    for mw in LICENCE_MIDDLEWARES:
        if mw not in middleware:
            middleware.append(mw)
    settings.MIDDLEWARE = middleware


@pytest.fixture
def etab_user():
    """Utilisateur non superuser rattaché à un établissement."""
    etab = baker.make('etablissements.Etablissement')
    user = baker.make('accounts.User', is_superuser=False, etablissement=etab)
    return user


@pytest.fixture
def licence_active(etab_user):
    return baker.make(
        'licences.Licence',
        etablissement=etab_user.etablissement,
        type_licence='STARTER',
        statut='ACTIVE',
        date_activation=datetime.datetime.now(datetime.timezone.utc),
        date_expiration=datetime.date.today() + datetime.timedelta(days=30),
    )


@pytest.fixture
def licence_expiree(etab_user):
    return baker.make(
        'licences.Licence',
        etablissement=etab_user.etablissement,
        type_licence='STARTER',
        statut='ACTIVE',
        date_activation=datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=360),
        date_expiration=datetime.date.today() - datetime.timedelta(days=5),
    )


@pytest.fixture
def licence_revoquee(etab_user):
    return baker.make(
        'licences.Licence',
        etablissement=etab_user.etablissement,
        type_licence='STARTER',
        statut='REVOQUEE',
        date_activation=datetime.datetime.now(datetime.timezone.utc),
        date_expiration=datetime.date.today() + datetime.timedelta(days=30),
    )


@pytest.mark.django_db
class TestGateMiddleware:
    """Le flag global pilote la présence des middlewares."""

    def test_middleware_absents_par_defaut(self, settings):
        # Le settings de test est importé sans LICENSE_ENFORCEMENT=true,
        # donc les middlewares licences ne doivent pas être présents.
        assert not any(m in settings.MIDDLEWARE for m in LICENCE_MIDDLEWARES)

    def test_flag_non_defini_par_defaut(self, settings):
        assert settings.LICENSE_ENFORCEMENT is False


@pytest.mark.django_db
class TestEnforcementOff:
    """Mode développement/démo : aucun blocage (non-régressive)."""

    def test_licence_expiree_acces_libre(self, client, etab_user, licence_expiree):
        client.force_login(etab_user)
        response = client.get(reverse('core:home'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestEnforcementOn:
    """Mode production : les middlewares contrôlent chaque requête."""

    def test_licence_active_acces_libre(self, client, etab_user, licence_active,
                                        licence_enforcement):
        client.force_login(etab_user)
        response = client.get(reverse('core:home'))
        assert response.status_code == 200

    def test_licence_expiree_bloquee(self, client, etab_user, licence_expiree,
                                     licence_enforcement):
        client.force_login(etab_user)
        response = client.get(reverse('core:home'))
        assert response.status_code == 302
        assert response.url == reverse('licences:renouveler')
        # Le statut a été synchronisé en base
        licence_expiree.refresh_from_db()
        assert licence_expiree.statut == 'EXPIREE'

    def test_licence_revoquee_bloquee(self, client, etab_user, licence_revoquee,
                                      licence_enforcement):
        client.force_login(etab_user)
        response = client.get(reverse('core:home'))
        assert response.status_code == 302
        assert response.url == reverse('licences:support')

    def test_sans_licence_bloquee(self, client, etab_user, licence_enforcement):
        client.force_login(etab_user)
        response = client.get(reverse('core:home'))
        assert response.status_code == 302
        assert response.url == reverse('licences:activer')

    def test_anonyme_non_affecte(self, client, licence_enforcement):
        """L'anonyme n'est pas traité par le middleware (redirection login)."""
        response = client.get(reverse('core:home'))
        assert response.status_code == 302
        assert 'licences' not in response.url

    def test_pages_licences_exemptees(self, client, etab_user, licence_expiree,
                                      licence_enforcement):
        """Les pages de résolution (activation/renouvellement) restent
        accessibles même avec une licence expirée."""
        client.force_login(etab_user)
        for name in ('activer', 'renouveler'):
            response = client.get(reverse(f'licences:{name}'))
            assert response.status_code == 200, name
