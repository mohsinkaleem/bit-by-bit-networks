#!/usr/bin/env python3
"""Chapter 34 lab: anycast. One address, hundreds of computers; which one answers you?

    python3 anycast.py             ask all 13 DNS root servers which copy of them answered, and how far away it is
    python3 anycast.py 1.1.1.1 8.8.8.8 9.9.9.9    the same for other DNS servers

DNS servers answer a special question, "hostname.bind" (or "id.server") in the CHAOS class, with
the name of the machine that answered. It's how their operators debug anycast. The round trip is
timed from question to answer, over TCP (UDP DNS is sometimes filtered; so is ping).
"""
import socket
import struct
import sys
import time


def chaos_query(name):
    """A DNS question in class CH (3) for a TXT record, by hand (Chapter 29 does this properly)."""
    q = struct.pack("!HHHHHH", 0xB17E, 0x0000, 1, 0, 0, 0)
    q += b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
    return q + struct.pack("!HH", 16, 3)


def first_txt(reply):
    """The first TXT string in the answer (skipping the header and the question)."""
    i = 12
    while reply[i]:
        i += 1 + reply[i]
    i += 5                                   # the zero byte, type and class
    if struct.unpack("!H", reply[6:8])[0] == 0:
        return "(no answer)"
    i += 12 if reply[i] & 0xC0 == 0xC0 else 0    # a pointer to the name, type, class, TTL, length
    return reply[i + 1:i + 1 + reply[i]].decode("utf-8", "replace")


# --8<-- [start:ask]
def ask(server):
    """Connect over TCP, then ask who you are, timing each question and answer."""
    addr = socket.gethostbyname(server)
    s = socket.create_connection((addr, 53), timeout=4)
    names, rtt = [], float("inf")
    for qname in ("hostname.bind", "id.server"):
        q = chaos_query(qname)
        t0 = time.monotonic()
        s.sendall(struct.pack("!H", len(q)) + q)            # DNS over TCP: a 2-byte length first
        n = struct.unpack("!H", s.recv(2))[0]
        reply = b""
        while len(reply) < n:
            reply += s.recv(n - len(reply))
        rtt = min(rtt, (time.monotonic() - t0) * 1000)      # one round trip, question to answer
        names.append(first_txt(reply))
    s.close()
    name = next((n for n in names if n != "(no answer)"), "(won't say)")
    return addr, rtt, name
# --8<-- [end:ask]


def main():
    servers = sys.argv[1:] or [f"{c}.root-servers.net" for c in "abcdefghijklm"]
    rows = []
    for server in servers:
        try:
            rows.append((server,) + ask(server))
        except OSError as e:
            rows.append((server, "?", float("inf"), f"(no answer: {e})"))
    rows.sort(key=lambda r: r[2])
    for server, addr, rtt, name in rows:
        print(f"{server:<20} {addr:<16} {rtt:6.1f} ms   answered by {name}")


if __name__ == "__main__":
    main()
