"""Volet « Système » du menu latéral (Mon abonnement, Licences) : Super Admin uniquement.

Super Admin = rôle SUPER_ADMIN ou superuser Django (``User.est_super_admin``).
"""
import pytest
from django.urls import reverse
from model_bakery import baker

from etablissements.models import Etablissement

MENU_ABONNEMENT = 'data-url="/licences/mon-abonnement/"'
MENU_LICENCES = 'data-url="/licences/"'


@pytest.fixture
def etab():
    return baker.make(Etablissement)


def _connecter(client, etab, **attrs):
    user = baker.make('accounts.User', etablissement=etab, must_change_password=False, **attrs)
    client.force_login(user)
    return user


@pytest.mark.django_db
class TestVoletSysteme:
    def test_est_super_admin(self, etab):
        assert baker.make('accounts.User', etablissement=etab, role='SUPER_ADMIN').est_super_admin
        assert baker.make('accounts.User', etablissement=etab, is_superuser=True).est_super_admin
        assert not baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', is_staff=True).est_super_admin

    def test_role_super_admin_sans_drapeau_voit_tout_le_volet(self, client, etab):
        _connecter(client, etab, role='SUPER_ADMIN')
        html = client.get(reverse('licences:statut')).content.decode()
        assert MENU_ABONNEMENT in html and MENU_LICENCES in html
        assert client.get(reverse('licences:gestion')).status_code == 200

    def test_superuser_django_voit_tout_le_volet(self, client, etab):
        _connecter(client, etab, is_superuser=True)
        html = client.get(reverse('licences:statut')).content.decode()
        assert MENU_ABONNEMENT in html and MENU_LICENCES in html
        assert client.get(reverse('licences:gestion')).status_code == 200

    @pytest.mark.parametrize('role', ['DIRECTEUR', 'SECRETAIRE', 'ENSEIGNANT'])
    def test_autres_roles_ni_menu_ni_acces(self, client, etab, role):
        _connecter(client, etab, role=role)
        html = client.get('/').content.decode()
        assert MENU_ABONNEMENT not in html and MENU_LICENCES not in html
        for nom in ('statut', 'gestion'):
            reponse = client.get(reverse(f'licences:{nom}'))
            assert reponse.status_code == 302 and reponse.url.startswith('/?next='), nom
