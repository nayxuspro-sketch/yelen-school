"""Lanceurs Windows : le serveur autonome lit `.env` et l'accès à distance a son lanceur.

Ces fichiers ne peuvent pas être exécutés dans l'intégration continue Linux ; ces vérifications
gardent au moins leur contrat : un `.env` chargé au démarrage, un lanceur administrateur qui appelle
le script PowerShell, et un script qui n'écrit jamais le jeton dans un fichier.
"""
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def test_demarrage_autonome_charge_le_env():
    """`waitress-serve` ne passe pas par `manage.py` : sans export explicite, SECRET_KEY, ALLOWED_HOSTS et
    CSRF_TRUSTED_ORIGINS du `.env` sont ignorés (sessions perdues, nom public refusé en 400)."""
    script = (RACINE / 'demarrer-autonome.bat').read_text(encoding='utf-8')

    assert 'call :charger_env' in script
    assert ':charger_env' in script
    assert 'for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do' in script
    # L'adresse locale détectée reste autorisée même si le .env vient d'un autre réseau.
    assert 'set "ALLOWED_HOSTS=!ALLOWED_HOSTS!,localhost,127.0.0.1"' in script


def test_lanceur_acces_distance():
    """Le lanceur Windows exige l'élévation puis appelle le script PowerShell avec ses arguments."""
    bat = (RACINE / 'activer-acces-distance.bat').read_text(encoding='utf-8')

    assert 'net session' in bat
    assert 'installer\\activer-acces-distance.ps1' in bat
    assert 'exit /b %EXIT_CODE%' in bat


def test_script_acces_distance_ne_divulgue_pas_le_jeton():
    """Le jeton du tunnel sert à enregistrer le service : il ne doit jamais finir dans le `.env` ni dans le journal."""
    script = (RACINE / 'installer' / 'activer-acces-distance.ps1').read_text(encoding='utf-8-sig')

    assert 'ALLOWED_HOSTS' in script and 'CSRF_TRUSTED_ORIGINS' in script
    assert 'ACCES_DISTANCE_DOMAINE' in script
    assert "'service', 'install', $Jeton" in script
    # Aucune ligne ne mêle le jeton à une écriture sur disque.
    for ligne in script.splitlines():
        if '$Jeton' in ligne:
            assert 'Set-DotEnvValue' not in ligne
            assert 'Write-AccesLog' not in ligne


def test_aucun_document_ne_cite_un_lanceur_inexistant():
    """`demarrer.bat` n'existe pas (le fichier est `demarrage.bat`, et `demarrer-autonome.bat` pour le mode sans
    Docker) : une consigne de redémarrage erronée laisse l'administrateur bloqué devant « n'est pas reconnu »."""
    racine = RACINE
    lanceurs = {p.name for p in racine.glob('*.bat')}
    assert 'demarrage.bat' in lanceurs and 'demarrer.bat' not in lanceurs

    fautifs = []
    documents = [f for f in (racine / 'docs').glob('*.md')] + list(racine.glob('*.md'))
    for fichier in documents:
        if fichier.name == 'CHANGELOG.md':      # journal des versions : il documente le correctif
            continue
        for numero, ligne in enumerate(fichier.read_text(encoding='utf-8').splitlines(), 1):
            instruction = ligne.replace('demarrer-autonome.bat', '')
            if 'demarrer.bat' in instruction and "n'existe pas" not in instruction:
                fautifs.append(f'{fichier.name}:{numero}')
    assert not fautifs, f'Lanceur inexistant cité : {fautifs}'
