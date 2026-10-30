"""Un enseignant ne fait l'appel que de ses classes (enseignements actifs de l'année, Pédagogie › Enseignements)."""
import datetime
import json

import pytest
from django.urls import reverse
from django.utils.html import escape
from model_bakery import baker

from presences.models import Appel


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
    membre = baker.make('personnel.MembrePersonnel', etablissement=etab, email='prof@yelen.test')
    client.force_login(user)
    return membre


@pytest.fixture
def classes(etab, annee, prof):
    """6e A (sa classe, Mathématiques) et 5e B (classe d'un collègue)."""
    cycle = baker.make('parametres.Cycle', etablissement=etab, nom='Collège', ordre=1)
    sienne = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6e A', actif=True)
    autre = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='5e B', actif=True)
    baker.make('pedagogie.Enseignement', classe=sienne, annee_scolaire=annee, personnel=prof,
               matiere=baker.make('pedagogie.Matiere', nom='Mathématiques', code='MATH'))
    baker.make('pedagogie.Enseignement', classe=autre, annee_scolaire=annee,
               personnel=baker.make('personnel.MembrePersonnel', etablissement=etab, email='collegue@yelen.test'),
               matiere=baker.make('pedagogie.Matiere', nom='Histoire', code='HIST'))
    return sienne, autre


def _html(response):
    return response.content.decode()


# ── Choix de la classe ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_classe_select_enseignant_ne_voit_que_ses_classes(client, classes):
    html = _html(client.get(reverse('presences:classe_select')))

    assert '6e A' in html and '5e B' not in html
    assert "Vos classes de l'année" in html or escape("Vos classes de l'année") in html


@pytest.mark.django_db
def test_classe_select_direction_voit_toutes_les_classes(client, etab, classes):
    client.force_login(baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False))

    html = _html(client.get(reverse('presences:classe_select')))

    assert '6e A' in html and '5e B' in html and 'Vos classes' not in html


@pytest.mark.django_db
def test_enseignement_inactif_ou_d_une_autre_annee_ne_compte_pas(client, etab, annee, prof, classes):
    sienne, autre = classes
    ancienne = baker.make('parametres.Classe', etablissement=etab, cycle=sienne.cycle, nom='4e C', actif=True)
    baker.make('pedagogie.Enseignement', classe=ancienne, personnel=prof,
               annee_scolaire=baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=False))
    baker.make('pedagogie.Enseignement', classe=autre, annee_scolaire=annee, personnel=prof, est_actif=False)

    html = _html(client.get(reverse('presences:classe_select')))

    assert '6e A' in html and '4e C' not in html and '5e B' not in html


@pytest.mark.django_db
def test_enseignant_sans_fiche_personnel_n_a_aucune_classe(client, etab, annee, classes):
    client.force_login(baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, email='inconnu@yelen.test',
                                  must_change_password=False))
    sienne, _ = classes

    html = _html(client.get(reverse('presences:classe_select')))
    response = client.get(reverse('presences:appel_create', args=[sienne.pk]), follow=True)

    assert '6e A' not in html and escape("Aucune classe ne vous est attribuée") in html
    assert escape("aucune fiche du personnel ne porte l'adresse de votre compte (inconnu@yelen.test)") in _html(response)


# ── Création de l'appel ────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_appel_classe_non_attribuee_refuse(client, classes):
    _, autre = classes

    response = client.get(reverse('presences:appel_create', args=[autre.pk]))
    post = client.post(reverse('presences:appel_create', args=[autre.pk]),
                       {'date': datetime.date.today().isoformat()}, follow=True)

    assert response.status_code == 302 and response.url == reverse('presences:classe_select')
    assert escape("Appel impossible : la classe 5e B ne vous est pas attribuée cette année") in _html(post)
    assert not Appel.objects.exists()


@pytest.mark.django_db
def test_appel_matieres_limitees_aux_siennes_dans_la_classe(client, etab, annee, prof, classes):
    sienne, _ = classes
    francais = baker.make('pedagogie.Matiere', nom='Français', code='FR')
    baker.make('pedagogie.Enseignement', classe=sienne, annee_scolaire=annee, matiere=francais,
               personnel=baker.make('personnel.MembrePersonnel', etablissement=etab, email='fr@yelen.test'))

    html = _html(client.get(reverse('presences:appel_create', args=[sienne.pk])))
    refus = client.post(reverse('presences:appel_create', args=[sienne.pk]),
                        {'date': datetime.date.today().isoformat(), 'matiere': str(francais.pk)}, follow=True)
    ok = client.post(reverse('presences:appel_create', args=[sienne.pk]), {'date': datetime.date.today().isoformat()})

    assert 'Mathématiques' in html and 'Français' not in html
    assert escape("cette matière ne vous est pas attribuée en 6e A") in _html(refus)
    assert Appel.objects.count() == 1 and ok.status_code == 302   # l'appel général de sa classe reste possible


# ── Saisie, pointage QR, historique ────────────────────────────────────────────

@pytest.mark.django_db
def test_saisie_et_pointage_qr_d_une_autre_classe_refuses(client, annee, classes):
    _, autre = classes
    appel = baker.make('presences.Appel', classe=autre, annee_scolaire=annee, est_clos=False)

    saisie = client.get(reverse('presences:appel_saisie', args=[appel.pk]))
    scanner = client.get(reverse('presences:qr_scanner', args=[appel.pk]))
    pointage = client.post(reverse('presences:api_qr_pointer', args=[appel.pk]),
                           json.dumps({'matricule': 'X'}), content_type='application/json')
    cartes = client.get(reverse('presences:cartes_qr_classe', args=[autre.pk]))

    assert saisie.status_code == 302 and saisie.url == reverse('presences:appel_list')
    assert scanner.status_code == 302 and scanner.url == reverse('presences:appel_list')
    assert pointage.status_code == 403 and "5e B ne vous est pas attribuée" in pointage.json()['message']
    assert cartes.status_code == 302 and cartes.url == reverse('presences:classe_select')


@pytest.mark.django_db
def test_saisie_differee_signale_le_refus(client, annee, classes):
    """La file hors réseau reçoit un refus explicite, jamais un faux succès."""
    _, autre = classes
    appel = baker.make('presences.Appel', classe=autre, annee_scolaire=annee, est_clos=False)

    response = client.post(reverse('presences:appel_saisie', args=[appel.pk]), {}, HTTP_X_SAISIE_DIFFEREE='1')

    assert response.status_code == 200 and response.json()['ok'] is False
    assert "5e B ne vous est pas attribuée" in response.json()['messages'][0]['texte']


@pytest.mark.django_db
def test_historique_csv_et_impression_limites_a_ses_classes(client, annee, classes):
    sienne, autre = classes
    baker.make('presences.Appel', classe=sienne, annee_scolaire=annee, date=datetime.date(2026, 10, 29))
    baker.make('presences.Appel', classe=autre, annee_scolaire=annee, date=datetime.date(2026, 10, 29))

    liste = _html(client.get(reverse('presences:appel_list')))
    csv = client.get(reverse('presences:appel_csv')).content.decode('utf-8-sig')
    impression = _html(client.get(reverse('presences:appel_print')))
    forcee = _html(client.get(reverse('presences:appel_list'), {'classe': str(autre.pk)}))

    assert '6e A' in liste and '5e B' not in liste
    assert '6e A' in csv and '5e B' not in csv
    assert '6e A' in impression and '5e B' not in impression
    assert 'Aucun appel' in forcee   # filtrer sur la classe d'un collègue ne révèle rien


@pytest.mark.django_db
def test_direction_voit_tous_les_appels(client, etab, annee, classes):
    sienne, autre = classes
    client.force_login(baker.make('accounts.User', role='CENSEUR', etablissement=etab, must_change_password=False))
    baker.make('presences.Appel', classe=sienne, annee_scolaire=annee, date=datetime.date(2026, 10, 29))
    appel = baker.make('presences.Appel', classe=autre, annee_scolaire=annee, date=datetime.date(2026, 10, 29), est_clos=False)

    liste = _html(client.get(reverse('presences:appel_list')))

    assert '6e A' in liste and '5e B' in liste
    assert client.get(reverse('presences:appel_saisie', args=[appel.pk])).status_code == 200
