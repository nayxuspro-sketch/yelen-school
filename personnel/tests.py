import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestPersonnelViews:
    def test_personnel_list_redirect_anon(self, client):
        url = reverse('personnel:personnel_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_personnel_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('personnel:personnel_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_salaire_list_redirect_anon(self, client):
        url = reverse('personnel:salaire_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_salaire_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('personnel:salaire_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_conge_list_redirect_anon(self, client):
        url = reverse('personnel:conge_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_conge_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('personnel:conge_list')
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestSalairePersonnelModel:
    def test_prime_anciennete_moins_2_ans(self):
        from personnel.models import SalairePersonnel
        membre = baker.make('personnel.MembrePersonnel', date_embauche=date.today() - timedelta(days=365))
        prime = SalairePersonnel.calculer_prime_anciennete(membre, Decimal('100000'))
        assert prime == Decimal('0')

    def test_prime_anciennete_entre_2_et_5_ans(self):
        from personnel.models import SalairePersonnel
        membre = baker.make('personnel.MembrePersonnel', date_embauche=date.today() - timedelta(days=365 * 3))
        prime = SalairePersonnel.calculer_prime_anciennete(membre, Decimal('100000'))
        assert prime == Decimal('5000')

    def test_prime_anciennete_plus_20_ans(self):
        from personnel.models import SalairePersonnel
        membre = baker.make('personnel.MembrePersonnel', date_embauche=date.today() - timedelta(days=365 * 25))
        prime = SalairePersonnel.calculer_prime_anciennete(membre, Decimal('100000'))
        assert prime == Decimal('25000')

    def test_prime_anciennete_sans_date_embauche(self):
        from personnel.models import SalairePersonnel
        membre = baker.make('personnel.MembrePersonnel', date_embauche=None)
        prime = SalairePersonnel.calculer_prime_anciennete(membre, Decimal('100000'))
        assert prime == Decimal('0')


@pytest.mark.django_db
class TestCongePersonnelModel:
    def test_calcul_jours_ouvrables_semaine_complete(self):
        from personnel.models import CongePersonnel
        # Lundi au samedi = 6 jours ouvrables
        etab = baker.make('etablissements.Etablissement')
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab)
        conge = baker.prepare(
            'personnel.CongePersonnel',
            personnel=membre,
            date_debut=date(2026, 4, 6),   # lundi
            date_fin=date(2026, 4, 11),    # samedi
        )
        assert conge._calcul_jours_ouvrables() == 6

    def test_calcul_jours_ouvrables_exclut_dimanche(self):
        from personnel.models import CongePersonnel
        # Samedi + dimanche + lundi = 2 jours ouvrables (sam + lun)
        etab = baker.make('etablissements.Etablissement')
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab)
        conge = baker.prepare(
            'personnel.CongePersonnel',
            personnel=membre,
            date_debut=date(2026, 4, 11),  # samedi
            date_fin=date(2026, 4, 13),    # lundi
        )
        assert conge._calcul_jours_ouvrables() == 2

    def test_jours_restants_initial(self):
        from personnel.models import CongePersonnel
        etab = baker.make('etablissements.Etablissement')
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab)
        restants = CongePersonnel.jours_restants(membre, 2026)
        assert restants == CongePersonnel.DROITS_ANNUELS
