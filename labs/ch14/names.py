#!/usr/bin/env python3
"""Chapter 14 lab: the town's name servers, and a resolver that asks them for you.

    python3 names.py              start everything (Ctrl-C to stop); leave it running
    python3 names.py --naive      ...with a trusting resolver that Eve can fool (see eve.py)

Then, in another terminal:  python3 lookup.py otto.seaside

    port 7053  the root: knows who's in charge of each part of town
    port 7054  seaside's name server (Grandpa Otto's town)
    port 7055  school's name server
    port 7056  library's name server
    port 7050  the resolver on Alice's street: asks around, and remembers answers

Messages are short lines of text:
    Q <id> <name>                          a question
    A <id> <name> <address> <seconds>      an answer, good for that many seconds
    R <id> <zone> <port> <seconds>         a referral: "ask the server on <port>, it's in charge of <zone>"
    N <id> <name>                          no such name
"""
import argparse
import random
import selectors
import socket
import threading
import time

HOST = "127.0.0.1"
ROOT_PORT, RESOLVER_PORT = 7053, 7050

# --8<-- [start:zones]
ZONES = {
    ROOT_PORT: {"seaside": ("R", 7054, 600), "school": ("R", 7055, 600), "library": ("R", 7056, 600),
                "street": ("R", 7057, 600)},
    7054: {"otto.seaside": ("A", "4.2", 30), "harbor.seaside": ("A", "4.8", 30), "cafe.seaside": ("A", "4.5", 30)},
    7055: {"newsletter.school": ("A", "2.7", 30), "teacher.school": ("A", "2.1", 30)},
    7056: {"catalog.library": ("A", "3.1", 30)},
    7057: {"alice.street": ("A", "1.1", 30), "bob.street": ("A", "1.2", 30), "carol.street": ("A", "1.3", 30)},
}
# --8<-- [end:zones]
NAMES = {7053: "root", 7054: "seaside", 7055: "school", 7056: "library", 7057: "street"}


# --8<-- [start:server]
def name_server(sock, port):
    """Answer from our own zone if we can; otherwise point to whoever is in charge of the name's last part."""
    zone = ZONES[port]
    while True:
        data, asker = sock.recvfrom(512)
        parts = data.decode().split()
        if len(parts) == 3 and parts[0] == "Q":
            _, qid, name = parts
            if name in zone and zone[name][0] == "A":
                _, addr, ttl = zone[name]
                reply = f"A {qid} {name} {addr} {ttl}"
            elif name.split(".")[-1] in zone:
                top = name.split(".")[-1]
                _, where, ttl = zone[top]
                reply = f"R {qid} {top} {where} {ttl}"
            else:
                reply = f"N {qid} {name}"
            sock.sendto(reply.encode(), asker)
        elif len(parts) == 3 and parts[0] == "U" and parts[1] in zone:     # an update from the zone's owner
            zone[parts[1]] = ("A", parts[2], zone[parts[1]][2])
            print(f"[{NAMES[port]}] {parts[1]} is now {parts[2]}")
# --8<-- [end:server]


class Resolver:
    def __init__(self, naive):
        self.naive = naive
        self.cache = {}                 # name or zone -> (kind, value, expires)
        self.next_id = 1
        self.out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.out.bind((HOST, 7051 if naive else 0))   # the naive resolver always asks from port 7051
        self.out.settimeout(1.0)

    def remember(self, key, kind, value, ttl):
        self.cache[key] = (kind, value, time.monotonic() + int(ttl))

    def recall(self, key):
        hit = self.cache.get(key)
        if hit and hit[2] > time.monotonic():
            return hit
        self.cache.pop(key, None)
        return None

    # --8<-- [start:ask]
    def ask(self, port, name):
        if self.naive:
            qid = self.next_id                        # 1, 2, 3, ... easy to guess
            self.next_id += 1
        else:
            qid = random.randrange(65536)             # a random number Eve would have to guess
        self.out.sendto(f"Q {qid} {name}".encode(), (HOST, port))
        while True:
            data, sender = self.out.recvfrom(512)
            parts = data.decode().split()
            if parts[1] != str(qid):
                continue                              # an answer to some other question
            if not self.naive and sender != (HOST, port):
                continue                              # not from the server we asked: ignore it
            return parts
    # --8<-- [end:ask]

    # --8<-- [start:resolve]
    def resolve(self, name):
        steps = []
        hit = self.recall(name)
        if hit:
            left = hit[2] - time.monotonic()
            return f"A {name} {hit[1]} remembered, {left:.0f}s left", steps
        top = name.split(".")[-1]
        referral = self.recall(top)
        port = referral[1] if referral else ROOT_PORT        # start at the root, unless we know better
        if referral:
            steps.append(f"remembered that {top} is served on port {port}")
        for _ in range(5):
            steps.append(f"asked {NAMES.get(port, port)} (port {port}) about {name}")
            reply = self.ask(port, name)
            if reply[0] == "A":
                self.remember(name, "A", reply[3], reply[4])
                return f"A {name} {reply[3]} fresh, good for {reply[4]}s", steps
            if reply[0] == "R":
                self.remember(reply[2], "R", int(reply[3]), reply[4])
                port = int(reply[3])
                continue
            return f"N {name}", steps
        return f"N {name}", steps
    # --8<-- [end:resolve]

    def serve(self, sock):
        while True:
            data, asker = sock.recvfrom(512)
            parts = data.decode().split()
            if len(parts) == 2 and parts[0] == "Q":
                try:
                    answer, steps = self.resolve(parts[1])
                except socket.timeout:
                    answer, steps = f"N {parts[1]} (timed out)", []
                for s in steps:
                    print(f"[resolver]  {s}")
                print(f"[resolver] → {answer}")
                sock.sendto(("\n".join([answer] + steps)).encode(), asker)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--naive", action="store_true", help="predictable question numbers, and believe any answer")
    args = p.parse_args()
    for port in ZONES:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, port))
        threading.Thread(target=name_server, args=(sock, port), daemon=True).start()
        print(f"{NAMES[port]:>8} name server on port {port}: {', '.join(ZONES[port])}")
    resolver = Resolver(args.naive)
    rsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rsock.bind((HOST, RESOLVER_PORT))
    print(f"resolver on port {RESOLVER_PORT}" + (" (NAIVE: numbered questions from port 7051, believes anyone)" if args.naive else ""))
    print("Ready. Ctrl-C to stop.\n")
    try:
        resolver.serve(rsock)
    except KeyboardInterrupt:
        print("\nname servers shutting down")


if __name__ == "__main__":
    main()
