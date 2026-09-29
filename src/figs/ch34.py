#!/usr/bin/env python3
"""Generate chapter 34 figures.  python3 src/figs/ch34.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def box(x, y, w, h, label, cls="f-card", stroke="var(--line)", sub=None, sub2=None):
    out = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" class="{cls}" stroke="{stroke}" stroke-width="1.6"/>'
    dy = -7 if sub and sub2 else 0 if sub else 4
    out += text(x + w / 2, y + h / 2 + dy - (4 if sub else 0), label, "mid sm b")
    if sub:
        out += text(x + w / 2, y + h / 2 + dy + 12, sub, "mid xs muted")
    if sub2:
        out += text(x + w / 2, y + h / 2 + dy + 26, sub2, "mid xs muted")
    return out


def arrow(x1, y1, x2, y2, cls="s-ink", w=2):
    mk = "ink" if cls == "s-ink" else cls[2:]
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="{w}" marker-end="url(#ah-{mk})"/>'


# ---------------------------------------------------------------- forward and reverse proxies

def proxies():
    b = [text(180, 22, "a forward proxy works for the users", "mid sm b"), text(540, 22, "a reverse proxy works for the website", "mid sm b"),
         '<line x1="360" y1="10" x2="360" y2="236" class="grid" stroke-dasharray="4 4"/>']
    # forward: people on the left, proxy, sites on the right
    for i, who in enumerate(("alice", "bob", "carol")):
        b.append(f'<use href="#{who}-head" x="20" y="{44 + i * 60}" width="44" height="44"/>')
        b.append(arrow(68, 66 + i * 60, 132, 126, "s-muted", 1.6))
    b.append(box(136, 96, 90, 60, "proxy", "t-purple", "var(--purple)", "the school’s"))
    for i, site in enumerate(("example.org", "bbc.co.uk", "wikipedia")):
        b.append(box(262, 52 + i * 52, 88, 34, site))
        b.append(arrow(228, 126, 258, 69 + i * 52, "s-muted", 1.6))
    b.append(text(180, 214, "It can log, filter and cache for everyone behind it.", "mid xs"))
    b.append(text(180, 230, "The sites see the proxy’s address, not the users’.", "mid xs"))
    # reverse: internet users on the left, proxy, servers on the right
    b.append(f'<use href="#cloud" x="376" y="80" width="100" height="60"/>')
    b.append(text(426, 116, "everyone", "mid xs b"))
    b.append(arrow(478, 112, 526, 122, "s-muted", 1.8))
    b.append(box(530, 96, 90, 60, "reverse", "t-orange", "var(--orange)", "proxy", "(a load balancer)"))
    for i in range(3):
        b.append(f'<use href="#server" x="{660}" y="{44 + i * 56}" width="30" height="48"/>')
        b.append(arrow(622, 126, 656, 68 + i * 56, "s-muted", 1.6))
    b.append(text(540, 214, "It can spread the load, end TLS, cache, and hide", "mid xs"))
    b.append(text(540, 230, "the servers. Visitors only ever see the proxy.", "mid xs"))
    svg = fig("".join(b), 720, 244, "A forward proxy sits in front of users and fetches sites for them; a reverse proxy sits in front of servers and answers for them",
              "Two kinds of middleman. They’re the same program in different places: a proxy takes a request, and makes it again, somewhere else.")
    (OUT / "ch34-proxies.svg").write_text(svg)


# ---------------------------------------------------------------- layer 4 and layer 7 balancing

def layers():
    b = []
    rows = [("layer 4 (transport)", "sees: addresses, ports, protocol", "a connection to 104.20.26.136:443 → pick a server, forward every packet of it",
             "fast, simple, and can't see inside TLS", "t-blue", "var(--blue)"),
            ("layer 7 (application)", "sees: the HTTP request itself", "GET /photos/beans.jpg, Host: garden.example, Cookie: … → the photo servers",
             "ends TLS, so it can read, route and rewrite requests", "t-green", "var(--green)")]
    for i, (name, sees, example, note, cls, stroke) in enumerate(rows):
        y = 16 + i * 104
        b.append(f'<rect x="20" y="{y}" width="680" height="90" rx="10" class="{cls}" stroke="{stroke}" stroke-width="1.6"/>')
        b.append(text(36, y + 24, name, "sm b"))
        b.append(text(36, y + 44, sees, "xs b"))
        b.append(text(36, y + 62, example, "xs mono"))
        b.append(text(36, y + 80, note, "xs muted"))
    svg = fig("".join(b), 720, 228, "What a layer 4 load balancer can see compared with a layer 7 one",
              "Two kinds of load balancer. Big sites use both: layer 4 balancers spread connections over a fleet of layer 7 proxies, which hold the certificates, read the requests, and pass them on. QUIC’s visible connection ID (Chapter 33) exists so that layer 4 balancers can keep each connection on the same server.")
    (OUT / "ch34-layers.svg").write_text(svg)


# ---------------------------------------------------------------- a real CDN, and its caches

def cdn():
    b = []
    nodes = [(20, "Bob", "#bob-head"), (170, "Fastly, nearby", "edge: cache-XXX"), (360, "Fastly, Ashburn", "shield: cache-iad"),
             (560, "python.org", "the origin")]
    b.append(f'<use href="#bob-head" x="30" y="56" width="56" height="56"/>')
    b.append(text(58, 128, "Bob", "mid sm b"))
    b.append(box(150, 58, 150, 58, "Fastly, nearby", "t-green", "var(--green)", "edge cache: XXX"))
    b.append(box(350, 58, 150, 58, "Fastly, Ashburn", "t-blue", "var(--blue)", "shield cache: IAD"))
    b.append(box(560, 58, 140, 58, "python.org", "f-card", "var(--line)", "the origin server"))
    b.append('<g data-show="2">' + arrow(90, 80, 146, 80, "s-ink") + arrow(146, 96, 90, 96, "s-green") + text(118, 150, "HIT", "mid sm b f-green") + "</g>")
    b.append('<g data-show="3">' + arrow(302, 80, 346, 80, "s-ink") + arrow(502, 80, 556, 80, "s-ink")
             + arrow(556, 96, 502, 96, "s-orange") + arrow(346, 96, 302, 96, "s-orange") + text(528, 150, "MISS", "mid sm b f-orange")
             + text(324, 150, "HIT, next time", "mid xs b f-green") + "</g>")
    b.append('<g data-show="1">' + text(360, 30, "www.python.org  CNAME  dualstack.python.map.fastly.net  →  151.101.64.223", "mid xs mono b") + "</g>")
    b.append(text(360, 186, "x-served-by: cache-iad-…-IAD, cache-iad-…-IAD, cache-iad-…-IAD, cache-XXX-…-XXX", "mid xs mono"))
    b.append(text(360, 204, "x-cache: MISS, HIT, HIT      x-cache-hits: 0, 273, 18      age: 1704", "mid xs mono"))
    steps = ["The website’s DNS name is a <strong>CNAME</strong> (Chapter 29) pointing into the content delivery network’s own names, which answer with addresses of a CDN site near the person asking.",
             "Bob’s request reaches an <strong>edge</strong> cache near him. If it has a fresh copy (Chapter 30’s rules), it answers at once: here, a HIT, and the real server never hears about it.",
             "If not, the edge asks a bigger <strong>shield</strong> cache near the real server, and only if that misses too does anyone bother the <strong>origin</strong>. The headers are a record of the journey: this copy was fetched from python.org 1,704 seconds ago (a MISS), and has since been served from the Ashburn cache 273 times."]
    svg = fig("".join(b), 720, 214, "A content delivery network: Bob's request is answered by a nearby edge cache, which falls back to a shield cache and then the origin",
              "A real content delivery network: <code>curl -sI https://www.python.org/</code> from Grandpa’s Pi. (Fastly’s names contain city codes; the one near the Pi is blanked out as XXX.)", steps)
    (OUT / "ch34-cdn.svg").write_text(svg)


# ---------------------------------------------------------------- anycast: the root servers from the Pi

def anycast():
    # (letter, ms, where) from labs/ch34/anycast.py on the Pi; nearby cities blanked
    data = [("e", 2.9, "XXX"), ("d", 3.5, "(its name doesn’t say)"), ("j", 18.1, "(its name doesn’t say)"), ("k", 21.2, "XXX"),
            ("m", 40.2, "XXX"), ("i", 40.3, "XXX"), ("b", 42.9, "Singapore"), ("l", 59.0, "XXX"), ("g", 121.1, "(its name doesn’t say)"),
            ("a", 127.0, "Tokyo"), ("h", 147.1, "London"), ("c", 154.6, "Paris")]
    b = [text(20, 20, "The same 13 addresses, asked from Grandpa’s Pi: which copy answered, and how long the round trip took", "xs b")]
    x0, scale = 150, 2.6
    for i, (letter, ms, where) in enumerate(data):
        y = 34 + i * 19
        b.append(text(20, y + 12, f"{letter}.root-servers.net", "xs mono"))
        cls = "var(--green)" if ms < 25 else "var(--orange)" if ms < 100 else "var(--red)"
        b.append(f'<rect x="{x0}" y="{y}" width="{ms * scale:.1f}" height="14" rx="3" fill="{cls}" fill-opacity="0.75"/>')
        b.append(text(x0 + ms * scale + 6, y + 11, f"{ms:g} ms  {where}", "xs"))
    b.append(text(20, 280, "Every root server letter is really hundreds of machines around the world, all using the same address. The", "xs"))
    b.append(text(20, 296, "one you reach is the one your network’s routes lead to: usually, but not always, the nearest. (f-root didn’t answer.)", "xs"))
    svg = fig("".join(b), 720, 306, "Bar chart of round-trip times to the twelve answering DNS root servers from the Pi, from 3 ms to 155 ms, with the city of the instance that answered",
              "Anycast, measured with <code>anycast.py</code>. The name each server gives (like <code>nnn1-jptyo-2</code> for a-root) says where it is. Nearby cities are blanked out as XXX.")
    (OUT / "ch34-anycast.svg").write_text(svg)


def anycast_how():
    sites = [(120, 150, "site A"), (360, 60, "site B"), (600, 150, "site C")]
    b = []
    for x, y, name in sites:
        b.append(f'<use href="#server" x="{x - 14}" y="{y - 22}" width="28" height="44"/>')
        b.append(text(x, y + 38, name, "mid xs b"))
        b.append(text(x, y + 52, "announces 1.1.1.0/24", "mid xs mono muted"))
    users = [(60, 250, 0), (330, 250, 1), (660, 250, 2), (240, 250, 0), (470, 250, 1)]
    for ux, uy, s in users:
        sx, sy, _ = sites[s]
        b.append(f'<circle cx="{ux}" cy="{uy}" r="7" class="f-ink"/>')
        b.append(f'<g data-show="=2">' + f'<path d="M{ux},{uy - 8} L{sx},{sy + 58}" class="line s-green" stroke-width="1.8" marker-end="url(#ah-green)"/></g>')
        s2 = 0 if s == 1 else s
        sx2, sy2, _ = sites[s2]
        b.append(f'<g data-show="=3">' + f'<path d="M{ux},{uy - 8} L{sx2},{sy2 + 58}" class="line s-{"orange" if s == 1 else "green"}" stroke-width="1.8" marker-end="url(#ah-{"orange" if s == 1 else "green"})"/></g>')
    b.append('<g data-show="3"><path d="M340,40 l40,40 M380,40 l-40,40" class="line s-red" stroke-width="4"/></g>')
    b.append(text(360, 290, "people (and their resolvers) in different places", "mid xs muted"))
    steps = ["Three sites, far apart, all announce the same block of addresses with BGP (Chapter 24). To the internet’s routers, they look like three routes to the same place.",
             "Each network picks its best route, usually the shortest AS path, so each person reaches the site nearest to them, in network terms. Nobody’s computer does anything special: the address is the same everywhere.",
             "If a site fails, it stops announcing, and within seconds BGP sends its people to the next best site. The same trick spreads out attacks: a flood aimed at the address lands on hundreds of sites at once."]
    svg = fig("".join(b), 720, 300, "Anycast: three sites announce the same address block; people reach the nearest one; when one fails, its people move to another",
              "<strong>Anycast</strong>: one address, many places.", steps)
    (OUT / "ch34-anycast-how.svg").write_text(svg)


# ---------------------------------------------------------------- where error pages come from

def errors():
    b = []
    xs = [(20, "browser"), (170, "CDN edge"), (340, "load balancer"), (520, "web servers")]
    for x, name in xs:
        b.append(box(x, 30, 140 if x < 520 else 180, 44, name, "f-card"))
    for x in (160, 310, 480):
        b.append(arrow(x + 2, 52, x + 26, 52, "s-muted"))
    rows = [("502 Bad Gateway", "the server behind me refused, or sent back nonsense", "t-red", "var(--red)"),
            ("503 Service Unavailable", "I have no healthy servers (or I'm overloaded): try later", "t-orange", "var(--orange)"),
            ("504 Gateway Timeout", "the server behind me didn't answer in time", "t-purple", "var(--purple)")]
    for i, (code, why, cls, stroke) in enumerate(rows):
        y = 96 + i * 38
        b.append(f'<rect x="20" y="{y}" width="210" height="30" rx="6" class="{cls}" stroke="{stroke}" stroke-width="1.4"/>')
        b.append(text(32, y + 20, code, "sm b"))
        b.append(text(244, y + 20, "the CDN or balancer says: “" + why + "”", "xs"))
    b.append(text(20, 222, "These errors are written by a middleman, about the server behind it, which may never have seen the request at all.", "xs"))
    svg = fig("".join(b), 720, 232, "Where 502, 503 and 504 errors come from: a CDN or load balancer reporting a problem with the server behind it",
              "Error pages from the middle. The lab’s load balancer produces all three.")
    (OUT / "ch34-errors.svg").write_text(svg)


if __name__ == "__main__":
    proxies()
    layers()
    cdn()
    anycast()
    anycast_how()
    errors()
    print("wrote ch34 figures")
