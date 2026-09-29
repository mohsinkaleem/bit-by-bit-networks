#!/usr/bin/env python3
"""Chapter 23 lab: longest-prefix match, the rule every router (and your laptop) uses.

    python3 lpm.py                              look up some addresses in a small campus router's table
    python3 lpm.py mine 1.1.1.1 192.168.1.4     the same, in YOUR computer's real routing table
    python3 lpm.py aggregate 10.1.0.0/24 10.1.1.0/24 10.1.2.0/24 10.1.3.0/24
                                                squeeze neighbouring networks into fewer routes (CIDR)
    python3 lpm.py bench                        a trie against a plain list, with 200,000 routes

The table is a binary trie: one level per bit of the address. To look an address up, walk down
it one bit at a time, and remember the last route you passed. That's the longest match.
"""
import ipaddress
import random
import re
import subprocess
import sys
import time


# --8<-- [start:trie]
class Trie:
    """Routes stored by their prefix bits. Each node is [child for bit 0, child for bit 1, route]."""

    def __init__(self):
        self.root = [None, None, None]

    def add(self, prefix, route):
        net = ipaddress.ip_network(prefix)
        bits, node = int(net.network_address), self.root
        for i in range(net.prefixlen):                  # follow (or grow) one branch per prefix bit
            bit = (bits >> (31 - i)) & 1
            if node[bit] is None:
                node[bit] = [None, None, None]
            node = node[bit]
        node[2] = (net, route)

    def lookup(self, address, trail=None):
        bits, node = int(ipaddress.ip_address(address)), self.root
        best = node[2]                                  # the default route, 0.0.0.0/0, lives at the root
        for i in range(32):
            node = node[(bits >> (31 - i)) & 1]
            if node is None:
                break                                   # no longer prefix can match: stop walking
            if node[2] is not None:
                best = node[2]                          # a longer match than anything so far
                if trail is not None:
                    trail.append(node[2])
        return best
# --8<-- [end:trie]


CAMPUS = [  # the main building's router, from the story
    ("0.0.0.0/0", "via 10.0.0.1 (the internet provider)"),
    ("10.0.0.0/8", "drop: private, and not ours"),
    ("10.1.0.0/16", "via 10.0.23.2 (towards the lab building)"),
    ("10.1.1.0/24", "via 10.0.12.1 (the library)"),
    ("10.1.3.0/24", "dev lan (this building)"),
    ("10.1.3.99/32", "via 10.0.12.1 (one server that moved to the library)"),
]


def show(trie, addresses):
    for a in addresses:
        trail = []
        net, route = trie.lookup(a, trail) or (None, "no route: “network unreachable”")
        matches = ["0.0.0.0/0"] if trie.root[2] else []
        matches += [str(n) for n, _ in trail if str(n) != "0.0.0.0/0"]
        print(f"{a:<16} matches {', '.join(matches) or 'nothing'}")
        print(f"{'':<16} longest: {net}  →  {route}\n")


# ---------------------------------------------------------------- your own table

def my_routes():
    """Read the computer's IPv4 routing table: netstat on macOS, ip route on Linux."""
    try:
        out = subprocess.run(["ip", "-4", "route"], capture_output=True, text=True, check=True).stdout
        routes = []
        for line in out.splitlines():
            words = line.split()
            if not words or words[0] in ("broadcast", "local", "unreachable", "blackhole"):
                continue
            dest = "0.0.0.0/0" if words[0] == "default" else words[0]
            if "/" not in dest:
                dest += "/32"
            routes.append((dest, " ".join(words[1:])))
        return routes
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    out = subprocess.run(["netstat", "-rn", "-f", "inet"], capture_output=True, text=True).stdout
    routes = []
    for line in out.splitlines():
        words = line.split()
        if len(words) < 4 or not re.match(r"^(default|\d)", words[0]):
            continue
        dest, gateway, flags, iface = words[0], words[1], words[2], words[3]
        if dest == "default":
            dest = "0.0.0.0/0"
        elif "/" not in dest:
            parts = dest.split(".")
            if "H" in flags or len(parts) == 4:          # a single computer
                dest = ".".join(parts + ["0"] * (4 - len(parts))) + "/32"
            else:                                        # macOS writes 192.168.1 for 192.168.1.0/24
                dest = ".".join(parts + ["0"] * (4 - len(parts))) + f"/{8 * len(parts)}"
        else:
            addr, plen = dest.split("/")
            parts = addr.split(".")
            dest = ".".join(parts + ["0"] * (4 - len(parts))) + "/" + plen
        how = f"dev {iface}" if gateway.startswith("link#") else f"via {gateway} dev {iface}"
        routes.append((dest, how + f"  [{flags}]"))
    return routes


# ---------------------------------------------------------------- aggregation

# --8<-- [start:aggregate]
def aggregate(prefixes):
    """Merge sibling networks (two halves of a bigger one) until nothing more can merge."""
    nets = set(ipaddress.ip_network(p) for p in prefixes)
    nets = {n for n in nets if not any(n != m and n.subnet_of(m) for m in nets)}  # already covered
    merged = True
    while merged:
        merged = False
        for n in sorted(nets):
            if n.prefixlen == 0:
                continue
            parent = n.supernet()                        # one bit shorter
            halves = set(parent.subnets())               # the two halves of the parent
            if halves <= nets:
                nets -= halves
                nets.add(parent)
                print(f"  {' + '.join(str(h) for h in sorted(halves))}  →  {parent}")
                merged = True
                break
    return sorted(nets)
# --8<-- [end:aggregate]


def bench(n=200_000):
    rng = random.Random(23)
    routes = []
    for _ in range(n):
        plen = rng.choice([16, 18, 20, 22, 24, 24, 24, 24])
        net = ipaddress.ip_network((rng.getrandbits(32) & (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF, plen))
        routes.append((net, "x"))
    trie = Trie()
    t0 = time.perf_counter()
    for net, r in routes:
        trie.add(net, r)
    print(f"built a trie of {n:,} routes in {time.perf_counter() - t0:.1f} s")
    probes = [str(ipaddress.ip_address(rng.getrandbits(32))) for _ in range(300)]
    t0 = time.perf_counter()
    for a in probes:
        trie.lookup(a)
    per_trie = (time.perf_counter() - t0) / len(probes)
    t0 = time.perf_counter()
    for a in probes[:30]:
        ip = ipaddress.ip_address(a)
        max((net for net, _ in routes if ip in net), key=lambda net: net.prefixlen, default=None)
    per_list = (time.perf_counter() - t0) / 30
    print(f"trie: {per_trie * 1e6:8.1f} µs per lookup (at most 32 steps)")
    print(f"list: {per_list * 1e6:8.1f} µs per lookup (checks every route)  →  {per_list / per_trie:,.0f}× slower")
    print("A real router does this in hardware, hundreds of millions of times a second.")


def main():
    args = sys.argv[1:]
    if args[:1] == ["mine"]:
        trie = Trie()
        routes = my_routes()
        print("your routing table:")
        for dest, how in routes:
            print(f"  {dest:<20} {how}")
            trie.add(dest, how)
        print()
        show(trie, args[1:] or ["1.1.1.1", "192.168.1.1", "127.0.0.1", "224.0.0.251"])
    elif args[:1] == ["aggregate"]:
        print("merging:")
        result = aggregate(args[1:])
        print(f"{len(set(args[1:]))} routes became {len(result)}: " + ", ".join(map(str, result)))
    elif args[:1] == ["bench"]:
        bench()
    else:
        trie = Trie()
        print("the main building's routing table:")
        for dest, how in CAMPUS:
            print(f"  {dest:<14} {how}")
            trie.add(dest, how)
        print()
        show(trie, args or ["10.1.1.20", "10.1.3.99", "10.1.3.7", "10.1.2.5", "10.9.9.9", "188.184.67.127"])


if __name__ == "__main__":
    main()
