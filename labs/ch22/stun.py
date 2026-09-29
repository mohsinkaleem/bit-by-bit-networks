#!/usr/bin/env python3
"""Chapter 22 lab: ask servers on the internet what your address looks like from outside (STUN).

    python3 stun.py                  your public address and port, as three different servers see them
    python3 stun.py --port 50505     ...from a port of your choosing: does your router keep it?

STUN is how video calls and games find out what address to give the other side. It's one tiny
UDP question: "what address did this come from?"
"""
import argparse
import os
import socket
import struct

SERVERS = [("stun.l.google.com", 19302), ("stun1.l.google.com", 19302), ("stun.cloudflare.com", 3478)]
MAGIC = 0x2112A442


# --8<-- [start:ask]
def ask(sock, server, timeout=2.0):
    """Send a STUN "binding request", and return the (address, port) the server saw us come from."""
    txid = os.urandom(12)
    sock.sendto(struct.pack("!HHI", 0x0001, 0, MAGIC) + txid, server)
    sock.settimeout(timeout)
    while True:
        data, _ = sock.recvfrom(2048)
        kind, length, magic = struct.unpack_from("!HHI", data)
        if kind != 0x0101 or data[8:20] != txid:
            continue                                     # not the answer to our question
        at = 20
        while at < 20 + length:
            attr, size = struct.unpack_from("!HH", data, at)
            value = data[at + 4:at + 4 + size]
            if attr == 0x0020:                           # XOR-MAPPED-ADDRESS
                port = struct.unpack("!H", value[2:4])[0] ^ (MAGIC >> 16)
                addr = bytes(a ^ b for a, b in zip(value[4:8], struct.pack("!I", MAGIC)))
                return socket.inet_ntoa(addr), port
            at += 4 + size + (-size % 4)                 # attributes are padded to 4 bytes
        return None
# --8<-- [end:ask]


def private(address):
    a, b = map(int, address.split(".")[:2])
    return a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)


def shared(address):
    a, b = map(int, address.split(".")[:2])
    return a == 100 and 64 <= b <= 127


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=0, help="our own port (0 = any)")
    args = p.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.port))
    sock.connect(("8.8.8.8", 53))                        # only to learn which local address we'd use
    inside = sock.getsockname()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((inside[0], args.port))
    inside = sock.getsockname()
    print(f"inside:  {inside[0]}:{inside[1]}" + ("   (a private address: there's a NAT on the way out)" if private(inside[0]) else ""))
    seen = []
    for host, port in SERVERS:
        try:
            server = (socket.gethostbyname(host), port)
            outside = ask(sock, server)
        except (OSError, socket.timeout) as e:
            print(f"  {host}: no answer ({e})")
            continue
        seen.append(outside)
        print(f"  {host:<22} saw us as {outside[0]}:{outside[1]}")
    if not seen:
        raise SystemExit("No STUN server answered. Is UDP blocked on this network?")
    addresses, ports = {a for a, _ in seen}, {p for _, p in seen}
    print(f"outside: {seen[0][0]}" + ("   (a “shared” address: your provider has a NAT too, Chapter 22)" if shared(seen[0][0]) else ""))
    if len(ports) == 1:
        kept = "and even kept your port number" if seen[0][1] == inside[1] else "but changed the port number"
        print(f"Every server saw the same address and port. Your NAT gives one mapping per inside port, {kept}.")
        print("That's the friendly kind: games and video calls can connect straight through it.")
    else:
        print("Each server saw a different port: your NAT makes a new mapping for every destination.")
        print("That's the unfriendly (“symmetric”) kind: video calls may need to relay through a server.")


if __name__ == "__main__":
    main()
