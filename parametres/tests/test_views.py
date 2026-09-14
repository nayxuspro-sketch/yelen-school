import pytest
from django.urls import reverse
from model_bakery import baker

from etablissements.models import Etablissement
from parametres.models import Cycle, DeclencheurSMS

@pytest.mark.django_db
class TestParametresViews:
    @pytest.fixture
    def logged_in_client(self, client):
        user = baker.make('accounts.User', is_superuser=True)
        client.force_login(user)
        return client

    def test_signataires_list_view(self, logged_in_client):
        url = reverse('parametres:signataires_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'cycles' in response.context

    def test_cycle_list_htmx_response_refreshes_tree(self, client):
        etablissement = baker.make(
            Etablissement,
            code='TEST-CYCLES',
            nom='Établissement de test',
            ville='Ouagadougou',
        )
        user = baker.make(
            'accounts.User',
            username='cycle-test',
            email='cycle-test@example.test',
            etablissement=etablissement,
        )
        cycle = baker.make(
            Cycle,
            etablissement=etablissement,
            nom='Primaire',
            code='PRIM',
        )
        client.force_login(user)

        response = client.get(
            reverse('parametres:cycle_list'),
            HTTP_HX_REQUEST='true',
        )

        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="cycle-list-container"' in content
        assert cycle.nom in content

    def test_sms_auto_config_creates_one_trigger_per_type(self, client):
        etablissement = baker.make(
            Etablissement,
            code='TEST-SMS',
            nom='Établissement SMS',
            ville='Ouagadougou',
        )
        user = baker.make(
            'accounts.User',
            username='sms-config-test',
            email='sms-config-test@example.test',
            role='DIRECTEUR',
            etablissement=etablissement,
        )
        client.force_login(user)

        response = client.get(reverse('parametres:sms_auto_config'))

        assert response.status_code == 200
        assert DeclencheurSMS.objects.filter(etablissement=etablissement).count() == 3

    def test_sms_auto_toggle_is_scoped_to_establishment(self, client):
        etablissement = baker.make(
            Etablissement,
            code='TEST-SMS-TOGGLE',
            nom='Établissement SMS Toggle',
            ville='Ouagadougou',
        )
        user = baker.make(
            'accounts.User',
            username='sms-toggle-test',
            email='sms-toggle-test@example.test',
            role='DIRECTEUR',
            etablissement=etablissement,
        )
        trigger = baker.make(
            DeclencheurSMS,
            etablissement=etablissement,
            type_declencheur='ABSENCE_J1',
            actif=False,
        )
        client.force_login(user)

        response = client.post(
            reverse('parametres:sms_auto_toggle', kwargs={'pk': trigger.pk})
        )

        assert response.status_code == 200
        trigger.refresh_from_db()
        assert trigger.actif is True
