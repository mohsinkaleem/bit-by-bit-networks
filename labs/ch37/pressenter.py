#!/usr/bin/env python3
"""Chapter 37 lab: press Enter, slowly. Every step of fetching a URL, done by hand and timed.

    python3 pressenter.py https://example.org/
    python3 pressenter.py https://en.wikipedia.org/wiki/Computer_network

It finds your router, asks your DNS server itself (with Chapter 29's code), opens the TCP connection,
does TLS with Python's ssl module (Chapter 32 built the same thing by hand), and speaks HTTP/2 with
Chapter 33's frames and header compression. Then it draws a waterfall of where the time went.
"""
import platform
import re
import socket
import ssl
import struct
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "ch29"), str(HERE.parent / "ch33")]
import dig                                                     # noqa: E402  (Chapter 29)
import dnswire                                                 # noqa: E402
import h2client                                                # noqa: E402  (Chapter 33)
import hpack                                                   # noqa: E402

T0 = time.monotonic()
PHASES = []


def now():
    return (time.monotonic() - T0) * 1000


def phase(name, start, note=""):
    PHASES.append((name, start, now()))
    print(f"   ⏱  {name}: {now() - start:.1f} ms {note}\n")


# ---------------------------------------------------------------- 0. where am I?

# --8<-- [start:local]
def local_network():
    """The default route and the router's MAC address, as the operating system knows them (Chapters 20, 21)."""
    gw = dev = mac = None
    if platform.system() == "Linux":
        for line in Path("/proc/net/route").read_text().splitlines()[1:]:
            f = line.split()
            if f[1] == "00000000":                                      # destination 0.0.0.0: the default route
                dev, gw = f[0], socket.inet_ntoa(struct.pack("<I", int(f[2], 16)))
        for line in Path("/proc/net/arp").read_text().splitlines()[1:]:
            f = line.split()
            if f[0] == gw:
                mac = f[3]
    else:
        out = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True).stdout
        gw = re.search(r"gateway: (\S+)", out).group(1)
        dev = re.search(r"interface: (\S+)", out).group(1)
        arp = subprocess.run(["arp", "-n", gw], capture_output=True, text=True).stdout
        m = re.search(r" at ([0-9a-f:]+)", arp)
        mac = m.group(1) if m else None
    return gw, dev, mac


def dns_server():
    """The resolver the operating system uses (DHCP told it, Chapter 22)."""
    for line in Path("/etc/resolv.conf").read_text().splitlines():
        if line.startswith("nameserver"):
            return line.split()[1]
    return "1.1.1.1"
# --8<-- [end:local]


# ---------------------------------------------------------------- the steps

def resolve(host, server):
    start = now()
    answers = {}
    for qtype in ("A", "AAAA", "HTTPS"):
        t = now()
        try:
            reply, how = dig.ask(server, dnswire.build_query(host, qtype))
        except OSError as e:
            print(f"   {qtype:<5} no answer ({e})")
            continue
        msg = dnswire.parse(reply)
        answers[qtype] = [str(r[3]) for r in msg["answer"] if r[2] == qtype]
        shown = ", ".join(answers[qtype]) or "(none)"
        print(f"   {qtype:<5} {shown[:92]}   [{how}, {now() - t:.1f} ms]")
    phase("DNS", start, f"(three questions to {server})")
    return answers


# --8<-- [start:steps]
def connect(host, ip, port=443):
    start = now()
    sock = socket.create_connection((ip, port), timeout=10)
    src = sock.getsockname()
    print(f"   {src[0]}:{src[1]} → {ip}:{port}  (the port on our side was picked by the operating system)")
    phase("TCP handshake", start, "(SYN, SYN-ACK, ACK: one round trip)")
    return sock


def secure(sock, host):
    start = now()
    ctx = ssl.create_default_context()
    ctx.set_alpn_protocols(["h2", "http/1.1"])
    tls = ctx.wrap_socket(sock, server_hostname=host)
    cert = tls.getpeercert()
    issuer = dict(x[0] for x in cert["issuer"]).get("commonName")
    print(f"   {tls.version()}, {tls.cipher()[0]}; ALPN chose {tls.selected_alpn_protocol()!r}")
    print(f"   certificate for {', '.join(v for _, v in cert['subjectAltName'][:3])}, from {issuer}, until {cert['notAfter']}")
    phase("TLS handshake", start, "(ClientHello … Finished: one more round trip)")
    return tls


def fetch(tls, host, path):
    start = now()
    tls.sendall(h2client.PREFACE + h2client.frame(4, 0, 0) + h2client.frame(
        1, h2client.END_STREAM | h2client.END_HEADERS, 1, hpack.encode(
            [(":method", "GET"), (":scheme", "https"), (":authority", host), (":path", path),
             ("user-agent", "bitbybit-pressenter/1.0"), ("accept-encoding", "identity")], hpack.Table())))
    print(f"   → HTTP/2 preface, SETTINGS, HEADERS: GET {path}")
    table, body, first, headers = hpack.Table(), 0, None, {}
    while True:
        ftype, flags, sid, payload = h2client.read_frame(tls)
        if ftype == 4 and not flags & 1:
            tls.sendall(h2client.frame(4, 1, 0))                          # acknowledge the server's SETTINGS
        elif ftype == 1 and sid == 1:
            first = first or now()
            headers = {n: v for n, v, _, _ in hpack.decode(payload, table)}
            print(f"   ← HEADERS: {headers.get(':status')}, {headers.get('content-type')}, server {headers.get('server')}"
                  + (f", cache {headers['cf-cache-status']}" if "cf-cache-status" in headers else "")
                  + (f", age {headers['age']} s" if "age" in headers else ""))
        elif ftype == 0 and sid == 1:
            first = first or now()
            body += len(payload)
            if payload:
                tls.sendall(h2client.frame(8, 0, 0, struct.pack("!I", len(payload))) +
                            h2client.frame(8, 0, 1, struct.pack("!I", len(payload))))   # keep the windows open
        if sid == 1 and flags & h2client.END_STREAM:
            break
    PHASES.append(("waiting for the first byte", start, first))
    print(f"   ⏱  waiting for the first byte: {first - start:.1f} ms (the request's round trip, and the server's thinking)")
    print(f"   ← DATA: {body:,} bytes")
    phase("downloading", first, "")
    tls.sendall(h2client.frame(7, 0, 0, struct.pack("!II", 0, 0)))
    tls.close()
# --8<-- [end:steps]


def waterfall():
    total = max(end for _, _, end in PHASES)
    print(f"the whole thing: {total:.0f} ms\n")
    width = 60
    for name, start, end in PHASES:
        a, b = int(start / total * width), max(int(start / total * width) + 1, int(end / total * width))
        print(f"   {name:<28} {' ' * a}{'█' * (b - a)}{' ' * (width - b)}  {end - start:6.1f} ms")


def main():
    url = urllib.parse.urlsplit(sys.argv[1] if len(sys.argv) > 1 else "https://example.org/")
    host, path = url.hostname, url.path or "/"
    print(f"1. the URL: scheme {url.scheme}, host {host}, path {path}\n")
    gw, dev, mac = local_network()
    print(f"2. this computer: default route via {gw} on {dev}; the router's MAC address is {mac or '(not in the ARP cache yet)'}\n")
    server = dns_server()
    print(f"3. DNS: asking {server}")
    answers = resolve(host, server)
    ip = answers.get("A", [None])[0]
    if not ip:
        raise SystemExit("no IPv4 address")
    print(f"4. TCP: connecting to {ip}")
    sock = connect(host, ip)
    print("5. TLS")
    tls = secure(sock, host)
    if tls.selected_alpn_protocol() != "h2":
        raise SystemExit("this server didn't choose HTTP/2; try another")
    print("6. HTTP/2")
    fetch(tls, host, path)
    waterfall()


if __name__ == "__main__":
    main()
