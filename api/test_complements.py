"""Compléments API (5.43.0) : jetons, cloisonnement RBAC de bout en bout, licences.

``api/tests.py`` couvre l'obtention d'un jeton et le cloisonnement principal ; ce module couvre la
rotation/révocation des jetons, chaque endpoint « données élève » (y compris ses filtres), les refus de
``api.permissions`` et les deux variantes de ``/api/licences/active/``.
"""
import datetime as dt

import pytest
from django.urls import reverse
from model_bakery import baker
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory

from api.permissions import EleveScopeAccess, IsStaffRole
from api.views import eleves_visibles, get_eleve_scope

pytestmark = pytest.mark.django_db


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement')


@pytest.fixture
def annee(etab):
    return baker.make('parametres.AnneeScolaire', etablissement=etab, est_courante=True)


def _staff(etab, role='ENSEIGNANT'):
    return baker.make('accounts.User', etablissement=etab, role=role, must_change_password=False)


def _auth(user):
    token, _ = Token.objects.get_or_create(user=user)
    return {'HTTP_AUTHORIZATION': f'Token {token.key}'}


def _inscrire(etab, annee, nom='KABORÉ'):
    eleve = baker.make('inscriptions.Eleve', nom=nom)
    classe = baker.make('parametres.Classe', etablissement=etab)
    inscription = baker.make('inscriptions.Inscription', eleve=eleve, annee_scolaire=annee, classe=classe)
    return eleve, inscription


# ── Jetons ────────────────────────────────────────────────────────────────────────────────────

def test_token_exige_les_deux_champs(client):
    reponse = client.post(reverse('api:obtenir_token'), {'username': 'x'}, content_type='application/json')
    assert reponse.status_code == 400 and 'requis' in reponse.json()['erreur']


def test_token_refuse_des_identifiants_invalides(client, etab):
    _staff(etab)
    reponse = client.post(reverse('api:obtenir_token'),
                          {'username': 'inconnu', 'password': 'mauvais'}, content_type='application/json')
    assert reponse.status_code == 401 and reponse.json()['erreur'] == 'Identifiants invalides.'


def test_rotation_du_token_invalide_l_ancien(client, etab):
    """L'API s'authentifie par adresse e-mail (comme l'écran de connexion), champ « username ». """
    utilisateur = _staff(etab, role='DIRECTEUR')
    utilisateur.email = 'direction@laafi.bf'
    utilisateur.set_password('MotDePasse2026!')
    utilisateur.save(update_fields=['password', 'email'])
    connexion = client.post(reverse('api:obtenir_token'),
                            {'username': 'DIRECTION@laafi.bf', 'password': 'MotDePasse2026!'},
                            content_type='application/json')
    ancien = connexion.json()['token']

    rotation = client.post(reverse('api:renouveler_token'), HTTP_AUTHORIZATION=f'Token {ancien}')
    nouveau = rotation.json()['token']
    assert rotation.status_code == 200 and nouveau != ancien
    assert not Token.objects.filter(key=ancien).exists()
    assert client.get(reverse('api:annees_list'), HTTP_AUTHORIZATION=f'Token {ancien}').status_code == 401
    assert client.get(reverse('api:annees_list'), HTTP_AUTHORIZATION=f'Token {nouveau}').status_code == 200


def test_revocation_du_token(client, etab):
    utilisateur = _staff(etab)
    entetes = _auth(utilisateur)
    assert client.delete(reverse('api:revoquer_token'), **entetes).status_code == 204
    assert client.get(reverse('api:annees_list'), **entetes).status_code == 401


# ── Années et périodes ───────────────────────────────────────────────────────────────────────

def test_annees_et_periodes_sont_cloisonnees_par_etablissement(client, etab, annee):
    autre = baker.make('etablissements.Etablissement')
    annee_autre = baker.make('parametres.AnneeScolaire', etablissement=autre)
    periode = baker.make('parametres.PeriodeEvaluation', annee_scolaire=annee, numero=1)
    entetes = _auth(_staff(etab))

    annees = client.get(reverse('api:annees_list'), **entetes).json()
    assert [a['id'] for a in annees] == [str(annee.pk)]
    periodes = client.get(reverse('api:annee_periodes', args=[annee.pk]), **entetes)
    assert [p['id'] for p in periodes.json()] == [str(periode.pk)]
    assert client.get(reverse('api:annee_periodes', args=[annee_autre.pk]), **entetes).status_code == 404


def test_annees_vues_par_un_super_admin(client, etab, annee):
    baker.make('parametres.AnneeScolaire', etablissement=baker.make('etablissements.Etablissement'))
    reponse = client.get(reverse('api:annees_list'), **_auth(_staff(etab, role='SUPER_ADMIN')))
    assert len(reponse.json()) == 2


# ── Données élève ───────────────────────────────────────────────────────────────────────────

def test_un_enseignant_ne_voit_que_les_eleves_de_son_etablissement(client, etab, annee):
    dedans, _ = _inscrire(etab, annee, nom='OUÉDRAOGO')
    dehors, _ = _inscrire(baker.make('etablissements.Etablissement'), baker.make('parametres.AnneeScolaire'), 'SAWADOGO')
    entetes = _auth(_staff(etab))

    liste = client.get(reverse('api:eleves_list'), **entetes).json()
    assert [e['id'] for e in liste] == [str(dedans.pk)]
    assert client.get(reverse('api:eleve_detail', args=[dehors.pk]), **entetes).status_code == 404
    filtree = client.get(reverse('api:eleves_list'), {'nom': 'OUÉD'}, **entetes).json()
    assert [e['id'] for e in filtree] == [str(dedans.pk)]
    assert client.get(reverse('api:eleves_list'), {'matricule': 'ZZZ'}, **entetes).json() == []


def test_un_parent_ne_voit_que_ses_enfants(client, etab, annee):
    enfant, _ = _inscrire(etab, annee)
    autre, _ = _inscrire(etab, annee, nom='ZONGO')
    parent = _staff(etab, role='PARENT')
    parent.eleves_lies.add(enfant)
    entetes = _auth(parent)

    assert [e['id'] for e in client.get(reverse('api:eleves_list'), **entetes).json()] == [str(enfant.pk)]
    assert client.get(reverse('api:eleve_detail', args=[enfant.pk]), **entetes).status_code == 200
    assert client.get(reverse('api:eleve_detail', args=[autre.pk]), **entetes).status_code == 404


def test_les_sous_ressources_d_un_eleve_repondent(client, etab, annee):
    eleve, inscription = _inscrire(etab, annee)
    trimestre = baker.make('pedagogie.Trimestre', annee_scolaire=annee, numero=1)
    baker.make('pedagogie.MoyenneGenerale', inscription=inscription, trimestre=trimestre, moyenne=12)
    rubrique = baker.make('parametres.RubriquePaiement', etablissement=etab)
    baker.make('finances.Paiement', inscription=inscription, rubrique=rubrique, montant=15000)
    entetes = _auth(_staff(etab, role='COMPTABLE'))

    inscriptions = client.get(reverse('api:eleve_inscriptions', args=[eleve.pk]), **entetes)
    assert [i['id'] for i in inscriptions.json()] == [str(inscription.pk)]
    moyennes = client.get(reverse('api:eleve_moyennes', args=[eleve.pk]), **entetes)
    assert len(moyennes.json()) == 1
    assert client.get(reverse('api:eleve_moyennes', args=[eleve.pk]), {'annee': str(annee.pk)}, **entetes).json()
    assert client.get(reverse('api:eleve_moyennes', args=[eleve.pk]),
                      {'annee': str(annee.pk)}, **entetes).status_code == 200
    paiements = client.get(reverse('api:eleve_paiements', args=[eleve.pk]), **entetes)
    assert len(paiements.json()) == 1
    # Aucune présence ni bulletin saisi : listes vides, jamais d'erreur
    assert client.get(reverse('api:eleve_presences', args=[eleve.pk]), **entetes).json() == []
    assert client.get(reverse('api:eleve_bulletins', args=[eleve.pk]), **entetes).json() == []

    appel = baker.make('presences.Appel', classe=inscription.classe, matiere=None,
                       date=dt.date(2026, 10, 15))
    baker.make('presences.Presence', inscription=inscription, appel=appel, statut='ABSENT')
    presences = client.get(reverse('api:eleve_presences', args=[eleve.pk]), **entetes).json()
    assert len(presences) == 1 and presences[0]['statut'] == 'ABSENT' and presences[0]['matiere'] is None

    baker.make('bulletins.Bulletin', inscription=inscription, trimestre=trimestre, est_publie=True)
    bulletins = client.get(reverse('api:eleve_bulletins', args=[eleve.pk]), **entetes).json()
    assert len(bulletins) == 1 and bulletins[0]['moyenne'] == '12.00'


def test_eleves_visibles_et_scope_selon_le_role(etab, annee):
    eleve, _ = _inscrire(etab, annee)
    super_admin = _staff(etab, role='SUPER_ADMIN')
    sans_etablissement = baker.make('accounts.User', etablissement=None, role='ENSEIGNANT',
                                    must_change_password=False)
    assert list(eleves_visibles(super_admin)) == [eleve]
    assert list(eleves_visibles(sans_etablissement)) == []
    assert get_eleve_scope(sans_etablissement, eleve.pk) is None


# ── Permissions ─────────────────────────────────────────────────────────────────────────────

class _Requete:
    def __init__(self, user):
        self.user = user


def test_is_staff_role_refuse_anonymes_et_familles(etab):
    permission = IsStaffRole()
    assert permission.has_permission(_Requete(None), None) is False
    from django.contrib.auth.models import AnonymousUser
    assert permission.has_permission(_Requete(AnonymousUser()), None) is False
    assert permission.has_permission(_Requete(_staff(etab)), None) is True
    assert permission.has_permission(_Requete(_staff(etab, role='PARENT')), None) is False
    assert permission.has_permission(_Requete(_staff(etab, role='ELEVE')), None) is False
    assert permission.has_permission(_Requete(_staff(etab, role='SUPER_ADMIN')), None) is True


def test_eleve_scope_access_refuse_une_famille_sans_eleve_ratache(etab):
    permission = EleveScopeAccess()
    assert permission.has_permission(_Requete(None), None) is False
    assert permission.has_permission(_Requete(_staff(etab, role='PARENT')), None) is False
    parent = _staff(etab, role='PARENT')
    parent.eleves_lies.add(baker.make('inscriptions.Eleve'))
    assert permission.has_permission(_Requete(parent), None) is True
    assert permission.has_permission(_Requete(_staff(etab, role='SECRETAIRE')), None) is True


# ── Licences ────────────────────────────────────────────────────────────────────────────────

def test_licence_absente_puis_inactive(client, etab):
    entetes = _auth(_staff(etab))
    absente = client.get(reverse('api:licences_active'), **entetes)
    assert absente.status_code == 404 and absente.json()['statut'] == 'ABSENTE'

    baker.make('licences.Licence', etablissement=etab, statut='EN_ATTENTE',
               date_expiration=dt.date.today() + dt.timedelta(days=30))
    inactive = client.get(reverse('api:licences_active'), **entetes)
    assert inactive.status_code == 200 and inactive.json()['active'] is False
    stricte = client.get(reverse('api:licences_active'), {'strict': 'true'}, **entetes)
    assert stricte.status_code == 403 and stricte.json()['active'] is False


def test_fabrique_de_requete_reste_compatible():
    """Les permissions lisent ``request.user`` : une requête DRF vide ne doit pas les faire échouer."""
    requete = APIRequestFactory().get('/api/eleves/')
    requete.user = None
    assert IsStaffRole().has_permission(requete, None) is False
