#!/usr/bin/env python3
"""Generate chapter 44 figures.  python3 src/figs/ch44.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def box(x, y, w, h, cls="f-card", stroke="var(--line)", rx=8, dash=False, sw=1.6):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" class="{cls}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def line(x1, y1, x2, y2, cls="s-ink", w=2.2, arrow=False, dash=False):
    mk = f' marker-end="url(#ah-{"ink" if cls == "s-ink" else cls[2:]})"' if arrow else ""
    d = ' stroke-dasharray="5 4"' if dash else ""
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="{w}"{mk}{d}/>'


# ---------------------------------------------------------------- the lab's mesh, before and after (mesh.sh, real numbers)

def mesh():
    pos = {1: (140, 70), 2: (400, 70), 3: (400, 200), 4: (270, 290), 5: (110, 230)}
    links = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 1), (1, 3)]
    b = []
    for a, c in links:
        (x1, y1), (x2, y2) = pos[a], pos[c]
        weak = (a, c) == (1, 3)
        b.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="line s-muted" stroke-width="{2 if weak else 3}"' + (' stroke-dasharray="3 6"' if weak else "") + "/>")
    b.append(text(250, 150, "weak: 30% lost", "mid xs muted"))
    # step 1: via house 2
    b.append('<g data-show="=1">' + f'<path d="M140,70 L400,70 L400,200" class="line s-green" stroke-width="6" fill="none" opacity="0.8"/>' + "</g>")
    # step 2: house 2 down, via 5 and 4
    b.append('<g data-show="=2">' + f'<path d="M140,70 L110,230 L270,290 L400,200" class="line s-green" stroke-width="6" fill="none" opacity="0.8"/>'
             + '<path d="M388,58 l24,24 M412,58 l-24,24" class="line s-red" stroke-width="4"/>' + "</g>")
    for h, (x, y) in pos.items():
        cls = "t-yellow" if h == 5 else "f-card"
        b.append(f'<circle cx="{x}" cy="{y}" r="24" class="{cls}" stroke="var(--line)" stroke-width="1.6"/>')
        b.append(text(x, y + 5, f"house {h}" if h != 5 else "pub", "mid xs b"))
    b.append('<path d="M86,238 L40,262" class="line s-orange" stroke-width="3"/>')
    b.append(text(38, 280, "5G: the way out", "xs b f-orange"))
    # house 1's table
    b.append(box(470, 20, 240, 250, "f-surface", "var(--line)", 10))
    b.append(text(484, 42, "house 1’s choices for house 3", "xs b"))
    rows1 = [("via house 2", "220", True), ("via house 5", "194", False), ("direct (weak)", "145", False)]
    rows2 = [("via house 5", "198", True), ("direct (weak)", "(lower)", False), ("via house 2", "gone", False)]
    for step, rows in ((1, rows1), (2, rows2)):
        g = [f'<g data-show="={step}">']
        for i, (via, tq, best) in enumerate(rows):
            y = 70 + i * 30
            g.append(box(484, y - 16, 212, 24, "t-green" if best else "f-card", "var(--line)", 5, sw=1))
            g.append(text(494, y, ("★ " if best else "") + via, "xs" + (" b" if best else "")))
            g.append(text(686, y, tq, "end xs mono b" if best else "end xs mono"))
        g.append(text(484, 172, "quality out of 255, measured from", "xs muted"))
        g.append(text(484, 188, "how many of each house’s hellos", "xs muted"))
        g.append(text(484, 204, "get through, hop by hop", "xs muted"))
        g.append(text(484, 236 if step == 1 else 236, "two good hops beat one bad one" if step == 1 else "about 5 s of silence, then a new path", "xs b"))
        g.append("</g>")
        b.append("".join(g))
    steps = ["Every second, each house broadcasts a small “hello, I’m here” message, and every house passes on the ones it hears. From how many arrive through each neighbour, house 1 rates every path to house 3. The direct link across the green loses too much; two clean hops through house 2 are better.",
             "House 2’s radio breaks. Its hellos stop, and for about five seconds house 1’s pings go nowhere. Then the ratings catch up, and house 1 sends through the pub and house 4 instead: three hops, but three good ones."]
    svg = fig("".join(b), 720, 310, "Five houses in a mesh: the path from house 1 to house 3 goes via house 2, and after house 2 fails, via the pub and house 4",
              "This chapter’s lab, run on Grandpa’s Pi: the real ratings, from <code>batctl originators</code>.", steps)
    (OUT / "ch44-mesh.svg").write_text(svg)


# ---------------------------------------------------------------- 5G: radio, core as software, slices

def fiveg():
    b = []
    b.append(box(14, 110, 70, 40, "f-card"))
    b.append(text(49, 135, "phone", "mid xs b"))
    # antenna with beams
    b.append('<path d="M180,70 L180,180" class="line s-ink" stroke-width="4"/>')
    b.append(box(166, 60, 28, 36, "t-blue", "var(--blue)", 3))
    for k, (dx, dy) in enumerate(((-80, 55), (-90, 90), (-70, 125))):
        b.append(f'<path d="M166,78 Q{166 + dx / 2},{78 + dy / 2 - 12} {166 + dx},{78 + dy} Q{166 + dx / 2},{78 + dy / 2 + 8} 166,82 Z" class="t-blue" opacity="{0.9 if k == 1 else 0.35}"/>')
    b.append(text(180, 200, "base station", "mid xs b"))
    b.append(text(180, 214, "(gNB): beams aimed", "mid xs"))
    b.append(text(180, 228, "at each phone", "mid xs"))
    b.append(line(196, 80, 262, 80, "s-ink", 2, arrow=True))
    b.append(box(266, 30, 250, 170, "f-surface", "var(--line)", 12))
    b.append(text(391, 50, "the core: software, on ordinary servers", "mid xs b"))
    for i, (name, what) in enumerate((("AMF", "who you are, where you are"), ("SMF", "sets up your data sessions"), ("UPF", "the packets themselves: a router"))):
        y = 64 + i * 42
        b.append(box(282, y, 218, 34, "t-purple" if i < 2 else "t-green", "var(--purple)" if i < 2 else "var(--green)", 6))
        b.append(text(294, y + 21, name, "xs b"))
        b.append(text(334, y + 21, what, "xs"))
    b.append(line(516, 162, 580, 162, "s-green", 2.5, arrow=True))
    b.append(box(584, 138, 124, 48, "f-card"))
    b.append(text(646, 158, "the internet,", "mid xs b"))
    b.append(text(646, 174, "or a server nearby", "mid xs"))
    lanes = [("phones and video: fast", "t-blue"), ("a factory’s robots: quick and certain", "t-orange"), ("thousands of meters: cheap", "t-green")]
    b.append(text(14, 262, "network slices: one set of antennas and servers, run as separate networks with different promises", "xs b"))
    for i, (name, cls) in enumerate(lanes):
        b.append(box(14 + i * 234, 272, 222, 26, cls, "none", 6, sw=0))
        b.append(text(125 + i * 234, 289, name, "mid xs"))
    svg = fig("".join(b), 720, 306, "5G: a phone talks to a base station that aims radio beams, which connects to a core network made of software functions, and on to the internet; slices share it all",
              "5G, from the network’s point of view. The radio got cleverer; the big change is behind it, where the specialised boxes of older mobile networks became programs, run the way a cloud runs anything else (Chapter 39).")
    (OUT / "ch44-5g.svg").write_text(svg)


# ---------------------------------------------------------------- the latency budget: how far can the server be?

def edge():
    apps = [("a video call feels natural", 150), ("an online game feels fair", 50),
            ("a virtual-reality headset doesn’t make you queasy", 20), ("a factory robot arm stays in step", 5)]
    b = [text(20, 22, "if the round trip must be under…, the server can be at most this far away (light in fibre: 200 km per ms)", "xs b")]
    sc = 520 / 15000
    for i, (what, ms) in enumerate(apps):
        y = 42 + i * 52
        spare = ms - min(10, ms * 0.6)                       # leave time for the radio, queues and the server itself
        km = spare / 2 * 200
        b.append(text(20, y + 14, f"{ms} ms: {what}", "xs b"))
        b.append(box(20, y + 22, max(km * sc, 3), 16, "t-teal", "var(--teal)", 3, sw=1))
        b.append(text(26 + max(km * sc, 3), y + 35, f"{km:,.0f} km", "xs mono"))
    b.append(text(20, 42 + 4 * 52 + 12, "after allowing up to 10 ms for the radio, the queues and the server’s own work.  Real cables wander, so real distances are shorter.", "xs muted"))
    svg = fig("".join(b), 720, 42 + 4 * 52 + 24, "Bars: a 150 ms budget allows servers 14,000 km away, 50 ms 4,000 km, 20 ms 1,000 km, 5 ms only 200 km",
              "The latency budget. Past a certain point, speed isn’t the problem: distance is. The only way to answer in 5 ms is to be nearby: at the edge.")
    (OUT / "ch44-edge.svg").write_text(svg)


if __name__ == "__main__":
    mesh()
    fiveg()
    edge()
    print("wrote ch44 figures")
