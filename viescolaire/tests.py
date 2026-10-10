import pytest
from django.urls import reverse
from model_bakery import baker


@pytest.mark.django_db
class TestViescolaireViews:
    def test_conseil_list_redirect_anon(self, client):
        url = reverse('viescolaire:conseil_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_conseil_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('viescolaire:conseil_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_activite_list_redirect_anon(self, client):
        url = reverse('viescolaire:activite_list')
        response = client.get(url)
        assert response.status_code == 302

    def test_activite_list_logged_in(self, client):
        etab = baker.make('etablissements.Etablissement')
        user = baker.make('accounts.User', etablissement=etab)
        client.force_login(user)
        url = reverse('viescolaire:activite_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_sanction_list_redirect_anon(self, client):
        url = reverse('viescolaire:sanction_list')
        response = client.get(url)
        assert response.status_code == 302


class TestApercuEdtJours:
    """L'aperçu de génération d'EDT affiche le nom du jour côté serveur (plus de script inline,
    bloqué par la CSP) et seulement quand le jour change."""

    def test_jour_nom(self):
        from viescolaire.services import SeancePrevue
        seance = SeancePrevue(enseignement_id='x', jour=1, heure_debut='07:30', heure_fin='08:20',
                              matiere_nom='Maths', prof_nom='Zongo')
        assert seance.jour_nom == 'Lundi'
        seance.jour = 9
        assert seance.jour_nom == '9'

    @pytest.mark.django_db
    def test_apercu_sans_script_et_jour_affiche_une_fois(self):
        from django.template.loader import render_to_string
        from viescolaire.services import ResultatGeneration, SeancePrevue
        classe = baker.make('parametres.Classe')
        annee = baker.make('parametres.AnneeScolaire', etablissement=classe.etablissement)
        seances = [
            SeancePrevue('e1', 1, '07:30', '08:20', 'Maths', 'Zongo'),
            SeancePrevue('e2', 1, '08:20', '09:10', 'SVT', 'Kabore'),
            SeancePrevue('e3', 2, '07:30', '08:20', 'Anglais', 'Traore'),
        ]
        resultat = ResultatGeneration(seances=seances, nb_placees=3, nb_total=3)

        html = render_to_string('viescolaire/partials/edt_apercu.html',
                                {'classe': classe, 'annee': annee, 'mode': 'remplacer', 'resultat': resultat})

        assert '<script' not in html
        assert html.count('Lundi') == 1 and html.count('Mardi') == 1
        assert html.count('class="edt-gen-day-cell"') == 3
