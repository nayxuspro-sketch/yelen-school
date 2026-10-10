import pytest
from decimal import Decimal
from django.urls import reverse
from model_bakery import baker
from pedagogie.models import Matiere, Note

@pytest.mark.django_db
class TestPedagogieViews:
    @pytest.fixture
    def logged_in_client(self, client):
        user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN')
        client.force_login(user)
        return client

    def test_matiere_list_view(self, logged_in_client):
        """Vérifie l'accès à la liste des matières."""
        url = reverse('pedagogie:matiere_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'matiere_list' in response.context

    def test_enseignement_list_view(self, logged_in_client):
        """Vérifie l'accès à la liste des enseignements."""
        baker.make('parametres.AnneeScolaire', est_courante=True)
        url = reverse('pedagogie:enseignement_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'classes_groupes' in response.context

    def test_enseignements_dans_le_menu_pedagogie(self, logged_in_client):
        """L'entrée « Enseignements » de la barre latérale (retirée par erreur dans d402ea0) suit « Matières »."""
        html = logged_in_client.get(reverse('pedagogie:matiere_list')).content.decode()
        menu = html.split('id="pedagogie-submenu"')[1].split('</div>')[0]
        lien = f'href="{reverse("pedagogie:enseignement_list")}" class="sb-item-submodern" data-url="/pedagogie/enseignements/"'
        assert lien in menu
        assert menu.index('>Matières<') < menu.index('>Enseignements<') < menu.index('>Évaluations<')

    def test_evaluation_list_view(self, logged_in_client):
        """Vérifie l'accès à la liste des évaluations."""
        baker.make('parametres.AnneeScolaire', est_courante=True)
        url = reverse('pedagogie:evaluation_list')
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert 'evaluation_list' in response.context

    def test_matiere_create_post(self, logged_in_client):
        """Vérifie la création d'une matière via POST."""
        url = reverse('pedagogie:matiere_create')
        data = {
            'code': 'MAT-FINAL', 
            'nom': 'Mathematiques Final', 
            'categorie': 'SCIENTIFIQUE',
            'coefficient': '2.00',
            'moy_max': '20.00',
            'moy_min': '0.00',
            'heures_hebdomadaires': '4.0',
            'est_discipline': False,
            'est_obligatoire': True
        }
        response = logged_in_client.post(url, data)
        # Si redirection (302), c'est un succès. Sinon, c'est que le form est invalide.
        assert response.status_code == 302
        assert Matiere.objects.filter(code='MAT-FINAL').exists()

    def test_evaluation_saisie_post(self, logged_in_client):
        """Vérifie la saisie groupée des notes."""
        annee = baker.make('parametres.AnneeScolaire', est_courante=True)
        classe = baker.make('parametres.Classe')
        ins = baker.make('inscriptions.Inscription', annee_scolaire=annee, classe=classe)
        ens = baker.make('pedagogie.Enseignement', annee_scolaire=annee, classe=classe)
        evaluation = baker.make('pedagogie.Evaluation', enseignement=ens)
        url = reverse('pedagogie:evaluation_saisie', kwargs={'pk': evaluation.pk})
        data = {f'note_{ins.id}': '18.5', f'obs_{ins.id}': 'Excellent'}
        response = logged_in_client.post(url, data)
        assert response.status_code == 302
        assert Note.objects.filter(inscription=ins, evaluation=evaluation, valeur=Decimal('18.5')).exists()

    def test_calculer_moyennes_classe_post(self, logged_in_client):
        """Vérifie le déclenchement du calcul des moyennes via POST."""
        classe = baker.make('parametres.Classe')
        trimestre = baker.make('pedagogie.Trimestre')
        url = reverse('pedagogie:calculer_moyennes_classe', kwargs={'class_id': classe.pk})
        response = logged_in_client.post(url, {'trimestre_id': trimestre.pk})
        assert response.status_code == 302
