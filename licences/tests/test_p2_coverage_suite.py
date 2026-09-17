"""
Tests couverture P2 (suite) — heartbeat (révocation/expiration/réponses),
binding (create_activation), boot_check (_verifier_licence, strict),
decorators (helpers + décorateurs enforcement ON), pdf_utils.

Objectif : couverture ≥ 80 % sur l'app `licences`.
"""
import json
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory
from django.utils import timezone
from model_bakery import baker

from licences.models import Licence, LicenceAuditLog, StatutLicence, TypeLicence

pytestmark = pytest.mark.django_db


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _licence(niveau=TypeLicence.PREMIUM, jours=100, statut=StatutLicence.ACTIVE, etab=None):
    etab = etab or baker.make('etablissements.Etablissement')
    lic = Licence(
        etablissement=etab,
        type_licence=niveau,
        statut=statut,
        date_expiration=date.today() + timedelta(days=jours),
    )
    lic.save()
    return lic


def _hb_response(lic, statut='ACTIVE', ts='2026-09-17T10:00:00Z'):
    """Construit une réponse heartbeat correctement signée HMAC."""
    import hashlib
    import hmac as _hmac
    message = f"{lic.cle_licence}:{statut}:{ts}".encode('utf-8')
    sig = _hmac.new(lic._get_heartbeat_signing_key(), message, hashlib.sha256).hexdigest()
    return {'cle_licence': lic.cle_licence, 'statut': statut, 'timestamp': ts, 'hmac': sig, 'message': 'srv'}


class _FakeResp:
    def __init__(self, data):
        self._b = json.dumps(data).encode('utf-8')

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _patch_url(settings):
    settings.LICENCE_HEARTBEAT_URL = 'https://editeur.example/heartbeat'


# ────────────────────────────────────────────────────────────────────
# heartbeat.py
# ────────────────────────────────────────────────────────────────────

class TestHeartbeat:

    def test_success(self, settings):
        from licences.heartbeat import send_heartbeat
        _patch_url(settings)
        lic = _licence()
        with patch('licences.heartbeat.urllib_request.urlopen', return_value=_FakeResp(_hb_response(lic))):
            res = send_heartbeat(lic)
        assert res['ok'] is True and res['action'] == 'success'
        lic.refresh_from_db()
        assert lic.heartbeat_failures == 0
        assert lic.dernier_heartbeat is not None
        assert lic.bail_offline_expire_le > timezone.now()

    def test_revoked_remotely(self, settings):
        from licences.heartbeat import send_heartbeat
        _patch_url(settings)
        lic = _licence()
        with patch('licences.heartbeat.urllib_request.urlopen',
                   return_value=_FakeResp(_hb_response(lic, 'REVOQUEE'))):
            res = send_heartbeat(lic)
        assert res['action'] == 'revoked' and res['ok'] is False
        lic.refresh_from_db()
        assert lic.statut == StatutLicence.REVOQUEE
        assert LicenceAuditLog.objects.filter(licence=lic, action='REVOCATION').exists()

    def test_expired_remotely(self, settings):
        from licences.heartbeat import send_heartbeat
        _patch_url(settings)
        lic = _licence()
        with patch('licences.heartbeat.urllib_request.urlopen',
                   return_value=_FakeResp(_hb_response(lic, 'EXPIREE'))):
            res = send_heartbeat(lic)
        assert res['action'] == 'expired'
        lic.refresh_from_db()
        assert lic.statut == StatutLicence.EXPIREE

    def test_invalid_signature(self, settings):
        from licences.heartbeat import send_heartbeat
        _patch_url(settings)
        lic = _licence()
        bad = _hb_response(lic)
        bad['hmac'] = 'deadbeef' * 8
        with patch('licences.heartbeat.urllib_request.urlopen', return_value=_FakeResp(bad)):
            res = send_heartbeat(lic)
        assert res['action'] == 'failure' and res['ok'] is False
        lic.refresh_from_db()
        assert lic.heartbeat_failures == 1

    def test_network_failure_then_bail_expired(self, settings):
        from licences.heartbeat import send_heartbeat
        _patch_url(settings)
        lic = _licence()
        with patch('licences.heartbeat.urllib_request.urlopen', side_effect=URLError('down')):
            res = send_heartbeat(lic)
            assert res['action'] == 'failure'
            # Force un bail déjà expiré → prochain échec = bail_expired
            Licence.objects.filter(pk=lic.pk).update(
                bail_offline_expire_le=timezone.now() - timedelta(days=1))
            lic.refresh_from_db()
            res2 = send_heartbeat(lic)
        assert res2['action'] == 'bail_expired' and res2['bail_jours_restants'] == 0

    def test_unexpected_error(self, settings):
        from licences.heartbeat import send_heartbeat
        _patch_url(settings)
        lic = _licence()
        with patch('licences.heartbeat.urllib_request.urlopen', side_effect=ValueError('boom')):
            res = send_heartbeat(lic)
        assert res['action'] == 'error' and res['ok'] is False

    def test_check_all_heartbeats(self, settings):
        from licences.heartbeat import check_all_heartbeats
        _patch_url(settings)
        l1 = _licence()
        l2 = _licence()
        l3 = _licence()
        responses = {
            l1.cle_licence: _FakeResp(_hb_response(l1)),
            l2.cle_licence: _FakeResp(_hb_response(l2, 'REVOQUEE')),
        }

        def fake_urlopen(req, timeout=10):
            key = req.get_header('X-licence-key')
            if key == l3.cle_licence:
                raise ValueError('boom')
            return responses[key]

        with patch('licences.heartbeat.urllib_request.urlopen', side_effect=fake_urlopen):
            res = check_all_heartbeats()
        assert res['total'] >= 3 and res['sent'] >= 3
        assert res['success'] >= 1 and res['revoked'] >= 1
        assert res['failures'] >= 1 and len(res['errors']) >= 1

    def test_check_all_skips_when_not_required(self, settings):
        from licences.heartbeat import check_all_heartbeats
        _patch_url(settings)
        lic = _licence()
        Licence.objects.filter(pk=lic.pk).update(dernier_heartbeat=timezone.now())
        with patch('licences.heartbeat.urllib_request.urlopen') as m:
            res = check_all_heartbeats()
        assert res['sent'] == 0
        m.assert_not_called()

    def test_load_public_key_variants(self, settings):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from licences.heartbeat import _load_public_key
        settings.LICENCE_PUBLIC_KEY = ''
        assert _load_public_key() is None
        raw = Ed25519PrivateKey.generate().public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        settings.LICENCE_PUBLIC_KEY = raw.hex()
        assert _load_public_key() is not None
        settings.LICENCE_PUBLIC_KEY = '!!invalide!!'
        assert _load_public_key() is None

    def test_verify_response_ed25519(self, settings):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        priv = Ed25519PrivateKey.generate()
        settings.LICENCE_PUBLIC_KEY = priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
        lic = _licence()
        data = _hb_response(lic)
        msg = f"{lic.cle_licence}:ACTIVE:{data['timestamp']}".encode()
        data['ed25519'] = priv.sign(msg).hex()
        assert lic.verify_heartbeat_response(data) is True
        data['ed25519'] = Ed25519PrivateKey.generate().sign(msg).hex()
        assert lic.verify_heartbeat_response(data) is False
        # Mauvaise clé licence
        assert lic.verify_heartbeat_response({'cle_licence': 'AUTRE'}) is False


# ────────────────────────────────────────────────────────────────────
# binding.py
# ────────────────────────────────────────────────────────────────────

class TestBinding:

    def test_create_activation_with_request(self):
        from licences.binding import create_activation_for_licence
        lic = _licence()
        rf = RequestFactory()
        req = rf.get('/', HTTP_X_FORWARDED_FOR='10.1.2.3, 192.168.0.1', HTTP_USER_AGENT='UA-test')
        act = create_activation_for_licence(lic, request=req)
        assert act.pk and act.est_active
        assert act.ip_address == '10.1.2.3'
        assert act.user_agent == 'UA-test'
        assert act.verify_fingerprint() is True

    def test_create_activation_remote_addr_and_offline(self):
        from licences.binding import create_activation_for_licence
        lic = _licence()
        req = RequestFactory().get('/', REMOTE_ADDR='127.0.0.9')
        act = create_activation_for_licence(lic, request=req, mode='OFFLINE')
        assert act.ip_address == '127.0.0.9' and act.mode_activation == 'OFFLINE'

    def test_collect_functions_resilient(self):
        from licences import binding
        with patch('licences.binding.uuid.getnode', side_effect=RuntimeError):
            assert binding.get_mac_address() == ''
        with patch('licences.binding.socket.gethostname', side_effect=RuntimeError):
            assert binding.get_hostname() == ''
        with patch('licences.binding.platform.processor', side_effect=RuntimeError), \
             patch('os.path.exists', return_value=False):
            assert binding.get_cpu_id() == ''


# ────────────────────────────────────────────────────────────────────
# boot_check.py
# ────────────────────────────────────────────────────────────────────

class TestBootCheck:

    def test_tampering_revokes(self):
        from licences.boot_check import run_boot_check
        lic = _licence()
        Licence.objects.filter(pk=lic.pk).update(signature_hmac='0' * 64, signature_ed25519='')
        res = run_boot_check()
        assert lic.cle_licence in res['tampering'] and res['ok'] is False
        lic.refresh_from_db()
        assert lic.statut == StatutLicence.REVOQUEE

    def test_expired_updates_status(self):
        from licences.boot_check import run_boot_check
        lic = _licence(jours=10)
        # Date passée sans passer par save() (qui recalcule la signature avec la date)
        past = date.today() - timedelta(days=1)
        lic.date_expiration = past
        lic.signature_hmac = lic.generer_signature() if hasattr(lic, 'generer_signature') else lic.signature_hmac
        Licence.objects.filter(pk=lic.pk).update(date_expiration=past, signature_hmac=lic.signature_hmac,
                                                 signature_ed25519='')
        res = run_boot_check()
        lic.refresh_from_db()
        assert lic.statut in (StatutLicence.EXPIREE, StatutLicence.REVOQUEE)
        assert res['ok'] is False

    def test_bail_expired_detected(self):
        from licences.boot_check import run_boot_check
        lic = _licence()
        Licence.objects.filter(pk=lic.pk).update(bail_offline_expire_le=timezone.now() - timedelta(days=2))
        res = run_boot_check()
        assert lic.cle_licence in res['bail_expired']

    def test_binding_invalid_detected(self, settings):
        from licences.binding import create_activation_for_licence
        from licences.boot_check import run_boot_check
        from licences.models import LicenceActivation
        settings.LICENCE_BINDING_ENABLED = True
        lic = _licence()
        act = create_activation_for_licence(lic)
        LicenceActivation.objects.filter(pk=act.pk).update(hostname='machine-pirate')
        res = run_boot_check()
        assert any(s.startswith(lic.cle_licence) for s in res['binding_invalid'])

    def test_strict_raises_when_enforced(self, settings):
        from licences.boot_check import run_boot_check
        settings.LICENSE_ENFORCEMENT = True
        settings.LICENCE_ANTITAMPER_ENABLED = True
        lic = _licence()
        Licence.objects.filter(pk=lic.pk).update(bail_offline_expire_le=timezone.now() - timedelta(days=2))
        with patch('licences.boot_check._check_antitamper', return_value={'ok': True, 'issues': []}):
            with pytest.raises(RuntimeError):
                run_boot_check(strict=True)

    def test_strict_antitamper_failure_raises(self, settings):
        from licences.boot_check import run_boot_check
        settings.LICENSE_ENFORCEMENT = True
        settings.LICENCE_ANTITAMPER_ENABLED = True
        with patch('licences.boot_check._check_antitamper', return_value={'ok': False, 'issues': ['x']}):
            with pytest.raises(RuntimeError):
                run_boot_check(strict=True)
            # Non strict : pas d'exception, juste erreurs
            res = run_boot_check(strict=False)
            assert res['ok'] is False and any('ANTITAMPER' in e for e in res['errors'])

    def test_db_error_handled(self):
        from licences.boot_check import run_boot_check
        with patch('licences.models.Licence.objects.only', side_effect=Exception('no such table licences')):
            res = run_boot_check()
        assert res['errors']

    def test_check_licences_command_strict_and_json(self, settings):
        from django.core.management import call_command
        from io import StringIO
        _licence()
        out = StringIO()
        call_command('check_licences', '--json', stdout=out)
        data = json.loads(out.getvalue())
        assert 'ok' in data
        settings.LICENSE_ENFORCEMENT = True
        settings.LICENCE_ANTITAMPER_ENABLED = True
        with patch('licences.boot_check._check_antitamper', return_value={'ok': False, 'issues': ['x']}):
            with pytest.raises(SystemExit):
                call_command('check_licences', '--strict', stdout=StringIO(), stderr=StringIO())

    def test_check_licences_command_heartbeat(self, settings):
        from django.core.management import call_command
        from io import StringIO
        _patch_url(settings)
        lic = _licence()
        with patch('licences.heartbeat.urllib_request.urlopen', return_value=_FakeResp(_hb_response(lic))):
            call_command('check_licences', '--heartbeat', stdout=StringIO())
        lic.refresh_from_db()
        assert lic.dernier_heartbeat is not None


# ────────────────────────────────────────────────────────────────────
# decorators.py
# ────────────────────────────────────────────────────────────────────

@pytest.fixture
def enforce(settings):
    settings.LICENSE_ENFORCEMENT = True


def _user(niveau=None, etab=True, jours=100):
    e = baker.make('etablissements.Etablissement') if etab else None
    user = baker.make('accounts.User', etablissement=e, role='DIRECTEUR', is_superuser=False)
    lic = _licence(niveau, jours=jours, etab=e) if (niveau and e) else None
    return user, lic


class TestDecoratorsHelpers:

    def test_helpers_enforcement_off(self, settings):
        from licences import decorators as d
        settings.LICENSE_ENFORCEMENT = False
        user, _ = _user()
        assert d.has_feature(user, 'ia_predictive') is True
        assert len(d.get_features_disponibles(user)) > 10
        assert d.user_has_feature(user, 'inscriptions') is True

    def test_helpers_enforcement_on(self, enforce):
        from licences import decorators as d
        u_none, _ = _user(etab=False)
        assert d.has_feature(u_none, 'inscriptions') is False
        assert d.get_features_disponibles(u_none) == []
        assert d.get_niveau_licence(u_none) is None
        assert d.get_licence_info(u_none) is None

        u_nolic, _ = _user()
        assert d.has_feature(u_nolic, 'inscriptions') is False
        assert d.get_features_disponibles(u_nolic) == []
        assert d.get_niveau_licence(u_nolic) is None
        assert d.get_licence_info(u_nolic) is None

        u_std, lic = _user(TypeLicence.STANDARD)
        assert d.has_feature(u_std, 'cursus_scolaire') is True
        assert d.has_feature(u_std, 'ia_predictive') is False
        assert 'cursus_scolaire' in d.get_features_disponibles(u_std)
        assert d.get_niveau_licence(u_std) == 'STANDARD'
        info = d.get_licence_info(u_std)
        assert info['type'] == 'STANDARD' and info['est_active'] is True

        # Licence non active → get_licence_active None
        Licence.objects.filter(pk=lic.pk).update(statut=StatutLicence.REVOQUEE)
        etab = type(u_std.etablissement).objects.get(pk=u_std.etablissement.pk)
        assert d.get_licence_active(etab) is None


class TestRequiresLicenceFeature:

    def _view(self, **kw):
        from licences.decorators import requires_licence_feature

        @requires_licence_feature('ia_predictive', **kw)
        def v(request):
            return HttpResponse('ok')
        return v

    def _req(self, user):
        from django.contrib.messages.storage.fallback import FallbackStorage
        req = RequestFactory().get('/x/')
        req.user = user
        req.session = {}
        req._messages = FallbackStorage(req)
        return req

    def test_off_passthrough(self, settings):
        settings.LICENSE_ENFORCEMENT = False
        user, _ = _user()
        assert self._view()(self._req(user)).status_code == 200

    def test_no_etab_redirect(self, enforce):
        user, _ = _user(etab=False)
        resp = self._view()(self._req(user))
        assert resp.status_code == 302 and '/licences/mon-abonnement/' in resp['Location']

    def test_no_licence_api_mode(self, enforce):
        user, _ = _user()
        resp = self._view(api_mode=True)(self._req(user))
        assert isinstance(resp, JsonResponse) and resp.status_code == 403
        assert json.loads(resp.content)['upgrade_required'] is True

    def test_insufficient_level_raise(self, enforce):
        user, _ = _user(TypeLicence.STARTER)
        with pytest.raises(PermissionDenied):
            self._view(raise_exception=True)(self._req(user))

    def test_insufficient_level_api_details(self, enforce):
        user, _ = _user(TypeLicence.STARTER)
        resp = self._view(api_mode=True)(self._req(user))
        body = json.loads(resp.content)
        assert body['current_licence'] == 'STARTER' and 'PREMIUM' in body['required_levels']

    def test_granted(self, enforce):
        user, _ = _user(TypeLicence.PREMIUM)
        assert self._view()(self._req(user)).status_code == 200


class TestCheckLicenceValidityAndMixin:

    def _req(self, user, path='/x/'):
        from django.contrib.messages.storage.fallback import FallbackStorage
        req = RequestFactory().get(path)
        req.user = user
        req.session = {}
        req._messages = FallbackStorage(req)
        return req

    def test_check_licence_validity(self, enforce, settings):
        from licences.decorators import check_licence_validity

        @check_licence_validity
        def v(request):
            return HttpResponse('ok')

        settings.LICENSE_ENFORCEMENT = False
        user, _ = _user()
        assert v(self._req(user)).status_code == 200
        settings.LICENSE_ENFORCEMENT = True
        u0, _ = _user(etab=False)
        assert v(self._req(u0)).status_code == 302
        assert v(self._req(user)).status_code == 302  # pas de licence
        u_ok, _ = _user(TypeLicence.STARTER)
        assert v(self._req(u_ok)).status_code == 200

    def test_mixin(self, enforce, settings):
        from django.contrib.auth.models import AnonymousUser
        from django.views import View
        from licences.decorators import LicenceFeatureMixin

        class V(LicenceFeatureMixin, View):
            required_feature = 'ia_predictive'

            def get(self, request):
                return HttpResponse('ok')

        class VNoFeature(LicenceFeatureMixin, View):
            required_feature = None

        with pytest.raises(ValueError):
            VNoFeature.as_view()(self._req(_user()[0]))

        settings.LICENSE_ENFORCEMENT = False
        assert V.as_view()(self._req(_user()[0])).status_code == 200
        settings.LICENSE_ENFORCEMENT = True

        anon = self._req(AnonymousUser())
        assert V.as_view()(anon).status_code == 302
        assert V.as_view()(self._req(_user(etab=False)[0])).status_code == 302
        assert V.as_view()(self._req(_user()[0])).status_code == 302
        assert V.as_view()(self._req(_user(TypeLicence.STARTER)[0])).status_code == 302
        assert V.as_view()(self._req(_user(TypeLicence.PREMIUM)[0])).status_code == 200

        class VRaise(V):
            raise_exception = True
        with pytest.raises(PermissionDenied):
            VRaise.as_view()(self._req(_user(TypeLicence.STARTER)[0]))

    def test_cache_by_licence(self):
        from django.core.cache import cache
        from licences.decorators import cache_by_licence
        calls = []

        @cache_by_licence(timeout=60)
        def v(request):
            calls.append(1)
            return HttpResponse('cached')

        cache.clear()
        user, _ = _user(TypeLicence.STANDARD)
        req = self._req(user)
        v(req)
        v(req)
        assert len(calls) == 1
        cache.clear()


# ────────────────────────────────────────────────────────────────────
# pdf_utils.py
# ────────────────────────────────────────────────────────────────────

class TestPdfUtils:

    def test_info_via_user(self):
        from licences.pdf_utils import get_licence_info_for_pdf, inject_licence_filigrane_context
        user, lic = _user(TypeLicence.STANDARD)
        info = get_licence_info_for_pdf(user)
        assert info['cle_licence'] == lic.cle_licence and info['signature_valide'] is True
        ctx = inject_licence_filigrane_context({}, user)
        assert ctx['licence_info']['etablissement_nom'] == user.etablissement.nom

    def test_info_via_etab_and_missing(self):
        from licences.pdf_utils import get_licence_info_for_pdf, inject_licence_filigrane_context
        user, lic = _user(TypeLicence.PREMIUM)
        assert get_licence_info_for_pdf(user, etablissement=user.etablissement)['type'] == 'PREMIUM'
        etab_sans = baker.make('etablissements.Etablissement')
        assert get_licence_info_for_pdf(user, etablissement=etab_sans) is None
        u_nolic, _ = _user()
        assert get_licence_info_for_pdf(u_nolic) is None
        assert 'licence_info' not in inject_licence_filigrane_context({}, u_nolic)
        u_noetab, _ = _user(etab=False)
        assert get_licence_info_for_pdf(u_noetab) is None
