#!/usr/bin/env python3
"""Chapter 25 lab: find every IPv6 device on your network, with no sudo and no IPv6 internet.

    python3 neighbours.py en0              (macOS: your Wi-Fi is usually en0)
    python3 neighbours.py wlan0            (Linux)
    python3 neighbours.py en0 --listen 600 (macOS only) decode the neighbour discovery messages
                                           that arrive: router advertisements, "who has?" and answers

Every IPv6 device has a link-local address and listens to ff02::1, "all nodes on this link",
so one ping to that group gets an answer from all of them. Then we ask the computer's
neighbour table (IPv6's version of the ARP table) for their card addresses.
"""
import ipaddress
import re
import select
import socket
import struct
import subprocess
import sys
import time


# --8<-- [start:ping]
def ping_all_nodes(iface, wait=2.0):
    """Send one ICMPv6 echo request to ff02::1 on this interface; collect everyone who answers."""
    index = socket.if_nametoindex(iface)
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_ICMPV6)   # no sudo needed
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, index)
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 0)                # not ourselves
    ident = 0x2525
    s.sendto(struct.pack("!BBHHH", 128, 0, 0, ident, 1) + b"anyone there?", ("ff02::1", 0, 0, index))
    sent, answers = time.time(), {}
    while time.time() < sent + wait:
        ready, _, _ = select.select([s], [], [], sent + wait - time.time())
        if not ready:
            break
        data, addr = s.recvfrom(1500)
        if data[0] == 129 and addr[0] not in answers:                                 # 129 = echo reply
            answers[addr[0].split("%")[0]] = (time.time() - sent) * 1000
    return answers
# --8<-- [end:ping]


def neighbour_table():
    """{IPv6 address: card address} from ndp (macOS) or ip neigh (Linux)."""
    table = {}
    try:
        out = subprocess.run(["ip", "-6", "neigh"], capture_output=True, text=True, check=True).stdout
        for line in out.splitlines():
            m = re.match(r"(\S+) dev \S+ lladdr (\S+)(.*)", line)
            if m:
                table[m.group(1)] = (m.group(2), "router" in m.group(3))
    except (FileNotFoundError, subprocess.CalledProcessError):
        out = subprocess.run(["ndp", "-an"], capture_output=True, text=True).stdout
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and ":" in parts[1]:
                mac = ":".join(f"{int(x, 16):02x}" for x in parts[1].split(":"))  # macOS drops leading zeros
                table[parts[0].split("%")[0]] = (mac, "R" in parts[5:6])
    return table


def hidden_mac(addr):
    iid = ipaddress.IPv6Address(addr).packed[8:]
    if iid[3:5] != b"\xff\xfe":
        return None
    b = bytearray(iid[:3] + iid[5:])
    b[0] ^= 0x02
    return ":".join(f"{x:02x}" for x in b)


# --8<-- [start:decode]
def decode(data):
    """One neighbour discovery message, in English."""
    kind = data[0]
    if kind == 133:
        return "router solicitation: “are there any routers here?”"
    if kind == 134:
        hops, flags, lifetime = data[4], data[5], struct.unpack("!H", data[6:8])[0]
        out = [f"router advertisement: hop limit {hops}",
               "addresses from DHCPv6" if flags & 0x80 else "",
               "other settings from DHCPv6" if flags & 0x40 else "",
               f"use me as a default router for {lifetime} s" if lifetime else "DON’T use me as a default router"]
        opts = options(data[16:])
        if not any(o.startswith("prefix") for o in opts):
            opts.append("no prefixes, so nothing to make a global address from")
        return "; ".join(x for x in out + opts if x)
    target = ipaddress.IPv6Address(data[8:24]) if len(data) >= 24 else None
    if kind == 135:
        return "; ".join([f"neighbour solicitation: “who has {target}?”"] + options(data[24:]))
    if kind == 136:
        flags = data[4]
        who = ("router, " if flags & 0x80 else "") + ("an answer" if flags & 0x40 else "unasked")
        return "; ".join([f"neighbour advertisement: “{target} is me” ({who})"] + options(data[24:]))
    if kind == 137:
        return f"redirect: “for that destination, use a better router”"
    return f"ICMPv6 type {kind}"


def options(data):
    out, i = [], 0
    while i + 2 <= len(data) and data[i + 1]:
        kind, length = data[i], data[i + 1] * 8               # option lengths count 8-byte units
        value = data[i + 2:i + length]
        if kind in (1, 2):                                     # the sender's card, or the card for that address
            out.append(("from card " if kind == 1 else "its card is ") + ":".join(f"{b:02x}" for b in value[:6]))
        elif kind == 3:
            plen, pflags = value[0], value[1]
            valid, preferred = struct.unpack("!II", value[2:10])
            prefix = ipaddress.IPv6Network((value[14:30], plen))
            out.append(f"prefix {prefix}" + (" (make addresses from it)" if pflags & 0x40 else "") + f", valid {valid} s")
        elif kind == 5:
            out.append(f"MTU {struct.unpack('!I', value[2:6])[0]}")
        elif kind == 25:
            servers = [str(ipaddress.IPv6Address(value[6 + k:22 + k])) for k in range(0, len(value) - 6, 16)]
            out.append("name servers " + ", ".join(servers))
        else:
            out.append(f"option {kind}")
        i += length
    return out
# --8<-- [end:decode]


def listen(iface, seconds):
    index = socket.if_nametoindex(iface)
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_ICMPV6)
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, index)
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255)
    s.sendto(struct.pack("!BBHI", 133, 0, 0, 0), ("ff02::2", 0, 0, index))      # "any routers here?"
    print(f"listening on {iface} for {seconds} s (routers usually advertise every few minutes)…")
    end = time.time() + seconds
    while time.time() < end:
        ready, _, _ = select.select([s], [], [], end - time.time())
        if not ready:
            break
        data, addr = s.recvfrom(1500)
        if 133 <= data[0] <= 137:
            print(f"{time.strftime('%H:%M:%S')}  from {addr[0].split('%')[0]:<26} {decode(data)}")


def main():
    iface = sys.argv[1] if len(sys.argv) > 1 else "en0"
    if "--listen" in sys.argv:
        return listen(iface, float(sys.argv[sys.argv.index("--listen") + 1]))
    print(f"pinging ff02::1 (every IPv6 device) on {iface}…")
    answers = ping_all_nodes(iface)
    table = neighbour_table()
    if not answers:
        print("nobody answered. (Is IPv6 switched on? Are you on the right interface?)")
    for addr, ms in sorted(answers.items(), key=lambda kv: kv[1]):
        mac, router = table.get(addr, ("?", False))
        note = []
        if router:
            note.append("a router")
        inside = hidden_mac(addr)
        if inside:
            note.append(f"its address has its card address inside: {inside}")
        else:
            note.append("its address is random: no card address inside")
        print(f"  {addr:<28} {ms:6.1f} ms   card {mac:<17}   " + "; ".join(note))


if __name__ == "__main__":
    main()
