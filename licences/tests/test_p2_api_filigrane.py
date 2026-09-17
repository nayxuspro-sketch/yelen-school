"""
Tests P2 — LicenceAuditLog centralisation + filigrane PDF + IsLicenseActive API
"""

import pytest
from datetime import date, timedelta
from django.test import RequestFactory, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, force_authenticate, APIRequestFactory
from rest_framework.authtoken.models import Token

from licences.models import Licence, LicenceAuditLog, StatutLicence, TypeLicence
from licences.api import IsLicenseActiveView, LicenceAuditLogCentralView, LicenceAuditLogVerifyView
from licences.pdf_utils import get_licence_info_for_pdf, inject_licence_filigrane_context

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def etablissement(db):
    from model_bakery import baker
    return baker.make('etablissements.Etablissement', nom="École P2 Test")


@pytest.fixture
def licence_active(etablissement):
    lic = Licence(
        etablissement=etablissement,
        type_licence=TypeLicence.PREMIUM,
        statut=StatutLicence.ACTIVE,
        date_expiration=date.today() + timedelta(days=200),
    )
    lic.save()
    return lic


@pytest.fixture
def user_staff(etablissement):
    u = User.objects.create_user(username='staffp2', email='staffp2@example.com', password='test12345678', is_staff=True)
    u.etablissement = etablissement
    u.save()
    return u


@pytest.fixture
def user_regular(etablissement):
    u = User.objects.create_user(username='regularp2', email='regularp2@example.com', password='test12345678')
    u.etablissement = etablissement
    u.save()
    return u


# ── IsLicenseActive API ──────────────────────────────────────────────────────

class TestIsLicenseActiveAPI:
    def test_api_active_returns_licence_info(self, etablissement, licence_active, user_regular):
        factory = APIRequestFactory()
        request = factory.get('/api/licences/active/')
        force_authenticate(request, user=user_regular)
        view = IsLicenseActiveView.as_view()
        response = view(request)
        assert response.status_code == 200
        assert response.data['active'] is True
        assert response.data['cle_licence'] == licence_active.cle_licence
        assert response.data['type_licence'] == 'PREMIUM'
        assert 'jours_restants' in response.data
        assert 'signature_valide' in response.data

    def test_api_active_strict_403_si_inactive(self, etablissement, user_regular):
        # Pas de licence
        factory = APIRequestFactory()
        request = factory.get('/api/licences/active/?strict=true')
        force_authenticate(request, user=user_regular)
        view = IsLicenseActiveView.as_view()
        response = view(request)
        assert response.status_code == 404  # pas de licence = 404 même en strict

        # Licence expirée
        lic = Licence(
            etablissement=etablissement,
            type_licence=TypeLicence.STARTER,
            statut=StatutLicence.EXPIREE,
            date_expiration=date.today() - timedelta(days=1),
        )
        lic.save()
        request = factory.get('/api/licences/active/?strict=true')
        force_authenticate(request, user=user_regular)
        response = view(request)
        assert response.status_code == 403
        assert response.data['active'] is False

    def test_api_via_token_auth(self, etablissement, licence_active, user_regular):
        client = APIClient()
        token = Token.objects.create(user=user_regular)
        client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        resp = client.get('/api/licences/active/')
        assert resp.status_code == 200
        assert resp.data['active'] is True

    def test_licence_status_view_session(self, etablissement, licence_active, user_regular):
        from licences.api import LicenceStatusView
        factory = APIRequestFactory()
        request = factory.get('/licences/api/status/')
        force_authenticate(request, user=user_regular)
        view = LicenceStatusView.as_view()
        response = view(request)
        assert response.status_code == 200
        assert response.data['active'] is True


# ── LicenceAuditLog centralisation ───────────────────────────────────────────

class TestAuditLogCentralisation:
    def test_audit_log_created_on_boot_check(self, etablissement, licence_active):
        # Créer un log via save() initial (allowed)
        log = LicenceAuditLog(
            licence=licence_active,
            action='VERIFICATION',
            description='Test centralisation',
            acteur_systeme=True,
        )
        log.save()
        assert log.hash_actuel != ''
        assert log.verifier_chaine() is True

    def test_central_view_staff_only(self, etablissement, licence_active, user_regular, user_staff):
        factory = APIRequestFactory()

        # Regular user → 403
        request = factory.get('/licences/api/audit/')
        force_authenticate(request, user=user_regular)
        view = LicenceAuditLogCentralView.as_view()
        response = view(request)
        assert response.status_code == 403

        # Staff → 200
        LicenceAuditLog(
            licence=licence_active,
            action='CREATION',
            description='Creation test',
            acteur_systeme=True,
        ).save()
        request = factory.get('/licences/api/audit/')
        force_authenticate(request, user=user_staff)
        response = view(request)
        assert response.status_code == 200
        assert 'logs' in response.data
        assert 'stats' in response.data
        assert response.data['pagination']['total'] >= 1

    def test_central_view_filter(self, etablissement, licence_active, user_staff):
        LicenceAuditLog(licence=licence_active, action='ACTIVATION', description='Act', acteur_systeme=True).save()
        LicenceAuditLog(licence=licence_active, action='REVOCATION', description='Rev', acteur_systeme=True).save()

        factory = APIRequestFactory()
        request = factory.get('/licences/api/audit/?action=ACTIVATION')
        force_authenticate(request, user=user_staff)
        view = LicenceAuditLogCentralView.as_view()
        response = view(request)
        assert response.status_code == 200
        # Tous les logs retournés doivent être ACTIVATION
        for log in response.data['logs']:
            assert log['action'] == 'ACTIVATION'

    def test_verify_chain(self, etablissement, licence_active, user_staff):
        # Créer chaîne - chaque save est initial, donc allowed
        LicenceAuditLog(licence=licence_active, action='CREATION', description='1', acteur_systeme=True).save()
        LicenceAuditLog(licence=licence_active, action='ACTIVATION', description='2', acteur_systeme=True).save()
        LicenceAuditLog(licence=licence_active, action='VERIFICATION', description='3', acteur_systeme=True).save()

        factory = APIRequestFactory()
        request = factory.post('/licences/api/audit/verify/', {'licence_id': str(licence_active.id)}, format='json')
        force_authenticate(request, user=user_staff)
        view = LicenceAuditLogVerifyView.as_view()
        response = view(request)
        assert response.status_code == 200
        assert response.data['ok'] is True
        assert response.data['chaine_intacte'] is True
        assert response.data['total'] >= 3

    def test_verify_chain_detect_tampering(self, etablissement, licence_active, user_staff):
        l1 = LicenceAuditLog(licence=licence_active, action='CREATION', description='1', acteur_systeme=True)
        l1.save()
        l2 = LicenceAuditLog(licence=licence_active, action='ACTIVATION', description='2', acteur_systeme=True)
        l2.save()

        # Tamper : modifier description sans recalculer hash (via update pour bypass save)
        LicenceAuditLog.objects.filter(pk=l2.pk).update(description='TAMPERED')

        factory = APIRequestFactory()
        request = factory.post('/licences/api/audit/verify/', {'licence_id': str(licence_active.id)}, format='json')
        force_authenticate(request, user=user_staff)
        view = LicenceAuditLogVerifyView.as_view()
        response = view(request)
        assert response.status_code == 200
        assert response.data['ok'] is False
        assert len(response.data['invalides']) >= 1


# ── Filigrane PDF ────────────────────────────────────────────────────────────

class TestFiligranePDF:
    def test_get_licence_info_for_pdf(self, etablissement, licence_active, user_regular):
        info = get_licence_info_for_pdf(user_regular, etablissement)
        assert info is not None
        assert info['type'] == 'PREMIUM'
        assert info['cle_licence'] == licence_active.cle_licence
        assert info['etablissement_nom'] == etablissement.nom
        assert 'jours_restants' in info

    def test_inject_filigrane_context(self, etablissement, licence_active, user_regular):
        ctx = {'foo': 'bar'}
        ctx = inject_licence_filigrane_context(ctx, user_regular, etablissement)
        assert 'licence_info' in ctx
        assert ctx['licence_info']['type'] == 'PREMIUM'

    def test_template_filigrane_exists(self):
        from pathlib import Path
        p = Path('documents/templates/documents/pdf/partials/filigrane_licence.html')
        assert p.exists()
        content = p.read_text()
        assert 'licence_info' in content
        assert 'filigrane' in content.lower()

    def test_all_pdf_templates_include_filigrane(self):
        from pathlib import Path
        pdf_templates = list(Path('documents/templates/documents/pdf').glob('*.html'))
        assert len(pdf_templates) >= 5
        for tpl in pdf_templates:
            if tpl.name == 'partials':
                continue
            if 'partials' in str(tpl):
                continue
            content = tpl.read_text()
            # Ignorer le partial lui-même
            if tpl.name == 'filigrane_licence.html':
                continue
            assert 'filigrane_licence' in content, f"{tpl} n'inclut pas filigrane"

        # Pour pedagogie, bulletin_base.html doit contenir filigrane, et les enfants en héritent
        base_path = Path('pedagogie/templates/pedagogie/pdf/bulletin_base.html')
        assert base_path.exists()
        base_content = base_path.read_text()
        assert 'filigrane_licence' in base_content, "bulletin_base.html doit inclure filigrane"

        bulletin_templates = list(Path('pedagogie/templates/pedagogie/pdf').glob('*.html'))
        for tpl in bulletin_templates:
            if tpl.name == 'bulletin_base.html':
                continue
            content = tpl.read_text()
            # Si template extends bulletin_base, filigrane vient de l'héritage
            if 'extends' in content and 'bulletin_base' in content:
                # OK via héritage, mais on vérifie quand même que base l'a
                continue
            assert 'filigrane_licence' in content, f"{tpl} n'inclut pas filigrane"
