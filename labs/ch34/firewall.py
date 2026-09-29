#!/usr/bin/env python3
"""Chapter 34 lab: a packet filter, first without memory, then with connection tracking.

    python3 firewall.py              the same packets through both firewalls
    python3 firewall.py --table      …and the connection-tracking table after each packet

Grandpa's Pi (192.168.1.4) should be able to reach anything, answer SSH only from the home network,
and accept nothing else from outside. Both firewalls see the same twelve packets, including two
from Eve (198.51.100.66).
"""
import sys
from dataclasses import dataclass

PI, LAN = "192.168.1.4", "192.168.1."


@dataclass
class Packet:
    note: str
    src: str
    dst: str
    proto: str               # tcp, udp or icmp
    sport: int = 0
    dport: int = 0
    flags: str = ""          # for TCP: S, SA, A, F…; for ICMP: the type
    t: float = 0.0           # seconds since the start
    about: tuple = ()        # ICMP errors carry the start of the packet they're about


TRAFFIC = [
    Packet("Pi opens a connection to example.org", PI, "104.20.26.136", "tcp", 51000, 443, "S", 0.0),
    Packet("…example.org answers", "104.20.26.136", PI, "tcp", 443, 51000, "SA", 0.03),
    Packet("…and sends the web page", "104.20.26.136", PI, "tcp", 443, 51000, "A", 0.07),
    Packet("Pi asks the router for a name", PI, "192.168.1.1", "udp", 40000, 53, "", 1.0),
    Packet("…and gets an answer", "192.168.1.1", PI, "udp", 53, 40000, "", 1.01),
    Packet("Bob's laptop connects with SSH", "192.168.1.3", PI, "tcp", 60000, 22, "S", 2.0),
    Packet("Eve tries SSH from the internet", "198.51.100.66", PI, "tcp", 55555, 22, "S", 3.0),
    Packet("Eve's “reply” from port 443, to a port nobody opened", "198.51.100.66", PI, "tcp", 443, 22, "SA", 3.5),
    Packet("Eve's UDP “DNS answer” nobody asked for", "198.51.100.66", PI, "udp", 53, 40001, "", 4.0),
    Packet("Pi runs traceroute: a UDP probe", PI, "188.184.67.127", "udp", 33434, 33435, "", 5.0),
    Packet("…a router says “time exceeded”", "203.0.113.9", PI, "icmp", 0, 0, "time-exceeded", 5.02,
           ("udp", PI, 33434, "188.184.67.127", 33435)),
    Packet("the DNS server answers again, 3 minutes later", "192.168.1.1", PI, "udp", 53, 40000, "", 181.0),
]


# ---------------------------------------------------------------- without memory

# --8<-- [start:stateless]
def stateless(p):
    """Rules that only look at one packet at a time. To let replies in, they must guess what a reply looks like."""
    if p.src == PI:
        return "accept", "anything from the Pi may go out"
    if p.proto == "tcp" and p.sport == 443:
        return "accept", "let in anything from port 443 (it's probably a web server replying)"
    if p.proto == "udp" and p.sport == 53:
        return "accept", "let in anything from port 53 (it's probably a DNS answer)"
    if p.proto == "tcp" and p.dport == 22 and p.src.startswith(LAN):
        return "accept", "SSH from the home network"
    if p.proto == "icmp":
        return "accept", "let in ICMP (we need its errors)"
    return "drop", "everything else"
# --8<-- [end:stateless]


# ---------------------------------------------------------------- with connection tracking

# --8<-- [start:conntrack]
class Conntrack:
    TIMEOUTS = {"tcp": 432000, "udp": 30, "icmp": 30}         # seconds: Linux's defaults (an established TCP connection: 5 days)

    def __init__(self):
        self.table = {}                                       # (proto, src, sport, dst, dport) → {"state", "expires"}

    def key(self, p):
        return (p.proto, p.src, p.sport, p.dst, p.dport)

    def reverse(self, p):
        return (p.proto, p.dst, p.dport, p.src, p.sport)

    def lookup(self, p):
        """'established' if this packet belongs to a connection we've seen, 'related' if it's an error about one."""
        for k in list(self.table):
            if self.table[k]["expires"] < p.t:
                del self.table[k]                            # forget connections that have gone quiet
        if p.proto == "icmp" and p.about:
            proto, src, sport, dst, dport = p.about
            return "related" if (proto, src, sport, dst, dport) in self.table else "new"
        for k in (self.key(p), self.reverse(p)):
            if k in self.table:
                entry = self.table[k]
                entry["expires"] = p.t + self.TIMEOUTS[p.proto]
                if k == self.reverse(p):
                    entry["state"] = "ESTABLISHED"           # we've seen traffic both ways
                return "established"
        return "new"

    def remember(self, p):
        self.table[self.key(p)] = {"state": "NEW", "expires": p.t + self.TIMEOUTS[p.proto]}


def stateful(p, ct):
    state = ct.lookup(p)
    if state in ("established", "related"):
        return "accept", f"ct state {state}: part of (or about) a connection already allowed"
    if p.src == PI:
        ct.remember(p)
        return "accept", "new, from the Pi: allowed, and remembered"
    if p.proto == "tcp" and p.dport == 22 and p.flags == "S" and p.src.startswith(LAN):
        ct.remember(p)
        return "accept", "new SSH connection from the home network: allowed, and remembered"
    return "drop", "new, from outside: dropped"
# --8<-- [end:conntrack]


def main():
    show_table = "--table" in sys.argv
    ct = Conntrack()
    width = max(len(p.note) for p in TRAFFIC)
    print(f"{'packet':<{width}}  without memory     with connection tracking")
    for p in TRAFFIC:
        v1, why1 = stateless(p)
        v2, why2 = stateful(p, ct)
        flag = "  ← different!" if v1 != v2 else ""
        print(f"{p.note:<{width}}  {v1.upper():<18} {v2.upper()}{flag}")
        if show_table or v1 != v2:
            print(f"{'':<{width}}    without: {why1}")
            print(f"{'':<{width}}    with:    {why2}")
        if show_table:
            for (proto, s, sp, d, dp), e in ct.table.items():
                print(f"{'':<{width}}      conntrack: {proto} {s}:{sp} → {d}:{dp}  {e['state']}, forget at {e['expires']:g} s")
    print("\nThe firewall without memory let Eve in twice, by pretending to be a reply. The one with memory knows what")
    print("the Pi really asked for, and only lets in answers to that, and errors about it, for as long as the conversation lasts.")


if __name__ == "__main__":
    main()
