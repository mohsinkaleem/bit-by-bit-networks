#!/usr/bin/env python3
"""Generate chapter 17 figures.  python3 src/figs/ch17.py"""
import math
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- differential signalling

BITS = [1, 0, 1, 1, 0, 1, 0, 0]
X0, BW, N = 140, 56, 256          # track start, width per bit, samples


def samples(sign=1, noise=0.0):
    pts = []
    for i in range(N + 1):
        t = i / N * len(BITS)
        bit = BITS[min(int(t), len(BITS) - 1)]
        level = (1 if bit else -1) * sign
        bump = noise * math.exp(-((t - 3.5) ** 2) / 0.18)          # a burst of interference during bit 4
        pts.append(level + bump)
    return pts


def track(y, values, cls, amp=26):
    d = "M" + " L".join(f"{X0 + i / N * len(BITS) * BW:.1f},{y - v * amp:.1f}" for i, v in enumerate(values))
    return f'<path d="{d}" class="line {cls}" stroke-width="3"/>'


def guides(y, label, amp=26, top="+", bottom="−"):
    out = [f'<line x1="{X0}" y1="{y}" x2="{X0 + len(BITS) * BW}" y2="{y}" class="grid" stroke-dasharray="4 4"/>',
           text(X0 - 12, y + 5, label, "end sm b")]
    for i in range(len(BITS) + 1):
        out.append(f'<line x1="{X0 + i * BW}" y1="{y - amp - 8}" x2="{X0 + i * BW}" y2="{y + amp + 8}" class="grid"/>')
    return "".join(out)


def differential():
    b = []
    for i, bit in enumerate(BITS):
        b.append(text(X0 + i * BW + BW / 2, 22, str(bit), "mid mono b"))
    b.append(text(X0 - 12, 22, "bits sent", "end xs muted"))
    ya, yb, yr = 74, 158, 250
    b.append(guides(ya, "wire A"))
    # step 1: one wire, measured against ground, gets hit
    b.append(f'<g data-show="=1">{track(ya, samples(1, -1.6), "s-blue")}'
             f'<path d="M{X0 + 3.5 * BW - 14},{ya + 44} l10,-12 l-6,0 l10,-14" class="line s-orange" stroke-width="3"/>'
             + text(X0 + 3.5 * BW + 16, ya + 52, "interference!", "hand f-orange")
             + text(X0 + 3.5 * BW, 132, "✗ this 1 looks like a 0", "mid hand f-red") + "</g>")
    b.append(f'<g data-show="2">{guides(yb, "wire B")}</g>')
    b.append(f'<g data-show="=2">{track(ya, samples(1), "s-blue")}{track(yb, samples(-1), "s-purple")}</g>')
    b.append(f'<g data-show="3">{track(ya, samples(1, -1.6), "s-blue")}{track(yb, samples(-1, -1.6), "s-purple")}'
             f'<path d="M{X0 + 3.5 * BW - 14},{ya + 44} l10,-12 l-6,0 l10,-14" class="line s-orange" stroke-width="3"/>'
             f'<path d="M{X0 + 3.5 * BW - 14},{yb + 44} l10,-12 l-6,0 l10,-14" class="line s-orange" stroke-width="3"/>'
             + text(X0 + len(BITS) * BW + 12, (ya + yb) / 2 + 5, "the same dip", "hand f-orange")
             + text(X0 + len(BITS) * BW + 12, (ya + yb) / 2 + 25, "on both", "hand f-orange") + "</g>")
    diff = [a - c for a, c in zip(samples(1, -1.6), samples(-1, -1.6))]
    b.append(f'<g data-show="4">{guides(yr, "A − B", 18)}{track(yr, diff, "s-green", 18)}'
             + text(X0 + len(BITS) * BW + 12, yr + 5, "clean, and", "hand f-green")
             + text(X0 + len(BITS) * BW + 12, yr + 25, "twice as big", "hand f-green") + "</g>")
    steps = ["One wire, measured against the ground. A burst of interference from a nearby power cable pushes the voltage down in the middle of a 1, and the receiver reads a 0.",
             "Use a <em>pair</em> of wires instead. Wire A carries the signal, and wire B carries its mirror image: when A goes up, B goes down.",
             "The two wires are twisted tightly together, so they’re always in almost the same place. Interference pushes both of them the same way, by the same amount.",
             "The receiver only looks at the <em>difference</em> between the two wires. The interference is in both, so it cancels out, and the signal comes out twice as big."]
    svg = fig("".join(b), 720, 292, "Differential signalling: a noise burst corrupts a single wire, but cancels out when the receiver subtracts one wire of a twisted pair from the other",
              "Why every network cable is made of twisted pairs.", steps)
    (OUT / "ch17-twist.svg").write_text(svg)


# ---------------------------------------------------------------- inside the cable

PINS = [("white-orange", "var(--orange)", True), ("orange", "var(--orange)", False), ("white-green", "var(--green)", True),
        ("blue", "var(--blue)", False), ("white-blue", "var(--blue)", True), ("green", "var(--green)", False),
        ("white-brown", "var(--copper)", True), ("brown", "var(--copper)", False)]


def rj45():
    b = [text(170, 24, "An RJ45 plug, from the front (T568B)", "mid sm b")]
    x0, pw = 50, 30
    b.append(f'<rect x="{x0 - 16}" y="36" width="{8 * pw + 32}" height="150" rx="10" class="f-card" stroke="var(--ink)" stroke-width="2"/>')
    b.append(f'<rect x="{x0 + 70}" y="186" width="{8 * pw - 140}" height="20" rx="4" class="f-card" stroke="var(--ink)" stroke-width="2"/>')
    for i, (name, colour, striped) in enumerate(PINS):
        x = x0 + i * pw + 4
        b.append(f'<rect x="{x}" y="54" width="{pw - 8}" height="92" rx="3" fill="{colour}" '
                 + ('style="opacity:0.35"' if striped else '') + '/>')
        if striped:
            for k in range(6):
                b.append(f'<rect x="{x}" y="{58 + k * 15}" width="{pw - 8}" height="6" fill="{colour}"/>')
        b.append(text(x + (pw - 8) / 2, 164, str(i + 1), "mid mono sm b"))
    pairs = [("pair 2", 0, 1, "var(--orange)"), ("pair 3", 2, 5, "var(--green)"), ("pair 1", 3, 4, "var(--blue)"), ("pair 4", 6, 7, "var(--copper)")]
    # brackets under the pins
    for n, (name, a, c, colour) in enumerate(pairs):
        y = 222 + n * 16
        xa, xc = x0 + a * pw + 15, x0 + c * pw + 15
        b.append(f'<path d="M{xa},{y - 6} L{xa},{y} L{xc},{y} L{xc},{y - 6}" class="line" style="stroke:{colour}" stroke-width="2.5"/>')
        b.append(text(xc + 10, y + 4, name, "xs b", style=f"fill:{colour}"))
    # the right-hand side: who uses what
    rows = [("10 and 100 Mb/s", "pairs 2 and 3 only: one pair each way", "var(--orange)"),
            ("1 Gb/s", "all four pairs, both directions at once", "var(--green)"),
            ("10 Gb/s", "all four pairs, both ways, 16 voltage levels", "var(--blue)")]
    b.append(text(360, 54, "Which pairs carry what", "sm b"))
    for n, (speed, what, colour) in enumerate(rows):
        y = 78 + n * 50
        b.append(f'<rect x="360" y="{y}" width="340" height="40" rx="6" class="f-card" style="stroke:{colour}" stroke-width="2"/>')
        b.append(text(372, y + 17, speed, "sm b"))
        b.append(text(372, y + 33, what, "xs"))
    b.append(text(360, 252, "Each pair is twisted at a different rate, so that", "xs muted"))
    b.append(text(360, 266, "the pairs don’t pick up each other’s signals.", "xs muted"))
    svg = fig("".join(b), 720, 290, "An RJ45 connector with eight colour-coded pins in four twisted pairs, and which pairs each Ethernet speed uses",
              "Eight wires, four twisted pairs. Faster Ethernet uses more of them, in both directions at once.")
    (OUT / "ch17-rj45.svg").write_text(svg)


# ---------------------------------------------------------------- more levels, more bits

def levels():
    bits = "1100100111100001"
    rows = [(2, "2 levels", "1 bit per symbol", "16 symbols"), (4, "4 levels", "2 bits per symbol", "8 symbols"),
            (16, "16 levels", "4 bits per symbol", "4 symbols")]
    b = [text(360, 20, "The same 16 bits, " + " ".join(bits[i:i + 4] for i in range(0, 16, 4)) + ", sent three ways", "mid sm b")]
    x0, width, amp = 200, 500, 30
    for n, (L, name, per, count) in enumerate(rows):
        yc = 86 + n * 106
        k = int(math.log2(L))
        symbols = [int(bits[i:i + k], 2) for i in range(0, 16, k)]
        sw = width / len(symbols)
        b.append(text(14, yc - 6, name, "slab b"))
        b.append(text(14, yc + 12, per, "xs"))
        b.append(text(14, yc + 28, count, "xs muted"))
        for lv in range(L):
            y = yc + amp - lv * 2 * amp / (L - 1)
            b.append(f'<rect x="{x0}" y="{y - amp / (L - 1) * 0.55:.1f}" width="{width}" height="{amp / (L - 1) * 1.1:.1f}" class="t-orange" style="opacity:0.55"/>')
            b.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + width}" y2="{y:.1f}" class="grid"/>')
        d = []
        for i, sym in enumerate(symbols):
            y = yc + amp - sym * 2 * amp / (L - 1)
            d.append(f"{'M' if i == 0 else 'L'}{x0 + i * sw:.1f},{y:.1f} L{x0 + (i + 1) * sw:.1f},{y:.1f}")
            if L > 2:
                b.append(text(x0 + i * sw + sw / 2, yc - amp - 6, bits[i * k:(i + 1) * k], "mid mono xs muted"))
        b.append(f'<path d="{" ".join(d)}" class="line s-blue" stroke-width="3"/>')
        b.append(text(x0 - 10, yc + amp + 4, "−1 V", "end xs muted"))
        b.append(text(x0 - 10, yc - amp + 8, "+1 V", "end xs muted"))
    b.append(text(450, 378, "Orange bands: how far noise can push a level before it’s mistaken for its neighbour.", "mid xs muted"))
    svg = fig("".join(b), 720, 390, "The same 16 bits sent with 2, 4 and 16 voltage levels: fewer symbols are needed, but the levels get closer together",
              "More levels carry more bits in each symbol, but leave less room for noise.")
    (OUT / "ch17-levels.svg").write_text(svg)


# ---------------------------------------------------------------- glass

def fiber():
    b = [text(20, 24, "Light bounces along the core, trapped by the cladding around it", "sm b")]
    y0, y1 = 60, 140
    b.append(f'<rect x="80" y="{y0 - 18}" width="560" height="{y1 - y0 + 36}" rx="{(y1 - y0 + 36) / 2}" class="t-teal" stroke="var(--teal)" stroke-width="2"/>')
    b.append(f'<rect x="80" y="{y0}" width="560" height="{y1 - y0}" class="t-blue" stroke="var(--blue)" stroke-width="1.5"/>')
    pts, x, up = [(84, 100)], 84, True
    while x < 620:
        x = min(x + 64, 632)
        pts.append((x, y0 + 3 if up else y1 - 3))
        up = not up
    b.append(f'<path d="M{" L".join(f"{px},{py}" for px, py in pts)}" class="line s-red" stroke-width="3" marker-end="url(#ah-red)"/>')
    b.append(f'<rect x="20" y="82" width="56" height="36" rx="6" class="f-card" stroke="var(--ink)" stroke-width="2"/>')
    b.append(text(48, 105, "laser", "mid xs b"))
    b.append(f'<rect x="644" y="82" width="62" height="36" rx="6" class="f-card" stroke="var(--ink)" stroke-width="2"/>')
    b.append(text(675, 105, "detector", "mid xs b"))
    for lx, cls, stroke, label in ((150, "t-blue", "var(--blue)", "core: the glass the light travels in"),
                                   (420, "t-teal", "var(--teal)", "cladding: different glass, which reflects it back")):
        b.append(f'<rect x="{lx}" y="170" width="16" height="12" rx="2" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(text(lx + 22, 180, label, "xs"))
    # cross sections
    for cx, core, name, sub, sub2 in ((130, 25, "multimode", "50 µm core, cheap:", "a few hundred metres"),
                                      (440, 5, "single-mode", "9 µm core, one clean path:", "100 km and more")):
        b.append(f'<circle cx="{cx}" cy="240" r="38" class="t-teal" stroke="var(--teal)" stroke-width="2"/>')
        b.append(f'<circle cx="{cx}" cy="240" r="{core}" class="f-blue"/>')
        b.append(text(cx + 52, 228, name, "sm b"))
        b.append(text(cx + 52, 244, sub, "xs"))
        b.append(text(cx + 52, 258, sub2, "xs"))
    b.append(text(360, 304, "(A human hair is about 70 µm thick. The cladding of both is 125 µm across.)", "mid xs muted"))
    svg = fig("".join(b), 720, 316, "Light travelling along an optical fibre by reflecting off the boundary between core and cladding, and cross-sections of multimode and single-mode fibre",
              "Glass instead of copper: pulses of light, trapped inside a thread thinner than a hair.")
    (OUT / "ch17-fiber.svg").write_text(svg)


# ---------------------------------------------------------------- how long is a packet?

def packets():
    b = [text(20, 24, "A 1,500-byte packet, stretched out along the fiber from Mumbai to Geneva", "sm b")]
    rows = [("10 Mb/s", 245, "each packet is 245 km of light: about 27 fit end to end", 1),
            ("1 Gb/s", 2.45, "each packet is 2.4 km of light: about 2,700 fit", 100),
            ("100 Gb/s", 0.0245, "each packet is 24 metres of light: about 275,000 fit", 10000)]
    x0, x1, km = 110, 690, 6721
    scale = (x1 - x0) / km
    for n, (speed, plen, note, zoom) in enumerate(rows):
        y = 56 + n * 96
        yl = y + 18
        b.append(text(14, yl + 5, speed, "sm b"))
        b.append(text(x0, y, note, "xs"))
        w = plen * scale
        if zoom == 1:
            for i in range(int(km / plen)):
                b.append(f'<rect x="{x0 + i * w:.1f}" y="{yl - 7}" width="{w - 1.5:.1f}" height="14" rx="2" class="f-blue"/>')
        else:
            b.append(f'<line x1="{x0}" y1="{yl}" x2="{x1}" y2="{yl}" class="line s-blue" stroke-width="14" style="opacity:0.8"/>')
            zx, zy, zw = x0 + 150, yl + 18, 300
            b.append(f'<rect x="{x0 - 1}" y="{yl - 9}" width="6" height="18" class="f-none s-red" stroke-width="2"/>')
            b.append(f'<path d="M{x0 + 5},{yl + 9} L{zx},{zy} M{x0 - 1},{yl + 9} L{zx - 1},{zy + 24}" class="line s-red" stroke-width="1" style="opacity:0.6"/>')
            b.append(f'<rect x="{zx}" y="{zy}" width="{zw}" height="24" rx="3" class="f-surface s-red" stroke-width="2"/>')
            zwid = w * zoom
            i = 0
            while (i + 1) * zwid <= zw - 4:
                b.append(f'<rect x="{zx + 3 + i * zwid:.1f}" y="{zy + 5}" width="{zwid - 1.5:.1f}" height="14" rx="2" class="f-blue"/>')
                i += 1
            b.append(text(zx + zw + 10, zy + 17, f"zoomed in {zoom:,}×", "xs f-red b"))
    b.append(text(x0, 344, "Mumbai", "xs b"))
    b.append(text(x1, 344, "Geneva, 6,721 km", "end xs b"))
    b.append(text(360, 372, "Faster links don’t make light go faster. They just make each packet shorter.", "mid hand"))
    svg = fig("".join(b), 720, 384, "At 10 megabits a packet is 245 km long; at 1 gigabit, 2.4 km; at 100 gigabits, 24 metres; the light takes the same time either way",
              "Bandwidth is how short each packet is. Latency is how long the road is.")
    (OUT / "ch17-packets.svg").write_text(svg)


# ---------------------------------------------------------------- how loud is the Wi-Fi?

def dbm():
    b = [text(20, 24, "Wi-Fi signal strength, in dBm (every 10 dBm down is 10 times weaker)", "sm b")]
    top, bottom, lo, hi = 50, 330, -100, -20
    x = 236

    def y(v):
        return top + (hi - v) / (hi - lo) * (bottom - top)
    b.append(f'<rect x="{x - 12}" y="{top}" width="24" height="{bottom - top}" rx="12" class="t-green"/>')
    for v in range(-100, -19, 10):
        b.append(f'<line x1="{x - 18}" y1="{y(v):.1f}" x2="{x - 12}" y2="{y(v):.1f}" class="line s-muted" stroke-width="1.5"/>')
        b.append(text(x - 24, y(v) + 4, f"{v}", "end xs muted"))
    zones = [(-20, -50, "var(--green)", "excellent"), (-50, -67, "var(--teal)", "good: video calls work"),
             (-67, -80, "var(--yellow)", "patchy"), (-80, -100, "var(--red)", "unusable")]
    for a, c, colour, name in zones:
        b.append(f'<rect x="{x - 12}" y="{y(a):.1f}" width="24" height="{y(c) - y(a):.1f}" style="fill:{colour};opacity:0.55"/>')
        b.append(text(x - 58, (y(a) + y(c)) / 2 + 4, name, "end xs b", style=f"fill:{colour}"))
    marks = [(-40, "Grandpa Otto’s Pi, next to the router"), (-58, "Bob’s laptop, two rooms away"),
             (-95, "the noise: background radio hiss")]
    for v, label in marks:
        b.append(f'<line x1="{x + 14}" y1="{y(v):.1f}" x2="{x + 60}" y2="{y(v):.1f}" class="line" stroke-width="2"/>')
        b.append(f'<circle cx="{x}" cy="{y(v):.1f}" r="6" class="f-ink"/>')
        b.append(text(x + 68, y(v) + 5, f"{v} dBm: {label}", "sm"))
    ax = 640
    b.append(f'<path d="M{ax},{y(-58) + 8:.1f} L{ax},{y(-95) - 8:.1f}" class="line s-purple" stroke-width="3" '
             f'marker-start="url(#ah-purple)" marker-end="url(#ah-purple)"/>')
    b.append(text(ax - 12, y(-72), "37 dB apart:", "end sm b", style="fill:var(--purple)"))
    b.append(text(ax - 12, y(-72) + 17, "the signal is 5,000×", "end xs"))
    b.append(text(ax - 12, y(-72) + 31, "stronger than the noise", "end xs"))
    svg = fig("".join(b), 720, 344, "A scale of Wi-Fi signal strengths from -20 to -100 dBm, marking the Pi at -38, a laptop at -58 and the noise floor at -95",
              "−58 dBm is about 0.0000016 milliwatts: the laptop’s receiver is listening to a billionth of a watt.")
    (OUT / "ch17-dbm.svg").write_text(svg)


if __name__ == "__main__":
    differential()
    rj45()
    levels()
    fiber()
    packets()
    dbm()
    print("wrote ch17 figures")
