"""Le bloc utilisateur du menu latéral mène à « Mon profil » (changement de mot de passe)."""
import pytest
from django.urls import reverse
from model_bakery import baker

from etablissements.models import Etablissement


@pytest.mark.django_db
@pytest.mark.parametrize('role', ['ENSEIGNANT', 'PARENT'])
def test_menu_mene_au_profil(client, role):
    client.force_login(baker.make('accounts.User', etablissement=baker.make(Etablissement), role=role,
                                  must_change_password=False))
    html = client.get(reverse('accounts:profile')).content.decode()
    assert 'href="%s" class="sb-user-modern"' % reverse('accounts:profile') in html
    assert 'Changer le mot de passe' in html
