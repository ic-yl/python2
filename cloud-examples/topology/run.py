"""Exercise the learner's Nginx rules with a fresh loopback-only Docker project."""

import argparse
import http.client
import ipaddress
import json
import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
CONFIGS = {'base': 'edge.conf', 'maintenance': 'my_variant.conf',
           'guide': 'guide.conf', 'example': 'variant_example.conf'}
NETWORKS = {'edge': {'entry', 'transit'}, 'api': {'transit', 'data'}, 'db': {'data'}}


def require(condition, name):
    if not condition:
        raise ValueError(name)


def request(host_port, path, site='workbench.test'):
    link = http.client.HTTPConnection('127.0.0.1', host_port, timeout=3)
    try:
        link.request('GET', path, headers={'Host': site, 'X-Forwarded-Proto': 'https', 'X-Forwarded-For': '192.0.2.27'})
        response = link.getresponse()
        body = response.read(16385)
        require(len(body) <= 16384, 'unexpected_response_size')
        return response.status, response.getheader('Retry-After'), body
    finally:
        link.close()


def routes(port, mode):
    if mode == 'guide':
        status, _, body = request(port, '/identity?case=green')
        require(status == 200 and json.loads(body)['path'] == '/identity' and json.loads(body)['query'] == 'case=green', 'guide_identity')
        require(request(port, '/other')[0] == 404, 'guide_unknown_path')
        return 2
    if mode == 'example':
        require(request(port, '/report')[:2] == (503, '30'), 'example_retry_after')
        require(request(port, '/other')[0] == 404, 'example_unknown_path')
        return 2
    status, _, body = request(port, '/api/status?case=blue')
    require(status == 200, 'status_route_http')
    observation = json.loads(body)
    require(observation['source'] == 'api-fixture' and observation['db_tcp_connected'] is True, 'status_route_backend')
    require((observation['path'], observation['query']) == ('/api/status', 'case=blue'), 'path_and_query_preserved')
    require((observation['host'], observation['proto']) == ('workbench.test', 'http'), 'trusted_scheme_and_host')
    peer = ipaddress.ip_address(observation['peer'])
    require(peer.version == 4 and peer != ipaddress.ip_address('192.0.2.27'), 'peer_not_taken_from_request')
    require(request(port, '/anything')[0] == 404, 'unknown_route')
    require(request(port, '/api/status', 'other.test')[0] == 421, 'unknown_host')
    status, after, body = request(port, '/api/export')
    if mode == 'base':
        require(status == 200 and json.loads(body)['path'] == '/api/export' and after is None, 'normal_export')
    else:
        require((status, after) == (503, '120'), 'paused_export_expected_503_and_120')
        require(b'api-fixture' not in body, 'paused_export_did_not_return_fixture_response')
    return 8 if mode == 'base' else 9


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=CONFIGS)
    args = parser.parse_args()
    project = 'cdx3edge' + uuid4().hex[:12]
    label = f'label=com.docker.compose.project={project}'
    env = {name: value for name, value in os.environ.items()
           if not name.startswith('COMPOSE_') and name not in ('EDGE_IMAGE', 'DB_IMAGE', 'API_IMAGE', 'COURSE_CONF')}
    env['COURSE_CONF'] = CONFIGS[args.mode]
    compose = ['compose', '--env-file', 'images.env', '-f', 'topology.yml', '-p', project]

    def call(*parts, ok=True, timeout=25):
        result = subprocess.run(['docker', *parts], cwd=ROOT, env=env, capture_output=True,
                                encoding='utf8', errors='replace', timeout=timeout)
        if ok and result.returncode:
            raise RuntimeError(f'{parts[0]} failed: {result.stderr.strip()[-1400:]}')
        return result

    def composed(*parts, **options):
        return call(*compose, *parts, **options)

    for image in composed('config', '--images').stdout.splitlines():
        require('@sha256:' in image, 'image_reference_must_be_pinned')
        call('image', 'inspect', '--format', '{{.Id}}', image)
    lesson = json.loads(composed('config', '--format', 'json').stdout)
    require(set(lesson['services']) == set(NETWORKS) and not lesson.get('volumes'), 'expected_only_the_three_lab_roles')
    require(all(not row.get('external') for row in lesson['networks'].values()), 'expected_owned_networks')
    proof = {'mode': args.mode, 'project': project}
    try:
        composed('up', '-d', '--no-build', '--pull', 'never', '--wait', '--wait-timeout', '30', timeout=45)
        identities = {role: composed('ps', '-q', role).stdout.strip() for role in NETWORKS}
        require(all(identities.values()), 'missing_running_role')
        info = {role: json.loads(call('inspect', identity).stdout)[0] for role, identity in identities.items()}
        require(all(value['Config']['Labels']['com.docker.compose.project'] == project for value in info.values()), 'project_owner')
        for role, names in NETWORKS.items():
            require(set(info[role]['NetworkSettings']['Networks']) == {f'{project}_{name}' for name in names}, 'memberships_' + role)
        for name in lesson['networks']:
            result = json.loads(call('network', 'inspect', f'{project}_{name}').stdout)[0]
            require(result['Internal'] is (name != 'entry'), 'internal_flag_' + name)
        for role in ('api', 'db'):
            require(not info[role]['HostConfig']['PortBindings'], 'native_host_port_' + role)
        ports = info['edge']['NetworkSettings']['Ports']
        require(set(key for key, value in ports.items() if value) == {'8080/tcp'}, 'only_one_edge_port_binding')
        binding, = ports['8080/tcp']
        require(binding['HostIp'] == '127.0.0.1', 'edge_host_bind_not_loopback')
        port = int(binding['HostPort'])
        require(composed('exec', '-T', 'db', 'psql', '-U', 'course', '-d', 'lab', '-Atc', 'SELECT 7').stdout.strip() == '7', 'postgres_query')
        db_ip = str(ipaddress.IPv4Address(info['db']['NetworkSettings']['Networks'][f'{project}_data']['IPAddress']))
        composed('exec', '-T', 'edge', 'busybox', 'true')
        result = composed('exec', '-T', 'edge', 'busybox', 'nc', '-n', '-v', '-z', '-w', '1', db_ip, '5432', ok=False, timeout=5)
        diagnostics = (result.stdout + result.stderr).strip().lower()
        require(result.returncode == 1 and any(word in diagnostics for word in ('timed out', 'timeout', 'unreachable', 'refused', 'no route')),
                f'edge_cannot_open_db_socket: exit={result.returncode}, diagnostics={diagnostics[-160:]}')
        for delay in (0.2, 0.4, 0.8, None):
            try:
                proof['httpChecks'] = routes(port, args.mode)
                break
            except (ConnectionRefusedError, ConnectionResetError):
                if delay is None:
                    raise
                time.sleep(delay)
        line = composed('logs', '--no-color', '--no-log-prefix', 'api')
        upstream = line.stdout + line.stderr
        export_forwarded = '"GET /api/export HTTP/' in upstream
        require(export_forwarded is (args.mode == 'base'), 'export_upstream_activity')
        proof.update(networks={role: sorted(names) for role, names in NETWORKS.items()}, postgresQuery=7,
                     allowedEdgeBind='127.0.0.1', directEdgeToOwnedPostgres='rejected', noBackendPortPublished=True,
                     upstreamExportObserved=export_forwarded)
    finally:
        composed('down', '--timeout', '2', '--volumes', '--remove-orphans', timeout=25)
        require(not call('ps', '-aq', '--filter', label).stdout.strip(), 'owned_containers_still_exist')
        require(not call('network', 'ls', '-q', '--filter', label).stdout.strip(), 'owned_networks_still_exist')
        require(not call('volume', 'ls', '-q', '--filter', label).stdout.strip(), 'owned_volumes_still_exist')
    print(json.dumps(dict(proof, passed=True, ownedResourcesRemoved=True)))


if __name__ == '__main__':
    main()
