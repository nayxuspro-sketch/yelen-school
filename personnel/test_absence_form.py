import pytest
from django.urls import reverse
from model_bakery import baker

from personnel.models import AbsencePersonnel, ObservationAbsence

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    prim = baker.make('parametres.Cycle', etablissement=etab, code='PRIM', nom='Primaire', ordre=1)
    sec = baker.make('parametres.Cycle', etablissement=etab, code='POST', nom='Post-primaire', ordre=2)
    maitre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salif',
                        fonction='Enseignant')
    maitre.cycles.add(prim)
    prof = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZONGO', prenom='Paul',
                      fonction='Professeur')
    prof.cycles.add(sec)
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return {'etab': etab, 'prim': prim, 'sec': sec, 'maitre': maitre, 'prof': prof, 'client': client}


def test_la_saisie_propose_le_cycle_lie_a_la_table_cycle(ecole):
    page = ecole['client'].get(reverse('personnel:absence_create'))
    assert page.status_code == 200
    html = page.content.decode()
    assert f'<option value="{ecole["prim"].pk}"' in html and 'Primaire' in html and 'Post-primaire' in html
    assert 'name="cycle"' in html
    assert list(page.context['cycles']) == [ecole['prim'], ecole['sec']]


def test_le_cycle_restreint_la_liste_des_agents(ecole):
    page = ecole['client'].get(reverse('personnel:absence_create'), {'cycle': ecole['sec'].pk})
    agents = list(page.context['form'].fields['personnel'].queryset)
    assert agents == [ecole['prof']]                       # seul l'agent du secondaire
    page = ecole['client'].get(reverse('personnel:absence_create'))
    assert set(page.context['form'].fields['personnel'].queryset) == {ecole['maitre'], ecole['prof']}


def test_observation_en_liste_deroulante_amorcee(ecole):
    form = ecole['client'].get(reverse('personnel:absence_create')).context['form']
    valeurs = [v for v, _ in form.fields['observation'].widget.choices]
    assert 'Raison de santé' in valeurs and 'Congé annuel' in valeurs and '' in valeurs


def test_le_bouton_ajoute_une_observation_manquante(ecole):
    url = reverse('personnel:observation_absence_create')
    assert ecole['client'].get(url).status_code == 200
    reponse = ecole['client'].post(url, {'libelle': 'Décès d’un proche'})
    assert reponse.status_code == 302
    observation = ObservationAbsence.objects.get(libelle='Décès d’un proche')
    assert observation.etablissement == ecole['etab']
    assert 'observation=' in reponse['Location']

    valeurs = [v for v, _ in ecole['client'].get(reverse('personnel:absence_create')).context['form']
               .fields['observation'].widget.choices]
    assert 'Décès d’un proche' in valeurs                 # la nouvelle observation est proposée


def test_absence_enregistree_avec_cycle_et_observation(ecole):
    reponse = ecole['client'].post(reverse('personnel:absence_create'), {
        'cycle': ecole['prim'].pk, 'personnel': ecole['maitre'].pk,
        'date_debut': '2026-11-02', 'date_fin': '2026-11-04', 'motif': 'MALADIE',
        'justifiee': 'on', 'observation': 'Raison de santé',
    })
    assert reponse.status_code == 302
    absence = AbsencePersonnel.objects.get(personnel=ecole['maitre'])
    assert absence.observation == 'Raison de santé' and absence.nombre_jours == 3 and absence.motif == 'MALADIE'
