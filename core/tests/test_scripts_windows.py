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


def test_le_guide_enseigne_la_saisie_de_la_cle_tailscale_dans_l_application():
    """Une clé Tailscale se saisit dans l'application (menu ⋯ → « Use an auth key »), jamais dans la page web
    `login.tailscale.com` : y chercher un champ clé mène à une fenêtre de clé d'accès (passkey) et bloque
    l'enseignant. Deux réglages, s'ils sont manqués, coûtent une réinstallation : la clé ne doit pas être
    *ephemeral* (l'appareil serait supprimé à la première déconnexion) et l'expiration de clé doit être
    désactivée sur chaque appareil (180 jours par défaut)."""
    guide = (RACINE / 'docs' / 'GUIDE_DEPLOIEMENT_WINDOWS.md').read_text(encoding='utf-8')
    section = guide.split('### 9.5 Accès du personnel par Tailscale Serve', 1)
    assert len(section) == 2, 'la section 9.5 du guide est introuvable'
    texte = section[1].split('\n---', 1)[0]

    assert 'Use an auth key' in texte
    assert 'tailscale up --authkey' in texte          # application Windows : pas de champ clé
    assert 'Ne jamais cocher' in texte and 'Ephemeral' in texte
    assert 'Disable key expiry' in texte
    assert 'Éphémère' in texte and 'Cheminée' in texte  # lecture des badges de la liste Machines


# ── Mise à jour hors ligne (5.47.3) ──────────────────────────────────────────

def test_mise_a_jour_hors_ligne_verifie_l_empreinte_avant_tout():
    """Une archive de mise à jour n'est utilisée qu'après vérification de son empreinte SHA-256, et cette
    vérification passe AVANT la sauvegarde et avant toute écriture : une archive altérée ne change rien."""
    script = (RACINE / 'installer' / 'mettre-a-jour.ps1').read_text(encoding='utf-8-sig').replace('\r\n', '\n')

    assert '[string]$DepuisArchive' in script and '[string]$Empreinte' in script
    assert 'Get-FileHash -LiteralPath $Chemin -Algorithm SHA256' in script
    assert "if ($reel -ne $attendu)" in script and 'Mise à jour annulée' in script
    # Empreinte absente ou mal formée : refus explicite, jamais de passage silencieux.
    assert 'Empreinte SHA-256 absente' in script and 'Empreinte SHA-256 mal formée' in script

    verification = script.index('$ArchivePath = Resolve-ArchiveMiseAJour')
    sauvegarde = script.index('if (-not $SansSauvegarde)')
    fusion = script.index('git merge --ff-only FETCH_HEAD')
    assert verification < sauvegarde < fusion, 'empreinte → sauvegarde → fusion'


def test_mise_a_jour_hors_ligne_utilise_le_bundle_et_reste_compatible_git():
    """L'archive est un bundle git : elle emprunte exactement le chemin de GitHub (fetch puis avance rapide),
    ce qui conserve le retour arrière et la détection « déjà à jour »."""
    script = (RACINE / 'installer' / 'mettre-a-jour.ps1').read_text(encoding='utf-8-sig').replace('\r\n', '\n')

    assert 'git -C $Root bundle verify --quiet $Chemin' in script, 'vérification indépendante du répertoire courant'
    assert 'git fetch --quiet $ArchivePath main' in script
    assert 'git fetch --quiet origin main' in script, 'le chemin GitHub doit rester intact'
    # Le message de panne réseau doit indiquer la solution hors ligne.
    assert '-DepuisArchive pour une mise à jour hors ligne' in script

    bat = (RACINE / 'mettre-a-jour.bat').read_text(encoding='utf-8')
    assert '%*' in bat, 'les options doivent être transmises au script PowerShell'


def test_outil_editeur_produit_une_archive_verifiable():
    """Côté éditeur, l'archive et son empreinte sont produites ensemble et le bundle est contrôlé avant livraison."""
    script = (RACINE / 'installer' / 'outils-editeur' / 'creer-archive-mise-a-jour.ps1') \
        .read_text(encoding='utf-8-sig').replace('\r\n', '\n')

    assert 'git' in script and "'bundle', 'create'" in script
    assert 'bundle verify' in script and 'ne pas le livrer' in script
    assert 'Get-FileHash -LiteralPath $archive -Algorithm SHA256' in script
    assert '"$archive.sha256"' in script
    # Format lisible par `sha256sum -c` : empreinte, deux espaces, nom du fichier.
    assert '"$empreinte  $nom"' in script
    # Un fichier non suivi ne part pas dans le bundle : il ne doit pas bloquer l'éditeur.
    assert '--untracked-files=no' in script
    # L'archive .zip destinée au bouton Configuration > Mise à jour embarque le bundle et son .sha256.
    assert 'Compress-Archive -LiteralPath $archive, $fichierEmpreinte -DestinationPath $archiveZip -Force' in script


def test_mise_a_jour_interface_sans_docker_sock_et_agent_hote():
    """Le conteneur web ne monte jamais docker.sock : l'archive vérifiée passe par ./mises-a-jour
    et l'agent planifié côté hôte Windows valide strictement le nom et l'empreinte avant exécution."""
    compose = (RACINE / 'docker-compose.client.yml').read_text(encoding='utf-8')
    assert 'docker.sock' not in compose
    assert './mises-a-jour:/app/mises-a-jour' in compose

    maj = (RACINE / 'installer' / 'mettre-a-jour.ps1').read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    assert 'function Expand-ZipMiseAJour' in maj
    assert "if ([System.IO.Path]::GetExtension($Chemin).ToLower() -eq '.zip')" in maj

    agent = (RACINE / 'installer' / 'appliquer-mise-a-jour-en-attente.ps1') \
        .read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    assert '^yelen-school-\\d+\\.\\d+\\.\\d+\\.bundle$' in agent
    assert '^[0-9a-f]{64}$' in agent
    assert '-File $UpdateScript -DepuisArchive $cheminArchive -Empreinte $empreinte' in agent

    reg = (RACINE / 'installer' / 'register-update-agent-task.ps1') \
        .read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    assert "if ($existante.State -eq 'Running') { exit 0 }" in reg
