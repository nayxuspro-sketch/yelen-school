"""
Tests — vacations.models
"""

from decimal import Decimal

import pytest
from model_bakery import baker


@pytest.mark.django_db
class TestHeureVacationProperties:
    def _make_heure(self, effectuees, annulees, taux=Decimal('2500')):
        personnel = baker.make(
            'personnel.MembrePersonnel',
            nom='TEST', prenom='User', matricule='PERS-T-2026-0001',
            genre='M', nationalite='BF', lieu_naissance='OUA',
            telephone='0', numero_cni='B0', fonction='Ens.',
            titre_honorifique='M.', situation_matrimoniale='C',
            poste_principal_code='ENS',
        )
        contrat = baker.make(
            'vacations.ContratVacation',
            personnel=personnel,
            taux_horaire=taux,
        )
        return baker.make(
            'vacations.HeureVacation',
            contrat=contrat,
            heures_effectuees=Decimal(str(effectuees)),
            heures_annulees=Decimal(str(annulees)),
        )

    def test_heures_nettes_normal(self):
        h = self._make_heure(10, 2)
        assert h.heures_nettes == Decimal('8')

    def test_heures_nettes_ne_peut_pas_etre_negative(self):
        """Si annulées > effectuées, heures_nettes = 0."""
        h = self._make_heure(2, 5)
        assert h.heures_nettes == Decimal('0')

    def test_montant_du(self):
        h = self._make_heure(8, 0, taux=Decimal('3000'))
        assert h.montant_du == Decimal('24000')

    def test_montant_du_avec_annulations(self):
        h = self._make_heure(10, 2, taux=Decimal('2500'))
        assert h.montant_du == Decimal('20000')  # 8h × 2500


@pytest.mark.django_db
class TestBulletinVacationCalculTotaux:
    def test_calculer_totaux_heures_validees_uniquement(self, annee, personnel, contrat):
        # Une heure validée
        baker.make(
            'vacations.HeureVacation',
            contrat=contrat,
            mois=3, annee=2026,
            heures_effectuees=Decimal('8'),
            heures_annulees=Decimal('0'),
            est_valide=True,
        )
        # Une heure non validée (ne doit pas être comptée)
        baker.make(
            'vacations.HeureVacation',
            contrat=contrat,
            mois=4, annee=2026,
            heures_effectuees=Decimal('4'),
            heures_annulees=Decimal('0'),
            est_valide=False,
        )
        bulletin = baker.make(
            'vacations.BulletinVacation',
            personnel=personnel,
            annee_scolaire=annee,
            mois=3, annee=2026,
        )
        bulletin.calculer_totaux()

        assert bulletin.total_heures == Decimal('8')
        assert bulletin.montant_total == contrat.taux_horaire * Decimal('8')

    def test_calculer_totaux_sans_heures(self, annee, personnel):
        bulletin = baker.make(
            'vacations.BulletinVacation',
            personnel=personnel,
            annee_scolaire=annee,
            mois=5, annee=2026,
        )
        bulletin.calculer_totaux()

        assert bulletin.total_heures == Decimal('0')
        assert bulletin.montant_total == Decimal('0')


@pytest.mark.django_db
class TestContratVacationStr:
    def test_str_sans_enseignement(self, contrat):
        s = str(contrat)
        assert contrat.personnel.nom in s

    def test_str_contient_annee_scolaire(self, contrat, annee):
        assert annee.libelle in str(contrat)
