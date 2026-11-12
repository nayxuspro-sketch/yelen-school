"""Le choix d'une matière dans une affectation dépend du cycle de la classe."""

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import Enseignement, Matiere


@pytest.fixture
def contexte(db):
    etablissement = baker.make('etablissements.Etablissement')
    primaire = baker.make('parametres.Cycle', etablissement=etablissement, code='PRIM')
    secondaire = baker.make('parametres.Cycle', etablissement=etablissement, code='SEC')
    classe_primaire = baker.make('parametres.Classe', etablissement=etablissement, cycle=primaire)
    classe_secondaire = baker.make('parametres.Classe', etablissement=etablissement, cycle=secondaire)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etablissement, est_courante=True)

    matiere_primaire = Matiere.objects.create(code='MAT-PRI', nom='Matière primaire')
    matiere_secondaire = Matiere.objects.create(code='MAT-SEC', nom='Matière secondaire')
    baker.make('pedagogie.MatiereCycle', matiere=matiere_primaire, cycle=primaire)
    baker.make('pedagogie.MatiereCycle', matiere=matiere_secondaire, cycle=secondaire)

    return {
        'etablissement': etablissement,
        'primaire': primaire,
        'secondaire': secondaire,
        'classe_primaire': classe_primaire,
        'classe_secondaire': classe_secondaire,
        'annee': annee,
        'matiere_primaire': matiere_primaire,
        'matiere_secondaire': matiere_secondaire,
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


def test_page_nouvelle_affectation_ne_propose_pas_de_matiere_avant_la_classe(admin_client, contexte):
    response = admin_client.get(reverse('pedagogie:enseignement_create'))

    assert response.status_code == 200
    form = response.context['form']
    assert not form.fields['matiere'].queryset.exists()
    assert form.fields['classe'].widget.attrs['hx-target'] == '#id_matiere'
    assert list(form.fields).index('classe') < list(form.fields).index('matiere')
    assert f'value="{contexte["matiere_primaire"].pk}"' not in response.content.decode()


def test_post_accepte_une_matiere_du_cycle_choisi(admin_client, contexte):
    response = admin_client.post(reverse('pedagogie:enseignement_create'), {
        'classe': str(contexte['classe_primaire'].pk),
        'matiere': str(contexte['matiere_primaire'].pk),
        'annee_scolaire': str(contexte['annee'].pk),
        'est_actif': 'on',
    })

    assert response.status_code == 302
    assert Enseignement.objects.filter(
        classe=contexte['classe_primaire'], matiere=contexte['matiere_primaire']
    ).exists()


def test_post_refuse_une_matiere_d_un_autre_cycle(admin_client, contexte):
    response = admin_client.post(reverse('pedagogie:enseignement_create'), {
        'classe': str(contexte['classe_primaire'].pk),
        'matiere': str(contexte['matiere_secondaire'].pk),
        'annee_scolaire': str(contexte['annee'].pk),
        'est_actif': 'on',
    })

    assert response.status_code == 200
    assert 'matiere' in response.context['form'].errors
    assert Enseignement.objects.count() == 0


def test_options_htmx_ne_retournent_que_les_matieres_du_cycle(admin_client, contexte):
    response = admin_client.get(reverse('pedagogie:enseignement_matieres'), {
        'classe': str(contexte['classe_primaire'].pk),
    }, HTTP_HX_REQUEST='true')

    html = response.content.decode()
    assert response.status_code == 200
    assert f'value="{contexte["matiere_primaire"].pk}"' in html
    assert str(contexte['matiere_secondaire'].pk) not in html
