#!/usr/bin/env python3
"""Chapter 20 lab: build IP headers by hand, chop packets into fragments, and glue real ones back together.

    python3 fragment.py header                          build one IPv4 header, field by field, with its checksum
    python3 fragment.py split 4000 --mtu 1500           how a 4,000-byte packet is cut up for a 1,500-byte link
    python3 fragment.py split 3028 --mtu 1500 --then 1492
                                                        ...and cut up again by a smaller link, like the real one
    python3 fragment.py reassemble frag.pcap            put the Pi's real fragments from the chapter back together
    python3 fragment.py reassemble frag.pcap --shuffle  ...even when they arrive in a random order
"""
import argparse
import random
import struct

PROTOCOLS = {1: "ICMP", 6: "TCP", 17: "UDP"}


def checksum(data):
    """The Internet checksum from Chapter 10."""
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total > 0xFFFF:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def addr(text):
    return bytes(int(x) for x in text.split("."))


# --8<-- [start:header]
def ip_header(src, dst, payload_len, ident, proto=1, ttl=64, dont_fragment=False, more=False, offset=0):
    """A 20-byte IPv4 header. `offset` is in bytes, and must be a multiple of 8."""
    flags = (0x4000 if dont_fragment else 0) | (0x2000 if more else 0) | offset // 8
    header = struct.pack("!BBHHHBBH4s4s",
                         0x45,                    # version 4, header length 5 × 4 = 20 bytes
                         0,                       # priority (DSCP) and congestion bits (ECN)
                         20 + payload_len,        # total length
                         ident,                   # the same for every fragment of one packet
                         flags,                   # 3 flag bits, then the offset in 8-byte units
                         ttl, proto,
                         0,                       # the checksum: zero while we calculate it
                         addr(src), addr(dst))
    return header[:10] + struct.pack("!H", checksum(header)) + header[12:]
# --8<-- [end:header]


# --8<-- [start:split]
def fragment(payload, mtu, start=0, last=True):
    """Cut a payload into pieces that fit an MTU. Every piece except the last must hold a multiple
    of 8 bytes, because the offset field counts in eighths. Returns (offset, more, data) triples."""
    room = (mtu - 20) // 8 * 8                      # data per fragment: fits the link, and divides by 8
    pieces = []
    for at in range(0, len(payload), room):
        data = payload[at:at + room]
        more = at + room < len(payload) or not last
        pieces.append((start + at, more, data))
    return pieces
# --8<-- [end:split]


def show_header():
    h = ip_header("192.168.1.4", "1.1.1.1", 64, ident=18883, dont_fragment=True)
    names = [("version + header length", 0, 1), ("priority", 1, 2), ("total length", 2, 4), ("identification", 4, 6),
             ("flags + fragment offset", 6, 8), ("hops left (TTL)", 8, 9), ("protocol", 9, 10), ("checksum", 10, 12),
             ("source", 12, 16), ("destination", 16, 20)]
    print("An IPv4 header for a ping from the Pi to 1.1.1.1, with 64 bytes of ICMP inside:\n")
    for name, a, b in names:
        value = int.from_bytes(h[a:b], "big")
        extra = {"total length": f"= {value} bytes", "identification": f"= {value}", "hops left (TTL)": f"= {value}",
                 "protocol": f"= {value}, {PROTOCOLS.get(value)}", "flags + fragment offset": "“don’t fragment”, offset 0",
                 "source": ".".join(map(str, h[a:b])), "destination": ".".join(map(str, h[a:b])),
                 "version + header length": "version 4, 5 × 4 = 20 bytes"}.get(name, "")
        print(f"  {name:<26} {h[a:b].hex(' '):<12} {extra}")
    print(f"\nChecking it: the checksum of the whole header, checksum included, is {checksum(h)}. Zero means it's intact.")


def show_split(size, mtu, then):
    payload = bytes(size - 20)
    print(f"A {size:,}-byte packet ({size - 20:,} bytes of data) over a {mtu:,}-byte link:")
    for offset, more, data in fragment(payload, mtu):
        print(f"  offset {offset:>5} ({offset // 8:>3} × 8)  {len(data):>5} bytes of data  {'more to come' if more else 'the last one'}"
              f"   → {20 + len(data):,}-byte packet")
        if then and 20 + len(data) > then:
            for o2, m2, d2 in fragment(data, then, start=offset, last=not more):
                print(f"      the next link cuts it again: offset {o2:>5}, {len(d2):>5} bytes, {'more' if m2 else 'last'}")


# --8<-- [start:reassemble]
def reassemble(fragments):
    """fragments: (offset, more, data) in any order. Returns the whole payload, or None if a piece is missing."""
    pieces = sorted(fragments)
    if not pieces or pieces[0][0] != 0 or pieces[-1][1]:
        return None                                  # no start yet, or no piece that says "the last one"
    whole, expected = b"", 0
    for offset, more, data in pieces:
        if offset > expected:
            return None                              # a hole: something hasn't arrived
        whole = whole[:offset] + data                # (pieces can overlap: a later one wins)
        expected = offset + len(data)
    return whole
# --8<-- [end:reassemble]


def read_frames(path):
    with open(path, "rb") as f:
        f.read(24)
        while True:
            rec = f.read(16)
            if len(rec) < 16:
                return
            yield f.read(struct.unpack("<IIII", rec)[2])


def show_reassembly(path, shuffle):
    groups = {}
    for frame in read_frames(path):
        if frame[12:14] != b"\x08\x00":
            continue
        ip = frame[14:]
        total, ident, flags, proto = struct.unpack("!H H H x B", ip[2:10])
        key = (ip[12:16], ip[16:20], ident, proto)
        groups.setdefault(key, []).append(((flags & 0x1FFF) * 8, bool(flags & 0x2000), ip[20:total]))
    for (src, dst, ident, proto), pieces in groups.items():
        if shuffle:
            random.shuffle(pieces)
        print(f"{'.'.join(map(str, src))} → {'.'.join(map(str, dst))}, identification {ident}, {len(pieces)} pieces arrived as:")
        for offset, more, data in pieces:
            print(f"    offset {offset:>5}, {len(data):>5} bytes, {'more' if more else 'last'}")
        whole = reassemble(pieces)
        if whole is None:
            print("  → still waiting for a missing piece")
            continue
        kind = {0: "echo reply", 8: "echo request"}.get(whole[0], "?") if proto == 1 else PROTOCOLS.get(proto)
        ok = "✓" if checksum(whole) == 0 else "✗"
        print(f"  → reassembled {len(whole):,} bytes: an ICMP {kind}, checksum over the whole thing {ok}\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("header")
    sp = sub.add_parser("split")
    sp.add_argument("size", type=int)
    sp.add_argument("--mtu", type=int, default=1500)
    sp.add_argument("--then", type=int, help="a smaller link further on")
    r = sub.add_parser("reassemble")
    r.add_argument("file")
    r.add_argument("--shuffle", action="store_true")
    args = p.parse_args()
    if args.cmd == "header":
        show_header()
    elif args.cmd == "split":
        show_split(args.size, args.mtu, args.then)
    elif args.cmd == "reassemble":
        show_reassembly(args.file, args.shuffle)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
