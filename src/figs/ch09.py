#!/usr/bin/env python3
"""Generate chapter 9 figures.  python3 src/figs/ch09.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def star_panel(ox, title, sub, box_sprite, flows):
    """flows: list of (from_idx, to_idx_list, colour class)."""
    hosts = [("alice", "Alice", (ox + 50, 70)), ("bob", "Bob", (ox + 290, 70)),
             ("carol", "Carol", (ox + 50, 250)), ("dave", "Dave", (ox + 290, 250))]
    cx, cy = ox + 170, 160
    out = [text(ox + 170, 24, title, "mid slab b"), text(ox + 170, 318, sub, "mid hand")]
    for sid, name, (x, y) in hosts:
        out.append(f'<line x1="{x}" y1="{y}" x2="{cx}" y2="{cy}" class="wire" stroke-width="4"/>')
    for frm, tos, cls in flows:
        fx, fy = hosts[frm][2]
        out.append(f'<line x1="{fx}" y1="{fy}" x2="{cx}" y2="{cy}" class="line {cls}" stroke-width="5" stroke-dasharray="8 6"/>')
        for t in tos:
            tx, ty = hosts[t][2]
            out.append(f'<path d="M{cx},{cy} L{(cx + tx) / 2 + (tx - cx) * 0.3:.0f},{(cy + ty) / 2 + (ty - cy) * 0.3:.0f}" '
                       f'class="line {cls}" stroke-width="5" marker-end="url(#ah-{cls[2:]})"/>')
    out.append(f'<use href="#{box_sprite}" x="{cx - 75}" y="{cy - 23}" width="150" height="46"/>')
    for sid, name, (x, y) in hosts:
        out.append(f'<use href="#{sid}-head" x="{x - 26}" y="{y - 30}" width="52" height="52"/>')
        out.append(text(x, y + 36, name, "mid sm b halo"))
    return "".join(out)


def star():
    body = star_panel(10, "A hub: repeat everything, everywhere", "Alice → Bob reaches everyone (and collides)", "hub",
                      [(0, [1, 2, 3], "s-orange")])
    body += star_panel(370, "A switch: only where it needs to go", "Alice → Bob and Carol → Dave, both at once", "switch",
                       [(0, [1], "s-green"), (2, [3], "s-blue")])
    body += '<line x1="360" y1="30" x2="360" y2="280" class="line s-line"/>'
    svg = fig(body, 720, 332, "A hub repeats every frame to every port; a switch sends each frame only toward its destination",
              "Same star-shaped wiring, very different boxes in the middle.")
    (OUT / "ch09-star.svg").write_text(svg)


def two_switches():
    body = []
    s1, s2 = (200, 130), (520, 130)
    for (x, y), name in ((s1, "S1"), (s2, "S2")):
        body.append(f'<use href="#switch" x="{x - 75}" y="{y - 23}" width="150" height="46"/>')
        body.append(text(x, y - 32, name, "mid slab b"))
    body.append(f'<line x1="{s1[0] + 75}" y1="{s1[1]}" x2="{s2[0] - 75}" y2="{s2[1]}" class="wire" stroke-width="5"/>')
    body.append(text(360, 120, "port 9 ↔ port 9", "mid xs muted"))
    hosts = [("alice", "Alice 0a:11", (80, 250), s1, "port 1"), ("bob", "Bob 0b:22", (280, 250), s1, "port 2"),
             ("carol", "Carol 0c:33", (440, 250), s2, "port 1"), ("dave", "Dave 0d:44", (640, 250), s2, "port 2")]
    for sid, name, (x, y), (sx, sy), port in hosts:
        body.append(f'<line x1="{x}" y1="{y - 28}" x2="{sx + (x - sx) * 0.3}" y2="{sy + 22}" class="wire" stroke-width="3.5"/>')
        body.append(f'<use href="#{sid}-head" x="{x - 24}" y="{y - 30}" width="48" height="48"/>')
        body.append(text(x, y + 32, name, "mid xs b"))
        body.append(text(x, y - 38, port, "mid xs muted halo"))
    for x, rows in ((30, ["0a:11 → port 1", "0b:22 → port 2", "0c:33 → port 9", "0d:44 → port 9"]),
                    (570, ["0a:11 → port 9", "0b:22 → port 9", "0c:33 → port 1", "0d:44 → port 2"])):
        body.append(f'<rect x="{x}" y="16" width="130" height="92" rx="8" class="card"/>')
        for i, r in enumerate(rows):
            body.append(text(x + 10, 36 + i * 20, r, "mono xs" + (" b f-teal" if "9" in r.split("port")[1] else "")))
    svg = fig("".join(body), 720, 300, "Two switches joined together; each learns that several addresses live behind the connecting port",
              "To S1, Carol and Dave both simply live “out of port 9”. It doesn’t need to know any more than that.")
    (OUT / "ch09-two.svg").write_text(svg)


TRI = {"S1": (360, 60), "S2": (170, 250), "S3": (550, 250)}


def triangle_base(blocked=None):
    out = []
    for a, b in (("S1", "S2"), ("S2", "S3"), ("S3", "S1")):
        (x1, y1), (x2, y2) = TRI[a], TRI[b]
        if blocked == {a, b}:
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="line s-red" stroke-width="4" stroke-dasharray="10 8"/>')
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            out.append(f'<path d="M{mx - 12},{my - 12} l24,24 M{mx + 12},{my - 12} l-24,24" class="line s-red" stroke-width="5"/>')
            out.append(text(mx, my + 34, "blocked", "mid hand f-red"))
        else:
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="wire" stroke-width="5"/>')
    for name, (x, y) in TRI.items():
        out.append(f'<use href="#switch" x="{x - 60}" y="{y - 18}" width="120" height="37"/>')
        out.append(text(x, y + 38, name, "mid slab b halo"))
    out.append('<line x1="360" y1="60" x2="360" y2="0" class="wire" stroke-width="3"/>')
    out.append('<use href="#alice-head" x="386" y="-2" width="40" height="40"/>')
    out.append(text(430, 24, "Alice", "sm b"))
    return "".join(out)


def storm():
    body = [triangle_base()]

    def copy(x, y, label, step, cls="f-orange"):
        return (f'<g data-show="={step}"><circle cx="{x}" cy="{y}" r="15" class="{cls}" stroke="var(--surface)" stroke-width="2"/>'
                f'<text x="{x}" y="{y + 5}" class="mid xs b" fill="#fff">{label}</text></g>')
    body.append(copy(268, 150, "1", 1) + copy(452, 150, "1", 1))
    body.append(copy(360, 262, "2", 2) + copy(300, 262, "2", 2) + copy(420, 262, "2", 2))
    body.append(copy(250, 140, "3", 3) + copy(290, 170, "3", 3) + copy(470, 140, "3", 3) + copy(430, 170, "3", 3))
    body.append(f'<g data-show="4">{text(360, 330, "…and around, and around, and around", "mid hand lg f-red")}</g>')
    body.append(f'<g data-show="=4"><circle cx="360" cy="180" r="44" class="f-red" opacity="0.2"/>{text(360, 186, "∞", "mid xl b f-red")}</g>')
    steps = ["Alice sends one broadcast. S1 floods it out of both of its other ports, so one copy heads to S2 and one to S3.",
             "S2 floods its copy to S3, and S3 floods its copy to S2. Now two copies are crossing on the bottom link.",
             "Each of those gets flooded onward around the triangle, back to S1, which floods them yet again. None of them will ever stop, because a switch has no way to tell it’s seen a frame before. (In a network with more loops, every lap even <em>multiplies</em> the copies.)",
             "Within seconds the links are 100% full of copies of one broadcast, and every new broadcast adds more. Meanwhile the switches keep seeing Alice’s address arrive on different ports, and their tables thrash. The network is down. This is a <strong>broadcast storm</strong>."]
    svg = fig('<g transform="translate(0,34)">' + "".join(body) + "</g>", 720, 384, "A broadcast circling a loop of three switches forever, multiplying as it goes",
              "Three switches in a loop, and one innocent broadcast.", steps)
    (OUT / "ch09-storm.svg").write_text(svg)


def stp():
    body = [triangle_base(blocked={"S2", "S3"})]
    body.append(text(360, 330, "S1 has the lowest ID, so it’s the root. Every switch keeps its shortest path to S1, and the one link on neither path is switched off.",
                     "mid sm"))
    body.append('<text x="300" y="58" class="end lg">👑</text>')
    svg = fig('<g transform="translate(0,34)">' + "".join(body) + "</g>", 720, 384, "Spanning tree: one link of the triangle is blocked so no loop remains",
              "A spanning tree: every switch still reaches every other, but there’s exactly one path between any two.")
    (OUT / "ch09-stp.svg").write_text(svg)


if __name__ == "__main__":
    star()
    two_switches()
    storm()
    stp()
    print("wrote ch09 figures")
