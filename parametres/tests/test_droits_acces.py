"""Droits d'accès aux modules par rôle : valeurs par défaut, application, administration."""
import pytest
from django.urls import reverse
from model_bakery import baker

from etablissements.models import Etablissement
from parametres import droits


@pytest.fixture(autouse=True)
def cache_vide():
    droits.invalider_cache()
    yield
    droits.invalider_cache()


@pytest.fixture
def etab():
    return baker.make(Etablissement)


def _client_role(client, etab, role):
    client.force_login(baker.make('accounts.User', etablissement=etab, role=role, must_change_password=False))
    return client


@pytest.mark.django_db
class TestValeursParDefaut:
    def test_comportement_historique(self):
        matrice = droits.matrice_effective()

        assert 'inscriptions' in matrice['ENSEIGNANT'] and 'viescolaire' in matrice['AVS']
        assert 'finances' not in matrice['ENSEIGNANT'] and 'finances' not in matrice['AVS']
        assert 'finances' in matrice['SECRETAIRE'] and 'finances' in matrice['COMPTABLE']
        assert 'parametres' in matrice['DIRECTEUR'] and 'parametres' not in matrice['SECRETAIRE']

    def test_super_admin_tout(self):
        assert droits.modules_autorises(baker.prepare('accounts.User', role='SUPER_ADMIN')) == droits.CODES_MODULES


@pytest.mark.django_db
class TestApplicationDesDroits:
    def test_module_refuse_redirige_avec_message(self, client, etab):
        _client_role(client, etab, 'ENSEIGNANT')

        reponse = client.get(reverse('finances:paiement_list'))

        assert reponse.status_code == 302 and reponse.url == '/'
        suite = client.get('/')
        assert 'Accès au module « Finances » non autorisé' in suite.content.decode()

    def test_module_refuse_en_htmx(self, client, etab):
        _client_role(client, etab, 'ENSEIGNANT')
        assert client.get(reverse('finances:paiement_list'), HTTP_HX_REQUEST='true').status_code == 403

    def test_module_autorise(self, client, etab):
        _client_role(client, etab, 'ENSEIGNANT')
        assert client.get(reverse('inscriptions:eleve_list')).status_code == 200

    def test_menu_suit_les_droits(self, client, etab):
        _client_role(client, etab, 'ENSEIGNANT')

        html = client.get('/').content.decode()

        assert 'id="inscriptions-toggle"' in html
        assert 'id="finances-toggle"' not in html and 'id="params-toggle"' not in html
        assert 'droits-acces' not in html


@pytest.mark.django_db
class TestAdministrationParLeSuperAdmin:
    def test_reservee_au_super_admin(self, client, etab):
        _client_role(client, etab, 'DIRECTEUR')
        assert client.get(reverse('parametres:droits_acces')).status_code == 403

    def test_matrice_affichee(self, client, etab):
        _client_role(client, etab, 'SUPER_ADMIN')

        html = client.get(reverse('parametres:droits_acces')).content.decode()

        assert 'name="droit" value="SECRETAIRE:finances"' in html
        assert html.count('type="checkbox"') == len(droits.ROLES_CONFIGURABLES) * len(droits.MODULES)
        assert 'id="matrice-droits"' in html and 'data-url="/parametres/droits-acces/"' in html

    def test_enregistrement_applique_immediatement(self, client, etab):
        from parametres.models import DroitAcces
        _client_role(client, etab, 'SUPER_ADMIN')
        coches = [f'{role}:{module.code}' for role in droits.ROLES_CONFIGURABLES for module in droits.MODULES]
        coches.remove('ENSEIGNANT:inscriptions')      # retrait d'un accès ouvert par défaut

        reponse = client.post(reverse('parametres:droits_acces'), {'droit': coches})

        assert reponse.status_code == 302
        assert DroitAcces.objects.count() == len(droits.ROLES_CONFIGURABLES) * len(droits.MODULES)
        enseignant = _client_role(client.__class__(), etab, 'ENSEIGNANT')
        assert enseignant.get(reverse('finances:paiement_list')).status_code == 200   # accès ajouté
        assert enseignant.get(reverse('inscriptions:eleve_list')).status_code == 302  # accès retiré
        html = enseignant.get('/').content.decode()
        assert 'id="finances-toggle"' in html and 'id="inscriptions-toggle"' not in html
