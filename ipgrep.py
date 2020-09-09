#! /usr/bin/env python3

import argparse
import csv
import fileinput
import json
import pycares
import re
import requests
import select
import socket
import sys

IPTOASN_BASE_ENDPOINT_URL = "https://api.iptoasn.com/v1/as/ip/"


class IPLookup(object):
    def lookup(self, ip):
        url = IPTOASN_BASE_ENDPOINT_URL + ip
        r = requests.get(url)
        if r.status_code != 200:
            return None
        info = r.json()
        if info is None or info['announced'] is False:
            return None
        return info


class ASN(object):
    def __init__(self, number, country_code, description):
        self.number = number
        self.description = description


class Host(object):
    def __init__(self, ip=None, name=None, asn=None):
        self.ip = ip
        self.name = name
        self.asn = asn

    def __repr__(self):
        return "ip: {}\t name: {} ASN: {}".format(
            self.ip, self.name, self.asn.description)


class ResolverResponse(object):
    def __init__(self, name, channel, res):
        def cb(results, err):
            if results is None:
                return
            for result in results:
                res.add((result.host, self.name))

        self.name = name
        channel.query(name, pycares.QUERY_TYPE_A, cb)


class Resolver(object):
    """name resolver, ignores locally configured search domains"""
    def __init__(self, timeout, tries, servers=None):
        flags = pycares.ARES_FLAG_NOSEARCH
        timeout = float(timeout)
        tries = int(tries)
        if servers:
            self.channel = pycares.Channel(flags, timeout, tries,
                                           servers=servers)
        else:
            self.channel = pycares.Channel(flags, timeout, tries)

    def _wait(self):
        while True:
            read_fds, write_fds = self.channel.getsock()
            if not read_fds and not write_fds:
                break
            timeout = self.channel.timeout()
            if timeout == 0.0:
                self.channel.process_fd(pycares.ARES_SOCKET_BAD,
                                        pycares.ARES_SOCKET_BAD)
                continue
            rlist, wlist, xlist = select.select(read_fds, write_fds, [],
                                                timeout)
            for fd in rlist:
                self.channel.process_fd(fd, pycares.ARES_SOCKET_BAD)
            for fd in wlist:
                self.channel.process_fd(pycares.ARES_SOCKET_BAD, fd)

    def resolve(self, names):
        res = set()
        for name in names:
            response = ResolverResponse(name, self.channel, res)
        self._wait()
        return res


class Extractor(object):
    def __init__(self, txt):
        self.txt = txt

    def extract_names(self):
        label_r = b"[a-z0-9-]{1,63}([.]|\\[.]|,|\[[.]\]|[.]\]| [.])"
        label_last = b"[a-z0-9]{1,16}($|[^a-z0-9])"
        matches = re.findall(b"(" +
                             b"(" + label_r + b"){1,8}" +
                             label_last + b")[.]?",
                             self.txt, re.I)
        names = [re.sub(b",", b".", x[0]).lower() for x in matches]
        names = [re.sub(b"[^a-z0-9-.]", b"", x).decode() for x in names]
        return names

    def extract_ips(self):
        matches = re.findall(b"([^0-9]|^)([0-9]{1,3}(\.|\s*\[\.?\]\s*)" +
                             b"[0-9]{1,3}(\.|\s*\[\.?\]\s*)" +
                             b"[0-9]{1,3}(\.|\s*\[\.?\]\s*)" +
                             b"[0-9]{1,3})([^0-9]|$)", self.txt)
        ips = [re.sub(b"[^0-9.]", b"", x[1]).decode() for x in matches]
        return ips


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--timeout', default=5.0,
                        help='seconds each name server is given to respond to a query')
    parser.add_argument('--tries', default=4,
                        help='times the resolver will try contacting each name server')
    parser.add_argument('--servers', default='',
                        help='comma-separated list of nameservers used to do the lookups')
    parser.add_argument('files', metavar='FILE', nargs='*', help='files to grep (default: stdin)')
    args = parser.parse_args()

    ip_lookup = IPLookup()
    resolver = Resolver(args.timeout, args.tries, args.servers.split(','))
    csvw = csv.writer(sys.stdout, delimiter="\t")
    names, ips = set(), set()

    for line in fileinput.input(files=args.files, mode='rb'):
        extractor = Extractor(line)
        names = names | set(extractor.extract_names())
        ips = ips | set(extractor.extract_ips())

    resolved = resolver.resolve(names)
    hosts_fromnames = set([Host(ip=ip, name=name) for ip, name in resolved])
    hosts_fromips = set([Host(ip=ip) for ip in ips])
    hosts = hosts_fromnames | hosts_fromips

    for host in hosts:
        subnet = ip_lookup.lookup(host.ip)
        asn = ASN(0, "-", "-")
        if subnet:
            asn = ASN(subnet['as_number'], subnet['as_country_code'],
                      "AS{}: {} ({})".format(subnet['as_number'],
                                             subnet['as_description'],
                                             subnet['as_country_code']))
        if not host.name:
            host.name = "-"
        host.asn = asn

    for host in sorted(hosts, key=lambda x: (x.asn.description, x.ip, x.name)):
        csvw.writerow([host.ip, host.name, host.asn.description])
