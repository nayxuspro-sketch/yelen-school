"""Compte rendu quotidien du promoteur par SMS (communication/compte_rendu.py) : chiffres et texte du jour
(≤ 160 caractères), envoi à l'heure par le service SMS une seule fois par jour, envoi à la demande par ``sms_auto``,
paramétrage (heure, numéros) et aperçu dans Paramètres → SMS automatiques."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from model_bakery import baker

from communication import compte_rendu
from parametres.models import DeclencheurSMS

pytestmark = pytest.mark.django_db

JOUR = date(2026, 10, 30)


@pytest.fixture
def etab():
    etab = baker.make('etablissements.Etablissement', code='LPB')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='Lycée Privé Bethel', sigle='LPB')
    return etab


@pytest.fixture
def direction(etab):
    return baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False)


@pytest.fixture
def declencheur(etab):
    return baker.make(DeclencheurSMS, etablissement=etab, type_declencheur='COMPTE_RENDU', actif=True,
                      heure_envoi=time(18, 0), destinataires='70123456, +22676543210')


@pytest.fixture
def journee(etab, direction):
    """Une journée complète : 3 encaissements (dont un remboursé en partie), 2 dépenses (1 validée, 1 brouillon),
    1 caisse arrêtée sur 2 caissiers, 2 appels (3 absents, 1 retard)."""
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)
    classe = baker.make('parametres.Classe', etablissement=etab, cycle=baker.make('parametres.Cycle'))
    inscriptions = [baker.make('inscriptions.Inscription', classe=classe, annee_scolaire=annee,
                               eleve=baker.make('inscriptions.Eleve', date_naissance=date(2012, 1, 1), photo=''))
                    for _ in range(4)]
    caissier2 = baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False)
    paiements = [
        baker.make('finances.Paiement', inscription=inscriptions[0], montant=Decimal('150000'), date_paiement=JOUR,
                   mode_paiement='ESPECES', encaisse_par=direction),
        baker.make('finances.Paiement', inscription=inscriptions[1], montant=Decimal('100000'), date_paiement=JOUR,
                   mode_paiement='MOBILE_MONEY', encaisse_par=caissier2),
        baker.make('finances.Paiement', inscription=inscriptions[2], montant=Decimal('50000'), date_paiement=JOUR,
                   mode_paiement='ESPECES', encaisse_par=direction),
        baker.make('finances.Paiement', inscription=inscriptions[3], montant=Decimal('999999'),
                   date_paiement=JOUR - timedelta(days=1), mode_paiement='ESPECES', encaisse_par=direction),  # veille
    ]
    baker.make('finances.Remboursement', paiement=paiements[2], montant=Decimal('20000'), date_remboursement=JOUR,
               rembourse_par=direction)
    categorie = baker.make('finances.CategorieDepense', etablissement=etab)
    baker.make('finances.Depense', annee_scolaire=annee, categorie=categorie, montant=Decimal('85000'),
               date_depense=JOUR, statut='VALIDEE')
    baker.make('finances.Depense', annee_scolaire=annee, categorie=categorie, montant=Decimal('40000'),
               date_depense=JOUR, statut='BROUILLON')                                               # non comptée
    baker.make('finances.ClotureCaisse', etablissement=etab, date=JOUR, caissier=direction, montant_compte=Decimal('175000'),
               ecart=Decimal('-5000'))
    appels = [baker.make('presences.Appel', classe=classe, annee_scolaire=annee, date=JOUR, matiere=None),
              baker.make('presences.Appel', classe=classe, annee_scolaire=annee, date=JOUR,
                         matiere=baker.make('pedagogie.Matiere'))]
    for appel, statuts in zip(appels, (['ABSENT', 'ABSENT', 'RETARD', 'PRESENT'], ['ABSENT', 'ABSENT', 'PRESENT', 'PRESENT'])):
        for inscription, statut in zip(inscriptions, statuts):
            baker.make('presences.Presence', appel=appel, inscription=inscription, statut=statut)
    return etab


# ── Composition ──────────────────────────────────────────────────────────────

def test_chiffres_et_texte_du_jour(journee):
    c = compte_rendu.chiffres_du_jour(journee, JOUR)

    assert c['encaisse'] == Decimal('300000') and c['nb_paiements'] == 3           # la veille est exclue
    assert c['rembourse'] == Decimal('20000') and c['especes'] == Decimal('180000')  # espèces 200 000 − remboursé
    assert c['depenses'] == Decimal('85000') and c['nb_depenses'] == 1              # brouillon non compté
    assert c['caissiers'] == 2 and c['caisses_arretees'] == 1 and c['ecart'] == Decimal('-5000')
    assert c['appels'] == 2 and c['absents'] == 2 and c['retards'] == 1            # élèves distincts, pas lignes

    texte = compte_rendu.composer(journee, JOUR)
    assert texte == ("LPB 30/10: Encaisse 300 000 F (3 recus), rembourse 20 000 F, especes 180 000 F. "
                     "Depenses 85 000 F. Caisses arretees 1/2, ecart -5 000 F. Absents 2 (2 appels).")   # retards retirés : 169 > 160
    assert len(texte) <= compte_rendu.LIMITE
    assert not any(car in texte for car in 'çêâîôûë')                                # jeu GSM : un seul SMS

    c['ecart'], c['rembourse'] = Decimal('0'), Decimal('0')                           # journée ordinaire : texte complet
    assert compte_rendu.composer(journee, JOUR, c) == ("LPB 30/10: Encaisse 300 000 F (3 recus), especes 180 000 F. "
                                                       "Depenses 85 000 F. Caisses arretees 1/2. Absents 2, retards 1 (2 appels).")


def test_journee_vide(etab):
    assert compte_rendu.composer(etab, JOUR) == "LPB 30/10: Encaisse 0 F (0 recus). Depenses 0 F. Aucun appel saisi."


def test_texte_raccourci_pour_tenir_en_un_sms(etab):
    chiffres = {'encaisse': Decimal('12345000'), 'nb_paiements': 123, 'rembourse': Decimal('1234000'),
                'especes': Decimal('10000000'), 'depenses': Decimal('2345000'), 'nb_depenses': 12, 'caissiers': 3,
                'caisses_arretees': 3, 'ecart': Decimal('-123000'), 'appels': 45, 'absents': 123, 'retards': 45}
    texte = compte_rendu.composer(etab, JOUR, chiffres)

    assert len(texte) <= compte_rendu.LIMITE
    assert texte == ("LPB 30/10: Encaisse 12 345 000 F, rembourse 1 234 000 F. Depenses 2 345 000 F. Caisses arretees 3/3. "
                     "Absents 123 (45 appels).")


# ── Envoi à l'heure par le service SMS ───────────────────────────────────────

def test_envoi_a_l_heure_une_seule_fois_par_jour(journee, declencheur, mocker):
    mocker.patch('core.sms.sms_actifs', return_value=True)
    envoyer = mocker.patch('core.tasks.envoyer_sms_async')
    tz = timezone.get_current_timezone()
    avant = datetime(2026, 10, 30, 17, 59, tzinfo=tz)
    apres = datetime(2026, 10, 30, 18, 0, tzinfo=tz)

    assert compte_rendu.envoyer_comptes_rendus_dus(avant) == 0
    envoyer.assert_not_called()

    assert compte_rendu.envoyer_comptes_rendus_dus(apres) == 2
    assert [appel.args[0] for appel in envoyer.call_args_list] == ['70123456', '+22676543210']
    assert envoyer.call_args.args[1].startswith('LPB 30/10: Encaisse 300 000 F')
    declencheur.refresh_from_db()
    assert declencheur.last_run == apres and declencheur.nb_envoyes_total == 2

    assert compte_rendu.envoyer_comptes_rendus_dus(apres + timedelta(hours=2)) == 0       # déjà parti aujourd'hui
    assert compte_rendu.envoyer_comptes_rendus_dus(apres + timedelta(days=1)) == 2        # le lendemain
    assert envoyer.call_count == 4


def test_pas_d_envoi_si_inactif_sans_numero_ou_sms_desactives(declencheur, mocker):
    envoyer = mocker.patch('core.tasks.envoyer_sms_async')
    quand = datetime(2026, 10, 30, 19, 0, tzinfo=timezone.get_current_timezone())

    mocker.patch('core.sms.sms_actifs', return_value=False)
    assert compte_rendu.envoyer_comptes_rendus_dus(quand) == 0
    mocker.patch('core.sms.sms_actifs', return_value=True)

    declencheur.actif = False
    declencheur.save()
    assert compte_rendu.envoyer_comptes_rendus_dus(quand) == 0
    declencheur.actif, declencheur.destinataires = True, ''
    declencheur.save()
    assert compte_rendu.envoyer_comptes_rendus_dus(quand) == 0

    envoyer.assert_not_called()
    declencheur.refresh_from_db()
    assert declencheur.last_run is None


def test_service_sms_envoie_les_comptes_rendus_dus(mocker):
    mocker.patch('communication.sms_recus.relever_boite_reception',
                 return_value={'ok': True, 'motif': '', 'nouveaux': 0, 'ignores': 0})
    mocker.patch('core.tasks.traiter_file_sms', return_value={'envoyes': 0, 'echecs': 0, 'en_attente': 0})
    dus = mocker.patch('communication.compte_rendu.envoyer_comptes_rendus_dus', return_value=2)
    sortie = StringIO()

    call_command('sms_recus', stdout=sortie)

    dus.assert_called_once_with()
    assert 'Compte rendu quotidien du promoteur : 2 SMS mis en file.' in sortie.getvalue()


# ── Commande sms_auto : à la demande seulement ───────────────────────────────

def test_sms_auto_ignore_le_compte_rendu_sauf_demande_explicite(journee, declencheur, mocker):
    mocker.patch('core.sms.get_sms_val', return_value=True)
    mocker.patch('core.tasks.traiter_file_sms', return_value={'envoyes': 0, 'echecs': 0, 'en_attente': 0})
    envoyer = mocker.patch('core.tasks.envoyer_sms_async')

    call_command('sms_auto', stdout=StringIO())                      # lot du matin : pas le compte rendu
    envoyer.assert_not_called()

    sortie = StringIO()
    call_command('sms_auto', type='COMPTE_RENDU', stdout=sortie)    # bouton Tester : envoi immédiat
    assert envoyer.call_count == 2
    assert '[Compte rendu quotidien du promoteur] 2 SMS envoyé(s)' in sortie.getvalue()
    declencheur.refresh_from_db()
    assert declencheur.nb_envoyes_total == 2
    assert declencheur.last_run is None                              # l'envoi automatique du jour reste dû

    call_command('sms_auto', type='COMPTE_RENDU', dry_run=True, stdout=StringIO())
    assert envoyer.call_count == 2


# ── Paramétrage et aperçu ────────────────────────────────────────────────────

def test_page_affiche_le_compte_rendu_et_son_apercu(client, journee, direction, mocker):
    mocker.patch('django.utils.timezone.localdate', return_value=JOUR)
    client.force_login(direction)

    page = client.get(reverse('parametres:sms_auto_config')).content.decode()

    assert 'Compte rendu quotidien du promoteur' in page
    assert 'LPB 30/10: Encaisse 300 000 F (3 recus)' in page
    assert 'name="heure_envoi"' in page and 'name="destinataires"' in page
    assert DeclencheurSMS.objects.filter(etablissement=journee, type_declencheur='COMPTE_RENDU').exists()


def test_enregistrement_heure_et_numeros(client, etab, direction):
    client.force_login(direction)
    client.get(reverse('parametres:sms_auto_config'))
    d = DeclencheurSMS.objects.get(etablissement=etab, type_declencheur='COMPTE_RENDU')
    url = reverse('parametres:sms_auto_save', kwargs={'pk': d.pk})

    reponse = client.post(url, {'heure_envoi': '18:30', 'destinataires': '70 12 34 56 ; +226 76 54 32 10'}, follow=True)
    d.refresh_from_db()
    assert d.heure_envoi == time(18, 30) and d.destinataires == '70123456, +22676543210'
    assert d.liste_destinataires() == ['70123456', '+22676543210']
    assert 'envoi chaque jour à 18:30 à 2 numéro(s)' in reponse.content.decode()

    for donnees, erreur in (
        ({'heure_envoi': '18:30', 'destinataires': '1234'}, 'Numéro invalide : 1234'),
        ({'heure_envoi': '18:30', 'destinataires': ''}, 'Indiquez de 1 à 5 numéros'),
        ({'heure_envoi': '', 'destinataires': '70123456'}, "Indiquez l'heure d'envoi"),
    ):
        assert escape(erreur) in client.post(url, donnees, follow=True).content.decode()
    d.refresh_from_db()
    assert d.heure_envoi == time(18, 30) and d.destinataires == '70123456, +22676543210'   # inchangé


def test_tester_exige_un_numero(client, etab, direction, mocker):
    mocker.patch('parametres.views.messages_sms._sms_enabled', return_value=True)
    client.force_login(direction)
    d = baker.make(DeclencheurSMS, etablissement=etab, type_declencheur='COMPTE_RENDU', actif=True, destinataires='')

    page = client.post(reverse('parametres:sms_auto_executer', kwargs={'pk': d.pk}), follow=True).content.decode()

    assert escape("Indiquez d'abord le ou les numéros du promoteur.") in page
