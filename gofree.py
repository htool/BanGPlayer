#!/usr/bin/python3
"""Navico GoFree multicast discovery (239.2.1.1:2052)."""

import fcntl
import json
import logging
import socket
import struct
import sys
import time

GOFREE_GROUP = '239.2.1.1'
GOFREE_PORT = 2052
GOFREE_WAIT = 2.5

TARGET_METAVAR = 'IP_OR_NAME'
TARGET_HELP = 'IP or GoFree name of Zeus/Vulcan MFD (omit to auto-discover)'


def add_target_args(parser):
    parser.add_argument(
        'target', nargs='?', default=None, metavar=TARGET_METAVAR,
        help=TARGET_HELP
    )
    parser.add_argument(
        '--discover', action='store_true',
        help='list GoFree MFDs on the LAN and exit'
    )


def ipv4_addrs():
    addrs = ['0.0.0.0']
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for _idx, name in socket.if_nameindex():
            try:
                ifreq = fcntl.ioctl(
                    s.fileno(),
                    0x8915,
                    struct.pack('256s', name.encode('utf-8')[:15])
                )
                ip = socket.inet_ntoa(ifreq[20:24])
                if ip and not ip.startswith('127.'):
                    addrs.append(ip)
            except OSError:
                continue
    finally:
        s.close()
    return addrs


def parse_gofree(data, addr):
    text = data.decode('utf-8', errors='replace').strip('\x00').strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
    except ValueError:
        logging.debug('GoFree non-JSON from %s: %r', addr[0], text[:160])
        return None
    if isinstance(obj, list):
        obj = obj[0] if obj else {}
    if not isinstance(obj, dict):
        return None
    name = obj.get('Name') or obj.get('name') or ''
    ip = obj.get('IP') or obj.get('ip') or obj.get('IPAddress') or addr[0]
    model = obj.get('Model') or obj.get('model') or ''
    # Prefer the packet source if the MFD also announces a leftover link-local.
    if ip.startswith('169.254.') and not addr[0].startswith('169.254.'):
        logging.debug('GoFree announced %s, using source %s', ip, addr[0])
        ip = addr[0]
    return {'name': name, 'ip': ip, 'model': model}


def listen(wait=GOFREE_WAIT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass
    sock.bind(('', GOFREE_PORT))
    for ip in ipv4_addrs():
        try:
            mreq = struct.pack('=4s4s', socket.inet_aton(GOFREE_GROUP), socket.inet_aton(ip))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            logging.debug('GoFree joined %s on %s', GOFREE_GROUP, ip)
        except OSError as err:
            logging.debug('GoFree join %s failed: %s', ip, err)
    sock.settimeout(0.25)
    found = {}
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        rec = parse_gofree(data, addr)
        if rec and rec['ip']:
            found[rec['ip']] = rec
            logging.debug('GoFree %s', rec)
    sock.close()
    return list(found.values())


def is_ipv4(value):
    try:
        socket.inet_aton(value)
        return True
    except socket.error:
        return False


def print_devices(devices):
    print('Found %d Navico MFD(s) via GoFree:' % len(devices))
    for d in devices:
        extra = d['model']
        if extra and extra != d['name']:
            print('  %s  (%s)  %s' % (d['name'] or '-', extra, d['ip']))
        else:
            print('  %s  %s' % (d['name'] or '-', d['ip']))


def match(devices, query):
    q = query.lower()
    exact = [d for d in devices if d['ip'] == query
             or d['name'].lower() == q
             or d['model'].lower() == q]
    if exact:
        return exact
    return [d for d in devices
            if q in d['name'].lower() or q in d['model'].lower()]


def resolve(target):
    if target and is_ipv4(target):
        return target
    devices = listen()
    if target:
        matches = match(devices, target)
        if len(matches) == 1:
            d = matches[0]
            logging.info('GoFree: %s (%s) at %s', d['name'] or d['model'] or target, d['model'], d['ip'])
            return d['ip']
        if len(matches) > 1:
            print_devices(matches)
            print('Pass a more specific name or IP.')
            sys.exit(1)
        try:
            ip = socket.getaddrinfo(target, None, socket.AF_INET)[0][4][0]
            logging.info('Resolved %s to %s', target, ip)
            return ip
        except socket.gaierror as err:
            print('Could not find MFD %r via GoFree or DNS: %s' % (target, err))
            sys.exit(1)
    if not devices:
        print('No Navico MFD found via GoFree (%s:%d). Pass an IP or name.' % (GOFREE_GROUP, GOFREE_PORT))
        sys.exit(1)
    if len(devices) > 1:
        print_devices(devices)
        print('Pass a name or IP to choose one.')
        sys.exit(1)
    d = devices[0]
    logging.info('GoFree: %s (%s) at %s', d['name'] or d['model'], d['model'], d['ip'])
    return d['ip']


def discover_and_exit():
    devices = listen()
    if not devices:
        print('No Navico MFD found via GoFree (%s:%d).' % (GOFREE_GROUP, GOFREE_PORT))
        sys.exit(1)
    print_devices(devices)
    sys.exit(0)
