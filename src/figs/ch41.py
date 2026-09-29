#!/usr/bin/env python3
"""Generate chapter 41 figures.  python3 src/figs/ch41.py"""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent
sys.path.insert(0, str(OUT.parent.parent / "labs" / "ch41"))
import dtn   # noqa: E402
import mars  # noqa: E402


def box(x, y, w, h, cls="f-card", stroke="var(--line)", rx=8, dash=False, sw=1.6):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" class="{cls}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def line(x1, y1, x2, y2, cls="s-ink", w=2.2, arrow=False, dash=False):
    mk = f' marker-end="url(#ah-{"ink" if cls == "s-ink" else cls[2:]})"' if arrow else ""
    d = ' stroke-dasharray="5 4"' if dash else ""
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="{w}"{mk}{d}/>'


# ---------------------------------------------------------------- how far, over two years (from mars.py)

def distance():
    start = date(2026, 9, 28)
    days = 800
    pts = []
    for k in range(0, days + 1):
        d = start + timedelta(days=k)
        km, angle = mars.mars_from_earth(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))
        pts.append((k, km / 1e6, angle))
    x0, x1, y0, y1 = 70, 650, 250, 40            # 0…420 million km

    def X(k):
        return x0 + k / days * (x1 - x0)

    def Y(mkm):
        return y0 - mkm / 420 * (y0 - y1)
    b = []
    for mkm in (0, 100, 200, 300, 400):
        b.append(f'<line x1="{x0}" y1="{Y(mkm):.1f}" x2="{x1}" y2="{Y(mkm):.1f}" class="grid"/>')
        b.append(text(x0 - 8, Y(mkm) + 4, f"{mkm}", "end xs muted"))
        b.append(text(x1 + 8, Y(mkm) + 4, f"{mkm * 1e6 / mars.C / 60:.0f} min", "xs muted"))
    b.append(text(x0 - 8, 26, "million km", "end xs b"))
    b.append(text(x1 + 8, 26, "one way", "xs b"))
    for k in range(0, days + 1):
        d = start + timedelta(days=k)
        if d.day == 1 and d.month in (1, 7):
            b.append(f'<line x1="{X(k):.1f}" y1="{y0}" x2="{X(k):.1f}" y2="{y0 + 5}" class="line s-muted" stroke-width="1"/>')
            b.append(text(X(k), y0 + 18, f"{d:%b %Y}", "mid xs muted"))
    quiet = [k for k, _, a in pts if a < 3]
    if quiet:
        b.append(f'<rect x="{X(quiet[0]):.1f}" y="{y1}" width="{X(quiet[-1]) - X(quiet[0]) + 4:.1f}" height="{y0 - y1}" class="t-red" opacity="0.8"/>')
        b.append(text(X(quiet[0]) - 6, y1 + 14, "the Sun is in the way", "end xs b f-red"))
    b.append('<path d="M' + " L".join(f"{X(k):.1f},{Y(m):.1f}" for k, m, _ in pts) + '" class="line s-orange" stroke-width="3" fill="none"/>')
    near = min(pts, key=lambda p: p[1])
    b.append(f'<circle cx="{X(near[0]):.1f}" cy="{Y(near[1]):.1f}" r="5" class="f-green"/>')
    nd = start + timedelta(days=near[0])
    b.append(text(X(near[0]) + 10, Y(near[1]) + 16, f"nearest: {nd:%d %b %Y}, {near[1]:.0f} million km", "xs b f-green"))
    b.append(f'<circle cx="{X(0):.1f}" cy="{Y(pts[0][1]):.1f}" r="5" class="f-ink"/>')
    b.append(text(X(0) + 10, Y(pts[0][1]) - 8, f"28 Sep 2026: {pts[0][1]:.0f} million km", "xs b"))
    svg = fig("".join(b), 720, 280, "A chart of the distance from Earth to Mars over two years, from about 250 million km down to 101 million in February 2027 and up to 360 million in 2028, with the Sun blocking the way in March 2028",
              "Earth to Mars, over the next two years, as this chapter’s <code>mars.py</code> calculates it. Earth goes round the Sun about twice for every once of Mars, so every 26 months or so it overtakes it (nearest), and in between they’re on opposite sides of the Sun.")
    (OUT / "ch41-distance.svg").write_text(svg)


# ---------------------------------------------------------------- why TCP gives up

def tcp():
    q = Seq([("Earth", 250, None), ("Mars", 610, None)], top=40, scale=26, head=False)
    L = 338 / 60                                             # minutes, Mars at its nearest
    q.msg("Earth", "Mars", 0, L, "SYN", "blue", step="1", label_at=0.25)
    for s in (1, 3, 7, 15, 31, 63):
        q.items.append(f'<g data-show="1"><line x1="250" y1="{q.y(s / 60):.1f}" x2="610" y2="{q.y(s / 60 + L):.1f}" class="line s-blue" stroke-width="1" opacity="0.5"/></g>')
    q.timer("Earth", 0, 134 / 60, "gives up after 134 s", step="1")
    q.note("Earth", 134 / 60 + 0.1, "“Could not connect to server”", step="1", side="right")
    q.note("Mars", L, "the first SYN arrives", step="2", side="left")
    q.msg("Mars", "Earth", L, 2 * L, "SYN-ACK", "green", step="2", label_at=0.3)
    q.note("Earth", 2 * L, "nobody is waiting for it any more", step="2", side="right")
    body, h = q.render(extra_bottom=20)
    body += text(710, 16, "Mars at its nearest: 5 min 38 s each way", "end xs muted")
    steps = ["Earth’s computer sends a SYN, to open a TCP connection (Chapter 27). No answer after a second, so it sends another; then after 3 s, 7, 15, 31 and 63, each time waiting twice as long. After seven tries it gives up: on the Pi, 134 seconds after the start.",
             "Five and a half minutes after the first SYN left, it reaches Mars, which answers politely. The SYN-ACK reaches Earth eleven minutes after the start, and is thrown away."]
    svg = fig(body, 720, h, "A sequence diagram: a TCP connection attempt from Earth gives up after 2 minutes 7 seconds, long before the first SYN reaches Mars 5 and a half minutes later",
              "TCP’s timers were made for a planet. Even to Mars at its very nearest, the conversation can’t start.", steps)
    (OUT / "ch41-tcp.svg").write_text(svg)


# ---------------------------------------------------------------- the contact plan, and the bundle's journey (dtn.py)

def plan():
    T = 1500                                                 # minutes shown
    x0, x1 = 150, 700

    def X(m):
        return x0 + m / T * (x1 - x0)
    rows = [("Earth ⇄ orbiter", ("earth", "orbiter"), 60), ("orbiter ⇄ rover", ("orbiter", "rover"), 110)]
    b = [text(20, 24, "the contact plan (dtn.py): when each radio link is up", "xs b")]
    for h in range(0, T + 1, 180):
        b.append(f'<line x1="{X(h):.1f}" y1="40" x2="{X(h):.1f}" y2="236" class="grid"/>')
        c = dtn.clock(h)
        b.append(text(X(h), 252, c.split(", ")[1], "mid xs muted"))
        if c.endswith("00:00") or h == 0:
            b.append(text(X(h), 266, c.split(",")[0], "mid xs b muted"))
    for name, link, y in rows:
        b.append(text(20, y + 16, name, "xs b"))
        for a, z in dtn.PLAN[link]:
            if a < T:
                b.append(box(X(a), y, max(X(min(z, T)) - X(a), 3), 22, "t-green", "var(--green)", 3, sw=1.2))
    # the journey: question (blue), answer (purple); stored periods as bars
    j = [(5, 19, 150, "blue", "question: 14 minutes in flight, then 3 hours stored on the orbiter"), (19, 200, 150, "blue", ""),
         (200, 1440, 196, "purple", "answer: stored on the orbiter, 20 hours, until Earth’s dish is back"),
         (1440, 1454, 196, "purple", "")]
    for a, z, y, col, label in j:
        b.append(f'<rect x="{X(a):.1f}" y="{y}" width="{max(X(z) - X(a), 3):.1f}" height="14" rx="3" class="f-{col}" opacity="0.75"/>')
        if label:
            b.append(text(X(a) + 4, y + 30, label, f"xs f-{col}"))
    b.append(text(20, 162, "the question", "xs b f-blue"))
    b.append(text(20, 208, "the answer", "xs b f-purple"))
    svg = fig("".join(b), 720, 276, "A timeline of the contact plan: two-hour links between Earth and the orbiter each day, twelve-minute passes over the rover; the question waits 3 hours on the orbiter, and the answer waits 20 hours",
              "The run below, as a timeline. At no moment is there a path all the way from Earth to the rover, so every bundle spends most of its life in storage, waiting for the next link.")
    (OUT / "ch41-plan.svg").write_text(svg)


# ---------------------------------------------------------------- one bundle, block by block

def anatomy():
    b = []
    parts = [("9f", "start of the bundle: an array of blocks, length unknown", "f-card", "var(--line)"),
             ("89 07 00 01", "primary block: 9 items. Version 7, flags 0, CRC type 1 (CRC-16)", "t-blue", "var(--blue)"),
             ("82 01 6e “//rover/camera”", "destination: [1 = the dtn scheme, the name]", "t-blue", "var(--blue)"),
             ("82 01 68 “//earth/”", "source node", "t-blue", "var(--blue)"),
             ("82 01 00", "report to: dtn:none (nobody)", "t-blue", "var(--blue)"),
             ("82 1b 00 00 00 c4 7b ce 2e e0 01", "created: 843,890,700,000 ms after 1 January 2000, bundle number 1", "t-blue", "var(--blue)"),
             ("1a 24 0c 84 00", "lifetime: 604,800,000 ms, a week", "t-blue", "var(--blue)"),
             ("42 86 5c", "CRC-16 of this block, so damage can be spotted", "t-blue", "var(--blue)"),
             ("85 0a 02 00 00 43 82 10 00", "hop count block: type 10, number 2, data [16, 0]: at most 16 hops, none yet", "t-orange", "var(--orange)"),
             ("85 01 01 00 00 58 21 “Please…”", "payload block: type 1, number 1, 33 bytes of data", "t-green", "var(--green)"),
             ("ff", "end of the bundle", "f-card", "var(--line)")]
    for i, (hexs, what, cls, stroke) in enumerate(parts):
        y = 12 + i * 30
        b.append(box(10, y, 290, 24, cls, stroke, 5, sw=1.2))
        b.append(text(20, y + 16, hexs, "xs mono b"))
        b.append(text(312, y + 16, what, "xs"))
    svg = fig("".join(b), 720, 12 + len(parts) * 30 + 4, "The bytes of one bundle, block by block: primary block with version, flags, CRC type, destination, source, report-to, creation time, lifetime and CRC; a hop count block; a payload block",
              "One bundle, all 105 bytes, as <code>dtn.py --bundle</code> builds it. The primary block never changes on the way; the other blocks can.")
    (OUT / "ch41-bundle.svg").write_text(svg)


if __name__ == "__main__":
    distance()
    tcp()
    plan()
    anatomy()
    print("wrote ch41 figures")
