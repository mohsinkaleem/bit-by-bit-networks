#!/usr/bin/env python3
"""Chapter 18 lab: real Ethernet frames, card (MAC) addresses, and a switch with VLANs.

    python3 frames.py build                        build some frames byte by byte, and save them to frames.pcap
    python3 frames.py mac 2c:cf:67:5e:10:c2 ff:ff:ff:ff:ff:ff     take MAC addresses apart
    python3 frames.py mac --mine                   ...including your own computer's
    python3 frames.py switch                       a switch with two VLANs, learning as frames arrive
    sudo python3 frames.py send IFACE              Linux only: send real frames out of an interface (see the chapter)

Then look at the saved frames with tcpdump:   tcpdump -r frames.pcap -e -n -xx
"""
import argparse
import re
import socket
import struct
import subprocess
import sys
import time
import zlib

# The first three bytes of a card address are the manufacturer's "organizationally unique identifier".
# The full list has over 50,000 entries (https://standards-oui.ieee.org); these are a few you'll meet.
VENDORS = {"2c:cf:67": "Raspberry Pi", "d8:3a:dd": "Raspberry Pi", "dc:a6:32": "Raspberry Pi", "b8:27:eb": "Raspberry Pi Foundation",
           "3c:22:fb": "Apple", "84:2f:57": "Apple", "a4:83:e7": "Apple", "f0:18:98": "Apple", "00:1b:21": "Intel",
           "3c:7c:3f": "ASUS", "00:50:56": "VMware (a virtual card, for a virtual machine)"}
SPECIAL = {"ff:ff:ff:ff:ff:ff": "broadcast: every card on the network", "01:80:c2:00:00:00": "switches talking spanning tree (Chapter 9)",
           "01:00:5e": "IPv4 multicast (a group of listeners)", "33:33": "IPv6 multicast"}


def mac_bytes(text):
    return bytes(int(x, 16) for x in text.split(":"))


def mac_str(b):
    return ":".join(f"{x:02x}" for x in b)


# --8<-- [start:frame]
def ethernet_frame(dst, src, ethertype, payload, vlan=None, priority=0):
    """Build a frame the way a network card does, apart from the preamble, which is pure timing."""
    header = mac_bytes(dst) + mac_bytes(src)
    if vlan is not None:                                   # an 802.1Q tag: 4 bytes squeezed in before the type
        header += struct.pack("!HH", 0x8100, priority << 13 | vlan)
    header += struct.pack("!H", ethertype)
    if len(payload) < 46:                                  # the shortest payload allowed is 46 bytes (Chapter 8),
        payload += bytes(46 - len(payload))                # so short ones are padded with zeros
    body = header + payload
    fcs = struct.pack("<I", zlib.crc32(body))              # Chapter 10's CRC-32, sent lowest byte first
    return body + fcs
# --8<-- [end:frame]


def on_the_wire(frame):
    """Everything the cable actually carries for one frame, and how much of it is your data."""
    return 7 + 1 + len(frame) + 12                         # preamble, start-of-frame byte, the frame, a 12-byte gap


def write_pcap(path, frames):
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        now = time.time()
        for n, frame in enumerate(frames):
            t = now + n * 0.001
            data = frame[:-4]                              # captures normally leave the checksum off, like real cards
            f.write(struct.pack("<IIII", int(t), int(t % 1 * 1e6), len(data), len(data)) + data)


def build():
    pi, router, laptop = "2c:cf:67:5e:10:c2", "14:c3:5e:40:0b:32", "e2:5f:b1:3c:77:0a"
    samples = [
        ("a tiny message to the router", ethernet_frame(router, pi, 0x88B5, b"hi, router!"), 11),
        ("the same, to everyone", ethernet_frame("ff:ff:ff:ff:ff:ff", pi, 0x88B5, b"hi, everyone!"), 13),
        ("a full-size frame", ethernet_frame(router, laptop, 0x88B5, bytes(1500)), 1500),
        ("tagged for VLAN 20", ethernet_frame(router, pi, 0x88B5, b"hi from VLAN 20", vlan=20), 15),
        ("VLAN 30, top priority", ethernet_frame(router, pi, 0x88B5, b"urgent!", vlan=30, priority=7), 7),
    ]
    print(f"{'frame':<30}{'data':>7}{'frame':>7}{'on the wire':>13}{'useful':>9}")
    for name, frame, useful in samples:
        wire = on_the_wire(frame)
        print(f"{name:<30}{useful:>7}{len(frame):>7}{wire:>13}{useful / wire:>9.1%}")
    frame = samples[0][1]
    print("\nThe first one, byte by byte:")
    parts = [("to", frame[0:6]), ("from", frame[6:12]), ("type", frame[12:14]), ("data", frame[14:25]),
             ("padding", frame[25:60]), ("check (FCS)", frame[60:64])]
    for label, chunk in parts:
        print(f"  {label:>12}  {chunk.hex(' ')}")
    write_pcap("frames.pcap", [f for _, f, _ in samples])
    print("\nSaved to frames.pcap. Try: tcpdump -r frames.pcap -e -n -xx")


# --8<-- [start:mac]
def describe_mac(text):
    b = mac_bytes(text)
    first = b[0]
    notes = [f"first byte {first:02x} = {first:08b}"]
    if first & 1:
        notes.append("a group address (multicast): many cards may listen")
    else:
        notes.append("one card (unicast)")
        notes.append("chosen by software, not set at a factory" if first & 2 else "set at the factory, unique in the world")
    lower = mac_str(b)
    for prefix, name in SPECIAL.items():
        if lower.startswith(prefix):
            notes.append(name)
    if not first & 3:
        notes.append("made by " + VENDORS.get(lower[:8], "someone not in this lab's short list"))
    return notes
# --8<-- [end:mac]


def my_macs():
    if sys.platform == "darwin":
        out = subprocess.run(["ifconfig"], capture_output=True, text=True).stdout
        pattern = r"^(\S+?):.*?\n(?:\t.*\n)*?\tether ([0-9a-f:]{17})"
    else:
        out = subprocess.run(["ip", "-o", "link"], capture_output=True, text=True).stdout
        pattern = r"^\d+: (\S+?)[:@].*?link/ether ([0-9a-f:]{17})"
    return re.findall(pattern, out, re.M)


def mac_command(addresses, mine):
    found = [(f"{name}", addr) for name, addr in my_macs()] if mine else [("", a) for a in addresses]
    for name, addr in found:
        print(f"{addr}  {name}")
        for note in describe_mac(addr):
            print(f"    {note}")


# --8<-- [start:switch]
class Switch:
    """A learning switch (Chapter 9) that also understands VLANs.
    ports: {port: ("access", vlan)} or {port: ("trunk", {vlans})}"""

    def __init__(self, ports):
        self.ports = ports
        self.table = {}                                     # (vlan, card address) -> port

    def receive(self, port, frame_vlan, src, dst):
        kind, cfg = self.ports[port]
        vlan = cfg if kind == "access" else frame_vlan      # access ports add the tag; trunks already have one
        if kind == "trunk" and vlan not in cfg:
            return f"VLAN {vlan} isn't allowed on port {port}: dropped", []
        self.table[(vlan, src)] = port                      # learn, but separately for each VLAN
        if dst != "ff:ff:ff:ff:ff:ff" and (vlan, dst) in self.table:
            out = [self.table[(vlan, dst)]]
            how = "known"
        else:
            out = [p for p, (k, c) in self.ports.items() if p != port and (c == vlan if k == "access" else vlan in c)]
            how = "flooded"
        sends = [(p, "tagged" if self.ports[p][0] == "trunk" else "untagged") for p in out if p != port]
        return f"VLAN {vlan}, {how}", sends
# --8<-- [end:switch]


def switch_demo():
    names = {1: "laptop", 2: "TV", 3: "doorbell", 4: "thermostat", 5: "to the router"}
    macs = {"laptop": "e2:5f:b1:3c:77:0a", "TV": "a4:83:e7:11:22:33", "doorbell": "3c:7c:3f:44:55:66",
            "thermostat": "d8:3a:dd:77:88:99", "router": "14:c3:5e:40:0b:32"}
    sw = Switch({1: ("access", 10), 2: ("access", 10), 3: ("access", 20), 4: ("access", 20), 5: ("trunk", {10, 20})})
    print("Ports: 1 laptop and 2 TV are in VLAN 10 (family); 3 doorbell and 4 thermostat are in VLAN 20 (gadgets);")
    print("5 is a trunk to the router, carrying both VLANs with tags.\n")
    events = [(3, None, "doorbell", "ff:ff:ff:ff:ff:ff", "the doorbell shouts “who has 192.168.20.1?”"),
              (5, 20, "router", "doorbell", "the router answers the doorbell, tagged VLAN 20"),
              (1, None, "laptop", "ff:ff:ff:ff:ff:ff", "the laptop shouts “who has 192.168.10.1?”"),
              (5, 10, "router", "laptop", "the router answers the laptop, tagged VLAN 10"),
              (3, None, "doorbell", "laptop", "the doorbell tries to send straight to the laptop"),
              (1, None, "laptop", "TV", "the laptop sends to the TV (not learned yet)"),
              (2, None, "TV", "laptop", "the TV answers")]
    for port, tag, src, dst, story in events:
        dst_mac = macs.get(dst, dst)
        how, sends = sw.receive(port, tag, macs[src], dst_mac)
        where = ", ".join(f"{p} ({names[p]}, {t})" for p, t in sends) or "nowhere"
        print(f"{story}\n    in on port {port}: {how} → out of {where}")
    print("\nThe switch's table (VLAN, card address → port):")
    for (vlan, mac), port in sorted(sw.table.items()):
        who = next(n for n, m in macs.items() if m == mac)
        print(f"    VLAN {vlan:<3} {mac}  → port {port}   ({who})")


def send(iface, count):
    """Linux only, as root: hand finished frames to a network card with a raw 'packet' socket."""
    if not hasattr(socket, "AF_PACKET"):
        raise SystemExit("Raw packet sockets are Linux only. On a Mac, use 'build' and look at frames.pcap instead.")
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    sock.bind((iface, 0))
    src = open(f"/sys/class/net/{iface}/address").read().strip()
    for n in range(count):
        for vlan in (None, 20):
            frame = ethernet_frame("ff:ff:ff:ff:ff:ff", src, 0x88B5, f"hello #{n} from Bit by Bit".encode(), vlan=vlan)
            sock.send(frame[:-4])                          # the card adds its own checksum
    print(f"sent {count * 2} frames out of {iface}, half of them tagged for VLAN 20")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("build")
    m = sub.add_parser("mac")
    m.add_argument("addresses", nargs="*")
    m.add_argument("--mine", action="store_true")
    sub.add_parser("switch")
    s = sub.add_parser("send")
    s.add_argument("iface")
    s.add_argument("--count", type=int, default=2)
    args = p.parse_args()
    if args.cmd == "build":
        build()
    elif args.cmd == "mac":
        mac_command(args.addresses, args.mine)
    elif args.cmd == "switch":
        switch_demo()
    elif args.cmd == "send":
        send(args.iface, args.count)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
