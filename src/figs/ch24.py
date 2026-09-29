#!/usr/bin/env python3
"""Generate chapter 24 figures.  python3 src/figs/ch24.py"""
import sys
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def box(x, y, name, sub, cls="f-surface", stroke="var(--line)", w=110, h=40, extra=""):
    return (f'<rect x="{x - w / 2:g}" y="{y - h / 2:g}" width="{w}" height="{h}" rx="8" class="{cls}" stroke="{stroke}" stroke-width="1.8"{extra}/>'
            + text(x, y - 2, name, "mid xs b") + text(x, y + 13, sub, "mid mono xs muted"))


# ---------------------------------------------------------------- who pays whom

def asmap():
    P = {"t1a": (200, 50, "Tier 1 West", "AS64500"), "t1b": (520, 50, "Tier 1 East", "AS64501"),
         "north": (200, 160, "Northnet", "AS64510"), "south": (520, 160, "Southnet", "AS64530"),
         "uni": (110, 270, "University", "AS65001"), "bob": (360, 270, "Bob’s ISP", "AS65002"), "shop": (610, 270, "a shop", "AS65088")}
    cust = [("t1a", "north"), ("t1b", "south"), ("t1a", "south"), ("north", "uni"), ("north", "bob"), ("south", "bob"), ("south", "shop")]
    b = []
    for a, c in cust:
        (x1, y1, *_), (x2, y2, *_) = P[a], P[c]
        b.append(f'<line x1="{x1}" y1="{y1 + 20}" x2="{x2}" y2="{y2 - 20}" class="line s-muted" stroke-width="2.5"/>')
    b.append(f'<line x1="255" y1="50" x2="465" y2="50" class="line s-muted dash" stroke-width="2.5"/>')
    b.append(f'<line x1="255" y1="160" x2="465" y2="160" class="line s-muted dash" stroke-width="2.5"/>')
    for k, (x, y, n, s) in P.items():
        b.append(box(x, y, n, s))
    # step 1: money
    b.append('<g data-show="=1">' + "".join(
        f'<text x="{(P[a][0] + P[c][0]) / 2 + 8:g}" y="{(P[a][1] + P[c][1]) / 2 + 4:g}" class="xs b f-orange halo">£ ↑</text>' for a, c in cust)
             + text(360, 44, "peers: nobody pays", "mid xs b f-green halo") + text(360, 154, "peers", "mid xs b f-green halo") + "</g>")
    # step 2: Northnet's announcements
    def arr(x1, y1, x2, y2, cls, label=None, lx=None, ly=None):
        out = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="line s-{cls}" stroke-width="3.5" marker-end="url(#ah-{cls})"/>'
        if label:
            out += text(lx, ly, label, "xs b halo", style=f"fill:var(--{cls})")
        return out
    b.append('<g data-show="=2">'
             + arr(180, 140, 180, 80, "green", "the university’s route: to everyone", 18, 108)
             + arr(262, 168, 450, 168, "green")
             + arr(170, 182, 118, 244, "blue")
             + arr(214, 182, 330, 250, "blue", "everything, to customers", 238, 222)
             + "</g>")
    b.append('<g data-show="=3">'
             + arr(250, 150, 450, 150, "red") + text(356, 140, "✗ Southnet’s routes to Southnet? no", "mid xs b f-red halo")
             + arr(200, 138, 200, 76, "red") + text(210, 108, "✗ peers’ and providers’ routes go up? no", "xs b f-red halo")
             + "</g>")
    b.append('<g data-show="=4">'
             + f'<path d="M520,180 C520,230 420,262 404,262" class="line s-orange" stroke-width="3.5" marker-end="url(#ah-orange)"/>'
             + f'<path d="M318,262 C260,250 220,220 214,186" class="line s-orange" stroke-width="3.5" marker-end="url(#ah-orange)"/>'
             + text(360, 318, "If Bob’s ISP passed Southnet’s routes to Northnet, it would carry their traffic, and pay both of them to do it.", "mid xs b f-orange")
             + "</g>")
    steps = ["The internet is about 88,000 networks, each run by one organization and called an <strong>autonomous system</strong> (AS), with a number. Most of them buy their connection to the rest of the internet from bigger ones: the customer pays the provider, for “transit”, and the money flows upward. At the top are a dozen or so <strong>tier 1</strong> networks, who pay nobody.",
             "Northnet tells <em>everyone</em> about its own customers’ addresses: its providers, its peers and its other customers. That’s what its customers pay it for: to be reachable. And it tells its customers about everything it knows, because they pay for that too.",
             "But it doesn’t tell its providers or its peers about routes it learned from <em>other</em> providers or peers. If it told Southnet “you can reach Tier 1 West through me”, it would end up carrying traffic between two networks that pay it nothing.",
             "A customer with two providers mustn’t pass routes from one to the other, either. That’s a <strong>route leak</strong>, and it’s one of the most common ways the internet breaks. These two rules, choose customers first and don’t carry traffic for free, are what keep BGP stable, and nobody wrote them into the protocol: they’re just money."]
    svg = fig("".join(b), 720, 330, "Autonomous systems connected as customers, providers and peers, with the rules for which routes each one passes on",
              "Customers, providers and peers: who pays, and who hears what.", steps)
    (OUT / "ch24-asmap.svg").write_text(svg)


# ---------------------------------------------------------------- a path vector, and why it can't loop

def pathvector():
    P = {"uni": (90, 240, "University", "AS65001"), "north": (300, 240, "Northnet", "AS64510"),
         "west": (300, 70, "Tier 1 West", "AS64500"), "east": (590, 70, "Tier 1 East", "AS64501"),
         "south": (590, 240, "Southnet", "AS64530")}
    b = []
    for a, c in [("uni", "north"), ("north", "west"), ("west", "east"), ("north", "east"), ("east", "south")]:
        (x1, y1, *_), (x2, y2, *_) = P[a], P[c]
        b.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="line s-line" stroke-width="4"/>')
    for k, (x, y, n, s) in P.items():
        b.append(box(x, y, n, s, w=116))

    def ann(x, y, path, step, cls="t-green", stroke="var(--green)"):
        w = 16 + 7.4 * len(path)
        return (f'<g data-show="{step}"><rect x="{x - w / 2:g}" y="{y - 12}" width="{w:g}" height="22" rx="5" class="{cls}" stroke="{stroke}"/>'
                + text(x, y + 3, path, "mid mono xs b") + "</g>")

    def arrow(x1, y1, x2, y2, step, cls="green"):
        return f'<g data-show="{step}"><line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="line s-{cls}" stroke-width="3" marker-end="url(#ah-{cls})"/></g>'
    b.append(arrow(152, 226, 236, 226, "1"))
    b.append(ann(194, 206, "10.1.0.0/16: 65001", "1"))
    b.append(arrow(286, 216, 286, 96, "2"))
    b.append(ann(222, 150, "64510 65001", "2"))
    b.append(arrow(356, 222, 526, 110, "2"))
    b.append(ann(395, 150, "64510 65001", "2"))
    b.append(arrow(604, 94, 604, 216, "3"))
    b.append(ann(590, 286, "64501 64510 65001", "3"))
    b.append(arrow(360, 56, 528, 56, "3"))
    b.append(ann(444, 36, "64500 64510 65001", "3"))
    b.append(text(444, 84, "(Tier 1 East already has a shorter one)", "mid xs muted", **{"data-show": "3"}))
    b.append(arrow(552, 102, 380, 216, "4", "red"))
    b.append(ann(525, 186, "64501 64510 65001", "4", cls="t-red", stroke="var(--red)"))
    b.append(f'<g data-show="4"><text x="260" y="294" class="mid hand f-red">“64510? That’s me. It’s a loop: ignore it.”</text></g>')
    steps = ["The university announces its addresses to Northnet. The announcement carries an <strong>AS path</strong>, which starts with just the university’s own number.",
             "Northnet adds its own number to the front, and passes the route on to its two providers. Anyone who hears it now knows the whole list of networks it would pass through.",
             "Each network adds its number and passes it on. Southnet’s route to the university goes through three networks. Unlike Chapter 11’s routers, which only knew a distance, every network can see the whole path…",
             "…so loops are easy to spot. When Tier 1 East offers the route back to Northnet, Northnet finds its own number already in the path, and ignores it. No counting to infinity. BGP is called a <strong>path vector</strong> protocol for this reason."]
    svg = fig("".join(b), 720, 306, "An announcement for 10.1.0.0/16 spreading between five autonomous systems, the AS path growing at each step, and a loop being rejected",
              "The AS path grows by one number at every network.", steps)
    (OUT / "ch24-pathvector.svg").write_text(svg)


# ---------------------------------------------------------------- CERN's real routes

def cern():
    ups = [("GÉANT", "21320", 80, 1, "research"), ("SWITCH & co.", "559, 1103…", 16, 1, "research"),
           ("Hurricane", "6939", 18, 1, "peer"),
           ("IP-Max", "25091", 174, 2, "transit"), ("Cogent", "174", 37, 2, "transit"),
           ("Infomaniak", "29222", 28, 2, "transit"), ("Sunrise", "6730", 7, 2, "transit")]
    b = [text(360, 20, "Routes to CERN’s 188.184.0.0/16, as the world’s networks saw them (RIPE route collectors, 28 September 2026)", "mid sm b")]
    cx, cy = 360, 270
    b.append(f'<rect x="{cx - 80}" y="{cy - 22}" width="160" height="44" rx="10" class="t-blue" stroke="var(--blue)" stroke-width="2"/>')
    b.append(text(cx, cy - 2, "CERN", "mid sm b"))
    b.append(text(cx, cy + 14, "AS513", "mid mono xs"))
    n = len(ups)
    for i, (name, asn, routes, copies, kind) in enumerate(ups):
        x = 60 + i * (600 / (n - 1))
        y = 110
        good = copies == 1
        stroke = "var(--green)" if good else "var(--orange)"
        width = 2 + routes / 16
        b.append(f'<path d="M{x:g},{y + 26} C{x:g},{y + 90} {cx + (x - cx) * 0.25:g},{cy - 70} {cx + (x - cx) * 0.18:g},{cy - 24}" class="line" stroke="{stroke}" stroke-width="{width:g}" style="opacity:0.85"/>')
        b.append(f'<rect x="{x - 44:g}" y="{y - 22}" width="88" height="48" rx="8" class="{"t-green" if good else "t-orange"}" stroke="{stroke}" stroke-width="1.8"/>')
        b.append(text(x, y - 5, name, "mid xs b"))
        b.append(text(x, y + 9, "AS" + asn, "mid mono xs"))
        b.append(text(x, y + 21, f"{routes} routes", "mid xs muted"))
        label = " ".join(["513"] * copies)
        lw = 12 + 7.4 * len(label)
        b.append(f'<rect x="{x - lw / 2:g}" y="{y + 36}" width="{lw:g}" height="18" rx="4" class="f-surface" stroke="{stroke}"/>')
        b.append(text(x, y + 49, label, "mid mono xs b", style=f"fill:{stroke}"))
    b.append(text(160, 74, "research networks and a peer: “… 513”", "mid xs b f-green"))
    b.append(text(560, 74, "paid-for transit: “… 513 513”", "mid xs b f-orange"))
    svg = fig("".join(b), 720, 306, "CERN's upstream networks from real route collector data: research networks see AS513 once, commercial transit providers see it twice",
              "CERN adds an extra copy of its own number on its commercial connections, so those paths look one network longer. Anyone who can reach it through the research networks, does. (Line thickness: how many of the 363 routes went that way.)")
    (OUT / "ch24-cern.svg").write_text(svg)


# ---------------------------------------------------------------- the YouTube hijack

def youtube():
    b = []
    yt, pk, pccw, world = (110, 90), (110, 230), (330, 230), (590, 160)
    b.append(box(*yt, "YouTube", "AS36561", w=120))
    b.append(box(*pk, "Pakistan Telecom", "AS17557", w=130))
    b.append(box(*pccw, "PCCW Global", "AS3491", w=120))
    b.append('<rect x="480" y="60" width="226" height="200" rx="10" class="f-card" stroke="var(--line)" stroke-width="1.5"/>')
    b.append(text(593, 82, "a router anywhere else", "mid xs b"))
    b.append(f'<line x1="170" y1="90" x2="480" y2="120" class="line s-muted" stroke-width="2"/>')
    b.append(f'<line x1="175" y1="230" x2="270" y2="230" class="line s-muted" stroke-width="2"/>')
    b.append(f'<line x1="390" y1="230" x2="480" y2="200" class="line s-muted" stroke-width="2"/>')
    rows = {
        "1": [("208.65.152.0/22 → YouTube", "")],
        "2": [("208.65.152.0/22 → YouTube", ""), ("208.65.153.0/24 → Pakistan", "b f-red")],
        "3": [("208.65.152.0/22 → YouTube", ""), ("208.65.153.0/24 → Pakistan", "f-red"), ("208.65.153.0/24 → YouTube", "")],
        "4": [("208.65.152.0/22 → YouTube", ""), ("208.65.153.0/24 → Pakistan", "f-red"), ("208.65.153.0/25 → YouTube", "b f-green"), ("208.65.153.128/25 → YouTube", "b f-green")],
    }
    verdict = {"1": ("videos go to YouTube", "f-green"), "2": ("the /24 is longer: videos go to Pakistan!", "f-red"),
               "3": ("two equal /24s: a coin toss", "f-orange"), "4": ("the /25s are longest: back to YouTube", "f-green")}
    for step, lines in rows.items():
        g = [f'<g data-show="={step}">']
        for i, (t, cls) in enumerate(lines):
            g.append(text(494, 110 + i * 22, t, "mono xs " + cls))
        g.append(text(593, 238, verdict[step][0], "mid xs b " + verdict[step][1]))
        g.append("</g>")
        b.append("".join(g))
    b.append('<g data-show="2-3"><path d="M175,218 C220,190 250,200 272,220" class="line s-red" stroke-width="3" marker-end="url(#ah-red)"/>'
             '<path d="M392,222 C430,200 450,190 478,184" class="line s-red" stroke-width="3" marker-end="url(#ah-red)"/>'
             + text(270, 180, "208.65.153.0/24", "mid mono xs b f-red halo") + "</g>")
    b.append('<g data-show="3-4"><path d="M172,84 C300,60 400,80 478,104" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/></g>')
    steps = ["24 February 2008. YouTube announces its addresses as one block, 208.65.152.0/22. Routers everywhere send YouTube’s traffic its way.",
             "Pakistan’s government orders YouTube blocked. Pakistan Telecom does it by announcing a route for 208.65.153.0/24, the part of YouTube’s block with its web servers, pointing nowhere. The announcement was meant to stay inside Pakistan, but its provider, PCCW, passes it on to the whole world. It’s a /24, longer than YouTube’s /22, so within minutes routers everywhere send YouTube’s traffic to Pakistan, where it’s thrown away.",
             "About 80 minutes later, YouTube starts announcing 208.65.153.0/24 itself. Now routers see two equally specific routes, and each picks one by AS path length and its own preferences. Some traffic comes back.",
             "Ten minutes after that, YouTube announces the two halves, 208.65.153.0/25 and 208.65.153.128/25. They’re longer than anything Pakistan Telecom sent, and longest-prefix match wins again, for YouTube this time. About two hours after it all began, PCCW stops passing on the bad route."]
    svg = fig("".join(b), 720, 280, "The 2008 YouTube hijack: a more specific /24 announced by Pakistan Telecom wins over YouTube's /22, until YouTube announces even more specific /25s",
              "The YouTube hijack of 2008, as a routing table far away saw it.", steps)
    (OUT / "ch24-youtube.svg").write_text(svg)




# ---------------------------------------------------------------- one real UPDATE, byte by byte

def update():
    sys.path.insert(0, str(OUT.parent.parent / "labs" / "ch24"))
    from bgp_speaker import update_msg
    msg = update_msg(["10.1.0.0/16"], path=[65001], next_hop="10.0.1.1")
    groups = [("marker", 0, 16, "16 bytes of ff", "f-card", "var(--line)"),
              ("length", 16, 18, "46 bytes", "t-purple", "var(--purple)"),
              ("type", 18, 19, "2 = UPDATE", "t-purple", "var(--purple)"),
              ("withdrawn", 19, 21, "none", "t-red", "var(--red)"),
              ("attributes", 21, 23, "20 bytes", "t-yellow", "var(--yellow)"),
              ("ORIGIN", 23, 27, "IGP", "t-yellow", "var(--yellow)"),
              ("AS_PATH", 27, 36, "a sequence of 1: 65001", "t-orange", "var(--orange)"),
              ("NEXT_HOP", 36, 43, "10.0.1.1", "t-yellow", "var(--yellow)"),
              ("routes (NLRI)", 43, 46, "/16: 10.1", "t-green", "var(--green)")]
    b = []
    x, y, bw = 14, 40, 21
    for name, a, c, meaning, cls, stroke in groups:
        chunk = msg[a:c]
        if name == "marker":
            w = 120
        else:
            w = max(78, bw * len(chunk))                  # room for the labels, even for one byte
        pad = (w - 3 - bw * len(chunk)) / 2 if name != "marker" else 0
        if x + w > 706:
            x, y = 14, y + 98
        b.append(f'<rect x="{x}" y="{y}" width="{w - 3}" height="30" rx="5" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        if name == "marker":
            b.append(text(x + (w - 3) / 2, y + 20, "ff ff … ff", "mid mono xs b"))
        else:
            for i, byte in enumerate(chunk):
                b.append(text(x + pad + i * bw + bw / 2, y + 20, f"{byte:02x}", "mid mono xs b"))
        b.append(text(x + (w - 3) / 2, y - 8, name, "mid xs b"))
        b.append(text(x + (w - 3) / 2, y + 48, meaning, "mid xs muted"))
        x += w + 6
    b.append(text(14, y + 80, "Each attribute is: flags (40 = “every router must understand this, and pass it on”), a type number, a length, then the value.", "xs"))
    svg = fig("".join(b), 720, y + 94, "The 46 bytes of a real BGP UPDATE announcing 10.1.0.0/16 with AS path 65001, field by field",
              "The university’s announcement, from <code>bgp_speaker.py --hex</code>: a whole route in 46 bytes.")
    (OUT / "ch24-update.svg").write_text(svg)


if __name__ == "__main__":
    asmap()
    pathvector()
    cern()
    youtube()
    update()
    print("wrote ch24 figures")
