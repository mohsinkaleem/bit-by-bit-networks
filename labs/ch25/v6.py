#!/usr/bin/env python3
"""Chapter 25 lab: IPv6 addresses, taken apart and built by hand.

    python3 v6.py explain 2001:1458:201:a4::100:1a0     write it out in full, find its parts and its kind
    python3 v6.py explain fe80::16c3:5eff:fe40:b32      …this one has a card address hidden inside
    python3 v6.py slaac 2001:db8:1:2::/64 14:c3:5e:40:0b:32
                                                        the addresses a computer would make for itself
    python3 v6.py solicit fe80::16c3:5eff:fe40:b32      where to send a "who has?" for this address

No network needed: it's all arithmetic on 128-bit numbers.
"""
import hashlib
import ipaddress
import sys

KINDS = [  # (prefix, what it's for). The first one that matches wins, so specific ones come first.
    ("::1/128", "loopback: this computer itself"),
    ("::/128", "unspecified: “I don’t have an address yet”"),
    ("::ffff:0:0/96", "an IPv4 address, dressed up as IPv6"),
    ("64:ff9b::/96", "NAT64: an IPv4 address, reached through a translator"),
    ("2001:db8::/32", "documentation: for examples in books"),
    ("2002::/16", "6to4: an old way of tunnelling IPv6 over IPv4"),
    ("fe80::/10", "link-local: only works on this one network"),
    ("fc00::/7", "unique local: private, like 192.168.x.x"),
    ("ff00::/8", "multicast: a group of listeners"),
    ("2000::/3", "global unicast: unique on the whole internet"),
]


# --8<-- [start:write]
def full(addr):
    """All eight groups, all four digits each."""
    return ipaddress.IPv6Address(addr).exploded


def short(addr):
    """Drop leading zeros in each group, then replace the longest run of all-zero groups with ::"""
    groups = [format(g, "x") for g in groups_of(addr)]              # rule 1: 0db8 -> db8, 0000 -> 0
    best_start, best_len, start = -1, 1, None
    for i, g in enumerate(groups + ["end"]):
        if g == "0" and start is None:
            start = i
        elif g != "0" and start is not None:
            if i - start > best_len:                                  # rule 2: only runs of 2 or more,
                best_start, best_len = start, i - start               #         and only the longest one
            start = None
    if best_start < 0:
        return ":".join(groups)
    left = ":".join(groups[:best_start])
    right = ":".join(groups[best_start + best_len:])
    return f"{left}::{right}"


def groups_of(addr):
    n = int(ipaddress.IPv6Address(addr))
    return [(n >> (112 - 16 * i)) & 0xFFFF for i in range(8)]
# --8<-- [end:write]


def kind(addr):
    a = ipaddress.IPv6Address(addr)
    for prefix, what in KINDS:
        if a in ipaddress.IPv6Network(prefix):
            return prefix, what
    return None, "reserved"


# --8<-- [start:eui64]
def eui64(mac):
    """A 64-bit interface ID from a 48-bit card address: flip one bit, and put ff:fe in the middle."""
    b = bytearray(int(x, 16) for x in mac.split(":"))
    b[0] ^= 0x02                                   # the "chosen by software" bit (Chapter 18), inverted
    return bytes(b[:3]) + b"\xff\xfe" + bytes(b[3:])


def hidden_mac(addr):
    """If the last 64 bits have ff:fe in the middle, they're probably a card address in disguise."""
    iid = ipaddress.IPv6Address(addr).packed[8:]
    if iid[3:5] != b"\xff\xfe":
        return None
    b = bytearray(iid[:3] + iid[5:])
    b[0] ^= 0x02
    return ":".join(f"{x:02x}" for x in b)
# --8<-- [end:eui64]


def stable_privacy(prefix, mac, secret=b"a secret only this computer knows", counter=0):
    """RFC 7217: the same address every time on the same network, but different on every network,
    and with nothing in it that identifies the computer."""
    net = ipaddress.IPv6Network(prefix)
    h = hashlib.sha256(net.network_address.packed[:8] + mac.encode() + counter.to_bytes(1, "big") + secret).digest()
    return ipaddress.IPv6Address(net.network_address.packed[:8] + h[:8])


def explain(addr):
    a = ipaddress.IPv6Address(addr)
    print(f"you typed:   {addr}")
    print(f"in full:     {full(a)}")
    print(f"shortest:    {short(a)}   (Python agrees: {a.compressed})")
    groups = groups_of(a)
    print("in bits:     " + " ".join(format(g, "016b") for g in groups[:4]))
    print("             " + " ".join(format(g, "016b") for g in groups[4:]))
    prefix, what = kind(a)
    print(f"kind:        {what}" + (f"   ({prefix})" if prefix else ""))
    if a in ipaddress.IPv6Network("2000::/3") or a in ipaddress.IPv6Network("fc00::/7") or a in ipaddress.IPv6Network("fe80::/10"):
        net = ipaddress.IPv6Network(f"{a}/64", strict=False)
        print(f"network:     {net}   (the first 64 bits: which network)")
        print(f"interface:   ::{short(ipaddress.IPv6Address(int(a) & (2 ** 64 - 1)))[2:] if int(a) & (2 ** 64 - 1) else '0'}   (the last 64 bits: which computer on it)")
        mac = hidden_mac(a)
        if mac:
            print(f"hidden MAC:  {mac}   (the interface part was made from this card address)")
    if a.ipv4_mapped:
        print(f"IPv4 inside: {a.ipv4_mapped}")


def slaac(prefix, mac):
    net = ipaddress.IPv6Network(prefix)
    if net.prefixlen != 64:
        print("(SLAAC only works with a /64: the interface part must be 64 bits)")
    iid = eui64(mac)
    print(f"card address:           {mac}")
    print(f"flip bit, insert ff:fe: {iid.hex(':')}")
    link = ipaddress.IPv6Address(bytes.fromhex("fe80000000000000") + iid)
    glob = ipaddress.IPv6Address(net.network_address.packed[:8] + iid)
    print(f"link-local (old style): {link}")
    print(f"global (old style):     {glob}   ← anyone can see your card address, on every network you join")
    print(f"stable privacy:         {stable_privacy(prefix, mac)}   ← the same here every time, different elsewhere")
    print(f"another network:        {stable_privacy('2001:db8:99:1::/64', mac)}")


# --8<-- [start:solicit]
def solicit(addr):
    """Neighbour discovery doesn't broadcast "who has?": it multicasts to a group that only
    computers whose address ends in the same 24 bits will have joined."""
    last24 = ipaddress.IPv6Address(addr).packed[13:]
    group = ipaddress.IPv6Address(bytes.fromhex("ff0200000000000000000001ff") + last24)
    mac = "33:33:" + ":".join(f"{b:02x}" for b in group.packed[12:])   # IPv6 multicast MACs start 33:33
    return group, mac
# --8<-- [end:solicit]


def main():
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "explain":
        for i, a in enumerate(args[1:]):
            if i:
                print()
            explain(a)
    elif len(args) == 3 and args[0] == "slaac":
        slaac(args[1], args[2])
    elif len(args) == 2 and args[0] == "solicit":
        group, mac = solicit(args[1])
        print(f"to find {args[1]}, ask the group {group}")
        print(f"which travels in an Ethernet frame to {mac}")
        print("Only computers whose addresses end in the same 24 bits listen to that group, so almost nobody else is disturbed.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
