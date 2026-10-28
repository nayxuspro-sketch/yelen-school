"""Lot I — I1 seuil d'absences : alertes à la clôture de l'appel, notification direction, SMS parent, page de suivi."""
import datetime as dt

import pytest
from django.urls import reverse
from model_bakery import baker

from core.models import Notification, SmsSortant
from presences.alertes import verifier_seuils
from presences.models import AlerteAbsences, Presence, SeuilAbsences

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    directeur = baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False)
    baker.make('accounts.User', role='CENSEUR', etablissement=etab, must_change_password=False)
    baker.make('accounts.User', role='ENSEIGNANT', etablissement=etab, must_change_password=False)
    client.force_login(directeur)
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=dt.date(2026, 10, 1), date_fin=dt.date(2027, 6, 30))
    baker.make('pedagogie.Trimestre', annee_scolaire=annee, nom='Trimestre 1', numero=1,
               date_debut=dt.date(2026, 10, 1), date_fin=dt.date(2026, 12, 20))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6ème A', cycle=baker.make('parametres.Cycle', etablissement=etab))
    eleve = baker.make('inscriptions.Eleve', nom='KABORE', prenom='Issa', telephone_parent='70 00 00 01', photo='')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
    return {'etab': etab, 'directeur': directeur, 'annee': annee, 'classe': classe, 'inscription': inscription}


def _absence(ecole, jour):
    appel = baker.make('presences.Appel', classe=ecole['classe'], annee_scolaire=ecole['annee'], date=jour, est_clos=True)
    baker.make('presences.Presence', appel=appel, inscription=ecole['inscription'], statut=Presence.StatutChoices.ABSENT)
    return appel


def test_alerte_au_seuil_puis_aux_paliers_suivants(ecole):
    reglage = SeuilAbsences.pour(ecole['etab'])
    reglage.seuil = 2
    reglage.sms_parent = False
    reglage.save()
    assert verifier_seuils(_absence(ecole, dt.date(2026, 10, 5))) == []
    creees = verifier_seuils(_absence(ecole, dt.date(2026, 10, 6)))
    assert len(creees) == 1
    alerte = creees[0]
    assert (alerte.palier, alerte.nb_absences, alerte.seuil, alerte.periode) == (1, 2, 2, 'Trimestre 1')
    # la direction (directeur + censeur) est notifiée, pas l'enseignant
    notifs = Notification.objects.filter(type='ABSENCE')
    assert notifs.count() == 2 and set(notifs.values_list('destinataire__role', flat=True)) == {'DIRECTEUR', 'CENSEUR'}
    assert 'KABORE ISSA' in notifs.first().titre and notifs.first().lien == reverse('presences:alertes_absences')
    # 3e absence : pas de nouvelle alerte ; 4e : palier 2
    assert verifier_seuils(_absence(ecole, dt.date(2026, 10, 7))) == []
    assert verifier_seuils(_absence(ecole, dt.date(2026, 10, 8)))[0].palier == 2
    # réexécution sur le dernier appel : rien en double
    assert verifier_seuils(Presence.objects.latest('created_at').appel) == [] and AlerteAbsences.objects.count() == 2


def test_periode_annee_et_absences_excusees(ecole):
    reglage = SeuilAbsences.pour(ecole['etab'])
    reglage.seuil = 2
    reglage.par_periode = False
    reglage.sms_parent = False
    reglage.save()
    _absence(ecole, dt.date(2026, 10, 5))
    # une absence excusée (justificatif accepté) ne compte pas
    appel = baker.make('presences.Appel', classe=ecole['classe'], annee_scolaire=ecole['annee'], date=dt.date(2026, 10, 6), est_clos=True)
    baker.make('presences.Presence', appel=appel, inscription=ecole['inscription'], statut=Presence.StatutChoices.EXCUSE)
    assert verifier_seuils(appel) == []
    alerte = verifier_seuils(_absence(ecole, dt.date(2027, 1, 15)))[0]   # 2e absence, hors trimestre 1 : compte annuel
    assert alerte.periode == 'Année 2026-2027' and alerte.nb_absences == 2
    reglage.actif = False
    reglage.save()
    assert verifier_seuils(_absence(ecole, dt.date(2027, 1, 16))) == [] and AlerteAbsences.objects.count() == 1


def test_sms_parent_avec_le_modele(ecole, settings, mocker, django_capture_on_commit_callbacks):
    settings.SMS_ENABLED = True
    mocker.patch('core.tasks.threading.Thread')
    reglage = SeuilAbsences.pour(ecole['etab'])
    reglage.seuil = 1
    reglage.save()
    with django_capture_on_commit_callbacks(execute=True):
        alerte = verifier_seuils(_absence(ecole, dt.date(2026, 10, 5)))[0]
    assert alerte.sms_envoye
    sms = SmsSortant.objects.get(numero='70 00 00 01')
    assert 'KABORE ISSA (6ème A) totalise 1 absences non justifiées (Trimestre 1)' in sms.message and 'LE SAVOIR' in sms.message


def test_cloture_de_l_appel_declenche_la_verification(client, ecole):
    reglage = SeuilAbsences.pour(ecole['etab'])
    reglage.seuil = 1
    reglage.sms_parent = False
    reglage.save()
    appel = baker.make('presences.Appel', classe=ecole['classe'], annee_scolaire=ecole['annee'], date=dt.date(2026, 10, 5), est_clos=False)
    presence = baker.make('presences.Presence', appel=appel, inscription=ecole['inscription'], statut=Presence.StatutChoices.PRESENT)
    reponse = client.post(reverse('presences:appel_saisie', args=[appel.pk]),
                          {f'statut_{presence.pk}': 'ABSENT', 'clore': '1'}, follow=True)
    assert AlerteAbsences.objects.count() == 1
    from html import unescape
    assert "Seuil d'absences atteint pour 1 élève(s) : KABORE ISSA" in unescape(reponse.content.decode())


def test_page_reglage_et_traitement(client, ecole):
    reglage = SeuilAbsences.pour(ecole['etab'])
    reglage.seuil = 1
    reglage.sms_parent = False
    reglage.save()
    alerte = verifier_seuils(_absence(ecole, dt.date(2026, 10, 5)))[0]
    html = client.get(reverse('presences:alertes_absences')).content.decode()
    assert 'KABORE ISSA' in html and 'À traiter' in html and 'name="seuil"' in html
    reponse = client.post(reverse('presences:alertes_absences_config'),
                          {'seuil': '4', 'actif': 'on', 'par_periode': 'on'}, follow=True)
    reglage.refresh_from_db()
    assert (reglage.seuil, reglage.actif, reglage.par_periode, reglage.sms_parent) == (4, True, True, False)
    assert 'Seuil enregistré : 4 absences' in reponse.content.decode()
    client.post(reverse('presences:alertes_absences_config'), {'seuil': '0'})
    reglage.refresh_from_db()
    assert reglage.seuil == 4
    client.post(reverse('presences:alerte_absences_traiter', args=[alerte.pk]), {'observation': 'Parent convoqué le 12/10'})
    alerte.refresh_from_db()
    assert alerte.traitee and alerte.traitee_par == ecole['directeur'] and alerte.observation == 'Parent convoqué le 12/10'
    html = client.get(reverse('presences:alertes_absences')).content.decode()
    assert 'Aucune alerte à traiter' in html
    assert 'Parent convoqué le 12/10' in client.get(reverse('presences:alertes_absences'), {'toutes': '1'}).content.decode()


def test_alerte_d_un_autre_etablissement_inaccessible(client, ecole):
    autre = baker.make('etablissements.Etablissement')
    inscription = baker.make('inscriptions.Inscription', classe=baker.make('parametres.Classe', etablissement=autre),
                             eleve=baker.make('inscriptions.Eleve', photo=''))
    alerte = AlerteAbsences.objects.create(inscription=inscription, periode='X', palier=1, seuil=1, nb_absences=1, date_appel=dt.date(2026, 10, 5))
    assert client.post(reverse('presences:alerte_absences_traiter', args=[alerte.pk])).status_code == 404
    assert 'X' not in [a.periode for a in client.get(reverse('presences:alertes_absences')).context['alertes']]
