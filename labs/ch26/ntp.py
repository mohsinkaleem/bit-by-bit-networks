#!/usr/bin/env python3
"""Chapter 26 lab: what time is it? Ask over UDP, the way your computer does.

    python3 ntp.py                             ask five public time servers
    python3 ntp.py time.apple.com --explain    show the four timestamps, and the arithmetic
    python3 ntp.py serve                       run a (wrong) time server on 127.0.0.1:7123…
    python3 ntp.py 127.0.0.1:7123 --explain    …and ask it, from another window

This is SNTP, the simple version of the Network Time Protocol: one 48-byte UDP datagram
out, one back. No connection, no handshake.
"""
import argparse
import socket
import struct
import time

EPOCH = 2208988800           # NTP counts seconds from 1900; Unix from 1970. This is the difference.
SERVERS = ["time.apple.com", "time.google.com", "time.cloudflare.com", "pool.ntp.org", "ntp.ubuntu.com"]


def to_ntp(t):
    """A 64-bit NTP timestamp: 32 bits of seconds, 32 bits of fractions of a second."""
    return struct.pack("!II", int(t) + EPOCH, int((t % 1) * 2 ** 32))


def from_ntp(b):
    secs, frac = struct.unpack("!II", b)
    return secs - EPOCH + frac / 2 ** 32


# --8<-- [start:query]
def query(server, port=123, timeout=3):
    request = bytearray(48)
    request[0] = (0 << 6) | (4 << 3) | 3           # leap 0, version 4, mode 3 = "I'm a client"
    t1 = time.time()
    request[40:48] = to_ntp(t1)                     # "transmit time": the server copies it back to us
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(request, (server, port))           # one datagram out…
        reply, addr = s.recvfrom(512)               # …one back. That's the whole protocol.
    t4 = time.time()
    t2 = from_ntp(reply[32:40])                     # when the server received our request
    t3 = from_ntp(reply[40:48])                     # when it sent the reply
    offset = ((t2 - t1) + (t3 - t4)) / 2            # how far our clock is from the server's
    delay = (t4 - t1) - (t3 - t2)                   # time spent on the network, there and back
    return dict(addr=addr[0], stratum=reply[1], refid=reply[12:16], t1=t1, t2=t2, t3=t3, t4=t4,
                offset=offset, delay=delay, echoed=reply[24:32] == to_ntp(t1))
# --8<-- [end:query]


def refid(r):
    if r["stratum"] == 1:
        return r["refid"].rstrip(b"\0").decode("ascii", "replace") + " (a clock of its own)"
    if r["stratum"] == 0:
        return "“kiss of death”: " + r["refid"].decode("ascii", "replace")
    return "synchronized to " + socket.inet_ntoa(r["refid"])


def explain(r, server):
    def hms(t):
        return time.strftime("%H:%M:%S", time.localtime(t)) + f".{int((t % 1) * 1e6):06d}"
    print(f"asked {server} ({r['addr']}), stratum {r['stratum']}, {refid(r)}")
    print(f"  t1 = {hms(r['t1'])}   we sent the request (by our clock)")
    print(f"  t2 = {hms(r['t2'])}   it arrived (by the server's clock)")
    print(f"  t3 = {hms(r['t3'])}   the reply left (by the server's clock)")
    print(f"  t4 = {hms(r['t4'])}   the reply arrived (by our clock)")
    print(f"  round trip, minus the server's thinking time: (t4 - t1) - (t3 - t2) = {r['delay'] * 1000:.2f} ms")
    off = f"{r['offset'] * 1000:+.2f} ms" if abs(r["offset"]) < 10 else f"{r['offset']:+.1f} seconds"
    print(f"  our clock is off by ((t2 - t1) + (t3 - t4)) / 2 = {off}   (+ means we're behind)")
    if not r["echoed"]:
        print("  (the server didn't copy our transmit time back, so this answer can't be matched to our question!)")


# --8<-- [start:serve]
def serve(port=7123, wrong_by=600.0):
    """A time server that's ten minutes fast, like Grandpa Otto's kitchen clock."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", port))
        print(f"a time server {wrong_by:+.0f} s wrong is listening on 127.0.0.1:{port} (Ctrl-C to stop)")
        while True:
            request, client = s.recvfrom(512)
            now = time.time() + wrong_by
            reply = bytearray(48)
            reply[0] = (0 << 6) | (4 << 3) | 4       # mode 4 = "I'm a server"
            reply[1] = 2                             # stratum 2: "I get my time from someone else"
            reply[12:16] = socket.inet_aton("127.0.0.1")
            reply[24:32] = request[40:48]            # copy the client's transmit time back
            reply[32:40] = to_ntp(now)               # received
            reply[40:48] = to_ntp(time.time() + wrong_by)   # sent
            s.sendto(reply, client)
            print(f"answered {client[0]}:{client[1]}")
# --8<-- [end:serve]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("servers", nargs="*")
    p.add_argument("--explain", action="store_true")
    args = p.parse_args()
    if args.servers == ["serve"]:
        try:
            serve()
        except KeyboardInterrupt:
            print()
        return
    for spec in args.servers or SERVERS:
        host, _, port = spec.partition(":")
        try:
            r = query(host, int(port or 123))
        except OSError as e:
            print(f"{spec:<22} no answer ({e})")
            continue
        if args.explain:
            explain(r, spec)
        else:
            print(f"{spec:<22} {r['addr']:<16} stratum {r['stratum']}  offset {r['offset'] * 1000:+8.2f} ms"
                  f"  delay {r['delay'] * 1000:6.2f} ms   {refid(r)}")


if __name__ == "__main__":
    main()
