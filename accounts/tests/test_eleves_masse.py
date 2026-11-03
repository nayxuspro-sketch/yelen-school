"""Comptes élèves en masse (5.48.1) : un compte par élève inscrit sans compte, identifiant = matricule inscrit au dos de
la carte scolaire, mot de passe provisoire, connexion par matricule, isolation des rôles."""
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

    def inscrire(nom, prenom, matricule, statut='AFFECTE', telephone_parent='70 12 34 56'):
        eleve = baker.make('inscriptions.Eleve', nom=nom, prenom=prenom, matricule=matricule, photo='',
                           date_naissance=date(2013, 1, 1), telephone_parent=telephone_parent)
        return baker.make('inscriptions.Inscription', eleve=eleve, classe=classe, annee_scolaire=annee, statut=statut)

    awa = inscrire('OUEDRAOGO', 'Awa', 'LS-2026-01')
    ali = inscrire('OUEDRAOGO', 'Ali', 'LS-2026-02', telephone_parent='')
    deja = inscrire('KABORE', 'Eve', 'LS-2026-03')
    compte_existant = baker.make('accounts.User', etablissement=etab, role='ELEVE', must_change_password=False)
    compte_existant.eleves_lies.add(deja.eleve)
    inscrire('TRAORE', 'Zoé', 'LS-2026-04', statut='ABANDON')
    directeur = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', must_change_password=False)
    client.force_login(directeur)
    return {'etab': etab, 'annee': annee, 'awa': awa, 'ali': ali, 'deja': deja, 'directeur': directeur}


def test_seuls_les_eleves_sans_compte_sont_proposes(client, ecole):
    fiches = parents_masse.eleves_sans_compte(ecole['etab'], ecole['annee'])
    assert [f['matricule'] for f in fiches] == ['LS-2026-02', 'LS-2026-01'], 'tri par classe puis nom'
    page = client.get(reverse('accounts:eleves_masse'))
    assert page.status_code == 200 and page.context['nb_sans_compte'] == 2
    assert 'LS-2026-01' in page.content.decode()


def test_creation_en_masse_identifiant_matricule_et_connexion(client, ecole, mocker):
    mocker.patch('core.sms.sms_actifs', return_value=True)
    envoi = mocker.patch('core.tasks.envoyer_sms_async', return_value=object())

    reponse = client.post(reverse('accounts:eleves_masse'), {'matricules': ['LS-2026-01']})
    assert reponse.status_code == 200
    resultat, = reponse.context['resultats']
    compte, mot_de_passe = resultat['compte'], resultat['mot_de_passe']
    assert resultat['identifiant'] == 'LS-2026-01' and len(mot_de_passe) == 12
    assert compte.role == 'ELEVE' and compte.must_change_password is True
    assert list(compte.eleves_lies.all()) == [ecole['awa'].eleve]
    assert envoi.call_args.args[0] == '70 12 34 56'
    assert 'Identifiant: LS-2026-01' in envoi.call_args.args[1] and len(envoi.call_args.args[1]) <= 160

    # L'élève se connecte avec son matricule (saisi au dos de la carte scolaire) et arrive sur son portail
    client.logout()
    connexion = client.post(reverse('accounts:login'),
                            {'username': 'ls-2026-01', 'password': mot_de_passe})
    assert connexion.status_code == 302 and connexion.url == reverse('core:portail_eleve')

    # Le compte ne peut pas être créé deux fois
    client.force_login(ecole['directeur'])
    assert [f['matricule'] for f in parents_masse.eleves_sans_compte(ecole['etab'], ecole['annee'])] == ['LS-2026-02']


def test_eleve_sans_telephone_et_page_vide(client, ecole, mocker):
    envoi = mocker.patch('core.tasks.envoyer_sms_async', return_value=object())
    reponse = client.post(reverse('accounts:eleves_masse'), {'matricules': ['LS-2026-02']})
    assert reponse.status_code == 200 and 'resultats' in reponse.context
    assert envoi.call_count == 0, 'aucun SMS sans numéro de téléphone'
    compte = User.objects.get(email__iexact='LS-2026-02@eleve.invalid')
    assert compte.telephone == '' and compte.identifiant_connexion == 'LS-2026-02'
    # Reste un élève à équiper, puis plus aucun : la page le dit
    assert client.get(reverse('accounts:eleves_masse')).context['nb_sans_compte'] == 1
    client.post(reverse('accounts:eleves_masse'), {'matricules': ['LS-2026-01']})
    page = client.get(reverse('accounts:eleves_masse'))
    assert page.context['nb_sans_compte'] == 0 and 'Aucune année' not in page.content.decode()
    # Rien de coché : refus lisible, aucun compte créé
    reponse = client.post(reverse('accounts:eleves_masse'), {'matricules': []}, follow=True)
    assert 'Cochez au moins un élève.' in reponse.content.decode()


def test_identifiant_de_connexion_accepte_le_matricule_et_le_telephone(ecole):
    baker.make('accounts.User', email='LS-2026-05@eleve.invalid', username='LS-2026-05@eleve.invalid', role='ELEVE')
    assert parents_masse.email_depuis_identifiant(' LS-2026-05 ') == 'LS-2026-05@eleve.invalid'
    assert parents_masse.email_depuis_identifiant('(+226) 70-12-34-56') == '70123456@parent.invalid'
    assert parents_masse.email_depuis_identifiant('INCONNU-2026-99') == 'inconnu-2026-99', 'matricule inconnu : inchangé'
    assert parents_masse.email_depuis_identifiant('awa@ecole.bf') == 'awa@ecole.bf'
    compte = User.objects.get(email__iexact='LS-2026-05@eleve.invalid')
    assert parents_masse.identifiant_connexion(compte) == 'LS-2026-05'


def test_page_reservee_a_la_direction(client, ecole):
    client.force_login(baker.make('accounts.User', etablissement=ecole['etab'], role='SECRETAIRE',
                                  must_change_password=False))
    assert client.get(reverse('accounts:eleves_masse')).status_code == 302
