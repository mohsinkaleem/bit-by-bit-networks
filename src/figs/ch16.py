#!/usr/bin/env python3
"""Generate chapter 16 figures.  python3 src/figs/ch16.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def box(x, y, w, h, label, cls="f-card", stroke="var(--ink)", tcls="mid sm b", rx=8, sub=None):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}" stroke="{stroke}" stroke-width="2"/>']
    ty = y + h / 2 + (5 if not sub else -2)
    out.append(text(x + w / 2, ty, label, tcls))
    if sub:
        out.append(text(x + w / 2, ty + 15, sub, "mid xs muted"))
    return "".join(out)


def arrow(x1, y1, x2, y2, cls="s-ink", head="ink", width=2.5, extra=""):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="line {cls}" stroke-width="{width}" '
            f'marker-end="url(#ah-{head})"{extra}/>')


# ---------------------------------------------------------------- where the sniffer sits

def tap():
    b = [f'<rect x="170" y="14" width="420" height="332" rx="16" class="f-surface" stroke="var(--ink)" stroke-width="2"/>',
         text(380, 36, "Bob’s laptop", "mid slab b")]
    b.append(box(188, 50, 96, 44, "game", "t-purple", "var(--purple)"))
    b.append(box(296, 50, 96, 44, "browser", "t-purple", "var(--purple)"))
    b.append(box(446, 50, 126, 44, "tcpdump", "t-teal", "var(--teal-ink)", "mid mono sm b"))
    b.append('<line x1="180" y1="110" x2="580" y2="110" class="line s-muted dash" stroke-width="1.5"/>')
    b.append(text(600, 104, "programs", "xs muted"))
    b.append(text(600, 124, "the kernel", "xs muted"))
    b.append(box(188, 126, 204, 34, "TCP, UDP", "t-green", "var(--green)", sub=None))
    b.append(box(188, 172, 204, 34, "IP", "t-yellow", "var(--yellow)"))
    b.append(box(188, 262, 384, 30, "driver", "f-card", "var(--muted)"))
    b.append(box(188, 302, 384, 30, "Wi-Fi card", "t-blue", "var(--blue)"))
    # the tap
    b.append(f'<rect x="420" y="118" width="152" height="118" rx="10" class="t-orange" stroke="var(--orange)" stroke-width="2"/>')
    b.append(text(432, 134, "the tap (BPF)", "xs b"))
    b.append(box(434, 142, 124, 28, "buffer", "f-surface", "var(--orange)", "mid xs b"))
    b.append(box(434, 192, 124, 32, "filter program", "f-surface", "var(--orange)", "mid xs b"))
    # the normal path, up and down
    b.append(arrow(240, 302, 240, 294))
    b.append(arrow(240, 262, 240, 208))
    b.append(arrow(240, 172, 240, 162))
    b.append(arrow(236, 126, 236, 96))
    b.append(arrow(340, 96, 340, 126, "s-muted", "muted"))
    b.append(arrow(340, 162, 340, 172, "s-muted", "muted"))
    b.append(arrow(340, 206, 340, 260, "s-muted", "muted"))
    b.append(text(350, 238, "going out", "xs muted"))
    b.append(text(250, 238, "coming in", "xs"))
    # the copy
    b.append(arrow(496, 262, 496, 228, "s-orange", "orange", 3))
    b.append(text(504, 248, "a copy of", "xs f-orange b"))
    b.append(text(504, 259, "every one", "xs f-orange b"))
    b.append(arrow(496, 192, 496, 174, "s-orange", "orange", 3))
    b.append(text(504, 187, "match?", "xs f-orange b"))
    b.append(arrow(536, 142, 536, 98, "s-teal", "teal", 3))
    b.append(f'<path d="M558,208 L604,208" class="line s-muted" stroke-width="2" marker-end="url(#ah-muted)"/>')
    b.append(text(610, 205, "no match:", "xs muted"))
    b.append(text(610, 219, "skip it", "xs muted"))
    # outside
    b.append(f'<use href="#router" x="40" y="280" width="84" height="56"/>')
    b.append(text(82, 272, "home router", "mid xs b"))
    b.append('<path d="M124,317 L186,317" class="line s-muted dash" stroke-width="2.5"/>')
    b.append(text(154, 308, "radio", "mid xs muted"))
    svg = fig("".join(b), 720, 356, "Inside a laptop: packets pass the tap between the driver and IP; a filter picks which copies go up to tcpdump",
              "The tap sits just above the card’s driver. Every packet in or out passes it, and a small filter program decides which copies go up to <code>tcpdump</code>.")
    (OUT / "ch16-tap.svg").write_text(svg)


# ---------------------------------------------------------------- anatomy of one tcpdump line

def chips(y, parts, x0=14, labels_y=(0, 0)):
    """parts: (text, class, stroke, label lines, drop). Returns svg and the next x."""
    out, x = [], x0
    for txt, cls, stroke, label, drop in parts:
        w = len(txt) * 7.4 + 12 if txt.strip() else 14
        if cls:
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="28" rx="5" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        out.append(text(x + w / 2, y + 19, txt.replace("&", "&amp;"), "mid mono sm b" if cls else "mid mono sm"))
        if label:
            cx, ly = x + w / 2, y + 28 + drop
            out.append(f'<line x1="{cx:.1f}" y1="{y + 30}" x2="{cx:.1f}" y2="{ly + 2}" class="line s-muted" stroke-width="1.2"/>')
            for n, line in enumerate(label):
                out.append(text(cx, ly + 14 + n * 14, line, "mid xs" + (" b" if n == 0 else " muted")))
        x += w + 6
    return "".join(out)


def anatomy():
    grey, yel, grn = ("f-card", "var(--muted)"), ("t-yellow", "var(--yellow)"), ("t-green", "var(--green)")
    row1 = [("23:04:18.526572", *grey, ["captured at", "hours:minutes:seconds"], 6),
            ("IP", *yel, ["an IPv4 packet", "(Chapter 11)"], 44),
            ("192.168.1.4", *yel, ["from: the Pi’s", "address…"], 6),
            (".57426", *grn, ["…and port", "(Chapter 12)"], 44),
            (">", None, None, None, 0),
            ("188.184.67.127", *yel, ["to: info.cern.ch’s", "address…"], 6),
            (".80:", *grn, ["…port 80,", "the web"], 44)]
    row2 = [("Flags [S],", *grn, ["TCP flags:", "S = SYN, “hello”"], 6),
            ("seq 3208982406,", *grn, ["sequence number", "(Chapter 13)"], 44),
            ("win 64240,", *grn, ["window: room", "to receive"], 6),
            ("options [mss 1460,…],", *grn, ["extras, like the", "biggest piece it takes"], 44),
            ("length 0", *grn, ["bytes of data:", "none, yet"], 6)]
    b = chips(20, row1) + chips(150, row2)
    svg = fig(b, 720, 280, "One line of tcpdump output split into its parts: time, protocol, source and destination with ports, TCP flags, sequence number, window, options and length",
              "One line of <code>tcpdump</code>, taken apart. Yellow parts come from the IP header, green parts from TCP.")
    (OUT / "ch16-anatomy.svg").write_text(svg)


# ---------------------------------------------------------------- the filter program, step by step

PKT8 = bytes.fromhex("14c35e400b322ccf675e10c208004500008071c74000400606cdc0a80104bcb8437fe0520050"
                     "bf452f87d53656948018003f45d30000")
PROGRAM = ["(000) ldh      [12]",
           "(001) jeq      #0x800      jt 2   jf 10",
           "(002) ldb      [23]",
           "(003) jeq      #0x6        jt 4   jf 10",
           "(004) ldh      [20]",
           "(005) jset     #0x1fff     jt 10  jf 6",
           "(006) ldxb     4*([14]&0xf)",
           "(007) ldh      [x + 16]",
           "(008) jeq      #0x50       jt 9   jf 10",
           "(009) ret      #262144",
           "(010) ret      #0"]


def bpf():
    b = [text(16, 24, "tcpdump -d 'ip and tcp dst port 80'", "mono xs b"),
         text(372, 20, "packet 8: the Pi asks info.cern.ch for “/”", "xs b")]
    top, rh = 36, 27
    for n, line in enumerate(PROGRAM):
        y = top + n * rh
        b.append(f'<rect x="12" y="{y}" width="340" height="{rh - 3}" rx="4" class="f-card" stroke="var(--line)" stroke-width="1"/>')
        b.append(text(20, y + 17, line.replace(" ", "&#160;"), "mono xs"))
    # which instruction each step is on, what it reads, and the registers after it
    steps = [(0, [(12, 2)], "A = 0x0800", "X = 0"), (1, [], "A = 0x0800", "X = 0"),
             (2, [(23, 1)], "A = 6", "X = 0"), (3, [], "A = 6", "X = 0"),
             (4, [(20, 2)], "A = 0x4000", "X = 0"), (5, [], "A = 0x4000", "X = 0"),
             (6, [(14, 1)], "A = 0x4000", "X = 20"), (7, [(36, 2)], "A = 80", "X = 20"),
             (8, [], "A = 80", "X = 20"), (9, [], "A = 80", "X = 20")]
    for s, (pc, _, _, _) in enumerate(steps, start=1):
        y = top + pc * rh
        colour = "var(--green)" if pc == 9 else "var(--yellow)"
        b.append(f'<g data-show="={s}"><rect x="10" y="{y - 2}" width="344" height="{rh + 1}" rx="5" class="f-none" '
                 f'style="stroke:{colour}" stroke-width="3"/><path d="M2,{y + 6} l7,5 l-7,5 z" class="f-ink"/></g>')
    # packet bytes: 16 per row
    gx, gy, cw, ch = 372, 48, 20.8, 24
    for i, byte in enumerate(PKT8):
        r, c = divmod(i, 16)
        cls = "t-blue" if i < 14 else "t-yellow" if i < 34 else "t-green"
        b.append(f'<rect x="{gx + c * cw:.1f}" y="{gy + r * ch}" width="{cw - 2:.1f}" height="{ch - 2}" rx="3" class="{cls}"/>')
        b.append(text(gx + c * cw + (cw - 2) / 2, gy + r * ch + 16, f"{byte:02x}", "mid mono xs"))
    for c in range(0, 16, 4):
        b.append(text(gx + c * cw + 1, gy - 5, str(c), "xs muted"))
    b.append(text(gx + 6 * cw, gy + 4 * ch + 14, "frame", "xs b", style="fill:var(--blue)"))
    b.append(text(gx + 8.6 * cw, gy + 4 * ch + 14, "IP header", "xs b", style="fill:var(--orange)"))
    b.append(text(gx + 12.6 * cw, gy + 4 * ch + 14, "TCP header", "xs b", style="fill:var(--green)"))
    for s, (pc, reads, A, X) in enumerate(steps, start=1):
        g = [f'<g data-show="={s}">']
        for start, size in reads:
            for i in range(start, start + size):
                r, c = divmod(i, 16)
                g.append(f'<rect x="{gx + c * cw - 1:.1f}" y="{gy + r * ch - 1}" width="{cw:.1f}" height="{ch}" rx="4" '
                         f'class="f-none s-red" stroke-width="3"/>')
        g.append(f'<rect x="{gx}" y="{gy + 4 * ch + 30}" width="150" height="34" rx="6" class="f-card" stroke="var(--ink)" stroke-width="1.5"/>')
        g.append(text(gx + 12, gy + 4 * ch + 52, A, "mono sm b"))
        g.append(f'<rect x="{gx + 162}" y="{gy + 4 * ch + 30}" width="100" height="34" rx="6" class="f-card" stroke="var(--ink)" stroke-width="1.5"/>')
        g.append(text(gx + 174, gy + 4 * ch + 52, X, "mono sm b"))
        g.append("</g>")
        b.append("".join(g))
    b.append(text(gx, gy + 4 * ch + 84, "the two registers, after this step", "xs muted"))
    captions = [
        "<code>ldh [12]</code>: load 2 bytes from offset 12 into register A. That’s the frame’s “what’s inside” field: 0x0800, an IPv4 packet.",
        "<code>jeq #0x800</code>: is A equal to 0x0800? Yes, so carry on to instruction 2. (If not, jump to 10, which throws the packet away.)",
        "<code>ldb [23]</code>: load 1 byte from offset 23: the IP header’s “what’s inside” field. It’s 6, meaning TCP.",
        "<code>jeq #0x6</code>: TCP? Yes. A name lookup (UDP, 17) would fail right here and jump to 10.",
        "<code>ldh [20]</code>: load the IP header’s flags and fragment position. 0x4000 is just the “don’t chop me up” flag.",
        "<code>jset #0x1fff</code>: are any of the fragment-position bits set? No: this is a whole packet (or its first piece), so the TCP header is really here (Chapter 20).",
        "<code>ldxb 4*([14]&amp;0xf)</code>: IP headers can vary in length, so find where TCP starts. Byte 14 is 0x45, and 4 × 5 = 20 goes into register X.",
        "<code>ldh [x + 16]</code>: load 2 bytes at 14 + 20 + 2 = offset 36: the TCP destination port. 0x0050 is 80.",
        "<code>jeq #0x50</code>: port 80? Yes!",
        "<code>ret #262144</code>: keep it. The number is how many bytes of it to copy up to <code>tcpdump</code>, and 262,144 means “all of it”. Nine small steps, a few nanoseconds.",
    ]
    svg = fig("".join(b), 720, 344, "The compiled filter program for 'ip and tcp dst port 80', stepped through one real packet, highlighting the bytes each step reads",
              "The filter <code>ip and tcp dst port 80</code>, compiled by tcpdump, running on one real packet.", captions)
    (OUT / "ch16-bpf.svg").write_text(svg)


# ---------------------------------------------------------------- what can a sniffer see from here?

def laptop(x, y, label, sniff=False, side="below"):
    out = [f'<use href="#computer" x="{x - 24}" y="{y - 22}" width="48" height="43"/>']
    if side == "below":
        out.append(text(x, y + 36, label, "mid xs b"))
    else:
        out.append(text(x + 34, y - 2, label, "xs b"))
        out.append(text(x + 34, y + 12, "(sniffing)", "xs muted"))
    if sniff:
        out.append(f'<circle cx="{x + 22}" cy="{y - 18}" r="8" class="f-surface" stroke="var(--red)" stroke-width="3"/>'
                   f'<line x1="{x + 27}" y1="{y - 12}" x2="{x + 34}" y2="{y - 5}" class="line s-red" stroke-width="3.5"/>')
    return "".join(out)


def padlock(x, y):
    return (f'<g transform="translate({x - 7},{y - 9})"><rect x="0" y="6" width="14" height="11" rx="2" class="f-orange"/>'
            f'<path d="M3,6 v-3 a4,4 0 0 1 8,0 v3" class="line s-orange" stroke-width="2"/></g>')


def vantage():
    b = []
    for n, (title, device) in enumerate((("On a hub", "hub"), ("On a switch", "switch"), ("On Wi-Fi", "router"))):
        px = 8 + n * 240
        cx, ax, cxr = px + 112, px + 46, px + 178
        b.append(f'<rect x="{px}" y="8" width="224" height="300" rx="12" class="f-card" stroke="var(--line)" stroke-width="1.5"/>')
        b.append(text(cx, 32, title, "mid slab b"))
        if device == "router":
            b.append(f'<use href="#router" x="{cx - 34}" y="130" width="68" height="46"/>')
            for x2, y2 in ((cx, 102), (ax + 10, 212), (cxr - 10, 212)):
                b.append(f'<line x1="{cx}" y1="153" x2="{x2}" y2="{y2}" class="line s-muted dot-line" stroke-width="2"/>')
        else:
            b.append(f'<use href="#{device}" x="{cx - 50}" y="138" width="100" height="31"/>')
            b.append(f'<line x1="{cx}" y1="102" x2="{cx}" y2="138" class="wire" stroke-width="3"/>')
            b.append(f'<line x1="{ax}" y1="214" x2="{cx - 30}" y2="169" class="wire" stroke-width="3"/>')
            b.append(f'<line x1="{cxr}" y1="214" x2="{cx + 30}" y2="169" class="wire" stroke-width="3"/>')
        b.append(laptop(cx, 78, "Bob", sniff=True, side="right"))
        b.append(laptop(ax, 236, "Alice"))
        b.append(laptop(cxr, 236, "Carol"))
        # Alice → Carol, drawn beside the wires
        b.append(f'<path d="M{ax + 4},{202} L{cx - 36},{176}" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/>')
        b.append(f'<path d="M{cx + 36},{176} L{cxr - 4},{202}" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/>')
        if device == "hub":
            b.append(f'<path d="M{cx + 14},{134} L{cx + 14},{106}" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/>')
            b.append(text(cx, 286, "Bob sees everything,", "mid xs b"))
            b.append(text(cx, 300, "including Alice → Carol", "mid xs"))
        elif device == "switch":
            b.append(f'<path d="M{cx + 14},{134} L{cx + 14},{106}" class="line s-orange dash" stroke-width="2.5" marker-end="url(#ah-orange)"/>')
            b.append(text(cx + 22, 126, "“who has?”", "xs f-orange b"))
            b.append(text(cx, 286, "Bob sees only his own", "mid xs b"))
            b.append(text(cx, 300, "packets, and broadcasts", "mid xs"))
        else:
            b.append(f'<path d="M{cx + 14},{126} L{cx + 14},{106}" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/>')
            b.append(padlock((ax + cx - 32) / 2 - 10, 184))
            b.append(padlock((cx + cxr + 32) / 2 + 10, 184))
            b.append(padlock(cx + 30, 118))
            b.append(text(cx, 286, "Bob’s card hears it all,", "mid xs b"))
            b.append(text(cx, 300, "but each laptop has its own lock", "mid xs"))
    svg = fig("".join(b), 720, 316, "What a sniffer on Bob's laptop can see: everything on a hub, only its own traffic and broadcasts on a switch, and encrypted frames on Wi-Fi",
              "Where you sit decides what you can see.")
    (OUT / "ch16-vantage.svg").write_text(svg)


# ---------------------------------------------------------------- seven layers, five layers, and what tshark prints

def osi():
    osi_rows = ["7 Application", "6 Presentation", "5 Session", "4 Transport", "3 Network", "2 Data link", "1 Physical"]
    top, rh = 44, 34
    b = [text(90, 30, "OSI model", "mid slab b"), text(255, 30, "Internet model", "mid slab b"),
         text(440, 30, "tshark -V prints", "mid slab b"), text(632, 30, "People say…", "mid slab b")]
    colours = ["t-purple", "t-purple", "t-purple", "t-green", "t-yellow", "t-blue", "t-red"]
    strokes = ["var(--purple)"] * 3 + ["var(--green)", "var(--yellow)", "var(--blue)", "var(--red)"]
    for n, name in enumerate(osi_rows):
        y = top + n * rh
        b.append(f'<rect x="10" y="{y}" width="160" height="{rh - 4}" rx="6" class="{colours[n]}" stroke="{strokes[n]}" stroke-width="1.5"/>')
        b.append(text(22, y + 20, name, "sm b"))
    internet = [(0, 3, "Application"), (3, 1, "Transport"), (4, 1, "Internet"), (5, 1, "Link"), (6, 1, "Physical")]
    tshark = [(0, 3, "Hypertext Transfer Protocol"), (3, 1, "Transmission Control Protocol"), (4, 1, "Internet Protocol Version 4"),
              (5, 1, "Ethernet II"), (6, 1, "Frame 8: 142 bytes on wire")]
    says = [(0, 3, ["“a layer 7 firewall”", "(it reads the HTTP)"]), (3, 1, ["“a layer 4 load balancer”"]),
            (4, 1, ["“a layer 3 switch”", "(a router, really)"]), (5, 1, ["“a layer 2 switch”"]), (6, 1, ["“layer 1 problem”", "(a bad cable)"])]
    idx = {0: 0, 3: 3, 4: 4, 5: 5, 6: 6}
    for (start, span, name), (_, _, ts), (_, _, say) in zip(internet, tshark, says):
        y, h = top + start * rh, span * rh - 4
        cls, stroke = colours[idx[start]], strokes[idx[start]]
        b.append(f'<rect x="190" y="{y}" width="130" height="{h}" rx="6" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(text(255, y + h / 2 + 5, name, "mid sm b"))
        b.append(f'<rect x="336" y="{y}" width="208" height="{h}" rx="6" class="f-card" stroke="var(--line)" stroke-width="1.5"/>')
        b.append(text(346, y + h / 2 + 5, ts, "mono xs"))
        for k, line in enumerate(say):
            b.append(text(560, y + h / 2 + 5 - 7 * (len(say) - 1) + k * 14, line, "xs" + (" muted" if k else "")))
    b.append(text(360, top + 7 * rh + 18, "Layers 5 and 6 never really caught on as separate things. The numbers for 1 to 4, and 7, are used every day.", "mid xs muted"))
    svg = fig("".join(b), 720, top + 7 * rh + 30, "The seven OSI layers next to the five internet layers, with tshark's names for each, and common jargon",
              "The same stack, counted two ways. Engineers use the internet’s layers, with OSI’s numbers.")
    (OUT / "ch16-osi.svg").write_text(svg)


if __name__ == "__main__":
    tap()
    anatomy()
    bpf()
    vantage()
    osi()
    print("wrote ch16 figures")
