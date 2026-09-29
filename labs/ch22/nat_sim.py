#!/usr/bin/env python3
"""Chapter 22 lab: a home router's NAT, simulated packet by packet.

    python3 nat_sim.py               a normal evening: several devices, one public address
    python3 nat_sim.py --forward     Bob's friend tries to join his game server, before and after port forwarding
    python3 nat_sim.py --punch       Alice and Bob, behind two different NATs, connect straight to each other
"""
import argparse

PUBLIC = "203.0.113.77"


# --8<-- [start:nat]
class Nat:
    """Rewrites addresses on the way out, remembers what it did, and undoes it on the way back."""

    def __init__(self, public, timeout=120):
        self.public, self.timeout = public, timeout
        self.out = {}          # (inside address, inside port) -> outside port
        self.back = {}         # outside port -> {"inside": (address, port), "remotes": set(), "last": time}
        self.forwards = {}     # outside port -> (inside address, inside port), set up by hand

    def outbound(self, now, src, dst):
        """A packet from inside, src=(address, port), going to dst. Returns the rewritten source."""
        port = self.out.get(src)
        if port is None or port not in self.back:
            port = src[1] if src[1] not in self.back and src[1] not in self.forwards else self.free_port()
            self.out[src] = port
            self.back[port] = {"inside": src, "remotes": set(), "last": now}
            note = "new mapping" + ("" if port == src[1] else f"; port {src[1]} was taken")
        else:
            note = "existing mapping"
        entry = self.back[port]
        entry["remotes"].add(dst)                  # from now on, answers from dst may come in
        entry["last"] = now
        return (self.public, port), note

    def inbound(self, now, src, dst_port):
        """A packet from outside, arriving at our public address and dst_port. Returns where it goes, or None."""
        self.expire(now)
        if dst_port in self.forwards:
            return self.forwards[dst_port], "port forwarding rule"
        entry = self.back.get(dst_port)
        if entry is None:
            return None, "no mapping for that port: nobody inside asked for this"
        if src not in entry["remotes"]:
            return None, f"{entry['inside'][0]} never sent anything to {src[0]}:{src[1]}"
        entry["last"] = now
        return entry["inside"], "an answer to something sent from inside"

    def expire(self, now):
        for port in [p for p, e in self.back.items() if now - e["last"] > self.timeout]:
            del self.out[self.back.pop(port)["inside"]]

    def free_port(self):
        port = 1024
        while port in self.back or port in self.forwards:
            port += 1
        return port
# --8<-- [end:nat]


def fmt(a):
    return f"{a[0]}:{a[1]}"


def send_out(nat, now, name, src, dst):
    new_src, note = nat.outbound(now, src, dst)
    print(f"{now:>4}s  {name:<14} {fmt(src):>21} → {fmt(dst):<20} leaves as {fmt(new_src):<20} ({note})")


def send_in(nat, now, name, src, port):
    where, why = nat.inbound(now, src, port)
    result = f"delivered to {fmt(where)}" if where else "DROPPED"
    print(f"{now:>4}s  {name:<14} {fmt(src):>21} → {fmt((nat.public, port)):<20} {result:<31} ({why})")


def table(nat, now):
    print(f"\nThe NAT's table at {now}s:")
    for port, e in sorted(nat.back.items()):
        remotes = ", ".join(sorted(fmt(r) for r in e["remotes"]))
        print(f"   {nat.public}:{port:<6} ↔ {fmt(e['inside']):<20} may hear from: {remotes}  (idle {now - e['last']}s)")
    for port, inside in nat.forwards.items():
        print(f"   {nat.public}:{port:<6} ↔ {fmt(inside):<20} forwarded, for anyone")
    print()


def evening():
    nat = Nat(PUBLIC)
    laptop, pi, tv = "192.168.1.3", "192.168.1.4", "192.168.1.8"
    cern, dns, video = ("188.184.67.127", 80), ("1.1.1.1", 53), ("198.51.100.200", 443)
    send_out(nat, 0, "Bob's laptop", (laptop, 52000), cern)
    send_out(nat, 0, "Grandpa's Pi", (pi, 52000), dns)
    send_out(nat, 1, "the TV", (tv, 33333), video)
    send_in(nat, 1, "CERN answers", cern, 52000)
    send_in(nat, 1, "1.1.1.1 answers", dns, 1024)
    send_in(nat, 2, "a stranger", ("198.51.100.66", 4444), 52000)
    send_in(nat, 2, "a stranger", ("198.51.100.66", 4444), 22)
    table(nat, 2)
    send_in(nat, 300, "CERN, late", cern, 52000)
    print("\nAfter five quiet minutes the mappings have expired, and even a real answer is turned away.")


def forward():
    nat = Nat(PUBLIC)
    gaming_pc, friend = ("192.168.1.20", 25565), ("198.51.100.50", 3000)
    send_in(nat, 0, "Bob's friend", friend, 25565)
    print("\nBob adds a rule in the router: outside port 25565 goes to his gaming PC.\n")
    nat.forwards[25565] = gaming_pc
    send_in(nat, 10, "Bob's friend", friend, 25565)
    table(nat, 10)


def punch():
    home, uni = Nat(PUBLIC), Nat("198.51.100.9")
    bob, alice, stun = ("192.168.1.3", 50000), ("10.23.147.8", 41000), ("192.0.2.1", 3478)
    print("Both ask a STUN server what they look like from outside:")
    send_out(home, 0, "Bob", bob, stun)
    send_out(uni, 0, "Alice", alice, stun)
    bob_out, alice_out = (home.public, 50000), (uni.public, 41000)
    print(f"\nThe game's server tells each the other's outside address: Bob is {fmt(bob_out)}, Alice is {fmt(alice_out)}.")
    print("Alice sends first. Bob's NAT has never heard of her:")
    send_out(uni, 1, "Alice", alice, bob_out)
    send_in(home, 1, "Alice → Bob", alice_out, bob_out[1])
    print("…but her packet opened a hole in HER NAT. Now Bob sends to her:")
    send_out(home, 1, "Bob", bob, alice_out)
    send_in(uni, 1, "Bob → Alice", bob_out, alice_out[1])
    print("…and that opened his. Now everything gets through, both ways, with no server in the middle:")
    send_out(uni, 2, "Alice", alice, bob_out)
    send_in(home, 2, "Alice → Bob", alice_out, bob_out[1])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--forward", action="store_true")
    p.add_argument("--punch", action="store_true")
    args = p.parse_args()
    if args.forward:
        forward()
    elif args.punch:
        punch()
    else:
        evening()


if __name__ == "__main__":
    main()
