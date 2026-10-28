"""Bandeau « ENVIRONNEMENT DE TEST » (YELEN_ENVIRONNEMENT=test) : présent sur la connexion et les pages
de l'application, absent en production."""
import pytest
from django.test import override_settings
from django.urls import reverse
from model_bakery import baker

BANDEAU = 'ENVIRONNEMENT DE TEST'


@pytest.mark.django_db
class TestBandeauEnvironnement:
    def test_absent_par_defaut(self, client):
        reponse = client.get(reverse('accounts:login'))
        assert reponse.status_code == 200
        assert BANDEAU not in reponse.content.decode()

    @override_settings(YELEN_ENVIRONNEMENT_TEST=True)
    def test_present_sur_la_connexion(self, client):
        reponse = client.get(reverse('accounts:login'))
        assert BANDEAU in reponse.content.decode()

    @override_settings(YELEN_ENVIRONNEMENT_TEST=True)
    def test_present_sur_les_pages_de_l_application(self, client):
        etablissement = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etablissement, is_superuser=True,
                          is_staff=True, must_change_password=False)
        client.force_login(user)
        reponse = client.get(reverse('licences:statut'))
        assert reponse.status_code == 200
        html = reponse.content.decode()
        assert BANDEAU in html
        assert 'class="app-layout env-test"' in html
