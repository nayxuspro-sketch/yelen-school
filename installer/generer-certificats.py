#!/usr/bin/env python3
"""Génère l'autorité locale et le certificat serveur du HTTPS réseau local de YELEN SCHOOL.

Exécuté dans le conteneur web par installer/activer-https.ps1 :
    python /app/installer/generer-certificats.py --hosts 192.168.1.10,SERVEUR-ECOLE --out /app/certs

Produit dans --out :
    yelen-ca.crt        autorité racine à installer sur chaque poste (10 ans)
    yelen-ca.key        clé privée de l'autorité (reste sur le serveur, jamais diffusée)
    yelen-serveur.crt   certificat du serveur, SAN = adresses IP et noms fournis (825 jours)
    yelen-serveur.key   clé privée du serveur
L'autorité existante est réutilisée pour que les postes n'aient pas à la réinstaller.
"""
import argparse
import datetime as dt
import ipaddress
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CA_NAME = 'YELEN SCHOOL - Autorite locale'
CA_DAYS = 3650
SERVER_DAYS = 825  # limite acceptée par tous les navigateurs pour une autorité privée


def _write_private(path, key):
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


def _write_cert(path, cert):
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _names(hosts):
    """Sépare adresses IP et noms DNS ; ignore les doublons et les valeurs vides."""
    ips, dns = [], []
    for host in dict.fromkeys(h.strip() for h in hosts if h.strip()):
        try:
            ips.append(ipaddress.ip_address(host))
        except ValueError:
            dns.append(host.lower())
    return ips, dns


def load_or_create_ca(out, now):
    ca_crt, ca_key = out / 'yelen-ca.crt', out / 'yelen-ca.key'
    if ca_crt.exists() and ca_key.exists():
        key = serialization.load_pem_private_key(ca_key.read_bytes(), password=None)
        cert = x509.load_pem_x509_certificate(ca_crt.read_bytes())
        if cert.not_valid_after_utc > now + dt.timedelta(days=SERVER_DAYS):
            return cert, key, False
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CA_NAME),
                         x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'YELEN SCHOOL')])
    cert = (x509.CertificateBuilder()
            .subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=CA_DAYS))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True,
                                         content_commitment=False, key_encipherment=False,
                                         data_encipherment=False, key_agreement=False,
                                         encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .sign(key, hashes.SHA256()))
    _write_private(ca_key, key)
    _write_cert(ca_crt, cert)
    return cert, key, True


def create_server_cert(out, ca_cert, ca_key, ips, dns, now):
    key = ec.generate_private_key(ec.SECP256R1())
    common_name = str(ips[0]) if ips else dns[0]
    san = [x509.IPAddress(ip) for ip in ips] + [x509.DNSName(name) for name in dns]
    cert = (x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                                     x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'YELEN SCHOOL')]))
            .issuer_name(ca_cert.subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=SERVER_DAYS))
            .add_extension(x509.SubjectAlternativeName(san), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=True,
                                         content_commitment=False, data_encipherment=False,
                                         key_agreement=False, key_cert_sign=False, crl_sign=False,
                                         encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                           critical=False)
            .sign(ca_key, hashes.SHA256()))
    _write_private(out / 'yelen-serveur.key', key)
    _write_cert(out / 'yelen-serveur.crt', cert)
    return cert


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--hosts', required=True,
                        help='adresses IP et noms du serveur, séparés par des virgules')
    parser.add_argument('--out', default='/app/certs', help='dossier de sortie (défaut : /app/certs)')
    args = parser.parse_args(argv)

    ips, dns = _names(args.hosts.split(','))
    if not ips and not dns:
        parser.error('--hosts ne contient aucune adresse valide')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)

    ca_cert, ca_key, ca_created = load_or_create_ca(out, now)
    server = create_server_cert(out, ca_cert, ca_key, ips, dns, now)

    print(f"Autorité locale : {'créée' if ca_created else 'réutilisée'} ({out / 'yelen-ca.crt'})")
    print(f"Certificat serveur : {out / 'yelen-serveur.crt'}")
    print(f"  Adresses couvertes : {', '.join([str(ip) for ip in ips] + dns)}")
    print(f"  Valide jusqu'au    : {server.not_valid_after_utc:%d/%m/%Y}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
