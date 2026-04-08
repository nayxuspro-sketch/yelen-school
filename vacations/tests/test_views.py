"""
Tests — vacations.views
"""

import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestContratListView:
    def test_redirige_si_anonyme(self, client):
        url = reverse('vacations:contrat_list')
        assert client.get(url).status_code == 302

    def test_accessible_connecte(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(reverse('vacations:contrat_list')).status_code == 200

    def test_affiche_contrats_annee_courante(self, client, admin_user, contrat):
        client.force_login(admin_user)
        response = client.get(reverse('vacations:contrat_list'))
        assert response.status_code == 200
        assert contrat in response.context['contrats']


@pytest.mark.django_db
class TestSaisieHeuresView:
    def test_redirige_si_anonyme(self, client, contrat):
        url = reverse('vacations:saisie_heures', kwargs={'contrat_id': contrat.pk})
        assert client.get(url).status_code == 302

    def test_accessible_connecte(self, client, admin_user, contrat):
        client.force_login(admin_user)
        url = reverse('vacations:saisie_heures', kwargs={'contrat_id': contrat.pk})
        assert client.get(url).status_code == 200

    def test_post_enregistre_heures(self, client, admin_user, contrat):
        client.force_login(admin_user)
        url = reverse('vacations:saisie_heures', kwargs={'contrat_id': contrat.pk})
        response = client.post(url, {
            'mois': 3,
            'annee': 2026,
            'heures_effectuees': '8',
            'heures_annulees': '0',
            'observations': '',
        })
        assert response.status_code == 302
        from vacations.models import HeureVacation
        assert HeureVacation.objects.filter(contrat=contrat, mois=3, annee=2026).exists()


@pytest.mark.django_db
class TestBulletinListView:
    def test_redirige_si_anonyme(self, client):
        assert client.get(reverse('vacations:bulletin_list')).status_code == 302

    def test_accessible_connecte(self, client, admin_user):
        client.force_login(admin_user)
        assert client.get(reverse('vacations:bulletin_list')).status_code == 200

    def test_filtre_par_statut(self, client, admin_user, annee, personnel):
        baker.make(
            'vacations.BulletinVacation',
            personnel=personnel,
            annee_scolaire=annee,
            mois=3, annee=2026,
            statut='PAYE',
        )
        autre_personnel = baker.make(
            'personnel.MembrePersonnel',
            nom='SOME', prenom='One', matricule='PERS-T-2026-0002',
            genre='F', nationalite='BF', lieu_naissance='OUA',
            telephone='1', numero_cni='B1', fonction='Ens.',
            titre_honorifique='Mme', situation_matrimoniale='C',
            poste_principal_code='ENS',
        )
        baker.make(
            'vacations.BulletinVacation',
            personnel=autre_personnel,
            annee_scolaire=annee,
            mois=4, annee=2026,
            statut='BROUILLON',
        )
        client.force_login(admin_user)
        response = client.get(reverse('vacations:bulletin_list'), {'statut': 'PAYE'})
        assert response.status_code == 200
        assert all(b.statut == 'PAYE' for b in response.context['bulletins'])


@pytest.mark.django_db
class TestValiderHeure:
    def test_valider_heure(self, client, admin_user, contrat):
        heure = baker.make('vacations.HeureVacation', contrat=contrat, est_valide=False)
        client.force_login(admin_user)
        url = reverse('vacations:valider_heure', kwargs={'heure_id': heure.pk})
        assert client.get(url).status_code == 302
        heure.refresh_from_db()
        assert heure.est_valide is True

    def test_invalider_heure(self, client, admin_user, contrat):
        heure = baker.make('vacations.HeureVacation', contrat=contrat, est_valide=True)
        client.force_login(admin_user)
        url = reverse('vacations:invalider_heure', kwargs={'heure_id': heure.pk})
        assert client.get(url).status_code == 302
        heure.refresh_from_db()
        assert heure.est_valide is False


@pytest.mark.django_db
class TestValiderBulletin:
    def test_valider_bulletin(self, client, admin_user, annee, personnel):
        bulletin = baker.make(
            'vacations.BulletinVacation',
            personnel=personnel,
            annee_scolaire=annee,
            statut='BROUILLON',
        )
        client.force_login(admin_user)
        url = reverse('vacations:valider_bulletin', kwargs={'bulletin_id': bulletin.pk})
        assert client.get(url).status_code == 302
        bulletin.refresh_from_db()
        assert bulletin.statut == 'VALIDE'

    def test_payer_bulletin(self, client, admin_user, annee, personnel):
        bulletin = baker.make(
            'vacations.BulletinVacation',
            personnel=personnel,
            annee_scolaire=annee,
            statut='VALIDE',
        )
        client.force_login(admin_user)
        url = reverse('vacations:payer_bulletin', kwargs={'bulletin_id': bulletin.pk})
        assert client.get(url).status_code == 302
        bulletin.refresh_from_db()
        assert bulletin.statut == 'PAYE'
        assert bulletin.date_paiement is not None
