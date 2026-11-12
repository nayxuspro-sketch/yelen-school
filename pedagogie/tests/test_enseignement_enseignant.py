"""Le champ Enseignant d'une affectation est limité aux enseignants de sa classe."""

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import Enseignement, Matiere


@pytest.fixture
def contexte(db):
    etablissement = baker.make('etablissements.Etablissement')
    cycle = baker.make('parametres.Cycle', etablissement=etablissement, code='PRIM')
    classe = baker.make('parametres.Classe', etablissement=etablissement, cycle=cycle, nom='CP1', niveau='CP1')
    autre_classe = baker.make('parametres.Classe', etablissement=etablissement, cycle=cycle, nom='CP2', niveau='CP2')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etablissement, est_courante=True)
    matiere = Matiere.objects.create(code='MAT-PRI', nom='Mathématiques')
    baker.make('pedagogie.MatiereCycle', matiere=matiere, cycle=cycle)
    matiere_existante = Matiere.objects.create(code='MAT-EX', nom='Français')

    titulaire = baker.make(
        'personnel.MembrePersonnel', etablissement=etablissement, nom='KABORE', prenom='Awa',
        fonction='Enseignante', classe_affectation=classe, qualite_affectation='TITULAIRE',
    )
    suppleant = baker.make(
        'personnel.MembrePersonnel', etablissement=etablissement, nom='SAWADOGO', prenom='Salif',
        fonction='Enseignant', classe_affectation=classe, qualite_affectation='SUPPLEANT',
    )
    autre_enseignant = baker.make(
        'personnel.MembrePersonnel', etablissement=etablissement, nom='TRAORE', prenom='Moussa',
        fonction='Enseignant', classe_affectation=autre_classe,
    )
    enseignant_cours = baker.make(
        'personnel.MembrePersonnel', etablissement=etablissement, nom='ZONGO', prenom='Aminata',
        fonction='Enseignante',
    )
    sans_classe = baker.make(
        'personnel.MembrePersonnel', etablissement=etablissement, nom='OUEDRAOGO', prenom='Boureima',
        fonction='Enseignant',
    )
    baker.make(
        'pedagogie.Enseignement', classe=classe, matiere=matiere_existante,
        annee_scolaire=annee, personnel=enseignant_cours,
    )

    return {
        'etablissement': etablissement,
        'classe': classe,
        'annee': annee,
        'matiere': matiere,
        'titulaire': titulaire,
        'suppleant': suppleant,
        'autre_enseignant': autre_enseignant,
        'enseignant_cours': enseignant_cours,
        'sans_classe': sans_classe,
    }


@pytest.fixture
def admin_client(client, contexte):
    client.force_login(baker.make(
        'accounts.User',
        etablissement=contexte['etablissement'],
        role='SUPER_ADMIN',
        is_superuser=True,
    ))
    return client


def test_options_htmx_affichent_seulement_les_enseignants_de_la_classe(admin_client, contexte):
    response = admin_client.get(reverse('pedagogie:enseignement_matieres'), {
        'classe': str(contexte['classe'].pk),
    }, HTTP_HX_REQUEST='true')

    html = response.content.decode()
    assert response.status_code == 200
    for cle in ('titulaire', 'suppleant', 'enseignant_cours'):
        enseignant = contexte[cle]
        assert f'value="{enseignant.pk}"' in html
        assert enseignant.get_nom_complet() in html
        assert enseignant.matricule not in html
    assert str(contexte['autre_enseignant'].pk) not in html
    assert str(contexte['sans_classe'].pk) not in html


def test_post_accepte_un_enseignant_de_la_classe(admin_client, contexte):
    response = admin_client.post(reverse('pedagogie:enseignement_create'), {
        'classe': str(contexte['classe'].pk),
        'matiere': str(contexte['matiere'].pk),
        'annee_scolaire': str(contexte['annee'].pk),
        'personnel': str(contexte['enseignant_cours'].pk),
        'est_actif': 'on',
    })

    assert response.status_code == 302
    assert Enseignement.objects.get(classe=contexte['classe'], matiere=contexte['matiere']).personnel == contexte['enseignant_cours']


def test_post_refuse_un_enseignant_d_une_autre_classe(admin_client, contexte):
    response = admin_client.post(reverse('pedagogie:enseignement_create'), {
        'classe': str(contexte['classe'].pk),
        'matiere': str(contexte['matiere'].pk),
        'annee_scolaire': str(contexte['annee'].pk),
        'personnel': str(contexte['autre_enseignant'].pk),
        'est_actif': 'on',
    })

    assert response.status_code == 200
    assert 'personnel' in response.context['form'].errors
    assert Enseignement.objects.filter(classe=contexte['classe'], matiere=contexte['matiere']).count() == 0
