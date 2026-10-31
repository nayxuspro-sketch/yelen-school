"""Compléments établissements (5.43.0) : fiche de configuration et pilotage du réseau.

Couvre les décisions de ``etablissements.views`` : rattachement du super-admin, mise à jour de la fiche,
statistiques d'en-tête, clôture du réseau aux seuls rôles SUPER_ADMIN / DIRECTEUR_RESEAU, création et
affectation d'un groupe, export consolidé XLSX.
"""
import pytest
from django.urls import reverse
from model_bakery import baker

from etablissements.models import Etablissement, GroupeEtablissements
from etablissements.views import etablissement_pilotable

pytestmark = pytest.mark.django_db


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement', nom='Lycée Laafi', code='LAAFI')


def _user(etab=None, **extra):
    return baker.make('accounts.User', must_change_password=False,
                      **({'etablissement': etab} if etab is not None else {}), **extra)


# ── Fiche de configuration ────────────────────────────────────────────────────────────────────

def test_fiche_affiche_les_stats_de_l_etablissement(client, etab):
    baker.make('inscriptions.Eleve', _quantity=3)
    baker.make('parametres.Classe', etablissement=etab, _quantity=2)
    client.force_login(_user(etab))
    reponse = client.get(reverse('etablissements:detail'))
    assert reponse.status_code == 200
    assert reponse.context['etablissement'] == etab
    assert reponse.context['stats'] == {'eleves': 3, 'personnel': 1, 'classes': 2}
    assert reponse.context['cycles_selected'] == etab.cycles


def test_fiche_sans_etablissement_explique_le_refus(client):
    client.force_login(_user(None))
    reponse = client.get(reverse('etablissements:detail'))
    assert reponse.status_code == 200
    assert 'error' in reponse.context and reponse.context['etablissement'] is None


def test_super_admin_sans_etablissement_reprend_le_premier(client, etab):
    client.force_login(_user(None, is_superuser=True))
    reponse = client.get(reverse('etablissements:detail'))
    assert reponse.context['etablissement'] == etab


def test_mise_a_jour_de_la_fiche(client, etab):
    client.force_login(_user(etab))
    donnees = {'nom': 'Lycée Laafi 2', 'code': 'LAAFI', 'adresse': 'Ouaga 2000', 'telephone': '70 00 00 00',
               'email': 'contact@laafi.bf', 'ville': 'Ouagadougou', 'pays': 'Burkina Faso',
               'cycles': ['PRIMAIRE', 'POST_PRIMAIRE']}
    reponse = client.post(reverse('etablissements:detail'), donnees)
    etab.refresh_from_db()
    assert reponse.status_code == 200
    assert etab.nom == 'Lycée Laafi 2' and etab.cycles == ['PRIMAIRE', 'POST_PRIMAIRE']
    assert reponse.context['success'] == "Configuration enregistrée avec succès."


def test_mise_a_jour_invalide_reste_sur_la_fiche(client, etab):
    client.force_login(_user(etab))
    reponse = client.post(reverse('etablissements:detail'), {'nom': '', 'code': ''})
    assert reponse.status_code == 200 and reponse.context['form'].errors


def test_super_admin_cree_et_se_rattache_a_l_etablissement(client):
    utilisateur = _user(None, is_superuser=True)
    client.force_login(utilisateur)
    donnees = {'nom': 'École Nongtaaba', 'code': 'NONGTAABA', 'adresse': 'Pabré', 'telephone': '70 11 11 11',
               'email': 'nongtaaba@lasafar.bf', 'ville': 'Ouagadougou', 'pays': 'Burkina Faso',
               'cycles': ['PRESCOLAIRE']}
    reponse = client.post(reverse('etablissements:detail'), donnees)
    cree = Etablissement.objects.get(code='NONGTAABA')
    utilisateur.refresh_from_db()
    assert reponse.status_code == 200 and cree.cycles == ['PRESCOLAIRE']
    assert utilisateur.etablissement_id == cree.pk


# ── Périmètre du reseau ──────────────────────────────────────────────────────────────────────

def test_pilotable_selon_role_et_groupe():
    groupe = baker.make(GroupeEtablissements)
    autre_groupe = baker.make(GroupeEtablissements)
    dedans = baker.make('etablissements.Etablissement', groupe=groupe)
    dehors = baker.make('etablissements.Etablissement', groupe=autre_groupe)
    super_admin = _user(role='SUPER_ADMIN')
    reseau = _user(role='DIRECTEUR_RESEAU', groupe=groupe)
    directeur = _user(dedans, role='DIRECTEUR')

    assert etablissement_pilotable(super_admin, str(dedans.pk)) == dedans
    assert etablissement_pilotable(super_admin, str(dehors.pk)) == dehors
    assert etablissement_pilotable(reseau, str(dedans.pk)) == dedans
    assert etablissement_pilotable(reseau, str(dehors.pk)) is None
    assert etablissement_pilotable(directeur, str(dedans.pk)) is None
    assert etablissement_pilotable(super_admin, 'pas-un-uuid') is None
    assert etablissement_pilotable(super_admin, None) is None
    assert etablissement_pilotable(reseau, str(baker.make('etablissements.Etablissement', groupe=None).pk)) is None


# ── Tableau de bord réseau ───────────────────────────────────────────────────────────────────

def test_dashboard_reseau_refuse_aux_autres_roles(client, etab):
    client.force_login(_user(etab, role='DIRECTEUR'))
    reponse = client.get(reverse('etablissements:reseau_dashboard'), follow=True)
    assert reponse.status_code == 200
    assert 'Accès réservé au Directeur Réseau.' in reponse.content.decode()


def test_dashboard_reseau_super_admin_consolide_tous_les_sites(client):
    groupe = baker.make(GroupeEtablissements, nom='Réseau Faso')
    for site in baker.make('etablissements.Etablissement', groupe=groupe, _quantity=2):
        baker.make('parametres.AnneeScolaire', etablissement=site, est_courante=True)
    client.force_login(_user(role='SUPER_ADMIN'))
    reponse = client.get(reverse('etablissements:reseau_dashboard'))
    assert reponse.status_code == 200
    assert len(reponse.context['lignes']) == 2
    assert reponse.context['totaux']['sites'] == 2
    assert list(reponse.context['groupes']) == [groupe]

    filtre = client.get(reverse('etablissements:reseau_dashboard'), {'groupe': str(groupe.pk)})
    assert len(filtre.context['lignes']) == 2 and filtre.context['groupe_filtre'] == groupe


def test_dashboard_reseau_directeur_sans_groupe_est_vide(client):
    client.force_login(_user(role='DIRECTEUR_RESEAU'))
    reponse = client.get(reverse('etablissements:reseau_dashboard'), follow=True)
    assert reponse.status_code == 200 and reponse.context['lignes'] == []


def test_dashboard_reseau_export_xlsx(client):
    groupe = baker.make(GroupeEtablissements)
    baker.make('etablissements.Etablissement', groupe=groupe)
    client.force_login(_user(role='SUPER_ADMIN'))
    reponse = client.get(reverse('etablissements:reseau_dashboard'), {'format': 'xlsx'})
    assert reponse.status_code == 200
    assert reponse['Content-Type'].startswith('application/vnd.openxmlformats')
    assert reponse.content[:2] == b'PK'


# ── Groupes ─────────────────────────────────────────────────────────────────────────────────

def test_liste_des_groupes_reservee_au_super_admin(client):
    baker.make(GroupeEtablissements, nom='Groupe A')
    baker.make('etablissements.Etablissement', groupe=None)
    client.force_login(_user(role='SUPER_ADMIN'))
    reponse = client.get(reverse('etablissements:groupe_list'))
    assert reponse.status_code == 200 and len(reponse.context['groupes']) == 1
    assert len(reponse.context['etablissements_sans_groupe']) == 1

    client.force_login(_user(role='DIRECTEUR_RESEAU'))
    assert client.get(reverse('etablissements:groupe_list')).status_code == 302


def test_creation_puis_modification_d_un_groupe(client):
    client.force_login(_user(role='SUPER_ADMIN'))
    client.post(reverse('etablissements:groupe_create'), {'nom': 'Réseau Laafi', 'code': 'R-LAAFI',
                                                          'description': '3 sites'})
    groupe = GroupeEtablissements.objects.get(code='R-LAAFI')
    assert groupe.nom == 'Réseau Laafi' and groupe.nb_etablissements == 0

    client.post(reverse('etablissements:groupe_edit', args=[groupe.pk]),
                {'nom': 'Réseau Laafi 2', 'code': 'R-LAAFI', 'description': ''})
    groupe.refresh_from_db()
    assert groupe.nom == 'Réseau Laafi 2' and groupe.description == ''


def test_groupe_sans_nom_ou_code_refuse(client):
    client.force_login(_user(role='SUPER_ADMIN'))
    reponse = client.post(reverse('etablissements:groupe_create'), {'nom': ' ', 'code': ''}, follow=True)
    assert GroupeEtablissements.objects.count() == 0
    assert 'Nom et code sont obligatoires.' in reponse.content.decode()


def test_affecter_un_etablissement_a_un_groupe(client):
    groupe = baker.make(GroupeEtablissements)
    site = baker.make('etablissements.Etablissement', groupe=None)
    client.force_login(_user(role='SUPER_ADMIN'))
    reponse = client.post(reverse('etablissements:groupe_affecter_etab', args=[groupe.pk]),
                          {'etablissement_pk': str(site.pk)})
    site.refresh_from_db()
    assert reponse.status_code == 302 and site.groupe == groupe
