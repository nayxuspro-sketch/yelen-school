"""
Licence hors ligne v3 — jeton signé Ed25519 par l'éditeur, liaison au serveur.

- jeton : émission / vérification / altération
- mode strict (LICENCE_PUBLIC_KEY) : plus aucun repli HMAC
- activation par jeton : établissement, serveur, expiration contrôlés
- liaison serveur : copie sur une autre machine = licence inutilisable
  (est_active, middleware, boot check)
- page Activer : identifiants affichés, saisie réservée au Super Admin
- commande éditeur emettre_licence
"""
from datetime import date, timedelta
from io import StringIO

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from model_bakery import baker

from licences import boot_check
from licences.jeton import (
    JetonInvalide, charger_cle_publique, construire_payload, emettre_jeton, verifier_jeton,
)
from licences.models import Licence, LicenceAuditLog, StatutLicence, TypeLicence
from licences.services import activer_jeton

pytestmark = pytest.mark.django_db

SERVEUR = 'a' * 64
AUTRE_SERVEUR = 'b' * 64


@pytest.fixture
def cles(settings):
    """Paire Ed25519 : la publique dans les settings (école), la privée retournée (éditeur)."""
    priv = Ed25519PrivateKey.generate()
    settings.LICENCE_PUBLIC_KEY = priv.public_key().public_bytes_raw().hex()
    settings.LICENCE_PRIVATE_KEY = ''
    return priv


@pytest.fixture
def etab():
    return baker.make('etablissements.Etablissement', nom='Lycée Jeton', code='LJ')


@pytest.fixture
def serveur(monkeypatch, settings):
    monkeypatch.setenv('YELEN_HOST_ID', SERVEUR)
    settings.LICENCE_BINDING_ENABLED = True


@pytest.fixture(autouse=True)
def boot_propre():
    boot_check.reinitialiser_etat_boot()
    yield
    boot_check.reinitialiser_etat_boot()


def _jeton(priv, etab, *, empreinte=SERVEUR, jours=200, type_licence='PREMIUM',
           cle='YELEN-AAAA-BBBB-CCCC'):
    payload = construire_payload(
        cle=cle, type_licence=type_licence, etablissement_id=etab.pk,
        date_expiration=date.today() + timedelta(days=jours), empreinte_serveur=empreinte,
    )
    return emettre_jeton(payload, priv)


# ── Jeton ────────────────────────────────────────────────────────────────────

class TestJeton:
    def test_emission_puis_verification(self, cles, etab, settings):
        jeton = _jeton(cles, etab)
        assert jeton.startswith('YELEN3.')
        payload = verifier_jeton(jeton, charger_cle_publique(settings.LICENCE_PUBLIC_KEY))
        assert payload['cle'] == 'YELEN-AAAA-BBBB-CCCC'
        assert payload['etablissement'] == str(etab.pk)
        assert payload['empreinte_serveur'] == SERVEUR
        # Espaces et retours à la ligne (copier-coller) tolérés
        colle = jeton[:30] + '\n' + jeton[30:60] + ' ' + jeton[60:]
        assert verifier_jeton(colle, charger_cle_publique(settings.LICENCE_PUBLIC_KEY)) == payload

    def test_mauvaise_cle_ou_alteration_refusees(self, cles, etab, settings):
        jeton = _jeton(cles, etab)
        autre = charger_cle_publique(Ed25519PrivateKey.generate().public_key().public_bytes_raw().hex())
        with pytest.raises(JetonInvalide):
            verifier_jeton(jeton, autre)
        prefixe, payload_b64, sig = jeton.split('.')
        altere = '.'.join((prefixe, payload_b64[:-2] + ('AA' if payload_b64[-2:] != 'AA' else 'BB'), sig))
        with pytest.raises(JetonInvalide):
            verifier_jeton(altere, charger_cle_publique(settings.LICENCE_PUBLIC_KEY))
        with pytest.raises(JetonInvalide):
            verifier_jeton('YELEN-EB91-4349-78ED', charger_cle_publique(settings.LICENCE_PUBLIC_KEY))
        with pytest.raises(JetonInvalide):
            verifier_jeton(jeton, None)


# ── Mode strict ──────────────────────────────────────────────────────────────

class TestModeStrict:
    def test_hmac_seul_refuse_quand_cle_publique_configuree(self, cles, etab):
        lic = Licence(etablissement=etab, type_licence=TypeLicence.PREMIUM,
                      statut=StatutLicence.ACTIVE, date_expiration=date.today() + timedelta(days=100))
        lic.save()  # HMAC uniquement : forgeable avec le .env de l'école
        assert lic.verifier_signature() is False
        assert lic.est_active() is False

    def test_jeton_fait_foi_malgre_hmac_corrompu(self, cles, etab, serveur):
        lic = activer_jeton(_jeton(cles, etab), etab)
        Licence.objects.filter(pk=lic.pk).update(signature_hmac='0' * 64)
        lic.refresh_from_db()
        assert lic.verifier_signature() is True
        assert lic.est_active() is True

    def test_jeton_ne_couvre_pas_une_licence_modifiee(self, cles, etab, serveur):
        lic = activer_jeton(_jeton(cles, etab, type_licence='STARTER'), etab)
        Licence.objects.filter(pk=lic.pk).update(type_licence='PREMIUM')
        lic.refresh_from_db()
        assert lic.verifier_signature() is False
        Licence.objects.filter(pk=lic.pk).update(
            type_licence='STARTER', date_expiration=date.today() + timedelta(days=3000))
        lic.refresh_from_db()
        assert lic.verifier_signature() is False


# ── Activation ───────────────────────────────────────────────────────────────

class TestActivation:
    def test_cree_une_licence_active_et_journalise(self, cles, etab, serveur):
        lic = activer_jeton(_jeton(cles, etab), etab)
        assert lic.statut == StatutLicence.ACTIVE
        assert lic.type_licence == 'PREMIUM'
        assert lic.cle_licence == 'YELEN-AAAA-BBBB-CCCC'
        assert lic.empreinte_serveur == SERVEUR
        assert lic.jeton_signe.startswith('YELEN3.')
        assert lic.est_active() is True
        assert LicenceAuditLog.objects.filter(licence=lic, action='ACTIVATION').exists()

    def test_remplace_la_licence_existante(self, cles, etab, serveur):
        ancienne = Licence(etablissement=etab, type_licence=TypeLicence.STARTER,
                           statut=StatutLicence.EXPIREE, date_expiration=date.today() - timedelta(days=1))
        ancienne.save()
        lic = activer_jeton(_jeton(cles, etab, cle='YELEN-1111-2222-3333'), etab)
        assert lic.pk == ancienne.pk
        assert Licence.objects.filter(etablissement=etab).count() == 1
        assert lic.cle_licence == 'YELEN-1111-2222-3333'
        assert lic.est_active() is True

    def test_autre_etablissement_refuse(self, cles, etab, serveur):
        autre = baker.make('etablissements.Etablissement')
        with pytest.raises(JetonInvalide, match='autre établissement'):
            activer_jeton(_jeton(cles, autre), etab)
        assert not Licence.objects.filter(etablissement=etab).exists()

    def test_autre_serveur_refuse(self, cles, etab, serveur):
        with pytest.raises(JetonInvalide, match='autre serveur'):
            activer_jeton(_jeton(cles, etab, empreinte=AUTRE_SERVEUR), etab)

    def test_jeton_expire_refuse(self, cles, etab, serveur):
        with pytest.raises(JetonInvalide, match='expiré'):
            activer_jeton(_jeton(cles, etab, jours=-1), etab)

    def test_sans_empreinte_licence_non_liee(self, cles, etab, serveur):
        lic = activer_jeton(_jeton(cles, etab, empreinte=''), etab)
        assert lic.empreinte_serveur == ''
        assert lic.liee_a_ce_serveur() is True


# ── Liaison au serveur : copie inutilisable ──────────────────────────────────

class TestLiaisonServeur:
    def test_copie_sur_autre_machine(self, cles, etab, serveur, monkeypatch):
        lic = activer_jeton(_jeton(cles, etab), etab)
        assert lic.est_active() is True
        monkeypatch.setenv('YELEN_HOST_ID', AUTRE_SERVEUR)  # même dossier, autre serveur
        assert lic.liee_a_ce_serveur() is False
        assert lic.est_active() is False
        resultat = boot_check.run_boot_check()
        assert lic.cle_licence in resultat['binding_invalid']
        assert LicenceAuditLog.objects.filter(licence=lic, action='TENTATIVE_FRAUDE').exists()

    def test_sans_liaison_activee_la_licence_reste_valide(self, cles, etab, serveur, settings, monkeypatch):
        lic = activer_jeton(_jeton(cles, etab), etab)
        settings.LICENCE_BINDING_ENABLED = False
        monkeypatch.setenv('YELEN_HOST_ID', AUTRE_SERVEUR)
        assert lic.est_active() is True

    def test_middleware_redirige_vers_activation(self, cles, etab, serveur, settings, monkeypatch, client):
        lic = activer_jeton(_jeton(cles, etab), etab)
        settings.LICENSE_ENFORCEMENT = True
        settings.MIDDLEWARE = list(settings.MIDDLEWARE) + ['licences.middleware.LicenceCheckMiddleware']
        user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR',
                          is_superuser=False, must_change_password=False)
        client.force_login(user)
        assert client.get(reverse('core:home')).status_code == 200
        monkeypatch.setenv('YELEN_HOST_ID', AUTRE_SERVEUR)
        cache.delete(f'licence_check_{lic.pk}')  # résultat positif mis en cache 5 min
        reponse = client.get(reverse('core:home'))
        assert reponse.status_code == 302
        assert reponse.url == reverse('licences:activer')
        assert LicenceAuditLog.objects.filter(licence=lic, action='TENTATIVE_FRAUDE').exists()


# ── Page Activer ─────────────────────────────────────────────────────────────

class TestPageActiver:
    def _super_admin(self, etab):
        return baker.make('accounts.User', etablissement=etab, role='SUPER_ADMIN',
                          is_superuser=False, must_change_password=False)

    def test_affiche_les_identifiants(self, cles, etab, serveur, client):
        client.force_login(self._super_admin(etab))
        reponse = client.get(reverse('licences:activer'))
        assert reponse.status_code == 200
        html = reponse.content.decode()
        assert str(etab.pk) in html
        assert SERVEUR in html
        assert 'name="jeton"' in html
        assert "Aucune licence n" in html

    def test_super_admin_active_par_code(self, cles, etab, serveur, client):
        client.force_login(self._super_admin(etab))
        reponse = client.post(reverse('licences:activer'), {'jeton': _jeton(cles, etab)})
        assert reponse.status_code == 302
        assert reponse.url == reverse('licences:statut')
        lic = Licence.objects.get(etablissement=etab)
        assert lic.est_active() is True
        page = client.get(reverse('licences:activer')).content.decode()
        assert 'Licence active' in page
        assert 'YELEN-AAAA-BBBB-CCCC' in page

    def test_code_invalide_message_sans_licence(self, cles, etab, serveur, client):
        client.force_login(self._super_admin(etab))
        reponse = client.post(reverse('licences:activer'), {'jeton': 'YELEN3.abc.def'}, follow=True)
        assert 'Activation refusée' in reponse.content.decode()
        assert not Licence.objects.filter(etablissement=etab).exists()

    def test_saisie_reservee_au_super_admin(self, cles, etab, serveur, client):
        user = baker.make('accounts.User', etablissement=etab, role='DIRECTEUR',
                          is_superuser=False, must_change_password=False)
        client.force_login(user)
        page = client.get(reverse('licences:activer'))
        assert page.status_code == 200
        assert 'name="jeton"' not in page.content.decode()
        assert client.post(reverse('licences:activer'), {'jeton': _jeton(cles, etab)}).status_code == 403
        assert not Licence.objects.filter(etablissement=etab).exists()

    def test_blocage_boot_leve_apres_activation(self, cles, etab, serveur, settings, client):
        settings.LICENSE_ENFORCEMENT = True
        settings.MIDDLEWARE = list(settings.MIDDLEWARE) + ['licences.middleware.LicenceCheckMiddleware']
        boot_check._etat_boot['fait'] = True
        boot_check._etat_boot['blocage'] = 'test'
        client.force_login(self._super_admin(etab))
        assert client.get(reverse('core:home')).status_code == 503
        assert client.get(reverse('licences:activer')).status_code == 200
        client.post(reverse('licences:activer'), {'jeton': _jeton(cles, etab)})
        assert boot_check.blocage_boot() is None
        assert client.get(reverse('core:home')).status_code == 200


# ── Commande éditeur ─────────────────────────────────────────────────────────

class TestCommandeEmettreLicence:
    def test_emet_un_code_activable(self, cles, etab, serveur, settings):
        settings.LICENCE_PRIVATE_KEY = cles.private_bytes_raw().hex()
        sortie = StringIO()
        call_command(
            'emettre_licence', '--etablissement', str(etab.pk), '--type', 'STANDARD',
            '--expiration', (date.today() + timedelta(days=365)).isoformat(),
            '--empreinte', SERVEUR, stdout=sortie,
        )
        texte = sortie.getvalue()
        jeton = next(ligne for ligne in texte.splitlines() if ligne.startswith('YELEN3.'))
        settings.LICENCE_PRIVATE_KEY = ''
        lic = activer_jeton(jeton, etab)
        assert lic.type_licence == 'STANDARD'
        assert lic.cle_licence.startswith('YELEN-') and len(lic.cle_licence) == 20
        assert lic.est_active() is True

    def test_refuse_sans_cle_privee(self, cles, etab, settings):
        from django.core.management.base import CommandError
        settings.LICENCE_PRIVATE_KEY = ''
        with pytest.raises(CommandError, match='LICENCE_PRIVATE_KEY'):
            call_command('emettre_licence', '--etablissement', str(etab.pk), '--type', 'PREMIUM',
                         '--expiration', (date.today() + timedelta(days=30)).isoformat())
