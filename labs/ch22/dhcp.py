#!/usr/bin/env python3
"""Chapter 22 lab: DHCP, the protocol that hands out addresses.

    python3 dhcp.py lease              your own computer's lease, option by option (macOS or Linux)
    python3 dhcp.py dora               a tiny DHCP server and two clients, talking on this computer;
                                       also writes dora.pcap for tcpdump or Wireshark
    sudo python3 dhcp.py discover wlan0
                                       Linux only: ask your real router for an offer, using a made-up
                                       card address. It never accepts, so nothing is really handed out.
"""
import argparse
import os
import random
import re
import socket
import struct
import subprocess
import sys
import threading
import time

COOKIE = bytes([99, 130, 83, 99])                # "the options start here": a magic number from 1993
KINDS = {1: "DISCOVER", 2: "OFFER", 3: "REQUEST", 4: "DECLINE", 5: "ACK", 6: "NAK", 7: "RELEASE", 8: "INFORM"}
OPTION_NAMES = {1: "subnet mask", 3: "router", 6: "name servers", 12: "host name", 15: "domain name", 28: "broadcast address",
                50: "requested address", 51: "lease time", 53: "message type", 54: "server", 55: "please tell me about",
                58: "renew after", 59: "rebind after", 61: "client id", 255: "end"}


def ip(b):
    return ".".join(map(str, b))


def ipb(text):
    return bytes(int(x) for x in text.split("."))


def mac(b):
    return ":".join(f"{x:02x}" for x in b)


# --8<-- [start:build]
def dhcp_message(op, kind, xid, chaddr, yiaddr="0.0.0.0", ciaddr="0.0.0.0", broadcast=True, options=()):
    """A DHCP message is an old BOOTP message (1985), with DHCP's options added at the end."""
    fixed = struct.pack("!BBBBIHH4s4s4s4s16s64s128s",
                        op,                          # 1 = from a client, 2 = from a server
                        1, 6, 0,                     # Ethernet, 6-byte card addresses, no relays yet
                        xid,                         # a random number that ties the conversation together
                        0, 0x8000 if broadcast else 0,   # "please broadcast your answer: I have no address yet"
                        ipb(ciaddr), ipb(yiaddr),    # the client's current address, and "your address"
                        bytes(4), bytes(4),
                        chaddr.ljust(16, b"\0"),     # the client's card address
                        bytes(64), bytes(128))       # server name and boot file: BOOTP leftovers
    opts = bytes([53, 1, kind])
    for code, value in options:
        opts += bytes([code, len(value)]) + value
    return fixed + COOKIE + opts + bytes([255])
# --8<-- [end:build]


# --8<-- [start:parse]
def parse(data):
    op, _, _, _, xid, _, flags = struct.unpack_from("!BBBBIHH", data)
    ciaddr, yiaddr = data[12:16], data[16:20]
    chaddr = data[28:34]
    options, i = {}, 240                             # 236 bytes of BOOTP, then the 4-byte cookie
    while i < len(data) and data[i] != 255:
        if data[i] == 0:                             # padding
            i += 1
            continue
        code, length = data[i], data[i + 1]
        options[code] = data[i + 2:i + 2 + length]
        i += 2 + length
    return {"op": op, "xid": xid, "ciaddr": ip(ciaddr), "yiaddr": ip(yiaddr), "chaddr": mac(chaddr),
            "kind": KINDS.get(options.get(53, b"\0")[0], "?"), "options": options}
# --8<-- [end:parse]


def describe_option(code, value):
    name = OPTION_NAMES.get(code, f"option {code}")
    if code in (1, 3, 6, 28, 50, 54):
        shown = ", ".join(ip(value[i:i + 4]) for i in range(0, len(value), 4))
    elif code in (51, 58, 59):
        secs = struct.unpack("!I", value)[0]
        shown = f"{secs:,} seconds ({secs / 3600:g} hours)"
    elif code == 53:
        shown = KINDS.get(value[0], "?")
    elif code == 55:
        shown = ", ".join(OPTION_NAMES.get(c, str(c)) for c in value)
    elif code in (12, 15):
        shown = value.decode(errors="replace")
    else:
        shown = value.hex(" ")
    return f"{name:>22}: {shown}"


def show(message, who):
    m = parse(message)
    print(f"{who} {m['kind']}  (transaction {m['xid']:08x}, client {m['chaddr']}" +
          (f", offering {m['yiaddr']}" if m["yiaddr"] != "0.0.0.0" else "") + ")")
    for code, value in m["options"].items():
        if code != 53:
            print("    " + describe_option(code, value))


# ---------------------------------------------------------------- your own lease

def lease():
    if sys.platform == "darwin":
        out = subprocess.run(["ipconfig", "getpacket", "en0"], capture_output=True, text=True).stdout
        if not out:
            raise SystemExit("No DHCP lease on en0. (Is Wi-Fi on? Try another interface, like en1.)")
        wanted = ["yiaddr", "dhcp_message_type", "server_identifier", "lease_time", "renewal_t1_time_value",
                  "rebinding_t2_time_value", "subnet_mask", "router", "domain_name_server", "domain_name"]
        for line in out.splitlines():
            key = line.split(" ")[0]
            if key in wanted:
                if key == "lease_time":
                    secs = int(line.split(":")[1].strip(), 16)
                    line += f"   = {secs:,} seconds = {secs / 3600:g} hours"
                print("  " + line.strip())
    else:
        out = subprocess.run(["nmcli", "-f", "DHCP4", "device", "show"], capture_output=True, text=True).stdout
        if not out:
            raise SystemExit("Couldn't ask NetworkManager (nmcli). On other systems, look in /var/lib/dhcp/.")
        for line in out.splitlines():
            if "requested_" not in line and "=" in line:
                name, value = line.split(":", 1)[1].split("=", 1)
                print(f"  {name.strip():>24} = {value.strip()}")
                if name.strip() == "expiry":
                    left = int(value) - time.time()
                    print(f"  {'':>24}   (that's in {left / 3600:.1f} hours; the computer renews at half-way)")


# ---------------------------------------------------------------- a whole conversation, on this computer

SERVER_PORT, CLIENT_PORT = 6767, 6868              # the real ports, 67 and 68, need administrator rights


# --8<-- [start:server]
class Server:
    """A tiny DHCP server: a pool of addresses, and a memory of who has which."""

    def __init__(self, first=100, last=199, lease_secs=86400):
        self.pool = [f"192.168.1.{n}" for n in range(first, last + 1)]
        self.leases = {}                                  # card address -> IP address
        self.lease_secs = lease_secs

    def answer(self, message):
        m = parse(message)
        client = bytes.fromhex(m["chaddr"].replace(":", ""))
        if m["kind"] == "DISCOVER":                       # pick an address: the same one as last time, if we can
            offer = self.leases.get(m["chaddr"]) or next(a for a in self.pool if a not in self.leases.values())
            return self.reply(2, m["xid"], client, offer)
        if m["kind"] == "REQUEST":
            wanted = ip(m["options"][50]) if 50 in m["options"] else m["ciaddr"]
            taken = [c for c, a in self.leases.items() if a == wanted and c != m["chaddr"]]
            if taken or wanted not in self.pool:
                return self.reply(6, m["xid"], client, "0.0.0.0")      # NAK: "no, start again"
            self.leases[m["chaddr"]] = wanted
            return self.reply(5, m["xid"], client, wanted)
        return None

    def reply(self, kind, xid, client, address):
        opts = [(54, ipb("192.168.1.1"))]
        if kind != 6:
            opts += [(51, struct.pack("!I", self.lease_secs)), (58, struct.pack("!I", self.lease_secs // 2)),
                     (59, struct.pack("!I", self.lease_secs * 7 // 8)), (1, ipb("255.255.255.0")),
                     (3, ipb("192.168.1.1")), (6, ipb("192.168.1.1")), (15, b"home")]
        return dhcp_message(2, kind, xid, client, yiaddr=address, options=opts)
# --8<-- [end:server]


def run_server(server, sock, captured):
    while True:
        data, addr = sock.recvfrom(2048)
        if data == b"stop":
            return
        captured.append(("client", data))
        reply = server.answer(data)
        if reply:
            captured.append(("server", reply))
            sock.sendto(reply, addr)


# --8<-- [start:client]
def client_joins(sock, card, hostname):
    """Discover, offer, request, acknowledge: DORA."""
    xid = random.getrandbits(32)
    ask = [(55, bytes([1, 3, 6, 15])), (12, hostname.encode())]
    sock.sendto(dhcp_message(1, 1, xid, card, options=ask), ("127.0.0.1", SERVER_PORT))
    offer = parse(sock.recvfrom(2048)[0])
    request = dhcp_message(1, 3, xid, card, options=[(50, ipb(offer["yiaddr"])), (54, ipb("192.168.1.1"))] + ask)
    sock.sendto(request, ("127.0.0.1", SERVER_PORT))
    ack = parse(sock.recvfrom(2048)[0])
    return ack["yiaddr"] if ack["kind"] == "ACK" else None
# --8<-- [end:client]


def dora():
    server, captured = Server(), []
    ssock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ssock.bind(("127.0.0.1", SERVER_PORT))
    thread = threading.Thread(target=run_server, args=(server, ssock, captured), daemon=True)
    thread.start()
    csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    csock.bind(("127.0.0.1", CLIENT_PORT))
    csock.settimeout(2)
    laptop, pi = bytes.fromhex("e25fb13c770a"), bytes.fromhex("2ccf675e10c2")
    got = client_joins(csock, laptop, "bobs-laptop")
    got2 = client_joins(csock, pi, "raspberrypi")
    got3 = client_joins(csock, laptop, "bobs-laptop")
    csock.sendto(b"stop", ("127.0.0.1", SERVER_PORT))
    thread.join(1)
    for who, data in captured:
        show(data, f"{'→' if who == 'client' else '←'} {who:<6}")
        print()
    print(f"Bob's laptop got {got}, the Pi got {got2}, and when the laptop came back it got {got3} again.")
    write_pcap("dora.pcap", captured)
    print("Saved the conversation to dora.pcap. Try: tcpdump -r dora.pcap -n -v")


def write_pcap(path, captured):
    """Wrap each message in UDP, IP and Ethernet headers, as it would look on a real network."""
    def csum(b):
        if len(b) % 2:
            b += b"\0"
        s = sum(struct.unpack(f"!{len(b) // 2}H", b))
        while s >> 16:
            s = (s & 0xFFFF) + (s >> 16)
        return ~s & 0xFFFF
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        t = time.time()
        for n, (who, data) in enumerate(captured):
            m = parse(data)
            client = bytes.fromhex(m["chaddr"].replace(":", ""))
            if who == "client":
                src, dst, sport, dport, smac, dmac = "0.0.0.0", "255.255.255.255", 68, 67, client, b"\xff" * 6
            else:
                src, dst, sport, dport, smac, dmac = "192.168.1.1", "255.255.255.255", 67, 68, bytes.fromhex("14c35e400b32"), b"\xff" * 6
            udp = struct.pack("!HHHH", sport, dport, 8 + len(data), 0) + data
            pseudo = ipb(src) + ipb(dst) + struct.pack("!BBH", 0, 17, len(udp))
            udp = udp[:6] + struct.pack("!H", csum(pseudo + udp) or 0xFFFF) + udp[8:]
            iph = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(udp), n, 0, 64, 17, 0, ipb(src), ipb(dst))
            iph = iph[:10] + struct.pack("!H", csum(iph)) + iph[12:]
            frame = dmac + smac + b"\x08\x00" + iph + udp
            f.write(struct.pack("<IIII", int(t), n * 1000, len(frame), len(frame)) + frame)


# ---------------------------------------------------------------- a real router (Linux, as root)

def discover(iface):
    if not sys.platform.startswith("linux") or os.geteuid() != 0:
        raise SystemExit("This needs Linux and sudo, because DHCP clients use port 68. Try 'dora' instead.")
    card = bytes([0x02, 0x62, 0x62]) + os.urandom(3)     # "chosen by software" bit set: a made-up card
    xid = random.getrandbits(32)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, 25, iface.encode())    # SO_BINDTODEVICE: only this interface
    sock.bind(("0.0.0.0", 68))
    message = dhcp_message(1, 1, xid, card, options=[(55, bytes([1, 3, 6, 15, 51, 58, 59]))])
    sock.sendto(message, ("255.255.255.255", 67))
    show(message, "→ sent")
    print()
    sock.settimeout(5)
    try:
        while True:
            data, (sender, _) = sock.recvfrom(2048)
            if parse(data)["xid"] == xid:
                show(data, f"← from {sender}:")
                print("\n(We never send a REQUEST, so the router will hand this address to someone else.)")
                return
    except socket.timeout:
        print("No offer within 5 seconds.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("lease")
    sub.add_parser("dora")
    d = sub.add_parser("discover")
    d.add_argument("iface")
    args = p.parse_args()
    if args.cmd == "lease":
        lease()
    elif args.cmd == "dora":
        dora()
    elif args.cmd == "discover":
        discover(args.iface)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
