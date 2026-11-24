"""Le choix d'une matière dans une affectation dépend du cycle et de la classe."""

import pytest
from django.urls import reverse
from model_bakery import baker

from pedagogie.models import Enseignement, Matiere


def _matiere(code, nom, cycle, niveau='', serie=''):
    matiere = Matiere.objects.create(code=code, nom=nom)
    baker.make(
        'pedagogie.MatiereCycle',
        matiere=matiere,
        cycle=cycle,
        niveau=niveau,
        serie=serie,
    )
    return matiere


@pytest.fixture
def contexte(db):
    etablissement = baker.make('etablissements.Etablissement')
    primaire = baker.make('parametres.Cycle', etablissement=etablissement, code='PRIM')
    secondaire = baker.make('parametres.Cycle', etablissement=etablissement, code='SEC')
    classe_primaire = baker.make(
        'parametres.Classe', etablissement=etablissement, cycle=primaire, niveau='CP1', nom='CP1'
    )
    classe_secondaire = baker.make(
        'parametres.Classe', etablissement=etablissement, cycle=secondaire,
        niveau='Tle', serie_bac='D', nom='Terminale D',
    )
    annee = baker.make('parametres.AnneeScolaire', etablissement=etablissement, est_courante=True)

    matiere_primaire = _matiere('MAT-PRI', 'Matière primaire', primaire)
    matiere_cp1 = _matiere('MAT-CP1', 'Matière CP1', primaire, niveau='CP1')
    matiere_cp2 = _matiere('MAT-CP2', 'Matière CP2', primaire, niveau='CP2')
    matiere_secondaire = _matiere('MAT-SEC', 'Matière secondaire', secondaire)
    matiere_serie_d = _matiere('MAT-TD', 'Matière série D', secondaire, niveau='Tle', serie='D')
    matiere_serie_a = _matiere('MAT-TA', 'Matière série A', secondaire, niveau='Tle', serie='A')
    # Au primaire la liste reste limitée à la classe : l'enseignant doit y être titulaire.
    enseignant = baker.make('personnel.MembrePersonnel', etablissement=etablissement,
                            classe_affectation=classe_primaire, qualite_affectation='TITULAIRE')

    return {
        'enseignant': enseignant,
        'etablissement': etablissement,
        'classe_primaire': classe_primaire,
        'classe_secondaire': classe_secondaire,
        'annee': annee,
        'matiere_primaire': matiere_primaire,
        'matiere_cp1': matiere_cp1,
        'matiere_cp2': matiere_cp2,
        'matiere_secondaire': matiere_secondaire,
        'matiere_serie_d': matiere_serie_d,
        'matiere_serie_a': matiere_serie_a,
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


def test_page_nouvelle_affectation_attend_le_choix_de_classe(admin_client, contexte):
    response = admin_client.get(reverse('pedagogie:enseignement_create'))

    assert response.status_code == 200
    form = response.context['form']
    assert not form.fields['matiere'].queryset.exists()
    assert form.fields['classe'].widget.attrs['hx-target'] == '#id_matiere'
    assert list(form.fields)[:4] == ['annee_scolaire', 'classe', 'personnel', 'matiere']
    assert f'value="{contexte["matiere_primaire"].pk}"' not in response.content.decode()


def test_post_accepte_une_matiere_configuree_pour_le_cycle(admin_client, contexte):
    response = admin_client.post(reverse('pedagogie:enseignement_create'), {
        'classe': str(contexte['classe_primaire'].pk),
        'matiere': str(contexte['matiere_primaire'].pk),
        'annee_scolaire': str(contexte['annee'].pk),
        'personnel': str(contexte['enseignant'].pk),
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
        'personnel': str(contexte['enseignant'].pk),
        'est_actif': 'on',
    })

    assert response.status_code == 200
    assert 'matiere' in response.context['form'].errors
    assert Enseignement.objects.count() == 0


def test_post_refuse_une_matiere_configuree_pour_un_autre_niveau(admin_client, contexte):
    response = admin_client.post(reverse('pedagogie:enseignement_create'), {
        'classe': str(contexte['classe_primaire'].pk),
        'matiere': str(contexte['matiere_cp2'].pk),
        'annee_scolaire': str(contexte['annee'].pk),
        'personnel': str(contexte['enseignant'].pk),
        'est_actif': 'on',
    })

    assert response.status_code == 200
    assert 'matiere' in response.context['form'].errors
    assert Enseignement.objects.count() == 0


def test_options_htmx_filtrent_le_cycle_et_le_niveau(admin_client, contexte):
    response = admin_client.get(reverse('pedagogie:enseignement_matieres'), {
        'classe': str(contexte['classe_primaire'].pk),
    }, HTTP_HX_REQUEST='true')

    html = response.content.decode()
    assert response.status_code == 200
    assert f'value="{contexte["matiere_primaire"].pk}"' in html
    assert f'value="{contexte["matiere_cp1"].pk}"' in html
    assert str(contexte['matiere_cp2'].pk) not in html
    assert str(contexte['matiere_secondaire'].pk) not in html


def test_options_htmx_filtrent_la_serie_de_la_classe(admin_client, contexte):
    response = admin_client.get(reverse('pedagogie:enseignement_matieres'), {
        'classe': str(contexte['classe_secondaire'].pk),
    }, HTTP_HX_REQUEST='true')

    html = response.content.decode()
    assert response.status_code == 200
    assert f'value="{contexte["matiere_secondaire"].pk}"' in html
    assert f'value="{contexte["matiere_serie_d"].pk}"' in html
    assert str(contexte['matiere_serie_a'].pk) not in html
