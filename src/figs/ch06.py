#!/usr/bin/env python3
"""Generate chapter 6 figures.  python3 src/figs/ch06.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


def url_parts():
    def row(y, parts, caption):
        out = [text(20, y - 34, caption, "sm b")]
        x = 90
        for i, (label, cls, name) in enumerate(parts):
            w = 12.4 * len(label) + 16
            out.append(f'<rect x="{x}" y="{y - 22}" width="{w}" height="36" rx="6" class="{cls}" stroke="var(--line)"/>')
            out.append(text(x + w / 2, y + 2, label, "mid mono lg b"))
            if name:
                drop = 30 if i != 2 else 54
                out.append(f'<path d="M{x + w / 2},{y + 16} L{x + w / 2},{y + drop}" class="line thin s-muted"/>')
                out.append(text(x + w / 2, y + drop + 16, name, "mid hand"))
            x += w + 2
        return "".join(out)
    body = row(70, [("ttp", "t-purple", "how to talk (scheme)"), ("://", "f-none", ""), ("carol", "t-blue", "which computer (host)"),
                    ("/recipes/snacks.mu", "t-yellow", "which document (path)")], "One of our addresses:")
    body += row(214, [("https", "t-purple", "scheme"), ("://", "f-none", ""), ("www.example.com", "t-blue", "host"),
                      ("/docs/intro.html", "t-yellow", "path")], "A real one, same parts:")
    svg = fig(body, 720, 300, "The parts of a URL: scheme, host and path",
              "Every link says three things: which protocol to speak, which computer to ask, and what to ask it for.")
    (OUT / "ch06-url.svg").write_text(svg)


def web_graph():
    comps = [("Alice’s computer", 20, 30, 200, 250, "t-red"), ("Bob’s computer", 250, 30, 220, 250, "t-blue"),
             ("Carol’s computer", 500, 30, 200, 250, "t-green")]
    docs = {"a-index": (70, 80, "index"), "a-volc": (70, 190, "volcanoes"),
            "b-index": (300, 70, "index"), "b-report": (300, 150, "report"), "b-sched": (390, 220, "schedule"), "b-img": (410, 120, "volcano.png"),
            "c-index": (550, 80, "index"), "c-bees": (550, 170, "bees"), "c-recipes": (630, 230, "recipes")}
    links = [("a-index", "a-volc"), ("a-index", "b-index"), ("a-volc", "b-img"), ("b-index", "b-report"), ("b-index", "c-index"),
             ("b-report", "b-sched"), ("b-sched", "a-volc"), ("b-sched", "c-bees"), ("c-index", "c-bees"), ("c-index", "c-recipes"),
             ("c-index", "b-index"), ("b-index", "b-img")]
    body = []
    for name, x, y, w, h, cls in comps:
        body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" class="{cls}" opacity="0.7"/>')
        body.append(text(x + 12, y + 22, name, "slab b sm"))
    for a, b in links:
        (x1, y1, _), (x2, y2, _) = docs[a], docs[b]
        sx, sy, ex, ey = x1 + 40, y1 + 14, x2 + 40, y2 + 14
        dx, dy = ex - sx, ey - sy
        # stop the arrow where it meets the target box (half-size 45 x 14, plus a small gap)
        scale = min(45 / abs(dx) if dx else 9e9, 14 / abs(dy) if dy else 9e9)
        ex, ey = ex - dx * scale - (dx / (abs(dx) + abs(dy))) * 4, ey - dy * scale - (dy / (abs(dx) + abs(dy))) * 4
        body.append(f'<path d="M{sx},{sy} L{ex:.1f},{ey:.1f}" class="line thin s-navy" marker-end="url(#ah-ink)" opacity="0.8"/>')
    for key, (x, y, label) in docs.items():
        w = 90 if key != "b-img" else 96
        body.append(f'<rect x="{x - 5}" y="{y}" width="{w}" height="28" rx="5" class="box"/>')
        body.append(text(x + w / 2 - 5, y + 19, label, "mid mono xs b"))
    body.append('<path d="M595,108 C640,120 660,150 668,170" class="line s-red dash" marker-end="url(#ah-red)"/>')
    body.append('<rect x="640" y="172" width="54" height="26" rx="5" class="t-red" stroke="var(--red)" stroke-dasharray="4 3"/>')
    body.append(text(667, 190, "404!", "mid mono xs b f-red"))
    body.append(text(360, 306, "each box is a document, each arrow a link: a web", "mid hand lg"))
    svg = fig("".join(body), 720, 318, "Documents on three computers linking to each other, including one broken link",
              "Nobody planned this shape. It grows one link at a time, which is exactly why it scales.")
    (OUT / "ch06-web.svg").write_text(svg)


def page_load():
    s = Seq([("Alice’s browser", 190, "alice"), ("Bob’s server", 530, "bob")], top=86, scale=30)
    s.msg("Alice’s browser", "Bob’s server", 0, 1, "GET /index.mu", step="1")
    s.msg("Bob’s server", "Alice’s browser", 1.3, 2.3, "200 OK (text/markup)", "green", step="1")
    s.note("Alice’s browser", 2.6, "shows the page… and spots &lt;image src=\"/volcano.png\"&gt;", step="2", side="right")
    s.msg("Alice’s browser", "Bob’s server", 3.3, 4.3, "GET /volcano.png", step="2")
    s.msg("Bob’s server", "Alice’s browser", 4.6, 5.6, "200 OK (image/png, 944 bytes)", "green", step="2")
    s.note("Alice’s browser", 6.0, "Alice clicks “homework notes”", step="3", side="right")
    s.msg("Alice’s browser", "Bob’s server", 6.6, 7.6, "GET /homework.mu", step="3")
    s.msg("Bob’s server", "Alice’s browser", 7.9, 8.9, "301 Moved → /school/homework.mu", "orange", step="3")
    s.msg("Alice’s browser", "Bob’s server", 9.3, 10.3, "GET /school/homework.mu", step="4")
    s.msg("Bob’s server", "Alice’s browser", 10.6, 11.6, "200 OK (text/markup)", "green", step="4")
    body, h = s.render()
    steps = ["The browser asks for Bob’s index page, and gets back a markup document.",
             "While drawing the page, it finds an image tag. The picture isn’t inside the page, so the browser makes a <em>second</em> request just for it. One page, two requests.",
             "Alice clicks a link to the homework notes. Bob moved that file last week, so the server doesn’t send it. Instead it replies <code>301</code> with a <code>Location</code> header: “it lives over here now”.",
             "Without bothering Alice, the browser asks again at the new location and gets the page. All Alice sees is the page appearing."]
    svg = fig(body, 720, h, "Sequence diagram of a browser fetching a page, then its image, then following a redirect",
              "What really happens when you click around.", steps)
    (OUT / "ch06-pageload.svg").write_text(svg)


if __name__ == "__main__":
    url_parts()
    web_graph()
    page_load()
    print("wrote ch06 figures")
