"""Barre d'actions groupées des listes élèves / personnel / utilisateurs (partials/bulk_actions.html)."""
import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestBarreActionsGroupees:
    @pytest.fixture
    def client_admin(self, client):
        etab = baker.make('etablissements.Etablissement', code='BULK', nom='Lycée Bulk')
        client.force_login(baker.make('accounts.User', etablissement=etab, is_superuser=True, is_staff=True,
                                      role='SUPER_ADMIN', must_change_password=False))
        baker.make('inscriptions.Eleve', nom='Traoré', prenom='Awa')          # sans inscription : listé
        baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Ouédraogo', prenom='Issa', matricule='')
        return client

    @pytest.mark.parametrize('nom_liste, nom_export, htmx', [
        ('inscriptions:eleve_list', 'inscriptions:eleve_list_csv', True),
        ('personnel:personnel_list', 'personnel:personnel_list_csv', True),
        ('accounts:user_list', 'accounts:user_list_csv', False),
    ])
    def test_barre_rendue_sans_script_avec_export_nomme(self, client_admin, nom_liste, nom_export, htmx):
        extra = {'HTTP_HX_REQUEST': 'true'} if htmx else {}
        html = client_admin.get(reverse(nom_liste), **extra).content.decode()

        assert 'id="bulk-actions-bar" class="card bulk-actions-bar" hidden' in html
        assert f'data-csp-action="bulk-export" data-export-url="{reverse(nom_export)}"' in html
        assert 'class="bulk-checkbox"' in html and 'onchange=' not in html and 'toggleBulkBar' not in html
        if htmx:
            assert '<script' not in html  # un script dans un partiel HTMX serait bloqué (nonce différent)

        # L'URL d'export nommée répond (l'ancienne URL codée en dur des utilisateurs, /accounts/csv/, n'existait pas)
        assert client_admin.get(reverse(nom_export) + '?ids=').status_code == 200
