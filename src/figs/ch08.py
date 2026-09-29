#!/usr/bin/env python3
"""Generate chapter 8 figures.  python3 src/figs/ch08.py"""
import math
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent
HEADS = ["alice", "bob", "carol", "dave", "eve", "alice"]


def mesh():
    body = []
    panels = [(2, 90), (3, 250), (4, 410), (6, 590)]
    for n, cx in panels:
        cy, r = 100, 58 if n > 2 else 50
        pts = [(cx + r * math.cos(2 * math.pi * i / n - math.pi / 2), cy + r * math.sin(2 * math.pi * i / n - math.pi / 2)) for i in range(n)]
        if n == 2:
            pts = [(cx - 48, cy), (cx + 48, cy)]
        for i in range(n):
            for j in range(i + 1, n):
                body.append(f'<line x1="{pts[i][0]:.0f}" y1="{pts[i][1]:.0f}" x2="{pts[j][0]:.0f}" y2="{pts[j][1]:.0f}" class="wire" stroke-width="2.5"/>')
        for i, (x, y) in enumerate(pts):
            body.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="17" class="box"/>')
            body.append(f'<use href="#{HEADS[i]}-head" x="{x - 15:.0f}" y="{y - 15:.0f}" width="30" height="30"/>')
        wires = n * (n - 1) // 2
        body.append(text(cx, 196, f"{n} computers", "mid sm b"))
        body.append(text(cx, 216, f"{wires} wire{'s' if wires > 1 else ''}", "mid hand lg f-red"))
    body.append(text(360, 252, "10 computers: 45 wires.  100 computers: 4,950 wires, and 99 network cards in every one.", "mid sm"))
    svg = fig("".join(body), 720, 266, "Connecting every pair of computers directly needs a fast-growing number of wires",
              "A private wire between every pair gets out of hand fast.")
    (OUT / "ch08-mesh.svg").write_text(svg)


def bus():
    body = ['<line x1="40" y1="150" x2="680" y2="150" class="wire" stroke-width="7"/>',
            '<rect x="24" y="140" width="16" height="20" rx="3" class="f-ink"/><rect x="680" y="140" width="16" height="20" rx="3" class="f-ink"/>',
            text(32, 182, "end cap", "mid xs muted"), text(688, 182, "end cap", "mid xs muted")]
    names = [("alice", "Alice", "0a:11"), ("bob", "Bob", "0b:22"), ("carol", "Carol", "0c:33"), ("dave", "Dave", "0d:44"), ("eve", "Eve", "0e:99")]
    for i, (sid, name, mac) in enumerate(names):
        x = 110 + i * 125
        body.append(f'<line x1="{x}" y1="96" x2="{x}" y2="146" class="wire" stroke-width="3"/>')
        body.append(f'<circle cx="{x}" cy="150" r="6" class="f-copper"/>')
        body.append(f'<use href="#{sid}-head" x="{x - 28}" y="30" width="56" height="56"/>')
        body.append(text(x, 108, name, "mid slab b sm halo"))
        body.append(text(x, 124, mac, "mid mono xs halo"))
    for d, cls in ((-1, "f-green"), (1, "f-green")):
        body.append(f'<g><circle r="8" class="{cls}"><animateMotion dur="2.4s" repeatCount="indefinite" path="M360,150 L{360 + d * 320},150"/></circle>'
                    f'<circle r="8" class="{cls}"><animateMotion dur="2.4s" begin="0.6s" repeatCount="indefinite" path="M360,150 L{360 + d * 320},150"/></circle></g>')
    body.append(text(360, 214, "Carol sends: the signal spreads both ways and every card hears it", "mid hand lg"))
    svg = fig("".join(body), 720, 232, "Five computers tapped into one long shared cable",
              "One cable, everyone clipped on. Cheap, simple, and nobody has any privacy.")
    (OUT / "ch08-bus.svg").write_text(svg)


def frame_layout():
    parts = [("preamble", "10101010…", "7", "t-purple"), ("start", "10101011", "1", "t-purple"),
             ("to", "0b:22:…", "6", "t-blue"), ("from", "0a:11:…", "6", "t-blue"), ("type", "what’s inside", "2", "t-green"),
             ("data", "the message itself", "46–1500", "t-yellow"), ("check", "Ch. 10!", "4", "t-red")]
    widths = [86, 76, 84, 84, 96, 170, 76]
    x = 14
    body = []
    for (name, sub, size, cls), w in zip(parts, widths):
        body.append(f'<rect x="{x}" y="36" width="{w}" height="62" rx="6" class="{cls}" stroke="var(--line)"/>')
        body.append(text(x + w / 2, 60, name, "mid slab b"))
        body.append(text(x + w / 2, 82, sub, "mid mono xs"))
        body.append(text(x + w / 2, 118, f"{size} bytes", "mid xs muted"))
        x += w + 2
    body.append('<path d="M14,134 L14,142 L178,142 L178,134" class="line s-purple"/>')
    body.append(text(96, 162, "get in step (Ch. 2)", "mid hand f-purple"))
    body.append('<path d="M180,134 L180,142 L350,142 L350,134" class="line s-blue"/>')
    body.append(text(265, 162, "card addresses", "mid hand f-blue"))
    svg = fig("".join(body), 720, 176, "Layout of a frame: preamble, start marker, destination, source, type, data, check",
              "Our new frame. Every card reads the “to” field and decides whether to keep going.")
    (OUT / "ch08-frame.svg").write_text(svg)


def spacetime():
    xa, xd, top, tau = 110, 610, 70, 110
    body = [f'<line x1="{xa}" y1="{top - 10}" x2="{xa}" y2="{top + 400}" class="line s-muted" stroke-dasharray="2 5"/>',
            f'<line x1="{xd}" y1="{top - 10}" x2="{xd}" y2="{top + 400}" class="line s-muted" stroke-dasharray="2 5"/>',
            f'<use href="#alice-head" x="{xa - 24}" y="4" width="48" height="48"/>',
            f'<use href="#dave-head" x="{xd - 24}" y="4" width="48" height="48"/>',
            text(xa, top - 14, "Alice (one end)", "mid sm b"), text(xd, top - 14, "Dave (far end)", "mid sm b"),
            f'<path d="M{xa + 30},{top + 390} L{xd - 30},{top + 390}" class="line thin s-muted" marker-end="url(#ah-muted)" marker-start="url(#ah-muted)"/>',
            text((xa + xd) / 2, top + 406, "distance along the cable", "mid xs muted"),
            text(40, top + 200, "time ↓", "mid xs muted")]
    eps = 12

    def band(x0, x1, t0, dur, cls, show, label=None):
        y0 = top + t0
        pts = f"{x0},{y0} {x1},{y0 + tau} {x1},{y0 + tau + dur} {x0},{y0 + dur}"
        out = f'<polygon points="{pts}" class="{cls}" opacity="0.3" stroke="var(--ink)" stroke-width="1"/>'
        if label:
            out += text(x0 + (14 if x1 > x0 else -14), y0 + 18, label, ("start" if x1 > x0 else "end") + " sm b halo")
        return f'<g data-show="{show}">{out}</g>'

    # step 1: long frame from Alice, Dave starts just before it reaches him
    body.append(band(xa, xd, 0, 290, "f-red", "=1", "Alice’s frame"))
    body.append(band(xd, xa, tau - eps, 120, "f-blue", "=1", "Dave starts"))
    body.append(f'<g data-show="=1"><circle cx="{xd - 8}" cy="{top + tau - 4}" r="11" class="f-yellow" stroke="var(--ink)"/>'
                f'<text x="{xd - 8}" y="{top + tau + 1}" class="mid xs b">💥</text>'
                f'<path d="M{xa + 14},{top + 2 * tau - eps} l40,-10" class="line s-orange" marker-start="url(#ah-orange)"/>'
                + text(xa + 60, top + 2 * tau - eps - 12, "Alice hears Dave’s signal while she’s still sending: collision detected ✓", "hand f-green halo") + "</g>")
    # step 2: short frame
    body.append(band(xa, xd, 0, 120, "f-red", "=2", "Alice’s short frame"))
    body.append(band(xd, xa, tau - eps, 120, "f-blue", "=2", "Dave starts"))
    body.append(f'<g data-show="=2"><path d="M{xa + 14},{top + 120} l40,0" class="line s-green"/>'
                + text(xa + 60, top + 124, "Alice finishes: “sent it, all good!”", "hand f-green halo")
                + f'<path d="M{xa + 14},{top + 2 * tau - eps} l40,-10" class="line s-red" marker-start="url(#ah-red)"/>'
                + text(xa + 60, top + 2 * tau - eps - 8, "…the collision arrives after she’s stopped listening ✗", "hand f-red halo") + "</g>")
    # step 3: the rule
    body.append(band(xa, xd, 0, 2 * tau, "f-green", "=3", "the shortest allowed frame"))
    body.append(f'<g data-show="=3"><path d="M{xa - 20},{top} L{xa - 20},{top + 2 * tau}" class="line s-ink" marker-start="url(#ah-ink)" marker-end="url(#ah-ink)"/>'
                + text(xa - 26, top + tau + 5, "2 × trip", "end hand") + "</g>")
    steps = ["Time runs down the page and distance runs across. Alice starts a long frame; its front edge takes a while to crawl down the cable (the slope). Just before it reaches Dave, he hears silence and starts sending too. The signals crash near Dave, and Dave’s signal crawls back towards Alice. It reaches her while she’s <em>still sending</em>, so she hears the collision and knows to retry.",
             "Same timing, but Alice’s frame is short. She finishes sending, hears no collision, and moves on, sure it worked. Dave’s signal only reaches her afterwards. Nobody will ever resend this frame: it’s silently lost.",
             "The fix: every frame must last at least as long as a round trip to the far end of the cable and back. That sets a <strong>minimum frame size</strong> (and, the other way round, a maximum cable length). Short messages get padded with filler to reach the minimum."]
    svg = fig("".join(body), 720, top + 416, "Space-time diagram showing why frames must last at least a round trip of the cable",
              "Why a frame can’t be too short: a sender only notices a collision while it’s still talking.", steps)
    (OUT / "ch08-spacetime.svg").write_text(svg)


def backoff():
    body = []
    rows = [(1, 2, 1), (2, 4, 2), (3, 8, 5), (4, 16, 11)]
    for i, (k, n, pick) in enumerate(rows):
        y = 30 + i * 46
        body.append(text(20, y + 22, f"after collision #{k}:", "sm b"))
        body.append(text(170, y + 22, f"pick 0–{n - 1}", "mono sm"))
        for j in range(n):
            x = 260 + j * 27
            cls = "f-orange" if j == pick else "t-yellow"
            body.append(f'<rect x="{x}" y="{y + 4}" width="24" height="26" rx="3" class="{cls}" stroke="var(--line)"/>')
            body.append(text(x + 12, y + 22, str(j), "mid xs mono" + (" b" if j == pick else "")))
    body.append(text(360, 222, "each extra collision doubles the choices, so two stations are less and less likely to pick the same one", "mid hand"))
    svg = fig("".join(body), 720, 236, "Binary exponential backoff: the range of random waits doubles after each collision",
              "Binary exponential backoff. The busier it gets, the more patient everyone becomes.")
    (OUT / "ch08-backoff.svg").write_text(svg)


if __name__ == "__main__":
    mesh()
    bus()
    frame_layout()
    spacetime()
    backoff()
    print("wrote ch08 figures")
