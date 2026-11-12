"""Lot J — sanction disciplinaire : case « Prévenir le parent » à la saisie (notification du portail parent + SMS
« Sanction disciplinaire »), sanctions visibles sur le portail parent."""
from datetime import date, timedelta
from html import unescape

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.models import Notification
from viescolaire.models import SanctionDisciplinaire

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    aujourdhui = timezone.localdate()
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=aujourdhui - timedelta(days=30), date_fin=aujourdhui + timedelta(days=240))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='4e B', actif=True)
    eleve = baker.make('inscriptions.Eleve', nom='KABORE', prenom='Issa', date_naissance=date(2012, 4, 2), photo='',
                       telephone_parent='70 00 00 01')
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut='ACTIF')
    parent = baker.make('accounts.User', etablissement=etab, role='PARENT', must_change_password=False)
    parent.eleves_lies.add(eleve)
    type_sanction = baker.make('parametres.TypeSanction', libelle='Avertissement', code='AVERT')
    user = baker.make(
        'accounts.User', etablissement=etab, role='DIRECTEUR', est_tous_cycles=True, must_change_password=False,
    )
    client.force_login(user)
    return {'etab': etab, 'annee': annee, 'classe': classe, 'eleve': eleve, 'inscription': inscription, 'parent': parent,
            'type_sanction': type_sanction, 'user': user, 'client': client}


def _donnees(ecole, **extra):
    return {'inscription': str(ecole['inscription'].pk), 'type_sanction': str(ecole['type_sanction'].pk),
            'date_sanction': '2026-10-20', 'motif': 'Bavardages répétés', 'statut': 'CONFIRME', **extra}


def test_la_case_prevenir_le_parent_est_cochee_par_defaut(ecole):
    html = ecole['client'].get(reverse('viescolaire:sanction_create')).content.decode()
    assert 'name="prevenir_parents"' in html and 'Prévenir le parent' in html
    assert 'name="prevenir_parents" class="dash-checkbox" checked' in html


def test_la_saisie_avec_la_case_cochee_notifie_le_parent_et_envoie_le_sms(ecole, settings, mocker,
                                                                           django_capture_on_commit_callbacks):
    settings.SMS_ENABLED = True
    mocker.patch('core.tasks.threading.Thread')
    from core.models import SmsSortant
    with django_capture_on_commit_callbacks(execute=True):
        reponse = ecole['client'].post(reverse('viescolaire:sanction_create'), _donnees(ecole, prevenir_parents='on'), follow=True)
    assert 'Parent informé' in unescape(reponse.content.decode())
    sanction = SanctionDisciplinaire.objects.get()
    assert sanction.parents_notifies_le is not None
    notification = Notification.objects.get(destinataire=ecole['parent'])
    assert notification.type == 'SANCTION' and notification.titre == 'Sanction disciplinaire — 20/10/2026'
    assert 'KABORE ISSA a reçu la sanction « Avertissement » le 20/10/2026. Motif : Bavardages répétés' == notification.message
    assert notification.lien == '/portail/parent/vie-scolaire/'
    sms = SmsSortant.objects.get(numero='70 00 00 01')
    assert sms.message == ('Bonjour, votre enfant KABORE ISSA (4e B) a reçu une sanction le 20/10/2026 : Avertissement. '
                           'Motif : Bavardages répétés. — LE SAVOIR')


def test_sans_la_case_rien_n_est_envoye(ecole, settings, mocker):
    settings.SMS_ENABLED = True
    envoi = mocker.patch('core.tasks.envoyer_sms_async')
    reponse = ecole['client'].post(reverse('viescolaire:sanction_create'), _donnees(ecole), follow=True)
    assert reponse.status_code == 200
    sanction = SanctionDisciplinaire.objects.get()
    assert sanction.parents_notifies_le is None and not Notification.objects.exists() and envoi.call_count == 0


def test_le_modele_sms_sanction_est_personnalisable(ecole, settings, mocker):
    from parametres.models import ModeleMessage
    ModeleMessage.objects.create(etablissement=ecole['etab'], type='SANCTION', contenu_sms='{nom_eleve} : {sanction} ({date}).', actif=True)
    settings.SMS_ENABLED = True
    envoi = mocker.patch('core.tasks.envoyer_sms_async')
    ecole['client'].post(reverse('viescolaire:sanction_create'), _donnees(ecole, prevenir_parents='on'))
    assert envoi.call_args.args == ('70 00 00 01', 'KABORE ISSA : Avertissement (20/10/2026).')
    assert 'SANCTION' in dict(ModeleMessage.TypeChoices.choices)


def test_sans_compte_parent_ni_numero_l_utilisateur_est_averti(ecole, settings):
    settings.SMS_ENABLED = True
    ecole['parent'].eleves_lies.clear()
    type(ecole['eleve']).objects.filter(pk=ecole['eleve'].pk).update(telephone_parent='', tuteur_telephone='', telephone_urgence='')
    reponse = ecole['client'].post(reverse('viescolaire:sanction_create'), _donnees(ecole, prevenir_parents='on'), follow=True)
    assert 'Parent non informé' in unescape(reponse.content.decode())
    assert SanctionDisciplinaire.objects.get().parents_notifies_le is None


def test_la_liste_des_sanctions_indique_le_parent_informe(ecole):
    baker.make(SanctionDisciplinaire, inscription=ecole['inscription'], type_sanction=ecole['type_sanction'],
               date_sanction=date(2026, 10, 20), motif='Retards', parents_notifies_le=timezone.now())
    html = ecole['client'].get(reverse('viescolaire:sanction_list')).content.decode()
    assert 'Parent informé (portail / SMS)' in html


def test_le_portail_parent_affiche_les_sanctions_sauf_les_annulees(client, ecole):
    baker.make(SanctionDisciplinaire, inscription=ecole['inscription'], type_sanction=ecole['type_sanction'],
               date_sanction=date(2026, 10, 20), motif='Bavardages répétés', statut='CONFIRME', duree_jours=0,
               parents_convoques=True, date_convocation=date(2026, 10, 22))
    baker.make(SanctionDisciplinaire, inscription=ecole['inscription'], type_sanction=ecole['type_sanction'],
               date_sanction=date(2026, 10, 21), motif='Erreur de saisie', statut='ANNULE')
    client.force_login(ecole['parent'])
    reponse = client.get(reverse('core:portail_parent_vie_scolaire'))
    assert reponse.status_code == 200
    sanctions = reponse.context['enfants'][0]['sanctions']
    assert [s.motif for s in sanctions] == ['Bavardages répétés']
    html = unescape(reponse.content.decode())
    assert 'Sanctions disciplinaires' in html and 'Avertissement' in html and 'Parents convoqués le 22/10/2026' in html
    assert 'Erreur de saisie' not in html


def test_aucune_notification_automatique_a_la_creation_hors_ecran(ecole):
    """L'ancien signal post_save notifiait chaque sanction, même importée : c'est désormais la case à la saisie qui décide."""
    baker.make(SanctionDisciplinaire, inscription=ecole['inscription'], type_sanction=ecole['type_sanction'],
               date_sanction=date(2026, 10, 20), motif='Import')
    assert not Notification.objects.exists()
