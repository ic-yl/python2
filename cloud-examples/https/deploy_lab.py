"""Transfer and observe disposable certificates inside the private Docker network."""

import argparse
import hashlib
import http.client
import json
import os
import socket
import ssl
import urllib.request
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization


DEPLOY = Path('/deploy')
SERVICE = 'pebble.course.test'
CA_CONFIG = '/issuer-connection.pem'


def request(domain, port, path, *, host=None, trust=None):
    connection = http.client.HTTPConnection(domain, port, timeout=4)
    if trust:
        context = ssl.create_default_context(cafile=trust)
        raw = socket.create_connection((domain, port), timeout=4)
        try:
            connection.sock = context.wrap_socket(raw, server_hostname=host or domain)
        except BaseException:
            raw.close()
            raise
    try:
        connection.request('GET', path, headers={'Host': host or domain})
        tls = connection.sock.getpeercert(binary_form=True) if trust else None
        reply = connection.getresponse()
        body = reply.read(4097).decode('utf8')
        assert len(body) <= 4096
        return dict(status=reply.status, location=reply.getheader('Location'), body=body,
                    certificateSha256=hashlib.sha256(tls).hexdigest() if tls else None)
    finally:
        connection.close()


def prepare(domain, number):
    directory = Path('/state/config/live')/domain
    cert = x509.load_pem_x509_certificate((directory/'cert.pem').read_bytes())
    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.DNSName)
    assert names == [domain]
    public = (directory/'fullchain.pem').read_bytes()
    private = (directory/'privkey.pem').read_bytes()
    key = serialization.load_pem_private_key(private, password=None)
    encoding = serialization.Encoding.DER
    format_ = serialization.PublicFormat.SubjectPublicKeyInfo
    assert key.public_key().public_bytes(encoding, format_) == cert.public_key().public_bytes(encoding, format_)
    target = DEPLOY/number
    target.mkdir(mode=0o755)
    (target/'fullchain.pem').write_bytes(public)
    secret = target/'privkey.pem'
    secret.write_bytes(private)
    os.chown(secret, 101, 101)
    secret.chmod(0o600)
    root = DEPLOY/'issuer.pem'
    if not root.exists():
        context = ssl.create_default_context(cafile=CA_CONFIG)
        with urllib.request.urlopen(f'https://{SERVICE}:15000/roots/0', context=context, timeout=4) as response:
            issuer = response.read(8193)
        assert 0 < len(issuer) <= 8192
        x509.load_pem_x509_certificate(issuer)
        root.write_bytes(issuer)
    return dict(sha256=cert.fingerprint(hashes.SHA256()).hex(), serial=hex(cert.serial_number), domains=names)


def select(number):
    assert number in ('first', 'renewed', 'mismatch') and (DEPLOY/number).is_dir()
    pending = DEPLOY/'next'
    pending.symlink_to(number, target_is_directory=True)
    pending.replace(DEPLOY/'active')


def make_mismatch():
    from cryptography.hazmat.primitives.asymmetric import ec

    bad = DEPLOY/'mismatch'
    bad.mkdir()
    (bad/'fullchain.pem').write_bytes((DEPLOY/'renewed/fullchain.pem').read_bytes())
    wrong = ec.generate_private_key(ec.SECP256R1()).private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    secret = bad/'privkey.pem'
    secret.write_bytes(wrong)
    os.chown(secret, 101, 101)
    secret.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('http', 'https', 'prepare', 'select', 'mismatch'))
    parser.add_argument('target')
    parser.add_argument('value', nargs='?')
    parser.add_argument('--host')
    args = parser.parse_args()
    if args.mode == 'prepare':
        assert args.target in ('preview.course.test', 'deploy.course.test') and args.value in ('first', 'renewed')
        result = prepare(args.target, args.value)
    elif args.mode == 'select':
        select(args.target)
        result = {'active': args.target}
    elif args.mode == 'mismatch':
        assert args.target == 'test-only'
        make_mismatch()
        result = {'candidate': 'mismatch'}
    elif args.mode == 'http':
        result = request(args.target, 5002, args.value, host=args.host)
    else:
        result = request(args.target, 5443, args.value, host=args.host, trust=str(DEPLOY/'issuer.pem'))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
