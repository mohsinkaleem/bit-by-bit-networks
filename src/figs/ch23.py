#!/usr/bin/env python3
"""Generate chapter 23 figures.  python3 src/figs/ch23.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- longest prefix wins

def lpm():
    addr = [10, 1, 3, 99]
    bits = "".join(format(o, "08b") for o in addr)
    x0, cw, gap = 150, 16.5, 8

    def bx(i):
        return x0 + i * cw + (i // 8) * gap

    b = [text(14, 30, "Looking up", "sm b"), text(14, 48, "10.1.3.99", "mono b")]
    for i, bit in enumerate(bits):
        b.append(f'<rect x="{bx(i):g}" y="18" width="{cw - 2:g}" height="24" rx="3" class="f-card" stroke="var(--line)"/>')
        b.append(text(bx(i) + (cw - 2) / 2, 35, bit, "mid mono sm b"))
    for k in range(4):
        b.append(text(bx(8 * k) + 4 * cw - 1, 58, str(addr[k]), "mid mono xs muted"))
    routes = [("0.0.0.0/0", 0, None, "the internet provider", "match (it matches everything)"),
              ("10.0.0.0/8", 8, None, "drop", "match"),
              ("10.1.0.0/16", 16, None, "the lab building", "match"),
              ("10.1.1.0/24", 24, 22, "the library", "no match: bit 22 is 0 here, but 1 in the address"),
              ("10.1.3.0/24", 24, None, "this building", "match"),
              ("10.1.3.99/32", 32, None, "the library (one server moved)", "match, and the longest ★")]
    y = 78
    for name, plen, miss, where, verdict in routes:
        win = plen == 32
        b.append(text(14, y + 16, name, "mono sm b" + (" f-green" if win else "")))
        if plen == 0:
            b.append(f'<line x1="{bx(0):g}" y1="{y + 12}" x2="{bx(31) + cw:g}" y2="{y + 12}" class="line s-muted" stroke-dasharray="3 5" stroke-width="2"/>')
        else:
            end = miss if miss is not None else plen
            if end:
                b.append(f'<rect x="{bx(0):g}" y="{y + 2}" width="{bx(end - 1) + cw - 2 - bx(0):g}" height="20" rx="4" '
                         f'class="{"t-green" if not miss else "t-yellow"}" stroke="{"var(--green)" if not miss else "var(--yellow)"}" stroke-width="{2.5 if win else 1.5}"/>')
            if miss is not None:
                b.append(f'<rect x="{bx(miss):g}" y="{y + 2}" width="{cw - 2:g}" height="20" rx="3" class="t-red" stroke="var(--red)" stroke-width="2"/>')
                b.append(text(bx(miss) + (cw - 2) / 2, y + 17, "0", "mid mono sm b f-red"))
                b.append(f'<rect x="{bx(miss + 1):g}" y="{y + 2}" width="{bx(plen - 1) + cw - 2 - bx(miss + 1):g}" height="20" rx="3" class="f-none" stroke="var(--red)" stroke-dasharray="3 3"/>')
        say = verdict if miss else f"{verdict}   → {where}"
        b.append(text(bx(0) + 4, y + 36, say, "xs " + ("f-red" if miss else "f-green b" if win else "muted")))
        y += 44
    # the result column sits on top of the bars' right-hand end, so draw it last with a halo
    svg = fig("".join(b), 720, y + 6,
              "The 32 bits of 10.1.3.99 compared with six routes of different prefix lengths; five match, and the /32 is the longest",
              "Every route whose prefix bits all agree with the address is a match. The one with the most bits wins.")
    (OUT / "ch23-lpm.svg").write_text(svg)


# ---------------------------------------------------------------- classes, then CIDR

def classful():
    x0, w = 150, 520
    per = w / 32
    rows = [("Class A", "0", 8, "126 networks of 16,777,214 computers", "t-red", "var(--red)"),
            ("Class B", "10", 16, "16,384 networks of 65,534", "t-orange", "var(--orange)"),
            ("Class C", "110", 24, "2,097,152 networks of 254", "t-yellow", "var(--yellow)")]
    b = [text(14, 22, "1981 to 1993: the first bits of an address said where the network part ended", "sm b")]
    y = 36
    for name, lead, plen, what, cls, stroke in rows:
        b.append(text(14, y + 20, name, "sm b"))
        b.append(f'<rect x="{x0}" y="{y + 4}" width="{plen * per:g}" height="24" rx="4" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(f'<rect x="{x0 + plen * per:g}" y="{y + 4}" width="{(32 - plen) * per:g}" height="24" rx="4" class="t-green" stroke="var(--green)" stroke-width="1.5"/>')
        b.append(text(x0 + 6, y + 21, lead + "…", "mono xs b"))
        b.append(text(x0 + plen * per / 2 + 10, y + 21, "network", "mid xs"))
        b.append(text(x0 + plen * per + (32 - plen) * per / 2, y + 21, "computer", "mid xs"))
        b.append(text(x0, y + 44, what, "xs muted"))
        y += 54
    b.append(f'<line x1="14" y1="{y}" x2="706" y2="{y}" class="grid"/>')
    y += 22
    b.append(text(14, y, "Since 1993 (CIDR): the slash says where it ends, and it can go anywhere", "sm b"))
    y += 12
    plen = 21
    b.append(text(14, y + 20, "/21", "sm b"))
    b.append(f'<rect x="{x0}" y="{y + 4}" width="{plen * per:g}" height="24" rx="4" class="t-blue" stroke="var(--blue)" stroke-width="1.5"/>')
    b.append(f'<rect x="{x0 + plen * per:g}" y="{y + 4}" width="{(32 - plen) * per:g}" height="24" rx="4" class="t-green" stroke="var(--green)" stroke-width="1.5"/>')
    b.append(text(x0 + plen * per / 2, y + 21, "network: 21 bits", "mid xs"))
    b.append(text(x0 + plen * per + (32 - plen) * per / 2, y + 21, "11 bits", "mid xs"))
    b.append(text(x0, y + 44, "2,046 computers: just right for a company of 2,000, which used to need a whole class B (and waste 63,000 addresses)", "xs muted"))
    svg = fig("".join(b), 720, y + 56, "Class A, B and C addresses with fixed network sizes, compared with a CIDR /21",
              "Classes came in three sizes, and nothing in between. CIDR lets a network be any power-of-two size.")
    (OUT / "ch23-classful.svg").write_text(svg)


# ---------------------------------------------------------------- aggregation

def aggregate():
    b = []
    custs = [("198.18.0.0/24", "a school"), ("198.18.1.0/24", "a bakery"),
             ("198.18.2.0/24", "a clinic"), ("198.18.3.0/24", "a library")]
    for i, (net, who) in enumerate(custs):
        y = 26 + i * 56
        moved = i == 2
        b.append(f'<g data-show="{"1-2" if moved else "1"}"><rect x="14" y="{y}" width="150" height="44" rx="8" class="t-green" stroke="var(--green)" stroke-width="1.5"/>'
                 + text(89, y + 19, who, "mid xs b") + text(89, y + 35, net, "mid mono xs") + "</g>")
        b.append(f'<g data-show="{"1-2" if moved else "1"}"><line x1="164" y1="{y + 22}" x2="236" y2="130" class="line s-muted" stroke-width="1.5"/></g>')
    b.append(f'<g data-show="3"><rect x="14" y="138" width="150" height="44" rx="8" class="t-purple" stroke="var(--purple)" stroke-width="2"/>'
             + text(89, 157, "the clinic (moved)", "mid xs b") + text(89, 173, "198.18.2.0/24", "mid mono xs")
             + '<path d="M164,160 C220,200 250,236 300,236" class="line s-purple" stroke-width="2"/></g>')
    b.append('<use href="#router" x="236" y="104" width="76" height="50"/>')
    b.append(text(274, 170, "Northnet", "mid sm b"))
    b.append(text(274, 186, "(the old provider)", "mid xs muted"))
    b.append('<g data-show="3"><use href="#router" x="300" y="212" width="60" height="40"/>'
             + text(330, 266, "Southnet", "mid xs b") + '<line x1="360" y1="232" x2="470" y2="170" class="line s-purple" stroke-width="2"/></g>')
    b.append('<line x1="312" y1="128" x2="470" y2="128" class="line s-muted" stroke-width="2"/>')
    b.append('<rect x="470" y="30" width="236" height="220" rx="10" class="f-card" stroke="var(--line)" stroke-width="1.5"/>')
    b.append(text(588, 52, "a router elsewhere on", "mid xs b"))
    b.append(text(588, 66, "the internet has to know:", "mid xs b"))
    b.append('<g data-show="=1">' + "".join(
        text(486, 96 + i * 22, f"{net} → Northnet", "mono xs") for i, (net, _) in enumerate(custs))
             + text(588, 196, "4 routes", "mid sm b f-orange") + "</g>")
    b.append('<g data-show="=2">' + text(486, 96, "198.18.0.0/22 → Northnet", "mono xs")
             + text(588, 196, "1 route", "mid sm b f-green") + "</g>")
    b.append('<g data-show="=3">' + text(486, 96, "198.18.0.0/22 → Northnet", "mono xs")
             + text(486, 118, "198.18.2.0/24 → Southnet", "mono xs b", style="fill:var(--purple)")
             + text(588, 170, "198.18.2.9: both match;", "mid xs") + text(588, 186, "the /24 is longer, so Southnet", "mid xs")
             + text(588, 214, "2 routes", "mid sm b f-orange") + "</g>")
    steps = ["An internet provider gives four customers a /24 each. If it told the rest of the internet about each one separately, every router in the world would need four entries for them.",
             "But the four networks sit side by side: together they’re exactly 198.18.0.0/22. So the provider announces just that one. This is <strong>aggregation</strong> (or “summarization”), and it’s the whole point of CIDR.",
             "The clinic moves to a different provider, and takes its addresses with it. Southnet announces 198.18.2.0/24. Routers elsewhere keep Northnet’s /22 and add Southnet’s /24, and longest-prefix match sends the clinic’s traffic the right way. The exception works, but it costs everyone an extra entry."]
    svg = fig("".join(b), 720, 280, "Four neighbouring customer networks announced as one aggregate route, then one customer moving to another provider",
              "Aggregation: announce one big route instead of many small ones. (198.18.0.0/15 is set aside for testing, so these addresses belong to nobody.)", steps)
    (OUT / "ch23-aggregate.svg").write_text(svg)


# ---------------------------------------------------------------- flooding

CAMPUS_POS = {"gateway": (70, 150), "main": (220, 150), "library": (390, 70), "lab": (390, 230),
              "dorms": (580, 70), "sports": (580, 230)}
CAMPUS_LINKS = [("gateway", "main", 1), ("main", "library", 10), ("main", "lab", 10), ("library", "lab", 10),
                ("library", "dorms", 10), ("lab", "sports", 100), ("dorms", "sports", 10)]


def campus_base(b, highlight=()):
    for a, c, cost in CAMPUS_LINKS:
        (x1, y1), (x2, y2) = CAMPUS_POS[a], CAMPUS_POS[c]
        b.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="line s-line" stroke-width="5"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        b.append(f'<rect x="{mx - 14:g}" y="{my - 10:g}" width="28" height="18" rx="4" class="f-surface" stroke="var(--line)"/>')
        b.append(text(mx, my + 4, str(cost), "mid mono xs b"))
    for name, (x, y) in CAMPUS_POS.items():
        b.append(f'<use href="#router" x="{x - 28}" y="{y - 18}" width="56" height="36"/>')
        b.append(text(x, y + 34, name, "mid xs b halo"))


def flood():
    b = []
    campus_base(b)

    def arrow(a, c, step, dup=False, frac=0.72):
        (x1, y1), (x2, y2) = CAMPUS_POS[a], CAMPUS_POS[c]
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        nx, ny = (y2 - y1) / length * 14, -(x2 - x1) / length * 14     # run beside the cable, not on it
        x1, y1, x2, y2 = x1 + nx, y1 + ny, x2 + nx, y2 + ny
        ex, ey = x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac
        sx, sy = x1 + (x2 - x1) * 0.22, y1 + (y2 - y1) * 0.22
        cls = "muted" if dup else "orange"
        out = f'<g data-show="{step}"><line x1="{sx:g}" y1="{sy:g}" x2="{ex:g}" y2="{ey:g}" class="line s-{cls}" stroke-width="3.5" marker-end="url(#ah-{cls})"/>'
        if dup:
            out += (f'<path d="M{ex - 7:g},{ey - 7:g} l14,14 M{ex + 7:g},{ey - 7:g} l-14,14" class="line s-red" stroke-width="3"/>')
        return out + "</g>"

    def got(name, step):
        x, y = CAMPUS_POS[name]
        return f'<g data-show="{step}"><circle cx="{x + 30}" cy="{y - 18}" r="9" class="f-orange"/>' + text(x + 30, y - 14, "✓", "mid xs b", style="fill:#fff") + "</g>"

    b.append('<g data-show="1-4"><rect x="250" y="4" width="200" height="40" rx="6" class="t-orange" stroke="var(--orange)" stroke-width="1.5"/>'
             + text(350, 20, "library, #1: main 10,", "mid mono xs b") + text(350, 36, "lab 10, dorms 10", "mid mono xs b") + "</g>")
    b.append(got("library", "1"))
    for n in ("main", "lab", "dorms"):
        b.append(arrow("library", n, "=2"))
        b.append(got(n, "2"))
    b.append(arrow("main", "gateway", "=3"))
    b.append(arrow("lab", "sports", "=3"))
    b.append(arrow("main", "lab", "=3", dup=True, frac=0.62))
    b.append(arrow("lab", "main", "=3", dup=True, frac=0.62))
    b.append(arrow("dorms", "sports", "=3", dup=True))
    b.append(got("gateway", "3"))
    b.append(got("sports", "3"))
    b.append(arrow("sports", "dorms", "=4", dup=True))
    b.append('<g data-show="5">' + "".join(
        f'<rect x="{x + 18}" y="{y - 30}" width="26" height="22" rx="3" class="t-blue" stroke="var(--blue)" stroke-width="1.5"/>'
        f'<path d="M{x + 22},{y - 14} l6,-8 l6,5 l6,-7" class="line s-blue" stroke-width="1.5"/>'
        for x, y in CAMPUS_POS.values()) + "</g>")
    steps = ["The library’s router writes a <strong>link-state advertisement</strong>: who it is, its cables, what each one costs, and a sequence number. It’s news about the library router, and nothing else.",
             "It sends the advertisement to every neighbour. Each one keeps a copy in its <strong>link-state database</strong>.",
             "Each neighbour passes it on to all of <em>its</em> neighbours, except the one it came from. Main and the lab send it to each other, but both already have it (the same sequence number), so they drop the copy. Sports hears it from the lab first, so the copy from the dorms is dropped too.",
             "Sports passes it on to the dorms, which already has it. Nobody has anything new to pass on, so the flood stops by itself: every router got the advertisement exactly once, in 3 rounds.",
             "Every router does the same with its own advertisement. Now all six have the same database: a complete map of the campus, with every cable and every cost. Each one works out its own shortest paths from it."]
    svg = fig("".join(b), 720, 280, "The library router's link-state advertisement flooding across a campus of six routers, with duplicate copies dropped",
              "Flooding: pass new news to everyone else, and ignore old news.", steps)
    (OUT / "ch23-flood.svg").write_text(svg)


# ---------------------------------------------------------------- becoming neighbours, from the real capture

def adjacency():
    seq = Seq([("library (10.255.0.1)", 150, None), ("main (10.255.0.3)", 570, None)], top=40, scale=34, head=False)
    L, M = "library (10.255.0.1)", "main (10.255.0.3)"
    seq.msg(L, M, 0.3, 0.8, "Hello: “I can hear: nobody”", "navy", step="1", sub="0.000 s, to 224.0.0.5")
    seq.msg(M, L, 1.4, 1.9, "Hello: “I can hear: nobody”", "purple", step="1", sub="0.005 s")
    seq.note(L, 2.7, "…10 seconds…", step="2")
    seq.msg(L, M, 3.4, 3.9, "Hello: “I can hear: 10.255.0.3”", "navy", step="2", sub="10.001 s: both know the cable works both ways")
    seq.msg(M, L, 5.0, 5.5, "Database Description: “here’s what I know”", "purple", step="3", sub="a list of advertisements: who, and which sequence number")
    seq.msg(L, M, 6.4, 6.9, "Database Description: “and here’s mine”", "navy", step="3")
    seq.msg(M, L, 7.8, 8.3, "LS Request: “send me yours, please”", "purple", step="4")
    seq.msg(L, M, 9.2, 9.7, "LS Update: the advertisements themselves", "navy", step="4", sub="all in the same millisecond")
    seq.msg(M, L, 10.8, 11.3, "LS Acknowledge: “got them”", "purple", step="5", sub="12.502 s")
    seq.note(L, 12.3, "Full: same database on both sides", step="5", cls="f-green")
    body, bottom = seq.render(20)
    steps = ["Each router multicasts a Hello every 10 seconds on each cable, to 224.0.0.5 (“all OSPF routers”). It says who it is, how often it says hello, how long to wait before giving up on a neighbour, and which routers it can already hear. Neither can hear the other yet.",
             "Ten seconds later, each Hello lists the other router. Now both know the cable works in both directions, and they’re neighbours (“2-Way”).",
             "They compare notes. Each sends a short summary of the advertisements in its database, without the details.",
             "Each asks for whatever the other has and it doesn’t (or has a newer copy of), and gets the full advertisements back.",
             "Every advertisement received is acknowledged, or it would be sent again. When nothing is missing on either side, the neighbours are <strong>Full</strong>, and any change from now on is flooded to them straight away."]
    svg = fig(body, 720, bottom, "The OSPF messages exchanged by two routers becoming neighbours, from a real capture: hellos, database descriptions, requests, updates and acknowledgements",
              "Two real routers becoming neighbours, from this chapter’s capture (<code>labs/ch23/ospf.pcap</code>).", steps)
    (OUT / "ch23-adjacency.svg").write_text(svg)


# ---------------------------------------------------------------- pulled out vs silent: real ping timings

def dead():
    b = []
    # --- experiment 1: 25 pings, 0.2 s apart. Replies 1-10 direct, 11-13 lost, 14-25 the long way.
    x0, sx = 40, 120        # 120 px per second
    b.append(text(14, 22, "1. The cable is pulled out: both routers notice at once", "sm b"))
    b.append(f'<line x1="{x0}" y1="62" x2="{x0 + 5.2 * sx:g}" y2="62" class="grid"/>')
    for k in range(6):
        b.append(f'<line x1="{x0 + k * sx}" y1="58" x2="{x0 + k * sx}" y2="66" class="grid"/>')
        b.append(text(x0 + k * sx, 80, f"{k} s", "mid xs muted"))
    for i in range(25):
        x = x0 + i * 0.2 * sx + 6
        if i < 10:
            b.append(f'<circle cx="{x:g}" cy="50" r="5" class="f-green"/>')
        elif i < 13:
            b.append(f'<path d="M{x - 4:g},{46} l8,8 M{x + 4:g},46 l-8,8" class="line s-red" stroke-width="2.5"/>')
        else:
            b.append(f'<circle cx="{x:g}" cy="50" r="5" class="f-blue"/>')
    cut = x0 + 2.0 * sx
    b.append(f'<line x1="{cut:g}" y1="32" x2="{cut:g}" y2="70" class="line s-orange" stroke-width="2" stroke-dasharray="4 3"/>')
    b.append(text(cut + 4, 40, "✂ pulled out", "xs b f-orange"))
    b.append(text(x0 + 5.3 * sx, 46, "3 pings lost: 0.6 s", "xs b f-red"))
    b.append(text(x0 + 5.3 * sx, 60, "then ttl 63: one hop more", "xs f-blue"))
    # --- experiment 2: 60 pings, 1 s apart. Replies 1-3, lost 4-38, replies 39-60.
    y2 = 130
    sx2 = 10.5
    b.append(text(14, y2 - 18, "2. The cable goes silent, but stays plugged in: nobody notices until the Hellos stop", "sm b"))
    b.append(f'<line x1="{x0}" y1="{y2 + 40}" x2="{x0 + 60 * sx2:g}" y2="{y2 + 40}" class="grid"/>')
    for k in range(0, 61, 10):
        b.append(f'<line x1="{x0 + k * sx2:g}" y1="{y2 + 36}" x2="{x0 + k * sx2:g}" y2="{y2 + 44}" class="grid"/>')
        b.append(text(x0 + k * sx2, y2 + 58, f"{k} s", "mid xs muted"))
    for i in range(60):
        x = x0 + i * sx2 + 5
        if i < 3:
            b.append(f'<circle cx="{x:g}" cy="{y2 + 28}" r="4" class="f-green"/>')
        elif i < 38:
            b.append(f'<path d="M{x - 3:g},{y2 + 25} l6,6 M{x + 3:g},{y2 + 25} l-6,6" class="line s-red" stroke-width="2"/>')
        else:
            b.append(f'<circle cx="{x:g}" cy="{y2 + 28}" r="4" class="f-blue"/>')
    q = x0 + 3.0 * sx2
    b.append(f'<line x1="{q:g}" y1="{y2 - 4}" x2="{q:g}" y2="{y2 + 46}" class="line s-orange" stroke-width="2" stroke-dasharray="4 3"/>')
    b.append(text(q + 4, y2 + 4, "silent", "xs b f-orange"))
    dead_at = x0 + 37.1 * sx2
    b.append(f'<line x1="{dead_at:g}" y1="{y2 - 4}" x2="{dead_at:g}" y2="{y2 + 46}" class="line s-purple" stroke-width="2" stroke-dasharray="4 3"/>')
    b.append(text(dead_at - 4, y2 + 4, "40 s since main’s last Hello:", "end xs b", style="fill:var(--purple)"))
    b.append(text(dead_at - 4, y2 + 17, "“main is dead”", "end xs b", style="fill:var(--purple)"))
    b.append(text(x0 + 20 * sx2, y2 + 80, "35 pings lost: 35 seconds of nothing", "mid xs b f-red"))
    svg = fig("".join(b), 720, y2 + 92,
              "Two real experiments: pings across a pulled-out cable lose 0.6 seconds, pings across a silent cable lose 35 seconds until OSPF's dead timer runs out",
              "Real pings from the library to the main building, while the cable between them fails. Green went the direct way, blue the long way round, red never arrived.")
    (OUT / "ch23-dead.svg").write_text(svg)


if __name__ == "__main__":
    lpm()
    classful()
    aggregate()
    flood()
    adjacency()
    dead()
    print("wrote ch23 figures")
