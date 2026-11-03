"""Mise à jour en ligne et par archive `.zip` depuis Configuration > Mise à jour."""
from __future__ import annotations

import hashlib
import html as html_lib
import io
import json
import threading
import time
import urllib.error
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from core.mise_a_jour import TAILLE_MAX_DECOMPRESSEE, verifier_version_depot_distant
from core.models import AuditLog

pytestmark = pytest.mark.django_db


def _fabriquer_zip(
    *,
    version: str = '9.0.0',
    contenu_bundle: bytes = b'# v2 git bundle\n0000000000000000000000000000000000000000 refs/heads/main\n\nPACK',
    empreinte: str | None = None,
    inclure_sha: bool = True,
    entrees_suppl: dict[str, bytes] | None = None,
) -> tuple[SimpleUploadedFile, str]:
    nom_bundle = f'yelen-school-{version}.bundle'
    sha_reel = hashlib.sha256(contenu_bundle).hexdigest()
    sha_ecrit = sha_reel if empreinte is None else empreinte

    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(nom_bundle, contenu_bundle)
        if inclure_sha:
            zf.writestr(f'{nom_bundle}.sha256', f'{sha_ecrit}  {nom_bundle}\n')
        for nom, donnees in (entrees_suppl or {}).items():
            zf.writestr(nom, donnees)
    return (
        SimpleUploadedFile(f'yelen-school-{version}.zip', tampon.getvalue(), content_type='application/zip'),
        sha_reel,
    )


@pytest.fixture(autouse=True)
def dossier_maj_isole(settings, tmp_path):
    settings.TWO_FACTOR_REQUIRED = False
    settings.YELEN_UPDATE_DIR = tmp_path / 'mises-a-jour'
    settings.YELEN_UPDATE_SYNC_WAIT_SECONDS = 0.0
    return settings.YELEN_UPDATE_DIR


def _connecter(client, role='DIRECTEUR'):
    etab = baker.make('etablissements.Etablissement')
    user = baker.make(
        'accounts.User',
        role=role,
        etablissement=etab,
        is_superuser=(role == 'SUPER_ADMIN'),
        must_change_password=False,
    )
    client.force_login(user)
    return user


def test_boutons_mise_a_jour_dans_configuration_reserves_a_la_direction(client):
    _connecter(client, 'DIRECTEUR')
    page_dir = client.get('/').content.decode()
    assert 'id="btn-maj-sidebar"' in page_dir
    assert 'id="btn-maj-en-ligne-sidebar"' in page_dir
    assert 'data-csp-trigger-click="input-maj-zip"' in page_dir
    assert 'data-csp-trigger-click="submit-maj-en-ligne"' in page_dir
    assert 'id="input-maj-zip"' in page_dir
    assert 'accept=".zip,application/zip"' in page_dir
    # Les deux boutons se trouvent bien dans la rubrique Configuration (avant Administration).
    sec_conf = '<span class="sb-section-modern">Configuration</span>'
    sec_admin = '<span class="sb-section-modern is-espacee">Administration</span>'
    assert (
        page_dir.index(sec_conf)
        < page_dir.index('id="btn-maj-sidebar"')
        < page_dir.index('id="btn-maj-en-ligne-sidebar"')
        < page_dir.index(sec_admin)
    )

    _connecter(client, 'COMPTABLE')
    page_comptable = client.get('/').content.decode()
    assert 'id="btn-maj-sidebar"' not in page_comptable
    assert 'id="btn-maj-en-ligne-sidebar"' not in page_comptable
    assert 'id="input-maj-zip"' not in page_comptable
    assert client.get(reverse('core:mise_a_jour')).status_code == 403
    assert client.post(reverse('core:mise_a_jour_en_ligne')).status_code == 403
    assert client.get(reverse('core:mise_a_jour_etat')).status_code == 403


def test_mise_a_jour_en_ligne_nouvelle_version_disponible_demarre(client, settings, dossier_maj_isole, mocker):
    settings.YELEN_VERSION = '5.47.5'
    mocker.patch('core.mise_a_jour.verifier_version_depot_distant', return_value='5.47.6')
    directeur = _connecter(client, 'DIRECTEUR')

    reponse = client.post(reverse('core:mise_a_jour_en_ligne'), follow=True)
    html = reponse.content.decode()

    assert reponse.status_code == 200
    assert 'Nouvelle version 5.47.6 disponible : la mise à jour commence.' in html
    assert 'hx-trigger="every 3s"' in html

    demande = json.loads((dossier_maj_isole / 'demande.json').read_text(encoding='utf-8'))
    assert demande['mode'] == 'EN_LIGNE'
    assert demande['statut'] == 'EN_ATTENTE'
    assert demande['version_avant'] == '5.47.5'
    assert demande['version_cible'] == '5.47.6'
    assert demande['demande_par'] == directeur.username

    trace = AuditLog.objects.filter(app_label='core', model_name='miseajour').latest('timestamp')
    assert trace.action == 'SECURITY'
    assert trace.object_id == '5.47.6'


def test_mise_a_jour_en_ligne_aucune_version_disponible_informe_sans_demarrer(
    client, settings, dossier_maj_isole, mocker
):
    settings.YELEN_VERSION = '5.47.6'
    mocker.patch('core.mise_a_jour.verifier_version_depot_distant', return_value='5.47.6')
    _connecter(client, 'DIRECTEUR')

    reponse = client.post(reverse('core:mise_a_jour_en_ligne'), follow=True)
    html = html_lib.unescape(reponse.content.decode())

    assert reponse.status_code == 200
    assert "Il n'y a pas de mise à jour disponible (version actuelle : 5.47.6)." in html
    assert not (dossier_maj_isole / 'demande.json').exists()


@pytest.mark.parametrize('statut_hote,version_cible,message_attendu', [
    ('AUCUNE_MAJ', '5.47.6', "Il n'y a pas de mise à jour disponible (version actuelle : 5.47.6)."),
    ('EN_COURS', '5.48.0', 'Nouvelle version 5.48.0 disponible : la mise à jour commence.'),
])
def test_mise_a_jour_en_ligne_relais_agent_hote_depot_prive(
    client, settings, dossier_maj_isole, mocker, statut_hote, version_cible, message_attendu
):
    settings.YELEN_VERSION = '5.47.6'
    settings.YELEN_UPDATE_SYNC_WAIT_SECONDS = 3.0
    mocker.patch('core.mise_a_jour.verifier_version_depot_distant', return_value=None)
    _connecter(client, 'SUPER_ADMIN')

    # Simule l'agent hôte Windows qui lit demande.json (VERIFICATION) et répond après git fetch.
    def agent_windows_simule():
        fichier = dossier_maj_isole / 'demande.json'
        for _ in range(40):
            if fichier.is_file():
                donnees = json.loads(fichier.read_text(encoding='utf-8'))
                if donnees.get('statut') == 'VERIFICATION':
                    donnees['statut'] = statut_hote
                    donnees['version_cible'] = version_cible
                    donnees['message'] = message_attendu
                    fichier.write_text(json.dumps(donnees), encoding='utf-8')
                    return
            time.sleep(0.05)

    ouvrier = threading.Thread(target=agent_windows_simule, daemon=True)
    ouvrier.start()
    reponse = client.post(reverse('core:mise_a_jour_en_ligne'), follow=True)
    ouvrier.join(timeout=2)

    assert message_attendu in html_lib.unescape(reponse.content.decode())


def test_verifier_version_depot_distant_http_et_jeton(settings, mocker):
    class FauxFlux:
        def __init__(self, contenu: bytes):
            self._contenu = contenu

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _n=-1):
            return self._contenu

    settings.YELEN_GITHUB_TOKEN = 'jeton-lecture-test'
    appel = mocker.patch('urllib.request.urlopen', return_value=FauxFlux(b'5.48.1\n'))
    assert verifier_version_depot_distant() == '5.48.1'
    requete = appel.call_args.args[0]
    assert requete.get_header('Authorization') == 'Bearer jeton-lecture-test'

    mocker.patch(
        'urllib.request.urlopen',
        side_effect=urllib.error.HTTPError('https://api.github.com/x', 404, 'Not Found', {}, None),
    )
    assert verifier_version_depot_distant() is None

    settings.YELEN_UPDATE_REPO = 'nom invalide !!'
    assert verifier_version_depot_distant() is None


def test_depot_archive_zip_valide_cree_demande_audit_et_suivi_htmx(client, settings, dossier_maj_isole):
    settings.YELEN_VERSION = '5.47.5'
    directeur = _connecter(client, 'DIRECTEUR')
    archive, sha = _fabriquer_zip(version='5.47.6')

    reponse = client.post(reverse('core:mise_a_jour'), {'archive_zip': archive}, follow=True)
    html = reponse.content.decode()

    assert reponse.status_code == 200
    assert 'Archive vérifiée (SHA-256)' in html
    assert 'hx-trigger="every 3s"' in html
    assert (dossier_maj_isole / 'yelen-school-5.47.6.bundle').is_file()
    assert (dossier_maj_isole / 'yelen-school-5.47.6.bundle.sha256').is_file()

    demande = json.loads((dossier_maj_isole / 'demande.json').read_text(encoding='utf-8'))
    assert demande['mode'] == 'ARCHIVE'
    assert demande['statut'] == 'EN_ATTENTE'
    assert demande['version_avant'] == '5.47.5'
    assert demande['version_cible'] == '5.47.6'
    assert demande['empreinte'] == sha
    assert demande['demande_par'] == directeur.username

    trace = AuditLog.objects.filter(app_label='core', model_name='miseajour').latest('timestamp')
    assert trace.action == 'SECURITY'
    assert trace.user_id == directeur.pk
    assert trace.object_id == '5.47.6'

    # Dès que la nouvelle version répond, le fragment passe automatiquement à « Terminée » et cesse le polling.
    settings.YELEN_VERSION = '5.47.6'
    fragment = client.get(reverse('core:mise_a_jour_etat')).content.decode()
    assert 'Terminée' in fragment
    assert 'hx-trigger="every 3s"' not in fragment


@pytest.mark.parametrize('cas,fabrique,attendu', [
    (
        'non_zip',
        lambda: SimpleUploadedFile('faux.zip', b'pas un zip', content_type='application/zip'),
        'archive .zip valide',
    ),
    (
        'traversee_chemin',
        lambda: _fabriquer_zip(entrees_suppl={'../intrus.txt': b'x'})[0],
        'Chemin relatif sortant interdit',
    ),
    (
        'chemin_absolu',
        lambda: _fabriquer_zip(entrees_suppl={'/etc/passwd': b'x'})[0],
        'Chemin absolu interdit',
    ),
    (
        'sans_sha256',
        lambda: _fabriquer_zip(inclure_sha=False)[0],
        'Empreinte SHA-256 absente',
    ),
    (
        'sha256_mal_forme',
        lambda: _fabriquer_zip(empreinte='xyz')[0],
        'Empreinte SHA-256 mal formée',
    ),
    (
        'sha256_faux',
        lambda: _fabriquer_zip(empreinte='0' * 64)[0],
        'Empreinte SHA-256 incorrecte',
    ),
    (
        'faux_bundle',
        lambda: _fabriquer_zip(contenu_bundle=b'CECI N EST PAS UN BUNDLE GIT\n')[0],
        'bundle Git valide',
    ),
    (
        'version_anterieure',
        lambda: _fabriquer_zip(version='5.47.0')[0],
        'Version antérieure refusée',
    ),
])
def test_archives_invalides_refusees_sans_ecriture(client, settings, dossier_maj_isole, cas, fabrique, attendu):
    settings.YELEN_VERSION = '5.47.5'
    _connecter(client, 'SUPER_ADMIN')

    reponse = client.post(reverse('core:mise_a_jour'), {'archive_zip': fabrique()}, follow=True)
    html = reponse.content.decode()

    assert attendu in html, f'{cas}: {html}'
    assert not (dossier_maj_isole / 'demande.json').exists()
    assert list(dossier_maj_isole.glob('*.bundle')) == []
    assert list(dossier_maj_isole.glob('*.tmp')) == []


def test_version_identique_signale_deja_a_jour_sans_relancer(client, settings, dossier_maj_isole):
    settings.YELEN_VERSION = '5.47.6'
    _connecter(client, 'DIRECTEUR')
    archive, _ = _fabriquer_zip(version='5.47.6')

    reponse = client.post(reverse('core:mise_a_jour'), {'archive_zip': archive}, follow=True)
    html = reponse.content.decode()

    assert 'déjà à jour (version 5.47.6)' in html
    assert not (dossier_maj_isole / 'demande.json').exists()


def test_refuse_depot_concurrent_pendant_execution_et_accepte_bom_powershell(
    client, settings, dossier_maj_isole
):
    settings.YELEN_VERSION = '5.47.5'
    _connecter(client, 'DIRECTEUR')
    dossier_maj_isole.mkdir(parents=True, exist_ok=True)
    # Simule un fichier demande.json écrit par Windows PowerShell avec BOM UTF-8.
    (dossier_maj_isole / 'demande.json').write_text(
        json.dumps({
            'version_avant': '5.47.5',
            'version_cible': '5.47.6',
            'statut': 'EN_COURS',
            'debut_le': timezone.now().isoformat(),
            'message': 'En cours...',
        }),
        encoding='utf-8-sig',
    )

    archive, _ = _fabriquer_zip(version='5.47.7')
    reponse = client.post(reverse('core:mise_a_jour'), {'archive_zip': archive}, follow=True)
    assert 'déjà en cours' in reponse.content.decode()
    reponse_en_ligne = client.post(reverse('core:mise_a_jour_en_ligne'), follow=True)
    assert 'déjà en cours' in reponse_en_ligne.content.decode()


def test_plafond_taille_archive_bloque_bombe_zip(client, settings, mocker):
    settings.YELEN_VERSION = '5.47.5'
    mocker.patch('core.mise_a_jour.TAILLE_MAX_DECOMPRESSEE', 32)
    assert TAILLE_MAX_DECOMPRESSEE > 32
    _connecter(client, 'DIRECTEUR')
    archive, _ = _fabriquer_zip(version='5.47.6')

    reponse = client.post(reverse('core:mise_a_jour'), {'archive_zip': archive}, follow=True)
    assert 'Archive trop volumineuse' in reponse.content.decode()


def test_expiration_demande_bloquee_en_verification_ou_en_cours(client, settings, dossier_maj_isole):
    """Une demande restée sans réponse de l'agent hôte Windows ne laisse pas la page tourner en boucle."""
    from datetime import timedelta

    settings.YELEN_VERSION = '5.47.8'
    _connecter(client, 'DIRECTEUR')
    dossier_maj_isole.mkdir(parents=True, exist_ok=True)

    (dossier_maj_isole / 'demande.json').write_text(
        json.dumps({
            'id': 'bloquee',
            'mode': 'EN_LIGNE',
            'version_avant': '5.47.8',
            'version_cible': '',
            'statut': 'VERIFICATION',
            'demande_le': (timezone.now() - timedelta(minutes=3)).isoformat(),
            'message': 'Vérification...',
        }),
        encoding='utf-8',
    )
    fragment = html_lib.unescape(client.get(reverse('core:mise_a_jour_etat')).content.decode())
    assert 'Échec' in fragment
    assert 'mettre-a-jour.bat' in fragment
    assert 'hx-trigger="every 3s"' not in fragment

    (dossier_maj_isole / 'demande.json').write_text(
        json.dumps({
            'id': 'en-cours-expiree',
            'mode': 'EN_LIGNE',
            'version_avant': '5.47.8',
            'version_cible': '5.47.9',
            'statut': 'EN_COURS',
            'debut_le': (timezone.now() - timedelta(minutes=35)).isoformat(),
            'message': 'En cours...',
        }),
        encoding='utf-8',
    )
    fragment2 = html_lib.unescape(client.get(reverse('core:mise_a_jour_etat')).content.decode())
    assert 'Échec' in fragment2
    assert 'hx-trigger="every 3s"' not in fragment2
