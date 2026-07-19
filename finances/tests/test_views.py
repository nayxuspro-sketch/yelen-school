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
        assert 'inscriptions' in response.context
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
