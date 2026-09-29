#!/usr/bin/env python3
"""Generate chapter 40 figures.  python3 src/figs/ch40.py"""
import json
import math
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent
C = 299792.458
RE = 6371.0


def box(x, y, w, h, cls="f-card", stroke="var(--line)", rx=8, dash=False, sw=1.6):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" class="{cls}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def line(x1, y1, x2, y2, cls="s-ink", w=2.2, arrow=False, dash=False):
    mk = f' marker-end="url(#ah-{"ink" if cls == "s-ink" else cls[2:]})"' if arrow else ""
    d = ' stroke-dasharray="5 4"' if dash else ""
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="{w}"{mk}{d}/>'


# ---------------------------------------------------------------- how high: LEO, MEO, GEO

def altitudes():
    rows = [("Starlink (most)", 480, "t-green", "var(--green)", "94 min", "thousands"),
            ("OneWeb", 1200, "t-teal", "var(--teal)", "109 min", "hundreds"),
            ("GPS", 20200, "t-yellow", "var(--yellow)", "12 hours", "about 30"),
            ("geostationary", 35786, "t-orange", "var(--orange)", "1 day", "3 cover most of the Earth")]
    x0, x1 = 150, 500
    lo, hi = math.log10(200), math.log10(50000)

    def X(km):
        return x0 + (math.log10(km) - lo) / (hi - lo) * (x1 - x0)
    b = [text(20, 24, "height above the ground (a logarithmic scale: each step is ten times higher)", "xs b")]
    for km in (300, 1000, 3000, 10000, 30000):
        b.append(f'<line x1="{X(km):.1f}" y1="36" x2="{X(km):.1f}" y2="214" class="grid"/>')
        b.append(text(X(km), 230, f"{km:,} km", "mid xs muted"))
    b.append(text(600, 46, "round trip,", "end xs b"))
    b.append(text(600, 58, "at least", "end xs b"))
    b.append(text(690, 46, "one orbit", "end xs b"))
    for i, (name, km, cls, stroke, period, how_many) in enumerate(rows):
        y = 72 + i * 36
        b.append(text(20, y + 16, name, "sm b"))
        b.append(box(x0, y, X(km) - x0, 22, cls, stroke, 4, sw=1.2))
        b.append(text(X(km) + 6, y + 16, f"{km:,} km", "xs mono"))
        b.append(text(600, y + 16, f"{4 * km / C * 1000:,.0f} ms", "end xs mono b"))
        b.append(text(690, y + 16, period, "end xs"))
    b.append(text(20, 256, "Round trip: up to the satellite and down to a ground station, then back the same way, at the speed of light, with the", "xs"))
    b.append(text(20, 272, "satellite straight overhead. Real connections add processing, queues and the rest of the internet.", "xs"))
    svg = fig("".join(b), 720, 284, "Satellite heights on a logarithmic scale: Starlink about 480 km, OneWeb 1,200 km, GPS 20,200 km, geostationary 35,786 km, with minimum round trips of 6, 16, 270 and 477 ms",
              "How high, and how long a round trip must take. A geostationary satellite goes round once a day, so it seems to hang still in the sky: one dish, pointed once, for ever. But it’s so far away that light alone costs half a second.")
    (OUT / "ch40-altitudes.svg").write_text(svg)


# ---------------------------------------------------------------- the bent pipe, and lasers

def bentpipe():
    b = []
    # ground
    b.append('<path d="M0,250 Q360,215 720,250 L720,280 L0,280 Z" class="f-teal2"/>')
    b.append(f'<use href="#house" x="36" y="186" width="56" height="60"/>')
    b.append(text(64, 270, "Uncle Ray’s farm", "mid xs b"))
    b.append(box(88, 200, 26, 12, "f-card", "var(--ink)", 3, sw=1.2))
    b.append(text(101, 196, "dish", "mid xs"))
    sats = [(170, 70), (330, 50), (490, 50), (620, 70)]
    for x, y in sats:
        b.append(f'<rect x="{x - 9}" y="{y - 6}" width="18" height="12" rx="2" class="f-navy"/>')
        b.append(f'<rect x="{x - 30}" y="{y - 4}" width="18" height="8" class="f-blue"/><rect x="{x + 12}" y="{y - 4}" width="18" height="8" class="f-blue"/>')
    # step 1: bent pipe
    b.append('<g data-show="=1">' + line(104, 200, 168, 80, "s-green", 2.5, arrow=True) + line(172, 80, 250, 222, "s-green", 2.5, arrow=True)
             + box(222, 222, 60, 20, "t-purple", "var(--purple)", 4) + text(252, 236, "gateway", "mid xs b")
             + line(282, 232, 330, 232, "s-ink", 2, arrow=True) + text(334, 236, "fibre to a data centre, then the internet", "xs")
             + text(210, 130, "up", "xs hand f-green") + "</g>")
    # step 2: lasers
    b.append('<g data-show="=2">' + line(104, 200, 168, 80, "s-green", 2.5, arrow=True)
             + line(180, 66, 318, 52, "s-red", 2.5, arrow=True) + line(342, 50, 478, 50, "s-red", 2.5, arrow=True)
             + line(500, 52, 608, 66, "s-red", 2.5, arrow=True) + line(622, 80, 640, 222, "s-green", 2.5, arrow=True)
             + box(612, 222, 60, 20, "t-purple", "var(--purple)", 4) + text(642, 236, "gateway", "mid xs b")
             + text(400, 38, "lasers, satellite to satellite", "mid xs b f-red")
             + text(360, 170, "no gateway in sight (the sea, or the far north)?", "mid xs")
             + text(360, 186, "pass it along in space, at the full speed of light", "mid xs") + "</g>")
    # step 3: moving
    b.append('<g data-show="=3">' + line(104, 200, 330, 60, "s-green", 2.5, arrow=True)
             + line(104, 200, 168, 80, "s-muted", 1.5, dash=True)
             + '<path d="M150,70 l-40,-4" class="line s-orange" stroke-width="2" marker-end="url(#ah-orange)"/>'
             + '<path d="M312,50 l-40,-4" class="line s-orange" stroke-width="2" marker-end="url(#ah-orange)"/>'
             + text(200, 140, "7.6 km every second", "mid xs hand f-orange")
             + text(400, 120, "the dish steers its beam", "xs")
             + text(400, 136, "electronically to the next one", "xs") + "</g>")
    steps = ["The simplest design, a <em>bent pipe</em>: the dish talks to a satellite overhead, and the satellite repeats everything down to a ground station, a <strong>gateway</strong>, within a few hundred kilometres, which is wired to the internet.",
             "Newer satellites have lasers to talk to each other. Over the ocean, or far from any gateway, packets hop from satellite to satellite until one is above a gateway. They’re routers, in orbit.",
             "And everything moves. The satellite overhead will be gone in a few minutes, so every few seconds the dish is handed to another one, and the paths through space change with it. The dish has no motor: it’s a flat grid of hundreds of tiny antennas that aims its beam by timing them (a “phased array”)."]
    svg = fig("".join(b), 720, 282, "A satellite dish talking to a satellite that relays to a ground gateway; then satellites passing traffic between themselves by laser; then the satellites moving and the dish switching",
              "How a low-orbit satellite internet carries a packet.", steps)
    (OUT / "ch40-bentpipe.svg").write_text(svg)


# ---------------------------------------------------------------- real passes over Greenwich

def passes():
    data = json.loads((OUT / "ch40-passes.json").read_text())
    T, best = data["seconds"], data["best"]
    x0, x1, y0, y1 = 60, 700, 250, 36           # plot box; elevation 40°…90°

    def X(t):
        return x0 + t / T * (x1 - x0)

    def Y(el):
        return y0 - (el - 40) / 50 * (y0 - y1)
    b = []
    for el in (40, 50, 60, 70, 80, 90):
        b.append(f'<line x1="{x0}" y1="{Y(el):.1f}" x2="{x1}" y2="{Y(el):.1f}" class="grid"/>')
        b.append(text(x0 - 8, Y(el) + 4, f"{el}°", "end xs muted"))
    for t in range(0, T + 1, 30):
        b.append(text(X(t), y0 + 18, f"{t} s", "mid xs muted"))
    b.append(text(x0, 20, "how high each satellite is, seen from Greenwich, over three minutes", "xs b"))
    for name, els in data["sats"].items():
        pts = [(X(t), Y(e)) for t, e in enumerate(els) if e >= 40]
        if len(pts) > 1:
            b.append('<path d="M' + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '" class="line s-muted" stroke-width="1.2" fill="none"/>')
    # the best, at each moment
    seg, start = [], 0
    for t in range(1, T + 2):
        if t == T + 1 or best[t] != best[start]:
            els = data["sats"][best[start]]
            pts = [(X(k), Y(els[k])) for k in range(start, min(t + 1, T + 1))]
            b.append('<path d="M' + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '" class="line s-green" stroke-width="3.5" fill="none"/>')
            if t <= T:
                b.append(f'<circle cx="{X(t):.1f}" cy="{Y(data["sats"][best[t]][t]):.1f}" r="4" class="f-orange"/>')
            start = t
    changes = sum(1 for a, c in zip(best, best[1:]) if a != c)
    b.append(text(x1, y0 + 36, f"green: the highest satellite at each moment · orange: a change of satellite ({changes} in {T // 60} minutes)", "end xs"))
    svg = fig("".join(b), 720, 296, "A chart of real Starlink satellite elevations over Greenwich across three minutes, with the highest one at each moment highlighted, changing ten times",
              f"Real orbits: each grey line is one Starlink satellite rising and setting (computed by this chapter’s lab, for {data['start'][:10]} at {data['start'][11:16]} UTC). A dish that always used the highest would change satellite every 18 seconds or so.")
    (OUT / "ch40-passes.svg").write_text(svg)


# ---------------------------------------------------------------- the race: fibre vs lasers in space

def race():
    london, newyork = (51.51, -0.13), (40.71, -74.01)
    p1, p2 = [math.radians(v) for v in london], [math.radians(v) for v in newyork]
    ang = math.acos(math.sin(p1[0]) * math.sin(p2[0]) + math.cos(p1[0]) * math.cos(p2[0]) * math.cos(p2[1] - p1[1]))
    ground = RE * ang
    h = 550
    space = (RE + h) * ang + 2 * h
    rows = [("a perfectly straight fibre, through the sea", ground, 2 / 3, "t-blue", "var(--blue)"),
            ("lasers in space, 550 km up, plus the trips up and down", space, 1, "t-red", "var(--red)")]
    b = [text(20, 24, f"London to New York: {ground:,.0f} km along the ground. One way, at best:", "sm b")]
    for i, (name, km, speed, cls, stroke) in enumerate(rows):
        ms = km / (C * speed) * 1000
        y = 44 + i * 58
        b.append(text(20, y + 14, name, "xs b"))
        b.append(box(20, y + 22, ms * 10, 22, cls, stroke, 4, sw=1.2))
        b.append(text(26 + ms * 10, y + 38, f"{km:,.0f} km at {'two-thirds of ' if speed < 1 else ''}the speed of light: {ms:.1f} ms", "xs mono"))
    b.append(text(20, 172, "Light in glass travels at about 200,000 km/s (Chapter 17); in a vacuum, 300,000. Over long enough distances, the longer", "xs"))
    b.append(text(20, 188, "path through space wins. Real cables aren’t straight, which makes the gap bigger still.", "xs"))
    svg = fig("".join(b), 720, 200, "Bars comparing one-way time London to New York: straight fibre about 28 ms, lasers in space about 23 ms",
              "Why some people want to send long-distance traffic through space, even when there’s a cable.")
    (OUT / "ch40-race.svg").write_text(svg)


if __name__ == "__main__":
    altitudes()
    bentpipe()
    passes()
    race()
    print("wrote ch40 figures")
