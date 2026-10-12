import re
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestExamensViews:
    def test_session_list_redirect_anon(self, client):
        url = reverse('examens:session_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_session_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('examens:session_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_session_create_redirect_anon(self, client):
        url = reverse('examens:session_create')
        response = client.get(url)
        assert response.status_code == 302

    def test_session_create_get(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('examens:session_create')
        response = client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
def test_saisie_resultats_affiche_la_moyenne_non_localisee(client):
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, role='SUPER_ADMIN'))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    session = baker.make('examens.SessionExamen', annee_scolaire=annee)
    candidat = baker.make('examens.InscriptionExamen', session=session, moyenne_examen=Decimal('11.75'))

    html = client.get(reverse('examens:saisie_resultats', kwargs={'session_id': session.pk})).content.decode()

    assert re.search(rf'name="moyenne_{candidat.pk}"\s+value="11\.75"', html)
