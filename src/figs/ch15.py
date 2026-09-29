#!/usr/bin/env python3
"""Generate chapter 15 figures.  python3 src/figs/ch15.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- the layers, side by side

def layers():
    rows = [("Programs talk: web pages, names", "Ch. 4–7, 14", "Application", "HTTP, DNS, email…", "programs", "t-purple", "var(--purple)"),
            ("Ports, datagrams, reliable connections", "Ch. 12–13", "Transport", "TCP, UDP", "your operating system", "t-green", "var(--green)"),
            ("Packets, network addresses, routers", "Ch. 10–11", "Internet", "IP (with ARP, ICMP)", "routers", "t-yellow", "var(--yellow)"),
            ("Frames, card addresses, switches, checks", "Ch. 3, 8–10", "Link", "Ethernet, Wi-Fi", "switches, network cards", "t-blue", "var(--blue)"),
            ("Bits on wires, light and radio", "Ch. 1–2", "Physical", "copper, fiber, radio", "cables, antennas", "t-red", "var(--red)")]
    body = [text(150, 22, "What we built", "mid slab b"), text(441, 22, "What the internet calls it", "mid slab b"),
            text(634, 22, "Who reads it", "mid slab b")]
    for i, (ours, ch, layer, real, who, cls, stroke) in enumerate(rows):
        y = 36 + i * 58
        body.append(f'<rect x="10" y="{y}" width="282" height="50" rx="8" class="{cls}" stroke="{stroke}" stroke-width="2"/>')
        body.append(text(22, y + 22, ours, "sm b"))
        body.append(text(22, y + 40, ch, "xs muted"))
        body.append(f'<path d="M298,{y + 25} l26,0" class="line s-muted" stroke-width="2" marker-end="url(#ah-muted)"/>')
        body.append(f'<rect x="334" y="{y}" width="214" height="50" rx="8" class="{cls}" stroke="{stroke}" stroke-width="2"/>')
        body.append(text(346, y + 22, f"{layer} layer", "sm b"))
        body.append(text(346, y + 40, real, "xs"))
        body.append(text(634, y + 30, who, "mid xs"))
    body.append(text(360, 334, "Each layer only reads its own header, and trusts the layer below to deliver.", "mid hand"))
    svg = fig("".join(body), 720, 346, "Our inventions arranged as layers next to the internet's layer names",
              "The same stack, two sets of names.")
    (OUT / "ch15-layers.svg").write_text(svg)


# ---------------------------------------------------------------- one request, all the way

NODES = {"alice": 60, "router": 250, "net": 450, "otto": 650}
Y = 64


def nested(x, y, w, layers):
    """layers: list of (label, detail, class, stroke), outermost first. Each sits inside the one before."""
    out, n = [], len(layers)
    height = 26 * n + 16
    for i, (label, detail, cls, stroke) in enumerate(layers):
        top = y + 26 * i
        out.append(f'<rect x="{x + 14 * i}" y="{top}" width="{w - 28 * i}" height="{height - 26 * i - 5 * i}" rx="8" '
                   f'class="{cls}" stroke="{stroke}" stroke-width="2"/>')
        out.append(text(x + 14 * i + 10, top + 18, label, "xs b"))
        out.append(text(x + 14 * i + 90, top + 18, detail, "mono xs"))
    return "".join(out)


FRAME = ("frame", "", "t-blue", "var(--blue)")


def journey():
    body = []
    for a, b in (("alice", "router"), ("router", "net"), ("net", "otto")):
        body.append(f'<line x1="{NODES[a]}" y1="{Y}" x2="{NODES[b]}" y2="{Y}" class="wire" stroke-width="5"/>')
    body.append(f'<use href="#alice-head" x="{NODES["alice"] - 26}" y="{Y - 28}" width="52" height="52"/>')
    body.append(f'<use href="#router" x="{NODES["router"] - 32}" y="{Y - 22}" width="64" height="44"/>')
    body.append(f'<use href="#cloud" x="{NODES["net"] - 60}" y="{Y - 36}" width="120" height="72"/>')
    body.append(f'<use href="#server" x="{NODES["otto"] - 18}" y="{Y - 28}" width="36" height="56"/>')
    for key, label in (("alice", "Alice’s laptop"), ("router", "home router"), ("net", "~12 routers"), ("otto", "grandpa-otto.example")):
        body.append(text(NODES[key], Y + 44, label, "mid xs b"))

    def dot(step, path, colour="f-blue"):
        return (f'<g data-show="={step}"><circle r="8" class="{colour}" stroke="var(--surface)" stroke-width="2">'
                f'<animateMotion dur="{0.7 * (len(path) - 1):.1f}s" begin="indefinite" fill="freeze" '
                f'path="M{" L".join(f"{NODES[p]},{Y}" for p in path)}"/></circle></g>')

    stages = [
        (1, ["alice", "router", "alice"], [FRAME, ("who has?", "192.168.1.1? tell 192.168.1.3", "f-surface", "var(--line)")],
         "ARP: “who has 192.168.1.1?” → “it’s card 14:c3:5e:40:0b:32”"),
        (2, ["alice", "router", "alice"], [FRAME, ("packet", "to 192.168.1.1", "t-yellow", "var(--yellow)"),
                                            ("datagram", "to port 53", "t-green", "var(--green)"),
                                            ("question", "grandpa-otto.example?", "t-purple", "var(--purple)")],
         "DNS over UDP: “grandpa-otto.example is 203.0.113.42”"),
        (3, ["alice", "router", "net", "otto", "net", "router", "alice"], [FRAME, ("packet", "to 203.0.113.42", "t-yellow", "var(--yellow)"),
                                                                         ("TCP", "port 80, SYN, #1000", "t-green", "var(--green)")],
         "TCP handshake: SYN → SYN+ACK → ACK"),
        (4, ["alice", "router"], [("frame", "to the router’s card", "t-blue", "var(--blue)"), ("packet", "to 203.0.113.42, hops 64", "t-yellow", "var(--yellow)"),
                                  ("TCP", "port 80, byte #1001", "t-green", "var(--green)"), ("HTTP", "GET / HTTP/1.1", "t-purple", "var(--purple)")],
         "the request, wrapped in four envelopes"),
        (5, ["router", "net", "otto"], [("frame", "new at every hop", "t-blue", "var(--blue)"), ("packet", "hops 63, 62, … 52", "t-yellow", "var(--yellow)"),
                                        ("TCP", "untouched", "t-green", "var(--green)"), ("HTTP", "untouched", "t-purple", "var(--purple)")],
         "routers rewrap the frame and lower the hop count"),
        (6, [], [("frame", "my card ✓ check ✓", "t-blue", "var(--blue)"), ("packet", "to me ✓", "t-yellow", "var(--yellow)"),
                 ("TCP", "port 80 → web server", "t-green", "var(--green)"), ("HTTP", "GET / → the home page", "t-purple", "var(--purple)")],
         "Otto’s server peels each layer off in turn"),
        (7, ["otto", "net", "router", "alice"], [FRAME, ("packet", "to 192.168.1.3", "t-yellow", "var(--yellow)"),
                                                 ("TCP", "byte #5001", "t-green", "var(--green)"), ("HTTP", "200 OK, &lt;h1&gt;Hello…", "t-purple", "var(--purple)")],
         "the page comes back the same way, then goodbye (FIN)"),
    ]
    for step, path, env, caption in stages:
        g = [f'<g data-show="={step}">', nested(140, 116, 440, env), text(360, 116 + 26 * len(env) + 44, caption, "mid hand"), "</g>"]
        body.append("".join(g))
        if path:
            body.append(dot(step, path, "f-green" if step == 7 else "f-blue"))
    steps = ["Alice types <code>http://grandpa-otto.example/</code>. Before her laptop can send anything off her network, it needs the router’s card address, so it asks “who has 192.168.1.1?” (Chapter 11).",
             "Next, the name. Her laptop asks the resolver, which here is the home router, in a UDP datagram to port 53 (Chapters 12 and 14).",
             "Now it knows where to go. It opens a TCP connection to port 80 at 203.0.113.42, with a three-way handshake (Chapter 13).",
             "The browser writes its request into the connection: <code>GET / HTTP/1.1</code> (Chapter 6). TCP numbers the bytes, IP addresses the packet, and Ethernet puts it in a frame for the router, with a CRC on the end (Chapters 8–13).",
             "About a dozen routers pass it along. Each one checks the frame, throws it away, lowers the hop count, and builds a new frame for the next link. The packet inside, and everything inside that, is never touched (Chapter 11).",
             "At Otto’s server, each layer checks its own header and passes the rest up: the card, then IP, then TCP, which delivers the bytes to the web server program listening on port 80.",
             "The server’s answer makes the same journey in reverse, the browser shows the page, and the two ends say goodbye. A whole book’s worth of inventions, in about 90 milliseconds."]
    svg = fig("".join(body), 720, 330, "One web request travelling from Alice's laptop to a server and back, with the envelopes at each stage",
              "One click, every layer.", steps)
    (OUT / "ch15-journey.svg").write_text(svg)


if __name__ == "__main__":
    layers()
    journey()
    print("wrote ch15 figures")
