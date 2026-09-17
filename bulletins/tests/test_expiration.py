"""
Tests S3 — expiration des liens publics bulletins.
"""
import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from model_bakery import baker


@pytest.mark.django_db
class TestBulletinLienExpiration:
    """S3a — bulletin_parent_consulter doit bloquer si token expiré."""

    def test_token_expire_bloque_affichage(self, client):
        bulletin = baker.make(
            'bulletins.Bulletin',
            token_signature='test-token-expire-1234567890abcdef',
            token_expire_le=timezone.now() - timedelta(days=1),
            est_publie=True,
        )
        url = reverse('bulletins:bulletin_parent_consulter', kwargs={'token': bulletin.token_signature})
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "n'est plus valide" in content or "plus valide" in content
        # Le template d'erreur ne doit pas afficher les données sensibles

    def test_token_valide_affiche_bulletin(self, client):
        bulletin = baker.make(
            'bulletins.Bulletin',
            token_signature='test-token-valide-1234567890abcdef',
            token_expire_le=timezone.now() + timedelta(days=1),
            est_publie=True,
        )
        url = reverse('bulletins:bulletin_parent_consulter', kwargs={'token': bulletin.token_signature})
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "n'est plus valide" not in content

    def test_token_valide_mais_non_publie(self, client):
        bulletin = baker.make(
            'bulletins.Bulletin',
            token_signature='test-token-nonpublie-1234567890ab',
            token_expire_le=timezone.now() + timedelta(days=1),
            est_publie=False,
        )
        url = reverse('bulletins:bulletin_parent_consulter', kwargs={'token': bulletin.token_signature})
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "pas encore disponible" in content

    def test_token_expire_prioritaire_sur_non_publie(self, client):
        """Si token expiré, on affiche 'plus valide' même si non publié (sécurité)."""
        bulletin = baker.make(
            'bulletins.Bulletin',
            token_signature='test-token-expire-nonpublie-1234',
            token_expire_le=timezone.now() - timedelta(days=1),
            est_publie=False,
        )
        url = reverse('bulletins:bulletin_parent_consulter', kwargs={'token': bulletin.token_signature})
        resp = client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "n'est plus valide" in content or "plus valide" in content

    def test_signer_bloque_si_expire(self, client):
        bulletin = baker.make(
            'bulletins.Bulletin',
            token_signature='test-token-signer-expire-123456',
            token_expire_le=timezone.now() - timedelta(days=1),
            est_publie=True,
        )
        url = reverse('bulletins:bulletin_parent_signer', kwargs={'token': bulletin.token_signature})
        resp = client.post(url, {'nom_signataire': 'Parent Test'})
        # La vue signer vérifie token_valide, ne doit pas signer
        bulletin.refresh_from_db()
        assert bulletin.signe_le is None
        # Redirige vers consulter qui affichera l'erreur d'expiration
        assert resp.status_code == 302
