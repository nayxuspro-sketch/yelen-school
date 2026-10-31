"""Rappels d'expiration de la licence : bandeau administrateurs dès J-30, notification + SMS à la direction à J-15 et J-7.

Les paliers sont émis une seule fois par période de licence, sans planificateur (première page du jour ou contrôle
des licences), quel que soit le mode de contrôle (LICENSE_ENFORCEMENT).
"""
from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.models import Notification
from etablissements.models import Etablissement
from licences import rappels
from licences.models import Licence, LicenceAlert, StatutLicence, TypeLicence

BANDEAU = 'class="licence-rappel'


@pytest.fixture
def etab():
    return baker.make(Etablissement)


@pytest.fixture
def directeur(etab):
    return baker.make('accounts.User', etablissement=etab, role='DIRECTEUR', telephone='+22670000001',
                      email='directeur@yelen.test', must_change_password=False)


@pytest.fixture
def sms(mocker):
    mocker.patch('core.sms.get_sms_val', return_value=True)
    return mocker.patch('core.tasks.envoyer_sms_async')


def _licence(etab, jours):
    licence = Licence(etablissement=etab, type_licence=TypeLicence.PREMIUM, statut=StatutLicence.ACTIVE,
                      date_activation=timezone.now() - timedelta(days=300),
                      date_expiration=date.today() + timedelta(days=jours))
    licence.save()
    return licence


def _types(licence):
    return sorted(licence.alertes.values_list('type_alerte', flat=True))


@pytest.mark.django_db
class TestPaliers:
    def test_j20_alerte_j30_sans_notification(self, etab, directeur, sms):
        assert rappels.emettre_rappels(_licence(etab, 20)) == ['J-30']
        assert Notification.objects.count() == 0 and not sms.called

    def test_j15_notification_et_sms_au_directeur(self, etab, directeur, sms):
        licence = _licence(etab, 15)
        assert rappels.emettre_rappels(licence) == ['J-30', 'J-15']
        notification = Notification.objects.get(destinataire=directeur)
        assert notification.titre == "Licence : expire dans 15 jours"
        assert licence.date_expiration.strftime('%d/%m/%Y') in notification.message
        assert notification.lien == ''                      # le Directeur n'a pas accès aux pages Licences
        numero, texte = sms.call_args.args[:2]
        assert numero == '+22670000001' and len(texte) <= 160 and 'expire dans 15 jours' in texte
        alerte = licence.alertes.get(type_alerte='J-15')
        assert alerte.envoyee and alerte.destinataires == ['directeur@yelen.test']
        assert not licence.alertes.get(type_alerte='J-30').envoyee

    def test_un_seul_envoi_par_palier(self, etab, directeur, sms):
        licence = _licence(etab, 15)
        rappels.emettre_rappels(licence)
        assert rappels.emettre_rappels(licence) == []
        assert Notification.objects.count() == 1 and sms.call_count == 1

    def test_j7_nouveau_rappel_puis_j1_silencieux(self, etab, directeur, sms):
        licence = _licence(etab, 15)
        rappels.emettre_rappels(licence)
        Licence.objects.filter(pk=licence.pk).update(date_expiration=date.today() + timedelta(days=7))
        licence.refresh_from_db()
        assert rappels.emettre_rappels(licence) == ['J-7']
        assert Notification.objects.filter(titre="Licence : expire dans 7 jours").count() == 1
        Licence.objects.filter(pk=licence.pk).update(date_expiration=date.today() + timedelta(days=1))
        licence.refresh_from_db()
        assert rappels.emettre_rappels(licence) == ['J-1']
        assert Notification.objects.count() == 2 and sms.call_count == 2

    def test_sans_directeur_les_super_admin_sont_prevenus(self, etab, sms):
        super_admin = baker.make('accounts.User', etablissement=etab, role='SUPER_ADMIN', must_change_password=False)
        baker.make('accounts.User', etablissement=etab, role='SECRETAIRE', must_change_password=False)
        rappels.emettre_rappels(_licence(etab, 10))
        notification = Notification.objects.get()
        assert notification.destinataire == super_admin and notification.lien == reverse('licences:renouveler')

    def test_periode_renouvelee_declenche_de_nouveaux_rappels(self, etab, directeur, sms):
        licence = _licence(etab, 12)
        il_y_a_un_an = timezone.now() - timedelta(days=365)
        for type_alerte in ('J-30', 'J-15'):                # alertes de la période précédente
            LicenceAlert.objects.create(licence=licence, type_alerte=type_alerte, date_alerte=il_y_a_un_an)
        assert rappels.emettre_rappels(licence) == ['J-30', 'J-15']
        assert Notification.objects.count() == 1

    def test_licence_expiree_alertes_sans_notification(self, etab, directeur, sms):
        assert rappels.emettre_rappels(_licence(etab, -3)) == ['J-30', 'J-15', 'J-7', 'J-1']
        assert Notification.objects.count() == 0 and not sms.called


@pytest.mark.django_db
class TestBandeau:
    def _connecter(self, client, etab, **attrs):
        user = baker.make('accounts.User', etablissement=etab, must_change_password=False, **attrs)
        client.force_login(user)
        return user

    def test_directeur_voit_le_bandeau_sans_lien(self, client, etab):
        _licence(etab, 20)
        self._connecter(client, etab, role='DIRECTEUR')
        html = client.get('/').content.decode()
        assert BANDEAU in html and 'La licence expire dans 20 jours' in html
        assert reverse('licences:renouveler') not in html

    def test_super_admin_voit_le_lien_de_renouvellement(self, client, etab):
        _licence(etab, 5)
        self._connecter(client, etab, role='SUPER_ADMIN')
        html = client.get('/').content.decode()
        assert 'licence-rappel--urgent' in html and 'expire dans 5 jours' in html
        assert f'href="{reverse("licences:renouveler")}">Renouveler</a>' in html

    def test_licence_expiree(self, client, etab):
        licence = _licence(etab, -2)
        self._connecter(client, etab, role='DIRECTEUR')
        html = client.get('/').content.decode()
        assert f"Licence expirée le {licence.date_expiration.strftime('%d/%m/%Y')}" in html

    def test_rien_avant_j30_ni_pour_les_autres_roles(self, client, etab):
        _licence(etab, 31)
        self._connecter(client, etab, role='DIRECTEUR')
        assert BANDEAU not in client.get('/').content.decode()
        Licence.objects.update(date_expiration=date.today() + timedelta(days=10))
        assert BANDEAU in client.get('/').content.decode()
        client.logout()
        self._connecter(client, etab, role='SECRETAIRE')
        assert BANDEAU not in client.get('/').content.decode()

    def test_premiere_page_du_jour_emet_les_rappels(self, client, etab, directeur, sms, monkeypatch):
        monkeypatch.setattr(rappels, '_verifie_le', {})
        licence = _licence(etab, 9)
        self._connecter(client, etab, role='SECRETAIRE')        # n'importe quel utilisateur de l'établissement
        client.get('/')
        assert _types(licence) == ['J-15', 'J-30'] and Notification.objects.get().destinataire == directeur
        assert rappels._verifie_le[etab.pk] == date.today()
        client.get('/')
        assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_controle_des_licences_passe_par_les_rappels(etab, directeur, sms, settings):
    """Avec LICENSE_ENFORCEMENT=true, le middleware émet les mêmes paliers (plus de création d'alerte silencieuse)."""
    from licences.middleware import LicenceCheckMiddleware
    licence = _licence(etab, 7)
    LicenceCheckMiddleware(lambda request: None)._generer_alertes_expiration(licence)
    assert _types(licence) == ['J-15', 'J-30', 'J-7'] and Notification.objects.count() == 1


@pytest.mark.django_db
class TestConnexion:
    """Contrôle de licence à la connexion (accounts.views._check_licence_post_login)."""

    def _compte(self, etab, role):
        email = f'{role.lower()}@yelen.test'
        user = baker.make('accounts.User', username=email, email=email, etablissement=etab, role=role,
                          must_change_password=False)
        user.set_password('Secret-2026-test')
        user.save()
        return user

    def _connexion(self, client, user):
        return client.post(reverse('accounts:login'), {'username': user.username, 'password': 'Secret-2026-test'})

    def test_pas_de_toast_pour_les_administrateurs_qui_ont_le_bandeau(self, client, etab):
        _licence(etab, 12)
        reponse = self._connexion(client, self._compte(etab, 'DIRECTEUR'))
        html = client.get(reponse.url, follow=True).content.decode()
        assert BANDEAU in html and 'Attention : la licence de votre établissement' not in html

    def test_toast_conserve_pour_les_autres_roles(self, client, etab):
        _licence(etab, 12)
        reponse = self._connexion(client, self._compte(etab, 'SECRETAIRE'))
        html = client.get(reponse.url, follow=True).content.decode()
        assert BANDEAU not in html and 'Attention : la licence de votre établissement expire le' in html

    def test_licence_expiree_le_super_admin_entre_pour_renouveler(self, client, etab):
        _licence(etab, -1)
        reponse = self._connexion(client, self._compte(etab, 'SUPER_ADMIN'))
        assert reponse.status_code == 302 and reponse.url == reverse('licences:activer')
        assert client.get(reverse('licences:activer')).status_code == 200      # toujours connecté

    def test_licence_expiree_les_autres_sont_refuses(self, client, etab):
        _licence(etab, -1)
        reponse = self._connexion(client, self._compte(etab, 'DIRECTEUR'))
        assert reponse.status_code == 302 and reponse.url == reverse('accounts:login')
        assert client.get('/').status_code == 302                                # déconnecté
