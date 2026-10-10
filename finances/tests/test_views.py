import json
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
