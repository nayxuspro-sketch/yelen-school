# licences/tests/test_hardening.py
# ================================================================
# Tests de durcissement (anti-fraude) — P0-5 / P0-6.
#
# Garanties :
#   - Plus de bypass superuser : le superuser est soumis au contrôle
#     de licence (licence expirée/absente = bloqué comme les autres).
#   - /admin/ n'est plus exempté du contrôle.
#   - /licences/ reste exempté (onboarding : création/activation/
#     renouvellement possibles même sans licence valide).
#   - /licences/outils/ (outil de développement exposant l'algorithme
#     de signature local) est désactivé (404) en mode production.
from datetime import date, timedelta

import pytest
from django.urls import reverse
from model_bakery import baker


LICENCE_MIDDLEWARES = [
    'licences.middleware.LicenceCheckMiddleware',
    'licences.middleware.LicenceLimitsMiddleware',
    'licences.middleware.LicenceContextMiddleware',
]


@pytest.fixture
def enforcement_on(settings):
    settings.LICENSE_ENFORCEMENT = True
    middleware = list(settings.MIDDLEWARE)
    for mw in LICENCE_MIDDLEWARES:
        if mw not in middleware:
            middleware.append(mw)
    settings.MIDDLEWARE = middleware


@pytest.fixture
def superuser_etab():
    etab = baker.make('etablissements.Etablissement')
    user = baker.make('accounts.User', is_superuser=True,
                      is_staff=True, etablissement=etab)
    return user


@pytest.fixture
def licence_expiree_etab():
    etab = baker.make('etablissements.Etablissement')
    user = baker.make('accounts.User', is_superuser=True,
                      is_staff=True, etablissement=etab)
    baker.make(
        'licences.Licence',
        etablissement=etab,
        type_licence='STANDARD',
        statut='ACTIVE',
        date_expiration=date.today() - timedelta(days=2),
    )
    return user


@pytest.fixture
def licence_valide_etab():
    etab = baker.make('etablissements.Etablissement')
    user = baker.make('accounts.User', is_superuser=True,
                      is_staff=True, etablissement=etab)
    baker.make(
        'licences.Licence',
        etablissement=etab,
        type_licence='PREMIUM',
        statut='ACTIVE',
        date_expiration=date.today() + timedelta(days=200),
    )
    return user


@pytest.mark.django_db
class TestSuperuserSoumisAuControle:
    """P0-5 : le superuser n'a plus de passe-droit."""

    def test_superuser_licence_valide_acces(self, client, licence_valide_etab,
                                            enforcement_on):
        client.force_login(licence_valide_etab)
        response = client.get(reverse('core:home'))
        assert response.status_code == 200

    def test_superuser_licence_expiree_bloquee(self, client, licence_expiree_etab,
                                               enforcement_on):
        """Avant : le superuser contournait tout. Maintenant : bloqué."""
        client.force_login(licence_expiree_etab)
        response = client.get(reverse('core:home'))
        assert response.status_code == 302
        assert response.url == reverse('licences:renouveler')

    def test_superuser_sans_licence_bloquee(self, client, superuser_etab,
                                            enforcement_on):
        client.force_login(superuser_etab)
        response = client.get(reverse('core:home'))
        assert response.status_code == 302
        assert response.url == reverse('licences:activer')

    def test_superuser_admin_non_exempte(self, client, licence_expiree_etab,
                                         enforcement_on):
        """/admin/ n'est plus exempté : licence expirée → redirection."""
        client.force_login(licence_expiree_etab)
        response = client.get('/admin/')
        assert response.status_code == 302
        assert 'licences' in response.url

    def test_superuser_admin_acces_avec_licence(self, client, licence_valide_etab,
                                                enforcement_on):
        client.force_login(licence_valide_etab)
        response = client.get('/admin/')
        # L'admin est atteint (page admin Django, 200 ou login déjà OK)
        assert response.status_code in (200, 302)
        if response.status_code == 302:
            # Une éventuelle redirection doit viser l'admin (session),
            # pas les licences
            assert 'licences' not in response.url


@pytest.mark.django_db
class TestOnboardingLicences:
    """Le module /licences/ reste accessible pour le déblocage."""

    @pytest.mark.parametrize('nom', ['activer', 'renouveler', 'statut', 'gestion'])
    def test_pages_licences_accessibles_licence_expiree(self, client,
                                                        licence_expiree_etab,
                                                        enforcement_on, nom):
        client.force_login(licence_expiree_etab)
        response = client.get(reverse(f'licences:{nom}'))
        assert response.status_code == 200, nom

    def test_creation_licence_possible_sans_licence(self, client, superuser_etab,
                                                    enforcement_on):
        """Onboarding : un superuser sans licence peut en créer une
        (POST sur licences:licence_create)."""
        client.force_login(superuser_etab)
        etab2 = baker.make('etablissements.Etablissement')
        response = client.post(
            reverse('licences:licence_create'),
            {
                'etablissement': str(etab2.id),
                'type_licence': 'STARTER',
                'date_expiration': (date.today() + timedelta(days=365)).isoformat(),
                'notes_interne': '',
            },
            follow=False,
        )
        assert response.status_code == 302
        from licences.models import Licence
        assert Licence.objects.filter(etablissement=etab2).exists()


@pytest.mark.django_db
class TestOutilsLicence:
    """L'outil offline de signature est un outil de développement."""

    def test_outils_desactive_en_production(self, client, licence_valide_etab,
                                            enforcement_on):
        client.force_login(licence_valide_etab)
        response = client.get(reverse('licences:outils'))
        assert response.status_code == 404

    def test_outils_disponible_en_developpement(self, client, licence_valide_etab):
        """Enforce off (développement) : l'outil reste utilisable."""
        client.force_login(licence_valide_etab)
        response = client.get(reverse('licences:outils'))
        assert response.status_code == 200

    def test_outils_interdit_anonyme(self, client):
        response = client.get(reverse('licences:outils'))
        assert response.status_code == 302  # @login_required
