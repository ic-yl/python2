"""Verify the learner's upstream TLS routes in one unique Docker Compose project."""

import argparse
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from certificates import generate


ROOT = Path(__file__).resolve().parent
CONFIGS = {'base': 'edge.conf', 'variant': 'my_variant.conf', 'guide': 'guide.conf', 'example': 'variant_example.conf'}


def require(condition, name):
    if not condition:
        raise ValueError(name)


def get(port, path):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=4)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        body = response.read(16385)
        require(len(body) <= 16384, 'bounded_response')
        return response.status, body
    finally:
        connection.close()


def test_routes(port, mode):
    results = []

    def positive(path, expected):
        status, body = get(port, path)
        require(status == 200, 'expected_success_' + path)
        value = json.loads(body)
        require(value == {'fixture': 'upstream-tls', 'path': path, 'sni': expected, 'served_name': expected}, 'sni_identity_' + path)
        results.append(dict(path=path, status=status, sni=value['sni'], servedName=value['served_name']))

    def negative(path, expected):
        status, body = get(port, path)
        require(status == expected, 'expected_' + str(expected) + '_' + path)
        require(b'upstream-tls' not in body, 'no_upstream_response_' + path)
        results.append(dict(path=path, status=status))

    if mode == 'guide':
        positive('/identity', 'identity.lab.test')
    elif mode == 'example':
        negative('/reject', 502)
    else:
        positive('/status', 'api.lab.test')
        if mode == 'base':
            negative('/wrong-name', 502)
        else:
            positive('/report', 'reports.lab.test')
            negative('/wrong-ca', 502)
    negative('/unlisted', 404)
    return results


def test_environment(args, private):
    project = 'cdx3upstream' + uuid4().hex[:12]
    project_label = 'label=com.docker.compose.project=' + project
    blocked_env = {'EDGE_IMAGE', 'UPSTREAM_IMAGE', 'COURSE_CONF', 'COURSE_TLS_ROOT'}
    env = {key: value for key, value in os.environ.items() if not key.startswith('COMPOSE_') and key not in blocked_env}
    env.update(COURSE_CONF=CONFIGS[args.mode], COURSE_TLS_ROOT=str(private))
    compose = ['compose', '--env-file', 'images.env', '-f', 'upstream-tls.yml', '-p', project]

    def docker(*command, timeout=25):
        result = subprocess.run(['docker', *command], cwd=ROOT, env=env, capture_output=True, timeout=timeout)
        out, err = (data.decode('utf8', 'replace') for data in (result.stdout, result.stderr))
        if result.returncode:
            raise RuntimeError(f'{command[0]} failed: {err.strip()[-1200:]}')
        return out, err

    def composed(*command, **kw):
        return docker(*compose, *command, **kw)

    images = composed('config', '--images')[0].splitlines()
    require(len(images) == 2 and all('@sha256:' in image for image in images), 'two_pinned_images_required')
    for image in images:
        docker('image', 'inspect', '--format', '{{.Id}}', image)
    definition = json.loads(composed('config', '--format', 'json')[0])
    require(set(definition['services']) == {'edge', 'upstream'} and not definition.get('volumes'), 'unexpected_exercise_roles')
    require(set(definition['networks']) == {'entry', 'private'} and
            all(not value.get('external') for value in definition['networks'].values()), 'unexpected_network_scope')
    openssl = args.openssl or shutil.which('openssl')
    require(bool(openssl), 'set --openssl to your OpenSSL 3.x executable')
    certificate_evidence = generate(openssl, private)
    try:
        composed('up', '-d', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '30', timeout=45)
        actual = {}
        for role in ('upstream', 'edge'):
            identity = composed('ps', '-q', role)[0].strip()
            require(bool(identity), 'missing_' + role)
            actual[role] = json.loads(docker('inspect', identity)[0])[0]
            require(actual[role]['Config']['Labels']['com.docker.compose.project'] == project, 'different_project')
        require(not actual['upstream']['HostConfig']['PortBindings'], 'private_upstream_has_host_binding')
        require(set(actual['upstream']['NetworkSettings']['Networks']) == {project + '_private'}, 'wrong_upstream_membership')
        require(set(actual['edge']['NetworkSettings']['Networks']) == {project + '_private', project + '_entry'}, 'wrong_edge_membership')
        network = json.loads(docker('network', 'inspect', project + '_private')[0])[0]
        require(network['Internal'] is True, 'upstream_network_must_be_internal')
        mounts = {row['Destination']: row['RW'] for row in actual['edge']['Mounts']}
        require(mounts == {'/trust': False, '/etc/nginx/nginx.conf': False, '/etc/nginx/course.conf': False}, 'edge_mount_inventory')
        require({entry.name for entry in (private/'trust').iterdir()} == {'course-ca.pem', 'other-ca.pem'}, 'edge_trust_files_only')
        bindings = {name: value for name, value in actual['edge']['NetworkSettings']['Ports'].items() if value}
        require(set(bindings) == {'8080/tcp'} and len(bindings['8080/tcp']) == 1, 'only_expected_edge_port')
        binding = bindings['8080/tcp'][0]
        require(binding['HostIp'] == '127.0.0.1', 'edge_binding_must_be_loopback')
        for delay in (0.2, 0.4, 0.8, None):
            try:
                results = test_routes(int(binding['HostPort']), args.mode)
                break
            except (ConnectionRefusedError, ConnectionResetError):
                if delay is None:
                    raise
                time.sleep(delay)
        out, err = composed('logs', '--no-color', '--no-log-prefix', 'edge')
        log = (out + err).lower()
        wrong_name = 'upstream ssl certificate does not match "missing.lab.test"' in log
        wrong_ca = 'upstream ssl certificate verify error' in log
        require(wrong_name is (args.mode == 'base'), 'actual_tls_name_log')
        require(wrong_ca is (args.mode in ('variant', 'example')), 'actual_tls_ca_log')
        return dict(passed=True, actualHttpRows=results, testedCertificateFingerprints=certificate_evidence,
                    upstreamNameRejected=wrong_name, wrongTrustAnchorRejected=wrong_ca, noPrivateKeysMountedAtEdge=True,
                    loopbackOnly=True, privateUpstreamExposed=False, noRetainedOwnedResources=True)
    except ValueError:
        out, err = composed('logs', '--no-color', '--no-log-prefix', '--tail', '10', 'edge')
        print((out + err).strip(), file=sys.stderr)
        raise
    finally:
        composed('down', '--timeout', '2', '--volumes', '--remove-orphans')
        for subject, flags in (('container', '-aq'), ('network', '-q'), ('volume', '-q')):
            require(not docker(subject, 'ls', flags, '--filter', project_label)[0].strip(), 'remaining_owned_' + subject)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=CONFIGS)
    parser.add_argument('--openssl')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='cdx3upstream-') as work:
        temporary = Path(work).resolve()
        result = test_environment(args, temporary)
    require(not temporary.exists(), 'temporary_certificates_still_exist')
    print(json.dumps(dict(result, mode=args.mode, generatedKeysRemoved=True)))


if __name__ == '__main__':
    main()
