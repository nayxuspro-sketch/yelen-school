"""Communication bidirectionnelle par SMS : le message est envoyé en clair (sans lien), le parent répond en
répondant au SMS (créneau, accusé de réception, date de règlement, motif) ; un SMS libre reçoit un accusé au plus
une fois par jour — plus jamais « Commande invalide » en rafale — et l'école ne répond jamais à ses propres SMS."""
from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from model_bakery import baker

from communication import bidirectionnel, sms_recus
from communication.models import IncomingSMSLog, MessageParent, ReponseParent
from communication.sms_recus import traiter_sms_recu
from core.models import SmsSortant

pytestmark = pytest.mark.django_db
PARENT = '+22670112233'


@pytest.fixture
def ecole(settings):
    settings.SMS_ENABLED = True
    etab = baker.make('etablissements.Etablissement', nom='Lycée Le Savoir')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='Lycée Le Savoir', sigle='LSV')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 7, 31))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6e A', actif=True)
    awa = baker.make('inscriptions.Eleve', matricule='01-2026-0001', nom='OUEDRAOGO', prenom='Awa', photo='',
                     date_naissance=date(2013, 1, 1), telephone_parent='70 11 22 33', tuteur_telephone='', telephone_urgence='')
    baker.make('inscriptions.Inscription', eleve=awa, classe=classe, annee_scolaire=annee, statut='AFFECTE')
    return {'etab': etab, 'annee': annee, 'awa': awa}


@pytest.fixture
def directeur(client, ecole):
    user = baker.make('accounts.User', etablissement=ecole['etab'], role='DIRECTEUR', must_change_password=False)
    client.force_login(user)
    return user


def message(ecole, type_, objet, contenu, creneaux=(), **extra):
    return baker.make(MessageParent, etablissement=ecole['etab'], eleve=ecole['awa'], type=type_, objet=objet,
                      contenu=contenu, creneaux_proposes=list(creneaux),
                      **{'telephone_utilise': '70 11 22 33', 'sms_envoye': True, **extra})


def test_le_message_part_en_clair_par_sms_et_le_parent_repond_au_sms(client, ecole, directeur, mocker):
    mocker.patch('core.tasks.threading.Thread')
    url = reverse('communication:message_create')
    base = {'eleve': ecole['awa'].pk, 'type': 'CONVOCATION', 'objet': 'Entretien', 'envoyer_sms': 'on',
            'contenu': 'Merci de venir rencontrer le professeur principal.', 'creneaux': 'Lundi 12 mai 10h\nMardi 13 mai 14h30'}

    reponse = client.post(url, base)

    assert reponse.status_code == 200 and reponse['HX-Trigger'] == 'messageCreated'
    msg = MessageParent.objects.get()
    assert msg.sms_envoye and msg.sms.numero == '70 11 22 33' and msg.sms.statut == SmsSortant.Statut.EN_ATTENTE
    assert msg.sms.message == ("LSV - Entretien. Merci de venir rencontrer le professeur principal. "
                               "Repondez 1, 2: 1) Lundi 12 mai 10h 2) Mardi 13 mai 14h30")
    assert 'repondre/' not in msg.sms.message and len(msg.sms.message) <= 160

    detail = client.get(reverse('communication:message_detail', args=[msg.pk])).content.decode()
    assert "En attente d'envoi" in detail and 'Repondez 1, 2:' in detail

    trop_long = client.post(url, {**base, 'contenu': 'x' * 120}).content.decode()
    assert 'caractères pour 160 maximum' in trop_long and MessageParent.objects.count() == 1

    ecole['awa'].telephone_parent = ''
    ecole['awa'].save()
    sans_numero = client.post(url, base).content.decode()
    assert 'Aucun numéro de parent ni de tuteur' in sans_numero and MessageParent.objects.count() == 1


def test_textes_sms_par_type(ecole):
    avert = MessageParent(type='AVERTISSEMENT', objet='Retards', contenu='3 retards cette semaine.')
    relance = MessageParent(type='RELANCE', objet='Scolarite', contenu='Reste 50 000 F.')
    justif = MessageParent(type='JUSTIFICATIF', objet='Absence du 12/10', contenu='Merci de justifier.')
    assert bidirectionnel.texte_sms(avert, 'LSV') == 'LSV - Retards. 3 retards cette semaine. Repondez OK pour accuser reception.'
    assert bidirectionnel.texte_sms(relance) == 'Scolarite. Reste 50 000 F. Repondez avec la date de reglement prevue (ex: 15/11).'
    assert bidirectionnel.texte_sms(justif).endswith("Repondez a ce SMS avec le motif de l'absence.")


@patch('core.tasks.envoyer_sms_async')
def test_reponses_par_sms_selon_le_type_de_message(envoyer, ecole):
    convocation = message(ecole, 'CONVOCATION', 'Entretien', 'Venir voir le PP.', ['Lundi 12 mai à 10h00', 'Mardi 13 mai à 14h30'])

    journal, _ = traiter_sms_recu(PARENT, 'Je prends le 2')
    assert (journal.command_type, journal.message_parent, journal.eleve) == ('REPONSE', convocation, ecole['awa'])
    assert journal.is_authorized and journal.processed_successfully
    assert journal.response_text == bidirectionnel.ACCUSE_RECEPTION
    reponse = ReponseParent.objects.get(message=convocation)
    assert reponse.creneau_choisi == 'Mardi 13 mai à 14h30' and reponse.commentaire.endswith('] Je prends le 2')
    assert MessageParent.objects.get(pk=convocation.pk).statut == 'REPONDU'

    traiter_sms_recu(PARENT, 'lundi 12 mai')   # second SMS : même réponse complétée, créneau mis à jour
    reponse.refresh_from_db()
    assert reponse.creneau_choisi == 'Lundi 12 mai à 10h00' and reponse.commentaire.count('[SMS ') == 2
    assert ReponseParent.objects.count() == 1

    avertissement = message(ecole, 'AVERTISSEMENT', 'Retards', '3 retards.')
    traiter_sms_recu('70112233', 'Bien recu, je lui en parle')   # numéro local : même parent, message le plus récent
    assert ReponseParent.objects.get(message=avertissement).accuse_reception is True

    relance = message(ecole, 'RELANCE', 'Scolarite', 'Reste 50 000 F.')
    traiter_sms_recu(PARENT, 'Je paie le 15/11')
    assert ReponseParent.objects.get(message=relance).date_reglement_prevue == date(2026, 11, 15)
    assert envoyer.call_count == 4 and all(c.args[1] == bidirectionnel.ACCUSE_RECEPTION for c in envoyer.call_args_list)


@patch('core.tasks.envoyer_sms_async')
def test_message_libre_accuse_une_fois_par_jour_jamais_commande_invalide(envoyer, ecole):
    premier, _ = traiter_sms_recu('+22676000000', 'Bonjour, mon fils est malade aujourd hui')
    second, _ = traiter_sms_recu('+22676000000', 'Merci')
    note, _ = traiter_sms_recu('+22676000000', 'NOTE')

    assert premier.command_type == 'INVALID' and premier.response_text == sms_recus.ACCUSE_MESSAGE_LIBRE
    assert second.command_type == 'INVALID' and second.response_text == '' and 'Message libre' in second.error_message
    assert note.response_text == sms_recus.USAGES['NOTE'] and note.error_message == 'Matricule manquant.'
    assert not IncomingSMSLog.objects.filter(response_text__icontains='invalide').exists()
    assert envoyer.call_count == 2
    assert all(j.est_libre for j in (premier, second)) and all(not j.lu_le for j in (premier, second))


@patch('core.tasks.envoyer_sms_async')
def test_l_ecole_ne_repond_jamais_a_ses_propres_sms(envoyer, ecole):
    SmsSortant.objects.create(numero='70 11 22 33', message='LSV - Entretien. Venir voir le PP. Repondez a ce SMS pour confirmer.')
    SmsSortant.objects.create(numero=PARENT, message=sms_recus.ACCUSE_MESSAGE_LIBRE)

    echo, _ = traiter_sms_recu(PARENT, 'LSV - Entretien. Venir voir le PP. Repondez a ce SMS pour confirmer.')
    echo_accuse, _ = traiter_sms_recu(PARENT, sms_recus.ACCUSE_MESSAGE_LIBRE)

    assert [(j.command_type, j.response_text) for j in (echo, echo_accuse)] == [('INVALID', ''), ('INVALID', '')]
    assert all(j.error_message.startswith("Echo d'un SMS envoyé par l'école") for j in (echo, echo_accuse))
    envoyer.assert_not_called()


def test_messages_recus_liste_les_reponses_avec_le_message_d_origine(client, ecole, directeur):
    convocation = message(ecole, 'CONVOCATION', 'Entretien du 12 mai', 'Venir voir le PP.')
    baker.make(IncomingSMSLog, sender_number=PARENT, message_text='Je serai present', command_type='REPONSE',
               message_parent=convocation, eleve=ecole['awa'], response_text=bidirectionnel.ACCUSE_RECEPTION)

    html = client.get(reverse('communication:messages_recus')).content.decode()
    commandes = client.get(reverse('communication:messages_recus'), {'type': 'commandes'}).content.decode()

    assert 'Je serai present' in html and 'Convocation à un entretien : Entretien du 12 mai' in html and '1 non lu' in html
    assert reverse('communication:message_detail', args=[convocation.pk]) in html
    assert 'Je serai present' not in commandes


def test_renvoi_du_sms_d_un_message_non_envoye_ou_en_echec(client, ecole, directeur, mocker):
    mocker.patch('core.tasks.threading.Thread')
    msg = message(ecole, 'AVERTISSEMENT', 'Retards', '3 retards.', sms_envoye=False, telephone_utilise='')
    liste_url, renvoi_url = reverse('communication:message_list'), reverse('communication:message_renvoyer_sms', args=[msg.pk])

    liste = client.get(liste_url).content.decode()
    assert 'Non envoyé' in liste and 'Envoyer le SMS' in liste

    retour = client.post(renvoi_url, {'next': liste_url})
    msg.refresh_from_db()
    assert retour.status_code == 302 and retour.url == liste_url
    assert msg.sms_envoye and msg.telephone_utilise == '70 11 22 33' and msg.sms.numero == '70 11 22 33'
    assert msg.sms.message == 'LSV - Retards. 3 retards. Repondez OK pour accuser reception.'
    premier = msg.sms

    SmsSortant.objects.filter(pk=premier.pk).update(statut='ECHEC', derniere_erreur='Passerelle injoignable')
    liste = client.get(liste_url).content.decode()
    assert 'Échec' in liste and '>Renvoyer<' in liste
    assert client.post(renvoi_url).url == reverse('communication:message_detail', args=[msg.pk])
    msg.refresh_from_db()
    assert msg.sms != premier and msg.sms.statut == 'EN_ATTENTE' and SmsSortant.objects.count() == 2

    detail = client.get(reverse('communication:message_detail', args=[msg.pk])).content.decode()
    assert 'Renvoyer le SMS' in detail and "En attente d'envoi" in detail

    ecole['awa'].telephone_parent = ''
    ecole['awa'].save()
    MessageParent.objects.filter(pk=msg.pk).update(telephone_utilise='')
    sans_numero = client.post(renvoi_url, follow=True).content.decode()
    assert 'Aucun numéro de parent ni de tuteur' in sans_numero and SmsSortant.objects.count() == 2


def test_renvoi_refuse_par_la_matrice_des_droits(client, ecole, directeur):
    from parametres import droits
    from parametres.models import DroitAcces
    msg = message(ecole, 'AVERTISSEMENT', 'Retards', '3 retards.', sms_envoye=False)
    DroitAcces.objects.create(role='DIRECTEUR', module='communication', fonctionnalite='/communication/',
                              action='envoyer', autorise=False)
    droits.invalider_cache()

    liste = client.get(reverse('communication:message_list')).content.decode()
    refus = client.post(reverse('communication:message_renvoyer_sms', args=[msg.pk]))

    assert 'Non envoyé' in liste and 'Envoyer le SMS' not in liste
    assert refus.status_code == 302 and refus.url == '/' and SmsSortant.objects.count() == 0
