#!/usr/bin/env python3
"""Generate chapter 14 figures.  python3 src/figs/ch14.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- everyone keeps a list

def lists():
    people = [("alice", "Alice", 20), ("bob", "Bob", 200), ("carol", "Carol", 380), ("dave", "Dave", 560)]
    rows = [("otto", "4.2"), ("library", "3.1"), ("newsletter", "2.7"), ("bob", "1.2")]
    body = []
    for sid, name, x in people:
        body.append(f'<use href="#{sid}-head" x="{x + 50}" y="8" width="44" height="44"/>')
        body.append(text(x + 72, 66, f"{name}’s list", "mid sm b"))
        body.append(f'<rect x="{x}" y="76" width="144" height="116" rx="6" class="t-yellow" stroke="var(--yellow)" stroke-width="2"/>')
        for i, (n, a) in enumerate(rows):
            y = 100 + i * 24
            stale = n == "otto"
            body.append(text(x + 12, y, n, "mono xs" + (" f-red" if stale else "")))
            body.append(text(x + 132, y, a, "end mono xs b" + (" f-red" if stale else "")))
            if stale:
                body.append(f'<line x1="{x + 8}" y1="{y - 4}" x2="{x + 136}" y2="{y - 4}" class="line s-red" stroke-width="2"/>')
    body.append(text(360, 226, "Otto’s town renumbers him to 4.9, and every list in town is wrong at once.", "mid hand f-red"))
    svg = fig("".join(body), 720, 240, "Every computer keeps its own list of names and numbers; one change makes them all out of date",
              "Everyone keeps their own list. It works, until something changes.")
    (OUT / "ch14-lists.svg").write_text(svg)


# ---------------------------------------------------------------- the tree of names

def tree():
    root = (360, 44)
    leaves = {"street": ["alice", "bob", "carol"], "school": ["teacher", "newsletter"], "library": ["catalog"],
              "seaside": ["otto", "harbor", "cafe"]}

    def gap_for(kids):
        return max(len(k) for k in kids) * 7 + 22

    def width_for(kids):
        return max(120, len(kids) * gap_for(kids) + 8)
    tops, x = {}, 8
    for top, kids in leaves.items():                      # lay the groups out side by side
        w = width_for(kids)
        tops[top] = (x + w / 2, 140)
        x += w + 8
    owners = {"street": ("t-blue", "var(--blue)", "run by our street"), "school": ("t-green", "var(--green)", "run by the school"),
              "library": ("t-purple", "var(--purple)", "run by the library"), "seaside": ("t-orange", "var(--orange)", "run by Otto’s town")}
    body = []
    for top, (x, y) in tops.items():
        cls, stroke, label = owners[top]
        kids = leaves[top]
        w = width_for(kids)
        body.append(f'<rect x="{x - w / 2}" y="{y - 26}" width="{w}" height="146" rx="14" class="{cls}" stroke="{stroke}" stroke-width="2" opacity="0.9"/>')
        body.append(text(x, y + 112, label, "mid xs muted"))
        body.append(f'<line x1="{root[0]}" y1="{root[1] + 16}" x2="{x}" y2="{y - 14}" class="line s-muted" stroke-width="2"/>')
    body.append(f'<rect x="{root[0] - 60}" y="{root[1] - 18}" width="120" height="36" rx="10" class="f-surface" stroke="var(--ink)" stroke-width="2"/>')
    body.append(text(root[0], root[1] + 6, "the root", "mid slab b"))
    body.append(text(root[0] + 74, root[1] + 6, "run by the town", "xs muted"))
    for top, (x, y) in tops.items():
        body.append(f'<rect x="{x - 44}" y="{y - 14}" width="88" height="28" rx="8" class="f-surface" stroke="var(--ink)" stroke-width="1.5"/>')
        body.append(text(x, y + 5, top, "mid mono sm b"))
        kids = leaves[top]
        gap = gap_for(kids)
        for i, k in enumerate(kids):
            kx = x + (i - (len(kids) - 1) / 2) * gap
            ky = y + 70
            bw = len(k) * 7 + 16
            body.append(f'<line x1="{x}" y1="{y + 14}" x2="{kx}" y2="{ky - 12}" class="line s-muted" stroke-width="1.5"/>')
            hl = k == "otto"
            body.append(f'<rect x="{kx - bw / 2}" y="{ky - 12}" width="{bw}" height="24" rx="6" class="f-surface" '
                        f'stroke="{"var(--red)" if hl else "var(--line)"}" stroke-width="{3 if hl else 1.5}"/>')
            body.append(text(kx, ky + 5, k, "mid mono xs" + (" b" if hl else "")))
    body.append(text(360, 300, "otto.seaside is read right to left: start at the root, go to seaside, then find otto.", "mid hand"))
    svg = fig("".join(body), 720, 314, "A tree of names: the root, four parts of town, and the names in each, each part run by its own owner",
              "Names in a tree. Each part of the tree is looked after by whoever owns it.")
    (OUT / "ch14-tree.svg").write_text(svg)


# ---------------------------------------------------------------- asking around

def resolve():
    seq = Seq([("Alice", 70, "alice"), ("resolver", 260, None), ("root", 460, None), ("seaside", 650, None)], top=92, scale=35)
    seq.msg("Alice", "resolver", 0, 1, "otto.seaside?", cls="blue", step="1")
    seq.msg("resolver", "root", 1.3, 2.3, "otto.seaside?", cls="blue", step="2")
    seq.msg("root", "resolver", 2.6, 3.6, "ask seaside’s server", cls="orange", step="2", sub="(and remember that for 2 days)")
    seq.msg("resolver", "seaside", 4.0, 5.0, "otto.seaside?", cls="blue", step="3", label_at=0.35)
    seq.msg("seaside", "resolver", 5.3, 6.3, "4.2", cls="green", step="3", sub="good for 1 hour", label_at=0.35)
    seq.msg("resolver", "Alice", 6.7, 7.7, "4.2", cls="green", step="4")
    seq.note("resolver", 8.3, "remember: otto.seaside = 4.2", step="4", side="right")
    seq.msg("Alice", "resolver", 9.0, 10.0, "otto.seaside?", cls="blue", step="5", sub="(Bob, ten minutes later)")
    seq.msg("resolver", "Alice", 10.3, 11.3, "4.2", cls="green", step="5", sub="straight from memory")
    body, bottom = seq.render()
    for x in (260, 460, 650):
        body += f'<use href="#server" x="{x - 18}" y="8" width="36" height="46"/>'
    steps = ["Alice’s computer doesn’t go looking itself. It asks the <strong>resolver</strong> on her street, a name server that does the asking for everyone.",
             "The resolver starts at the top. The root doesn’t know Otto, but it knows who runs “seaside”, and says so.",
             "The resolver asks seaside’s server, which does know, and says how long the answer is good for.",
             "The resolver passes the answer on, and remembers it.",
             "The next time anyone on the street asks, within the hour, the resolver answers straight away. The root and seaside don’t hear about it at all."]
    svg = fig(body, 720, bottom, "A resolver asks the root, then seaside's name server, then remembers the answer",
              "Asking around, and remembering.", steps)
    (OUT / "ch14-resolve.svg").write_text(svg)


# ---------------------------------------------------------------- poisoning

def poison():
    seq = Seq([("resolver", 110, None), ("Eve", 380, "eve"), ("seaside", 630, None)], top=92, scale=36)
    seq.msg("resolver", "seaside", 0, 1.4, "question #7: harbor.seaside?", cls="blue", step="1", label_at=0.28)
    seq.note("Eve", 1.85, "fake answers #1… #6, #7, #8… #50", step="2", side="right", cls="f-red")
    for i, t in enumerate((2.2, 2.6, 3.0, 3.4)):
        seq.msg("Eve", "resolver", t, t + 0.7, "#7: harbor is 6.66" if i == 2 else "", cls="red", step="2", label_at=0.5)
    seq.note("resolver", 4.7, "#7 matches! Believe it, and remember it for an hour", step="3", side="right", cls="f-red")
    seq.msg("seaside", "resolver", 5.3, 6.7, "#7: harbor is 4.8", cls="green", step="4", sub="too late: already answered")
    body, bottom = seq.render()
    body += '<use href="#server" x="92" y="8" width="36" height="46"/><use href="#server" x="612" y="8" width="36" height="46"/>'
    steps = ["The resolver asks seaside’s server about harbor.seaside, with question number 7.",
             "Eve can’t see the question, but she can guess. She floods the resolver with fake answers, each with a different number.",
             "One of them has the right number, and it arrives first. The resolver believes it.",
             "The real answer arrives a moment later, and it’s ignored. For the next hour, everyone on the street who asks for harbor.seaside is sent to Eve."]
    svg = fig(body, 720, bottom, "Eve floods a resolver with forged answers and one matches the question number",
              "Poisoning a resolver’s memory.", steps)
    (OUT / "ch14-poison.svg").write_text(svg)


if __name__ == "__main__":
    lists()
    tree()
    resolve()
    poison()
    print("wrote ch14 figures")
