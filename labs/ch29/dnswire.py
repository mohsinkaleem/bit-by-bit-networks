#!/usr/bin/env python3
"""Chapter 29 lab: DNS messages, byte by byte. Used by dig.py and resolver.py.

    python3 dnswire.py        build a query and show its bytes, field by field
"""
import ipaddress
import random
import struct

TYPES = {1: "A", 2: "NS", 5: "CNAME", 6: "SOA", 12: "PTR", 15: "MX", 16: "TXT", 28: "AAAA", 33: "SRV",
         41: "OPT", 43: "DS", 46: "RRSIG", 48: "DNSKEY", 65: "HTTPS", 257: "CAA"}
CODES = {v: k for k, v in TYPES.items()}
RCODES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 4: "NOTIMP", 5: "REFUSED"}
FLAGS = [(15, "qr"), (10, "aa"), (9, "tc"), (8, "rd"), (7, "ra"), (5, "ad"), (4, "cd")]


# --8<-- [start:build]
def encode_name(name):
    """'info.cern.ch' -> 4 i n f o 4 c e r n 2 c h 0: each label with its length in front."""
    out = b""
    for label in name.rstrip(".").split("."):
        if label:
            out += bytes([len(label)]) + label.encode()
    return out + b"\0"


def build_query(name, qtype="A", recursion=True, dnssec=False, ident=None):
    ident = random.randrange(65536) if ident is None else ident       # a random ID: part of the defence
    flags = 0x0100 if recursion else 0                                 # RD: "please do the lookup for me"
    header = struct.pack("!HHHHHH", ident, flags, 1, 0, 0, 1)         # 1 question, 1 additional (OPT)
    question = encode_name(name) + struct.pack("!HH", CODES[qtype], 1)  # class 1 = IN, the internet
    opt = b"\0" + struct.pack("!HHIH", 41, 1232, 0x8000 if dnssec else 0, 0)  # EDNS: "I can take 1232 bytes"
    return header + question + opt
# --8<-- [end:build]


# --8<-- [start:names]
def read_name(msg, at):
    """Read a name starting at msg[at]. Returns (name, where the name ended)."""
    labels, end, jumps = [], None, 0
    while True:
        n = msg[at]
        if n & 0xC0 == 0xC0:                         # two top bits set: a pointer to a name earlier on
            if end is None:
                end = at + 2
            at = ((n & 0x3F) << 8) | msg[at + 1]
            jumps += 1
            if jumps > 20:
                raise ValueError("pointer loop")     # a malicious message could point at itself
            continue
        if n == 0:
            return ".".join(labels) + ".", end if end is not None else at + 1
        labels.append(msg[at + 1:at + 1 + n].decode("ascii", "replace"))
        at += 1 + n
# --8<-- [end:names]


def parse_rdata(msg, rtype, at, length):
    data = msg[at:at + length]
    if rtype == 1:
        return str(ipaddress.IPv4Address(data))
    if rtype == 28:
        return str(ipaddress.IPv6Address(data))
    if rtype in (2, 5, 12):
        return read_name(msg, at)[0]
    if rtype == 15:
        return f"{struct.unpack('!H', data[:2])[0]} {read_name(msg, at + 2)[0]}"
    if rtype == 16:
        parts, i = [], 0
        while i < len(data):
            parts.append('"' + data[i + 1:i + 1 + data[i]].decode("utf-8", "replace") + '"')
            i += 1 + data[i]
        return " ".join(parts)
    if rtype == 6:
        mname, i = read_name(msg, at)
        rname, i = read_name(msg, i)
        serial, refresh, retry, expire, minimum = struct.unpack("!5I", msg[i:i + 20])
        return f"{mname} {rname} {serial} {refresh} {retry} {expire} {minimum}"
    if rtype == 33:
        prio, weight, port = struct.unpack("!HHH", data[:6])
        return f"{prio} {weight} {port} {read_name(msg, at + 6)[0]}"
    if rtype == 257:
        tag = data[2:2 + data[1]].decode()
        return f'{data[0]} {tag} "{data[2 + data[1]:].decode()}"'
    if rtype == 43:
        tag, alg, dtype = struct.unpack("!HBB", data[:4])
        return f"{tag} {alg} {dtype} {data[4:].hex().upper()}"
    if rtype == 65:
        return parse_https(data)
    return data.hex()


def parse_https(data):
    """HTTPS records (2023) tell a browser, before it connects, what the server supports."""
    prio = struct.unpack("!H", data[:2])[0]
    target, i = [], 2
    while data[i]:
        target.append(data[i + 1:i + 1 + data[i]].decode())
        i += 1 + data[i]
    i += 1
    out = [str(prio), ".".join(target) + "."]
    while i < len(data):
        key, n = struct.unpack("!HH", data[i:i + 4])
        v = data[i + 4:i + 4 + n]
        if key == 1:
            alpn, j = [], 0
            while j < len(v):
                alpn.append(v[j + 1:j + 1 + v[j]].decode())
                j += 1 + v[j]
            out.append("alpn=" + ",".join(alpn))
        elif key == 4:
            out.append("ipv4hint=" + ",".join(str(ipaddress.IPv4Address(v[k:k + 4])) for k in range(0, n, 4)))
        elif key == 6:
            out.append("ipv6hint=" + ",".join(str(ipaddress.IPv6Address(v[k:k + 16])) for k in range(0, n, 16)))
        elif key == 5 and v[2:4] == b"\xfe\x0d":      # Encrypted Client Hello settings (Chapter 32)
            j = 7 + 2                                  # list length, version, length, config id, KEM
            j += 2 + int.from_bytes(v[j:j + 2], "big")          # the public key
            j += 2 + int.from_bytes(v[j:j + 2], "big") + 1      # cipher suites, maximum name length
            public_name = v[j + 1:j + 1 + v[j]].decode()
            out.append(f"ech=({n} bytes: a public key for encrypting the ClientHello; outer name {public_name})")
        else:
            out.append(f"key{key}={v.hex()}")
        i += 4 + n
    return " ".join(out)


# --8<-- [start:parse]
def parse(msg):
    ident, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", msg[:12])
    out = {"id": ident, "flags": [name for bit, name in FLAGS if flags >> bit & 1],
           "rcode": RCODES.get(flags & 15, flags & 15), "question": [], "answer": [], "authority": [], "additional": []}
    at = 12
    for _ in range(qd):
        name, at = read_name(msg, at)
        qtype, qclass = struct.unpack("!HH", msg[at:at + 4])
        out["question"].append((name, TYPES.get(qtype, qtype)))
        at += 4
    for section, count in (("answer", an), ("authority", ns), ("additional", ar)):
        for _ in range(count):
            name, at = read_name(msg, at)
            rtype, rclass, ttl, length = struct.unpack("!HHIH", msg[at:at + 10])
            at += 10
            if rtype == 41:                              # the OPT pseudo-record: EDNS settings, not data
                out["edns"] = {"udp": rclass, "do": bool(ttl & 0x8000)}
            else:
                out[section].append((name, ttl, TYPES.get(rtype, rtype), parse_rdata(msg, rtype, at, length)))
            at += length
    return out
# --8<-- [end:parse]


def fields(msg):
    """[(start, end, field name, meaning)] for every part of a message: for dig.py --hex and the book's widget."""
    ident, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", msg[:12])
    names = ", ".join(n for b, n in FLAGS if flags >> b & 1) or "none"
    out = [(0, 2, "ID", f"{ident}: the answer must carry the same number"),
           (2, 4, "flags", f"{names}; rcode {RCODES.get(flags & 15, flags & 15)}"),
           (4, 6, "questions", str(qd)), (6, 8, "answers", str(an)), (8, 10, "authority", str(ns)), (10, 12, "additional", str(ar))]
    at = 12

    def name_fields(at, what):
        start = at
        while True:
            n = msg[at]
            if n & 0xC0 == 0xC0:
                target = ((n & 0x3F) << 8) | msg[at + 1]
                out.append((at, at + 2, f"{what}: pointer", f"the rest of the name is at byte {target}: “{read_name(msg, target)[0]}”"))
                return at + 2
            if n == 0:
                out.append((at, at + 1, f"{what}: end", "a zero length: the end of the name"))
                return at + 1
            out.append((at, at + 1 + n, f"{what}: label", f"length {n}, then “{msg[at + 1:at + 1 + n].decode()}”"))
            at += 1 + n
    for _ in range(qd):
        at = name_fields(at, "question name")
        qtype = struct.unpack("!H", msg[at:at + 2])[0]
        out.append((at, at + 2, "question type", f"{qtype} = {TYPES.get(qtype, qtype)}"))
        out.append((at + 2, at + 4, "question class", "1 = IN, the internet"))
        at += 4
    for section, count in (("answer", an), ("authority", ns), ("additional", ar)):
        for _ in range(count):
            at = name_fields(at, f"{section} name")
            rtype, rclass, ttl, length = struct.unpack("!HHIH", msg[at:at + 10])
            if rtype == 41:
                out.append((at, at + 2, "OPT", "41 = OPT: not a record, but EDNS settings"))
                out.append((at + 2, at + 4, "UDP size", f"{rclass}: the biggest UDP answer I can take"))
                out.append((at + 4, at + 8, "EDNS flags", "DNSSEC OK" if ttl & 0x8000 else "none"))
            else:
                out.append((at, at + 2, f"{section} type", f"{rtype} = {TYPES.get(rtype, rtype)}"))
                out.append((at + 2, at + 4, f"{section} class", "1 = IN"))
                out.append((at + 4, at + 8, f"{section} TTL", f"{ttl} seconds: how long it may be remembered"))
            out.append((at + 8, at + 10, "data length", f"{length} bytes"))
            if rtype in (2, 5, 12):                  # the data is itself a name, and may be compressed too
                name_fields(at + 10, f"{section} data")
            elif length:
                out.append((at + 10, at + 10 + length, f"{section} data", parse_rdata(msg, rtype, at + 10, length) if rtype != 41 else "(options)"))
            at += 10 + length
    return out


if __name__ == "__main__":
    q = build_query("info.cern.ch", "A", ident=0x1234)
    print(f"a query for info.cern.ch, type A: {len(q)} bytes")
    for start, end, name, meaning in fields(q):
        print(f"  {q[start:end].hex(' '):<42} {name:<16} {meaning}")
