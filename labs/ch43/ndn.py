#!/usr/bin/env python3
"""Chapter 43 lab: named-data networking (NDN), speaking the real NDN packet format over UDP.

    python3 ndn.py get /ndn/edu/ucla/ping/1234              ask the NDN testbed for a piece of data, by name
    python3 ndn.py get /grandpa/garden/beans.txt --via 192.168.1.4    …or ask your own NDN router for it
    python3 ndn.py router                                   be an NDN router: a content store, a pending
                                                            interest table and a forwarding table, on UDP 6363

Nothing here names a computer except the first hop. An Interest says what it wants; any router or cache
that has a matching Data packet may answer, and the Data proves itself with its own signature. The
research testbed (named-data.net) answers pings at /ndn/<site>/ping/<anything>. Python 3.9+, no packages.
"""
import argparse
import hashlib
import os
import select
import socket
import time

TESTBED = "suns.cs.ucla.edu"          # the NDN testbed's router at UCLA, where NDN began
PORT = 6363                           # NDN's port, for UDP and TCP
INTEREST, DATA, NAME, COMPONENT, NONCE, LIFETIME = 5, 6, 7, 8, 10, 12
MUST_BE_FRESH, CAN_BE_PREFIX, META, CONTENT, SIGINFO, SIGVALUE, SIGTYPE, FRESHNESS = 18, 33, 20, 21, 22, 23, 27, 25


# --8<-- [start:tlv]
def number(n):
    """NDN's variable-length numbers: one byte if small, else a marker byte and 2, 4 or 8 more."""
    if n < 253:
        return bytes([n])
    size = 2 if n < 65536 else 4 if n < 2 ** 32 else 8
    return bytes([{2: 253, 4: 254, 8: 255}[size]]) + n.to_bytes(size, "big")


def tlv(kind, value=b""):                        # Type, Length, Value: everything in NDN is built of these
    return number(kind) + number(len(value)) + value


def read_number(b, i):
    if b[i] < 253:
        return b[i], i + 1
    size = {253: 2, 254: 4, 255: 8}[b[i]]
    return int.from_bytes(b[i + 1:i + 1 + size], "big"), i + 1 + size


def elements(b):
    """Split bytes into a list of (type, value, raw bytes of the whole element)."""
    out, i = [], 0
    while i < len(b):
        start = i
        kind, i = read_number(b, i)
        length, i = read_number(b, i)
        out.append((kind, b[i:i + length], b[start:i + length]))
        i += length
    return out
# --8<-- [end:tlv]


def make_name(uri):
    return tlv(NAME, b"".join(tlv(COMPONENT, c.encode()) for c in uri.strip("/").split("/") if c))


def name_uri(name_value):
    return "/" + "/".join(v.decode(errors="replace") for _, v, _ in elements(name_value))


def components(name_value):
    return [raw for _, _, raw in elements(name_value)]


# --8<-- [start:packets]
def make_interest(uri, fresh=False, prefix=False):
    return tlv(INTEREST, make_name(uri)
               + (tlv(CAN_BE_PREFIX) if prefix else b"")          # "anything whose name starts with this"
               + (tlv(MUST_BE_FRESH) if fresh else b"")           # "not a stale copy, please"
               + tlv(NONCE, os.urandom(4))                        # a random number, to spot loops
               + tlv(LIFETIME, (4000).to_bytes(2, "big")))        # give up after 4 seconds


def make_data(uri, content, freshness_ms=10000):
    signed = (make_name(uri)
              + tlv(META, tlv(FRESHNESS, freshness_ms.to_bytes(4, "big")))  # how long a cached copy stays fresh
              + tlv(CONTENT, content)
              + tlv(SIGINFO, tlv(SIGTYPE, b"\x00")))              # signature type 0: a SHA-256 digest
    return tlv(DATA, signed + tlv(SIGVALUE, hashlib.sha256(signed).digest()))


def parse(packet):
    """Returns a dict describing an Interest or a Data packet (unwrapping NDNLP, if a router added it)."""
    (kind, value, _), = elements(packet)[:1]
    if kind == 100:                                               # an NDNLPv2 wrapper: find the fragment inside
        return parse(next(v for t, v, _ in elements(value) if t == 80))
    p = {"kind": {INTEREST: "Interest", DATA: "Data"}[kind], "raw": packet}
    for t, v, raw in elements(value):
        if t == NAME:
            p["name"], p["name_value"] = name_uri(v), v
        elif t == NONCE:
            p["nonce"] = v
        elif t == CAN_BE_PREFIX:
            p["prefix"] = True
        elif t == MUST_BE_FRESH:
            p["fresh"] = True
        elif t == META:
            p["freshness"] = next((int.from_bytes(fv, "big") for ft, fv, _ in elements(v) if ft == FRESHNESS), 0)
        elif t == CONTENT:
            p["content"] = v
        elif t == SIGINFO:
            p["sigtype"] = next((fv[0] for ft, fv, _ in elements(v) if ft == SIGTYPE), None)
            p["signed_end"] = value.index(raw) + len(raw)
        elif t == SIGVALUE:
            p["signature"] = v
    if p["kind"] == "Data" and p.get("sigtype") == 0:             # check the digest ourselves
        p["valid"] = hashlib.sha256(value[:p["signed_end"]]).digest() == p["signature"]
    return p
# --8<-- [end:packets]


def show(p):
    content = p.get("content", b"")
    text = content.decode() if content and all(32 <= c < 127 or c in (9, 10) for c in content) else f"{len(content)} bytes"
    print(f"  Data {p['name']}")
    print(f"    content:   {text!r}" if content else "    content:   (empty)")
    print(f"    fresh for: {p.get('freshness', 0)} ms")
    sig = {0: "SHA-256 digest", 1: "RSA", 3: "ECDSA", 4: "HMAC", 5: "Ed25519"}.get(p.get("sigtype"), "?")
    print(f"    signature: {sig}" + ({True: ", checked: it matches", False: ", checked: WRONG"}.get(p.get("valid"), "")))


def get(uri, via, fresh=False, prefix=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(5)
    interest = make_interest(uri, fresh, prefix)
    s.sendto(interest, (via, PORT))
    print(f"Interest {uri}{' (or anything under it)' if prefix else ''}: {len(interest)} bytes, to {via}")
    try:
        show(parse(s.recv(9000)))
    except socket.timeout:
        print("  no Data came back (nobody had it, or the Interest was lost)")


# ---------------------------------------------------------------- an NDN router

GARDEN = {"beans.txt": b"Runner beans: 2.1 kg this week. The slugs have gone.\n",
          "rota.txt": b"Watering: Bob on Saturday, Alice on Sunday.\n"}


def under(prefix, name):
    return name[:len(prefix)] == prefix


# --8<-- [start:router]
def router(upstream):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    up = (socket.gethostbyname(upstream), PORT)
    fib = [(components(make_name("/grandpa")[2:]), "the garden app, here"),   # forwarding table: prefix → where
           (components(make_name("/ndn")[2:]), up)]
    pit = {}                      # pending interests: name → (faces waiting for it, can be prefix, expires)
    store = {}                    # content store: name → (Data bytes, arrived at, fresh for ms)
    seen = {}                     # recent nonces, to spot Interests that have gone round in a loop
    print(f"NDN router on UDP port {PORT}: /grandpa is served here; /ndn goes to {upstream} ({up[0]})")
    while True:
        ready, _, _ = select.select([sock], [], [], 1)
        now = time.time()
        pit = {k: v for k, v in pit.items() if v[2] > now}
        if not ready:
            continue
        packet, face = sock.recvfrom(9000)
        p = parse(packet)
        who = "the testbed" if face == up else f"{face[0]}:{face[1]}"
        comps = components(p["name_value"])
        if p["kind"] == "Interest":
            if seen.get(p["nonce"], 0) > now:
                print(f"  Interest {p['name']} from {who}: a nonce I've seen before: a loop. Dropped.")
                continue
            seen[p["nonce"]] = now + 10
            for key, (data, t, fresh_ms) in store.items():            # 1. do I have it already?
                if (key == p["name_value"] or (p.get("prefix") and under(comps, components(key)))) and \
                        (not p.get("fresh") or now - t < fresh_ms / 1000):
                    sock.sendto(data, face)
                    print(f"  Interest {p['name']} from {who}: in my content store! Answered it myself.")
                    break
            else:
                key = p["name_value"]
                if key in pit:                                          # 2. has someone asked already?
                    pit[key][0].add(face)
                    print(f"  Interest {p['name']} from {who}: already asked upstream. Now {len(pit[key][0])} waiting.")
                    continue
                pit[key] = ({face}, p.get("prefix", False), now + 4)
                prefix, hop = max(((pfx, h) for pfx, h in fib if under(pfx, comps)), key=lambda x: len(x[0]),
                                  default=(None, None))                  # 3. longest prefix match (Chapter 23)
                if hop is None:
                    print(f"  Interest {p['name']} from {who}: no route. Dropped.")
                elif hop == up:
                    sock.sendto(packet, up)
                    print(f"  Interest {p['name']} from {who}: not here; forwarded to the testbed")
                else:
                    item = GARDEN.get(p["name"].split("/")[-1])
                    if item:
                        data = make_data(p["name"], item)
                        store[key] = (data, now, 10000)
                        for f in pit.pop(key)[0]:
                            sock.sendto(data, f)
                        print(f"  Interest {p['name']} from {who}: made the Data here ({len(data)} bytes), and cached it")
        else:
            waiting = [k for k, (faces, can_prefix, _) in pit.items()
                       if k == p["name_value"] or (can_prefix and under(components(k), comps))]
            if not waiting:
                print(f"  Data {p['name']} from {who}: nobody asked for it. Dropped.")   # no Interest, no Data
                continue
            store[p["name_value"]] = (packet, now, p.get("freshness", 0))
            faces = set().union(*(pit.pop(k)[0] for k in waiting))
            for f in faces:
                sock.sendto(packet, f)
            print(f"  Data {p['name']} from {who}: sent to {len(faces)} waiting, and cached")
# --8<-- [end:router]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("get")
    g.add_argument("name")
    g.add_argument("--via", default=TESTBED)
    g.add_argument("--fresh", action="store_true")
    g.add_argument("--prefix", action="store_true")
    r = sub.add_parser("router")
    r.add_argument("--upstream", default=TESTBED)
    a = ap.parse_args()
    if a.cmd == "get":
        get(a.name, a.via, a.fresh, a.prefix)
    else:
        router(a.upstream)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
