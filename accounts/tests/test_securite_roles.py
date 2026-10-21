"""2FA obligatoire (Super Admin, Directeur), un seul Super Admin par établissement, session de caisse limitée."""
import pyotp
import pytest
from django.urls import reverse
from model_bakery import baker

from accounts.models import User
from etablissements.models import Etablissement

pytestmark = pytest.mark.django_db
MDP = 'MotDePasseSolide-2026'


@pytest.fixture
def etab():
    return baker.make(Etablissement)


def _utilisateur(etab, role, **extra):
    extra.setdefault('must_change_password', False)
    return baker.make(User, etablissement=etab, role=role, **extra)


# ── 1. Double authentification obligatoire ───────────────────────────────────

class TestDeuxFacteursObligatoires:
    @pytest.fixture(autouse=True)
    def _obligatoire(self, settings):
        settings.TWO_FACTOR_REQUIRED = True

    @pytest.mark.parametrize('role,extra', [('DIRECTEUR', {}), ('SUPER_ADMIN', {}), ('ENSEIGNANT', {'is_superuser': True})])
    def test_sans_totp_redirige_vers_activation(self, client, etab, role, extra):
        client.force_login(_utilisateur(etab, role, **extra))
        reponse = client.get(reverse('core:home'))
        assert reponse.status_code == 302
        assert reponse.url == reverse('accounts:totp_setup')

    def test_htmx_recoit_hx_redirect(self, client, etab):
        client.force_login(_utilisateur(etab, 'DIRECTEUR'))
        reponse = client.get(reverse('core:home'), HTTP_HX_REQUEST='true',
                             HTTP_HX_CURRENT_URL='http://testserver/accounts/profile/')
        assert reponse.status_code == 204
        assert reponse['HX-Redirect'] == reverse('accounts:totp_setup')

    def test_htmx_depuis_la_page_d_activation_sans_rechargement(self, client, etab):
        """Le badge de notifications de la page d'activation ne doit pas provoquer de boucle de rechargement."""
        client.force_login(_utilisateur(etab, 'DIRECTEUR'))
        reponse = client.get(reverse('core:notifications_badge'), HTTP_HX_REQUEST='true',
                             HTTP_HX_CURRENT_URL='http://testserver' + reverse('accounts:totp_setup'))
        assert reponse.status_code == 204
        assert 'HX-Redirect' not in reponse

    def test_activation_et_deconnexion_restent_accessibles(self, client, etab):
        client.force_login(_utilisateur(etab, 'DIRECTEUR'))
        reponse = client.get(reverse('accounts:totp_setup'))
        assert reponse.status_code == 200
        contenu = reponse.content.decode()
        assert 'obligatoire pour votre rôle' in contenu
        assert 'form-deconnexion' in contenu
        assert client.post(reverse('accounts:logout')).status_code == 302

    def test_changement_de_mot_de_passe_initial_prioritaire(self, client, etab):
        client.force_login(_utilisateur(etab, 'DIRECTEUR', must_change_password=True))
        assert client.get(reverse('core:home')).url == reverse('accounts:profile')

    def test_roles_non_concernes_et_totp_actif_passent(self, client, etab):
        client.force_login(_utilisateur(etab, 'COMPTABLE'))
        assert client.get(reverse('accounts:profile')).status_code == 200
        client.force_login(_utilisateur(etab, 'DIRECTEUR', totp_enabled=True, totp_secret=pyotp.random_base32()))
        assert client.get(reverse('accounts:profile')).status_code == 200

    def test_desactivation_refusee(self, client, etab):
        secret = pyotp.random_base32()
        directeur = _utilisateur(etab, 'DIRECTEUR', totp_enabled=True, totp_secret=secret)
        client.force_login(directeur)
        reponse = client.post(reverse('accounts:totp_disable'), {'code': pyotp.TOTP(secret).now()}, follow=True)
        directeur.refresh_from_db()
        assert directeur.totp_enabled is True
        assert 'ne peut pas être désactivée' in reponse.content.decode()
        assert 'totp_disable' not in reponse.content.decode()

    def test_reinitialisation_par_administrateur(self, client, etab):
        directeur = _utilisateur(etab, 'DIRECTEUR', totp_enabled=True, totp_secret=pyotp.random_base32())
        client.force_login(_utilisateur(etab, 'SUPER_ADMIN', totp_enabled=True, totp_secret=pyotp.random_base32()))
        url = reverse('accounts:user_set_password', args=[directeur.pk])
        assert 'reinitialiser_2fa' in client.get(url).content.decode()
        assert client.post(url, {'action': 'reinitialiser_2fa'}).status_code == 302
        directeur.refresh_from_db()
        assert directeur.totp_enabled is False and directeur.totp_secret == ''


def test_obligation_suspendue_par_reglage(client, etab, settings):
    settings.TWO_FACTOR_REQUIRED = False
    client.force_login(_utilisateur(etab, 'DIRECTEUR'))
    assert client.get(reverse('accounts:profile')).status_code == 200


# ── 2. Un seul Super Admin par établissement ─────────────────────────────────

class TestSuperAdminUnique:
    def _donnees(self, etab, role='SUPER_ADMIN', **extra):
        donnees = {'last_name': 'Ouedraogo', 'first_name': 'Awa', 'email': 'awa@ecole.bf', 'telephone': '',
                   'etablissement': str(etab.pk), 'role': role, 'password1': MDP, 'password2': MDP}
        donnees.update(extra)
        return donnees

    def test_creation_refusee_si_un_super_admin_existe(self, client, etab):
        existant = _utilisateur(etab, 'SUPER_ADMIN', first_name='Issa', last_name='Kabore')
        client.force_login(existant)
        reponse = client.post(reverse('accounts:user_create'), self._donnees(etab))
        assert reponse.status_code == 200
        assert 'Un seul Super Admin par établissement : Issa Kabore' in reponse.content.decode()
        assert not User.objects.filter(email='awa@ecole.bf').exists()

    def test_creation_acceptee_pour_un_autre_etablissement_ou_un_autre_role(self, client, etab):
        client.force_login(_utilisateur(etab, 'SUPER_ADMIN'))
        autre_etab = baker.make(Etablissement)
        assert client.post(reverse('accounts:user_create'), self._donnees(autre_etab)).status_code == 302
        assert client.post(reverse('accounts:user_create'),
                           self._donnees(etab, role='DIRECTEUR', email='dir@ecole.bf')).status_code == 302

    def test_promotion_refusee(self, client, etab):
        client.force_login(_utilisateur(etab, 'SUPER_ADMIN'))
        directeur = _utilisateur(etab, 'DIRECTEUR', email='dir@ecole.bf')
        donnees = {'last_name': directeur.last_name, 'first_name': directeur.first_name, 'email': directeur.email,
                   'telephone': '', 'etablissement': str(etab.pk), 'role': 'SUPER_ADMIN', 'is_active': 'on'}
        reponse = client.post(reverse('accounts:user_update', args=[directeur.pk]), donnees)
        assert reponse.status_code == 200
        assert 'Un seul Super Admin par établissement' in reponse.content.decode()
        directeur.refresh_from_db()
        assert directeur.role == 'DIRECTEUR'

    def test_super_admin_existant_peut_modifier_sa_fiche(self, client, etab):
        admin = _utilisateur(etab, 'SUPER_ADMIN', email='admin@ecole.bf')
        client.force_login(admin)
        donnees = {'last_name': 'Nouveau', 'first_name': 'Awa', 'email': admin.email,
                   'telephone': '', 'etablissement': str(etab.pk), 'role': 'SUPER_ADMIN', 'is_active': 'on'}
        assert client.post(reverse('accounts:user_update', args=[admin.pk]), donnees).status_code == 302

    def test_reactivation_refusee(self, client, etab):
        client.force_login(_utilisateur(etab, 'SUPER_ADMIN'))
        inactif = _utilisateur(etab, 'SUPER_ADMIN', is_active=False)
        client.post(reverse('accounts:user_toggle_active', args=[inactif.pk]))
        inactif.refresh_from_db()
        assert inactif.is_active is False

    def test_create_superuser_refuse_le_doublon(self, etab):
        _utilisateur(etab, 'SUPER_ADMIN')
        with pytest.raises(ValueError, match='Un seul Super Admin'):
            User.objects.create_superuser('x@ecole.bf', 'x@ecole.bf', MDP, etablissement=etab)
        # Compte technique sans établissement : hors règle.
        assert User.objects.create_superuser('tech@yelen.bf', 'tech@yelen.bf', MDP).role == 'SUPER_ADMIN'


# ── 3. Caisse : session limitée à l'inactivité ───────────────────────────────

class TestSessionCaisse:
    def _connecter(self, client, etab, role):
        utilisateur = _utilisateur(etab, role, email=f'{role.lower()}@ecole.bf')
        utilisateur.set_password(MDP)
        utilisateur.save()
        assert client.post(reverse('accounts:login'), {'username': utilisateur.email, 'password': MDP}).status_code == 302
        return utilisateur

    def test_comptable_expire_apres_quinze_minutes(self, client, etab, settings):
        settings.CAISSE_INACTIVITE_MINUTES = 15
        self._connecter(client, etab, 'COMPTABLE')
        assert client.session.get_expiry_age() == 900
        contenu = client.get(reverse('accounts:profile')).content.decode()
        assert 'js/inactivite' in contenu and 'data-secondes="900"' in contenu

    def test_autres_roles_inchanges(self, client, etab, settings):
        self._connecter(client, etab, 'SECRETAIRE')
        assert client.session.get_expiry_age() == settings.SESSION_COOKIE_AGE
        assert 'js/inactivite' not in client.get(reverse('accounts:profile')).content.decode()


# ── 4. Heure du serveur sur les écrans TOTP ──────────────────────────────────

def test_heure_serveur_affichee_sur_les_ecrans_totp(client, etab, settings):
    settings.TWO_FACTOR_REQUIRED = True
    secret = pyotp.random_base32()
    directeur = _utilisateur(etab, 'DIRECTEUR', email='dir@ecole.bf', totp_enabled=True, totp_secret=secret)
    directeur.set_password(MDP)
    directeur.save()
    assert client.post(reverse('accounts:login'), {'username': directeur.email, 'password': MDP}).url == reverse('accounts:login_2fa')
    for url in (reverse('accounts:login_2fa'),):
        contenu = client.get(url).content.decode()
        assert 'id="heure-serveur"' in contenu and 'js/heure_serveur' in contenu and 'data-fuseau="Africa/Ouagadougou"' in contenu
    client.force_login(_utilisateur(etab, 'DIRECTEUR', email='dir2@ecole.bf'))
    assert 'id="heure-serveur"' in client.get(reverse('accounts:totp_setup')).content.decode()
