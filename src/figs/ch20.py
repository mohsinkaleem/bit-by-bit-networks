#!/usr/bin/env python3
"""Generate chapter 20 figures.  python3 src/figs/ch20.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def bitrow(y, value, prefix, label, show="1", highlight=None):
    """32 little boxes for the bits of `value`, yellow for the network part and green for the host part."""
    out = [f'<g data-show="{show}">', text(116, y + 16, label, "end sm b")]
    for i in range(32):
        bit = value >> (31 - i) & 1
        x = 128 + i * 17.5 + (i // 8) * 6
        net = i < prefix
        cls = "t-yellow" if net else "t-green"
        out.append(f'<rect x="{x:.1f}" y="{y}" width="16" height="22" rx="2" class="{cls}"/>')
        out.append(text(x + 8, y + 16, str(bit), "mid mono sm b"))
    out.append("</g>")
    return "".join(out)


def ip(text_):
    a, b, c, d = map(int, text_.split("."))
    return a << 24 | b << 16 | c << 8 | d


# ---------------------------------------------------------------- the AND

def andfig():
    addr, mask = ip("192.168.1.3"), 0xFFFFFF00
    b = [text(128 + 4 * 17.5 + 2, 22, "192", "mid mono sm muted"), text(128 + 12 * 17.5 + 8, 22, "168", "mid mono sm muted"),
         text(128 + 20 * 17.5 + 14, 22, "1", "mid mono sm muted"), text(128 + 28 * 17.5 + 20, 22, "3", "mid mono sm muted")]
    b.append(bitrow(32, addr, 24, "192.168.1.3", "1"))
    b.append(bitrow(76, mask, 24, "255.255.255.0", "2"))
    b.append(f'<g data-show="3"><line x1="128" y1="110" x2="708" y2="110" class="line" stroke-width="2"/></g>')
    b.append(bitrow(118, addr & mask, 24, "192.168.1.0", "3"))
    b.append(f'<g data-show="1"><path d="M128,{168} L128,{176} L{128 + 24 * 17.5 + 12},{176} L{128 + 24 * 17.5 + 12},{168}" class="line s-yellow" stroke-width="2.5"/>'
             + text(128 + 12 * 17.5 + 6, 194, "network: 24 bits", "mid sm b", style="fill:var(--orange)")
             + f'<path d="M{128 + 24 * 17.5 + 18},{168} L{128 + 24 * 17.5 + 18},{176} L{128 + 32 * 17.5 + 18},{176} L{128 + 32 * 17.5 + 18},{168}" class="line s-green" stroke-width="2.5"/>'
             + text(128 + 28 * 17.5 + 18, 194, "host: 8 bits", "mid sm b f-green") + "</g>")
    steps = ["An IPv4 address is 32 bits, written as four bytes in decimal. <code>192.168.1.3/24</code> means the first 24 bits name the network, and the last 8 name one computer on it.",
             "The same split, written as a <strong>netmask</strong>: a 1 for every network bit, and a 0 for every host bit. 24 ones is <code>255.255.255.0</code>.",
             "AND them together, bit by bit: a 1 only where both have a 1. The host bits all become 0, and what’s left is the network’s own address, <code>192.168.1.0</code>. Every computer does this before sending every packet."]
    svg = fig("".join(b), 720, 206, "An IP address and its netmask in binary, combined with AND to give the network address",
              "Where the network part ends.", steps)
    (OUT / "ch20-and.svg").write_text(svg)


# ---------------------------------------------------------------- the whole address space

KINDS = {"private": ("t-green", "var(--green)", "private (for homes and offices)"),
         "special": ("t-orange", "var(--orange)", "loopback, “this network”, or partly special"),
         "multicast": ("t-purple", "var(--purple)", "multicast (groups)"),
         "reserved": ("f-line", "var(--muted)", "reserved, never used"),
         "public": ("t-blue", "var(--blue)", "public: handed out to the world")}
NOTES = {9: "IBM", 12: "AT&T", 17: "Apple", 18: "MIT", 19: "Ford", 44: "radio hams", 56: "US Post"}


def kind_of(n):
    if n == 10:
        return "private"
    if n in (172, 192):
        return "private"                          # 172.16/12 and 192.168/16 are inside these
    if n in (0, 127, 100, 169):
        return "special"
    if 224 <= n <= 239:
        return "multicast"
    if n >= 240:
        return "reserved"
    return "public"


def addrmap():
    b = [text(14, 22, "Every IPv4 address there is: 256 squares of 16.7 million each (a “/8”)", "sm b")]
    x0, y0, c = 14, 34, 25
    for n in range(256):
        r, col = divmod(n, 16)
        cls, stroke, _ = KINDS[kind_of(n)]
        x, y = x0 + col * c, y0 + r * c
        b.append(f'<rect x="{x}" y="{y}" width="{c - 2}" height="{c - 2}" rx="2" class="{cls}" stroke="{stroke}" stroke-width="1"/>')
        b.append(text(x + (c - 2) / 2, y + 16, str(n), "mid xs" + (" b" if n in NOTES or kind_of(n) != "public" else " muted")))
    # legend and notes on the right
    lx = x0 + 16 * c + 22
    for i, (k, (cls, stroke, label)) in enumerate(KINDS.items()):
        y = y0 + 6 + i * 26
        b.append(f'<rect x="{lx}" y="{y}" width="18" height="18" rx="3" class="{cls}" stroke="{stroke}"/>')
        b.append(text(lx + 26, y + 14, label, "xs"))
    notes = ["10: all of it is private (a whole /8!)", "172 and 192: only 172.16–172.31 and",
             "  192.168 are private; the rest is public", "127: loopback, always “this computer”",
             "100: 100.64–100.127 is for providers’ NAT", "169: 169.254 is link-local",
             "Some early owners (bold):", "9 IBM · 12 AT&T · 17 Apple · 18 MIT", "19 Ford · 44 radio hams · 56 US Post"]
    for i, line in enumerate(notes):
        b.append(text(lx, y0 + 160 + i * 17, line, "xs" + (" b" if line.startswith("Some") else "")))
    svg = fig("".join(b), 720, y0 + 16 * c + 12, "The IPv4 address space as a grid of 256 blocks, coloured by use: private, special, multicast, reserved and public",
              "The whole IPv4 internet on one page. Every public square has been handed out.")
    (OUT / "ch20-map.svg").write_text(svg)


# ---------------------------------------------------------------- the header

def header():
    rows = [
        [("version", 4, "4", "t-yellow"), ("header length", 4, "5", "t-yellow"), ("DSCP", 6, "0", "t-yellow"),
         ("ECN", 2, "0", "t-yellow"), ("total length", 16, "128 bytes", "t-yellow")],
        [("identification", 16, "29127", "t-orange"), ("flags", 3, "DF", "t-orange"), ("fragment offset", 13, "0", "t-orange")],
        [("time to live", 8, "64", "t-red"), ("protocol", 8, "6 = TCP", "t-yellow"), ("header checksum", 16, "0x06cd", "t-red")],
        [("source address", 32, "192.168.1.4", "t-blue")],
        [("destination address", 32, "188.184.67.127", "t-blue")],
    ]
    x0, w, h = 40, 640, 52
    b = []
    for i in range(0, 33, 8):
        b.append(text(x0 + i * w / 32, 22, str(i), "mid xs muted"))
    b.append(text(x0 + w / 2, 10, "bits →", "mid xs muted"))
    for r, row in enumerate(rows):
        y, bit = 30 + r * h, 0
        for name, width, value, cls in row:
            x, ww = x0 + bit * w / 32, width * w / 32
            b.append(f'<rect x="{x:.1f}" y="{y}" width="{ww:.1f}" height="{h - 4}" rx="4" class="{cls}" stroke="var(--line)" stroke-width="1.5"/>')
            b.append(text(x + ww / 2, y + 19, name, "mid xs b"))
            b.append(text(x + ww / 2, y + 36, value, "mid mono xs"))
            bit += width
        b.append(text(x0 - 8, y + 28, f"{r * 4}", "end xs muted"))
    b.append(text(x0 - 8, 22, "byte", "end xs muted"))
    notes = [("orange", "var(--orange)", "for chopping up and gluing back"), ("red", "var(--red)", "changed by every router"),
             ("blue", "var(--blue)", "the same end to end (until Chapter 22)")]
    for i, (name, colour, words) in enumerate(notes):
        b.append(f'<rect x="{x0 + i * 220}" y="{30 + 5 * h + 8}" width="14" height="14" rx="3" style="fill:{colour};opacity:0.5"/>')
        b.append(text(x0 + i * 220 + 20, 30 + 5 * h + 19, words, "xs"))
    svg = fig("".join(b), 720, 30 + 5 * h + 30, "The IPv4 header drawn 32 bits wide, with the values from the Pi's request to info.cern.ch",
              "The 20-byte IPv4 header, with the values from the Pi’s “GET /” in Chapter 16.")
    (OUT / "ch20-header.svg").write_text(svg)


# ---------------------------------------------------------------- chopped, and chopped again

def frag():
    scale = 0.165                                 # pixels per byte
    x0 = 170

    def piece(y, off, size, label, cls, stroke, step, last=False):
        x, w = x0 + off * scale, size * scale
        return (f'<g data-show="{step}"><rect x="{x:.1f}" y="{y}" width="{max(w, 3):.1f}" height="30" rx="3" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>'
                + (text(x + w / 2, y + 20, label, "mid xs b") if label else "") + "</g>")
    b = [text(x0 - 12, 58, "the ping", "end sm b"), text(x0 - 12, 128, "leaving the Pi", "end sm b"),
         text(x0 - 12, 192, "after the", "end sm b"), text(x0 - 12, 208, "1,492-byte link", "end sm b")]
    b.append(piece(40, 0, 3008, "3,008 bytes of ICMP: too big for one 1,500-byte frame", "t-purple", "var(--purple)", "1"))
    for off, size, lab in ((0, 1480, "offset 0: 1,480, more"), (1480, 1480, "offset 1480: 1,480, more"), (2960, 48, "")):
        b.append(piece(110, off, size, lab, "t-yellow", "var(--yellow)", "2"))
    b.append(f'<g data-show="2">{text(x0 + 3008 * scale + 10, 130, "48, last", "xs b")}</g>')
    for off, size, lab in ((0, 1472, "0: 1,472, more"), (1472, 8, ""), (1480, 1472, "1480: 1,472, more"), (2952, 8, ""), (2960, 48, "")):
        b.append(piece(180, off, size, lab, "t-orange", "var(--orange)", "3"))
    b.append(f'<g data-show="3">{text(x0 + 1476 * scale, 232, "8", "mid xs b f-red")}{text(x0 + 2956 * scale, 232, "8", "mid xs b f-red")}'
             f'{text(x0 + 3008 * scale + 10, 200, "48, last", "xs b")}</g>')
    b.append(f'<g data-show="4">{text(360, 262, "reassembled at the Pi: 3,008 bytes, checksum ✓", "mid hand f-green")}</g>')
    steps = ["The Pi pings 1.1.1.1 with 3,000 bytes of data. With the 8-byte ping header, that’s 3,008 bytes: far too big for one Ethernet frame, whose limit is 1,500 bytes including the 20-byte IP header.",
             "So the Pi cuts it into <strong>fragments</strong>. Each gets its own IP header, with the same identification number, the “more fragments” flag on all but the last, and an <strong>offset</strong> saying where its data belongs. The offset counts in units of 8 bytes, so every piece but the last holds a multiple of 8.",
             "The reply comes back from 1.1.1.1 in three pieces too, but somewhere on the way, a link with a limit of 1,492 bytes (the PPPoE connection from Chapter 18) can’t fit the two big ones. A router there cuts each of <em>them</em> in two: 1,472 bytes, and a tiny 8-byte leftover. Five fragments arrive.",
             "Only the final destination glues the pieces together, using the offsets, in whatever order they arrive. If even one piece is lost, the whole packet is thrown away after a timeout."]
    svg = fig("".join(b), 720, 276, "A 3,008-byte ping cut into three fragments by the Pi, and the reply's fragments cut again into five by a smaller link",
              "Real fragments, from a real ping: <code>ping -s 3000 1.1.1.1</code> on the Pi.", steps)
    (OUT / "ch20-frag.svg").write_text(svg)


if __name__ == "__main__":
    andfig()
    addrmap()
    header()
    frag()
    print("wrote ch20 figures")
