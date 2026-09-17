# licences/tests/test_signature_integrity.py
# ================================================================
# Tests d'intégrité cryptographique de la signature HMAC (format v2).
#
# Garanties :
#   - v2 signe statut, établissement, date d'activation ET expiration
#     → toute falsification locale (statut, dates, transfert) casse la
#       signature.
#   - Compatibilité arrière : une signature v1 (légacy) toujours valide
#     reste acceptée → aucun déploiement existant n'est cassé.
#   - save() ré-signe en v2 (transition automatique).
import hashlib
import hmac
from datetime import date, timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from model_bakery import baker


def _sign(message: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def _msg_v1(licence) -> str:
    return f"{licence.cle_licence}:{licence.type_licence}:{licence.date_expiration.isoformat()}"


def _msg_v2(licence) -> str:
    """Message v2 — délégué au modèle (source de vérité unique)."""
    return licence._message_signature_v2()


@pytest.fixture
def licence():
    etab = baker.make('etablissements.Etablissement')
    return baker.make(
        'licences.Licence',
        etablissement=etab,
        type_licence='STANDARD',
        statut='ACTIVE',
        date_activation=timezone.now(),
        date_expiration=date.today() + timedelta(days=30),
    )


@pytest.mark.django_db
class TestSignatureV2:
    def test_nouvelle_licence_signee_v2(self, licence):
        """Une licence créée aujourd'hui porte une signature v2 valide."""
        assert licence.verifier_signature() is True
        # Et la signature stockée correspond bien au message v2
        assert licence.signature_hmac == _sign(_msg_v2(licence))

    def test_est_active_avec_signature_valide(self, licence):
        assert licence.est_active() is True

    def test_tampering_statut_invalide(self, licence):
        """Réactiver localement (REVOQUEE -> ACTIVE) sans ré-signer casse la v2."""
        # Simulation d'un attaquant qui passe REVOQUEE -> ACTIVE en direct DB
        licence2 = baker.make(
            'licences.Licence',
            etablissement=baker.make('etablissements.Etablissement'),
            type_licence='STANDARD',
            statut='REVOQUEE',
            date_activation=timezone.now(),
            date_expiration=date.today() + timedelta(days=30),
        )
        # L'attaquant "réactive" sans passer par save() (pas de ré-signature)
        type(licence2).objects.filter(pk=licence2.pk).update(statut='ACTIVE')
        licence2.refresh_from_db()
        assert licence2.statut == 'ACTIVE'
        assert licence2.verifier_signature() is False
        assert licence2.est_active() is False

    def test_tampering_date_expiration_invalide(self, licence):
        """Allonger la date d'expiration en direct DB casse la v2."""
        nouveau = licence.date_expiration + timedelta(days=365)
        type(licence).objects.filter(pk=licence.pk).update(date_expiration=nouveau)
        licence.refresh_from_db()
        assert licence.verifier_signature() is False
        assert licence.est_active() is False

    def test_tampering_type_invalide(self, licence):
        """Passer Starter -> Réseau en direct DB casse la v2."""
        type(licence).objects.filter(pk=licence.pk).update(type_licence='RESEAU')
        licence.refresh_from_db()
        assert licence.verifier_signature() is False

    def test_transfert_etablissement_invalide(self, licence):
        """Attacher la licence à un autre établissement casse la v2."""
        autre_etab = baker.make('etablissements.Etablissement')
        type(licence).objects.filter(pk=licence.pk).update(
            etablissement=autre_etab,
        )
        licence.refresh_from_db()
        assert licence.verifier_signature() is False

    def test_revoquer_officiel_repasse_par_save(self, licence):
        """La révocation par l'API officielle (save()) reste signée."""
        licence.revoquer(raison='non-paiement')
        assert licence.statut == 'REVOQUEE'
        assert licence.verifier_signature() is True
        assert licence.est_active() is False

    def test_renouveler_officiel_repasse_par_save(self, licence):
        """Le renouvellement officiel (save()) reste signé et actif."""
        licence.renouveler(duree_jours=365)
        assert licence.verifier_signature() is True
        assert licence.est_active() is True


@pytest.mark.django_db
class TestCompatV1:
    def _installer_v1(self, licence):
        """Simule une licence d'un déploiement ancien (signature v1)."""
        type(licence).objects.filter(pk=licence.pk).update(
            signature_hmac=_sign(_msg_v1(licence)),
        )
        licence.refresh_from_db()

    def test_signature_v1_toujours_valide(self, licence):
        """Rétrocompatibilité : v1 valide → licence acceptée."""
        self._installer_v1(licence)
        assert licence.verifier_signature() is True
        assert licence.est_active() is True

    def test_signature_v1_tampee_date_invalide(self, licence):
        """Même en v1, changer la date casse la signature."""
        self._installer_v1(licence)
        nouveau = licence.date_expiration + timedelta(days=365)
        type(licence).objects.filter(pk=licence.pk).update(date_expiration=nouveau)
        licence.refresh_from_db()
        assert licence.verifier_signature() is False

    def test_save_resigne_en_v2(self, licence):
        """Tout save() sur une licence v1 la fait migrer en v2."""
        self._installer_v1(licence)
        assert licence.signature_hmac == _sign(_msg_v1(licence))

        licence.save()
        licence.refresh_from_db()
        assert licence.signature_hmac == _sign(_msg_v2(licence))
        assert licence.verifier_signature() is True

    def test_boot_check_pas_de_fausse_revocation(self, licence):
        """Une v1 saine ne doit PAS être révoquée par le boot check."""
        self._installer_v1(licence)
        from licences.boot_check import run_boot_check
        result = run_boot_check()
        assert licence.cle_licence not in result['tampering']
