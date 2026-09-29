#!/usr/bin/env python3
"""Chapter 15 lab: build sample.pcap, a small packet capture of one web page being fetched.

    python3 make_sample.py        writes sample.pcap next to this file

The capture follows one visit to http://grandpa-otto.example/ from a laptop: a "who has?" for the
gateway, a name lookup, a TCP handshake, one HTTP request and response, and goodbye. Every byte is
built by hand below, with real header layouts and real checksums, so tcpdump and Wireshark can read it.
"""
import struct
import time
from pathlib import Path

ALICE_MAC, ROUTER_MAC, BROADCAST = bytes.fromhex("e25fb13c770a"), bytes.fromhex("14c35e400b32"), b"\xff" * 6
ALICE, ROUTER, OTTO = (192, 168, 1, 3), (192, 168, 1, 1), (203, 0, 113, 42)
NAME = "grandpa-otto.example"


def ip(addr):
    return bytes(addr)


def checksum(data):
    """The Internet checksum from Chapter 10."""
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total > 0xFFFF:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def ethernet(dst, src, ethertype, payload):
    return dst + src + struct.pack("!H", ethertype) + payload       # the CRC isn't captured: the card checks and strips it


def ipv4(src, dst, proto, payload, ttl=64, ident=0):
    header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), ident, 0x4000, ttl, proto, 0, ip(src), ip(dst))
    header = header[:10] + struct.pack("!H", checksum(header)) + header[12:]
    return header + payload


def udp(src, dst, sport, dport, data):
    length = 8 + len(data)
    pseudo = ip(src) + ip(dst) + struct.pack("!BBH", 0, 17, length)
    seg = struct.pack("!HHHH", sport, dport, length, 0) + data
    return seg[:6] + struct.pack("!H", checksum(pseudo + seg)) + seg[8:]


def tcp(src, dst, sport, dport, seq, ack, flags, data=b"", window=65535):
    bits = {"F": 1, "S": 2, "R": 4, "P": 8, "A": 16}
    f = sum(bits[c] for c in flags)
    seg = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, 5 << 4, f, window, 0, 0) + data
    pseudo = ip(src) + ip(dst) + struct.pack("!BBH", 0, 6, len(seg))
    return seg[:16] + struct.pack("!H", checksum(pseudo + seg)) + seg[18:]


def arp(op, sha, spa, tha, tpa):
    return struct.pack("!HHBBH6s4s6s4s", 1, 0x0800, 6, 4, op, sha, ip(spa), tha, ip(tpa))


def dns_name(name):
    return b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0"


def dns_query(qid):
    return struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0) + dns_name(NAME) + struct.pack("!HH", 1, 1)


def dns_answer(qid):
    question = dns_name(NAME) + struct.pack("!HH", 1, 1)
    answer = struct.pack("!HHHIH4s", 0xC00C, 1, 1, 3600, 4, ip(OTTO))    # 0xC00C: "the name at byte 12"
    return struct.pack("!HHHHHH", qid, 0x8180, 1, 1, 0, 0) + question + answer


def build():
    request = (f"GET / HTTP/1.1\r\nHost: {NAME}\r\nUser-Agent: curl/8.7.1\r\nAccept: */*\r\n\r\n").encode()
    page = b"<!doctype html><title>Grandpa Otto</title><h1>Hello from the seaside!</h1>\n"
    response = (b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: " + str(len(page)).encode() + b"\r\n\r\n" + page)
    a_seq, o_seq, sport = 1000, 5000, 52000
    out = [
        ethernet(BROADCAST, ALICE_MAC, 0x0806, arp(1, ALICE_MAC, ALICE, b"\0" * 6, ROUTER)),
        ethernet(ALICE_MAC, ROUTER_MAC, 0x0806, arp(2, ROUTER_MAC, ROUTER, ALICE_MAC, ALICE)),
        ethernet(ROUTER_MAC, ALICE_MAC, 0x0800, ipv4(ALICE, ROUTER, 17, udp(ALICE, ROUTER, 53123, 53, dns_query(0x1d2e)), ident=1)),
        ethernet(ALICE_MAC, ROUTER_MAC, 0x0800, ipv4(ROUTER, ALICE, 17, udp(ROUTER, ALICE, 53, 53123, dns_answer(0x1d2e)), ident=77)),
        ethernet(ROUTER_MAC, ALICE_MAC, 0x0800, ipv4(ALICE, OTTO, 6, tcp(ALICE, OTTO, sport, 80, a_seq, 0, "S"), ident=2)),
        ethernet(ALICE_MAC, ROUTER_MAC, 0x0800, ipv4(OTTO, ALICE, 6, tcp(OTTO, ALICE, 80, sport, o_seq, a_seq + 1, "SA"), ttl=52)),
        ethernet(ROUTER_MAC, ALICE_MAC, 0x0800, ipv4(ALICE, OTTO, 6, tcp(ALICE, OTTO, sport, 80, a_seq + 1, o_seq + 1, "A"), ident=3)),
        ethernet(ROUTER_MAC, ALICE_MAC, 0x0800, ipv4(ALICE, OTTO, 6, tcp(ALICE, OTTO, sport, 80, a_seq + 1, o_seq + 1, "PA", request), ident=4)),
        ethernet(ALICE_MAC, ROUTER_MAC, 0x0800, ipv4(OTTO, ALICE, 6, tcp(OTTO, ALICE, 80, sport, o_seq + 1, a_seq + 1 + len(request), "PA", response), ttl=52)),
        ethernet(ROUTER_MAC, ALICE_MAC, 0x0800, ipv4(ALICE, OTTO, 6, tcp(ALICE, OTTO, sport, 80, a_seq + 1 + len(request), o_seq + 1 + len(response), "A"), ident=5)),
        ethernet(ROUTER_MAC, ALICE_MAC, 0x0800, ipv4(ALICE, OTTO, 6, tcp(ALICE, OTTO, sport, 80, a_seq + 1 + len(request), o_seq + 1 + len(response), "FA"), ident=6)),
        ethernet(ALICE_MAC, ROUTER_MAC, 0x0800, ipv4(OTTO, ALICE, 6, tcp(OTTO, ALICE, 80, sport, o_seq + 1 + len(response), a_seq + 2 + len(request), "FA"), ttl=52)),
        ethernet(ROUTER_MAC, ALICE_MAC, 0x0800, ipv4(ALICE, OTTO, 6, tcp(ALICE, OTTO, sport, 80, a_seq + 2 + len(request), o_seq + 2 + len(response), "A"), ident=7)),
    ]
    gaps = [0, 0.0012, 0.0008, 0.0151, 0.0006, 0.0243, 0.0003, 0.0002, 0.0261, 0.0004, 0.0009, 0.0238, 0.0002]
    return out, gaps


def write_pcap(path, frames, gaps):
    """The classic pcap format: a 24-byte file header, then a 16-byte header before each captured frame."""
    t = 1790000000.0
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))   # link type 1 = Ethernet
        for frame, gap in zip(frames, gaps):
            t += gap
            f.write(struct.pack("<IIII", int(t), int(round((t % 1) * 1e6)), len(frame), len(frame)) + frame)


if __name__ == "__main__":
    frames, gaps = build()
    path = Path(__file__).with_name("sample.pcap")
    write_pcap(path, frames, gaps)
    print(f"wrote {path.name}: {len(frames)} frames, {path.stat().st_size} bytes")
