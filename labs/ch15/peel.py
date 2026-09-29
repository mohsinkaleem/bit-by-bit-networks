#!/usr/bin/env python3
"""Chapter 15 lab: peel real packets apart, one layer at a time, in this book's words.

    python3 peel.py sample.pcap              one line per packet
    python3 peel.py sample.pcap -v           every layer of every packet, with chapter numbers
    python3 peel.py sample.pcap -v -n 8      just packet 8
    python3 peel.py sample.pcap --hex -n 8   packet 8's bytes, layer by layer

Reads classic .pcap files, like the ones tcpdump -w writes: from Ethernet and Wi-Fi interfaces,
and from the loopback interface (lo0 on a Mac, lo on Linux).
"""
import argparse
import struct
import sys

TCP_FLAGS = [(2, "SYN"), (16, "ACK"), (8, "PSH"), (1, "FIN"), (4, "RST")]


def checksum(data):
    """The Internet checksum from Chapter 10. Run over data that includes a correct checksum, it gives 0."""
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total > 0xFFFF:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def mac(b):
    return ":".join(f"{x:02x}" for x in b)


def ip4(b):
    return ".".join(map(str, b))


# --8<-- [start:pcap]
def read_pcap(path):
    with open(path, "rb") as f:
        head = f.read(24)
        magic = struct.unpack("<I", head[:4])[0]
        if magic == 0x0A0D0D0A:
            raise SystemExit("This is a pcapng file. Convert it first: tcpdump -r file.pcapng -w file.pcap")
        endian = "<" if magic in (0xA1B2C3D4, 0xA1B23C4D) else ">"
        linktype = struct.unpack(endian + "I", head[20:24])[0]
        while True:
            rec = f.read(16)
            if len(rec) < 16:
                return
            secs, frac, captured, length = struct.unpack(endian + "IIII", rec)
            yield secs + frac / 1e6, linktype, f.read(captured)
# --8<-- [end:pcap]


def dns_name(msg, i):
    parts = []
    while msg[i]:
        if msg[i] & 0xC0 == 0xC0:                   # a pointer back to a name earlier in the message
            parts.append(dns_name(msg, struct.unpack("!H", msg[i:i + 2])[0] & 0x3FFF)[0])
            return ".".join(parts), i + 2
        parts.append(msg[i + 1:i + 1 + msg[i]].decode())
        i += 1 + msg[i]
    return ".".join(parts), i + 1


# --8<-- [start:peel]
def peel(linktype, data):
    """Returns a list of layers, outermost first: (name, chapter, description, header length)."""
    layers = []
    if linktype == 1:                                          # Ethernet (and Wi-Fi, as your computer shows it)
        dst, src, kind = data[:6], data[6:12], struct.unpack("!H", data[12:14])[0]
        what = {0x0800: "an IP packet", 0x0806: "an ARP message", 0x86DD: "an IPv6 packet"}.get(kind, hex(kind))
        to = "everyone (broadcast)" if dst == b"\xff" * 6 else mac(dst)
        layers.append(("frame", 8, f"to {to}, from {mac(src)}; inside: {what}", 14))
        data = data[14:]
    elif linktype == 0:                                        # macOS loopback: 4 bytes saying what's inside
        kind = 0x0800 if struct.unpack("<I", data[:4])[0] == 2 else 0x86DD
        layers.append(("loopback", 4, "never left this computer", 4))
        data = data[4:]
    else:
        return layers + [("?", 0, f"link type {linktype} isn't supported", 0)]

    if kind == 0x0806:
        op, sha, spa, tha, tpa = struct.unpack("!6xH6s4s6s4s", data[:28])
        text = f"who has {ip4(tpa)}? tell {ip4(spa)}" if op == 1 else f"{ip4(spa)} is card {mac(sha)}"
        return layers + [("who has? (ARP)", 11, text, 28)]
    if kind != 0x0800:
        return layers + [("IPv6", 25, "the newer kind of address (Part II)", 40)]

    hlen = (data[0] & 0x0F) * 4
    total, ttl, proto = struct.unpack("!H", data[2:4])[0], data[8], data[9]
    src, dst = ip4(data[12:16]), ip4(data[16:20])
    ok = "✓" if checksum(data[:hlen]) == 0 else "✗ BAD"
    layers.append(("packet (IP)", 11, f"to {dst}, from {src}, hops left {ttl}, header check {ok}", hlen))
    body = data[hlen:total]
    pseudo = data[12:20] + struct.pack("!BBH", 0, proto, len(body))

    if proto == 17:
        sport, dport, length = struct.unpack("!HHH", body[:6])
        ok = "✓" if checksum(pseudo + body) == 0 else "✗ BAD"
        layers.append(("datagram (UDP)", 12, f"from port {sport} to port {dport}, {length - 8} bytes of data, check {ok}", 8))
        payload = body[8:]
        if 53 in (sport, dport):
            qid, flags, qd, an = struct.unpack("!HHHH", payload[:8])
            name, i = dns_name(payload, 12)
            if flags & 0x8000:
                i += 4
                answers = []
                for _ in range(an):
                    _, i = dns_name(payload, i)
                    rtype, _, ttl2, rlen = struct.unpack("!HHIH", payload[i:i + 10])
                    if rtype == 1:
                        answers.append(f"{ip4(payload[i + 10:i + 14])} (good for {ttl2} s)")
                    i += 10 + rlen
                layers.append(("name answer (DNS)", 14, f"#{qid}: {name} is {', '.join(answers) or 'unknown'}", len(payload)))
            else:
                layers.append(("name question (DNS)", 14, f"#{qid}: what's the address of {name}?", len(payload)))
        return layers
    if proto == 6:
        sport, dport, seq, ack, off, fl, win = struct.unpack("!HHIIBBH", body[:16])
        thlen = (off >> 4) * 4
        ok = "✓" if checksum(pseudo + body) == 0 else "✗ BAD"
        flags = "+".join(name for bit, name in TCP_FLAGS if fl & bit) or "none"
        layers.append(("connection (TCP)", 13, f"from port {sport} to port {dport}, {flags}, byte #{seq}, "
                                                f"acknowledging #{ack}, room for {win}, check {ok}", thlen))
        payload = body[thlen:]
        if payload:
            first = payload.split(b"\r\n", 1)[0].decode(errors="replace")
            layers.append(("data (HTTP)" if b"HTTP/" in payload[:200] else "data", 6, f"{len(payload)} bytes: {first!r}", len(payload)))
        return layers
    return layers + [("?", 0, f"protocol {proto}", 0)]
# --8<-- [end:peel]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("-v", action="store_true", help="show every layer")
    p.add_argument("-n", type=int, help="only this packet number")
    p.add_argument("--hex", action="store_true", help="show the bytes, split into layers")
    args = p.parse_args()
    start = None
    for number, (when, linktype, data) in enumerate(read_pcap(args.file), start=1):
        start = start or when
        if args.n and number != args.n:
            continue
        layers = peel(linktype, data)
        stamp = f"{(when - start) * 1000:7.1f} ms"
        if not (args.v or args.hex):
            name, chapter, text, _ = layers[-1]
            damaged = any("✗" in layer[2] for layer in layers[:-1])
            print(f"{number:>3} {stamp}  {len(data):>4} bytes  {name}: {text}" + ("   ✗ A CHECK FAILED" if damaged else ""))
            continue
        print(f"packet {number}, at {stamp}, {len(data)} bytes")
        offset = 0
        for depth, (name, chapter, text, size) in enumerate(layers):
            print(f"{'  ' * depth}└ {name} (Ch. {chapter}): {text}")
            if args.hex:
                chunk = data[offset:offset + size]
                for i in range(0, len(chunk), 16):
                    print(f"{'  ' * depth}    {chunk[i:i + 16].hex(' ')}")
                offset += size
        print()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(__doc__)
    else:
        main()
