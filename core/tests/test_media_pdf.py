"""Fichiers /media/ servis après connexion dans tous les modes, et lus sur le disque par les PDF.

Défaut d'origine : avec DEBUG=False (production), aucune route ne servait MEDIA_URL →
photos, logos et cachets en 404 dans les pages, et absents des PDF (WeasyPrint les
téléchargeait en HTTP auprès du serveur lui-même).
"""
import io

import pytest
from django.urls import reverse
from model_bakery import baker

from core import pdf as core_pdf

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / 'media'
    settings.MEDIA_ROOT.mkdir()
    settings.DEBUG = False
    return settings.MEDIA_ROOT


@pytest.fixture
def photo_png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (60, 80), (200, 30, 30)).save(buf, 'PNG')
    return buf.getvalue()


@pytest.fixture
def fichier_media(media_root, photo_png):
    dossier = media_root / 'personnel' / 'photos'
    dossier.mkdir(parents=True)
    (dossier / 'awa.png').write_bytes(photo_png)
    return '/media/personnel/photos/awa.png'


@pytest.fixture
def utilisateur():
    user = baker.make('accounts.User', role='SUPER_ADMIN', is_active=True, must_change_password=False)
    user.set_password('Ecole-Yelen-2026!')
    user.save()
    return user


class TestMediaProtege:
    def test_anonyme_redirige_vers_la_connexion(self, client, fichier_media):
        reponse = client.get(fichier_media)
        assert reponse.status_code == 302
        assert reverse('accounts:login') in reponse['Location']

    def test_utilisateur_connecte_recoit_le_fichier(self, client, fichier_media, photo_png, utilisateur):
        client.force_login(utilisateur)
        reponse = client.get(fichier_media)
        assert reponse.status_code == 200
        assert reponse['Content-Type'] == 'image/png'
        assert 'private' in reponse['Cache-Control']
        assert b''.join(reponse.streaming_content) == photo_png

    def test_fichier_inexistant(self, client, media_root, utilisateur):
        client.force_login(utilisateur)
        assert client.get('/media/personnel/photos/absente.png').status_code == 404

    def test_sortie_du_dossier_media_refusee(self, client, media_root, utilisateur):
        client.force_login(utilisateur)
        reponse = client.get('/media/../manage.py')
        assert reponse.status_code in (400, 404)


class TestFichierLocalPdf:
    def test_media_de_l_application_lu_sur_le_disque(self, settings, fichier_media, media_root):
        settings.ALLOWED_HOSTS = ['testserver']
        fichier = core_pdf.fichier_local('http://testserver' + fichier_media)
        assert fichier == (media_root / 'personnel' / 'photos' / 'awa.png').resolve()

    def test_hote_inconnu_ignore(self, settings, fichier_media):
        settings.ALLOWED_HOSTS = ['testserver']
        assert core_pdf.fichier_local('http://autre-serveur' + fichier_media) is None

    def test_chemin_hors_media_ignore(self, settings, media_root):
        settings.ALLOWED_HOSTS = ['testserver']
        assert core_pdf.fichier_local('http://testserver/media/../manage.py') is None
        assert core_pdf.fichier_local('http://testserver/comptes/login/') is None

    def test_fichier_statique_resolu(self, settings):
        settings.ALLOWED_HOSTS = ['testserver']
        fichier = core_pdf.fichier_local('http://testserver/static/css/yelen.css')
        assert fichier is not None and fichier.name == 'yelen.css'

    def test_fetcher_renvoie_le_contenu_et_le_type(self, settings, fichier_media, photo_png):
        settings.ALLOWED_HOSTS = ['testserver']
        reponse = core_pdf.FetcherLocal().fetch('http://testserver' + fichier_media)
        try:
            assert reponse.content_type == 'image/png'
            assert reponse.read() == photo_png
        finally:
            reponse.close()


class TestBadgePersonnelPdf:
    def test_photo_embarquee_dans_le_badge(self, client, media_root, photo_png, utilisateur):
        pytest.importorskip('weasyprint')
        from django.core.files.base import ContentFile
        etab = baker.make('etablissements.Etablissement')
        utilisateur.etablissement = etab
        utilisateur.save()
        membre = baker.make('personnel.MembrePersonnel', etablissement=etab, nom='Ouedraogo', prenom='Awa')
        membre.photo.save('awa.png', ContentFile(photo_png), save=True)
        client.force_login(utilisateur)

        apercu = client.get(reverse('personnel:badge', args=[membre.pk]))
        assert apercu.status_code == 200
        assert membre.photo.url.encode() in apercu.content
        assert client.get(membre.photo.url).status_code == 200

        pdf = client.get(reverse('personnel:badge', args=[membre.pk]) + '?format=pdf')
        assert pdf.status_code == 200
        assert pdf['Content-Type'] == 'application/pdf'
        assert b'/Image' in pdf.content, "la photo doit être embarquée dans le PDF du badge"
