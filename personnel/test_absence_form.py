from datetime import date, time

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
    user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False, est_tous_cycles=True)
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


def _saisie(ecole, **extra):
    """Champs du formulaire « Saisie des absences quotidiennes des professeurs ». """
    classe = baker.make('parametres.Classe', etablissement=ecole['etab'], cycle=ecole['prim'], nom='CP1', niveau='CP1')
    matiere = baker.make('pedagogie.Matiere', code='MATH', nom='Mathématiques')
    donnees = {
        'cycle': ecole['prim'].pk, 'personnel': ecole['maitre'].pk, 'date': '2026-11-04',
        'classe': classe.pk, 'matiere': matiere.pk, 'heure_debut': '09:00', 'heure_fin': '11:00',
        'observation': 'Raison de santé',
    }
    donnees.update(extra)
    return donnees, classe, matiere


def test_absence_quotidienne_enregistree_avec_seance_et_heures(ecole):
    donnees, classe, matiere = _saisie(ecole)
    reponse = ecole['client'].post(reverse('personnel:absence_create'), donnees)
    assert reponse.status_code == 302
    absence = AbsencePersonnel.objects.get(personnel=ecole['maitre'])
    assert (absence.date_debut, absence.date_fin) == (date(2026, 11, 4), date(2026, 11, 4))
    assert (absence.classe, absence.matiere) == (classe, matiere)
    assert (absence.heure_debut, absence.heure_fin) == (time(9, 0), time(11, 0))
    assert absence.nombre_heures == 2.0 and absence.nombre_jours == 1
    assert absence.observation == 'Raison de santé' and absence.motif == 'MALADIE'      # motif déduit


def test_observation_obligatoire(ecole):
    donnees, _, _ = _saisie(ecole, observation='')
    page = ecole['client'].post(reverse('personnel:absence_create'), donnees)
    assert page.status_code == 200
    assert 'Sélectionnez obligatoirement une observation' in page.content.decode()
    assert not AbsencePersonnel.objects.exists()


def test_heure_de_fin_anterieure_refusee(ecole):
    donnees, _, _ = _saisie(ecole, heure_debut='11:00', heure_fin='09:00')
    page = ecole['client'].post(reverse('personnel:absence_create'), donnees)
    assert page.status_code == 200 and 'postérieure à l&#x27;heure de début' in page.content.decode()
    assert not AbsencePersonnel.objects.exists()


def test_le_formulaire_reprend_les_champs_de_la_maquette(ecole):
    baker.make('parametres.AnneeScolaire', etablissement=ecole['etab'], libelle='2026-2027', est_courante=True,
               date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    page = ecole['client'].get(reverse('personnel:absence_create'))
    html = page.content.decode()
    for libelle in ('Année scolaire', 'Date', 'Nom du professeur', 'Classe', 'Matière',
                    'Heure début', 'Heure fin', 'Nb heures', 'Observation'):
        assert libelle in html, libelle
    assert '2026-2027' in html
    assert reverse('personnel:observation_absence_create') in html      # bouton « + » à côté de l'observation
    assert 'name="observation"' in html and 'Aucune' not in html
