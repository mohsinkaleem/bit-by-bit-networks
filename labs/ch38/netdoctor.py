#!/usr/bin/env python3
"""Chapter 38 lab: a network doctor. It checks one layer at a time, from the bottom up, and says where it breaks.

    python3 netdoctor.py                 check this computer's connection
    python3 netdoctor.py --big           also download 2 MB (catches problems that only big packets have)
    python3 netdoctor.py --big http://10.38.2.2:8038/big.bin     …from a server of your choice

Each check only runs if the ones below it passed, because a broken lower layer makes everything
above it look broken too. Works on macOS and Linux, without sudo.
"""
import platform
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ch29"))
import dig                                                      # noqa: E402  (Chapter 29)
import dnswire                                                  # noqa: E402

LINUX = platform.system() == "Linux"
results = []


def report(ok, layer, what, detail=""):
    mark = {True: "✓", False: "✗", None: "!"}[ok]
    print(f"  {mark} {layer:<10} {what}" + (f"  ({detail})" if detail else ""), flush=True)
    results.append((ok, layer, what))
    return ok


def ping(host, size=None, df=False, count=2):
    """The system's ping (it can send ICMP without sudo). Returns (received, output)."""
    if LINUX:
        cmd = ["ping", "-c", str(count), "-W", "1"] + (["-M", "do"] if df else []) + (["-s", str(size)] if size else [])
    else:
        cmd = ["ping", "-c", str(count), "-t", str(count + 1)] + (["-D"] if df else []) + (["-s", str(size)] if size else [])
    r = subprocess.run(cmd + [host], capture_output=True, text=True)
    out = r.stdout + r.stderr
    m = re.search(r"(\d+) (?:packets )?received", out)
    return (int(m.group(1)) if m else 0), out


def gateway():
    if LINUX:
        for line in Path("/proc/net/route").read_text().splitlines()[1:]:
            f = line.split()
            if f[1] == "00000000":
                return socket.inet_ntoa(bytes.fromhex(f[2])[::-1])
        return None
    out = subprocess.run(["route", "-n", "get", "default"], capture_output=True, text=True).stdout
    m = re.search(r"gateway: (\S+)", out)
    return m.group(1) if m else None


def resolver():
    for line in Path("/etc/resolv.conf").read_text().splitlines():
        if line.startswith("nameserver"):
            return line.split()[1]


# --8<-- [start:checks]
def check():
    print("layer by layer, from the bottom up:\n")
    # 1. an address, and a route out (Chapters 20 and 22)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 53))                                 # sends nothing: just asks for a route
        me = s.getsockname()[0]
    except OSError as e:
        return report(False, "IP", "no route to the internet", f"{e.strerror}: no default route? not connected?")
    if me.startswith("169.254."):
        return report(False, "IP", f"address {me}", "a self-assigned address: DHCP failed (Chapter 22)")
    report(True, "IP", f"this computer is {me}, and has a route out")
    # 2. the router (Chapter 21)
    gw = gateway()
    got, _ = ping(gw)
    report(bool(got), "gateway", f"the router, {gw}, answers ping" if got else f"the router, {gw}, doesn't answer ping",
           "" if got else "a Wi-Fi or cable problem, or it ignores ping: carry on and see")
    # 3. the internet, by address (Chapters 21, 27)
    t0 = time.monotonic()
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        report(True, "internet", "a TCP connection to 1.1.1.1:443 works", f"{(time.monotonic() - t0) * 1000:.0f} ms")
    except OSError as e:
        return report(False, "internet", "can't reach 1.1.1.1 by address", f"{e.strerror or e}: the problem is between the router and the internet")
    # 4. names (Chapter 29)
    server = resolver()
    try:
        ans = dnswire.parse(dig.ask_udp(server, dnswire.build_query("example.org"), timeout=2))["answer"]
        report(True, "DNS", f"{server} answers over UDP", f"example.org is {ans[-1][3]}")
    except OSError:
        try:
            dig.ask_tcp(server, dnswire.build_query("example.org"), timeout=3)
            report(None, "DNS", f"{server} only answers over TCP", "something blocks UDP port 53")
        except OSError:
            try:
                dig.ask_udp("1.1.1.1", dnswire.build_query("example.org"), timeout=2)
                return report(False, "DNS", f"the configured DNS server, {server}, doesn't answer",
                              "but 1.1.1.1 does: fix the DNS setting (DHCP, Chapter 22)")
            except OSError:
                return report(False, "DNS", "no DNS server answers", "DNS is blocked, or the internet only half works")
    # 5. a secure web page (Chapters 30, 32)
    try:
        t0 = time.monotonic()
        with ssl.create_default_context().wrap_socket(socket.create_connection(("example.org", 443), timeout=5),
                                                      server_hostname="example.org") as t:
            t.sendall(b"GET / HTTP/1.1\r\nHost: example.org\r\nConnection: close\r\n\r\n")
            first = t.recv(64).split(b"\r\n")[0].decode()
        report(True, "HTTPS", f"https://example.org/: {first}", f"{(time.monotonic() - t0) * 1000:.0f} ms")
    except (OSError, ssl.SSLError) as e:
        report(False, "HTTPS", "the web page failed", str(e))
        if "timed out" in str(e):                                  # connected, then silence: big packets lost?
            mtu_report(socket.gethostbyname("example.org"))
        return False
    return True


def mtu_report(target):
    size, told = path_mtu(target)
    return report(None, "MTU", f"the biggest packet that reaches {target} is {size} bytes",
                  f"a router said mtu {told}" if told else "and nobody said why: ICMP “too big” messages are being lost")
# --8<-- [end:checks]


# --8<-- [start:big]
def big_download(url="https://speed.cloudflare.com/__down?bytes=2000000", nbytes=2_000_000, limit=8):
    """Small things working and big things hanging is the signature of a path MTU problem (Chapter 38)."""
    u = urllib.parse.urlsplit(url)
    t0 = time.monotonic()
    got = 0
    try:
        t = socket.create_connection((u.hostname, u.port or (443 if u.scheme == "https" else 80)), timeout=limit)
        if u.scheme == "https":
            t = ssl.create_default_context().wrap_socket(t, server_hostname=u.hostname)
        with t:
            t.settimeout(limit)
            t.sendall(f"GET {u.path}{'?' + u.query if u.query else ''} HTTP/1.1\r\nHost: {u.hostname}\r\nConnection: close\r\n\r\n".encode())
            while got < nbytes and time.monotonic() - t0 < limit:
                data = t.recv(65536)
                if not data:
                    break
                got += len(data)
    except (OSError, ssl.SSLError):
        pass
    secs = time.monotonic() - t0
    if got >= nbytes:
        return report(True, "big", f"a {nbytes / 1e6:.0f} MB download finished", f"{secs:.1f} s, {got * 8 / secs / 1e6:.0f} Mbit/s")
    report(False, "big", f"a {nbytes / 1e6:.0f} MB download stalled after {got:,} bytes",
           "small packets get through, big ones vanish: suspect the path MTU")
    return False
# --8<-- [end:big]


# --8<-- [start:mtu]
def path_mtu(host="1.1.1.1"):
    """Find the biggest packet that gets through unfragmented, by halving the gap (as in Chapter 1's guessing game)."""
    lo, hi = 548, 1500                                           # every IPv4 path should manage 576
    while lo < hi:
        mid = (lo + hi + 1) // 2
        got, out = ping(host, size=mid - 28, df=True, count=1)    # 20 bytes of IP header + 8 of ICMP
        if got:
            lo = mid
        else:
            hi = mid - 1
    m = re.search(r"mtu ?=? ?(\d+)", out)
    return lo, m.group(1) if m else None
# --8<-- [end:mtu]


def main():
    ok = check()
    if ok and "--big" in sys.argv:
        rest = sys.argv[sys.argv.index("--big") + 1:]
        url = rest[0] if rest else "https://speed.cloudflare.com/__down?bytes=2000000"
        if not big_download(url):
            mtu_report(socket.gethostbyname(urllib.parse.urlsplit(url).hostname))
    print()
    bad = [r for r in results if r[0] is not True]
    print("diagnosis: " + ("everything checked works." if not bad else f"look at the {bad[0][1]} layer first: {bad[0][2]}."))


if __name__ == "__main__":
    main()
