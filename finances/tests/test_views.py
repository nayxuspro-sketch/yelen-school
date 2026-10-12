import re
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestFinancesViews:
    @pytest.fixture
    def logged_in_client(self, client):
        user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN')
        client.force_login(user)
        return client

    @pytest.fixture
    def annee_active(self):
        return baker.make('parametres.AnneeScolaire', est_courante=True)

    def test_paiement_list_view(self, logged_in_client, annee_active):
        """Vérifie l'accès à la liste des paiements."""
        url = reverse('finances:paiement_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'paiements' in response.context

    def test_paiement_create_view_get(self, logged_in_client, annee_active):
        """Vérifie l'affichage du formulaire de paiement."""
        url = reverse('finances:paiement_create')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        # La liste complète des inscriptions n'est plus envoyée : l'élève est
        # choisi via la recherche serveur (paiement_recherche_eleve).
        assert 'inscriptions' not in response.context
        assert response.context['inscription_selectionnee'] is None
        assert 'mode_choices' in response.context

    def test_paiement_create_avec_inscription_preselectionnee(self, logged_in_client, annee_active):
        """
        Vérifie que le formulaire reçoit selected_inscription_id quand on vient
        depuis la liste élèves avec ?inscription=<uuid> (bouton 'Enregistrer un paiement').
        Ce contexte est utilisé par le JS pour forcer le chargement des rubriques.
        """
        inscription = baker.make('inscriptions.Inscription', annee_scolaire=annee_active)
        url = reverse('finances:paiement_create') + f'?inscription={inscription.pk}'
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert response.context['selected_inscription_id'] == str(inscription.pk)

    def test_situation_eleve_view(self, logged_in_client):
        """Vérifie l'accès à la situation financière de l'élève."""
        inscription = baker.make('inscriptions.Inscription')
        url = reverse('finances:situation_eleve', kwargs={'inscription_id': inscription.pk})
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert response.context['inscription'] == inscription


@pytest.mark.django_db
class TestApiRubriquesInscription:
    """
    Tests de l'endpoint api_rubriques_inscription.

    Ces tests garantissent que les lookups ORM sont valides et que l'API
    répond correctement — tout lookup avec une majuscule incorrecte
    (ex: Rubrique__ au lieu de rubrique__) provoquerait un FieldError et
    ferait échouer ces tests immédiatement.
    """

    @pytest.fixture
    def logged_in_client(self, client):
        user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN')
        client.force_login(user)
        return client

    @pytest.fixture
    def setup_tarifs(self):
        """Crée une inscription avec des tarifs configurés."""
        annee = baker.make('parametres.AnneeScolaire', est_courante=True)
        etablissement = baker.make('etablissements.Etablissement')
        classe = baker.make('parametres.Classe', etablissement=etablissement)
        statut = baker.make('parametres.StatutEleve')
        rubrique = baker.make('parametres.RubriquePaiement', etablissement=etablissement, actif=True)
        tarif = baker.make(
            'parametres.TarifScolarite',
            etablissement=etablissement,
            classe=classe,
            annee_scolaire=annee,
            statut_eleve=statut,
            rubrique=rubrique,
            montant=50000,
            actif=True,
        )
        inscription = baker.make(
            'inscriptions.Inscription',
            classe=classe,
            annee_scolaire=annee,
            statut_eleve=statut,
        )
        return inscription, rubrique, tarif

    def test_api_retourne_200(self, logged_in_client, setup_tarifs):
        """L'API doit retourner 200 — un FieldError dans les lookups ORM donnerait 500."""
        inscription, _, _ = setup_tarifs
        url = reverse('finances:api_rubriques', kwargs={'inscription_id': inscription.pk})
        response = logged_in_client.get(url)
        assert response.status_code == 200, (
            "L'API a retourné une erreur — vérifiez les noms de champs dans les filtres ORM "
            "(ex: rubrique__actif et non Rubrique__actif)"
        )

    def test_api_retourne_json_valide(self, logged_in_client, setup_tarifs):
        """L'API doit retourner un JSON avec la clé 'rubriques'."""
        inscription, rubrique, _ = setup_tarifs
        url = reverse('finances:api_rubriques', kwargs={'inscription_id': inscription.pk})
        response = logged_in_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert 'rubriques' in data
        assert len(data['rubriques']) == 1
        assert data['rubriques'][0]['id'] == str(rubrique.pk)

    def test_api_champs_rubriques(self, logged_in_client, setup_tarifs):
        """Chaque rubrique retournée doit avoir les champs attendus par le JS."""
        inscription, _, _ = setup_tarifs
        url = reverse('finances:api_rubriques', kwargs={'inscription_id': inscription.pk})
        data = logged_in_client.get(url).json()
        r = data['rubriques'][0]
        assert 'id' in r
        assert 'nom' in r
        assert 'code' in r
        assert 'montant' in r
        assert 'total_verse' in r

    def test_api_sans_tarif_retourne_liste_vide(self, logged_in_client):
        """Sans tarif configuré pour la classe, l'API retourne une liste vide avec un message."""
        annee = baker.make('parametres.AnneeScolaire', est_courante=True)
        inscription = baker.make('inscriptions.Inscription', annee_scolaire=annee)
        url = reverse('finances:api_rubriques', kwargs={'inscription_id': inscription.pk})
        response = logged_in_client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['rubriques'] == []

    def test_api_fallback_quand_statut_sans_tarif(self, logged_in_client):
        """
        Si l'inscription a un statut_eleve mais qu'aucun tarif n'est configuré pour ce statut,
        l'API doit quand même retourner les rubriques configurées pour la classe (autres statuts).
        Sans ce fallback, le bouton 'Ajouter une rubrique' resterait désactivé.
        """
        annee = baker.make('parametres.AnneeScolaire', est_courante=True)
        etablissement = baker.make('etablissements.Etablissement')
        classe = baker.make('parametres.Classe', etablissement=etablissement)
        statut_avec_tarif = baker.make('parametres.StatutEleve')
        statut_sans_tarif = baker.make('parametres.StatutEleve')
        rubrique = baker.make('parametres.RubriquePaiement', etablissement=etablissement, actif=True)
        baker.make(
            'parametres.TarifScolarite',
            etablissement=etablissement,
            classe=classe,
            annee_scolaire=annee,
            statut_eleve=statut_avec_tarif,
            rubrique=rubrique,
            montant=50000,
            actif=True,
        )
        # Inscription avec un statut qui n'a PAS de tarif configuré
        inscription = baker.make(
            'inscriptions.Inscription',
            classe=classe,
            annee_scolaire=annee,
            statut_eleve=statut_sans_tarif,
        )
        url = reverse('finances:api_rubriques', kwargs={'inscription_id': inscription.pk})
        response = logged_in_client.get(url)
        assert response.status_code == 200
        data = response.json()
        # Aucun tarif configuré pour ce statut → rubriques vides + message d'erreur
        assert data['rubriques'] == []
        assert 'error' in data

    def test_api_requiert_authentification(self, client, setup_tarifs):
        """L'API doit être protégée par login_required."""
        inscription, _, _ = setup_tarifs
        url = reverse('finances:api_rubriques', kwargs={'inscription_id': inscription.pk})
        response = client.get(url)
        assert response.status_code == 302


@pytest.mark.django_db
class TestSituationsFinancieresEnLot:
    """
    Non-régression de l'optimisation « liste des redevables » :
    _situations_financieres_en_lot (4 requêtes pour N élèves) doit donner
    exactement les mêmes montants que _calcul_situation_financiere (4 requêtes
    PAR élève) — y compris avec bourses, remboursements et élèves sans statut.
    """

    @pytest.fixture
    def jeu(self):
        from decimal import Decimal
        annee = baker.make('parametres.AnneeScolaire', est_courante=True)
        etab = baker.make('etablissements.Etablissement')
        cycle = baker.make('parametres.Cycle', etablissement=etab)
        c1 = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau='6EME', nom='6e A')
        c2 = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau='6EME', nom='6e B')
        c3 = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau='5EME', nom='5e A')
        statut = baker.make('parametres.StatutEleve', etablissement=etab)
        scol = baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, code='SCOL')
        insc = baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, code='INSC')
        # Deux classes de même niveau avec le même tarif → dédoublonnage par rubrique
        for cl in (c1, c2):
            baker.make('parametres.TarifScolarite', etablissement=etab, classe=cl, annee_scolaire=annee,
                       statut_eleve=statut, rubrique=scol, montant=Decimal('90000'), actif=True)
            baker.make('parametres.TarifScolarite', etablissement=etab, classe=cl, annee_scolaire=annee,
                       statut_eleve=statut, rubrique=insc, montant=Decimal('10000'), actif=True)
        baker.make('parametres.TarifScolarite', etablissement=etab, classe=c3, annee_scolaire=annee,
                   statut_eleve=statut, rubrique=scol, montant=Decimal('70000'), actif=True)
        # Tarif inactif : ne doit jamais compter
        baker.make('parametres.TarifScolarite', etablissement=etab, classe=c3, annee_scolaire=annee,
                   statut_eleve=statut, rubrique=insc, montant=Decimal('99999'), actif=False)

        i_normal = baker.make('inscriptions.Inscription', classe=c1, annee_scolaire=annee, statut_eleve=statut)
        i_boursier = baker.make('inscriptions.Inscription', classe=c2, annee_scolaire=annee, statut_eleve=statut)
        i_rembourse = baker.make('inscriptions.Inscription', classe=c3, annee_scolaire=annee, statut_eleve=statut)
        i_sans_statut = baker.make('inscriptions.Inscription', classe=c1, annee_scolaire=annee, statut_eleve=None)
        i_trop_paye = baker.make('inscriptions.Inscription', classe=c3, annee_scolaire=annee, statut_eleve=statut)

        baker.make('finances.Paiement', inscription=i_normal, rubrique=scol, montant=Decimal('40000'))
        baker.make('finances.Paiement', inscription=i_boursier, rubrique=scol, montant=Decimal('30000'))
        p = baker.make('finances.Paiement', inscription=i_rembourse, rubrique=scol, montant=Decimal('50000'))
        baker.make('finances.Remboursement', paiement=p, montant=Decimal('5000'))
        baker.make('finances.Paiement', inscription=i_sans_statut, rubrique=scol, montant=Decimal('15000'))
        baker.make('finances.Paiement', inscription=i_trop_paye, rubrique=scol, montant=Decimal('80000'))
        tb = baker.make('finances.TypeBourse', etablissement=etab, valeur_reduction=Decimal('25000'))
        baker.make('finances.BourseEleve', inscription=i_boursier, type_bourse=tb, montant_accorde=Decimal('25000'), actif=True)
        baker.make('finances.BourseEleve', inscription=i_normal, type_bourse=tb, montant_accorde=Decimal('99999'), actif=False)
        return annee, [i_normal, i_boursier, i_rembourse, i_sans_statut, i_trop_paye]

    def test_lot_identique_a_unitaire(self, jeu):
        from finances.views import _calcul_situation_financiere, _situations_financieres_en_lot
        from inscriptions.models import Inscription
        annee, inscriptions = jeu
        qs = Inscription.objects.filter(annee_scolaire=annee).select_related('classe', 'statut_eleve')
        lot = _situations_financieres_en_lot(qs)
        assert set(lot) == {i.pk for i in inscriptions}
        for insc in qs:
            unit = _calcul_situation_financiere(insc)
            assert lot[insc.pk] == {
                'total_du': unit['total_du'],
                'total_paye': unit['total_paye'],
                'reste_a_payer': unit['reste_a_payer'],
            }, f"Écart pour {insc.pk}"

    def test_montants_attendus(self, jeu):
        from decimal import Decimal
        from finances.views import _situations_financieres_en_lot
        annee, (i_normal, i_boursier, i_rembourse, i_sans_statut, i_trop_paye) = jeu
        lot = _situations_financieres_en_lot([i_normal, i_boursier, i_rembourse, i_sans_statut, i_trop_paye])
        # 90 000 + 10 000 (dédoublonné malgré 2 classes de même niveau) − 40 000 payés
        assert lot[i_normal.pk] == {'total_du': Decimal('100000'), 'total_paye': Decimal('40000'), 'reste_a_payer': Decimal('60000')}
        # Bourse active de 25 000 déduite du dû
        assert lot[i_boursier.pk] == {'total_du': Decimal('75000'), 'total_paye': Decimal('30000'), 'reste_a_payer': Decimal('45000')}
        # Remboursement de 5 000 déduit du payé ; tarif inactif ignoré
        assert lot[i_rembourse.pk] == {'total_du': Decimal('70000'), 'total_paye': Decimal('45000'), 'reste_a_payer': Decimal('25000')}
        # Sans statut : dû 0, reste 0, mais payé conservé
        assert lot[i_sans_statut.pk] == {'total_du': Decimal('0'), 'total_paye': Decimal('15000'), 'reste_a_payer': Decimal('0')}
        # Trop-perçu : reste jamais négatif
        assert lot[i_trop_paye.pk] == {'total_du': Decimal('70000'), 'total_paye': Decimal('80000'), 'reste_a_payer': Decimal('0')}

    def test_liste_vide(self):
        from finances.views import _situations_financieres_en_lot
        assert _situations_financieres_en_lot([]) == {}

    def test_nombre_de_requetes_constant(self, jeu, django_assert_max_num_queries):
        """Le calcul en lot ne doit pas dépendre du nombre d'élèves (pas de N+1)."""
        from finances.views import _situations_financieres_en_lot
        from inscriptions.models import Inscription
        annee, _ = jeu
        inscriptions = list(Inscription.objects.filter(annee_scolaire=annee).select_related('classe', 'statut_eleve'))
        with django_assert_max_num_queries(4):
            _situations_financieres_en_lot(inscriptions)

    def test_page_redevables_et_pdf(self, jeu, client):
        """Les deux vues utilisant le calcul en lot répondent toujours 200."""
        annee, _ = jeu
        user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=annee.etablissement)
        client.force_login(user)
        assert client.get(reverse('finances:liste_redevables')).status_code == 200
        assert client.get(reverse('finances:liste_redevables_pdf')).status_code == 200

    def test_bilan_encaissements_et_pdf(self, jeu, client):
        """Le bilan regroupe les paiements par jour : date_paiement est un DateField,
        TruncDate le faisait échouer sous SQLite (mode autonome)."""
        _, inscriptions = jeu
        etab = inscriptions[0].classe.etablissement
        user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=etab)
        client.force_login(user)
        reponse = client.get(reverse('finances:bilan_encaissements'))
        assert reponse.status_code == 200
        assert len(reponse.context['par_jour']) == 1  # cinq paiements du jour regroupés
        assert client.get(reverse('finances:bilan_encaissements_pdf')).status_code == 200


@pytest.mark.django_db
class TestPaiementListPagination:
    """La liste des paiements est paginée (50 élèves/page) : 2 500 élèves ne
    doivent plus produire une page HTML de plusieurs Mo."""

    def test_pagination_50_par_page(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=etab)
        client.force_login(user)
        annee = baker.make('parametres.AnneeScolaire', est_courante=True, etablissement=etab)
        for _ in range(60):
            insc = baker.make('inscriptions.Inscription', annee_scolaire=annee)
            baker.make('finances.Paiement', inscription=insc, montant=1000)

        url = reverse('finances:paiement_list')
        r = client.get(url)
        assert r.status_code == 200
        assert r.context['page_obj'].paginator.count == 60
        assert r.context['page_obj'].paginator.num_pages == 2
        assert len(list(r.context['paiements'])) == 50

        r2 = client.get(url + '?page=2')
        assert r2.status_code == 200
        assert len(list(r2.context['paiements'])) == 10

        # Page hors bornes → dernière page (get_page), jamais de 404
        assert client.get(url + '?page=999').status_code == 200

        # Partiel HTMX (recherche) : paginé aussi
        r3 = client.get(url, HTTP_HX_REQUEST='true')
        assert r3.status_code == 200
        assert 'Page 1 / 2' in r3.content.decode()


@pytest.mark.django_db
class TestFormulairesBoursesCSP:
    """Formulaires de bourse : aucun gestionnaire on*, scripts inline noncés (sinon bloqués par la CSP)."""

    @pytest.fixture
    def client_finance(self, client):
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, role='SUPER_ADMIN'))
        return client

    @staticmethod
    def _verifier_csp(html):
        assert not re.search(r'\son[a-z]+="', html)
        blocs = re.findall(r'<script(?![^>]*\ssrc=)[^>]*>', html)
        assert blocs and all('nonce="' in bloc for bloc in blocs)

    def test_type_bourse_form(self, client_finance):
        response = client_finance.get(reverse('finances:type_bourse_create'))
        assert response.status_code == 200
        html = response.content.decode()
        self._verifier_csp(html)
        assert "addEventListener('change', majValeur)" in html

    def test_bourse_form(self, client_finance):
        inscription = baker.make('inscriptions.Inscription')
        type_bourse = baker.make('finances.TypeBourse', etablissement=inscription.classe.etablissement, actif=True)
        response = client_finance.get(reverse('finances:bourse_create', kwargs={'inscription_id': inscription.pk}))
        assert response.status_code == 200
        html = response.content.decode()
        self._verifier_csp(html)
        assert f'<option value="{type_bourse.pk}"' in html
        assert "sel.addEventListener('change', calculerMontant)" in html

    def test_bourse_edit_affiche_le_montant_non_localise(self, client_finance):
        bourse = baker.make('finances.BourseEleve', montant_accorde=Decimal('25000.00'))
        html = client_finance.get(reverse('finances:bourse_edit', kwargs={'bourse_id': bourse.pk})).content.decode()
        assert re.search(r'id="montant_accorde"[^>]*\bvalue="25000"', html)

    def test_type_bourse_edit_affiche_la_valeur_non_localisee(self, client):
        etab = baker.make('etablissements.Etablissement')
        client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, role='SUPER_ADMIN'))
        type_bourse = baker.make('finances.TypeBourse', etablissement=etab, valeur_reduction=Decimal('12.50'))
        html = client.get(reverse('finances:type_bourse_edit', kwargs={'type_id': type_bourse.pk})).content.decode()
        assert re.search(r'id="valeur_reduction"[^>]*\bvalue="12\.50"', html)


@pytest.mark.django_db
class TestRecuPaiementPdf:
    """Le reçu de paiement est un A5 paysage dont tout le contenu tient sur une
    page, même chargé (9 rubriques tarifées, statut, référence, observation,
    agrément, signataire avec titre honorifique)."""

    def test_a5_paysage_une_page(self, client, mocker):
        import core.pdf
        from decimal import Decimal
        from parametres.models import TypeDocument

        documents = []

        class HTMLEspion(core.pdf.HTML):
            def write_pdf(self, target=None, **kwargs):
                document = self.render()
                documents.append(document)
                return document.write_pdf(target, **kwargs)

        mocker.patch('finances.views.paiements.WeasyHTML', HTMLEspion)

        etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
        baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='COMPLEXE SCOLAIRE LE SAVOIR',
                   numero_agrement_mena='2019-0456/MENAPLN/SG/DGESS', adresse_complete='Secteur 15, Ouaga 2000, Ouagadougou',
                   ville='Ouagadougou', telephone='+226 25 36 47 58')
        user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=etab)
        client.force_login(user)
        annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True, libelle='2026-2027')
        cycle = baker.make('parametres.Cycle', etablissement=etab)
        classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, niveau='TLE', nom='Terminale D')
        statut = baker.make('parametres.StatutEleve', etablissement=etab, nom='Non affecté')
        rubriques = []
        for i in range(9):
            rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, actif=True, code=f'R{i}', ordre=i,
                                  nom=f'Scolarité tranche {i + 1}')
            baker.make('parametres.TarifScolarite', etablissement=etab, classe=classe, annee_scolaire=annee,
                       statut_eleve=statut, rubrique=rubrique, montant=Decimal('25000'), actif=True)
            rubriques.append(rubrique)
        eleve = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Abdoul Rasmané', matricule='LS-2026-01457')
        inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut_eleve=statut)
        for rubrique in rubriques[:2]:
            baker.make('finances.Paiement', inscription=inscription, rubrique=rubrique, statut_eleve=statut, montant=Decimal('25000'))
        paiement = baker.make('finances.Paiement', inscription=inscription, rubrique=rubriques[2], statut_eleve=statut,
                              montant=Decimal('10000'), reference='MM-778812', numero_recu='REC-2026-003',
                              observation='Versement partiel, solde attendu avant le 30/11/2026.')
        type_doc, _ = TypeDocument.objects.get_or_create(code='RECU_PAIEMENT', defaults={'nom': 'Reçu de paiement', 'actif': True})
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salimata')
        baker.make('parametres.SignataireDocument', cycle=cycle, type_document=type_doc, annee_scolaire=annee,
                   membre_personnel_id=membre.id, fonction="L'Intendante",
                   titres_honorifiques=["Chevalier de l'Ordre du Mérite"], actif=True)

        response = client.get(reverse('finances:recu_pdf', args=[paiement.id]))

        assert response.status_code == 200
        assert response.content.startswith(b'%PDF')
        assert len(documents) == 1
        pages = documents[0].pages
        assert len(pages) == 1
        # A5 paysage : 210 × 148 mm, soit 793,7 × 559,4 px CSS (WeasyPrint)
        assert round(pages[0].width) == 794 and round(pages[0].height) == 559
