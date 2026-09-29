#!/usr/bin/env python3
"""Chapter 24 lab: a tiny BGP speaker. Real BGP messages, over a real TCP connection.

    python3 bgp_speaker.py                 the university (AS 65001) opens a session with its provider
                                           (AS 64510), both on this computer, and they swap routes
    python3 bgp_speaker.py --hex           …and show the bytes of every message
    python3 bgp_speaker.py --pcap bgp.pcap decode the BGP messages in a capture (like the one the demo saves)

Real BGP uses TCP port 179, which needs administrator rights, so the demo uses port 1179 on
127.0.0.1. The capture it saves (bgp.pcap) uses port 179, so tcpdump and Wireshark decode it:
    tcpdump -r bgp.pcap -n -v
"""
import argparse
import ipaddress
import socket
import struct
import threading
import time

MARKER = b"\xff" * 16                           # every BGP message starts with 16 bytes of ones
KINDS = {1: "OPEN", 2: "UPDATE", 3: "NOTIFICATION", 4: "KEEPALIVE"}
ORIGINS = {0: "IGP", 1: "EGP", 2: "incomplete"}
CEASE = {2: "administrative shutdown", 4: "administrative reset"}


# --8<-- [start:build]
def message(kind, body=b""):
    return MARKER + struct.pack("!HB", 19 + len(body), kind) + body


def open_msg(asn, hold, router_id):
    caps = (bytes([1, 4]) + struct.pack("!HBB", 1, 0, 1)      # capability 1: I speak IPv4 unicast
            + bytes([65, 4]) + struct.pack("!I", asn))         # capability 65: I understand 4-byte AS numbers
    params = bytes([2, len(caps)]) + caps                      # optional parameter 2 = capabilities
    two_byte_as = asn if asn < 65536 else 23456                # AS_TRANS, for big AS numbers
    return message(1, struct.pack("!BHH4sB", 4, two_byte_as, hold,
                                  ipaddress.ip_address(router_id).packed, len(params)) + params)


def prefixes(nets):
    out = b""
    for net in map(ipaddress.ip_network, nets):
        n = (net.prefixlen + 7) // 8                           # only as many bytes as the prefix needs
        out += bytes([net.prefixlen]) + net.network_address.packed[:n]
    return out


def update_msg(announce=(), withdraw=(), path=(), next_hop=None):
    withdrawn = prefixes(withdraw)
    attrs = b""
    if announce:
        segment = bytes([2, len(path)]) + b"".join(struct.pack("!I", a) for a in path)   # 2 = AS_SEQUENCE
        attrs += bytes([0x40, 1, 1, 0])                                                   # ORIGIN: IGP
        attrs += bytes([0x40, 2, len(segment)]) + segment                                 # AS_PATH
        attrs += bytes([0x40, 3, 4]) + ipaddress.ip_address(next_hop).packed              # NEXT_HOP
    return message(2, struct.pack("!H", len(withdrawn)) + withdrawn +
                   struct.pack("!H", len(attrs)) + attrs + prefixes(announce))
# --8<-- [end:build]


def read_prefixes(data):
    out, i = [], 0
    while i < len(data):
        plen = data[i]
        n = (plen + 7) // 8
        raw = (data[i + 1:i + 1 + n] + b"\0\0\0\0")[:4]           # put back the bytes that were left out
        out.append(str(ipaddress.ip_network((int.from_bytes(raw, "big"), plen))))
        i += 1 + n
    return out


# --8<-- [start:describe]
def describe(msg, four_byte=True):
    """Turn one BGP message into a line of English."""
    length, kind = struct.unpack("!HB", msg[16:19])
    body = msg[19:length]
    if kind == 1:
        ver, asn, hold, rid, plen = struct.unpack("!BHH4sB", body[:10])
        caps, i, params = [], 0, body[10:10 + plen]
        while i < len(params):
            ptype, pl = params[i], params[i + 1]
            j, p = 0, params[i + 2:i + 2 + pl]
            while ptype == 2 and j < len(p):
                code, cl = p[j], p[j + 1]
                value = p[j + 2:j + 2 + cl]
                if code == 65:
                    asn = struct.unpack("!I", value)[0]
                caps.append({1: "IPv4 unicast" if value[:4] == b"\0\x01\0\x01" else "another address family",
                             2: "route refresh", 64: "graceful restart", 65: "4-byte AS numbers",
                             69: "add-path"}.get(code, f"capability {code}"))
                j += 2 + cl
            i += 2 + pl
        return (f"version {ver}, my AS {asn}, hold time {hold} s, id {ipaddress.ip_address(rid)}, "
                f"I can do: {', '.join(caps)}")
    if kind == 2:
        wlen = struct.unpack("!H", body[:2])[0]
        withdrawn = read_prefixes(body[2:2 + wlen])
        alen = struct.unpack("!H", body[2 + wlen:4 + wlen])[0]
        attrs, nlri = body[4 + wlen:4 + wlen + alen], read_prefixes(body[4 + wlen + alen:])
        info, i = [], 0
        while i < len(attrs):
            flags, code = attrs[i], attrs[i + 1]
            if flags & 0x10:                                     # "extended length": 2 length bytes
                alen2, i = struct.unpack("!H", attrs[i + 2:i + 4])[0], i + 4
            else:
                alen2, i = attrs[i + 2], i + 3
            value = attrs[i:i + alen2]
            i += alen2
            if code == 1:
                info.append(f"origin {ORIGINS.get(value[0], value[0])}")
            elif code == 2:
                path, k = [], 0
                while k < len(value):
                    n, size = value[k + 1], 4 if four_byte else 2
                    path += [int.from_bytes(value[k + 2 + size * m:k + 2 + size * (m + 1)], "big") for m in range(n)]
                    k += 2 + n * size
                info.append("AS path " + (" ".join(map(str, path)) or "(empty)"))
            elif code == 3:
                info.append(f"next hop {ipaddress.ip_address(value)}")
            elif code == 4:
                info.append(f"MED {int.from_bytes(value, 'big')}")
            elif code == 5:
                info.append(f"local pref {int.from_bytes(value, 'big')}")
            elif code == 8:
                info.append("communities " + " ".join(f"{int.from_bytes(value[m:m + 2], 'big')}:{int.from_bytes(value[m + 2:m + 4], 'big')}"
                                                      for m in range(0, len(value), 4)))
            else:
                info.append(f"attribute {code}")
        parts = []
        if nlri:
            parts.append(f"announce {', '.join(nlri)}: {', '.join(info)}")
        if withdrawn:
            parts.append(f"withdraw {', '.join(withdrawn)}")
        return "; ".join(parts) or "end of the initial routes (an empty update)"
    if kind == 3:
        code, sub = body[0], body[1]
        if code == 6:
            return f"cease: {CEASE.get(sub, sub)}"
        return f"error {code}, subcode {sub}"
    return ""
# --8<-- [end:describe]


def read_message(sock):
    head = b""
    while len(head) < 19:
        chunk = sock.recv(19 - len(head))
        if not chunk:
            return None
        head += chunk
    length = struct.unpack("!H", head[16:18])[0]
    body = b""
    while len(body) < length - 19:
        body += sock.recv(length - 19 - len(body))
    return head + body


def hexdump(msg, indent="      "):
    for i in range(0, len(msg), 16):
        print(indent + " ".join(f"{b:02x}" for b in msg[i:i + 16]))


# ---------------------------------------------------------------- the demo: two speakers on one computer

UNI = dict(asn=65001, rid="10.255.1.1", addr="10.0.1.1")
NORTH = dict(asn=64510, rid="10.255.10.1", addr="10.0.1.2")


def provider(server, log):
    conn, _ = server.accept()
    got = read_message(conn)                                     # the university's OPEN
    log.append(("uni", got))
    for m in (open_msg(NORTH["asn"], 90, NORTH["rid"]), message(4)):
        conn.sendall(m)
        log.append(("north", m))
    while True:
        got = read_message(conn)
        if got is None:
            break
        log.append(("uni", got))
        kind = got[18]
        if kind == 4:                                            # its KEEPALIVE: the session is up. Our routes:
            for m in (update_msg(["0.0.0.0/0"], path=[64510], next_hop=NORTH["addr"]),
                      update_msg(["198.51.100.0/24"], path=[64510, 64500, 64496], next_hop=NORTH["addr"]),
                      update_msg()):
                conn.sendall(m)
                log.append(("north", m))
        if kind == 3:
            break
    conn.close()


# --8<-- [start:demo]
def demo(show_hex):
    server = socket.create_server(("127.0.0.1", 1179))
    log = []
    threading.Thread(target=provider, args=(server, log), daemon=True).start()

    sock = socket.create_connection(("127.0.0.1", 1179))        # 1. an ordinary TCP connection
    printed = 0

    def send(m):
        sock.sendall(m)                                         # (the provider logs what it receives)

    def show():
        nonlocal printed
        time.sleep(0.3)
        for who, m in log[printed:]:
            arrow = "→" if who == "uni" else "←"
            print(f"{arrow} {KINDS[m[18]]:<13} {describe(m)}")
            if show_hex:
                hexdump(m)
        printed = len(log)

    send(open_msg(UNI["asn"], 90, UNI["rid"]))                  # 2. "hello, I'm AS 65001"
    read_message(sock), read_message(sock)                      #    their OPEN, and a KEEPALIVE
    send(message(4))                                            # 3. "agreed": the session is established
    show()
    send(update_msg(["10.1.0.0/16"], path=[65001], next_hop=UNI["addr"]))   # 4. our addresses
    for _ in range(3):
        read_message(sock)                                      #    their routes, then an empty update
    show()
    print("…the session stays open, with a KEEPALIVE every 30 seconds. Later:")
    send(update_msg(withdraw=["10.1.0.0/16"]))                  # 5. take our route back
    send(message(3, bytes([6, 2])))                             # 6. "goodbye": cease, administrative shutdown
    show()
    sock.close()
    server.close()
    return log
# --8<-- [end:demo]


# ---------------------------------------------------------------- captures

def csum(b):
    if len(b) % 2:
        b += b"\0"
    s = sum(struct.unpack(f"!{len(b) // 2}H", b))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def write_pcap(path, log):
    """Wrap the conversation in TCP, IP and Ethernet headers, as it would look on port 179."""
    ends = {"uni": (UNI["addr"], 40001, bytes.fromhex("020000000101")),
            "north": (NORTH["addr"], 179, bytes.fromhex("020000000102"))}
    seq = {"uni": 1000, "north": 5000}
    frames = []

    def seg(who, flags, data=b""):
        other = "north" if who == "uni" else "uni"
        (src, sport, smac), (dst, dport, dmac) = ends[who], ends[other]
        ack = seq[other] if flags != 0x02 else 0
        tcp = struct.pack("!HHIIBBHHH", sport, dport, seq[who], ack, 5 << 4, flags, 64240, 0, 0) + data
        pseudo = ipaddress.ip_address(src).packed + ipaddress.ip_address(dst).packed + struct.pack("!BBH", 0, 6, len(tcp))
        tcp = tcp[:16] + struct.pack("!H", csum(pseudo + tcp)) + tcp[18:]
        ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0xC0, 20 + len(tcp), len(frames), 0x4000, 1, 6, 0,
                         ipaddress.ip_address(src).packed, ipaddress.ip_address(dst).packed)
        ip = ip[:10] + struct.pack("!H", csum(ip)) + ip[12:]
        frames.append(dmac + smac + b"\x08\x00" + ip + tcp)
        seq[who] += len(data) + (1 if flags & 0x03 else 0)

    seg("uni", 0x02)                                             # SYN
    seg("north", 0x12)                                           # SYN, ACK
    seg("uni", 0x10)                                             # ACK
    for who, m in log:
        seg(who, 0x18, m)                                        # PSH, ACK: one BGP message each
    t = time.time()
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for n, frame in enumerate(frames):
            f.write(struct.pack("<IIII", int(t), n * 2000, len(frame), len(frame)) + frame)


def read_pcap(path):
    """Collect the TCP payloads to and from port 179, in order, and split them into BGP messages."""
    data = open(path, "rb").read()
    endian = "<" if data[:4] in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
    streams, at, first = {}, 24, None
    while at + 16 <= len(data):
        sec, frac, caplen, _ = struct.unpack(endian + "IIII", data[at:at + 16])
        frame, at = data[at + 16:at + 16 + caplen], at + 16 + caplen
        if frame[12:14] != b"\x08\x00" or frame[23] != 6:
            continue
        ip = 14 + (frame[14] & 15) * 4
        sport, dport, seqno = struct.unpack("!HHI", frame[ip:ip + 8])
        payload = frame[ip + (frame[ip + 12] >> 4) * 4:14 + struct.unpack("!H", frame[16:18])[0]]
        if 179 not in (sport, dport) or not payload:
            continue
        key = (socket.inet_ntoa(frame[26:30]), sport)
        seen = streams.setdefault(key, {})
        seen.setdefault(seqno, (sec, payload))                   # ignore retransmissions
    out = []
    for (src, sport), segs in streams.items():
        buf = b"".join(p for _, (_, p) in sorted(segs.items()))
        t0 = min(s for s, _ in segs.values())
        i = 0
        while i + 19 <= len(buf) and buf[i:i + 16] == MARKER:
            length = struct.unpack("!H", buf[i + 16:i + 18])[0]
            out.append((src, buf[i:i + length]))
            i += length
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hex", action="store_true")
    p.add_argument("--pcap")
    args = p.parse_args()
    if args.pcap:
        for src, m in read_pcap(args.pcap):
            print(f"{src:<15} {KINDS.get(m[18], m[18]):<13} {describe(m)}")
        return
    log = demo(args.hex)
    write_pcap("bgp.pcap", log)
    print("\nSaved the session to bgp.pcap. Try: tcpdump -r bgp.pcap -n -v")


if __name__ == "__main__":
    main()
