import re
from decimal import Decimal

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
        assert 'cspSubmitOnChange' in js and 'requestSubmit' in js  # onchange="this.form.submit()" sans attribut inline


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


@pytest.mark.django_db
class TestSignataireConfig:
    """Page /parametres/signataires/configurer/ : style, script et onchange inline étaient bloqués par la CSP
    (page non mise en forme, onglets et sélecteur d'année inopérants)."""

    @pytest.fixture
    def contexte(self, client):
        from datetime import date
        from parametres.models import TitreFonction, TitreHonorifiquePersonnel, TypeDocument
        etab = baker.make('etablissements.Etablissement', code='SIG', nom='Ets Signataires')
        user = baker.make('accounts.User', is_superuser=True, etablissement=etab, must_change_password=False)
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027',
                           date_debut=date(2026, 9, 1), date_fin=date(2027, 7, 31), est_courante=True)
        primaire = baker.make('parametres.Cycle', etablissement=etab, code='PRI', nom='Primaire', ordre=1, actif=True)
        secondaire = baker.make('parametres.Cycle', etablissement=etab, code='SEC', nom='Secondaire', ordre=2, actif=True)
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Ouedraogo', prenom='Jean',
                            is_active=True, matricule='')
        TitreFonction.objects.get_or_create(nom='Le Directeur', defaults={'actif': True})
        TitreHonorifiquePersonnel.objects.get_or_create(nom='Monsieur', defaults={'actif': True})
        assert TypeDocument.objects.filter(categorie='SCOLARITE', actif=True).exists()  # migration 0002
        client.force_login(user)
        return annee, primaire, secondaire, membre

    def test_page_sans_style_script_ni_gestionnaire_inline(self, client, contexte):
        annee, primaire, secondaire, membre = contexte
        html = client.get(reverse('parametres:signataire_config')).content.decode()

        # Style et script de la page portent le nonce CSP ; plus aucun attribut on*= inline
        inline = [b for b in re.findall(r'<(?:script|style)\b[^>]*>', html) if 'src="' not in b]
        assert inline and all('nonce="' in b for b in inline), [b for b in inline if 'nonce="' not in b]
        assert 'onchange=' not in html and 'onclick=' not in html
        assert 'name="annee" class="input select" data-csp-submit-on-change' in html
        # Disposition des champs : grille déterministe, libellés standard, bouton dans la même rangée
        assert html.count('class="sc-form-row"') == html.count('class="sc-card"') > 0
        assert '<label class="input-label" for="sig-' in html and 'class="btn-primary sc-btn"' in html
        assert 'style="' not in html.split('<h1 class="page-title">')[1].split('<style nonce=')[0]
        # Sans paramètre ?cycle= : premier onglet (Primaire) actif, un seul panneau visible
        assert f'class="sc-tab sc-tab--active"\n          data-tab="cycle-{primaire.id}"' in html
        assert f'class="sc-tab "\n          data-tab="cycle-{secondaire.id}"' in html
        assert html.count('class="sc-panel sc-panel--active"') == 1

    def test_enregistrement_rouvre_l_onglet_du_cycle(self, client, contexte):
        from parametres.models import SignataireDocument, TypeDocument
        annee, primaire, secondaire, membre = contexte
        url = reverse('parametres:signataire_config')
        reponse = client.post(url, {
            'annee_id': str(annee.id), 'cycle_id': str(secondaire.id), 'categorie': 'SCOLARITE',
            'membre_personnel': str(membre.id), 'fonction': 'Le Directeur', 'titre_honorifique': 'Monsieur',
        })
        assert reponse.status_code == 302
        assert reponse['Location'] == f'{url}?annee={annee.id}&cycle={secondaire.id}'

        nb_types = TypeDocument.objects.filter(categorie='SCOLARITE', actif=True, cycle__isnull=True).count()
        sigs = SignataireDocument.objects.filter(cycle=secondaire, annee_scolaire=annee, actif=True)
        assert sigs.count() == nb_types and all(s.membre_personnel_id == membre.id for s in sigs)

        html = client.get(reponse['Location']).content.decode()
        assert 'Signataire enregistré pour Secondaire · Scolarité.' in html
        assert f'class="sc-tab sc-tab--active"\n          data-tab="cycle-{secondaire.id}"' in html
        assert f'class="sc-tab "\n          data-tab="cycle-{primaire.id}"' in html
        assert f'class="sc-panel sc-panel--active" id="cycle-{secondaire.id}"' in html
        # Le formulaire de la catégorie est pré-rempli avec le signataire enregistré
        assert f'<option value="{membre.id}"\n              selected>' in html


@pytest.mark.django_db
class TestFormulairesDecimauxNonLocalises:
    """Un champ <input type="number"> rejette la virgule : un décimal rendu localisé (« 7,50 »)
    laisse le champ vide à l'ouverture de la fenêtre d'édition et interdit l'enregistrement
    (champ required) ou perd la valeur. Les valeurs doivent être rendues avec le point."""

    @pytest.fixture
    def contexte(self, client):
        etab = baker.make(Etablissement, code='DEC', nom='Lycée Décimaux')
        user = baker.make('accounts.User', etablissement=etab, is_superuser=True, must_change_password=False)
        client.force_login(user)
        return {'client': client, 'etab': etab}

    def _cas(self, etab):
        from parametres.models import AppreciationMoyennePrimaire, AppreciationMoyenneSecondaire, RubriquePaiement
        from pedagogie.models import TypeEvaluation
        return [
            ('parametres:appreciation_primaire_edit',
             baker.make(AppreciationMoyennePrimaire, etablissement=etab, libelle='Bien', moy_min=Decimal('7.50'),
                        moy_max=Decimal('8.50'), couleur='#00A86B', ordre=2),
             {'moy_min': '7.50', 'moy_max': '8.50'},
             {'libelle': 'Bien', 'couleur': '#00A86B', 'ordre': '2', 'actif': 'on'}),
            ('parametres:appreciation_edit',
             baker.make(AppreciationMoyenneSecondaire, etablissement=etab, libelle='Assez bien', moy_min=Decimal('12.50'),
                        moy_max=Decimal('14.00'), couleur='#00A86B', ordre=3),
             {'moy_min': '12.50', 'moy_max': '14'},
             {'libelle': 'Assez bien', 'couleur': '#00A86B', 'ordre': '3', 'actif': 'on'}),
            ('parametres:rubrique_edit',
             baker.make(RubriquePaiement, etablissement=etab, nom='Cantine', code='CANT', montant=Decimal('52500.00'),
                        ordre=4, obligatoire=False, actif=True),
             {'montant': '52500'},
             {'nom': 'Cantine', 'code': 'CANT', 'description': '', 'ordre': '4', 'actif': 'on'}),
            ('parametres:type_evaluation_edit',
             baker.make(TypeEvaluation, code='DEC-DV', nom='Devoir', coefficient=Decimal('1.50'),
                        ponderation=Decimal('2.25'), nb_meilleures_notes=0, ordre=1),
             {'coefficient': '1.50', 'ponderation': '2.25'},
             {'code': 'DEC-DV', 'nom': 'Devoir', 'description': '', 'nb_meilleures_notes': '0', 'ordre': '1', 'est_visible': 'on'}),
        ]

    def test_valeurs_decimales_rendues_avec_le_point(self, contexte):
        for nom_url, obj, attendus, _ in self._cas(contexte['etab']):
            html = contexte['client'].get(reverse(nom_url, args=[obj.pk]), HTTP_HX_REQUEST='true').content.decode()
            for champ, valeur in attendus.items():
                motif = re.search(rf'name="{champ}"[^>]*value="([^"]*)"', html)
                assert motif, f'{nom_url} : champ {champ} introuvable'
                assert motif.group(1) == valeur, f'{nom_url} : {champ} rendu « {motif.group(1)} » au lieu de « {valeur} »'
                assert ',' not in motif.group(1)

    def test_aller_retour_sans_ressaisie(self, contexte):
        """Ce que le navigateur renvoie tel quel (valeurs rendues) doit être accepté et conservé."""
        for nom_url, obj, attendus, autres in self._cas(contexte['etab']):
            html = contexte['client'].get(reverse(nom_url, args=[obj.pk]), HTTP_HX_REQUEST='true').content.decode()
            donnees = dict(autres)
            for champ in attendus:
                donnees[champ] = re.search(rf'name="{champ}"[^>]*value="([^"]*)"', html).group(1)
            reponse = contexte['client'].post(reverse(nom_url, args=[obj.pk]), donnees, HTTP_HX_REQUEST='true')
            assert reponse.status_code == 204, f'{nom_url} : {reponse.content.decode()[:200]}'
            obj.refresh_from_db()
            for champ, valeur in attendus.items():
                assert getattr(obj, champ) == Decimal(valeur), f'{nom_url} : {champ} modifié'
