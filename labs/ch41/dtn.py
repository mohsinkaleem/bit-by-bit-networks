#!/usr/bin/env python3
"""Chapter 41 lab: delay-tolerant networking, with real Bundle Protocol bundles (RFC 9171).

    python3 dtn.py             a question from Earth to a Mars rover and its answer, over UDP, in fast-forward
    python3 dtn.py --bundle    build one bundle and take it apart, byte by byte
    python3 dtn.py --send      send one bundle to 127.0.0.1 port 4556, for Wireshark or tshark to decode

Three bundle nodes (Earth, a Mars orbiter and a rover) run in this one program, each with its own UDP
socket, as in RFC 7122's UDP "convergence layer". They follow a contact plan: the times when each radio
link will be up. A bundle waits in storage until its next link opens. One second here is half an hour.
Python 3.9+, no packages.
"""
import socket
import sys
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------- CBOR (RFC 8949): compact, typed bytes

# --8<-- [start:cbor]
class Indefinite(list):
    """An array whose length isn't written at the start: it ends with a 'break' byte instead."""


def cbor(item):
    def head(major, n):                          # 3 bits of type, then the length or the number itself
        if n < 24:
            return bytes([major << 5 | n])
        size = 1 if n < 256 else 2 if n < 65536 else 4 if n < 2 ** 32 else 8
        return bytes([major << 5 | {1: 24, 2: 25, 4: 26, 8: 27}[size]]) + n.to_bytes(size, "big")
    if isinstance(item, int):
        return head(0, item)                                  # major type 0: a whole number
    if isinstance(item, bytes):
        return head(2, len(item)) + item                      # 2: a byte string
    if isinstance(item, str):
        return head(3, len(item.encode())) + item.encode()    # 3: a text string
    if isinstance(item, Indefinite):
        return b"\x9f" + b"".join(cbor(i) for i in item) + b"\xff"
    if isinstance(item, list):
        return head(4, len(item)) + b"".join(cbor(i) for i in item)   # 4: an array
    raise TypeError(item)


def uncbor(data, i=0):
    """Decode one item starting at data[i]; return (item, where the next item starts)."""
    major, info = data[i] >> 5, data[i] & 31
    i += 1
    if info == 31 and major == 4:                             # an indefinite array: items until 0xff
        items = Indefinite()
        while data[i] != 0xFF:
            item, i = uncbor(data, i)
            items.append(item)
        return items, i + 1
    if info >= 24:
        size = 1 << (info - 24)
        n, i = int.from_bytes(data[i:i + size], "big"), i + size
    else:
        n = info
    if major == 0:
        return n, i
    if major in (2, 3):
        raw = data[i:i + n]
        return (raw if major == 2 else raw.decode()), i + n
    if major == 4:
        items = []
        for _ in range(n):
            item, i = uncbor(data, i)
            items.append(item)
        return items, i
    raise ValueError(f"CBOR major type {major} isn't used here")
# --8<-- [end:cbor]


def crc16_x25(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return crc ^ 0xFFFF


# ---------------------------------------------------------------- bundles (RFC 9171)

# --8<-- [start:bundle]
DTN_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)


def eid(uri):
    """An endpoint ID like dtn://rover/camera, as [scheme 1 (dtn), "//rover/camera"]."""
    return [1, 0] if uri == "dtn:none" else [1, uri[4:]]


def make_bundle(src, dst, payload, seq, lifetime_hours=24 * 7, created=None):
    """src is the sending node, like dtn://earth/; dst is an endpoint on a node, like dtn://rover/camera."""
    created = created or int((datetime.now(timezone.utc) - DTN_EPOCH).total_seconds() * 1000)
    primary = [7,                        # Bundle Protocol version 7
               0,                        # flags: nothing special
               1,                        # CRC type 1: a CRC-16 protects this block
               eid(dst), eid(src),       # where it's going, and which node sent it
               eid("dtn:none"),          # who wants status reports: nobody
               [created, seq],           # created when (ms since 2000), and a sequence number
               lifetime_hours * 3600000, # after this many ms, it's useless: delete it
               b"\x00\x00"]              # the CRC, zero while we calculate it…
    primary[-1] = crc16_x25(cbor(primary)).to_bytes(2, "big")         # …then filled in
    hops = [10, 2, 0, 0, cbor([16, 0])]  # block type 10, "hop count": at most 16 hops, 0 so far
    body = [1, 1, 0, 0, payload]         # block type 1, the payload, always last
    return cbor(Indefinite([primary, hops, body]))


def read_bundle(data):
    blocks, _ = uncbor(data)
    primary, *others = blocks
    crc, check = primary[-1], list(primary)
    check[-1] = b"\x00\x00"
    if crc16_x25(cbor(check)).to_bytes(2, "big") != crc:
        raise ValueError("CRC doesn't match: damaged on the way")
    fields = {"dst": "dtn:" + primary[3][1], "src": "dtn:" + primary[4][1], "created": primary[6][0], "seq": primary[6][1]}
    for block in others:
        if block[0] == 1:
            fields["payload"] = block[4]
        if block[0] == 10:
            fields["hops"] = uncbor(block[4])[0][1]
    return fields


def count_hop(data):
    """Forwarding a bundle adds one to its hop count. (The primary block never changes.)"""
    blocks, _ = uncbor(data)
    for block in blocks[1:]:
        if block[0] == 10:
            limit, count = uncbor(block[4])[0]
            block[4] = cbor([limit, count + 1])
    return cbor(Indefinite(blocks))
# --8<-- [end:bundle]


# ---------------------------------------------------------------- three nodes and a contact plan

LIGHT = 14                  # minutes, Earth to Mars, one way (python3 mars.py, 28 September 2026)
MINUTES_PER_SECOND = 30     # the fast-forward: one real second is half an hour
# --8<-- [start:plan]
PLAN = {                    # when each link is up, in minutes from the start (06:00 on day 1)
    ("earth", "orbiter"): [(0, 120), (1440, 1560)],                   # a big dish on Earth, two hours a day
    ("orbiter", "earth"): [(0, 120), (1440, 1560)],
    ("orbiter", "rover"): [(200, 212), (940, 952), (1680, 1692)],     # the orbiter passes over the rover
    ("rover", "orbiter"): [(200, 212), (940, 952), (1680, 1692)],     # twice a Martian day, for 12 minutes
}
DELAY = {("earth", "orbiter"): LIGHT, ("orbiter", "earth"): LIGHT}    # the orbiter and rover are close
ROUTE = {"earth": {"rover": "orbiter"}, "orbiter": {"rover": "rover", "earth": "earth"},
         "rover": {"earth": "orbiter"}}
PORTS = {"earth": 4556, "orbiter": 4557, "rover": 4558}
# --8<-- [end:plan]


def clock(minutes):
    day, rest = divmod(int(minutes) + 6 * 60, 24 * 60)
    return f"day {day + 1}, {rest // 60:02d}:{rest % 60:02d}"


class Node:
    def __init__(self, name):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", PORTS[name]))
        self.sock.setblocking(False)
        self.stored = []                   # bundles waiting for a contact
        self.in_flight = []                # (arrival time, next hop, bytes): radio waves on their way

    def say(self, now, text):
        print(f"  {clock(now):>13}  {self.name:<8} {text}", flush=True)

    # --8<-- [start:forward]
    def tick(self, now, sent_by_app):
        for data in sent_by_app:
            self.stored.append(data)
        for data in list(self.stored):                        # anything waiting that can go now?
            dst = read_bundle(data)["dst"].split("/")[2]
            hop = ROUTE[self.name][dst]
            if any(a <= now < b for a, b in PLAN[(self.name, hop)]):
                self.stored.remove(data)
                arrive = now + DELAY.get((self.name, hop), 0)
                self.in_flight.append((arrive, hop, count_hop(data)))
                self.say(now, f"link to {hop} is up: sent it" + (f"; it arrives in {arrive - now:.0f} minutes" if arrive > now else ""))
        for flight in list(self.in_flight):                   # radio waves that have now arrived
            if flight[0] <= now:
                self.in_flight.remove(flight)
                self.sock.sendto(flight[2], ("127.0.0.1", PORTS[flight[1]]))
    # --8<-- [end:forward]

    def receive(self, now):
        delivered = []
        while True:
            try:
                data, _ = self.sock.recvfrom(65535)
            except BlockingIOError:
                return delivered
            b = read_bundle(data)
            if b["dst"].split("/")[2] == self.name:
                self.say(now, f"delivered ({b['hops']} hops): “{b['payload'].decode()}”")
                delivered.append(b)
            else:
                self.stored.append(data)
                self.say(now, f"received a bundle for {b['dst']} ({len(data)} bytes); stored, waiting for a link")


def run():
    nodes = {n: Node(n) for n in PORTS}
    print(f"Earth to Mars: {LIGHT} minutes, one way. One second here is {MINUTES_PER_SECOND} minutes.")
    start = time.monotonic()
    question = make_bundle("dtn://earth/", "dtn://rover/camera", b"Please photograph the crater rim.", 1)
    outbox = {"earth": [question], "orbiter": [], "rover": []}
    nodes["earth"].say(5, f"new bundle for dtn://rover/camera ({len(question)} bytes)")
    got_answer = None
    while got_answer is None:
        now = 5 + (time.monotonic() - start) * MINUTES_PER_SECOND
        for name, node in nodes.items():
            node.tick(now, outbox[name])
            outbox[name] = []
        for name, node in nodes.items():
            for b in node.receive(now):
                if name == "rover":
                    reply = make_bundle("dtn://rover/", "dtn://earth/bob", b"rim.jpg: done. (thumbnail attached)", 1)
                    outbox["rover"].append(reply)
                    node.say(now, "the camera takes the photo, and sends a bundle back")
                if name == "earth":
                    got_answer = now
        time.sleep(0.02)
    print(f"question and answer took {(got_answer - 5) / 60:.1f} hours; light alone needs {2 * LIGHT} minutes.")
    together = [t for t in range(0, 3000) if all(any(a <= t < b for a, b in PLAN[link])
                                                  for link in (("earth", "orbiter"), ("orbiter", "rover")))]
    print(f"minutes when a whole path from Earth to the rover existed at once: {len(together)}")


# --8<-- [start:describe]
def describe():
    data = make_bundle("dtn://earth/", "dtn://rover/camera", b"Please photograph the crater rim.", 1,
                       created=int((datetime(2026, 9, 28, 6, 5, tzinfo=timezone.utc) - DTN_EPOCH).total_seconds() * 1000))
    print(f"one bundle, {len(data)} bytes:")
    print("  " + data.hex(" "))
    blocks, _ = uncbor(data)
    names = ["version", "flags", "CRC type", "destination", "source", "report to", "created (ms since 2000), number",
             "lifetime (ms)", "CRC-16"]
    print("the primary block:")
    for name, value in zip(names, blocks[0]):
        shown = "0x" + value.hex() if isinstance(value, bytes) else repr(value)
        print(f"  {name:<32} {cbor(value).hex(' '):<52} {shown}")
    for block in blocks[1:]:
        kind = {1: "payload", 10: "hop count"}[block[0]]
        print(f"a {kind} block: type {block[0]}, number {block[1]}, flags {block[2]}, CRC type {block[3]}, data {block[4]!r}")
    print("read back:", read_bundle(data))
# --8<-- [end:describe]


if __name__ == "__main__":
    if "--bundle" in sys.argv:
        describe()
    elif "--send" in sys.argv:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(make_bundle("dtn://earth/", "dtn://rover/camera", b"Please photograph the crater rim.", 1),
                 ("127.0.0.1", 4556))
        print("sent one bundle to 127.0.0.1 port 4556")
    else:
        run()
