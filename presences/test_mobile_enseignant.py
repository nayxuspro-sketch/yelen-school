"""Appel depuis le smartphone de l'enseignant (« Mes cours ») et SMS d'absence à la clôture."""
import datetime
from unittest.mock import patch

import pytest
from django.urls import reverse
from model_bakery import baker

from presences.models import Appel, Presence


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement', nom='LE SAVOIR')


@pytest.fixture
def annee(etab):
    return baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True)


@pytest.fixture
def prof(client, etab):
    """Enseignant connecté, relié à sa fiche du personnel par l'e-mail."""
    user = baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, email='prof@yelen.test',
                      must_change_password=False)
    membre = baker.make('personnel.MembrePersonnel', etablissement=etab, email='Prof@yelen.test')
    client.force_login(user)
    return membre


def _enseignement(etab, annee, membre, classe_nom, matiere_nom):
    classe = baker.make('parametres.Classe', etablissement=etab, nom=classe_nom)
    matiere = baker.make('pedagogie.Matiere', nom=matiere_nom)
    return baker.make('pedagogie.Enseignement', classe=classe, matiere=matiere, annee_scolaire=annee, personnel=membre)


def _eleve_inscrit(classe, annee, **eleve):
    return baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee, statut='INSCRIT',
                      eleve=baker.make('inscriptions.Eleve', **eleve))


# ── Mes cours ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_mes_cours_seances_du_jour_puis_autres_cours(client, etab, annee, prof):
    aujourdhui = datetime.date.today()
    ens_jour = _enseignement(etab, annee, prof, '6e A', 'Mathématiques')
    baker.make('viescolaire.SeanceCours', enseignement=ens_jour, jour=aujourdhui.isoweekday(),
               heure_debut=datetime.time(8, 0), heure_fin=datetime.time(10, 0), salle='S2')
    ens_autre = _enseignement(etab, annee, prof, '5e B', 'Physique')
    # Enseignement d'un collègue : invisible
    _enseignement(etab, annee, baker.make('personnel.MembrePersonnel', etablissement=etab), '3e C', 'Histoire')

    response = client.get(reverse('presences:mes_cours'))

    assert response.status_code == 200
    assert [c['enseignement'] for c in response.context['cours_du_jour']] == [ens_jour]
    assert [c['enseignement'] for c in response.context['autres_cours']] == [ens_autre]
    html = response.content.decode()
    assert '08:00 – 10:00 · S2' in html and '3e C' not in html
    # Bouton « Faire l'appel » : POST pré-rempli (date du jour, matière, horaires de la séance)
    assert f'action="{reverse("presences:appel_create", args=[ens_jour.classe_id])}"' in html
    assert f'name="matiere" value="{ens_jour.matiere_id}"' in html
    assert 'name="heure_debut" value="08:00"' in html and 'name="heure_fin" value="10:00"' in html
    assert f'name="date" value="{aujourdhui:%Y-%m-%d}"' in html
    assert f'{reverse("pedagogie:evaluation_list")}?classe={ens_jour.classe_id}' in html


@pytest.mark.django_db
def test_mes_cours_appel_deja_fait_propose_de_le_reprendre(client, etab, annee, prof):
    ens = _enseignement(etab, annee, prof, '6e A', 'Mathématiques')
    appel = baker.make('presences.Appel', classe=ens.classe, annee_scolaire=annee, matiere=ens.matiere,
                       date=datetime.date.today(), est_clos=False)

    html = client.get(reverse('presences:mes_cours')).content.decode()

    assert reverse('presences:appel_saisie', args=[appel.pk]) in html
    assert 'Reprendre l\'appel' in html and 'Appel en brouillon' in html
    assert f'action="{reverse("presences:appel_create", args=[ens.classe_id])}"' not in html


@pytest.mark.django_db
def test_mes_cours_sans_fiche_personnel(client, etab, annee):
    client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, email='x@yelen.test',
                                  must_change_password=False))

    response = client.get(reverse('presences:mes_cours'))

    assert response.status_code == 200
    assert 'Aucune fiche du personnel' in response.content.decode()


@pytest.mark.django_db
def test_bouton_appel_cree_la_seance_avec_matiere_horaires_et_auteur(client, etab, annee, prof):
    ens = _enseignement(etab, annee, prof, '6e A', 'Mathématiques')
    _eleve_inscrit(ens.classe, annee, nom='Ouedraogo', prenom='Awa')
    baker.make('inscriptions.Inscription', classe=ens.classe, annee_scolaire=annee, statut='ABANDON')

    response = client.post(reverse('presences:appel_create', args=[ens.classe_id]), {
        'date': datetime.date.today().isoformat(), 'matiere': str(ens.matiere_id),
        'heure_debut': '08:00', 'heure_fin': '10:00',
    })

    appel = Appel.objects.get()
    assert response.status_code == 302 and response.url == reverse('presences:appel_saisie', args=[appel.pk])
    assert (appel.matiere, appel.heure_debut, appel.heure_fin, appel.effectue_par) == (
        ens.matiere, datetime.time(8, 0), datetime.time(10, 0), prof)
    assert appel.presences.count() == 1  # l'abandon n'est pas appelé


@pytest.mark.django_db
def test_appel_saisie_autre_etablissement_introuvable(client, etab, annee, prof):
    autre = baker.make('presences.Appel', classe__etablissement=baker.make('etablissements.Etablissement'))

    assert client.get(reverse('presences:appel_saisie', args=[autre.pk])).status_code == 404


# ── SMS d'absence à la clôture ─────────────────────────────────────────────────

@pytest.fixture
def appel_avec_absent(etab, annee, prof, settings):
    settings.SMS_ENABLED = True
    ens = _enseignement(etab, annee, prof, '6e A', 'Mathématiques')
    appel = baker.make('presences.Appel', classe=ens.classe, annee_scolaire=annee, matiere=ens.matiere,
                       date=datetime.date(2026, 10, 21), est_clos=False)
    absent = baker.make('presences.Presence', appel=appel, statut='PRESENT',
                        inscription=_eleve_inscrit(ens.classe, annee, nom='Ouedraogo', prenom='Awa',
                                                   telephone_parent='70 00 00 01'))
    retard = baker.make('presences.Presence', appel=appel, statut='PRESENT',
                        inscription=_eleve_inscrit(ens.classe, annee, nom='Kabore', prenom='Issa',
                                                   tuteur_telephone='70 00 00 02'))
    present = baker.make('presences.Presence', appel=appel, statut='PRESENT',
                         inscription=_eleve_inscrit(ens.classe, annee, nom='Sawadogo', prenom='Ali',
                                                    telephone_parent='70 00 00 03'))
    return appel, absent, retard, present


def _post_saisie(client, appel, absent, retard, present, clore=False):
    data = {f'statut_{absent.pk}': 'ABSENT', f'statut_{retard.pk}': 'RETARD', f'retard_{retard.pk}': '15',
            f'statut_{present.pk}': 'PRESENT'}
    if clore:
        data['clore'] = '1'
    return client.post(reverse('presences:appel_saisie', args=[appel.pk]), data)


@pytest.mark.django_db
@patch('core.tasks.envoyer_sms_async')
def test_brouillon_n_envoie_rien_cloture_informe_une_seule_fois(mock_sms, client, appel_avec_absent):
    appel, absent, retard, present = appel_avec_absent

    # 1. Enregistrement en brouillon : statuts enregistrés, aucun SMS
    assert _post_saisie(client, appel, absent, retard, present).status_code == 302
    absent.refresh_from_db()
    assert absent.statut == 'ABSENT' and absent.parents_notifies_le is None
    mock_sms.assert_not_called()

    # 2. Clôture : un SMS par absent / retardataire, le jour même, horodaté
    response = _post_saisie(client, appel, absent, retard, present, clore=True)
    assert response.status_code == 302
    envois = {appel_[0][0]: appel_[0][1] for appel_ in mock_sms.call_args_list}
    assert set(envois) == {'70 00 00 01', '70 00 00 02'}
    assert 'OUEDRAOGO AWA a été absent(e) le 21/10/2026 en Mathématiques' in envois['70 00 00 01']
    assert 'KABORE ISSA est arrivé(e) en retard le 21/10/2026 en Mathématiques' in envois['70 00 00 02']
    absent.refresh_from_db(); retard.refresh_from_db(); present.refresh_from_db()
    assert absent.parents_notifies_le and retard.parents_notifies_le and present.parents_notifies_le is None
    assert '2 famille(s) informée(s) par SMS' in client.get(reverse('presences:appel_list')).content.decode()

    # 3. Après clôture : plus aucun envoi, bannière récapitulative
    mock_sms.reset_mock()
    _post_saisie(client, appel, absent, retard, present, clore=True)
    assert mock_sms.call_count == 0
    assert '2 famille(s) informée(s) par SMS' in client.get(reverse('presences:appel_saisie', args=[appel.pk])).content.decode()


@pytest.mark.django_db
@patch('core.tasks.envoyer_sms_async')
def test_sms_desactives_horodatage_quand_meme(mock_sms, client, appel_avec_absent, settings):
    settings.SMS_ENABLED = False
    appel, absent, retard, present = appel_avec_absent

    _post_saisie(client, appel, absent, retard, present, clore=True)

    mock_sms.assert_not_called()
    absent.refresh_from_db()
    assert absent.parents_notifies_le is not None


@pytest.mark.django_db
@patch('core.tasks.envoyer_sms_async')
def test_enregistrer_une_presence_absente_ne_declenche_plus_de_sms(mock_sms, etab, annee, settings):
    """L'ancien signal post_save (un SMS à chaque enregistrement) est remplacé par l'envoi à la clôture."""
    settings.SMS_ENABLED = True
    presence = baker.make('presences.Presence', statut='PRESENT', inscription__eleve__telephone_parent='70 00 00 09')

    presence.statut = Presence.StatutChoices.ABSENT
    presence.save()

    mock_sms.assert_not_called()


@pytest.mark.django_db
def test_manifest_raccourcis_enseignant(client):
    data = client.get(reverse('core:app_manifest')).json()

    assert [s['url'] for s in data['shortcuts']] == ['/presences/mes-cours/', '/pedagogie/evaluations/']
