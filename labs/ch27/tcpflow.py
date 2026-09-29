#!/usr/bin/env python3
"""Chapter 27 lab: read a TCP conversation out of a capture, and explain every segment.

    python3 tcpflow.py example-org.pcap          Grandpa Otto's Pi fetching https://example.org
    python3 tcpflow.py example-org.pcap --raw    the real sequence numbers, not counted from zero
    python3 tcpflow.py yours.pcap                any capture of one TCP connection (tcpdump -w, Chapter 16)

It works out what tcpdump and Wireshark do: relative sequence numbers, which segments are
retransmissions, which acknowledgements are duplicates, and what the SACK blocks say.
"""
import argparse
import socket
import struct


def read_pcap(path):
    data = open(path, "rb").read()
    endian = "<" if data[:4] in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1") else ">"
    nano = data[:4] in (b"\x4d\x3c\xb2\xa1", b"\xa1\xb2\x3c\x4d")
    at = 24
    while at + 16 <= len(data):
        sec, frac, caplen, _ = struct.unpack(endian + "IIII", data[at:at + 16])
        yield sec + frac / (1e9 if nano else 1e6), data[at + 16:at + 16 + caplen]
        at += 16 + caplen


# --8<-- [start:parse]
FLAGS = [(0x02, "SYN"), (0x10, "ACK"), (0x08, "PSH"), (0x01, "FIN"), (0x04, "RST"), (0x20, "URG"), (0x40, "ECE"), (0x80, "CWR")]


def parse_tcp(frame):
    """Ethernet + IPv4 + TCP → a dict, or None if it isn't TCP."""
    if frame[12:14] != b"\x08\x00" or frame[23] != 6:
        return None
    ip = 14
    ihl = (frame[ip] & 15) * 4
    total = struct.unpack("!H", frame[ip + 2:ip + 4])[0]
    t = ip + ihl
    sport, dport, seq, ack, off, flags, win = struct.unpack("!HHIIBBH", frame[t:t + 16])
    hlen = (off >> 4) * 4                                  # header length, in 4-byte words
    seg = dict(src=(socket.inet_ntoa(frame[26:30]), sport), dst=(socket.inet_ntoa(frame[30:34]), dport),
               seq=seq, ack=ack, flags=flags, win=win, len=total - ihl - hlen, opts={}, sack=[])
    o, end = t + 20, t + hlen
    while o < end:                                         # options: kind, length, value
        kind = frame[o]
        if kind == 0:
            break
        if kind == 1:                                      # NOP: padding
            o += 1
            continue
        size = frame[o + 1]
        value = frame[o + 2:o + size]
        if kind == 2:
            seg["opts"]["mss"] = struct.unpack("!H", value)[0]
        elif kind == 3:
            seg["opts"]["wscale"] = value[0]
        elif kind == 4:
            seg["opts"]["sackOK"] = True
        elif kind == 5:
            seg["sack"] = [struct.unpack("!II", value[i:i + 8]) for i in range(0, len(value), 8)]
        elif kind == 8:
            seg["opts"]["ts"] = struct.unpack("!II", value)
        o += size
    return seg
# --8<-- [end:parse]


# --8<-- [start:analyse]
def analyse(segments, raw=False):
    first = segments[0][1]
    client, server = first["src"], first["dst"]
    names = {client: "Pi", server: "server"}
    isn = {}                                                # each side's first sequence number
    sent = {client: [], server: []}                         # byte ranges each side has sent so far
    holes = {client: [], server: []}                        # gaps the other side is still waiting for
    highest_ack = {client: None, server: None}
    t0 = segments[0][0]
    for t, s in segments:
        me, them = s["src"], s["dst"]
        if s["flags"] & 0x02:
            isn[me] = s["seq"]
        rel = (lambda n, side: n if raw else (n - isn.get(side, n)) % 2 ** 32)
        seq, ack = rel(s["seq"], me), rel(s["ack"], them)
        flags = ",".join(name for bit, name in FLAGS if s["flags"] & bit)
        notes = []
        if s["opts"]:
            notes.append(" ".join(f"{k} {v}" if v is not True else k for k, v in s["opts"].items() if k != "ts"))
        if s["len"]:
            span = (seq, seq + s["len"])
            top = max((b for _, b in sent[me]), default=None)
            if any(a <= span[0] and span[1] <= b for a, b in sent[me]):
                last = span[1] == top
                notes.append("RETRANSMISSION: these bytes were sent before"
                             + (" (the last segment, resent to provoke an ACK: a “tail loss probe”)" if last else ""))
            elif top is not None and span[0] > top:
                notes.append(f"a hole: bytes {top}-{span[0]} haven't arrived")
                holes[me].append((top, span[0]))
            for gap in holes[me]:
                if span[0] <= gap[0] and gap[1] <= span[1]:
                    notes.append(f"fills the hole {gap[0]}-{gap[1]}")
                    holes[me].remove(gap)
                    break
            sent[me].append(span)
        if s["flags"] & 0x10 and not s["len"] and not s["flags"] & 0x03:
            if highest_ack[me] is not None and ack == highest_ack[me] and not s["sack"]:
                notes.append("duplicate ACK")
        for left, right in s["sack"]:
            l, r = rel(left, them), rel(right, them)
            if r <= ack:
                notes.append(f"D-SACK {l}-{r}: “I got these twice”")
            else:
                notes.append(f"SACK {l}-{r}: “I have these, but not {ack}-{l}”")
        if s["flags"] & 0x10:
            highest_ack[me] = max(ack, highest_ack[me] or 0)
        data = f"{seq}:{seq + s['len']}" if s["len"] else f"{seq}"
        ackpart = f" ack {ack}" if s["flags"] & 0x10 else ""
        print(f"{(t - t0) * 1000:7.1f} ms  {names[me]:>6} → {names[them]:<6} [{flags:<11}] seq {data:<10}{ackpart:<10}"
              f" len {s['len']:<5} {'; '.join(notes)}")
# --8<-- [end:analyse]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pcap")
    p.add_argument("--raw", action="store_true")
    args = p.parse_args()
    segments = [(t, s) for t, frame in read_pcap(args.pcap) if (s := parse_tcp(frame))]
    if not segments:
        raise SystemExit("no TCP in that capture")
    c, sv = segments[0][1]["src"], segments[0][1]["dst"]
    print(f"a connection from {c[0]}:{c[1]} (“Pi”) to {sv[0]}:{sv[1]} (“server”), {len(segments)} segments\n")
    analyse(segments, args.raw)


if __name__ == "__main__":
    main()
