"""
Tests pour la génération automatique de l'année scolaire.
"""

import unittest.mock as um
from datetime import date, datetime

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from model_bakery import baker

from parametres.models import AnneeScolaire
import parametres.services
from parametres.services import auto_generer_annee_scolaire


# ─── HELPERS ────────────────────────────────────────────────────────


def _mock_now(annee, mois, jour):
    return um.patch.object(
        timezone,
        "now",
        return_value=datetime(annee, mois, jour, tzinfo=timezone.get_current_timezone()),
    )


def _make_etab(**kw):
    defaults = dict(nom="Test", code="TST", ville="Ouaga", pays="Burkina Faso")
    defaults.update(kw)
    return baker.make("etablissements.Etablissement", **defaults)


@pytest.fixture(autouse=True)
def _cache_mem(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.MIDDLEWARE = [
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "parametres.middleware.AnneeScolaireAutoMiddleware",
    ]


# ─── SERVICE ────────────────────────────────────────────────────────


class TestService:

    def test_avant_5_juillet_rien(self, db):
        _make_etab()
        with _mock_now(2026, 7, 4):
            assert auto_generer_annee_scolaire() == []

    def test_5_juillet_cree(self, db):
        etab = _make_etab()
        with _mock_now(2026, 7, 5):
            created = auto_generer_annee_scolaire()
        assert len(created) == 1
        a = created[0]
        assert a.libelle == "2026-2027"
        assert a.date_debut == date(2026, 10, 1)
        assert a.date_fin == date(2027, 6, 30)
        assert a.est_courante is True
        assert a.etablissement == etab

    def test_apres_5_juillet_cree(self, db):
        _make_etab()
        with _mock_now(2026, 9, 1):
            created = auto_generer_annee_scolaire()
        assert len(created) == 1
        assert created[0].libelle == "2026-2027"

    def test_ne_duplique_pas(self, db):
        etab = _make_etab()
        baker.make(AnneeScolaire, etablissement=etab, libelle="2026-2027")
        with _mock_now(2026, 7, 5):
            assert auto_generer_annee_scolaire() == []

    def test_bascule_courante(self, db):
        etab = _make_etab()
        ancienne = baker.make(AnneeScolaire, etablissement=etab, libelle="2025-2026", est_courante=True)
        with _mock_now(2026, 7, 5):
            created = auto_generer_annee_scolaire()
        assert len(created) == 1
        ancienne.refresh_from_db()
        assert ancienne.est_courante is False
        assert created[0].est_courante is True

    def test_force_outrepasse_date(self, db):
        _make_etab()
        with _mock_now(2026, 3, 1):
            created = auto_generer_annee_scolaire(force=True)
        assert len(created) == 1
        assert created[0].libelle == "2026-2027"

    def test_etablissement_specifique(self, db):
        e1 = _make_etab(nom="A", code="A")
        _make_etab(nom="B", code="B")
        with _mock_now(2026, 7, 5):
            created = auto_generer_annee_scolaire(etablissement=e1)
        assert len(created) == 1
        assert created[0].etablissement == e1

    def test_etablissement_inactif_ignore(self, db):
        _make_etab(is_active=False)
        with _mock_now(2026, 7, 5):
            assert auto_generer_annee_scolaire() == []

    def test_plusieurs_etablissements(self, db):
        e1 = _make_etab(nom="A", code="A")
        e2 = _make_etab(nom="B", code="B")
        with _mock_now(2026, 7, 5):
            created = auto_generer_annee_scolaire()
        assert len(created) == 2
        assert {a.etablissement_id for a in created} == {e1.pk, e2.pk}


# ─── COMMANDE ───────────────────────────────────────────────────────


class TestCommand:

    def test_dry_run_ne_cree_pas(self, db):
        _make_etab()
        with _mock_now(2026, 7, 5):
            call_command("auto_generer_annee_scolaire", dry_run=True)
        assert AnneeScolaire.objects.count() == 0

    def test_force_avant_juillet(self, db):
        _make_etab()
        with _mock_now(2026, 3, 1):
            call_command("auto_generer_annee_scolaire", force=True)
        assert AnneeScolaire.objects.count() == 1

    def test_normal(self, db):
        _make_etab()
        with _mock_now(2026, 7, 5):
            call_command("auto_generer_annee_scolaire")
        a = AnneeScolaire.objects.first()
        assert a is not None
        assert a.libelle == "2026-2027"
        assert a.est_courante is True

    def test_avant_5_juillet_rien(self, db):
        _make_etab()
        with _mock_now(2026, 7, 4):
            call_command("auto_generer_annee_scolaire")
        assert AnneeScolaire.objects.count() == 0


# ─── MIDDLEWARE ─────────────────────────────────────────────────────


class TestMiddleware:

    def test_declenche_generation(self, db, client):
        etab = _make_etab()
        user = baker.make("accounts.User", etablissement=etab, is_superuser=True)
        client.force_login(user)
        with _mock_now(2026, 7, 5):
            client.get("/")
        assert AnneeScolaire.objects.filter(etablissement=etab, libelle="2026-2027").exists()

    def test_une_fois_par_jour(self, db, client, mocker):
        etab = _make_etab()
        user = baker.make("accounts.User", etablissement=etab, is_superuser=True)
        client.force_login(user)
        spy = mocker.spy(parametres.services, "auto_generer_annee_scolaire")
        with _mock_now(2026, 7, 5):
            client.get("/")
            client.get("/")
        assert spy.call_count == 1
