#!/usr/bin/env python3
"""Chapter 26 lab: what UDP sockets do, and don't do, for you.

    python3 udp_lab.py refused        send to a port nobody's listening on: who finds out?
    python3 udp_lab.py flood          a fast sender, a slow reader, and a full buffer
    python3 udp_lab.py big            how big can one datagram be?
    python3 udp_lab.py chat Bob       a chat room for everyone on your network, using multicast
                                      (run it on two computers, or in two windows)

Everything except chat stays on 127.0.0.1, ports 7100 to 7199.
"""
import os
import re
import select
import socket
import struct
import subprocess
import sys
import threading
import time


# --8<-- [start:refused]
def refused():
    nobody = ("127.0.0.1", 7199)                  # make sure nothing is listening here
    loose = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    loose.settimeout(1)
    loose.sendto(b"hello?", nobody)
    try:
        loose.recvfrom(100)
    except socket.timeout:
        print("unconnected socket: sent fine, then silence. It never finds out nobody was there.")

    tied = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tied.settimeout(1)
    tied.connect(nobody)                          # no packets sent: it just remembers the other end
    tied.send(b"hello?")
    try:
        tied.recv(100)
    except ConnectionRefusedError as e:
        print(f"connected socket:   {e!r}")
        print("  The other computer sent back an ICMP “port unreachable” (Chapter 21), and because this")
        print("  socket is connected, the kernel knew which socket it was about, and told us.")
# --8<-- [end:refused]


def udp_drops():
    """The kernel's own count of datagrams thrown away because a socket's buffer was full."""
    if os.path.exists("/proc/net/snmp"):
        lines = [l.split() for l in open("/proc/net/snmp") if l.startswith("Udp:")]
        return int(dict(zip(lines[0], lines[1]))["RcvbufErrors"])
    out = subprocess.run(["netstat", "-s", "-p", "udp"], capture_output=True, text=True).stdout
    m = re.search(r"(\d+) dropped due to full socket buffers", out)
    return int(m.group(1)) if m else 0


# --8<-- [start:flood]
def flood(count=20000, size=1000, rcvbuf=None):
    reader = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if rcvbuf:
        reader.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
    reader.bind(("127.0.0.1", 7101))
    buf = reader.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    before = udp_drops()
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for n in range(count):                                # as fast as we can: nobody will say "slow down"
        sender.sendto(struct.pack("!I", n) + bytes(size - 4), ("127.0.0.1", 7101))
    got, seen = 0, set()
    reader.setblocking(False)
    while True:                                           # now read whatever the kernel kept for us
        try:
            data = reader.recv(65535)
        except BlockingIOError:
            break
        got += 1
        seen.add(struct.unpack("!I", data[:4])[0])
    dropped = udp_drops() - before
    print(f"receive buffer {buf:,} bytes: sent {count:,} datagrams of {size} bytes, received {got:,}, "
          f"lost {count - got:,}  (the kernel counted {dropped:,} dropped for full buffers)")
    if seen:
        print(f"  the survivors were numbers {min(seen)} to {max(seen)}: "
              f"{'the first ones, until the buffer filled' if max(seen) < count - 1 else 'some from all over'}")
# --8<-- [end:flood]


def big():
    reader = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    reader.bind(("127.0.0.1", 7102))
    reader.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for size in (1000, 1472, 1473, 9216, 9217, 65507, 65508):
        try:
            sender.sendto(bytes(size), ("127.0.0.1", 7102))
            reader.settimeout(1)
            got = len(reader.recv(70000))
            print(f"{size:>6} bytes: sent and received ({got} bytes)")
        except OSError as e:
            print(f"{size:>6} bytes: {e.strerror}")
    if sys.platform == "darwin":
        print("macOS refuses anything bigger than its net.inet.udp.maxdgram setting: 9,216 bytes, unless you change it.")
    print("1472 = 1500 (Ethernet's MTU) - 20 (IP header) - 8 (UDP header): the most that fits in one frame.")
    print("65507 = 65535 (IP's biggest packet) - 20 - 8: the most UDP can carry at all. Anything over 1472")
    print("would be cut into IP fragments on a real network (Chapter 20). Loopback's MTU is much bigger.")


# --8<-- [start:chat]
GROUP, PORT = "239.255.42.99", 7199                   # 239.x.x.x: multicast for use inside one network


def chat(name):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)          # several chatters on one computer
    if hasattr(socket, "SO_REUSEPORT"):
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    s.bind(("", PORT))
    join = struct.pack("4s4s", socket.inet_aton(GROUP), socket.inet_aton("0.0.0.0"))
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, join)  # "please deliver this group to me"
    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)      # never past the first router
    s.sendto(f"{name} joined".encode(), (GROUP, PORT))
    print(f"chatting on {GROUP}:{PORT}. Type a line and press Enter; Ctrl-C to leave.")
    while True:
        ready, _, _ = select.select([s, sys.stdin], [], [])
        if s in ready:
            data, (ip, port) = s.recvfrom(1500)
            print(f"  [{ip}] {data.decode(errors='replace')}")
        if sys.stdin in ready:
            line = sys.stdin.readline()
            if not line:
                break
            s.sendto(f"{name}: {line.strip()}".encode(), (GROUP, PORT))
# --8<-- [end:chat]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "refused":
        refused()
    elif cmd == "flood":
        flood()
        flood(rcvbuf=8 * 1024 * 1024)
    elif cmd == "big":
        big()
    elif cmd == "chat":
        try:
            chat(sys.argv[2] if len(sys.argv) > 2 else socket.gethostname())
        except KeyboardInterrupt:
            print()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
