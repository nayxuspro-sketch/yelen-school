"""
Tests unitaires pour la génération automatique de l'année scolaire.
Utilise uniquement unittest.mock pour éviter la dépendance à PostgreSQL.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import date, datetime

from django.utils import timezone


class TestServiceAutoGenererAnneeScolaire(unittest.TestCase):
    """Tests du service sans base de données réelle."""

    def _mock_now(self, annee, mois, jour):
        fixed = datetime(annee, mois, jour, tzinfo=timezone.get_current_timezone())
        return patch.object(timezone, "now", return_value=fixed)

    def test_avant_5_juillet_retourne_liste_vide(self):
        mock_etab = MagicMock(spec=["pk", "nom"])
        mock_etab.pk = "etab-1"
        mock_etab.nom = "Test"

        with self._mock_now(2026, 7, 4):
            with patch("parametres.models.AnneeScolaire") as mock_as:
                with patch("etablissements.models.Etablissement") as mock_et:
                    mock_et.objects.filter.return_value = [mock_etab]
                    from parametres.services import auto_generer_annee_scolaire
                    result = auto_generer_annee_scolaire()

        self.assertEqual(result, [])
        mock_as.objects.create.assert_not_called()

    def test_5_juillet_cree_nouvelle_annee(self):
        mock_etab = MagicMock(spec=["pk", "nom"])
        mock_etab.pk = "etab-1"
        mock_etab.nom = "Test School"

        with self._mock_now(2026, 7, 5):
            with patch("parametres.models.AnneeScolaire") as mock_as:
                with patch("etablissements.models.Etablissement") as mock_et:
                    mock_et.objects.filter.return_value = [mock_etab]
                    mock_as.objects.filter.return_value.exists.return_value = False

                    nouvelle = MagicMock()
                    nouvelle.libelle = "2026-2027"
                    nouvelle.date_debut = date(2026, 10, 1)
                    nouvelle.date_fin = date(2027, 6, 30)
                    nouvelle.est_courante = True
                    nouvelle.etablissement = mock_etab
                    mock_as.objects.create.return_value = nouvelle

                    from parametres.services import auto_generer_annee_scolaire
                    result = auto_generer_annee_scolaire()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].libelle, "2026-2027")
        self.assertEqual(result[0].date_debut, date(2026, 10, 1))
        self.assertEqual(result[0].date_fin, date(2027, 6, 30))
        self.assertTrue(result[0].est_courante)

    def test_force_outrepasse_date(self):
        mock_etab = MagicMock(spec=["pk", "nom"])
        mock_etab.pk = "etab-1"

        with self._mock_now(2026, 3, 1):
            with patch("parametres.models.AnneeScolaire") as mock_as:
                with patch("etablissements.models.Etablissement") as mock_et:
                    mock_et.objects.filter.return_value = [mock_etab]
                    mock_as.objects.filter.return_value.exists.return_value = False
                    nouvelle = MagicMock()
                    nouvelle.libelle = "2026-2027"
                    mock_as.objects.create.return_value = nouvelle

                    from parametres.services import auto_generer_annee_scolaire
                    result = auto_generer_annee_scolaire(force=True)

        self.assertEqual(len(result), 1)

    def test_etablissement_inactif_ignore(self):
        with self._mock_now(2026, 7, 5):
            with patch("etablissements.models.Etablissement") as mock_et:
                mock_et.objects.filter.return_value = []
                from parametres.services import auto_generer_annee_scolaire
                result = auto_generer_annee_scolaire()
        self.assertEqual(result, [])

    def test_bascule_est_courante(self):
        mock_etab = MagicMock(spec=["pk", "nom"])
        mock_etab.pk = "etab-1"
        mock_etab.nom = "Test"

        with self._mock_now(2026, 7, 5):
            with patch("parametres.models.AnneeScolaire") as mock_as:
                with patch("etablissements.models.Etablissement") as mock_et:
                    mock_et.objects.filter.return_value = [mock_etab]
                    mock_as.objects.filter.return_value.exists.return_value = False
                    nouvelle = MagicMock()
                    nouvelle.libelle = "2026-2027"
                    nouvelle.est_courante = True
                    mock_as.objects.create.return_value = nouvelle

                    from parametres.services import auto_generer_annee_scolaire
                    result = auto_generer_annee_scolaire()

        mock_as.objects.filter.assert_any_call(
            etablissement=mock_etab, est_courante=True
        )
        mock_as.objects.filter.return_value.update.assert_called_with(
            est_courante=False
        )

    def test_ne_duplique_pas(self):
        mock_etab = MagicMock(spec=["pk", "nom"])
        mock_etab.pk = "etab-1"

        with self._mock_now(2026, 7, 5):
            with patch("parametres.models.AnneeScolaire") as mock_as:
                with patch("etablissements.models.Etablissement") as mock_et:
                    mock_et.objects.filter.return_value = [mock_etab]
                    mock_as.objects.filter.return_value.exists.return_value = True

                    from parametres.services import auto_generer_annee_scolaire
                    result = auto_generer_annee_scolaire()

        self.assertEqual(result, [])
        mock_as.objects.create.assert_not_called()

    def test_plusieurs_etablissements(self):
        e1 = MagicMock(spec=["pk", "nom"])
        e1.pk = "etab-1"
        e1.nom = "A"
        e2 = MagicMock(spec=["pk", "nom"])
        e2.pk = "etab-2"
        e2.nom = "B"

        with self._mock_now(2026, 7, 5):
            with patch("parametres.models.AnneeScolaire") as mock_as:
                with patch("etablissements.models.Etablissement") as mock_et:
                    mock_et.objects.filter.return_value = [e1, e2]
                    mock_as.objects.filter.return_value.exists.return_value = False

                    n1 = MagicMock()
                    n1.etablissement_id = e1.pk
                    n2 = MagicMock()
                    n2.etablissement_id = e2.pk
                    mock_as.objects.create.side_effect = [n1, n2]

                    from parametres.services import auto_generer_annee_scolaire
                    result = auto_generer_annee_scolaire()

        self.assertEqual(len(result), 2)


class TestManagementCommand(unittest.TestCase):
    """Tests de la commande de gestion."""

    def test_dry_run_ne_leve_pas_derreur(self):
        """dry-run s'exécute sans planter."""
        with patch("etablissements.models.Etablissement") as mock_et:
            mock_et.objects.filter.return_value = []
            from django.core.management import call_command
            call_command("auto_generer_annee_scolaire", dry_run=True)

    def test_force_appelle_service_avec_force(self):
        """--force transmet force=True au service."""
        annee_mock = MagicMock()
        annee_mock.libelle = "2026-2027"
        annee_mock.etablissement.nom = "Test"

        with patch(
            "parametres.services.auto_generer_annee_scolaire"
        ) as mock_svc:
            mock_svc.return_value = [annee_mock]
            from django.core.management import call_command
            call_command("auto_generer_annee_scolaire", force=True)
            mock_svc.assert_called_once_with(force=True)

    def test_commande_sans_dry_run_appelle_service(self):
        """Sans dry-run, la commande appelle le service sans force."""
        with patch(
            "parametres.services.auto_generer_annee_scolaire"
        ) as mock_svc:
            mock_svc.return_value = []
            from django.core.management import call_command
            call_command("auto_generer_annee_scolaire")
            mock_svc.assert_called_once_with(force=False)


if __name__ == "__main__":
    unittest.main()
