"""
Liste des évaluations : filtres classe/trimestre et pagination par classe
(thème performance — ~6 000 évaluations par an pour 2 500 élèves).
"""
import datetime

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import Trimestre
from pedagogie.views import EVALUATIONS_CLASSES_PAR_PAGE

URL = 'pedagogie:evaluation_list'


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement')


@pytest.fixture
def annee(etab):
    return baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)


@pytest.fixture
def admin_client(client, etab):
    user = baker.make('accounts.User', is_superuser=True, role='SUPER_ADMIN', etablissement=etab)
    client.force_login(user)
    return client


def _classe_avec_evaluations(etab, annee, nom, nb_evaluations=2, trimestre=None, matiere=None):
    classe = baker.make('parametres.Classe', etablissement=etab, nom=nom)
    matiere = matiere or baker.make('pedagogie.Matiere', nom=f'Matière {nom}')
    enseignement = baker.make('pedagogie.Enseignement', classe=classe, matiere=matiere, annee_scolaire=annee)
    trimestre = trimestre or (
        Trimestre.objects.filter(annee_scolaire=annee, numero=1).first()
        or baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 1', numero=1)
    )
    for i in range(nb_evaluations):
        baker.make('pedagogie.Evaluation', enseignement=enseignement, trimestre=trimestre,
                   titre=f'Devoir {i + 1} {nom}', date_planifiee=datetime.date(2026, 10, 1 + i), bareme=20)
    return classe


@pytest.mark.django_db
class TestPaginationParClasse:
    def test_premiere_page_limitee_a_n_classes(self, admin_client, etab, annee):
        noms = [f'Classe {i:02d}' for i in range(EVALUATIONS_CLASSES_PAR_PAGE + 2)]
        for nom in noms:
            _classe_avec_evaluations(etab, annee, nom)

        response = admin_client.get(reverse(URL))

        assert response.status_code == 200
        groupes = response.context['groupes']
        assert [g['classe'].nom for g in groupes] == noms[:EVALUATIONS_CLASSES_PAR_PAGE]
        assert response.context['page_obj'].paginator.num_pages == 2
        assert response.context['total_evaluations'] == 2 * len(noms)
        # Seules les évaluations des classes de la page sont chargées
        assert len(response.context['evaluation_list']) == 2 * EVALUATIONS_CLASSES_PAR_PAGE

    def test_deuxieme_page(self, admin_client, etab, annee):
        noms = [f'Classe {i:02d}' for i in range(EVALUATIONS_CLASSES_PAR_PAGE + 2)]
        for nom in noms:
            _classe_avec_evaluations(etab, annee, nom)

        response = admin_client.get(reverse(URL), {'page': 2})

        assert [g['classe'].nom for g in response.context['groupes']] == noms[EVALUATIONS_CLASSES_PAR_PAGE:]

    def test_fragment_htmx_contient_la_pagination_avec_les_filtres(self, admin_client, etab, annee):
        for i in range(EVALUATIONS_CLASSES_PAR_PAGE + 1):
            _classe_avec_evaluations(etab, annee, f'Classe {i:02d}')

        response = admin_client.get(reverse(URL), {'q': 'Devoir'}, HTTP_HX_REQUEST='true')

        html = response.content.decode()
        assert response.status_code == 200
        assert '<html' not in html.lower()          # fragment seulement
        assert 'page=2&q=Devoir' in html            # filtre conservé dans le lien
        assert 'hx-target="#evaluation-table"' in html

    def test_classe_sans_evaluation_n_apparait_pas(self, admin_client, etab, annee):
        _classe_avec_evaluations(etab, annee, 'Avec devoirs')
        baker.make('parametres.Classe', etablissement=etab, nom='Sans devoir')

        response = admin_client.get(reverse(URL))

        assert [g['classe'].nom for g in response.context['groupes']] == ['Avec devoirs']
        assert [c.nom for c in response.context['classes']] == ['Avec devoirs']


@pytest.mark.django_db
class TestFiltres:
    def test_filtre_par_classe(self, admin_client, etab, annee):
        c1 = _classe_avec_evaluations(etab, annee, '6e A')
        _classe_avec_evaluations(etab, annee, '6e B')

        response = admin_client.get(reverse(URL), {'classe': str(c1.pk)})

        assert [g['classe'].pk for g in response.context['groupes']] == [c1.pk]
        assert response.context['classe_id'] == str(c1.pk)
        assert response.context['total_evaluations'] == 2

    def test_filtre_par_trimestre(self, admin_client, etab, annee):
        t1 = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 1', numero=1)
        t2 = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 2', numero=2)
        _classe_avec_evaluations(etab, annee, '6e A', nb_evaluations=3, trimestre=t1)
        _classe_avec_evaluations(etab, annee, '5e A', nb_evaluations=1, trimestre=t2)

        response = admin_client.get(reverse(URL), {'trimestre': str(t2.pk)})

        assert [g['classe'].nom for g in response.context['groupes']] == ['5e A']
        assert response.context['total_evaluations'] == 1
        assert [t.nom for t in response.context['trimestres']] == ['Trimestre 1', 'Trimestre 2']

    def test_filtre_invalide_ignore_sans_erreur(self, admin_client, etab, annee):
        _classe_avec_evaluations(etab, annee, '6e A')

        response = admin_client.get(reverse(URL), {'classe': 'pas-un-uuid', 'trimestre': '42', 'page': 'abc'})

        assert response.status_code == 200
        assert response.context['classe_id'] == ''
        assert response.context['trimestre_id'] == ''
        assert len(response.context['groupes']) == 1

    def test_recherche_texte_combinee_a_la_pagination(self, admin_client, etab, annee):
        for i in range(EVALUATIONS_CLASSES_PAR_PAGE + 3):
            _classe_avec_evaluations(etab, annee, f'Classe {i:02d}')
        derniere = f'Classe {EVALUATIONS_CLASSES_PAR_PAGE + 2:02d}'   # serait en page 2 sans filtre

        response = admin_client.get(reverse(URL), {'q': derniere})

        assert [g['classe'].nom for g in response.context['groupes']] == [derniere]
        assert response.context['page_obj'].paginator.num_pages == 1


@pytest.mark.django_db
def test_enseignant_ne_voit_que_ses_classes(client, etab, annee):
    # Rapprochement User ↔ MembrePersonnel par e-mail (voir core.utils.get_membre_personnel)
    user = baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, email='prof@yelen.test')
    membre = baker.make('personnel.MembrePersonnel', etablissement=etab, email='Prof@yelen.test')
    sa_classe = baker.make('parametres.Classe', etablissement=etab, nom='Sa classe')
    ens = baker.make('pedagogie.Enseignement', classe=sa_classe, annee_scolaire=annee, personnel=membre)
    tri = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1)
    baker.make('pedagogie.Evaluation', enseignement=ens, trimestre=tri, date_planifiee=datetime.date(2026, 10, 1), bareme=20)
    _classe_avec_evaluations(etab, annee, 'Autre classe', trimestre=tri)
    client.force_login(user)

    response = client.get(reverse(URL))

    assert response.status_code == 200
    assert [g['classe'].nom for g in response.context['groupes']] == ['Sa classe']
    assert [c.nom for c in response.context['classes']] == ['Sa classe']


@pytest.mark.django_db
class TestTrimestreParDefaut:
    def _deux_trimestres(self, etab, annee):
        aujourd_hui = datetime.date.today()
        passe = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 1', numero=1,
                           date_debut=aujourd_hui - datetime.timedelta(days=200),
                           date_fin=aujourd_hui - datetime.timedelta(days=100))
        en_cours = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 2', numero=2,
                              date_debut=aujourd_hui - datetime.timedelta(days=30),
                              date_fin=aujourd_hui + datetime.timedelta(days=60))
        _classe_avec_evaluations(etab, annee, '6e A', nb_evaluations=3, trimestre=passe)
        _classe_avec_evaluations(etab, annee, '5e A', nb_evaluations=1, trimestre=en_cours)
        return passe, en_cours

    def test_premier_affichage_limite_au_trimestre_en_cours(self, admin_client, etab, annee):
        _, en_cours = self._deux_trimestres(etab, annee)

        response = admin_client.get(reverse(URL))

        assert response.context['trimestre_id'] == str(en_cours.pk)
        assert [g['classe'].nom for g in response.context['groupes']] == ['5e A']
        assert f'trimestre={en_cours.pk}' in response.context['params']

    def test_choix_explicite_tous_les_trimestres(self, admin_client, etab, annee):
        self._deux_trimestres(etab, annee)

        response = admin_client.get(reverse(URL), {'trimestre': ''})

        assert response.context['trimestre_id'] == ''
        assert [g['classe'].nom for g in response.context['groupes']] == ['5e A', '6e A']
        assert response.context['total_evaluations'] == 4

    def test_sans_trimestre_en_cours_toute_l_annee_est_affichee(self, admin_client, etab, annee):
        passe = baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 1', numero=1,
                           date_debut=datetime.date(2020, 1, 1), date_fin=datetime.date(2020, 3, 31))
        _classe_avec_evaluations(etab, annee, '6e A', trimestre=passe)

        response = admin_client.get(reverse(URL))

        assert response.context['trimestre_id'] == ''
        assert len(response.context['groupes']) == 1
