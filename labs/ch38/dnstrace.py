#!/usr/bin/env python3
"""Chapter 38 lab: where does my DNS question die? A traceroute made of real DNS questions (Linux only).

    python3 dnstrace.py example.org 8.8.8.8
    python3 dnstrace.py example.com 8.8.8.8

Ordinary traceroute (Chapter 21) sends throwaway packets. This one sends a real DNS question, with the
IP time-to-live set to 1, 2, 3…, so each router on the way that lets it expire tells us so. If a box
in the middle drops the question, the replies stop at that box. If the question gets through, but
the answer is lost on the way back, they carry on all the way. Needs no sudo: Linux reports the
ICMP errors on the same socket (IP_RECVERR, as in Chapter 21's pytrace.py).
"""
import random
import select
import socket
import struct
import sys
import time

IP_RECVERR, MSG_ERRQUEUE = 11, 0x2000


def query(name):
    q = struct.pack("!HHHHHH", random.randrange(65536), 0x0100, 1, 0, 0, 0)
    q += b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0"
    return q + struct.pack("!HH", 1, 1)                          # type A, class IN


# --8<-- [start:probe]
def probe(name, server, ttl, timeout=1.5):
    """Send one DNS question with this TTL. Returns ('answer', ms) or ('expired', router, ms) or ('silence',)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
    s.setsockopt(socket.IPPROTO_IP, IP_RECVERR, 1)              # deliver ICMP errors to this socket
    s.setblocking(False)
    t0 = time.monotonic()
    s.sendto(query(name), (server, 53))
    deadline = t0 + timeout
    while (left := deadline - time.monotonic()) > 0:
        select.select([s], [], [s], left)
        try:                                                      # an ICMP error? who sent it?
            _, anc, _, _ = s.recvmsg(512, 512, MSG_ERRQUEUE)
            for level, kind, data in anc:
                if level == socket.IPPROTO_IP and kind == IP_RECVERR:
                    router = socket.inet_ntoa(data[20:24])        # struct sock_extended_err, then the sender's address
                    return ("expired", router, (time.monotonic() - t0) * 1000)
        except BlockingIOError:
            pass
        try:
            s.recv(512)                                           # a real answer: the question got there and back
            return ("answer", (time.monotonic() - t0) * 1000)
        except (BlockingIOError, OSError):
            pass
    return ("silence",)
# --8<-- [end:probe]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "example.org"
    server = sys.argv[2] if len(sys.argv) > 2 else "8.8.8.8"
    print(f"a DNS question for {name}, to {server}, with a growing time-to-live:")
    for ttl in range(1, 21):
        r = probe(name, server, ttl)
        if r[0] == "answer":
            print(f"  ttl {ttl:>2}: an ANSWER from {server}, {r[1]:.1f} ms. The question got all the way there, and back.")
            return
        if r[0] == "expired":
            print(f"  ttl {ttl:>2}: expired at {r[1]:<16} {r[2]:6.1f} ms", flush=True)
        else:
            print(f"  ttl {ttl:>2}: silence", flush=True)
    print("no answer at any distance")


if __name__ == "__main__":
    main()
