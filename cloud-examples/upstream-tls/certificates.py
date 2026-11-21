"""Create fresh practice certificates in an explicitly owned temporary directory."""

import subprocess


def generate(openssl, private):
    trust, server = private/'trust', private/'server'
    trust.mkdir()
    server.mkdir()

    def call(*parts):
        result = subprocess.run([openssl, *parts], cwd=private, capture_output=True, timeout=15)
        if result.returncode:
            raise RuntimeError(result.stderr.decode('utf8', 'replace')[-800:])
        return result.stdout

    version = call('version').decode('ascii', 'replace').strip()
    if not version.startswith('OpenSSL 3.'):
        raise ValueError('this exercise uses OpenSSL 3.x')
    for label in ('course-ca', 'other-ca'):
        call('req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:prime256v1', '-noenc',
             '-days', '2', '-subj', f'/CN={label}.lab.test', '-keyout', label+'.key', '-out', str(trust/(label+'.pem')),
             '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0', '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    extensions = private/'leaf.cnf'
    evidence = {}
    for index, name in enumerate(('identity.lab.test', 'api.lab.test', 'reports.lab.test'), start=10):
        key, cert = server/(name+'.key'), server/(name+'.pem')
        csr = private/(name+'.csr')
        extensions.write_text('[leaf]\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\n'
                              f'extendedKeyUsage=serverAuth\nsubjectAltName=DNS:{name}\n', encoding='ascii')
        call('req', '-new', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:prime256v1', '-noenc',
             '-subj', '/CN='+name, '-keyout', str(key), '-out', str(csr))
        call('x509', '-req', '-in', str(csr), '-CA', str(trust/'course-ca.pem'), '-CAkey', 'course-ca.key',
             '-set_serial', str(index), '-days', '1', '-sha256', '-extfile', str(extensions), '-extensions', 'leaf', '-out', str(cert))
        call('verify', '-purpose', 'sslserver', '-verify_hostname', name, '-CAfile', str(trust/'course-ca.pem'), str(cert))
        evidence[name] = call('x509', '-in', str(cert), '-noout', '-sha256', '-fingerprint').decode('ascii').strip().split('=', 1)[1]
        # A synthetic leaf key can be read by the unprivileged fixture inside its read-only mount.
        # The enclosing temporary directory is accessible only to the local user outside Docker.
        key.chmod(0o644)
    return {'opensslVersion': version, 'leafFingerprints': evidence, 'trustAnchors': ['course-ca', 'other-ca']}
