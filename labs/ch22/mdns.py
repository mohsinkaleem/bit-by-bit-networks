#!/usr/bin/env python3
"""Chapter 22 lab: find computers on your own network by name, with no name server at all (mDNS).

    python3 mdns.py raspberrypi.local            who has this name? (ask the whole network)
    python3 mdns.py --services                   what kinds of services are being offered here?
    python3 mdns.py --browse _ssh._tcp           who offers this one?

Questions go to the multicast address 224.0.0.251, port 5353, and whoever has the answer replies.
"""
import argparse
import os
import socket
import struct
import time

GROUP = ("224.0.0.251", 5353)
TYPES = {1: "A", 12: "PTR", 16: "TXT", 28: "AAAA", 33: "SRV", 47: "NSEC"}


def encode(name):
    return b"".join(bytes([len(p)]) + p.encode() for p in name.rstrip(".").split(".")) + b"\0"


def decode(msg, i):
    parts = []
    while msg[i]:
        if msg[i] & 0xC0 == 0xC0:
            parts.append(decode(msg, struct.unpack_from("!H", msg, i)[0] & 0x3FFF)[0])
            return ".".join(parts), i + 2
        parts.append(msg[i + 1:i + 1 + msg[i]].decode(errors="replace"))
        i += 1 + msg[i]
    return ".".join(parts), i + 1


# --8<-- [start:query]
def query(name, qtype, wait=2.0):
    """Ask the whole local network. Because we don't send from port 5353, anyone who knows the answer
    replies straight to us ("legacy unicast"), so this needs no special permissions."""
    qid = int.from_bytes(os.urandom(2), "big")
    msg = struct.pack("!HHHHHH", qid, 0, 1, 0, 0, 0) + encode(name) + struct.pack("!HH", qtype, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)     # mDNS packets never leave the network
    sock.sendto(msg, GROUP)
    sock.settimeout(0.3)
    answers, deadline = [], time.time() + wait
    while time.time() < deadline:
        try:
            data, sender = sock.recvfrom(9000)
        except socket.timeout:
            continue
        answers.extend((sender[0], rec) for rec in records(data))
    return answers
# --8<-- [end:query]


def records(data):
    _, _, qd, an, ns, ar = struct.unpack_from("!HHHHHH", data)
    i = 12
    for _ in range(qd):
        _, i = decode(data, i)
        i += 4
    out = []
    for _ in range(an + ns + ar):
        name, i = decode(data, i)
        rtype, _, ttl, size = struct.unpack_from("!HHIH", data, i)
        i += 10
        value = data[i:i + size]
        if rtype == 1:
            shown = socket.inet_ntoa(value)
        elif rtype == 28:
            shown = socket.inet_ntop(socket.AF_INET6, value)
        elif rtype == 12:
            shown = decode(data, i)[0]
        elif rtype == 33:
            port = struct.unpack_from("!H", value, 4)[0]
            shown = f"{decode(data, i + 6)[0]}, port {port}"
        else:
            shown = f"{size} bytes"
        out.append((name, TYPES.get(rtype, str(rtype)), ttl, shown))
        i += size
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("name", nargs="?")
    p.add_argument("--services", action="store_true")
    p.add_argument("--browse", metavar="SERVICE")
    args = p.parse_args()
    if args.services:
        target, qtype = "_services._dns-sd._udp.local", 12
    elif args.browse:
        target, qtype = args.browse.rstrip(".") + ".local", 12
    elif args.name:
        target, qtype = args.name, 1
    else:
        return p.print_help()
    print(f"asking everyone on the network: {target}?")
    seen = set()
    for sender, (name, rtype, ttl, value) in query(target, qtype):
        key = (sender, name, rtype, value)
        if key not in seen:
            seen.add(key)
            print(f"  from {sender:<15} {name} {rtype} {value}   (remember for {ttl} s)")
    if not seen:
        print("  nobody answered")


if __name__ == "__main__":
    main()
