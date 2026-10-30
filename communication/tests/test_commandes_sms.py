"""Commandes SMS définies par l'école (communication/commandes.py + pages Communication → Commandes SMS) :
reconnaissance du mot-clé et des alias, réponse générale ou propre à un élève avec variables, autorisation du
parent, AIDE dynamique, priorité des commandes intégrées, validation du formulaire, pages et droits."""
from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from communication import commandes
from communication.models import CommandeSms, IncomingSMSLog
from communication.sms_recus import traiter_sms_recu

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(settings):
    settings.SMS_ENABLED = True
    etab = baker.make('etablissements.Etablissement', nom='Lycée Le Savoir')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 7, 31))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6e A', actif=True)
    awa = baker.make('inscriptions.Eleve', matricule='01-2026-0001', nom='OUEDRAOGO', prenom='Awa', photo='',
                     date_naissance=date(2013, 1, 1), telephone_parent='+22670112233', tuteur_telephone='', telephone_urgence='')
    inscription = baker.make('inscriptions.Inscription', eleve=awa, classe=classe, annee_scolaire=annee, statut='AFFECTE')
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1, nom='1er Trimestre')
    baker.make('pedagogie.MoyenneGenerale', inscription=inscription, trimestre=trimestre, moyenne=14.5, rang=3)
    return {'etab': etab, 'annee': annee, 'classe': classe, 'awa': awa, 'inscription': inscription}


def commande(etab, mot, reponse, portee='ECOLE', **extra):
    return CommandeSms.objects.create(etablissement=etab, mot_cle=mot, reponse=reponse, portee=portee, **extra)


@patch('core.tasks.envoyer_sms_async')
def test_commande_generale_repond_avec_ses_variables_et_ses_alias(envoyer, ecole):
    horaires = commande(ecole['etab'], 'HORAIRES', "{etablissement} - Cours de 7h a 12h. Nous sommes le {date} ({annee}).",
                        alias='HORAIRE, HEURES')

    journal, cree = traiter_sms_recu('+22676000000', '  horaire ')

    attendu = f"Lycée Le Savoir - Cours de 7h a 12h. Nous sommes le {timezone.localdate():%d/%m/%Y} (2026-2027)."
    assert cree and (journal.command_type, journal.commande, journal.processed_successfully) == ('PERSO', horaires, True)
    assert journal.response_text == attendu
    envoyer.assert_called_once_with('+22676000000', attendu)

    horaires.actif = False
    horaires.save()
    journal, _ = traiter_sms_recu('+22676000000', 'HORAIRES')
    assert journal.command_type == 'INVALID' and 'bien ete recu' in journal.response_text   # message libre, pas une commande


@patch('core.tasks.envoyer_sms_async')
def test_commande_eleve_reservee_au_parent_avec_variables_de_l_eleve(envoyer, ecole, mocker):
    mocker.patch('finances.views._calcul_situation_financiere',
                 return_value={'total_du': 150000, 'total_paye': 50000, 'reste_a_payer': 100000})
    frais = commande(ecole['etab'], 'FRAIS', "{eleve} ({classe}): du {total_du}, paye {total_paye}, reste {reste} F. "
                                             "Moy {moyenne} rang {rang} ({trimestre}), {absences} abs.", portee='ELEVE')

    parent, _ = traiter_sms_recu('+226 70 11 22 33', 'frais 01-2026-0001')
    assert parent.command_type == 'PERSO' and parent.commande == frais and parent.eleve == ecole['awa']
    assert parent.response_text == "Awa OUEDRAOGO (6e A): du 150 000, paye 50 000, reste 100 000 F. Moy 14,50 rang 3/1 (1er Trimestre), 0 abs."
    assert parent.is_authorized and parent.processed_successfully

    inconnu, _ = traiter_sms_recu('+22676000000', 'FRAIS 01-2026-0001')
    assert inconnu.command_type == 'PERSO' and not inconnu.is_authorized and 'pas autorise' in inconnu.response_text

    sans_matricule, _ = traiter_sms_recu('+22670112233', 'FRAIS')
    assert sans_matricule.command_type == 'PERSO' and sans_matricule.error_message == 'Matricule manquant.'
    assert sans_matricule.response_text == "Yelen - Envoyez FRAIS suivi du matricule de l'eleve (ex: FRAIS BF-2026-0001)."

    introuvable, _ = traiter_sms_recu('+22670112233', 'FRAIS 99-9999-9999')
    assert 'introuvable' in introuvable.response_text
    assert envoyer.call_count == 4


def test_aide_liste_les_commandes_de_l_ecole_dans_la_limite_d_un_sms(ecole):
    assert commandes.texte_aide() == 'Yelen - Commandes: NOTE <matricule> [T1], SOLDE <matricule>, ABS <matricule>.'

    commande(ecole['etab'], 'HORAIRES', 'x')
    commande(ecole['etab'], 'FRAIS', 'x', portee='ELEVE')
    commande(ecole['etab'], 'INACTIVE', 'x', actif=False)
    assert commandes.texte_aide() == ('Yelen - Commandes: NOTE <matricule> [T1], SOLDE <matricule>, ABS <matricule>, '
                                      'FRAIS <matricule>, HORAIRES.')

    for i in range(8):
        commande(ecole['etab'], f'MOTCLETRESLONGNUM{i:03d}', 'x')   # 20 caractères : maximum du champ
    aide = commandes.texte_aide()
    assert len(aide) <= CommandeSms.LONGUEUR_REPONSE and aide.endswith('...') and 'FRAIS <matricule>' in aide


@patch('core.tasks.envoyer_sms_async')
def test_les_commandes_integrees_gardent_la_priorite(envoyer, ecole):
    commande(ecole['etab'], 'PIRATE', 'Jamais envoye', alias='ABS')   # créé hors formulaire : le mot réservé ne détourne rien

    journal, _ = traiter_sms_recu('+22670112233', 'ABS 01-2026-0001')

    assert journal.command_type == 'ABS' and journal.commande is None and 'absence' in journal.response_text


@pytest.fixture
def directeur(client, ecole):
    user = baker.make('accounts.User', etablissement=ecole['etab'], role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return user


def test_formulaire_valide_les_mots_cles_et_les_variables(client, ecole, directeur):
    url = reverse('communication:commande_sms_nouvelle')
    commande(ecole['etab'], 'HORAIRES', 'x', alias='HEURES')

    def erreurs(**champs):
        page = client.post(url, {'portee': 'ECOLE', 'reponse': 'Bonjour', **champs})
        assert page.status_code == 400
        return page.content.decode()

    assert 'est une commande intégrée de YELEN' in erreurs(mot_cle='note')
    assert 'commence par une lettre' in erreurs(mot_cle='1A') and 'commence par une lettre' in erreurs(mot_cle='A')
    assert 'déjà utilisé par la commande HORAIRES' in erreurs(mot_cle='CONTACT', alias='heures')
    assert 'Un même mot apparaît deux fois' in erreurs(mot_cle='CONTACT', alias='CONTACT')
    assert 'Variable(s) inconnue(s) : {reste}' in erreurs(mot_cle='CONTACT', reponse='Reste {reste}') \
        and 'demandent la portée' in erreurs(mot_cle='CONTACT', reponse='Reste {reste}')
    assert 'Variable(s) inconnue(s) : {truc}.' in erreurs(mot_cle='CONTACT', reponse='{truc}')
    assert 'dépasse 160 caractères (161)' in erreurs(mot_cle='CONTACT', reponse='x' * 161)
    assert 'Rédigez la réponse' in erreurs(mot_cle='CONTACT', reponse='  ')

    ok = client.post(url, {'mot_cle': ' contact ', 'alias': 'tel,, telephone ', 'portee': 'ELEVE', 'actif': '1',
                           'description': 'Numéros utiles', 'reponse': "{etablissement}: secretariat 70 00 00 00 pour {eleve}"})
    assert ok.status_code == 302 and ok.url == reverse('communication:commandes_sms')
    contact = CommandeSms.objects.get(mot_cle='CONTACT')
    assert (contact.alias, contact.portee, contact.actif, contact.created_by) == ('TEL, TELEPHONE', 'ELEVE', True, directeur)
    assert contact.mots == ['CONTACT', 'TEL', 'TELEPHONE'] and contact.format_sms == 'CONTACT <matricule>'


def test_pages_liste_modification_bascule_suppression(client, ecole, directeur):
    horaires = commande(ecole['etab'], 'HORAIRES', 'Cours de 7h a 12h', description='Horaires des cours')
    baker.make(IncomingSMSLog, command_type='PERSO', commande=horaires, sender_number='+22670112233', message_text='HORAIRES')

    liste = client.get(reverse('communication:commandes_sms')).content.decode()
    assert 'Cours de 7h a 12h' in liste and 'Horaires des cours' in liste and 'NOTE &lt;matricule&gt;' in liste
    assert '+ Nouvelle commande' in liste and 'Supprimer la commande HORAIRES ?' in liste

    modif = client.post(reverse('communication:commande_sms_modifier', args=[horaires.pk]),
                        {'mot_cle': 'HORAIRES', 'portee': 'ECOLE', 'actif': '1', 'reponse': 'Cours de 7h30 a 12h30',
                         'description': 'Horaires des cours'})
    assert modif.status_code == 302 and CommandeSms.objects.get(pk=horaires.pk).reponse == 'Cours de 7h30 a 12h30'

    client.post(reverse('communication:commande_sms_basculer', args=[horaires.pk]))
    assert CommandeSms.objects.get(pk=horaires.pk).actif is False
    assert 'Désactivée' in client.get(reverse('communication:commandes_sms')).content.decode()

    simulateur = client.get(reverse('communication:sms_direct')).content.decode()
    assert 'NOTE, SOLDE, ABS, AIDE, HORAIRES' in simulateur and 'Horaires des cours' in simulateur

    client.post(reverse('communication:commande_sms_supprimer', args=[horaires.pk]))
    assert not CommandeSms.objects.filter(pk=horaires.pk).exists()
    assert IncomingSMSLog.objects.get(message_text='HORAIRES').commande is None   # l'historique reste


def test_gestion_reservee_par_la_matrice_des_droits(client, ecole):
    from parametres import droits
    client.force_login(baker.make('accounts.User', etablissement=ecole['etab'], role='ENSEIGNANT', must_change_password=False))
    droits.invalider_cache()

    liste = client.get(reverse('communication:commandes_sms'))
    creation = client.get(reverse('communication:commande_sms_nouvelle'))

    assert liste.status_code == 200 and '+ Nouvelle commande' not in liste.content.decode()
    assert creation.status_code == 302 and creation.url == '/'
