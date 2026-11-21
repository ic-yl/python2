"""Read real DNS replies from an owned, loopback-only CoreDNS lab."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.rdatatype


ROOT = Path(__file__).resolve().parent
ORIGIN = 'course.test.'
PROFILES = {
    'guide': ('guide.zone',),
    'example': ('variant-example.zone',),
    'cutover': ('zone-v1.txt', 'zone-after.txt'),
    'rollback': ('zone-after.txt', 'zone-rollback.txt'),
}


def require(value, rule):
    if not value:
        raise ValueError(rule)


def query(port, label, kind, transport=dns.query.udp):
    name = label + '.' + ORIGIN if label else ORIGIN
    request = dns.message.make_query(name, kind)
    result = transport(request, '127.0.0.1', port=port, timeout=2)
    records = [dict(kind=dns.rdatatype.to_text(row.rdtype), seconds=row.ttl,
                    values=[value.to_text() for value in row]) for row in result.answer]
    return dict(rcode=dns.rcode.to_text(result.rcode()), authoritative=bool(result.flags & dns.flags.AA), records=records,
                authorityKinds=[dns.rdatatype.to_text(row.rdtype) for row in result.authority])


def values(reply, kind):
    return [value for row in reply['records'] if row['kind'] == kind for value in row['values']]


def serial(port):
    reply = query(port, '', 'SOA')
    row, = values(reply, 'SOA')
    require(reply['authoritative'], 'expected_authoritative_soa')
    return int(row.split()[2])


def publish(zone, filename):
    raw = (ROOT / filename).read_bytes()
    require(0 < len(raw) <= 16384, 'zone_size')
    pending = zone.with_suffix('.pending')
    pending.write_bytes(raw)
    pending.chmod(0o644)
    pending.replace(zone)
    return hashlib.sha256(raw).hexdigest()


def standard_records(port, address, ipv6, prefix):
    results = {}
    for label, kind, expected in (('cutover', 'A', address), ('cutover', 'AAAA', ipv6),
                                   ('www', 'CNAME', 'cutover.course.test.'), ('policy', 'TXT', '"environment=training"'),
                                   ('', 'NS', 'ns.course.test.')):
        reply = query(port, label, kind)
        require(reply['authoritative'] and reply['rcode'] == 'NOERROR' and values(reply, kind) == [expected], prefix + '_' + kind)
        results[kind] = reply
    return results


def observe(mode, zone, authority, tcp, cache):
    if mode == 'guide':
        direct, forwarded, alias = query(authority, 'sample', 'A'), query(cache, 'sample', 'A'), query(authority, 'alias', 'CNAME')
        require(direct['authoritative'] and values(direct, 'A') == values(forwarded, 'A') == ['192.0.2.61'], 'guide_address')
        require(direct['records'][0]['seconds'] == 45 and 0 <= forwarded['records'][0]['seconds'] <= 12, 'guide_ttl_cap')
        require(values(alias, 'CNAME') == ['sample.course.test.'], 'guide_cname')
        return dict(authority=direct, cache=forwarded, alias=alias)
    if mode == 'example':
        present = query(authority, 'docs', 'AAAA', dns.query.udp)
        nodata = query(authority, 'ipv4-only', 'AAAA')
        absent = query(authority, 'retired', 'AAAA')
        require(values(present, 'AAAA') == ['2001:db8::70'], 'example_address')
        require(nodata['rcode'] == 'NOERROR' and not nodata['records'] and 'SOA' in nodata['authorityKinds'], 'example_type_absent')
        require(absent['rcode'] == 'NXDOMAIN' and not absent['records'] and 'SOA' in absent['authorityKinds'], 'example_name_absent')
        return dict(ipv6=present, typeAbsent=nodata, nameAbsent=absent)
    is_cutover = mode == 'cutover'
    old4, new4 = ('192.0.2.24', '192.0.2.48') if is_cutover else ('192.0.2.48', '192.0.2.24')
    old6, new6 = ('2001:db8::24', '2001:db8::48') if is_cutover else ('2001:db8::48', '2001:db8::24')
    old_serial, new_serial = (2026112001, 2026112002) if is_cutover else (2026112002, 2026112003)
    require(serial(authority) == old_serial, 'initial_soa_serial')
    standard_records(authority, old4, old6, 'initial')
    require(values(query(tcp, 'cutover', 'A', dns.query.tcp), 'A') == [old4], 'authoritative_tcp')
    clock = time.monotonic()
    require(values(query(cache, 'cutover', 'A'), 'A') == [old4], 'cache_initialized')
    next_zone = publish(zone, PROFILES[mode][1])
    while serial(authority) != new_serial:
        require(time.monotonic() - clock < 8, 'SOA_not_reloaded_to_expected_serial')
        time.sleep(.2)
    changed = standard_records(authority, new4, new6, 'changed')
    cached = query(cache, 'cutover', 'A')
    require(values(cached, 'A') == [old4], 'old_value_remains_in_cache')
    require(0 <= cached['records'][0]['seconds'] <= 12, 'old_cache_remaining_ttl')
    elapsed = round(time.monotonic() - clock, 2)
    while True:
        refreshed = query(cache, 'cutover', 'A')
        if values(refreshed, 'A') == [new4]:
            break
        require(time.monotonic() - clock < 18, 'cache_did_not_expire')
        time.sleep(.3)
    return dict(previousSerial=old_serial, currentSerial=new_serial, changedZoneSha256=next_zone, authoritativeRecords=changed,
                oldCachedAnswer=cached, refreshedCacheAnswer=refreshed, divergenceObservedSeconds=elapsed,
                cacheRefreshedSeconds=round(time.monotonic() - clock, 2), authoritativeTcpChecked=True)


def docker(*args):
    run = subprocess.run(['docker', *args], capture_output=True, text=True, encoding='utf8', errors='replace', timeout=25)
    if run.returncode:
        raise RuntimeError(f'Docker {args[0]} failed: {run.stderr.strip()[-1000:]}')
    return run.stdout


def exercise(mode, folder):
    image = (ROOT / 'image.txt').read_text(encoding='ascii').strip()
    require(bool(re.fullmatch(r'docker\.io/coredns/coredns@sha256:[a-f0-9]{64}', image)), 'exact_official_image_digest_required')
    expected_image = docker('image', 'inspect', '--format', '{{.Id}}', image).strip()
    # The read-only bind mount is read as an unprivileged container UID.
    folder.chmod(0o755)
    corefile = folder / 'Corefile'
    shutil.copyfile(ROOT / 'Corefile', corefile)
    corefile.chmod(0o644)
    zone = folder / 'course.test.zone'
    initial = publish(zone, PROFILES[mode][0])
    name = 'cdx3dnslesson' + uuid4().hex[:12]
    label = 'cdx3.dns.owner=' + name
    container = docker('run', '-d', '--name', name, '--label', label, '--pull=never', '--read-only',
                       '--cap-drop=ALL', '--cap-add=NET_BIND_SERVICE', '--user', '65532:65532',
                       '--publish', '127.0.0.1::1053/udp', '--publish', '127.0.0.1::1053/tcp',
                       '--publish', '127.0.0.1::1054/udp', '--mount', f'type=bind,source={folder},target=/course,readonly',
                       image, '-conf', '/course/Corefile').strip()
    try:
        info = json.loads(docker('inspect', container))[0]
        require(info['Config']['Labels']['cdx3.dns.owner'] == name and info['Image'] == expected_image, 'owned_container_identity')
        if not info['State']['Running']:
            raise ValueError('coredns_startup: ' + docker('logs', '--tail', '6', container).strip())
        bindings = {key: value for key, value in info['NetworkSettings']['Ports'].items() if value}
        require(set(bindings) == {'1053/udp', '1053/tcp', '1054/udp'}, 'published_port_set')
        for published in bindings.values():
            require(len(published) == 1 and published[0]['HostIp'] == '127.0.0.1', 'dns_must_bind_only_to_loopback')
        authority, tcp, cache = (int(bindings[key][0]['HostPort']) for key in ('1053/udp', '1053/tcp', '1054/udp'))
        for attempt in range(3):
            try:
                serial(authority)
                break
            except (dns.exception.Timeout, ConnectionResetError):
                if attempt == 2:
                    raise ValueError('coredns_readiness: ' + docker('logs', '--tail', '6', container).strip())
                time.sleep(.3)
        observations = observe(mode, zone, authority, tcp, cache)
    finally:
        owned = json.loads(docker('inspect', container))[0]
        require(owned['Config']['Labels']['cdx3.dns.owner'] == name, 'cleanup_ownership')
        docker('rm', '-f', container)
        require(not docker('ps', '-aq', '--filter', 'label=' + label).strip(), 'owned_dns_container_remaining')
    return dict(mode=mode, passed=True, observations=observations, initialZoneSha256=initial, runningImage=expected_image,
                clientVersion=version('dnspython'), loopbackOnly=True, ownedContainerRemoved=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('mode', choices=PROFILES)
    args = cli.parse_args()
    require(version('dnspython') == '2.9.2', 'install_the_locked_dnspython_version')
    with tempfile.TemporaryDirectory(prefix='cdx3dnslesson-') as scratch:
        folder = Path(scratch).resolve()
        report = exercise(args.mode, folder)
    require(not folder.exists(), 'temporary_zone_remaining')
    print(json.dumps(dict(report, temporaryZoneRemoved=True)))


if __name__ == '__main__':
    main()

