import re

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
        assert "addEventListener('input'" in js and 'cspSyncTarget' in js and 'cspCountTarget' in js
        assert "case 'insert-variable'" in js and 'window.insertVariable' not in js


@pytest.mark.django_db
class TestPartialsSansScriptInline:
    """Même défaut que le tarif : scripts inline (sans nonce) et attributs on*= bloqués par la CSP,
    remplacés par les attributs data-csp-* traités dans csp_handlers.js."""

    @pytest.fixture
    def client_etab(self, client):
        etab = baker.make(Etablissement, code='CSP', nom='Lycée Yelen')
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False)
        client.force_login(user)
        return client

    @pytest.mark.parametrize('nom_url, attendus', [
        ('parametres:statut_create', ['id="couleur-picker"', 'data-csp-sync-target="couleur-text"',
                                      'data-csp-sync-target="couleur-picker"']),
        ('parametres:appreciation_create', ['id="appr-color"', 'data-csp-sync-target="appr-color-label"']),
        ('parametres:appreciation_primaire_create', ['id="appr-color"', 'data-csp-sync-target="appr-color-label"']),
    ])
    def test_formulaires_couleur(self, client_etab, nom_url, attendus):
        html = client_etab.get(reverse(nom_url), HTTP_HX_REQUEST='true').content.decode()

        assert '<script' not in html and 'oninput=' not in html
        for attendu in attendus:
            assert attendu in html

    def test_modele_message(self, client_etab):
        html = client_etab.get(reverse('parametres:modele_message_form', kwargs={'type_msg': 'BULLETIN'})).content.decode()

        assert '<script' not in html and 'oninput=' not in html
        assert 'data-csp-count-target="count-BULLETIN"' in html
        assert 'data-csp-action="insert-variable"' in html and 'data-insert-target="contenu-BULLETIN"' in html
        # Compteur initialisé côté serveur avec la longueur du contenu par défaut
        from parametres.models import ModeleMessage
        longueur = len(ModeleMessage.DEFAUTS['BULLETIN'])
        assert f'<span id="count-BULLETIN">{longueur}</span>' in html


@pytest.mark.django_db
class TestSimulationTarifaire:
    """Régression : la page portait un <script> inline sans nonce (bloqué par la CSP) ;
    le résultat ne s'affichait jamais. Les sélecteurs pilotent désormais HTMX directement."""

    @pytest.fixture
    def contexte(self, client):
        etab = baker.make(Etablissement, code='SIM', nom='Lycée Yelen')
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False)
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True)
        cycle = baker.make(Cycle, etablissement=etab, nom='Secondaire', code='SEC', actif=True)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6ème A', actif=True)
        statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Nouveau', actif=True)
        rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Scolarité', code='SCOL', actif=True)
        baker.make('parametres.TarifScolarite', etablissement=etab, cycle=cycle, classe=classe, statut_eleve=statut,
                   rubrique=rubrique, annee_scolaire=annee, montant=75000, actif=True)
        client.force_login(user)
        return annee, classe, statut

    def test_page_pilotee_par_htmx_sans_script_inline(self, client, contexte):
        html = client.get(reverse('parametres:tarif_simulation')).content.decode()

        # Page complète : un script/style inline (sans src=) doit porter le nonce CSP (ceux de base.html)
        inline = [b for b in re.findall(r'<(?:script|style)\b[^>]*>', html) if 'src="' not in b]
        assert inline and all('nonce="' in b for b in inline), [b for b in inline if 'nonce="' not in b]
        assert f'hx-get="{reverse("parametres:tarif_simulation_resultat")}"' in html
        assert 'hx-trigger="change"' in html and 'hx-target="#simulation-result"' in html
        assert 'hx-sync="this:replace"' in html  # la dernière sélection l'emporte
        for champ in ('name="annee"', 'name="classe"', 'name="statut"'):
            assert champ in html
        assert 'id="simulation-result"' in html

    def test_resultat(self, client, contexte):
        annee, classe, statut = contexte
        url = reverse('parametres:tarif_simulation_resultat')

        complet = client.get(url, {'annee': annee.pk, 'classe': classe.pk, 'statut': statut.pk}).content.decode()
        assert '6ème A · Nouveau' in complet and 'Scolarité' in complet and '75000' in complet

        incomplet = client.get(url, {'annee': annee.pk, 'classe': '', 'statut': statut.pk}).content.decode()
        assert 'Sélectionnez une année, une classe et un statut' in incomplet

        autre_etab = baker.make('parametres.AnneeScolaire', etablissement=baker.make(Etablissement, code='AUTRE'))
        etranger = client.get(url, {'annee': autre_etab.pk, 'classe': classe.pk, 'statut': statut.pk}).content.decode()
        assert 'introuvable' in etranger
