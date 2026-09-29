#!/usr/bin/env python3
"""Chapter 20 lab: a subnet calculator, built from nothing but bit operations.

    python3 ipcalc.py 192.168.1.3/24                  everything about an address and its network
    python3 ipcalc.py 10.23.147.8/13                  the split can be anywhere
    python3 ipcalc.py 192.168.1.0/24 --split 4        cut a network into 4 equal pieces
    python3 ipcalc.py 192.168.1.3/24 --to 192.168.1.4 1.1.1.1 192.168.2.9
                                                      straight there, or through the router?
    python3 ipcalc.py --mine                          your own computer's addresses and networks
    python3 ipcalc.py --check                         compare with Python's own ipaddress module
"""
import argparse
import ipaddress
import random
import re
import subprocess
import sys


# --8<-- [start:convert]
def to_int(text):
    """'192.168.1.3' -> 3232235779: four bytes, glued together into one 32-bit number."""
    a, b, c, d = (int(part) for part in text.split("."))
    return a << 24 | b << 16 | c << 8 | d


def to_text(n):
    return ".".join(str(n >> shift & 255) for shift in (24, 16, 8, 0))


def to_bits(n, prefix=None):
    """The 32 bits in groups of 8, with a | where the network part ends."""
    out = ""
    for i, bit in enumerate(f"{n:032b}"):
        if i == prefix and 0 < i < 32:
            out += "|"
        elif i and i % 8 == 0:
            out += "."
        out += bit
    return out


def mask_of(prefix):
    """/24 -> 24 ones followed by 8 zeros -> 255.255.255.0"""
    return (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
# --8<-- [end:convert]


SPECIAL = [("0.0.0.0/8", "“this network”: only used by a computer that doesn’t know its address yet"),
           ("10.0.0.0/8", "private (RFC 1918): for homes and offices, never seen on the internet"),
           ("100.64.0.0/10", "shared (“carrier-grade NAT”): private addresses used by internet providers"),
           ("127.0.0.0/8", "loopback: always this computer itself"),
           ("169.254.0.0/16", "link-local: made up by a computer that couldn’t get an address (Chapter 22)"),
           ("172.16.0.0/12", "private (RFC 1918): for homes and offices, never seen on the internet"),
           ("192.0.2.0/24", "documentation: for examples in books like this one"),
           ("192.168.0.0/16", "private (RFC 1918): for homes and offices, never seen on the internet"),
           ("198.51.100.0/24", "documentation"), ("203.0.113.0/24", "documentation"),
           ("224.0.0.0/4", "multicast: a group of listeners, not one computer"),
           ("255.255.255.255/32", "broadcast to everyone on this network"),
           ("240.0.0.0/4", "reserved for the future (which never came)")]


def kind_of(n):
    for block, words in SPECIAL:
        base, prefix = block.split("/")
        if n & mask_of(int(prefix)) == to_int(base):
            return words
    return "public: a real internet address, unique in the world"


# --8<-- [start:info]
def describe(address, prefix):
    n, mask = to_int(address), mask_of(prefix)
    network = n & mask                           # keep the network bits, zero the host bits
    broadcast = network | ~mask & 0xFFFFFFFF     # set every host bit to 1
    size = 2 ** (32 - prefix)
    print(f"address    {address:<16} {to_bits(n, prefix)}")
    print(f"netmask    {to_text(mask):<16} {to_bits(mask, prefix)}   (/{prefix})")
    print(f"network    {to_text(network):<16} {to_bits(network, prefix)}" + ("   all host bits 0" if prefix < 32 else ""))
    if prefix <= 30:
        print(f"broadcast  {to_text(broadcast):<16} {to_bits(broadcast, prefix)}   all host bits 1")
        print(f"hosts      {to_text(network + 1)} to {to_text(broadcast - 1)}   ({size - 2:,} usable)")
    else:
        print(f"hosts      {size} address{'es' if size > 1 else ''}, no broadcast (a point-to-point link, or one computer)")
    print(f"kind       {kind_of(n)}")
# --8<-- [end:info]


def split(address, prefix, parts):
    bits = (parts - 1).bit_length()
    if 2 ** bits != parts or prefix + bits > 32:
        raise SystemExit("split into a power of two: 2, 4, 8, 16…")
    network = to_int(address) & mask_of(prefix)
    step = 2 ** (32 - prefix - bits)
    print(f"{to_text(network)}/{prefix} cut into {parts} pieces of {step:,} addresses:")
    for i in range(parts):
        start = network + i * step
        print(f"  {to_text(start) + '/' + str(prefix + bits):<20} {to_text(start)} to {to_text(start + step - 1)}")


# --8<-- [start:route]
def where_to(my_address, prefix, destinations, gateway=None):
    mine, mask = to_int(my_address), mask_of(prefix)
    gateway = gateway or to_text((mine & mask) + 1)  # routers usually take the first address
    for dest in destinations:
        same = to_int(dest) & mask == mine & mask
        how = "same network: send it straight there" if same else f"another network: send it to the router, {gateway}"
        print(f"{dest:<16} {to_text(to_int(dest) & mask)} {'==' if same else '!='} {to_text(mine & mask)}  →  {how}")
# --8<-- [end:route]


def mine():
    if sys.platform == "darwin":
        out = subprocess.run(["ifconfig"], capture_output=True, text=True).stdout
        found = [(ip, bin(int(m, 16)).count("1")) for ip, m in re.findall(r"inet (\d+\.\d+\.\d+\.\d+) netmask 0x([0-9a-f]+)", out)]
    else:
        out = subprocess.run(["ip", "-o", "-4", "addr"], capture_output=True, text=True).stdout
        found = [(ip, int(p)) for ip, p in re.findall(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", out)]
    for ip, prefix in found:
        print(f"\n{ip}/{prefix}")
        describe(ip, prefix)


def check():
    """Compare with Python's ipaddress module on thousands of random addresses."""
    rng = random.Random(20)
    for _ in range(10000):
        n, prefix = rng.getrandbits(32), rng.randint(0, 32)
        net = ipaddress.ip_network(f"{to_text(n)}/{prefix}", strict=False)
        assert to_int(str(net.network_address)) == n & mask_of(prefix)
        assert to_int(str(net.broadcast_address)) == n & mask_of(prefix) | ~mask_of(prefix) & 0xFFFFFFFF
    print("10,000 random networks: every network and broadcast address matches Python's ipaddress module.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("network", nargs="?", help="an address with a prefix, like 192.168.1.3/24")
    p.add_argument("--split", type=int, metavar="N")
    p.add_argument("--to", nargs="+", metavar="ADDRESS")
    p.add_argument("--mine", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    if args.mine:
        return mine()
    if args.check:
        return check()
    if not args.network:
        return p.print_help()
    address, _, prefix = args.network.partition("/")
    prefix = int(prefix or 32)
    if args.split:
        split(address, prefix, args.split)
    elif args.to:
        where_to(address, prefix, args.to)
    else:
        describe(address, prefix)


if __name__ == "__main__":
    main()
