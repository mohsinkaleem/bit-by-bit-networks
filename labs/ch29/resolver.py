#!/usr/bin/env python3
"""Chapter 29 lab: a real DNS resolver, from scratch. It starts at the root, like the real ones.

    python3 resolver.py info.cern.ch                  follow the referrals from the root to the answer
    python3 resolver.py www.bbc.co.uk AAAA
    python3 resolver.py info.cern.ch cds.cern.ch      the second lookup reuses what the first one learned
    python3 resolver.py nope-xyz.cern.ch              a name that doesn't exist

It asks with recursion switched off ("don't look it up for me, just tell me what you know"),
exactly as your internet provider's resolver does when it has nothing in its cache.
"""
import argparse
import random
import socket
import time

import dnswire
from dig import ask

# Where to start: the root servers. Every resolver in the world ships with this list.
ROOTS = {"a.root-servers.net.": "198.41.0.4", "b.root-servers.net.": "170.247.170.2",
         "c.root-servers.net.": "192.33.4.12", "d.root-servers.net.": "199.7.91.13",
         "e.root-servers.net.": "192.203.230.10", "f.root-servers.net.": "192.5.5.241",
         "g.root-servers.net.": "192.112.36.4", "h.root-servers.net.": "198.97.190.53",
         "i.root-servers.net.": "192.36.148.17", "j.root-servers.net.": "192.58.128.30",
         "k.root-servers.net.": "193.0.14.129", "l.root-servers.net.": "199.7.83.42",
         "m.root-servers.net.": "202.12.27.33"}


class Resolver:
    def __init__(self, verbose=True):
        self.cache = {}                       # (name, type) -> (expires at, records)
        self.zones = {".": dict(ROOTS)}       # zone -> {name server: address}, learned from referrals
        self.verbose, self.queries, self.depth = verbose, 0, 0

    def say(self, text):
        if self.verbose:
            print("   " * self.depth + text)

    def cached(self, name, rtype):
        hit = self.cache.get((name, rtype))
        if hit and hit[0] > time.time():
            return hit[1]
        return None

    def remember(self, records):
        for name, ttl, rtype, data in records:
            key = (name, rtype)
            exp, old = self.cache.get(key, (0, []))
            self.cache[key] = (time.time() + ttl, old + [(name, ttl, rtype, data)] if exp > time.time() else [(name, ttl, rtype, data)])

    # --8<-- [start:resolve]
    def resolve(self, name, rtype="A"):
        name = name.rstrip(".") + "."
        if (hit := self.cached(name, rtype)) is not None:
            self.say(f"{name} {rtype}: in the cache")
            return hit
        zone = self.closest_zone(name)            # start as close to the answer as we already know
        while True:
            server, address = self.pick(zone)
            self.queries += 1
            reply, how = ask(address, dnswire.build_query(name, rtype, recursion=False))
            m = dnswire.parse(reply)
            self.say(f"asked {server:<24} ({address:<15}) about {name} {rtype}: " + self.summary(m, how))
            if m["answer"]:
                self.remember(m["answer"])
                wanted = [r for r in m["answer"] if r[2] == rtype]
                if wanted:
                    return wanted
                cname = next(r[3] for r in m["answer"] if r[2] == "CNAME")
                self.say(f"it's an alias: now looking up {cname}")
                return [r for r in m["answer"] if r[2] == "CNAME"] + self.resolve(cname, rtype)
            if m["rcode"] == "NXDOMAIN" or not any(r[2] == "NS" for r in m["authority"]):
                return []                         # no such name, or no such record type
            # a referral: "I don't know, but these servers are responsible for a zone closer to it"
            child = m["authority"][0][0]
            glue = {r[0]: r[3] for r in m["additional"] if r[2] == "A"}
            self.zones[child] = {r[3]: glue.get(r[3]) for r in m["authority"] if r[2] == "NS"}
            zone = child
    # --8<-- [end:resolve]

    def closest_zone(self, name):
        labels = name.split(".")
        for i in range(len(labels)):
            zone = ".".join(labels[i:]) or "."
            if zone in self.zones:
                return zone
        return "."

    # --8<-- [start:pick]
    def pick(self, zone):
        """Choose one of the zone's name servers. If we only know its name (no "glue" address came
        with the referral), we have to look the name server itself up first."""
        servers = self.zones[zone]
        with_address = [(n, a) for n, a in servers.items() if a]
        if with_address:
            return random.choice(with_address)
        server = random.choice(list(servers))
        self.say(f"no address for {server}: looking that up first")
        self.depth += 1
        records = self.resolve(server, "A")
        self.depth -= 1
        address = next(r[3] for r in records if r[2] == "A")
        servers[server] = address
        return server, address
    # --8<-- [end:pick]

    @staticmethod
    def summary(m, how):
        if m["answer"]:
            return "the answer: " + ", ".join(f"{r[2]} {r[3]}" for r in m["answer"]) + f"  [{how}]"
        if m["rcode"] == "NXDOMAIN":
            return f"no such name (NXDOMAIN)  [{how}]"
        ns = [r for r in m["authority"] if r[2] == "NS"]
        if ns:
            glue = sum(1 for r in m["additional"] if r[2] in ("A", "AAAA"))
            return f"go and ask the {len(ns)} servers for {ns[0][0]} ({glue} glue addresses)  [{how}]"
        return f"nothing  [{how}]"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("names", nargs="+")
    a = p.parse_args()
    rtype = "A"
    names = []
    for x in a.names:
        if x.upper() in dnswire.CODES:
            rtype = x.upper()
        else:
            names.append(x)
    r = Resolver()
    for name in names:
        t, before = time.perf_counter(), r.queries
        print(f"\n{name} {rtype}?")
        answer = r.resolve(name, rtype)
        ms = (time.perf_counter() - t) * 1000
        found = [x for x in answer if x[2] == rtype]
        aliases = [x[3] for x in answer if x[2] == "CNAME"]
        result = ", ".join(f"{x[2]} {x[3]}" for x in found) or (f"no {rtype} record" if aliases else "nothing: it doesn't exist")
        if aliases:
            result += "   (via " + " → ".join(aliases) + ")"
        print(f"=> {result}   ({r.queries - before} questions, {ms:.0f} ms)")


if __name__ == "__main__":
    main()
