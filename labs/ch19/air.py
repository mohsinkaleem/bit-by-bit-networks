#!/usr/bin/env python3
"""Chapter 19 lab: decode raw Wi-Fi frames, the way a card in monitor mode hears them.

    python3 air.py --make-sample          write air.pcap: a laptop finding and joining a network
    python3 air.py air.pcap               one line per frame
    python3 air.py air.pcap -v            ...with every address and information element
    python3 air.py air.pcap --networks    just the networks that are announcing themselves

It reads captures with link type 127 (802.11 plus "radiotap", the radio details) or 105 (plain 802.11),
like the ones a Mac's Wireless Diagnostics → Window → Sniffer writes.
"""
import argparse
import struct
import time

TYPES = {(0, 0): "association request", (0, 1): "association response", (0, 4): "probe request",
         (0, 5): "probe response", (0, 8): "beacon", (0, 10): "disassociation", (0, 11): "authentication",
         (0, 12): "deauthentication", (1, 11): "RTS", (1, 12): "CTS", (1, 13): "ACK",
         (2, 0): "data", (2, 4): "null (just “I’m awake”)", (2, 8): "data", (2, 12): "null (just “I’m awake”)"}
AKM = {1: "WPA2 (company login)", 2: "WPA2 (password)", 8: "WPA3 (password)", 18: "open, encrypted (OWE)"}


def mac(b):
    return ":".join(f"{x:02x}" for x in b)


# --8<-- [start:radiotap]
def radiotap(data):
    """The capture's radio notes: returns (header length, channel frequency, signal in dBm)."""
    length, present = struct.unpack_from("<HI", data, 2)
    words = [present]
    while words[-1] & 0x80000000:                     # bit 31: another "present" word follows
        words.append(struct.unpack_from("<I", data, 4 + 4 * len(words))[0])
    pos, freq, signal = 4 + 4 * len(words), None, None
    sizes = {0: (8, 8), 1: (1, 1), 2: (1, 1), 3: (4, 2), 4: (2, 2), 5: (1, 1), 6: (1, 1)}
    for bit in range(7):                              # only the first few fields matter to us
        if not present & (1 << bit):
            continue
        size, align = sizes[bit]
        pos += -pos % align                           # every field starts on a multiple of its own size
        if bit == 3:
            freq = struct.unpack_from("<H", data, pos)[0]
        if bit == 5:
            signal = struct.unpack_from("<b", data, pos)[0]
        pos += size
    return length, freq, signal
# --8<-- [end:radiotap]


def channel_of(freq):
    if not freq:
        return None
    if freq == 2484:
        return 14
    if freq < 3000:
        return (freq - 2407) // 5
    return (freq - 5000) // 5 if freq < 5925 else (freq - 5950) // 5


# --8<-- [start:elements]
def elements(body):
    """Management frames end with a list of "information elements": (id, length, value), (id, length, value)…"""
    out, i = {}, 0
    while i + 2 <= len(body):
        eid, n = body[i], body[i + 1]
        out.setdefault(eid, body[i + 2:i + 2 + n])
        i += 2 + n
    return out


def describe_network(ies):
    ssid = ies.get(0, b"").decode(errors="replace") or "(hidden)"
    channel = ies[3][0] if 3 in ies else None
    security = "open, no password!"
    if 48 in ies:                                     # RSN: which kinds of login this network accepts
        rsn = ies[48]
        pairwise = struct.unpack_from("<H", rsn, 6)[0]
        akm_at = 8 + 4 * pairwise
        count = struct.unpack_from("<H", rsn, akm_at)[0]
        kinds = [rsn[akm_at + 2 + 4 * k + 3] for k in range(count)]
        security = " or ".join(AKM.get(k, f"type {k}") for k in kinds)
    generation = "Wi-Fi 6" if 255 in ies else "Wi-Fi 5" if 191 in ies else "Wi-Fi 4" if 45 in ies else "older"
    return ssid, channel, security, generation
# --8<-- [end:elements]


# --8<-- [start:frame]
def decode(frame):
    fc, flags = frame[0], frame[1]
    kind, sub = (fc >> 2) & 3, fc >> 4
    to_ds, from_ds, retry, protected = flags & 1, flags & 2, flags & 8, flags & 64
    name = TYPES.get((kind, sub), f"type {kind}/{sub}")
    a1 = frame[4:10]
    if kind == 1:                                     # control frames are tiny: just one or two addresses
        a2 = frame[10:16] if sub == 11 else None
        return name, (a2, a1, None), {}, retry, protected   # (from, to, via): an ACK doesn't even say who sent it
    a2, a3 = frame[10:16], frame[16:22]
    hdr = 24 + (6 if to_ds and from_ds else 0) + (2 if kind == 2 and sub & 8 else 0)
    ies = {}
    if kind == 0 and sub in (8, 5):
        ies = elements(frame[hdr + 12:])              # skip the timestamp, beacon interval and capabilities
    elif kind == 0 and sub in (0, 4):
        ies = elements(frame[hdr + (4 if sub == 0 else 0):])
    elif kind == 0 and sub == 11:
        ies = {"step": struct.unpack_from("<H", frame, hdr + 2)[0]}
    elif kind == 0 and sub == 1:
        ies = {"aid": struct.unpack_from("<H", frame, hdr + 4)[0] & 0x3FFF}
    elif kind == 2 and not protected and frame[hdr + 6:hdr + 8] == b"\x88\x8e":
        name = "key exchange (EAPOL)"
        key_info = struct.unpack_from(">H", frame, hdr + 8 + 5)[0]
        ies = {"message": 1 if key_info & 0x0080 and not key_info & 0x0100 else 2 if not key_info & 0x0080 and not key_info & 0x0200
               else 3 if key_info & 0x0080 else 4}
    # who's who depends on which way the frame is going (Chapter 19)
    if to_ds and not from_ds:
        who = (a2, a3, a1)                            # from a laptop, to someone beyond the access point a1
    elif from_ds and not to_ds:
        who = (a3, a1, a2)                            # from someone beyond the access point a2, to a1
    else:
        who = (a2, a1, a3)
    return name, who, ies, retry, protected
# --8<-- [end:frame]


def read_pcap(path):
    with open(path, "rb") as f:
        head = f.read(24)
        magic = struct.unpack("<I", head[:4])[0]
        if magic == 0x0A0D0D0A:
            raise SystemExit("That's pcapng. Convert it first: tcpdump -r in.pcapng -w out.pcap")
        endian = "<" if magic in (0xA1B2C3D4, 0xA1B23C4D) else ">"
        linktype = struct.unpack(endian + "I", head[20:24])[0]
        if linktype not in (105, 127):
            raise SystemExit(f"link type {linktype} isn't raw Wi-Fi. Capture in monitor mode (see the chapter).")
        while True:
            rec = f.read(16)
            if len(rec) < 16:
                return
            _, _, caplen, _ = struct.unpack(endian + "IIII", rec)
            data = f.read(caplen)
            yield (radiotap(data) if linktype == 127 else (0, None, None)), data


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", nargs="?")
    p.add_argument("-v", action="store_true")
    p.add_argument("--networks", action="store_true")
    p.add_argument("--make-sample", action="store_true")
    args = p.parse_args()
    if args.make_sample:
        return make_sample("air.pcap")
    if not args.file:
        return p.print_help()
    seen = {}
    for n, ((rlen, freq, signal), data) in enumerate(read_pcap(args.file), start=1):
        name, (src, dst, via), ies, retry, protected = decode(data[rlen:])
        radio = (f"{signal:>4} dBm" if signal is not None else "        ") + (f"  ch {channel_of(freq):<3}" if freq else "")
        if name in ("beacon", "probe response"):
            ssid, ch, security, gen = describe_network(ies)
            seen[mac(src)] = (ssid, ch, security, gen, signal)
            line = f"{name} from {mac(src)}: “{ssid}”, channel {ch}, {security}, {gen}"
        elif name == "probe request":
            ssid = ies.get(0, b"").decode(errors="replace")
            line = f"probe request from {mac(src)}: " + (f"“is {ssid} here?”" if ssid else "“is anyone here?”")
        elif name in ("ACK", "CTS"):
            line = f"{name} to {mac(dst)}"
        elif name == "authentication":
            line = f"authentication, step {ies['step']} of 2: {mac(src)} → {mac(dst)} (no password yet)"
        elif name == "association response":
            line = f"association response: {mac(src)} → {mac(dst)}: “welcome, you’re number {ies['aid']}”"
        elif name == "key exchange (EAPOL)":
            line = f"key exchange, message {ies['message']} of 4: {mac(src)} → {mac(dst)}"
        else:
            line = f"{name}: {mac(src)} → {mac(dst)}" + (f" (via {mac(via)})" if via and via != dst and via != src else "")
        if protected:
            line += ", encrypted"
        if retry:
            line += ", a RETRY"
        if not args.networks:
            print(f"{n:>3} {radio}  {line}")
            if args.v and ies and isinstance(next(iter(ies)), int):
                print("        elements: " + ", ".join(f"{k}({len(v)} bytes)" for k, v in sorted(ies.items())))
    if args.networks:
        print(f"{'signal':>7}  {'ch':>3}  {'network':<14} {'security':<22} {'generation'}")
        for bssid, (ssid, ch, security, gen, signal) in sorted(seen.items(), key=lambda kv: -(kv[1][4] or -999)):
            print(f"{signal:>4} dBm  {ch:>3}  {ssid:<14} {security:<22} {gen}")


# ---------------------------------------------------------------- a made-up capture to practise on

AP, LAPTOP, ROUTER = "14:c3:5e:40:0b:38", "e2:5f:b1:3c:77:0a", "14:c3:5e:40:0b:32"


def mb(text):
    return bytes(int(x, 16) for x in text.split(":"))


def rt(freq, signal):
    """A radiotap header with flags, rate, channel and signal."""
    band = 0x0080 if freq < 3000 else 0x0100                  # 2 GHz or 5 GHz, and OFDM (0x0040)
    return struct.pack("<BBHIBBHHb", 0, 0, 16, 0b101110, 0, 12, freq, 0x0040 | band, signal) + b"\0"


def ie(eid, value):
    return bytes([eid, len(value)]) + value


def rsn(akm):
    return struct.pack("<H4sH4sH4sH", 1, b"\x00\x0f\xac\x04", 1, b"\x00\x0f\xac\x04", 1, b"\x00\x0f\xac" + bytes([akm]), 0)


def mgmt(sub, dst, src, bssid, body, seq):
    return struct.pack("<BBH", sub << 4, 0, 0) + mb(dst) + mb(src) + mb(bssid) + struct.pack("<H", seq << 4) + body


def beacon(bssid, ssid, channel, akm=None, extras=b"", sub=8, dst="ff:ff:ff:ff:ff:ff"):
    fixed = struct.pack("<QHH", int(time.time() * 1e6), 100, 0x0411 if akm else 0x0401)
    body = fixed + ie(0, ssid.encode()) + ie(1, bytes([0x8c, 0x12, 0x98, 0x24, 0xb0, 0x48, 0x60, 0x6c])) + ie(3, bytes([channel]))
    if akm:
        body += ie(48, rsn(akm))
    return mgmt(sub, dst, bssid, bssid, body + extras, 100)


def make_sample(path):
    ht, vht, he = ie(45, bytes(26)), ie(191, bytes(12)), ie(255, bytes([35]) + bytes(20))
    f5, f24 = 5745, {1: 2412, 3: 2422, 6: 2437, 11: 2462}
    eapol = [bytes.fromhex(x) for x in ("0203005f02008a", "0103007502010a", "020300970213ca", "0103005f02030a")]
    frames = [
        (rt(f5, -40), beacon(AP, "HomeWiFi", 149, 2, ht + vht)),
        (rt(f24[3], -72), beacon("3c:7c:3f:12:34:56", "Flat 4B", 3, 2, ht)),
        (rt(f24[6], -61), beacon("a4:83:e7:65:43:21", "Cafe Guest", 6, None, ht + he)),
        (rt(f24[11], -64), beacon("00:1b:21:ab:cd:ef", "Neighbour", 11, 8, ht + he)),
        (rt(f5, -58), mgmt(4, "ff:ff:ff:ff:ff:ff", LAPTOP, "ff:ff:ff:ff:ff:ff", ie(0, b"") + ie(1, bytes([0x8c, 0x12])), 1)),
        (rt(f5, -40), beacon(AP, "HomeWiFi", 149, 2, ht + vht, sub=5, dst=LAPTOP)),
        (rt(f5, -40), struct.pack("<BBH", 0xd4, 0, 0) + mb(AP)),                                  # ACK
        (rt(f5, -58), mgmt(11, AP, LAPTOP, AP, struct.pack("<HHH", 0, 1, 0), 2)),                   # authentication
        (rt(f5, -40), mgmt(11, LAPTOP, AP, AP, struct.pack("<HHH", 0, 2, 0), 101)),
        (rt(f5, -58), mgmt(0, AP, LAPTOP, AP, struct.pack("<HH", 0x0411, 10) + ie(0, b"HomeWiFi") + ie(48, rsn(2)), 3)),
        (rt(f5, -40), mgmt(1, LAPTOP, AP, AP, struct.pack("<HHH", 0x0411, 0, 0xC003) + ie(1, bytes([0x8c])), 102)),
    ]
    for n, e in enumerate(eapol):
        from_ap = n % 2 == 0
        fc = struct.pack("<BB", 0x08, 0x02 if from_ap else 0x01)
        addrs = mb(LAPTOP) + mb(AP) + mb(AP) if from_ap else mb(AP) + mb(LAPTOP) + mb(AP)
        body = bytes.fromhex("aaaa03000000888e") + e[:4] + e[4:] + bytes(8)
        frames.append((rt(f5, -40 if from_ap else -58), fc + b"\0\0" + addrs + struct.pack("<H", (103 + n) << 4) + body))
    data_to_router = struct.pack("<BB", 0x88, 0x41) + b"\0\0" + mb(AP) + mb(LAPTOP) + mb(ROUTER) + struct.pack("<HH", 4 << 4, 0) + bytes(60)
    frames += [
        (rt(f5, -58), struct.pack("<BBH", 0xb4, 0, 300) + mb(AP) + mb(LAPTOP)),                   # RTS
        (rt(f5, -40), struct.pack("<BBH", 0xc4, 0, 280) + mb(LAPTOP)),                           # CTS
        (rt(f5, -58), data_to_router),
        (rt(f5, -40), struct.pack("<BBH", 0xd4, 0, 0) + mb(LAPTOP)),                             # ACK
        (rt(f5, -58), data_to_router[:1] + bytes([0x49]) + data_to_router[2:]),                   # the same, retried
    ]
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 127))
        t = time.time()
        for n, (radio, frame) in enumerate(frames):
            data = radio + frame
            f.write(struct.pack("<IIII", int(t), n * 1000, len(data), len(data)) + data)
    print(f"wrote {path}: {len(frames)} frames. Now try: python3 air.py {path}")


if __name__ == "__main__":
    main()
