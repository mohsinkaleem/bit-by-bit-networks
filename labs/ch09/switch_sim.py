#!/usr/bin/env python3
"""Chapter 9 lab: learning switches, loops, and a spanning tree.

    python3 switch_sim.py learn            one switch, four computers: watch the table fill up
    python3 switch_sim.py two              two switches joined together
    python3 switch_sim.py storm            three switches in a loop, then one broadcast...
    python3 switch_sim.py storm --stp      ...the same loop with spanning tree switched on
    python3 switch_sim.py learn --send A:B,B:A,C:ff,D:C     your own list of frames (ff = broadcast)
"""
import argparse
from collections import deque

BROADCAST = "ff"
MAX_EVENTS = 60        # stop the simulation if frames are still bouncing around after this many hops


class Host:
    def __init__(self, name):
        self.name, self.mac = name, name        # to keep things readable, a host's address is its name
        self.link = None                        # (node, port) at the other end of its cable

    def receive(self, in_port, frame, net):
        to, frm, data = frame
        if to in (self.mac, BROADCAST):
            net.say(f"    {self.name} receives {frm}→{to} ✓")
        else:
            net.say(f"    {self.name} ignores {frm}→{to}")


class Switch:
    def __init__(self, name, ident):
        self.name, self.ident = name, ident
        self.ports = {}                         # port number -> (node, their port)
        self.table = {}                         # mac -> port
        self.blocked = set()                    # ports switched off by spanning tree

    # --8<-- [start:learn]
    def receive(self, in_port, frame, net):
        to, frm, data = frame
        if in_port in self.blocked:
            return                                            # spanning tree: ignore this port
        old = self.table.get(frm)
        self.table[frm] = in_port                             # LEARN: frm lives out of in_port
        if old is not None and old != in_port:
            net.say(f"    {self.name}: {frm} moved from port {old} to port {in_port}?!")
        if to != BROADCAST and to in self.table:
            out = self.table[to]
            if out == in_port:
                net.say(f"    {self.name}: {to} is back where it came from, so drop it")
                return
            net.say(f"    {self.name}: {to} is on port {out}, forward there")
            net.send(self, out, frame)
        else:
            why = "broadcast" if to == BROADCAST else f"don't know {to} yet"
            outs = [p for p in self.ports if p != in_port and p not in self.blocked]
            net.say(f"    {self.name}: {why}, flood out of ports {outs}")
            for p in outs:
                net.send(self, p, frame)
    # --8<-- [end:learn]


class Network:
    def __init__(self):
        self.nodes = {}
        self.queue = deque()
        self.log = []

    def say(self, text):
        print(text)

    def add(self, node):
        self.nodes[node.name] = node
        return node

    def cable(self, a, a_port, b, b_port=None):
        """Connect a (switch or host) to b. Hosts have a single port called 0."""
        a_port = 0 if isinstance(a, Host) else a_port
        b_port = 0 if isinstance(b, Host) else b_port
        for node, port, other, other_port in ((a, a_port, b, b_port), (b, b_port, a, a_port)):
            if isinstance(node, Host):
                node.link = (other, other_port)
            else:
                node.ports[port] = (other, other_port)

    def send(self, node, port, frame):
        other, other_port = node.link if isinstance(node, Host) else node.ports[port]
        self.queue.append((other, other_port, frame))

    def transmit(self, host_name, to):
        host = self.nodes[host_name]
        frame = (to, host.mac, "hello")
        print(f"\n{host.name} sends a frame to {to}{' (broadcast)' if to == BROADCAST else ''}")
        self.send(host, 0, frame)
        events = 0
        while self.queue:
            node, port, frame = self.queue.popleft()
            node.receive(port, frame, self)
            events += 1
            if events >= MAX_EVENTS:
                print(f"\n  💥 still {len(self.queue)} copies of that frame bouncing around after {events} hops. "
                      f"Giving up: this is a BROADCAST STORM.")
                self.queue.clear()

    def tables(self):
        for node in self.nodes.values():
            if isinstance(node, Switch):
                entries = ", ".join(f"{mac}→port {p}" for mac, p in sorted(self.nodes[node.name].table.items())) or "(empty)"
                blocked = f"   blocked ports: {sorted(node.blocked)}" if node.blocked else ""
                print(f"  {node.name} table: {entries}{blocked}")


# --8<-- [start:stp]
def spanning_tree(net):
    """Pick the switch with the lowest id as root, keep each switch's shortest path to it,
    and block every other switch-to-switch port. (Real switches work this out by
    exchanging messages; here we just compute the answer.)"""
    switches = [n for n in net.nodes.values() if isinstance(n, Switch)]
    root = min(switches, key=lambda s: s.ident)
    dist, parent_port = {root.name: 0}, {}
    frontier = deque([root])
    while frontier:
        sw = frontier.popleft()
        for port, (other, other_port) in sorted(sw.ports.items()):
            if isinstance(other, Switch) and other.name not in dist:
                dist[other.name] = dist[sw.name] + 1
                parent_port[other.name] = other_port        # the port that leads toward the root
                frontier.append(other)
    for sw in switches:
        for port, (other, other_port) in sw.ports.items():
            if not isinstance(other, Switch):
                continue
            on_tree = parent_port.get(sw.name) == port or parent_port.get(other.name) == other_port
            if not on_tree:
                sw.blocked.add(port)
    print(f"spanning tree: root is {root.name}. Blocked: " +
          ", ".join(f"{s.name} port {p}" for s in switches for p in sorted(s.blocked)))
# --8<-- [end:stp]


def build(kind, stp):
    net = Network()
    if kind == "learn":
        s1 = net.add(Switch("S1", 1))
        for i, name in enumerate("ABCD", start=1):
            net.cable(net.add(Host(name)), 0, s1, i)
        default = "A:B,B:A,C:A,A:C,D:ff,D:B"
    elif kind == "two":
        s1, s2 = net.add(Switch("S1", 1)), net.add(Switch("S2", 2))
        for i, name in enumerate("AB", start=1):
            net.cable(net.add(Host(name)), 0, s1, i)
        for i, name in enumerate("CD", start=1):
            net.cable(net.add(Host(name)), 0, s2, i)
        net.cable(s1, 9, s2, 9)
        default = "A:D,D:A,B:A,C:B"
    else:  # storm: three switches wired in a triangle
        s1, s2, s3 = net.add(Switch("S1", 1)), net.add(Switch("S2", 2)), net.add(Switch("S3", 3))
        net.cable(net.add(Host("A")), 0, s1, 1)
        net.cable(net.add(Host("B")), 0, s2, 1)
        net.cable(net.add(Host("C")), 0, s3, 1)
        net.cable(s1, 2, s2, 3)
        net.cable(s2, 2, s3, 3)
        net.cable(s3, 2, s1, 3)
        default = "A:ff,B:C"
    if stp:
        spanning_tree(net)
    return net, default


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scenario", choices=["learn", "two", "storm"])
    p.add_argument("--stp", action="store_true", help="run spanning tree before sending anything")
    p.add_argument("--send", help="comma-separated SENDER:RECEIVER pairs, e.g. A:B,B:ff")
    args = p.parse_args()
    net, default = build(args.scenario, args.stp)
    for pair in (args.send or default).split(","):
        sender, receiver = pair.split(":")
        net.transmit(sender, receiver)
        net.tables()


if __name__ == "__main__":
    main()
