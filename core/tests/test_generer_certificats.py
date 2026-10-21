"""installer/generer-certificats.py : autorité locale réutilisée, certificat serveur signé, SAN complets."""
import importlib.util
import ipaddress
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

SCRIPT = Path(__file__).resolve().parents[2] / 'installer' / 'generer-certificats.py'


@pytest.fixture(scope='module')
def generer():
    spec = importlib.util.spec_from_file_location('generer_certificats', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lire(path):
    return x509.load_pem_x509_certificate(path.read_bytes())


def test_generation_complete(generer, tmp_path, capsys):
    assert generer.main(['--hosts', ' 192.168.1.10, Serveur-Ecole ,localhost,127.0.0.1,', '--out', str(tmp_path)]) == 0
    for nom in ('yelen-ca.crt', 'yelen-ca.key', 'yelen-serveur.crt', 'yelen-serveur.key'):
        assert (tmp_path / nom).exists(), nom

    ca = _lire(tmp_path / 'yelen-ca.crt')
    serveur = _lire(tmp_path / 'yelen-serveur.crt')
    assert ca.extensions.get_extension_for_class(x509.BasicConstraints).value.ca is True
    assert serveur.issuer == ca.subject
    # Signature du certificat serveur vérifiable avec la clé publique de l'autorité.
    ca.public_key().verify(serveur.signature, serveur.tbs_certificate_bytes, ec.ECDSA(hashes.SHA256()))

    san = serveur.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert san.get_values_for_type(x509.IPAddress) == [ipaddress.ip_address('192.168.1.10'),
                                                       ipaddress.ip_address('127.0.0.1')]
    assert san.get_values_for_type(x509.DNSName) == ['serveur-ecole', 'localhost']
    eku = serveur.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert x509.oid.ExtendedKeyUsageOID.SERVER_AUTH in eku
    assert (serveur.not_valid_after_utc - serveur.not_valid_before_utc).days <= 826

    sortie = capsys.readouterr().out
    assert 'Autorité locale : créée' in sortie
    assert '192.168.1.10, 127.0.0.1, serveur-ecole, localhost' in sortie


def test_autorite_reutilisee_au_renouvellement(generer, tmp_path, capsys):
    generer.main(['--hosts', '192.168.1.10', '--out', str(tmp_path)])
    ca_avant = (tmp_path / 'yelen-ca.crt').read_bytes()
    serveur_avant = (tmp_path / 'yelen-serveur.crt').read_bytes()
    capsys.readouterr()

    generer.main(['--hosts', '192.168.1.20', '--out', str(tmp_path)])
    assert (tmp_path / 'yelen-ca.crt').read_bytes() == ca_avant
    assert (tmp_path / 'yelen-serveur.crt').read_bytes() != serveur_avant
    assert 'Autorité locale : réutilisée' in capsys.readouterr().out


def test_hosts_vide_refuse(generer, tmp_path):
    with pytest.raises(SystemExit):
        generer.main(['--hosts', ' , ', '--out', str(tmp_path)])
