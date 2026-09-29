#!/usr/bin/env python3
"""Chapter 21 lab: ping, written from scratch. No sudo needed on macOS or Linux.

    python3 pyping.py 1.1.1.1                 four pings, like the real thing
    python3 pyping.py 1.1.1.1 --ttl 1         a hop limit of 1: who complains, and what do they say?
    python3 pyping.py 192.168.1.1 -v          every byte of each request and reply
    python3 pyping.py 1.1.1.1 --size 3000     a big one (the reply comes back in fragments, Chapter 20)

It uses an "ICMP datagram socket", which lets ordinary programs send echo requests and get the
replies. (The classic ping needed administrator rights for a raw socket.)
"""
import argparse
import os
import select
import socket
import struct
import sys
import time

IP_RECVERR, MSG_ERRQUEUE, IP_RECVTTL = 11, 0x2000, 12          # Linux constants Python doesn't always name
LINUX = sys.platform.startswith("linux")
MESSAGES = {(0, 0): "echo reply", (3, 0): "network unreachable", (3, 1): "host unreachable",
            (3, 3): "port unreachable", (3, 4): "too big, and you said don't fragment",
            (3, 13): "forbidden by a firewall", (8, 0): "echo request", (11, 0): "time exceeded: hop limit reached zero",
            (11, 1): "time exceeded: fragments never all arrived"}


def checksum(data):
    """The Internet checksum from Chapter 10."""
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total > 0xFFFF:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


# --8<-- [start:echo]
def echo_request(ident, seq, size=56):
    """An ICMP echo request: type 8, code 0, checksum, identifier, sequence number, then any data.
    Like the real ping, the data starts with the time it was sent, so the reply tells us the round trip."""
    data = struct.pack("!d", time.time())
    data += bytes(i % 256 for i in range(size - len(data)))
    header = struct.pack("!BBHHH", 8, 0, 0, ident, seq)
    return struct.pack("!BBHHH", 8, 0, checksum(header + data), ident, seq) + data
# --8<-- [end:echo]


class Pinger:
    """Sends echo requests and waits for whatever ICMP comes back: a reply, or a complaint from a router."""

    def __init__(self, ttl=64):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        if LINUX:                                         # Linux hands errors back on a separate queue
            self.sock.setsockopt(socket.IPPROTO_IP, IP_RECVERR, 1)
            self.sock.setsockopt(socket.IPPROTO_IP, IP_RECVTTL, 1)
        self.ident = os.getpid() & 0xFFFF

    def set_ttl(self, ttl):
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)

    def send(self, host, seq, size=56):
        packet = echo_request(self.ident, seq, size)
        self.sock.sendto(packet, (host, 0))
        return packet

    # --8<-- [start:receive]
    def receive(self, timeout):
        """Returns (kind, from_address, ttl, icmp_bytes, quoted_seq) or None after `timeout` seconds."""
        ready, _, _ = select.select([self.sock], [], [], timeout)
        if not ready:
            return None
        if LINUX:
            try:
                data, anc, _, (sender, _) = self.sock.recvmsg(65535, 64)
            except OSError:                               # a router's complaint waits on the error queue
                data, anc, _, _ = self.sock.recvmsg(65535, 512, MSG_ERRQUEUE)
                for level, kind, blob in anc:
                    if level == socket.IPPROTO_IP and kind == IP_RECVERR:
                        _, origin, icmp_type, icmp_code = struct.unpack_from("=IBBB", blob)
                        offender = socket.inet_ntoa(blob[20:24])
                        seq = struct.unpack_from("!H", data, 6)[0]     # our own request, handed back
                        return MESSAGES.get((icmp_type, icmp_code), f"type {icmp_type}"), offender, None, data, seq
                return None
            ttl = next((struct.unpack("=i", blob)[0] for level, kind, blob in anc if kind == socket.IP_TTL), None)
            seq = struct.unpack_from("!H", data, 6)[0]
            return MESSAGES.get((data[0], data[1]), f"type {data[0]}"), sender, ttl, data, seq
        data, (sender, _) = self.sock.recvfrom(65535)     # macOS hands us the whole IP packet
        hlen = (data[0] & 0x0F) * 4
        ttl, icmp = data[8], data[hlen:]
        if icmp[0] in (3, 11):                            # an error quotes our packet: IP header, then our ICMP header
            quoted = icmp[8:]
            seq = struct.unpack_from("!H", quoted, (quoted[0] & 0x0F) * 4 + 6)[0]
        else:
            seq = struct.unpack_from("!H", icmp, 6)[0]
        return MESSAGES.get((icmp[0], icmp[1]), f"type {icmp[0]}"), sender, ttl, icmp, seq
    # --8<-- [end:receive]


def hexdump(label, data):
    print(f"      {label}:")
    for i in range(0, min(len(data), 64), 16):
        print(f"        {data[i:i + 16].hex(' ')}")
    if len(data) > 64:
        print(f"        … {len(data) - 64} more bytes")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("host")
    p.add_argument("-c", "--count", type=int, default=4)
    p.add_argument("--ttl", type=int, default=64)
    p.add_argument("--size", type=int, default=56)
    p.add_argument("-v", action="store_true")
    args = p.parse_args()
    address = socket.gethostbyname(args.host)
    pinger = Pinger(args.ttl)
    print(f"PING {args.host} ({address}): {args.size} data bytes, hop limit {args.ttl}")
    times = []
    for seq in range(1, args.count + 1):
        sent_at = time.time()
        request = pinger.send(address, seq, args.size)
        deadline = sent_at + 2
        while True:
            got = pinger.receive(max(0, deadline - time.time()))
            if got is None:
                print(f"no answer for icmp_seq={seq}")
                break
            kind, sender, ttl, icmp, qseq = got
            if qseq != seq:
                continue                                  # someone else's, or a late one
            ms = (time.time() - sent_at) * 1000
            if kind == "echo reply":
                times.append(ms)
                print(f"{len(icmp)} bytes from {sender}: icmp_seq={seq}" + (f" ttl={ttl}" if ttl else "") + f" time={ms:.1f} ms")
            else:
                print(f"from {sender}: icmp_seq={seq} {kind}")
            if args.v:
                hexdump("sent (ICMP)", request)
                hexdump("received (ICMP)", icmp)
            break
        if seq < args.count:
            time.sleep(max(0, 1 - (time.time() - sent_at)))
    lost = args.count - len(times)
    print(f"--- {args.count} sent, {len(times)} answered, {lost / args.count:.0%} lost" +
          (f", round trip min/avg/max = {min(times):.1f}/{sum(times) / len(times):.1f}/{max(times):.1f} ms" if times else ""))


if __name__ == "__main__":
    main()
