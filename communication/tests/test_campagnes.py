"""Lot H — campagnes SMS ciblées : publics, dédoublonnage par numéro, variables, aperçu, mise en file par lot (un
seul fil d'envoi), suivi, renvoi des échecs et droits."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from model_bakery import baker

from communication import campagnes
from core import tasks
from core.models import CampagneSms, SmsSortant

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client, settings):
    settings.SMS_ENABLED = True
    etab = baker.make('etablissements.Etablissement', nom='LE SAVOIR')
    baker.make('parametres.IdentiteEtablissement', etablissement=etab, nom_etablissement='LE SAVOIR', sigle='LS')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab, nom='Scolarité', code='SCO', actif=True)
    cycle_sixieme = baker.make('parametres.Cycle', etablissement=etab, nom='Post-primaire', code='POST', ordre=1)
    cycle_cinquieme = baker.make('parametres.Cycle', etablissement=etab, nom='Secondaire', code='SEC', ordre=2)
    sixieme = baker.make('parametres.Classe', etablissement=etab, cycle=cycle_sixieme, nom='6e A', actif=True)
    cinquieme = baker.make('parametres.Classe', etablissement=etab, cycle=cycle_cinquieme, nom='5e A', actif=True)

    def inscrire(nom, prenom, classe, statut='AFFECTE', **champs):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, date_naissance=date(2013, 1, 1), photo='', **champs)
        return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut=statut)

    awa = inscrire('OUEDRAOGO', 'Awa', sixieme, telephone_parent='70 12 34 56')
    ali = inscrire('OUEDRAOGO', 'Ali', cinquieme, telephone_parent='+226 70123456')      # même famille, autre classe
    paul = inscrire('ZONGO', 'Paul', sixieme, telephone_parent='', tuteur_telephone='76000001')
    inscrire('SANA', 'Léa', sixieme, telephone_parent='12')                               # numéro invalide
    zoe = inscrire('TRAORE', 'Zoé', sixieme, telephone_parent='78888888')
    inscrire('KINDA', 'Omar', sixieme, statut='ABANDON', telephone_parent='79999999')      # parti : exclu
    baker.make('finances.Creance', inscription=awa, rubrique=rubrique, montant=Decimal('100000'), actif=True)
    baker.make('finances.Creance', inscription=zoe, rubrique=rubrique, montant=Decimal('20000'), actif=True)
    baker.make('finances.Creance', inscription=paul, rubrique=rubrique, montant=Decimal('50000'), actif=True)
    baker.make('finances.Paiement', inscription=paul, montant=Decimal('50000'), rubrique=rubrique)
    baker.make('personnel.MembrePersonnel', etablissement=etab, nom='KABORE', prenom='Salif', telephone='71 11 11 11')
    baker.make('personnel.MembrePersonnel', etablissement=etab, nom='ZIDA', prenom='Aline', telephone='')
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', est_tous_cycles=True, must_change_password=False)
    client.force_login(directeur)
    return {'etab': etab, 'annee': annee, 'sixieme': sixieme, 'cinquieme': cinquieme,
            'cycle_sixieme': cycle_sixieme, 'cycle_cinquieme': cycle_cinquieme,
            'awa': awa, 'ali': ali, 'paul': paul, 'zoe': zoe, 'directeur': directeur}


def _numeros(liste):
    return sorted(d.numero for d in liste)


def test_publics_et_dedoublonnage(ecole):
    e = ecole
    tous, compteurs = campagnes.destinataires(e['etab'], e['annee'], 'PARENTS_TOUS', {}, sigle='LS')
    assert _numeros(tous) == ['+22670123456', '+22676000001', '+22678888888']
    assert compteurs == {'sans_numero': 1}, 'numéro « 12 » invalide ; abandon exclu'
    famille = next(d for d in tous if d.numero == '+22670123456')
    assert famille.nom == 'OUEDRAOGO ALI, OUEDRAOGO AWA', 'ordre : classe puis nom'
    assert famille.variables == {'etablissement': 'LS', 'eleve': 'OUEDRAOGO ALI, OUEDRAOGO AWA', 'classe': '5e A, 6e A', 'reste': '0'}

    classes, _ = campagnes.destinataires(e['etab'], e['annee'], 'PARENTS_CLASSES', {'classes': [str(e['cinquieme'].pk)]})
    assert _numeros(classes) == ['+22670123456'] and classes[0].variables['eleve'] == 'OUEDRAOGO ALI'

    retard, _ = campagnes.destinataires(e['etab'], e['annee'], 'PARENTS_RETARD', {})
    assert _numeros(retard) == ['+22670123456', '+22678888888'], 'Paul a soldé sa créance'
    assert next(d for d in retard if d.numero == '+22670123456').variables['reste'] == '100 000'

    appel = baker.make('presences.Appel', classe=e['sixieme'], annee_scolaire=e['annee'], date=date(2026, 11, 3))
    baker.make('presences.Presence', appel=appel, inscription=e['paul'], statut='ABSENT')
    baker.make('presences.Presence', appel=appel, inscription=e['awa'], statut='RETARD')
    absents, _ = campagnes.destinataires(e['etab'], e['annee'], 'PARENTS_ABSENTS', {'date': '2026-11-03'})
    assert _numeros(absents) == ['+22676000001']
    assert campagnes.destinataires(e['etab'], e['annee'], 'PARENTS_ABSENTS', {'date': '2026-11-04'})[0] == []

    personnel, compteurs = campagnes.destinataires(e['etab'], e['annee'], 'PERSONNEL', {}, sigle='LS')
    assert _numeros(personnel) == ['+22671111111'] and compteurs == {'sans_numero': 1}
    assert personnel[0].variables == {'nom': 'KABORE Salif', 'etablissement': 'LS'}


def test_rendu_des_variables():
    assert campagnes.rendre('Bonjour, {eleve} ({classe}) doit {reste} F. {inconnue} — {etablissement}',
                            {'eleve': 'Awa', 'classe': '6e A', 'reste': '5 000', 'etablissement': 'LS'}) \
        == 'Bonjour, Awa (6e A) doit 5 000 F. {inconnue} — LS'


def test_apercu_puis_envoi_en_un_seul_fil(client, ecole, mocker, django_capture_on_commit_callbacks):
    e = ecole
    thread = mocker.patch('core.tasks.threading.Thread')
    donnees = {'titre': 'Réunion', 'cible': 'PARENTS_CLASSES', 'classes': [str(e['sixieme'].pk)],
               'message': 'Reunion parents {classe} samedi 8h. {etablissement}', 'confirmer': '0'}
    apercu = client.post(reverse('communication:campagne_nouvelle'), donnees)
    assert apercu.status_code == 200 and apercu.context['nb_destinataires'] == 3
    assert apercu.context['nb_sans_numero'] == 1 and apercu.context['plus_long'] == len('Reunion parents 6e A samedi 8h. LS')
    assert 'Envoyer 3 SMS' in apercu.content.decode() and not CampagneSms.objects.exists()

    donnees['confirmer'] = '1'
    with django_capture_on_commit_callbacks(execute=True):
        reponse = client.post(reverse('communication:campagne_nouvelle'), donnees)
    campagne = CampagneSms.objects.get()
    assert reponse.status_code == 302 and reponse.url == reverse('communication:campagne_detail', args=[campagne.pk])
    assert (campagne.titre, campagne.cible, campagne.nb_destinataires, campagne.envoyee_par) == ('Réunion', 'PARENTS_CLASSES', 3, e['directeur'])
    assert campagne.criteres == {'classes': [str(e['sixieme'].pk)]}
    sms = list(campagne.sms.order_by('numero'))
    assert [s.numero for s in sms] == ['+22670123456', '+22676000001', '+22678888888']
    assert all(s.message == 'Reunion parents 6e A samedi 8h. LS' and s.statut == 'EN_ATTENTE' for s in sms)
    assert sms[0].destinataire == 'OUEDRAOGO AWA'
    thread.assert_called_once()                                  # un seul fil pour toute la campagne

    # Corps du fil : la file est vidée par paquets ; une erreur définitive met le SMS en échec
    passerelle = mocker.patch('core.sms.envoyer_sms', side_effect=[(True, ''), (False, 'Numéro invalide'), (True, '')])
    mocker.patch('core.tasks.connection', MagicMock())
    tasks._vider_file()
    assert passerelle.call_count == 3
    assert campagne.bilan() == {'envoyes': 2, 'echecs': 1, 'en_attente': 0}
    echec = campagne.sms.get(statut='ECHEC')
    assert (echec.tentatives, echec.derniere_erreur) == (1, 'Numéro invalide')

    detail = client.get(reverse('communication:campagne_detail', args=[campagne.pk]))
    assert detail.status_code == 200 and 'Renvoyer les échecs (1)' in detail.content.decode()
    liste = client.get(reverse('communication:campagne_list'))
    assert liste.context['campagnes'][0].suivi == {'envoyes': 2, 'echecs': 1, 'en_attente': 0}

    with django_capture_on_commit_callbacks(execute=True):
        renvoi = client.post(reverse('communication:campagne_renvoyer', args=[campagne.pk]))
    assert renvoi.status_code == 302
    echec.refresh_from_db()
    assert (echec.statut, echec.tentatives, echec.derniere_erreur) == ('EN_ATTENTE', 0, '')
    assert thread.call_count == 2 and campagne.bilan() == {'envoyes': 2, 'echecs': 0, 'en_attente': 1}


def test_sms_desactives_ou_criteres_incomplets(client, ecole, settings):
    settings.SMS_ENABLED = False
    reponse = client.post(reverse('communication:campagne_nouvelle'), {
        'titre': 'Test', 'cible': 'PARENTS_TOUS', 'message': 'Bonjour', 'confirmer': '1'})
    assert reponse.status_code == 200 and 'SMS sont désactivés' in reponse.content.decode()
    assert not CampagneSms.objects.exists() and not SmsSortant.objects.exists()

    settings.SMS_ENABLED = True
    reponse = client.post(reverse('communication:campagne_nouvelle'), {
        'titre': 'Test', 'cible': 'PARENTS_CLASSES', 'message': 'Bonjour', 'confirmer': '1'})
    assert 'Cochez au moins une classe' in reponse.content.decode() and not CampagneSms.objects.exists()


def test_reserve_a_la_direction_secretariat_comptabilite(client, ecole):
    client.force_login(baker.make('accounts.User', etablissement=ecole['etab'], role='ENSEIGNANT', must_change_password=False))
    assert client.get(reverse('communication:campagne_list')).status_code == 403
    assert client.get(reverse('communication:campagne_nouvelle')).status_code == 403


def test_suppression_d_une_campagne_et_de_ses_sms(client, ecole):
    from parametres import droits
    from parametres.models import DroitAcces
    e = ecole
    campagne = CampagneSms.objects.create(etablissement=e['etab'], annee_scolaire=e['annee'], titre='Rentrée',
                                          message='Bonjour', cible='PARENTS_TOUS', nb_destinataires=2, envoyee_par=e['directeur'])
    SmsSortant.objects.create(numero='+22670123456', message='Bonjour', campagne=campagne, statut='ENVOYE')
    SmsSortant.objects.create(numero='+22676000001', message='Bonjour', campagne=campagne)   # encore en attente
    autre = SmsSortant.objects.create(numero='+22678888888', message='Hors campagne')
    liste_url, detail_url = reverse('communication:campagne_list'), reverse('communication:campagne_detail', args=[campagne.pk])
    url = reverse('communication:campagne_supprimer', args=[campagne.pk])

    assert f'action="{url}"' in client.get(liste_url).content.decode()
    assert 'Supprimer cette campagne et ses 2 SMS' in client.get(detail_url).content.decode()

    DroitAcces.objects.create(role='DIRECTEUR', module='communication', fonctionnalite='/communication/campagnes/',
                              action='supprimer', autorise=False)
    droits.invalider_cache()
    refus = client.post(url)
    assert refus.status_code == 302 and refus.url == '/' and CampagneSms.objects.filter(pk=campagne.pk).exists()
    assert f'action="{url}"' not in client.get(liste_url).content.decode()
    assert 'Supprimer la campagne' not in client.get(detail_url).content.decode()
    DroitAcces.objects.all().delete()
    droits.invalider_cache()

    retour = client.post(url, follow=True)
    assert retour.redirect_chain[0][0] == liste_url and 'Campagne « Rentrée » supprimée (2 SMS).' in retour.content.decode()
    assert not CampagneSms.objects.filter(pk=campagne.pk).exists()
    assert list(SmsSortant.objects.values_list('pk', flat=True)) == [autre.pk]


def test_campagnes_parentales_limitees_aux_cycles_autorises(client, ecole):
    e = ecole
    utilisateur = baker.make('accounts.User', etablissement=e['etab'], role='DIRECTEUR', must_change_password=False)
    utilisateur.cycles.add(e['cycle_sixieme'])
    client.force_login(utilisateur)

    formulaire = client.get(reverse('communication:campagne_nouvelle'))
    html = formulaire.content.decode()
    assert str(e['sixieme'].pk) in html and str(e['cinquieme'].pk) not in html

    apercu = client.post(reverse('communication:campagne_nouvelle'), {
        'titre': 'Parents du cycle', 'cible': 'PARENTS_TOUS', 'message': 'Bonjour', 'confirmer': '0',
    })
    assert apercu.status_code == 200 and apercu.context['nb_destinataires'] == 3
    assert apercu.context['nb_sans_numero'] == 1

    refus = client.post(reverse('communication:campagne_nouvelle'), {
        'titre': 'Classe hors périmètre', 'cible': 'PARENTS_CLASSES',
        'classes': [str(e['cinquieme'].pk)], 'message': 'Bonjour', 'confirmer': '1',
    })
    assert refus.status_code == 200 and 'hors de votre établissement ou des cycles accessibles' in refus.content.decode()
    assert not CampagneSms.objects.exists() and not SmsSortant.objects.exists()

    request = type('Request', (), {
        'user': utilisateur,
        'cycles_autorises': e['cycle_sixieme'].__class__.objects.filter(pk=e['cycle_sixieme'].pk),
        'est_tous_cycles': False,
    })()
    assert campagnes.destinataires(e['etab'], e['annee'], 'PARENTS_CLASSES',
                                   {'classes': [str(e['cinquieme'].pk)]}, request=request)[0] == []


def test_historique_sms_restraint_a_sa_portee_de_cycles(client, ecole):
    e = ecole
    classe_autorisee = CampagneSms.objects.create(
        etablissement=e['etab'], annee_scolaire=e['annee'], titre='Cycle accessible', message='Bonjour',
        cible='PARENTS_CLASSES', criteres={'classes': [str(e['sixieme'].pk)],
                                           'cycles_autorises': [str(e['cycle_sixieme'].pk)]},
    )
    classe_interdite = CampagneSms.objects.create(
        etablissement=e['etab'], annee_scolaire=e['annee'], titre='Cycle hors périmètre', message='Bonjour',
        cible='PARENTS_CLASSES', criteres={'classes': [str(e['cinquieme'].pk)]},
    )
    globale_ancienne = CampagneSms.objects.create(
        etablissement=e['etab'], annee_scolaire=e['annee'], titre='Ancienne campagne globale', message='Bonjour',
        cible='PARENTS_TOUS',
    )
    SmsSortant.objects.create(numero='+22670123456', message='Bonjour', campagne=classe_autorisee)
    utilisateur = baker.make('accounts.User', etablissement=e['etab'], role='DIRECTEUR', must_change_password=False)
    utilisateur.cycles.add(e['cycle_sixieme'])
    client.force_login(utilisateur)

    liste = client.get(reverse('communication:campagne_list'))
    assert [c.pk for c in liste.context['campagnes']] == [classe_autorisee.pk]
    assert client.get(reverse('communication:campagne_detail', args=[classe_autorisee.pk])).status_code == 200
    assert client.get(reverse('communication:campagne_detail', args=[classe_interdite.pk])).status_code == 404
    assert client.get(reverse('communication:campagne_detail', args=[globale_ancienne.pk])).status_code == 404


def test_campagne_personnel_ne_cible_que_les_membres_accessibles(ecole):
    e = ecole
    membre_accessible = baker.make('personnel.MembrePersonnel', etablissement=e['etab'], nom='AUTORISE', prenom='Cycle',
                                   telephone='70 00 00 01')
    membre_hors_cycle = baker.make('personnel.MembrePersonnel', etablissement=e['etab'], nom='HORS CYCLE', prenom='Cycle',
                                   telephone='70 00 00 02')
    membre_accessible.cycles.add(e['cycle_sixieme'])
    membre_hors_cycle.cycles.add(e['cycle_cinquieme'])
    utilisateur = baker.make('accounts.User', etablissement=e['etab'], role='DIRECTEUR', must_change_password=False)
    utilisateur.cycles.add(e['cycle_sixieme'])
    request = type('Request', (), {
        'user': utilisateur,
        'cycles_autorises': e['cycle_sixieme'].__class__.objects.filter(pk=e['cycle_sixieme'].pk),
        'est_tous_cycles': False,
    })()

    destinataires, _ = campagnes.destinataires(e['etab'], e['annee'], 'PERSONNEL', {}, request=request)
    assert [d.nom for d in destinataires] == ['AUTORISE Cycle']
