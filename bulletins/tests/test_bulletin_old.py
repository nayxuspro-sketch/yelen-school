import pytest
from decimal import Decimal
from model_bakery import baker


@pytest.mark.django_db
class TestBulletinAnnuel:
    """Tests pour le bulletin annuel de notes."""

    def setup_method(self):
        self.etab = baker.make('etablissements.Etablissement')
        self.annee = baker.make('parametres.AnneeScolaire', etablissement=self.etab)
        self.classe = baker.make('parametres.Classe', etablissement=self.etab)
        self.eleve = baker.make(
            'inscriptions.Eleve',
            nom='Kaboré',
            prenom='Mamadou',
            date_naissance='2010-05-15',
        )
        self.inscription = baker.make(
            'inscriptions.Inscription',
            eleve=self.eleve,
            classe=self.classe,
            annee_scolaire=self.annee,
        )
        self.matiere = baker.make('pedagogie.Matiere', nom='Mathématiques')
        self.enseig = baker.make(
            'pedagogie.Enseignement',
            classe=self.classe,
            matiere=self.matiere,
        )
        self.trimestre1 = baker.make(
            'pedagogie.Trimestre',
            annee_scolaire=self.annee,
            numero=1,
            nom='Trimestre 1',
        )
        self.trimestre2 = baker.make(
            'pedagogie.Trimestre',
            annee_scolaire=self.annee,
            numero=2,
            nom='Trimestre 2',
        )
        self.trimestre3 = baker.make(
            'pedagogie.Trimestre',
            annee_scolaire=self.annee,
            numero=3,
            nom='Trimestre 3',
        )

    def _resultat(self, trimestre, moyenne_sur_20, coeff=2):
        return baker.make(
            'pedagogie.Resultat',
            inscription=self.inscription,
            enseignement=self.enseig,
            trimestre=trimestre,
            moyenne_sur_20=Decimal(str(moyenne_sur_20)),
            coefficient_utilise=Decimal(str(coeff)),
            dispense=False,
        )

    def test_moyenne_annuelle_est_moyenne_arithmetique_des_periodes(self):
        self._resultat(self.trimestre1, 16.00)
        self._resultat(self.trimestre2, 12.00)
        self._resultat(self.trimestre3, 14.00)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(self.inscription, self.annee)

        assert bulletin.moyenne_annuelle == Decimal("14.00")

    def test_passe_en_classe_superieure_si_moyenne_egale_a_10(self):
        self._resultat(self.trimestre1, 10.00)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(self.inscription, self.annee)

        assert bulletin.est_admis is True
        assert bulletin.decision == "Passe en classe supérieure"

    def test_passe_en_classe_superieure_si_moyenne_sup_10(self):
        self._resultat(self.trimestre1, 12.50)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(self.inscription, self.annee)

        assert bulletin.est_admis is True

    def test_redouble_si_moyenne_inferieure_a_10(self):
        self._resultat(self.trimestre1, 9.50)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(self.inscription, self.annee)

        assert bulletin.est_admis is False
        assert bulletin.decision == "Redouble la classe"

    def test_idempotence_recalcul(self):
        self._resultat(self.trimestre1, 14.00)

        from bulletins.services import calculer_bulletin_annuel
        bulletin1 = calculer_bulletin_annuel(self.inscription, self.annee)
        bulletin2 = calculer_bulletin_annuel(self.inscription, self.annee)

        assert bulletin1.pk == bulletin2.pk

    def test_json_ne_contient_pas_de_detail_matiere(self):
        self._resultat(self.trimestre1, 12.00)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(self.inscription, self.annee)

        for periode in bulletin.donnees_json['periodes']:
            assert 'matieres' in periode
            assert 'resultats' not in periode
            assert len(periode['matieres']) == 1

    def test_arrondi_a_deux_decimales(self):
        self._resultat(self.trimestre1, 12.50)
        self._resultat(self.trimestre2, 13.50)

        from bulletins.services import calculer_bulletin_annuel
        bulletin = calculer_bulletin_annuel(self.inscription, self.annee)

        assert bulletin.moyenne_annuelle == Decimal("13.00")

    def test_aucune_periode_ne_produit_bulletin_vide(self):
        from bulletins.services import calculer_bulletin_annuel
        from bulletins.models import BulletinAnnuel

        bulletin = calculer_bulletin_annuel(self.inscription, self.annee)

        assert bulletin.moyenne_annuelle == Decimal("0.00")
        assert bulletin.donnees_json['nombre_periodes'] == 0
