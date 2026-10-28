"""Lot G — comptes parents en masse : regroupement par téléphone, création avec mot de passe provisoire, SMS
d'accueil, connexion par numéro de téléphone."""
from datetime import date

import pytest
from django.urls import reverse
from model_bakery import baker

from accounts import parents_masse
from accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def ecole(client):
    etab = baker.make('etablissements.Etablissement')
    annee = baker.make('parametres.AnneeScolaire', etablissement=etab, libelle='2026-2027', est_courante=True,
                       date_debut=date(2026, 10, 1), date_fin=date(2027, 6, 30))
    classe = baker.make('parametres.Classe', etablissement=etab, nom='6e A', actif=True)

    def inscrire(nom, prenom, telephone='', tuteur_telephone='', statut='AFFECTE', **champs):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, date_naissance=date(2013, 1, 1), photo='',
                           telephone_parent=telephone, tuteur_telephone=tuteur_telephone, **champs)
        return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut=statut)

    aine = inscrire('OUEDRAOGO', 'Awa', '+226 70 12 34 56', nom_pere='OUEDRAOGO Issa')
    cadet = inscrire('OUEDRAOGO', 'Ali', '70123456')
    seul = inscrire('ZONGO', 'Paul', tuteur_telephone='76 00 00 01', tuteur_nom='ZONGO Marie')
    muet = inscrire('SANA', 'Léa')
    equipe = inscrire('KABORE', 'Eve', '71 11 11 11')
    parent_existant = baker.make('accounts.User', etablissement=etab, role='PARENT', must_change_password=False)
    parent_existant.eleves_lies.add(equipe.eleve)
    inscrire('TRAORE', 'Zoé', '78 88 88 88', statut='ABANDON')
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(directeur)
    return {'etab': etab, 'annee': annee, 'aine': aine, 'cadet': cadet, 'seul': seul, 'muet': muet, 'equipe': equipe,
            'directeur': directeur}


def test_familles_regroupees_par_telephone(ecole):
    groupes, sans_telephone = parents_masse.familles_sans_compte(ecole['etab'], ecole['annee'])
    assert [(g['telephone'], g['responsable'], [i.eleve.prenom for i in g['enfants']], g['compte_existant']) for g in groupes] == [
        ('70123456', 'OUEDRAOGO Issa', ['Ali', 'Awa'], None),
        ('76000001', 'ZONGO Marie', ['Paul'], None),
    ]
    assert sans_telephone == [ecole['muet']]


def test_creation_en_masse_sms_et_connexion_par_telephone(client, ecole, mocker):
    mocker.patch('core.sms.sms_actifs', return_value=True)
    envoi = mocker.patch('core.tasks.envoyer_sms_async', return_value=object())
    page = client.get(reverse('accounts:parents_masse'))
    assert page.status_code == 200 and page.context['nb_enfants'] == 3

    reponse = client.post(reverse('accounts:parents_masse'), {'cles': ['70123456']})
    assert reponse.status_code == 200
    resultats = reponse.context['resultats']
    assert len(resultats) == 1
    compte, mot_de_passe = resultats[0]['compte'], resultats[0]['mot_de_passe']
    assert compte.email == '70123456@parent.invalid' and compte.identifiant_connexion == '70123456'
    assert (compte.role, compte.telephone, compte.must_change_password, compte.etablissement) == ('PARENT', '70123456', True, ecole['etab'])
    assert (compte.last_name, compte.first_name) == ('OUEDRAOGO', 'Issa')
    assert set(compte.eleves_lies.all()) == {ecole['aine'].eleve, ecole['cadet'].eleve}
    assert len(mot_de_passe) == 12 and compte.check_password(mot_de_passe)
    html = reponse.content.decode()
    assert mot_de_passe in html and 'data-csp-action="print"' in html
    numero, message = envoi.call_args.args
    assert numero == '70123456' and mot_de_passe in message and len(message) <= 160
    assert User.objects.filter(role='PARENT').count() == 2, 'ZONGO non cochée : pas de compte'

    # La famille créée disparaît de la liste ; la liste des utilisateurs affiche le téléphone comme identifiant
    assert [g['telephone'] for g in client.get(reverse('accounts:parents_masse')).context['groupes']] == ['76000001']
    assert '70123456' in client.get(reverse('accounts:user_list')).content.decode()

    # Connexion par téléphone (toute mise en forme), puis changement de mot de passe obligatoire
    client.logout()
    connexion = client.post(reverse('accounts:login'), {'username': '+226 70 12 34 56', 'password': mot_de_passe})
    assert connexion.status_code == 302
    assert client.get(reverse('core:portail_parent')).status_code == 302   # redirigé vers le changement de mot de passe
    assert client.get(reverse('accounts:profile')).status_code == 200
    assert client.session['_auth_user_id'] == str(compte.pk)


def test_compte_existant_sur_le_meme_telephone_est_complete(client, ecole, mocker):
    mocker.patch('core.sms.sms_actifs', return_value=False)
    existant = baker.make('accounts.User', etablissement=ecole['etab'], role='PARENT', email='70123456@parent.invalid',
                          must_change_password=False)
    groupes, _ = parents_masse.familles_sans_compte(ecole['etab'], ecole['annee'])
    assert groupes[0]['compte_existant'] == existant
    reponse = client.post(reverse('accounts:parents_masse'), {'cles': ['70123456', '76000001']})
    resultats = {r['identifiant']: r for r in reponse.context['resultats']}
    assert resultats['70123456']['mot_de_passe'] is None and resultats['76000001']['mot_de_passe']
    assert set(existant.eleves_lies.all()) == {ecole['aine'].eleve, ecole['cadet'].eleve}
    assert 'compte existant' in reponse.content.decode()


def test_identifiants_et_mot_de_passe():
    assert parents_masse.email_depuis_identifiant(' Awa@Ecole.BF ') == 'awa@ecole.bf'
    assert parents_masse.email_depuis_identifiant('(+226) 70-12-34-56') == '70123456@parent.invalid'
    assert parents_masse.email_depuis_identifiant('1234') == '1234', 'numéro incomplet : inchangé'
    assert parents_masse.telephone_normalise('0022670123456') == '70123456'
    assert len(parents_masse.mot_de_passe_provisoire()) == 12
    assert len(parents_masse.message_sms('LS', '70123456', 'Abcdefgh2345', 'https://192.168.11.108:8443/')) <= 160


def test_reserve_a_la_direction(client, ecole):
    secretaire = baker.make('accounts.User', etablissement=ecole['etab'], role='SECRETAIRE', must_change_password=False)
    client.force_login(secretaire)
    assert client.get(reverse('accounts:parents_masse')).status_code == 302
