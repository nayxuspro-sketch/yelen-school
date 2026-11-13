"""Prêts d'ouvrages (5.50.0) : échéance de retour, retards, relance des familles (portail, push, SMS), relance
automatique quotidienne via le déclencheur ``sms_auto`` et affichage dans la vie scolaire du portail."""
from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.models import Notification, SmsSortant
from manuels.models import AttributionManuel

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client, settings):
    settings.SMS_ENABLED = False
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    cycle = baker.make('parametres.Cycle', etablissement=etab, code='POST', nom='Post-primaire')
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=cycle, nom='6e A', actif=True)
    eleve = baker.make('inscriptions.Eleve', nom='KABORE', prenom='Issa', photo='', telephone_parent='70 00 00 01')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee)
    parent = baker.make('accounts.User', etablissement=etab, role='PARENT', must_change_password=False)
    parent.eleves_lies.add(eleve)
    compte_eleve = baker.make('accounts.User', etablissement=etab, role='ELEVE', must_change_password=False)
    compte_eleve.eleves_lies.add(eleve)
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    manuel = baker.make('manuels.ManuelScolaire', etablissement=etab, titre='Mathématiques 6e', cycle=cycle)
    exemplaire = baker.make('manuels.ExemplaireManuel', manuel=manuel)
    client.force_login(directeur)
    return {'etab': etab, 'annee': annee, 'classe': classe, 'eleve': eleve, 'inscription': inscription,
            'parent': parent, 'compte_eleve': compte_eleve, 'directeur': directeur,
            'manuel': manuel, 'exemplaire': exemplaire, 'client': client}


def _pret(ecole, jours_echeance, exemplaire=None):
    """Prêt dont le retour était prévu il y a ``jours_echeance`` jours (négatif : à venir)."""
    return baker.make(
        'manuels.AttributionManuel',
        exemplaire=exemplaire or baker.make('manuels.ExemplaireManuel', manuel=ecole['manuel']),
        inscription=ecole['inscription'],
        date_attribution=timezone.localdate() - timedelta(days=30),
        date_retour_prevue=timezone.localdate() - timedelta(days=jours_echeance),
    )


def test_retard_calcule_seulement_pour_un_pret_non_rendu(ecole):
    en_retard = _pret(ecole, 5)
    assert en_retard.est_en_retard and en_retard.jours_de_retard == 5
    a_venir = _pret(ecole, -3)
    assert not a_venir.est_en_retard and a_venir.jours_de_retard == 0
    sans_echeance = baker.make('manuels.AttributionManuel',
                               exemplaire=baker.make('manuels.ExemplaireManuel', manuel=ecole['manuel']),
                               inscription=ecole['inscription'], date_attribution=timezone.localdate())
    assert not sans_echeance.est_en_retard and sans_echeance.jours_de_retard == 0
    en_retard.date_retour = timezone.localdate()
    en_retard.save()
    assert not en_retard.est_en_retard, 'un ouvrage rendu n’est plus en retard'


def test_page_des_prets_filtre_retards_et_echeances(ecole):
    _pret(ecole, 4)
    _pret(ecole, -2)
    page = ecole['client'].get(reverse('manuels:prets_en_cours'))
    assert page.status_code == 200
    assert (page.context['nb_total'], page.context['nb_retards'], page.context['nb_echeances']) == (2, 1, 1)
    assert 'Mathématiques 6e' in page.content.decode()
    retards = ecole['client'].get(reverse('manuels:prets_en_cours') + '?etat=retard')
    assert retards.context['nb_total'] == 2 and len(retards.context['prets']) == 1
    assert retards.context['prets'][0].retard_jours == 4
    echeances = ecole['client'].get(reverse('manuels:prets_en_cours') + '?etat=echeance')
    assert len(echeances.context['prets']) == 1 and not echeances.context['prets'][0].en_retard


def test_relance_previant_portail_et_sms_puis_n_est_pas_repete(ecole, settings, mocker, django_capture_on_commit_callbacks):
    settings.SMS_ENABLED = True
    envoi = mocker.patch('core.tasks.envoyer_sms_async', return_value=object())
    pret = _pret(ecole, 3)

    with django_capture_on_commit_callbacks(execute=True):
        reponse = ecole['client'].post(reverse('manuels:relancer_prets'), {'prets': [pret.pk]}, follow=True)
    assert '1 famille relancée' in reponse.content.decode()

    avis = Notification.objects.get(destinataire=ecole['parent'])
    assert avis.titre == 'Prêt à rendre — Mathématiques 6e'
    assert avis.lien == '/portail/parent/vie-scolaire/' and '3 jours de retard' in avis.message
    assert Notification.objects.filter(destinataire=ecole['compte_eleve'],
                                       lien='/portail/eleve/vie-scolaire/').exists()
    message = envoi.call_args.args[1]
    assert 'Mathématiques 6e' in message and 'KABORE ISSA' in message and '70 00 00 01' in envoi.call_args.args[0]

    pret.refresh_from_db()
    assert pret.derniere_relance_le is not None


def test_relance_automatique_quotidienne_une_fois_par_intervalle(ecole, settings, mocker):
    settings.SMS_ENABLED = True
    mocker.patch('core.tasks.envoyer_sms_async', return_value=object())
    declencheur = baker.make('parametres.DeclencheurSMS', etablissement=ecole['etab'],
                             type_declencheur='PRETS_RETARD', actif=True, jours_avant=3)
    pret = _pret(ecole, 6)
    _pret(ecole, -10)                      # échéance à venir : jamais relancé

    call_command('sms_auto', type='PRETS_RETARD', stdout=StringIO())
    pret.refresh_from_db()
    assert pret.derniere_relance_le is not None
    assert Notification.objects.filter(destinataire=ecole['parent']).count() == 1

    # Seconde exécution le même jour : le déclencheur ne repart pas
    Notification.objects.all().delete()
    call_command('sms_auto', type='PRETS_RETARD', stdout=StringIO())
    assert not Notification.objects.exists()

    # Le lendemain (déclencheur réarmé), le prêt relancé il y a un jour est laissé tranquille
    declencheur.last_run = None
    declencheur.save(update_fields=['last_run'])
    pret.derniere_relance_le = timezone.now() - timedelta(days=1)
    pret.save(update_fields=['derniere_relance_le'])
    call_command('sms_auto', type='PRETS_RETARD', stdout=StringIO())
    assert not Notification.objects.exists()
    # Passé l'intervalle de trois jours, la relance repart
    declencheur.last_run = None
    declencheur.save(update_fields=['last_run'])
    pret.derniere_relance_le = timezone.now() - timedelta(days=4)
    pret.save(update_fields=['derniere_relance_le'])
    call_command('sms_auto', type='PRETS_RETARD', stdout=StringIO())
    assert Notification.objects.filter(destinataire=ecole['parent']).exists()


def test_liste_des_retards_en_pdf(ecole):
    _pret(ecole, 9)
    reponse = ecole['client'].get(reverse('manuels:prets_retards_pdf'))
    assert reponse.status_code == 200 and reponse['Content-Type'] == 'application/pdf'
    assert reponse.content[:4] == b'%PDF'


def test_vie_scolaire_du_portail_affiche_les_ouvrages_a_rendre(ecole):
    _pret(ecole, 2)
    ecole['client'].force_login(ecole['parent'])
    html = ecole['client'].get(reverse('core:portail_parent_vie_scolaire')).content.decode()
    assert 'Ouvrages à rendre' in html and 'Mathématiques 6e' in html and '2 jours de retard' in html
    ecole['client'].force_login(ecole['compte_eleve'])
    assert 'Ouvrages à rendre' in ecole['client'].get(
        reverse('core:portail_eleve_vie_scolaire')).content.decode()
    # Le prêt rendu disparaît de la page
    AttributionManuel.objects.update(date_retour=timezone.localdate())
    ecole['client'].force_login(ecole['parent'])
    assert 'Ouvrages à rendre' not in ecole['client'].get(
        reverse('core:portail_parent_vie_scolaire')).content.decode()


def test_relance_reservee_aux_roles_autorises(ecole):
    ecole['client'].force_login(baker.make('accounts.User', etablissement=ecole['etab'], role='COMPTABLE',
                                           must_change_password=False))
    reponse = ecole['client'].post(reverse('manuels:relancer_prets'), {'prets': []})
    assert reponse.status_code == 302, 'sans droit « relancer », la requête est renvoyée à l’accueil'


def test_sms_de_relance_tient_en_un_message(ecole, settings, mocker):
    settings.SMS_ENABLED = True
    from core.notifications import notifier_pret_retard
    from parametres.models import ModeleMessage
    envoi = mocker.patch('core.tasks.envoyer_sms_async', return_value=object())
    ModeleMessage.objects.filter(etablissement=ecole['etab'], type='PRET').delete()
    assert notifier_pret_retard(_pret(ecole, 1)) is True
    texte = envoi.call_args.args[1]
    assert 'devait être rendu' in texte and '{ouvrage}' not in texte and len(texte) <= 160
    assert SmsSortant.objects.count() == 0, 'SMS mis en file, pas encore consommé'
