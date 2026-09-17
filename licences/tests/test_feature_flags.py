# licences/tests/test_feature_flags.py
# ================================================================
# Tests des Feature Flags de licence appliqués aux vues.
#
# Niveaux (rappel) :
#   STARTER      : base (inscriptions, notes, presences, finances base…)
#   STANDARD     : + cursus, examens officiels, portail parents, personnel,
#                  vacations, statistiques
#   PREMIUM      : + IA prédictive, rapports avancés
#   RESEAU       : + multi-établissements
#
# Garanties clés :
#   - Enforce OFF (défaut dev/tests) : aucun blocage, toutes les vues
#     accessibles avec ou sans licence (non-régressif).
#   - Enforce ON : la licence de l'établissement de l'utilisateur détermine
#     l'accès ; refus = redirection vers /licences/mon-abonnement/.
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
def user_licence():
    """Fabrique : user_licence('STARTER') → (user, licence)."""
    def _make(niveau):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', is_superuser=False,
                          etablissement=etab, role='DIRECTEUR')
        licence = baker.make(
            'licences.Licence',
            etablissement=etab,
            type_licence=niveau,
            statut='ACTIVE',
            date_expiration=date.today() + timedelta(days=365),
        )
        return user, licence
    return _make


@pytest.mark.django_db
class TestFeatureFlagsOff:
    """Enforce off : comportement non-régressif (rien n'est bloqué)."""

    def test_predictions_accessibles_sans_licence(self, client, user_licence):
        user, _ = user_licence('STARTER')
        client.force_login(user)
        response = client.get(reverse('pedagogie:prediction_index'))
        assert response.status_code == 200

    def test_predictions_accessibles_sans_aucune_licence(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', is_superuser=False,
                          etablissement=etab, role='DIRECTEUR')
        client.force_login(user)
        response = client.get(reverse('pedagogie:prediction_index'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestFeatureFlagsOn:
    """Enforce on : le niveau de licence détermine l'accès."""

    def test_premium_bloque_ia(self, client, user_licence, enforcement_on):
        """STARTER (ni PREMIUM ni RESEAU) : IA prédictive refusée."""
        user, _ = user_licence('STARTER')
        client.force_login(user)
        response = client.get(reverse('pedagogie:prediction_index'))
        assert response.status_code == 302
        assert response.url == '/licences/mon-abonnement/'

    def test_premium_acced_ia(self, client, user_licence, enforcement_on):
        user, _ = user_licence('PREMIUM')
        client.force_login(user)
        response = client.get(reverse('pedagogie:prediction_index'))
        assert response.status_code == 200

    def test_standard_acced_examens(self, client, user_licence, enforcement_on):
        """STANDARD+ : examens officiels accessibles."""
        user, _ = user_licence('STANDARD')
        client.force_login(user)
        response = client.get(reverse('examens:session_list'))
        assert response.status_code == 200

    def test_starter_bloque_examens(self, client, user_licence, enforcement_on):
        user, _ = user_licence('STARTER')
        client.force_login(user)
        response = client.get(reverse('examens:session_list'))
        assert response.status_code == 302
        assert response.url == '/licences/mon-abonnement/'

    def test_starter_bloque_personnel(self, client, user_licence, enforcement_on):
        user, _ = user_licence('STARTER')
        client.force_login(user)
        response = client.get(reverse('personnel:personnel_list'))
        assert response.status_code == 302

    def test_premium_bloque_multi_etablissements(self, client, user_licence,
                                                 enforcement_on):
        """Même PREMIUM : le multi-établissements reste RESEAU uniquement."""
        user, _ = user_licence('PREMIUM')
        client.force_login(user)
        response = client.get(reverse('etablissements:reseau_dashboard'))
        # Le flag licence bloque AVANT le contrôle de rôle : redirection
        # licence (et non le message « réservé au Directeur Réseau »).
        assert response.status_code == 302
        assert response.url == '/licences/mon-abonnement/'

    def test_reseau_acced_multi_etablissements(self, client, user_licence,
                                               enforcement_on):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', is_superuser=False,
                          etablissement=etab, role='DIRECTEUR_RESEAU')
        licence = baker.make(
            'licences.Licence',
            etablissement=etab,
            type_licence='RESEAU',
            statut='ACTIVE',
            date_expiration=date(2030, 1, 1),
        )
        client.force_login(user)
        response = client.get(reverse('etablissements:reseau_dashboard'))
        assert response.status_code == 200

    def test_licence_expiree_bloque_features(self, client, enforcement_on):
        """Licence PREMIUM expirée : les features premium deviennent
        inaccessibles (licence inactive)."""
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', is_superuser=False,
                          etablissement=etab, role='DIRECTEUR')
        baker.make(
            'licences.Licence',
            etablissement=etab,
            type_licence='PREMIUM',
            statut='ACTIVE',
            date_expiration=date.today() - timedelta(days=1),
        )
        client.force_login(user)
        # Le middleware licence redirige d'abord vers renouveler
        response = client.get(reverse('pedagogie:prediction_index'))
        assert response.status_code == 302
        assert 'renouveler' in response.url
