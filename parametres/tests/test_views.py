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


@pytest.mark.django_db
class TestTarifFormMontantAutomatique:
    """Régression : le montant de la rubrique ne se recopiait plus dans « Montant (FCFA) »
    (script inline du partial bloqué par la CSP → mécanisme data-csp-fill-target)."""

    def test_partial_sans_script_inline_et_attributs_de_recopie(self, client):
        etab = baker.make(Etablissement, code='TARIF', nom='Lycée Yelen')
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False)
        rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Scolarité',
                              code='SCOL', montant=25000, actif=True)
        client.force_login(user)

        response = client.get(reverse('parametres:tarif_create'), HTTP_HX_REQUEST='true')

        html = response.content.decode()
        assert response.status_code == 200
        assert '<script' not in html, "script inline interdit par la CSP (script-src nonce)"
        assert 'id="id_rubrique_tarif"' in html and 'data-csp-fill-target="id_montant_tarif"' in html
        assert f'<option value="{rubrique.pk}"' in html and 'data-fill="25000' in html
        assert 'id="id_montant_tarif"' in html

    def test_gestionnaire_present_dans_csp_handlers(self):
        from pathlib import Path
        js = Path('static/js/csp_handlers.js').read_text(encoding='utf-8')
        assert "addEventListener('change'" in js and 'cspFillTarget' in js and 'dataset.fill' in js
