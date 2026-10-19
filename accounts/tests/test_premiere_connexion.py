"""Compte créé sans mot de passe : l'utilisateur crée le sien à sa première connexion."""
import pytest
from django.urls import reverse
from model_bakery import baker

from accounts.models import User
from etablissements.models import Etablissement

MDP = 'MotDePasse!2026xyz'


@pytest.fixture
def etab():
    return baker.make(Etablissement)


def _creer_sans_mot_de_passe(client, etab, email='awa@ecole.bf'):
    client.force_login(baker.make(User, etablissement=etab, role='SUPER_ADMIN', must_change_password=False))
    donnees = {'last_name': 'Zongo', 'first_name': 'Awa', 'email': email, 'telephone': '',
               'role': 'SECRETAIRE', 'etablissement': etab.pk, 'password1': '', 'password2': ''}
    assert client.post(reverse('accounts:user_create'), donnees).status_code == 302
    client.logout()
    return User.objects.get(email=email)


@pytest.mark.django_db
class TestPremiereConnexion:
    def test_creation_sans_mot_de_passe(self, client, etab):
        user = _creer_sans_mot_de_passe(client, etab)
        assert not user.has_usable_password()

    def test_mot_de_passe_saisi_reste_pris_en_compte(self, client, etab):
        client.force_login(baker.make(User, etablissement=etab, role='SUPER_ADMIN', must_change_password=False))
        donnees = {'last_name': 'Zongo', 'first_name': 'Awa', 'email': 'awa@ecole.bf', 'telephone': '',
                   'role': 'SECRETAIRE', 'etablissement': etab.pk, 'password1': MDP, 'password2': ''}
        reponse = client.post(reverse('accounts:user_create'), donnees)
        assert reponse.status_code == 200 and 'ne correspondent pas' in reponse.content.decode()
        donnees['password2'] = MDP
        assert client.post(reverse('accounts:user_create'), donnees).status_code == 302
        assert User.objects.get(email='awa@ecole.bf').check_password(MDP)

    def test_parcours_complet(self, client, etab):
        user = _creer_sans_mot_de_passe(client, etab)

        # Identifiant seul → page de création du mot de passe
        reponse = client.post(reverse('accounts:login'), {'username': 'AWA@ecole.bf', 'password': ''})
        assert reponse.status_code == 302 and reponse.url == reverse('accounts:premiere_connexion')
        assert 'awa@ecole.bf' in client.get(reverse('accounts:premiere_connexion')).content.decode()

        # Confirmation différente → refus, mot de passe toujours absent
        reponse = client.post(reverse('accounts:premiere_connexion'), {'password1': MDP, 'password2': MDP + 'x'})
        assert reponse.status_code == 200 and 'ne correspondent pas' in reponse.content.decode()
        user.refresh_from_db()
        assert not user.has_usable_password()

        # Création → connecté, mot de passe utilisable
        reponse = client.post(reverse('accounts:premiere_connexion'), {'password1': MDP, 'password2': MDP})
        assert reponse.status_code == 302 and reponse.url == reverse('core:home')
        assert client.get(reverse('accounts:profile')).status_code == 200
        user.refresh_from_db()
        assert user.check_password(MDP) and not user.must_change_password

        # Ensuite : connexion classique, l'identifiant seul ne suffit plus
        client.logout()
        reponse = client.post(reverse('accounts:login'), {'username': 'awa@ecole.bf', 'password': ''})
        assert reponse.status_code == 200
        assert client.get(reverse('accounts:premiere_connexion')).status_code == 302
        reponse = client.post(reverse('accounts:login'), {'username': 'awa@ecole.bf', 'password': MDP})
        assert reponse.status_code == 302 and reponse.url == reverse('core:home')

    def test_page_inaccessible_sans_passage_par_la_connexion(self, client, etab):
        _creer_sans_mot_de_passe(client, etab)
        reponse = client.get(reverse('accounts:premiere_connexion'))
        assert reponse.status_code == 302 and reponse.url == reverse('accounts:login')

    def test_compte_avec_mot_de_passe_non_concerne(self, client, etab):
        user = baker.make(User, etablissement=etab, email='ali@ecole.bf')
        user.set_password(MDP)
        user.save()
        reponse = client.post(reverse('accounts:login'), {'username': 'ali@ecole.bf', 'password': ''})
        assert reponse.status_code == 200
        assert client.session.get('_premiere_connexion_pk') is None


@pytest.mark.django_db
class TestReinitialisationParAdmin:
    def test_super_admin_reinitialise_puis_premiere_connexion(self, client, etab):
        user = baker.make(User, etablissement=etab, email='ali@ecole.bf', role='SECRETAIRE')
        user.set_password(MDP)
        user.save()
        client.force_login(baker.make(User, etablissement=etab, role='SUPER_ADMIN', must_change_password=False))

        reponse = client.post(reverse('accounts:user_set_password', args=[user.pk]), {'action': 'reinitialiser'})
        assert reponse.status_code == 302 and reponse.url == reverse('accounts:user_list')
        user.refresh_from_db()
        assert not user.has_usable_password()
        assert 'Mot de passe à créer' in client.get(reverse('accounts:user_list')).content.decode()

        client.logout()
        reponse = client.post(reverse('accounts:login'), {'username': 'ali@ecole.bf', 'password': MDP})
        assert reponse.status_code == 302 and reponse.url == reverse('accounts:premiere_connexion')

    def test_directeur_autre_etablissement_refuse(self, client, etab):
        user = baker.make(User, etablissement=etab, email='ali@ecole.bf')
        user.set_password(MDP)
        user.save()
        client.force_login(baker.make(User, etablissement=baker.make(Etablissement), role='DIRECTEUR',
                                      must_change_password=False))
        client.post(reverse('accounts:user_set_password', args=[user.pk]), {'action': 'reinitialiser'})
        user.refresh_from_db()
        assert user.check_password(MDP)
