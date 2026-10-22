"""Période d'abonnement : les jours restants ne dépassent jamais les jours prévus.

La durée affichée (« X / Y jours ») et la barre de progression suivent la période en
cours de la licence (activation ou dernier renouvellement → expiration), et non une
année forfaitaire de 365 jours.
"""
from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from etablissements.models import Etablissement
from licences.models import Licence, StatutLicence, TypeLicence


@pytest.fixture
def etab():
    return baker.make(Etablissement)


def _licence(etab, jours, **attrs):
    licence = Licence(etablissement=etab, type_licence=TypeLicence.PREMIUM,
                      date_expiration=date.today() + timedelta(days=jours), **attrs)
    licence.save()
    return licence


@pytest.mark.django_db
class TestDureePeriode:
    def test_licence_en_attente_de_370_jours(self, etab):
        licence = _licence(etab, 370)
        assert licence.jours_restants() == 370
        assert licence.duree_periode() == 370
        assert licence.progression_periode() == 100

    def test_activation_fixe_le_debut_de_periode(self, etab):
        licence = _licence(etab, 370)
        licence.activer()
        assert licence.date_debut_periode == timezone.now().date()
        assert licence.duree_periode() == 370

    def test_periode_entamee(self, etab):
        licence = _licence(etab, 65, statut=StatutLicence.ACTIVE,
                           date_activation=timezone.now() - timedelta(days=300))
        assert licence.duree_periode() == 365
        assert licence.jours_restants() == 65
        assert licence.progression_periode() == 18

    def test_renouvellement_ouvre_une_nouvelle_periode(self, etab):
        licence = _licence(etab, 65, statut=StatutLicence.ACTIVE,
                           date_activation=timezone.now() - timedelta(days=300))
        licence.renouveler(duree_jours=180)
        assert licence.date_debut_periode == timezone.now().date()
        assert licence.date_expiration == timezone.now().date() + timedelta(days=180)
        assert licence.duree_periode() == 180
        assert licence.jours_restants() == 180
        assert licence.progression_periode() == 100

    def test_licence_expiree(self, etab):
        licence = _licence(etab, -10, statut=StatutLicence.EXPIREE,
                           date_activation=timezone.now() - timedelta(days=375))
        assert licence.duree_periode() == 365
        assert licence.progression_periode() == 0

    @pytest.mark.parametrize('jours', [1, 180, 365, 370, 730])
    def test_restants_jamais_superieurs_aux_prevus(self, etab, jours):
        licence = _licence(etab, jours)
        assert 0 <= licence.jours_restants() <= licence.duree_periode()
        assert 0 <= licence.progression_periode() <= 100


@pytest.mark.django_db
class TestPagesLicence:
    def test_mon_abonnement_affiche_la_duree_prevue(self, client, etab):
        _licence(etab, 370, statut=StatutLicence.ACTIVE, date_activation=timezone.now())
        client.force_login(baker.make('accounts.User', etablissement=etab, role='SUPER_ADMIN',
                                      must_change_password=False))
        html = client.get(reverse('licences:statut')).content.decode()
        assert '370 / 370 jours' in html
        assert 'width: 100%' in html
        assert '/ 365 jours' not in html

    def test_tableau_licences_barre_bornee(self, client, etab):
        _licence(etab, 370, statut=StatutLicence.ACTIVE, date_activation=timezone.now())
        client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True,
                                      must_change_password=False))
        html = client.get(reverse('licences:gestion')).content.decode()
        assert '370 j restants' in html
        assert '--pct: 100%' in html
