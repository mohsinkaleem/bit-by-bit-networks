#!/usr/bin/env python3
"""Chapter 23 lab: link-state routing, the idea inside OSPF and IS-IS.

    python3 linkstate.py                       flood every router's news, then work out the shortest paths
    python3 linkstate.py --from library -v     the same, showing Dijkstra's algorithm one step at a time
    python3 linkstate.py --cut main-library    pull out a cable and watch the network heal
    python3 linkstate.py --pcap ospf.pcap      read a REAL OSPF capture, rebuild its map, and route with it

Every router tells every other router about its own cables (a "link-state advertisement"), by
flooding: send it to all your neighbours, who pass it on to all of theirs, unless they've seen it
already. Then every router has the same map, and works out the shortest paths on its own.
"""
import argparse
import heapq
import ipaddress
import struct

# The campus in the story. Costs are OSPF-style: 10 for a 10 Gb/s fibre, 100 for an old 1 Gb/s cable.
CAMPUS = {
    ("gateway", "main"): 1,
    ("main", "library"): 10,
    ("main", "lab"): 10,
    ("library", "lab"): 10,
    ("library", "dorms"): 10,
    ("lab", "sports"): 100,
    ("dorms", "sports"): 10,
}


def neighbours(links):
    out = {}
    for (a, b), cost in links.items():
        out.setdefault(a, {})[b] = cost
        out.setdefault(b, {})[a] = cost
    return out


# ---------------------------------------------------------------- flooding

# --8<-- [start:flood]
def flood(routers, lsdbs, news):
    """news: {router: (sequence number, {neighbour: cost})}, each starting at its own router.
    Deliver it hop by hop. Returns how many messages were sent."""
    queue = [(r, None, (r, news[r])) for r in news]    # (where it is, who sent it, (whose news, the news))
    sent = 0
    while queue:
        at, came_from, (origin, lsa) = queue.pop(0)
        have = lsdbs[at].get(origin)
        if have is not None and have[0] >= lsa[0] and came_from is not None:
            continue                                   # old news: don't pass it on (this stops the flood)
        lsdbs[at][origin] = lsa                        # new news: remember it…
        for n in routers[at]:
            if n != came_from:                         # …and tell every other neighbour
                queue.append((n, at, (origin, lsa)))
                sent += 1
    return sent
# --8<-- [end:flood]


# ---------------------------------------------------------------- shortest paths

# --8<-- [start:dijkstra]
def dijkstra(lsdb, source, verbose=False):
    """Shortest paths from source over the map in lsdb. Returns {router: (cost, first hop)}."""
    best = {}                                          # routers whose shortest path is settled
    frontier = [(0, source, None)]                     # (cost so far, router, first hop on the way)
    while frontier:
        cost, router, first = heapq.heappop(frontier)  # always settle the cheapest one next
        if router in best:
            continue                                   # already reached more cheaply
        best[router] = (cost, first)
        if verbose:
            print(f"  settle {router:<8} cost {cost:>3}" + (f"  (first hop: {first})" if first else ""))
        seq, links = lsdb.get(router, (0, {}))
        for n, c in links.items():
            if n in best:
                continue
            if router not in lsdb.get(n, (0, {}))[1]:
                continue                               # only use a cable that BOTH ends say exists
            heapq.heappush(frontier, (cost + c, n, first or n))
    return best
# --8<-- [end:dijkstra]


def table(best, source):
    print(f"{source}'s forwarding table:")
    for r, (cost, first) in sorted(best.items(), key=lambda kv: kv[1][0]):
        if r != source:
            print(f"  to {r:<8} send to {first:<8} total cost {cost}")


def simulate(args):
    links = dict(CAMPUS)
    routers = neighbours(links)
    lsdbs = {r: {} for r in routers}
    news = {r: (1, dict(routers[r])) for r in routers}
    sent = flood(routers, lsdbs, news)
    print(f"{len(routers)} routers flooded {len(news)} advertisements using {sent} messages.")
    same = all(lsdbs[r] == lsdbs[args.source] for r in routers)
    print("every router now has the same map:", "yes" if same else "NO")
    print()
    print(f"Dijkstra, run by {args.source}:" if args.verbose else "", end="\n" if args.verbose else "")
    best = dijkstra(lsdbs[args.source], args.source, args.verbose)
    table(best, args.source)
    for cut in args.cut:
        a, b = cut.split("-")
        key = (a, b) if (a, b) in links else (b, a)
        if key not in links:
            raise SystemExit(f"there's no cable {cut}")
        del links[key]
        routers = neighbours(links)
        for r in (a, b):
            routers.setdefault(r, {})
        print(f"\n✂  the {a}–{b} cable is cut. {a} and {b} each send new advertisements (sequence number 2).")
        news = {r: (lsdbs[r][r][0] + 1, dict(routers[r])) for r in (a, b)}
        sent = flood(routers, lsdbs, news)
        print(f"   that took {sent} messages. Everyone runs Dijkstra again.")
        new = dijkstra(lsdbs[args.source], args.source, args.verbose)
        for r in sorted(new):
            if r in best and best[r] != new[r] and r != args.source:
                print(f"   {args.source} → {r}: was via {best[r][1]} (cost {best[r][0]}), now via {new[r][1]} (cost {new[r][0]})")
        for r in sorted(set(best) - set(new)):
            print(f"   {args.source} → {r}: unreachable")
        best = new


# ---------------------------------------------------------------- a real OSPF capture

NAMES = {"10.255.0.1": "library", "10.255.0.2": "lab", "10.255.0.3": "main"}   # ospf_box.sh's router IDs
KINDS = {1: "Hello", 2: "Database Description", 3: "LS Request", 4: "LS Update", 5: "LS Acknowledge"}


def ip4(b):
    return ".".join(map(str, b))


# --8<-- [start:ospf]
def router_lsas(body):
    """Pull the Router-LSAs out of an LS Update. Yields (router, sequence, [(kind, id, data, metric)])."""
    count, = struct.unpack("!I", body[:4])
    at = 4
    for _ in range(count):
        age, opts, kind, lsid, adv, seq, csum, length = struct.unpack("!HBB4s4sIHH", body[at:at + 20])
        if kind == 1:                                  # a Router-LSA: "here are my cables"
            nlinks, = struct.unpack("!H", body[at + 22:at + 24])
            links, p = [], at + 24
            for _ in range(nlinks):
                lid, ldata, ltype, ntos, metric = struct.unpack("!4s4sBBH", body[p:p + 12])
                links.append((ltype, ip4(lid), ip4(ldata), metric))
                p += 12 + 4 * ntos
            yield ip4(adv), seq, links
        at += length
# --8<-- [end:ospf]


def read_pcap(path):
    data = open(path, "rb").read()
    endian = "<" if data[:4] == b"\xd4\xc3\xb2\xa1" else ">"
    at, first = 24, None
    while at + 16 <= len(data):
        sec, usec, caplen, _ = struct.unpack(endian + "IIII", data[at:at + 16])
        frame = data[at + 16:at + 16 + caplen]
        at += 16 + caplen
        first = first if first is not None else sec + usec / 1e6
        yield sec + usec / 1e6 - first, frame


def from_pcap(path, source):
    lsdb, stubs = {}, {}
    for t, frame in read_pcap(path):
        if frame[12:14] != b"\x08\x00" or frame[23] != 89:   # IPv4, protocol 89 = OSPF
            continue
        ip = 14 + (frame[14] & 15) * 4
        ver, kind, length, rid, area = struct.unpack("!BBH4s4s", frame[ip:ip + 12])
        body = frame[ip + 24:ip + length]
        src, dst = ip4(frame[26:30]), ip4(frame[30:34])
        info = ""
        if kind == 1:
            hello, dead = struct.unpack("!H", body[4:6])[0], struct.unpack("!I", body[8:12])[0]
            seen = [ip4(body[i:i + 4]) for i in range(20, len(body), 4)]
            info = f"every {hello}s, dead after {dead}s; I can hear: {', '.join(seen) or 'nobody yet'}"
        elif kind == 4:
            parts = []
            for adv, seq, links in router_lsas(body):
                cables = {l[1]: l[3] for l in links if l[0] == 1}
                nets = {f"{l[1]}/{ipaddress.ip_network('0.0.0.0/' + l[2]).prefixlen}": l[3] for l in links if l[0] == 3}
                if adv not in lsdb or seq >= lsdb[adv][0]:
                    lsdb[adv] = (seq, cables)
                    stubs[adv] = nets
                parts.append(f"router {adv} #{seq - 0x80000000}: {len(cables)} neighbours, {len(nets)} networks")
            info = "; ".join(parts)
        print(f"{t:7.3f}  {ip4(rid):<11} {KINDS.get(kind, kind):<21} {info}")
    print(f"\nThe map, from the newest advertisement of each router:")
    for r, (seq, cables) in sorted(lsdb.items()):
        print(f"  {r}: neighbours {cables}  networks {stubs[r]}")
    best = dijkstra(lsdb, source)
    print(f"\n{source}'s routes, worked out from the capture (compare BIRD's “show route”):")
    routes = {}
    for r, (cost, first) in best.items():
        for net, metric in stubs[r].items():
            if net not in routes or cost + metric < routes[net][0]:
                routes[net] = (cost + metric, first or "directly connected")
    for net, (cost, first) in sorted(routes.items(), key=lambda kv: ipaddress.ip_network(kv[0])):
        how = f"via router {first} ({NAMES.get(first, '?')})" if first in NAMES else first
        print(f"  {net:<14} cost {cost:>3}  {how}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--from", dest="source", default=None)
    p.add_argument("--cut", action="append", default=[], help="a cable to cut, like main-library")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--pcap")
    args = p.parse_args()
    if args.pcap:
        from_pcap(args.pcap, args.source or "10.255.0.1")
    else:
        args.source = args.source or "main"
        simulate(args)


if __name__ == "__main__":
    main()
