"""Lot I — I3 référentiel des salles : CRUD, nom canonique, suggestions EDT, capacité, occupation."""
import pytest
from django.urls import reverse
from model_bakery import baker

from parametres.models import Salle
from viescolaire.models import SeanceCours

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement')
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False))
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    cycle = baker.make('parametres.Cycle', etablissement=etab)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6ème A', actif=True)
    prof = baker.make('personnel.MembrePersonnel', etablissement=etab)
    enseignement = baker.make('pedagogie.Enseignement', classe=classe, annee_scolaire=annee, personnel=prof,
                              heures_hebdomadaires=2, est_actif=True)
    baker.make('viescolaire.ConfigEDT', etablissement=etab, jours_actifs=[1, 2, 3, 4, 5])
    return {'etab': etab, 'annee': annee, 'classe': classe, 'enseignement': enseignement}


def test_crud_salles(client, ecole):
    assert client.get(reverse('parametres:salle_list')).status_code == 200
    reponse = client.post(reverse('parametres:salle_create'), {'nom': 'Salle 1', 'capacite': 45, 'actif': 'on'})
    assert reponse.status_code == 204 and 'parametreUpdated' in reponse['HX-Trigger']
    salle = Salle.objects.get(nom='Salle 1', etablissement=ecole['etab'])
    assert salle.capacite == 45
    # doublon (même nom, casse différente) refusé
    reponse = client.post(reverse('parametres:salle_create'), {'nom': 'salle 1', 'capacite': 40, 'actif': 'on'})
    assert reponse.status_code == 200 and Salle.objects.count() == 1
    client.post(reverse('parametres:salle_edit', args=[salle.pk]), {'nom': 'Salle 1', 'capacite': 50, 'actif': 'on'})
    salle.refresh_from_db()
    assert salle.capacite == 50
    html = client.get(reverse('parametres:salle_list'), HTTP_HX_REQUEST='true').content.decode()
    assert 'Salle 1' in html and '50' in html
    assert client.post(reverse('parametres:salle_delete', args=[salle.pk]), HTTP_HX_REQUEST='true').status_code in (200, 204)
    assert not Salle.objects.filter(pk=salle.pk).exists()


def test_salle_canonique_et_cloisonnement(ecole):
    Salle.objects.create(etablissement=ecole['etab'], nom='Salle Informatique', capacite=30)
    assert Salle.canonique(ecole['etab'], '  salle   INFORMATIQUE ') == 'Salle Informatique'
    assert Salle.canonique(ecole['etab'], 'Préau') == 'Préau'
    assert Salle.canonique(ecole['etab'], '') == ''
    autre = baker.make('etablissements.Etablissement')
    assert Salle.canonique(autre, 'salle informatique') == 'salle informatique'


def test_edt_propose_les_salles_normalise_et_avertit_sur_la_capacite(client, ecole):
    Salle.objects.create(etablissement=ecole['etab'], nom='Salle 2', capacite=1)
    Salle.objects.create(etablissement=ecole['etab'], nom='Labo', capacite=None, actif=False)
    for _ in range(2):
        baker.make('inscriptions.Inscription', classe=ecole['classe'], annee_scolaire=ecole['annee'],
                   eleve=baker.make('inscriptions.Eleve', photo=''))
    url = reverse('viescolaire:emploi_du_temps', args=[ecole['classe'].pk])
    html = client.get(url, {'annee': ecole['annee'].pk}).content.decode()
    assert '<datalist' in html and 'Salle 2' in html and 'Labo' not in html.split('<datalist')[1].split('</datalist>')[0]
    reponse = client.post(reverse('viescolaire:seance_create', args=[ecole['classe'].pk]), {
        'annee': ecole['annee'].pk, 'enseignement': ecole['enseignement'].pk, 'jour': 1,
        'heure_debut': '08:00', 'heure_fin': '08:50', 'salle': 'salle 2',
    }, follow=True)
    seance = SeanceCours.objects.get()
    assert seance.salle == 'Salle 2'
    texte = reponse.content.decode()
    assert 'compte 1 places pour 2 élèves' in texte
    # conflit de salle détecté malgré une casse différente, pour une autre classe
    classe_b = baker.make('parametres.Classe', etablissement=ecole['etab'], cycle=ecole['classe'].cycle, nom='5ème A', actif=True)
    ens_b = baker.make('pedagogie.Enseignement', classe=classe_b, annee_scolaire=ecole['annee'],
                       personnel=baker.make('personnel.MembrePersonnel', etablissement=ecole['etab']), est_actif=True)
    client.post(reverse('viescolaire:seance_create', args=[classe_b.pk]), {
        'annee': ecole['annee'].pk, 'enseignement': ens_b.pk, 'jour': 1,
        'heure_debut': '08:00', 'heure_fin': '08:50', 'salle': 'SALLE 2',
    })
    assert SeanceCours.objects.count() == 1


def test_occupation_des_salles(client, ecole):
    Salle.objects.create(etablissement=ecole['etab'], nom='Salle 2', capacite=40)
    baker.make('viescolaire.SeanceCours', enseignement=ecole['enseignement'], jour=1, heure_debut='08:00', heure_fin='09:00', salle='Salle 2')
    baker.make('viescolaire.SeanceCours', enseignement=ecole['enseignement'], jour=2, heure_debut='08:00', heure_fin='08:30', salle='Salle 2')
    baker.make('viescolaire.SeanceCours', enseignement=ecole['enseignement'], jour=3, heure_debut='10:00', heure_fin='11:00', salle='Préau')
    html = client.get(reverse('viescolaire:occupation_salles'), {'annee': ecole['annee'].pk}).content.decode()
    assert 'Salle 2' in html and 'Préau' in html and '1,50' in html   # 1 h 30 par semaine en Salle 2
    assert '6ème A' in html
