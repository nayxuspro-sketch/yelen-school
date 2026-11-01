"""Boîte « Messages reçus » : SMS libres des parents à lire, lu / non lu, réponse par SMS, pastille du menu."""
from datetime import date

import pytest
from django.urls import reverse
from model_bakery import baker

from communication.models import IncomingSMSLog
from core.models import SmsSortant

pytestmark = pytest.mark.django_db


@pytest.fixture
def boite(client, settings):
    settings.SMS_ENABLED = True
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 7, 31))
    sixieme = baker.make('parametres.Classe', etablissement=etab, nom='6e A', actif=True)
    awa = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Awa', date_naissance=date(2013, 1, 1), photo='',
                     telephone_parent='70 11 22 33', tuteur_telephone='', telephone_urgence='')
    ali = baker.make('inscriptions.Eleve', nom='OUEDRAOGO', prenom='Ali', date_naissance=date(2015, 1, 1), photo='',
                     telephone_parent='', tuteur_telephone='+226 70 11 22 33', telephone_urgence='')
    baker.make('inscriptions.Inscription', eleve=awa, classe=sixieme, annee_scolaire=annee, statut='AFFECTE')
    libre = baker.make(IncomingSMSLog, sender_number='+22670112233', message_text='Je paierai lundi, merci',
                       command_type='INVALID', response_text='Yelen - Commande invalide.')
    inconnu = baker.make(IncomingSMSLog, sender_number='+22676000000', message_text='Bonjour', command_type='INVALID')
    commande = baker.make(IncomingSMSLog, sender_number='+22670112233', message_text='NOTE 01-2026-0001 T1',
                          command_type='NOTE', eleve=awa, is_authorized=True, processed_successfully=True)
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False,
                           first_name='Salif', last_name='KABORE')
    client.force_login(directeur)
    return {'libre': libre, 'inconnu': inconnu, 'commande': commande, 'directeur': directeur, 'awa': awa, 'ali': ali}


def test_liste_les_messages_libres_avec_la_famille_identifiee_par_le_numero(boite, client):
    html = client.get(reverse('communication:messages_recus')).content.decode()

    assert 'Je paierai lundi, merci' in html and 'Bonjour' in html
    assert 'NOTE 01-2026-0001 T1' not in html  # commande automatique : hors de la vue par défaut
    assert 'Famille de OUEDRAOGO AWA (6e A)' in html and 'Famille de OUEDRAOGO ALI' in html
    assert 'Numéro inconnu des fiches élèves' in html
    assert '2 non lus' in html and 'Tout marquer comme lu' in html
    assert 'name="texte"' in html and 'Marquer lu' in html


def test_affichage_en_cartes_sans_tableau_a_defilement(boite, client):
    """Chaque message occupe une carte pleine largeur : plus de tableau à défilement horizontal dont la
    colonne « Message » s'écrasait sur téléphone (un caractère par ligne)."""
    html = client.get(reverse('communication:messages_recus')).content.decode()

    assert html.count('class="boite-sms-item') == 2          # une carte par message de la page
    assert 'boite-sms-texte' in html and 'je paierai lundi' in html.lower()
    assert 'table-scroll' not in html and 'class="data-table' not in html
    assert 'Tout cocher sur cette page' in html and 'name="ids"' in html


def test_filtres_type_et_etat(boite, client):
    url = reverse('communication:messages_recus')
    IncomingSMSLog.objects.filter(pk=boite['libre'].pk).update(lu_le='2026-10-28T10:00:00Z', lu_par=boite['directeur'])

    commandes = client.get(url, {'type': 'commandes'}).content.decode()
    non_lus = client.get(url, {'type': 'tous', 'etat': 'non_lus'}).content.decode()
    lus = client.get(url, {'etat': 'lus'}).content.decode()

    assert 'NOTE 01-2026-0001 T1' in commandes and 'Je paierai lundi' not in commandes and 'OUEDRAOGO AWA' in commandes
    assert 'Bonjour' in non_lus and 'NOTE 01-2026-0001 T1' in non_lus and 'Je paierai lundi' not in non_lus
    assert 'Je paierai lundi' in lus and 'Bonjour' not in lus and '28/10 10:00 · Salif KABORE' in lus


def test_marquer_lu_puis_non_lu_et_tout_lu(boite, client):
    libre = boite['libre']
    suivant = reverse('communication:messages_recus') + '?type=libres&etat=non_lus'

    reponse = client.post(reverse('communication:messages_recus_marquer', args=[libre.pk]), {'etat': 'lu', 'next': suivant})
    libre.refresh_from_db()
    assert reponse.status_code == 302 and reponse.url == suivant
    assert libre.lu_le is not None and libre.lu_par == boite['directeur']

    client.post(reverse('communication:messages_recus_marquer', args=[libre.pk]), {'etat': 'non_lu'})
    libre.refresh_from_db()
    assert libre.lu_le is None and libre.lu_par is None

    reponse = client.post(reverse('communication:messages_recus_tout_lu'), {'next': 'https://evil.example/'}, follow=True)
    assert reponse.redirect_chain[-1][0] == reverse('communication:messages_recus')  # « next » externe ignoré
    assert '2 message(s) marqué(s) comme lu(s).' in reponse.content.decode()
    assert not IncomingSMSLog.objects.filter(command_type='INVALID', lu_le__isnull=True).exists()
    assert IncomingSMSLog.objects.get(pk=boite['commande'].pk).lu_le is None  # les commandes ne sont pas concernées


def test_repondre_par_sms_met_en_file_et_marque_lu(boite, client, mocker, django_capture_on_commit_callbacks):
    mocker.patch('core.tasks.threading.Thread')
    libre = boite['libre']

    with django_capture_on_commit_callbacks(execute=True):
        reponse = client.post(reverse('communication:messages_recus_repondre', args=[libre.pk]),
                              {'texte': '  Bien reçu,   merci. Le secrétariat  '}, follow=True)

    sms = SmsSortant.objects.get()
    assert (sms.numero, sms.message) == ('+22670112233', 'Bien reçu, merci. Le secrétariat')
    assert 'Réponse mise en file pour +22670112233.' in reponse.content.decode()
    libre.refresh_from_db()
    assert libre.lu_le is not None and libre.lu_par == boite['directeur']


def test_repondre_refuse_texte_vide_trop_long_ou_sms_desactives(boite, client, settings):
    url = reverse('communication:messages_recus_repondre', args=[boite['libre'].pk])

    vide = client.post(url, {'texte': '   '}, follow=True).content.decode()
    long = client.post(url, {'texte': 'x' * 161}, follow=True).content.decode()
    settings.SMS_ENABLED = False
    desactives = client.post(url, {'texte': 'Bonjour'}, follow=True).content.decode()

    assert 'entre 1 et 160 caractères' in vide and 'entre 1 et 160 caractères' in long
    assert 'Les SMS sont désactivés' in desactives
    assert not SmsSortant.objects.exists()
    assert IncomingSMSLog.objects.get(pk=boite['libre'].pk).lu_le is None


def test_pastille_du_menu_et_compteur(boite, client):
    accueil = client.get(reverse('communication:campagne_list')).content.decode()
    compteur = client.get(reverse('communication:messages_recus_compteur')).content.decode()

    assert 'hx-get="/communication/messages-recus/compteur/"' in accueil and 'Messages reçus' in accueil
    assert '>2</span>' in compteur
    IncomingSMSLog.objects.filter(command_type='INVALID').update(lu_le='2026-10-28T10:00:00Z')
    assert client.get(reverse('communication:messages_recus_compteur')).content.decode().strip() == ''


def test_le_simulateur_marque_ses_propres_messages_lus(boite, client, mocker):
    mocker.patch('core.tasks.envoyer_sms_async')

    client.post(reverse('communication:sms_direct_envoyer'), {'phone': '+22670112233', 'message': 'coucou'},
                HTTP_HX_REQUEST='true')

    simule = IncomingSMSLog.objects.get(message_text='coucou')
    assert simule.command_type == 'INVALID' and simule.lu_le is not None and simule.lu_par == boite['directeur']
    assert IncomingSMSLog.objects.filter(command_type='INVALID', lu_le__isnull=True).count() == 2  # les vrais restent à lire


def test_action_refusee_par_la_matrice_des_droits(boite, client):
    from parametres import droits
    from parametres.models import DroitAcces
    DroitAcces.objects.create(role='DIRECTEUR', module='communication', fonctionnalite='/communication/messages-recus/',
                              action='traiter', autorise=False)
    droits.invalider_cache()

    page = client.get(reverse('communication:messages_recus'))
    refus = client.post(reverse('communication:messages_recus_marquer', args=[boite['libre'].pk]), {'etat': 'lu'})

    assert page.status_code == 200 and 'Marquer lu' not in page.content.decode() and 'name="texte"' not in page.content.decode()
    assert refus.status_code == 302 and refus.url == '/'
    assert IncomingSMSLog.objects.get(pk=boite['libre'].pk).lu_le is None


def test_suppression_unitaire_selection_et_tous_les_lus(boite, client):
    from communication.sms_recus import traiter_sms_recu
    url = reverse('communication:messages_recus')
    IncomingSMSLog.objects.filter(pk=boite['libre'].pk).update(message_id='text:abc')

    retour = client.post(reverse('communication:messages_recus_supprimer', args=[boite['libre'].pk]), {'next': f'{url}?type=tous'})
    html = client.get(url).content.decode()
    ligne = IncomingSMSLog.objects.get(pk=boite['libre'].pk)
    journal, cree = traiter_sms_recu('+22670112233', 'Je paierai lundi, merci', message_id='text:abc')

    assert retour.status_code == 302 and retour.url == f'{url}?type=tous'
    assert 'Je paierai lundi' not in html and 'Bonjour' in html and '1 non lu' in html
    assert ligne.is_active is False and (journal.pk, cree) == (ligne.pk, False)   # la relève ne le retraite pas

    sans_choix = client.post(reverse('communication:messages_recus_supprimer_selection'), {}, follow=True)
    assert 'Cochez au moins un message' in sans_choix.content.decode()
    assert IncomingSMSLog.objects.filter(is_active=True).count() == 2

    client.post(reverse('communication:messages_recus_supprimer_selection'), {'ids': [str(boite['inconnu'].pk)]})
    assert IncomingSMSLog.objects.get(pk=boite['inconnu'].pk).is_active is False

    IncomingSMSLog.objects.filter(pk=boite['commande'].pk).update(lu_le='2026-10-28T10:00:00Z')
    baker.make(IncomingSMSLog, sender_number='+22676000001', message_text='Lu mais libre', command_type='INVALID',
               lu_le='2026-10-28T11:00:00Z')
    client.post(reverse('communication:messages_recus_supprimer_selection'), {'portee': 'lus', 'type': 'commandes'})
    assert IncomingSMSLog.objects.get(pk=boite['commande'].pk).is_active is False
    assert IncomingSMSLog.objects.get(message_text='Lu mais libre').is_active is True   # autre vue : intacte


def test_suppression_refusee_par_la_matrice_des_droits(boite, client):
    from parametres import droits
    from parametres.models import DroitAcces
    DroitAcces.objects.create(role='DIRECTEUR', module='communication', fonctionnalite='/communication/messages-recus/',
                              action='supprimer', autorise=False)
    droits.invalider_cache()

    page = client.get(reverse('communication:messages_recus')).content.decode()
    refus = client.post(reverse('communication:messages_recus_supprimer', args=[boite['libre'].pk]))

    assert 'Supprimer la sélection' not in page and 'name="ids"' not in page and 'Supprimer ce message' not in page
    assert refus.status_code == 302 and refus.url == '/' and IncomingSMSLog.objects.get(pk=boite['libre'].pk).is_active
