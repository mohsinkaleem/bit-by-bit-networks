#!/usr/bin/env python3
"""Chapter 29 lab: a tiny dig. Ask one DNS server one question, and show the whole answer.

    python3 dig.py info.cern.ch                     ask 1.1.1.1 for an A record
    python3 dig.py gmail.com MX @8.8.8.8            another type, another server
    python3 dig.py cloudflare.com HTTPS             a newer record type, decoded
    python3 dig.py info.cern.ch --hex               every byte of the answer, explained
    python3 dig.py org DNSKEY --udp-only            a big answer that doesn't fit in UDP (see the tc flag)
    python3 dig.py example.org --doh                the same question, sent inside HTTPS (DNS over HTTPS)
"""
import argparse
import socket
import struct
import time
import urllib.request

import dnswire


# --8<-- [start:ask]
def ask_udp(server, query, timeout=3):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(query, (server, 53))
        while True:
            reply, _ = s.recvfrom(4096)
            if reply[:2] == query[:2]:                  # same ID? (anything else is ignored: maybe a forgery)
                return reply


def ask_tcp(server, query, timeout=5):
    with socket.create_connection((server, 53), timeout=timeout) as s:
        s.sendall(struct.pack("!H", len(query)) + query)   # over TCP, each message has a 2-byte length first
        need = struct.unpack("!H", s.recv(2))[0]
        reply = b""
        while len(reply) < need:
            reply += s.recv(need - len(reply))
        return reply


def ask(server, query, udp_only=False, tcp=False):
    """UDP first; TCP if the answer was truncated (tc) or UDP got no answer at all."""
    if not tcp:
        try:
            reply = ask_udp(server, query)
            if udp_only or not (reply[2] & 0x02):       # the tc flag: "truncated, didn't fit"
                return reply, "UDP"
        except socket.timeout:
            if udp_only:
                raise
    return ask_tcp(server, query), "TCP"
# --8<-- [end:ask]


# --8<-- [start:doh]
def ask_doh(query, url="https://cloudflare-dns.com/dns-query"):
    """DNS over HTTPS: exactly the same message, as the body of an HTTP POST (RFC 8484)."""
    req = urllib.request.Request(url, data=query, method="POST",
                                 headers={"Content-Type": "application/dns-message", "Accept": "application/dns-message"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read()
# --8<-- [end:doh]


def show(reply, how, ms):
    m = dnswire.parse(reply)
    edns = m.get("edns")
    print(f";; {m['rcode']}, id {m['id']}, flags: {' '.join(m['flags'])}; over {how} in {ms:.0f} ms, {len(reply)} bytes"
          + (f"; EDNS udp {edns['udp']}" if edns else ""))
    print(f";; QUESTION: {m['question'][0][0]} {m['question'][0][1]}")
    for section in ("answer", "authority", "additional"):
        if m[section]:
            print(f";; {section.upper()}:")
            for name, ttl, rtype, data in m[section]:
                print(f"{name:<28} {ttl:>6}  {rtype:<6} {data}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("name")
    p.add_argument("args", nargs="*", help="a record type and/or @server")
    p.add_argument("--hex", action="store_true")
    p.add_argument("--tcp", action="store_true")
    p.add_argument("--udp-only", action="store_true")
    p.add_argument("--doh", action="store_true")
    p.add_argument("--dnssec", action="store_true")
    p.add_argument("--norec", action="store_true", help="don't ask for recursion (for asking authoritative servers)")
    a = p.parse_args()
    qtype = next((x.upper() for x in a.args if not x.startswith("@")), "A")
    server = next((x[1:] for x in a.args if x.startswith("@")), "1.1.1.1")
    query = dnswire.build_query(a.name, qtype, recursion=not a.norec, dnssec=a.dnssec)
    t = time.perf_counter()
    if a.doh:
        reply, how = ask_doh(query), "HTTPS (cloudflare-dns.com)"
    else:
        reply, how = ask(socket.gethostbyname(server), query, a.udp_only, a.tcp)
        how += f" from {server}"
    show(reply, how, (time.perf_counter() - t) * 1000)
    if a.hex:
        print()
        for start, end, name, meaning in dnswire.fields(reply):
            chunk = reply[start:end].hex(" ")
            if len(chunk) > 40:
                chunk = chunk[:37] + "…"
            print(f"{start:>4}  {chunk:<41} {name:<20} {meaning}")


if __name__ == "__main__":
    main()
