"""Run HTTP-01, issuance, HTTPS observation and renewal on an owned Docker network."""

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
ACME_URL = 'https://pebble.course.test:14000/dir'
DENIED = 'absent.course.test'


def require(value, message):
    if not value:
        raise ValueError(message)


def execute(command, *, unchecked=False, timeout=35):
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf8', errors='replace', timeout=timeout)
    if not unchecked and result.returncode:
        tail = (result.stdout + result.stderr).strip()[-1800:]
        raise RuntimeError(re.sub(r'(?<=acme-challenge/)[A-Za-z0-9_-]+', '<token>', tail))
    return result


def docker(*command, **options):
    return execute(['docker', *command], **options)


def mount(source, target, readonly=False, kind='bind'):
    return f'type={kind},source={source},target={target}' + (',readonly' if readonly else '')


def listener(root, openssl):
    folder = root/'listener'
    folder.mkdir()
    execute([openssl, 'req', '-new', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:prime256v1', '-noenc', '-days', '2',
             '-subj', '/CN=pebble.course.test', '-addext', 'subjectAltName=DNS:pebble.course.test',
             '-addext', 'basicConstraints=critical,CA:TRUE', '-keyout', str(folder/'key.pem'), '-out', str(folder/'cert.pem')])
    (folder/'key.pem').chmod(0o644)
    config = dict(pebble=dict(listenAddress='0.0.0.0:14000', managementListenAddress='0.0.0.0:15000',
                              certificate='/listener/cert.pem', privateKey='/listener/key.pem', httpPort=5002, tlsPort=5001,
                              externalAccountBindingRequired=False, ocspResponderURL='', retryAfter=dict(authz=1, order=1)))
    (folder/'config.json').write_text(json.dumps(config), encoding='ascii')
    return folder


def exercise(args, root):
    images = json.loads((ROOT/'images.json').read_bytes())
    require(set(images) == {'pebble', 'certbot', 'nginx'} and all(re.fullmatch(r'[^\s]+@sha256:[0-9a-f]{64}', image) for image in images.values()),
            'expected_pinned_image_references')
    image_ids = {role: docker('image', 'inspect', '--format', '{{.Id}}', image).stdout.strip() for role,image in images.items()}
    owner = 'cdx3https' + uuid4().hex[:12]
    key = 'cdx3.https.owner'
    label, network = f'{key}={owner}', owner+'-private'
    domain = 'preview.course.test' if args.mode in ('guide', 'example') else 'deploy.course.test'
    source_http, source_tls = ('guide-http.conf', 'guide-tls.conf') if domain.startswith('preview') else ('edge.conf', 'tls.conf')
    probe_path, probe_body = ('/status', 'preview ready\n') if domain.startswith('preview') else ('/health', 'ready\n')
    folder = listener(root, args.openssl or shutil.which('openssl'))
    volumes = {role: owner+'-'+role for role in ('web', 'state', 'deploy')}
    common = ['--pull=never', '--label', label, '--network', network]

    def client(*command, pending=False, python=False):
        overrides = ['--entrypoint', 'python'] if python else []
        mounts = [part for role, name in volumes.items() for part in ('--mount', mount(name,'/'+role,kind='volume'))]
        return docker('run','--rm',*common,*overrides,'--env','REQUESTS_CA_BUNDLE=/issuer-connection.pem',
                      '--env','HTTP_PROXY=','--env','HTTPS_PROXY=','--env','ALL_PROXY=','--env','NO_PROXY=.course.test',
                      '--mount',mount(folder/'cert.pem','/issuer-connection.pem',True), '--mount',mount(ROOT/'deploy_lab.py','/course/deploy_lab.py',True),
                      *mounts, images['certbot'],*command, unchecked=pending, timeout=90)

    def helper(*command, pending=False):
        result = client('-B', '/course/deploy_lab.py', *command, pending=pending, python=True)
        if result.returncode:
            return None
        return json.loads(result.stdout)

    def bound(role, identity):
        form = json.loads(docker('inspect', identity).stdout)[0]
        require(form['Config']['Labels'][key] == owner and form['Image'] == image_ids[role], 'owned_image_and_label')
        require(form['State']['Running'] and not form['HostConfig']['PortBindings'], role+'_private_running')
        require(set(form['NetworkSettings']['Networks']) == {network}, role+'_network_membership')

    def web_service(role, filename, aliases, volume):
        names = [argument for alias in aliases for argument in ('--network-alias',alias)]
        sidecar = docker('run','-d','--name',owner+'-'+role,*common,*names,'--user','101:101','--cap-drop=ALL','--read-only',
                         '--tmpfs','/tmp:mode=1777','--mount',mount(ROOT/'nginx-base.conf','/etc/nginx/nginx.conf',True),
                         '--mount',mount(ROOT/filename,'/etc/nginx/lesson.conf',True),
                         '--mount',mount(volumes[volume],'/'+volume,True,'volume'),'--entrypoint','nginx',images['nginx'],'-g','daemon off;').stdout.strip()
        bound('nginx', sidecar)
        return sidecar

    def tokens(container, status):
        logs = docker('logs', container)
        return set(re.findall(r'"GET /\.well-known/acme-challenge/([A-Za-z0-9_-]+) HTTP/[^\"]+" '+str(status)+r'\b',
                              logs.stdout + logs.stderr))

    def list_resources(kind):
        return docker(kind,'ls','-aq' if kind == 'container' else '-q','--filter','label='+label).stdout.splitlines()

    proof = {'passed': True, 'mode': args.mode, 'images': image_ids, 'publicPorts': 0, 'localAcmeOnly': True}
    try:
        docker('network','create','--internal','--label',label,network)
        for name in volumes.values():
            docker('volume','create','--label',label,name)
        http = web_service('http',source_http,[domain,DENIED],'web')
        pebble = docker('run','-d','--name',owner+'-pebble',*common,'--network-alias','pebble.course.test',
                        '--env','PEBBLE_VA_NOSLEEP=1','--env','PEBBLE_AUTHZREUSE=0','--env','PEBBLE_WFE_NONCEREJECT=0',
                        '--mount',mount(folder,'/listener',True),images['pebble'],'-config','/listener/config.json','-strict=false').stdout.strip()
        bound('pebble',pebble)
        require(json.loads(docker('network','inspect',network).stdout)[0]['Internal'], 'network_must_be_internal')
        readiness = f'import ssl,urllib.request,json; assert "newOrder" in json.load(urllib.request.urlopen({ACME_URL!r},context=ssl.create_default_context(cafile="/issuer-connection.pem"),timeout=3))'
        for retry in range(3):
            ready = client('-c',readiness,python=True,pending=True)
            if not ready.returncode:
                break
            require(retry < 2, 'acme_directory_not_ready')
            time.sleep(.5)
        shared = ('--server',ACME_URL,'--config-dir','/state/config','--work-dir','/state/work','--logs-dir','/state/logs','--non-interactive')
        certonly = ('certonly',*shared,'--webroot','-w','/web','--agree-tos','--register-unsafely-without-email')
        if args.mode == 'example':
            refused = client(*certonly,'-d',DENIED,pending=True)
            require(refused.returncode and 'unauthorized' in (refused.stdout+refused.stderr).lower() and bool(tokens(http,404)), 'missing_challenge_must_be_rejected')
            proof.update(negativeChallengeRefused=True, failedHttp01Tokens=len(tokens(http,404)))
        else:
            plain = helper('http',domain,'/normal?keep=1')
            if args.mode == 'guide':
                require(plain['status'] == 204, 'guide_normal_status')
            else:
                require(plain['status'] == 308 and plain['location'] == 'https://deploy.course.test/normal?keep=1', 'expected_http_redirect')
            require(helper('http',domain,'/normal','--host','unknown.course.test')['status'] == 404, 'unknown_host_must_fail')
            issued = client(*certonly,'-d',domain,pending=True)
            require(issued.returncode == 0 and bool(tokens(http,200)), 'http01_issuance_must_pass')
            initial_tokens = tokens(http,200)
            first = helper('prepare',domain,'first')
            helper('select','first')
            # TLS has a separate private endpoint so the two port roles remain observable.
            tls_alias = 'tls.'+domain
            tls = web_service('tls',source_tls,[tls_alias],'deploy')

            def live(expected):
                last_error = ''
                for _ in range(8):
                    response = client('-B','/course/deploy_lab.py','https',tls_alias,probe_path,'--host',domain,python=True,pending=True)
                    if response.returncode == 0:
                        observed = json.loads(response.stdout)
                        if observed['certificateSha256'] == expected:
                            require(observed['status'] == 200 and observed['body'] == probe_body, 'https_expected_health_response')
                            return observed
                        last_error = 'observed a different certificate'
                    else:
                        last_error = (response.stderr.strip().splitlines() or ['probe exited without a diagnostic'])[-1]
                    time.sleep(.2)
                raise ValueError('https_certificate_or_listener_not_verified: ' + last_error)

            first_live = live(first['sha256'])
            unlisted = helper('https',tls_alias,'/outside','--host',domain)
            require(unlisted['status'] == 404 and unlisted['certificateSha256'] == first['sha256'], 'https_unknown_path_must_fail')
            proof.update(initialCertificate=first, initiallyServed=first_live, http01TokensAtIssuance=len(initial_tokens))
            if args.mode == 'variant':
                client('renew',*shared,'--cert-name',domain,'--force-renewal','--no-random-sleep-on-renew')
                require(bool(tokens(http,200)-initial_tokens), 'renewal_must_have_a_new_challenge')
                renewed = helper('prepare',domain,'renewed')
                require(renewed['sha256'] != first['sha256'] and renewed['serial'] != first['serial'], 'renewal_changed_certificate')

                def install(selected, expected):
                    helper('select',selected)
                    docker('exec',tls,'nginx','-t')
                    docker('exec',tls,'nginx','-s','reload')
                    return live(expected)

                renewed_live = install('renewed',renewed['sha256'])
                helper('mismatch','test-only')
                helper('select','mismatch')
                refused = docker('exec',tls,'nginx','-t',unchecked=True)
                require(refused.returncode and 'key values mismatch' in (refused.stdout+refused.stderr).lower(), 'mismatched_key_must_fail_before_reload')
                unaffected_live = live(renewed['sha256'])
                rollback_live = install('first',first['sha256'])
                restored_live = install('renewed',renewed['sha256'])
                proof.update(renewedCertificate=renewed, renewedServed=renewed_live, invalidCandidateRejected=True,
                             servedAfterInvalidCandidate=unaffected_live, rollbackServed=rollback_live, restoredServed=restored_live,
                             distinctNewHttp01Tokens=len(tokens(http,200)-initial_tokens))
    finally:
        for kind, removal in (('container',('rm','-f')),('network',('rm',)),('volume',('rm',))):
            for identity in list_resources(kind):
                docker(kind,*removal,identity)
            require(not list_resources(kind), 'owned_cleanup_'+kind)
    return dict(proof, ownedResourcesRemoved=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('mode', choices=('guide','example','base','variant'))
    cli.add_argument('--openssl')
    args = cli.parse_args()
    require(bool(args.openssl or shutil.which('openssl')), 'set_the_openssl_executable')
    with tempfile.TemporaryDirectory(prefix='cloud75https-') as temporary:
        root = Path(temporary).resolve()
        proof = exercise(args, root)
    require(not root.exists(), 'temporary_listener_keys_removed')
    print(json.dumps(dict(proof, temporaryListenerRemoved=True)))


if __name__ == '__main__':
    main()
