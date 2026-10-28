"""Lot I — I5 sauvegarde depuis l'interface : base SQLite + médias, liste, téléchargement sûr."""
import sqlite3

import pytest
from django.core.management.base import CommandError
from django.urls import reverse
from model_bakery import baker

from core import exploitation, sauvegarde

pytestmark = pytest.mark.django_db


@pytest.fixture
def base_sqlite(tmp_path, settings, monkeypatch):
    """Une petite base SQLite indépendante de la base de test, un dossier de sauvegarde et un média."""
    db = tmp_path / 'db.sqlite3'
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE t (x INTEGER)')
    con.execute('INSERT INTO t VALUES (42)')
    con.commit()
    con.close()
    settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(db)}}
    settings.MEDIA_ROOT = str(tmp_path / 'media')
    (tmp_path / 'media' / 'photos').mkdir(parents=True)
    (tmp_path / 'media' / 'photos' / 'eleve.jpg').write_bytes(b'\xff\xd8' * 100)
    monkeypatch.setenv('BACKUP_DIR', str(tmp_path / 'backups'))
    from django.core.cache import cache
    cache.delete(exploitation.CACHE_CLE)
    return tmp_path


def test_sauvegarde_base_et_medias(base_sqlite):
    resultat = sauvegarde.sauvegarder_maintenant(avec_medias=True)
    assert resultat['base'].name.startswith('yelen_school_') and resultat['base'].name.endswith('.sqlite3.gz')
    assert resultat['medias'].name.endswith('_medias.zip') and resultat['medias'].parent == base_sqlite / 'backups'
    import zipfile
    assert zipfile.ZipFile(resultat['medias']).namelist() == ['photos/eleve.jpg']
    lignes = sauvegarde.lister_sauvegardes()
    assert {l['type'] for l in lignes} == {'Base de données', 'Médias'} and all(l['taille_mo'] >= 0 for l in lignes)
    assert exploitation.derniere_sauvegarde()['fichier'].startswith('yelen_school_')
    # sans médias
    assert sauvegarde.sauvegarder_maintenant(avec_medias=False)['medias'] is None


def test_mode_serveur_refuse(mocker):
    mocker.patch('core.sauvegarde.mode_sqlite', return_value=False)
    with pytest.raises(CommandError, match='Mode serveur'):
        sauvegarde.sauvegarder_maintenant()


def test_chemin_sauvegarde_strict(base_sqlite):
    dossier = base_sqlite / 'backups'
    dossier.mkdir()
    (dossier / 'yelen_school_2026-10-28_120000.sqlite3.gz').write_bytes(b'x')
    (dossier / 'secret.txt').write_bytes(b'x')
    assert sauvegarde.chemin_sauvegarde('yelen_school_2026-10-28_120000.sqlite3.gz') == dossier / 'yelen_school_2026-10-28_120000.sqlite3.gz'
    for nom in ('secret.txt', '../yelen_school_x', 'yelen_school_../../etc/passwd', 'yelen_school_absent.gz', '', None):
        assert sauvegarde.chemin_sauvegarde(nom) is None


def test_page_exploitation_sauvegarde_et_telechargement(client, base_sqlite, mocker):
    etab = baker.make('etablissements.Etablissement')
    directeur = baker.make('accounts.User', role='DIRECTEUR', etablissement=etab, must_change_password=False)
    client.force_login(directeur)
    html = client.get(reverse('core:exploitation')).content.decode()
    assert 'Sauvegarder maintenant' in html
    reponse = client.post(reverse('core:exploitation'), {'sauvegarder': '1', 'medias': 'on'}, follow=True)
    texte = reponse.content.decode()
    assert 'Sauvegarde terminée' in texte and '_medias.zip' in texte and 'Télécharger' in texte
    nom = sauvegarde.lister_sauvegardes()[0]['nom']
    telechargement = client.get(reverse('core:sauvegarde_telecharger', args=[nom]))
    assert telechargement.status_code == 200 and nom in telechargement['Content-Disposition']
    assert b''.join(telechargement.streaming_content)
    assert client.get(reverse('core:sauvegarde_telecharger', args=['yelen_school_inexistant.gz'])).status_code == 404
    # mode serveur : message d'erreur, pas d'exception
    mocker.patch('core.sauvegarde.mode_sqlite', return_value=False)
    reponse = client.post(reverse('core:exploitation'), {'sauvegarder': '1'}, follow=True)
    assert 'Sauvegarde impossible : Mode serveur' in reponse.content.decode()
    # téléchargement réservé aux administrateurs
    client.force_login(baker.make('accounts.User', role='COMPTABLE', etablissement=etab, must_change_password=False))
    assert client.get(reverse('core:sauvegarde_telecharger', args=[nom])).status_code == 403
