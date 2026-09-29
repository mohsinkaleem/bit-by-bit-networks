#!/usr/bin/env python3
"""Chapter 24 lab: BGP between autonomous systems, with the business rules real networks use.

    python3 bgp_sim.py                         the university announces its addresses; who picks which path?
    python3 bgp_sim.py --prepend 2             the university makes its path through Northnet look 2 hops longer
    python3 bgp_sim.py --hijack                Eve announces a more specific piece of the university's block
    python3 bgp_sim.py --hijack --rov          …but some networks check route origins (RPKI)
    python3 bgp_sim.py --leak                  SmallCo passes one provider's routes to its other provider
    python3 bgp_sim.py --why Tier1-East        every route one AS heard, and which one it picked

Each AS picks ONE best path per prefix, and tells its neighbours, following two rules
(written down by Lixin Gao and Jennifer Rexford in 2001):
  choose:  a customer's route beats a peer's, which beats a provider's; then the shortest AS path
  export:  customers' routes (and your own) go to everyone; everything else only goes to customers
"""
import argparse
import ipaddress

# Who's connected to whom. ("a", "b", "cust") means b is a's customer: b pays a.
# ("a", "b", "peer") means they carry each other's customers' traffic for free.
LINKS = [
    ("Tier1-West", "Tier1-East", "peer"),
    ("Tier1-West", "SmallCo", "cust"),
    ("Tier1-East", "SmallCo", "cust"),
    ("Tier1-West", "Southnet", "cust"),
    ("Tier1-West", "Northnet", "cust"),
    ("Tier1-East", "Northnet", "cust"),
    ("Tier1-East", "ResearchNet", "cust"),
    ("Northnet", "ResearchNet", "peer"),
    ("Southnet", "Eve", "cust"),
    ("Southnet", "Shop", "cust"),
    ("Southnet", "Bob's ISP", "cust"),
    ("Northnet", "Bob's ISP", "cust"),
    ("Northnet", "University", "cust"),
    ("ResearchNet", "University", "cust"),
]
ASN = {"Tier1-West": 64500, "Tier1-East": 64501, "SmallCo": 65077, "Southnet": 64530, "Northnet": 64510,
       "ResearchNet": 64520, "Eve": 65066, "Shop": 65088, "Bob's ISP": 65002, "University": 65001}
RANK = {"self": 4, "cust": 3, "peer": 2, "prov": 1}
HOW = {"self": "its own", "cust": "customer", "peer": "peer", "prov": "provider"}
ROAS = {"10.1.0.0/16": (65001, 16)}           # "only AS 65001 may announce this, and nothing longer than /16"


def relationships():
    rel = {a: {} for a in ASN}
    for a, b, kind in LINKS:
        if kind == "cust":
            rel[a][b], rel[b][a] = "cust", "prov"   # b is a's customer, so a is b's provider
        else:
            rel[a][b] = rel[b][a] = "peer"
    return rel


# --8<-- [start:propagate]
def propagate(rel, announcements, prepend=None, rov=(), leaker=None):
    """announcements: {prefix: origin AS}. Returns heard[as][prefix][neighbour] = the AS path it was told."""
    heard = {a: {p: {} for p in announcements} for a in ASN}
    changed = True
    while changed:                                  # keep going until nobody hears anything new
        changed = False
        for me in ASN:
            for prefix in announcements:
                route = choose(rel, me, prefix, heard, announcements)
                for nbr, kind in rel[me].items():
                    offer = None
                    # export rule: my own and my customers' routes go to everyone, the rest only to customers
                    if route and (route[2] in ("self", "cust") or kind == "cust" or me == leaker):
                        copies = 1 + (prepend[1] if prepend and route[2] == "self" and nbr == prepend[0] else 0)
                        offer = [ASN[me]] * copies + route[0]
                        if ASN[nbr] in offer:
                            offer = None            # its own number is already in the path: no loops
                        elif nbr in rov and not valid(prefix, offer[-1]):
                            offer = None            # route origin validation: that AS may not announce this
                    if heard[nbr][prefix].get(me) != offer:
                        heard[nbr][prefix][me] = offer   # a new route from a neighbour replaces its old one
                        changed = True
    return heard


def choose(rel, me, prefix, heard, announcements):
    """My best route to prefix: (AS path, neighbour it came from, relationship)."""
    if announcements[prefix] == me:
        return ([], None, "self")
    offers = [(path, nbr, rel[me][nbr]) for nbr, path in heard[me][prefix].items() if path]
    if not offers:
        return None
    #   1. who pays whom       2. the shortest AS path   3. a tie-breaker: the lowest AS number
    return max(offers, key=lambda o: (RANK[o[2]], -len(o[0]), -ASN[o[1]]))
# --8<-- [end:propagate]


def valid(prefix, origin):
    net = ipaddress.ip_network(prefix)
    for roa, (asn, maxlen) in ROAS.items():
        if net.subnet_of(ipaddress.ip_network(roa)):
            return asn == origin and net.prefixlen <= maxlen
    return True                                     # no ROA covers it ("not found"), so it's allowed


def forward(best, me, address):
    """Longest-prefix match (Chapter 23) over the routes this AS chose."""
    ip = ipaddress.ip_address(address)
    hit = None
    for prefix, route in best[me].items():
        net = ipaddress.ip_network(prefix)
        if route and ip in net and (hit is None or net.prefixlen > hit[0].prefixlen):
            hit = (net, route)
    return hit


def show(rel, heard, announcements, address, watch=None):
    best = {a: {p: choose(rel, a, p, heard, announcements) for p in announcements} for a in ASN}
    print(f"{'AS':<12} {'best path':<46} traffic for {address} ends up at")
    for me in ASN:
        lines = []
        for prefix, route in best[me].items():
            if route:
                path = " ".join(map(str, route[0])) or "-"
                lines.append(f"{prefix}: {path} ({HOW[route[2]]})")
        hit = forward(best, me, address)
        dest = announcements[str(hit[0])] if hit else "nowhere"
        if dest == "Eve":
            dest += "   ← HIJACKED"
        if watch and hit and ASN[watch] in hit[1][0]:
            dest += f"   ← through {watch}!"
        lines = lines or ["(no route)"]
        for i, text in enumerate(lines):
            print(f"{me if i == 0 else '':<12} {text:<46} {dest if i == len(lines) - 1 else ''}")


def why(rel, heard, announcements, me):
    for prefix in announcements:
        best = choose(rel, me, prefix, heard, announcements)
        print(f"{me} heard these routes to {prefix}:")
        for nbr, path in sorted(heard[me][prefix].items()):
            if path:
                mark = "  ★ best" if best and best[1] == nbr else ""
                print(f"  from {nbr:<12} ({HOW[rel[me][nbr]]:<8}) {' '.join(map(str, path))}{mark}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--prepend", type=int, default=0, help="extra copies of 65001 on the way to Northnet")
    p.add_argument("--hijack", action="store_true")
    p.add_argument("--rov", action="store_true", help="the tier-1s and Northnet drop invalid routes")
    p.add_argument("--leak", action="store_true", help="SmallCo passes Tier1-West's routes to Tier1-East")
    p.add_argument("--why", metavar="AS", help="list every route this AS heard")
    args = p.parse_args()
    rel = relationships()
    if args.leak:
        announcements = {"10.8.0.0/16": "Shop"}
        heard = propagate(rel, announcements, leaker="SmallCo")
        address, watch = "10.8.0.1", "SmallCo"
    else:
        announcements = {"10.1.0.0/16": "University"}
        if args.hijack:
            announcements["10.1.1.0/24"] = "Eve"
        rov = ("Tier1-West", "Tier1-East", "Northnet") if args.rov else ()
        heard = propagate(rel, announcements, prepend=("Northnet", args.prepend) if args.prepend else None, rov=rov)
        address, watch = "10.1.1.1", None
    if args.why:
        why(rel, heard, announcements, args.why)
    else:
        show(rel, heard, announcements, address, watch)


if __name__ == "__main__":
    main()
