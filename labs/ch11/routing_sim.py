#!/usr/bin/env python3
"""Chapter 11 lab: a town of four networks, joined by four routers in a ring.

    python3 routing_sim.py tables                  routers share their tables until they agree
    python3 routing_sim.py send alice otto         follow one packet, hop by hop
    python3 routing_sim.py send alice otto --cut R1-R4
                                                   ...after a digger cuts the cable between R1 and R4
    python3 routing_sim.py loop                    two routers with bad tables, and a packet caught between them
    python3 routing_sim.py trace alice otto        find every router on the way, using the hop limit

               street (network 1)              school (network 2)
     alice 1.1  bob 1.2  carol 1.3  dave 1.4      teacher 2.1
                    |                                  |
                   R1 --------------------------------- R2
                    |                                   |
                   R4 --------------------------------- R3
                    |                                  |
               otto 4.2                          library 3.1
          Grandpa Otto's town (network 4)       library (network 3)
"""
import argparse

HOSTS = {  # name: (address, card address)
    "alice": ("1.1", "0a:11"), "bob": ("1.2", "0b:22"), "carol": ("1.3", "0c:33"), "dave": ("1.4", "0d:44"),
    "teacher": ("2.1", "2e:01"), "library": ("3.1", "3b:01"), "otto": ("4.2", "40:02"),
}
ROUTERS = {  # name: (the network it serves, its address there, its card address there)
    "R1": (1, "1.254", "c1:01"), "R2": (2, "2.254", "c2:01"), "R3": (3, "3.254", "c3:01"), "R4": (4, "4.254", "c4:01"),
}
CABLES = [("R1", "R2"), ("R2", "R3"), ("R3", "R4"), ("R4", "R1")]
UNREACHABLE = 16                                   # "infinitely far": no route
ROUTERS_NETS = [1, 2, 3, 4]


def network_of(address):
    return int(address.split(".")[0])


class Router:
    def __init__(self, name):
        self.name = name
        self.net, self.address, self.card = ROUTERS[name]
        self.neighbors = []                          # routers at the other end of our cables
        self.table = {self.net: (None, 0)}           # network -> (next router or None for "right here", hops)

    # --8<-- [start:share]
    def hear(self, neighbor, their_table):
        """A neighbor told us every network it can reach, and how far away each one is.
        Anything it can reach, we can reach through it, one hop further."""
        changed = False
        for net, (_, hops) in their_table.items():
            offer = min(hops + 1, UNREACHABLE)
            current_via, current_hops = self.table.get(net, (None, UNREACHABLE))
            better = offer < current_hops
            news_from_our_route = current_via == neighbor.name and offer != current_hops
            if better or news_from_our_route:
                self.table[net] = (neighbor.name, offer)
                changed = True
        return changed
    # --8<-- [end:share]

    def forget(self, neighbor_name):
        """The cable to this neighbor went quiet: every route through it is gone."""
        for net, (via, hops) in list(self.table.items()):
            if via == neighbor_name:
                self.table[net] = (via, UNREACHABLE)

    def show(self):
        rows = []
        for net in sorted(self.table):
            via, hops = self.table[net]
            if hops >= UNREACHABLE:
                rows.append(f"net {net}: unreachable")
            else:
                rows.append(f"net {net}: " + ("right here" if via is None else f"via {via}, {hops} hop{'s' * (hops > 1)}"))
        return f"{self.name}  " + " | ".join(rows)


def build(cut=()):
    routers = {name: Router(name) for name in ROUTERS}
    for a, b in CABLES:
        if f"{a}-{b}" in cut or f"{b}-{a}" in cut:
            continue
        routers[a].neighbors.append(routers[b])
        routers[b].neighbors.append(routers[a])
    return routers


def share_until_stable(routers, quiet=False):
    """Every round, every router tells each neighbor its whole table."""
    for rnd in range(1, 20):
        snapshot = {name: dict(r.table) for name, r in routers.items()}
        changed = False
        for r in routers.values():
            for n in r.neighbors:
                changed |= r.hear(n, snapshot[n.name])
        if not quiet:
            print(f"\nafter round {rnd} of sharing:")
            for r in routers.values():
                print("  " + r.show())
        if not changed:
            if not quiet:
                lost = [f"{r.name} can't reach network {', '.join(str(n) for n in ROUTERS_NETS if r.table.get(n, (None, UNREACHABLE))[1] >= UNREACHABLE)}"
                        for r in routers.values() if any(r.table.get(n, (None, UNREACHABLE))[1] >= UNREACHABLE for n in ROUTERS_NETS)]
                print(f"\nround {rnd} changed nothing, so the tables have settled. " +
                      ("; ".join(lost) + "." if lost else "Every router knows a way to every network."))
            return rnd
    return rnd


# --8<-- [start:forward]
def send(routers, src, dst, ttl=64, verbose=True):
    """Follow a packet from host src to host dst. Returns the list of routers it passed through,
    and who reported its death if the hop limit ran out."""
    src_addr, src_card = HOSTS[src]
    dst_addr, dst_card = HOSTS[dst]
    say = print if verbose else (lambda *a: None)
    here_net = network_of(src_addr)
    gateway = next(r for r in routers.values() if r.net == here_net)
    if network_of(dst_addr) == here_net:
        say(f"  {src}: {dst_addr} is on my own network {here_net}. Who has {dst_addr}? → {dst} answers: card {dst_card}")
        say(f"    frame [to {dst_card} from {src_card}]  packet [to {dst_addr} from {src_addr}, hops left {ttl}]")
        say(f"  {dst}: it's for me ✓  (no routers needed)")
        return [], None
    say(f"  {src}: {dst_addr} isn't on my network {here_net}, so it goes to my gateway, {gateway.address}.")
    say(f"    Who has {gateway.address}? → {gateway.name} answers: card {gateway.card}")
    say(f"    frame [to {gateway.card} from {src_card}]  packet [to {dst_addr} from {src_addr}, hops left {ttl}]")
    path, router = [], gateway
    while True:
        path.append(router.name)
        ttl -= 1                                              # every router takes one off
        if ttl == 0:
            say(f"  {router.name}: hops left is 0! Drop it, and tell {src_addr} “your packet died here, at {router.address}”")
            return path, router.name
        net = network_of(dst_addr)
        via, hops = router.table.get(net, (None, UNREACHABLE))
        if hops >= UNREACHABLE:
            say(f"  {router.name}: I have no route to network {net}. Drop it, and tell {src_addr} it's unreachable")
            return path, None
        if via is None:
            say(f"  {router.name}: network {net} is right here. Who has {dst_addr}? → {dst} answers: card {dst_card}")
            say(f"    frame [to {dst_card} from {router.card}]  packet [to {dst_addr} from {src_addr}, hops left {ttl}]")
            say(f"  {dst}: it's for me ✓  (passed through {len(path)} router{'s' * (len(path) > 1)}: {' → '.join(path)})")
            return path, None
        nxt = routers[via]
        say(f"  {router.name}: network {net}? my table says via {via}. New frame, same packet:")
        say(f"    frame [to {nxt.card} from {router.card}]  packet [to {dst_addr} from {src_addr}, hops left {ttl}]")
        router = nxt
# --8<-- [end:forward]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["tables", "send", "loop", "trace"])
    p.add_argument("src", nargs="?", default="alice", choices=sorted(HOSTS))
    p.add_argument("dst", nargs="?", default="otto", choices=sorted(HOSTS))
    p.add_argument("--cut", action="append", default=[], help="a cable to cut, like R1-R4")
    p.add_argument("--ttl", type=int, default=64, help="hop limit to start the packet with")
    args = p.parse_args()

    if args.mode == "tables":
        routers = build()
        print("before sharing, each router only knows its own network:")
        for r in routers.values():
            print("  " + r.show())
        share_until_stable(routers)
        if args.cut:
            for c in args.cut:
                a, b = c.split("-")
                print(f"\n✂ the cable {a}-{b} is cut! {a} and {b} stop hearing each other.")
                routers[a].neighbors = [n for n in routers[a].neighbors if n.name != b]
                routers[b].neighbors = [n for n in routers[b].neighbors if n.name != a]
                routers[a].forget(b)
                routers[b].forget(a)
            share_until_stable(routers)
    elif args.mode == "send":
        routers = build(args.cut)
        share_until_stable(routers, quiet=True)
        print(f"{args.src} ({HOSTS[args.src][0]}) sends a packet to {args.dst} ({HOSTS[args.dst][0]})"
              + (f", with cable {', '.join(args.cut)} cut" if args.cut else ""))
        send(routers, args.src, args.dst, args.ttl)
    elif args.mode == "loop":
        routers = build()
        share_until_stable(routers, quiet=True)
        routers["R1"].table[4] = ("R2", 2)          # a typo in R1's table...
        routers["R2"].table[4] = ("R1", 2)          # ...and another in R2's
        print("R1 thinks network 4 is through R2, and R2 thinks it's through R1.")
        print(f"alice sends a packet to otto, starting with {args.ttl if args.ttl != 64 else 8} hops left:")
        send(routers, "alice", "otto", args.ttl if args.ttl != 64 else 8)
    else:  # trace
        routers = build(args.cut)
        share_until_stable(routers, quiet=True)
        print(f"tracing the route from {args.src} to {args.dst} ({HOSTS[args.dst][0]}):")
        for limit in range(1, 10):
            path, died_at = send(routers, args.src, args.dst, ttl=limit, verbose=False)
            if died_at:
                print(f"  {limit}  {died_at} ({routers[died_at].address}) says “your packet died here”")
            else:
                print(f"  {limit}  {args.dst} ({HOSTS[args.dst][0]}) answered: we've arrived")
                break


if __name__ == "__main__":
    main()
