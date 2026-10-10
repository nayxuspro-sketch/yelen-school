"""
Recherche serveur d'élève du formulaire d'encaissement (thème performance).

Remplace le <select> qui embarquait toutes les inscriptions de l'année
(2 500 options) par un fragment HTMX de 20 résultats au plus.
"""
import pytest
from django.urls import reverse
from model_bakery import baker

from finances.selectors import RESULTATS_RECHERCHE_MAX

URL_RECHERCHE = 'finances:paiement_recherche_eleve'


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement')


@pytest.fixture
def annee(etab):
    return baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)


@pytest.fixture
def classe_6e(etab):
    return baker.make('parametres.Classe', etablissement=etab, nom='6e A')


@pytest.fixture
def comptable_client(client, etab):
    user = baker.make('accounts.User', role='COMPTABLE', etablissement=etab)
    client.force_login(user)
    return client


def _inscrire(annee, classe, nom, prenom, matricule='', **extra):
    eleve = baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, matricule=matricule or f'M-{nom}-{prenom}')
    champs = dict(statut='AFFECTE', est_exonere=False)
    champs.update(extra)
    return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, **champs)


@pytest.mark.django_db
class TestRechercheEleve:
    def test_terme_trop_court_ne_renvoie_rien(self, comptable_client, annee, classe_6e):
        _inscrire(annee, classe_6e, 'TRAORE', 'Awa')
        response = comptable_client.get(reverse(URL_RECHERCHE), {'q': 'T'})
        assert response.status_code == 200
        assert response.context['resultats'] == []
        assert response.context['trop_court'] is True
        assert 'au moins 2 caractères' in response.content.decode()

    def test_recherche_multi_mots_nom_et_classe(self, comptable_client, annee, etab, classe_6e):
        classe_5e = baker.make('parametres.Classe', etablissement=etab, nom='5e B')
        cible = _inscrire(annee, classe_6e, 'TRAORE', 'Awa')
        _inscrire(annee, classe_5e, 'TRAORE', 'Moussa')
        _inscrire(annee, classe_6e, 'OUEDRAOGO', 'Awa')

        response = comptable_client.get(reverse(URL_RECHERCHE), {'q': 'traore 6e'})

        assert [i.pk for i in response.context['resultats']] == [cible.pk]
        html = response.content.decode()
        assert f'value="{cible.pk}"' in html
        assert 'data-classe="6e A"' in html

    def test_recherche_par_matricule(self, comptable_client, annee, classe_6e):
        cible = _inscrire(annee, classe_6e, 'KABORE', 'Issa', matricule='2026-0042')
        _inscrire(annee, classe_6e, 'KABORE', 'Fati', matricule='2026-0043')
        response = comptable_client.get(reverse(URL_RECHERCHE), {'q': '0042'})
        assert [i.pk for i in response.context['resultats']] == [cible.pk]

    def test_exclut_exoneres_abandons_autres_etablissements_et_autres_annees(
        self, comptable_client, annee, etab, classe_6e
    ):
        visible = _inscrire(annee, classe_6e, 'SAWADOGO', 'Ali')
        _inscrire(annee, classe_6e, 'SAWADOGO', 'Exo', est_exonere=True)
        _inscrire(annee, classe_6e, 'SAWADOGO', 'Parti', statut='ABANDON')
        autre_annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=False)
        _inscrire(autre_annee, classe_6e, 'SAWADOGO', 'Ancien')
        autre_etab = baker.make('etablissements.Etablissement')
        autre_classe = baker.make('parametres.Classe', etablissement=autre_etab, nom='6e A')
        autre_annee_etab = baker.make('parametres.AnneeScolaire', etablissement=autre_etab, est_courante=True)
        _inscrire(autre_annee_etab, autre_classe, 'SAWADOGO', 'Voisin')

        response = comptable_client.get(reverse(URL_RECHERCHE), {'q': 'sawadogo'})

        assert [i.pk for i in response.context['resultats']] == [visible.pk]

    def test_limite_a_vingt_resultats_et_signale_la_troncature(self, comptable_client, annee, classe_6e):
        for i in range(RESULTATS_RECHERCHE_MAX + 5):
            _inscrire(annee, classe_6e, 'ZONGO', f'Prenom{i:02d}')
        response = comptable_client.get(reverse(URL_RECHERCHE), {'q': 'zongo'})
        assert len(response.context['resultats']) == RESULTATS_RECHERCHE_MAX
        assert response.context['tronque'] is True
        assert 'premiers résultats' in response.content.decode()

    def test_role_sans_droit_d_encaissement_refuse(self, client, etab, annee, classe_6e):
        user = baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab)
        client.force_login(user)
        response = client.get(reverse(URL_RECHERCHE), {'q': 'traore'})
        assert response.status_code == 403


@pytest.mark.django_db
class TestFormulairePaiementAllege:
    def test_le_formulaire_n_embarque_plus_la_liste_des_eleves(self, comptable_client, annee, classe_6e):
        for i in range(30):
            _inscrire(annee, classe_6e, 'DIALLO', f'Prenom{i:02d}')
        response = comptable_client.get(reverse('finances:paiement_create'))
        html = response.content.decode()
        assert response.status_code == 200
        assert 'inscriptions' not in response.context
        assert html.count('data-nom="DIALLO"') == 0
        assert 'id="insc-search"' in html and 'hx-get=' in html

    def test_preselection_depuis_la_situation_eleve(self, comptable_client, annee, classe_6e):
        inscription = _inscrire(annee, classe_6e, 'TRAORE', 'Awa')
        response = comptable_client.get(reverse('finances:paiement_create'), {'inscription': inscription.pk})
        assert response.context['inscription_selectionnee'] == inscription
        assert response.context['selected_inscription_id'] == str(inscription.pk)
        html = response.content.decode()
        assert f'id="id_inscription"\n                 value="{inscription.pk}"' in html or f'value="{inscription.pk}"' in html
        assert 'TRAORE Awa — 6e A' in html

    def test_preselection_hors_etablissement_ignoree(self, comptable_client, annee):
        autre_etab = baker.make('etablissements.Etablissement')
        autre_classe = baker.make('parametres.Classe', etablissement=autre_etab, nom='3e')
        autre_annee = baker.make('parametres.AnneeScolaire', etablissement=autre_etab, est_courante=True)
        intrus = _inscrire(autre_annee, autre_classe, 'INTRUS', 'X')
        response = comptable_client.get(reverse('finances:paiement_create'), {'inscription': intrus.pk})
        assert response.status_code == 200
        assert response.context['inscription_selectionnee'] is None

    def test_re_rendu_apres_erreur_conserve_l_eleve(self, comptable_client, annee, classe_6e):
        inscription = _inscrire(annee, classe_6e, 'TRAORE', 'Awa')
        response = comptable_client.post(reverse('finances:paiement_create'), {
            'inscription': str(inscription.pk),
            'mode_paiement': 'ESPECES',
            # aucune rubrique → erreur de validation, re-rendu du formulaire
        })
        assert response.status_code == 200
        assert response.context['errors']
        assert response.context['inscription_selectionnee'] == inscription
