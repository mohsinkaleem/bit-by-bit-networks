#!/usr/bin/env python3
"""Generate chapter 11 figures.  python3 src/figs/ch11.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- a router between two networks

def router():
    body = []
    street = [("alice", 40, 60), ("bob", 40, 200), ("carol", 170, 262), ("dave", 250, 262)]
    school = [(596, 60), (630, 150), (596, 240)]
    sx, sy = 150, 150            # street switch
    cx, cy = 560, 150            # school switch
    rx, ry = 360, 150
    for sid, x, y in street:
        body.append(f'<line x1="{x + 24}" y1="{y + 20}" x2="{sx}" y2="{sy}" class="wire" stroke-width="3"/>')
    for x, y in school:
        body.append(f'<line x1="{x + 20}" y1="{y + 20}" x2="{cx}" y2="{cy}" class="wire" stroke-width="3"/>')
    body.append(f'<line x1="{sx}" y1="{sy}" x2="{rx}" y2="{ry}" class="wire" stroke-width="4"/>')
    body.append(f'<line x1="{rx}" y1="{ry}" x2="{cx}" y2="{cy}" class="wire" stroke-width="4"/>')
    # broadcast from Dave spreading through the street, stopping at the router
    flood = [(sx, sy, x + 24, y + 20) for sid, x, y in street] + [(sx, sy, rx - 44, ry)]
    for x1, y1, x2, y2 in flood:
        body.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="line s-orange" stroke-width="12" opacity="0.3"/>')
    for x1, y1, x2, y2 in flood:
        body.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="line s-orange" stroke-width="3" stroke-dasharray="7 6"/>')
    body.append(text(rx - 64, ry - 16, "✋", "mid lg"))
    body.append(text(rx - 64, ry + 40, "broadcasts", "mid hand f-orange halo"))
    body.append(text(rx - 64, ry + 58, "stop here", "mid hand f-orange halo"))
    body.append(f'<use href="#switch" x="{sx - 56}" y="{sy - 17}" width="112" height="34"/>')
    body.append(f'<use href="#switch" x="{cx - 56}" y="{cy - 17}" width="112" height="34"/>')
    body.append(f'<use href="#router" x="{rx - 42}" y="{ry - 28}" width="84" height="56"/>')
    body.append(text(rx, ry - 40, "the router", "mid slab b"))
    body.append(text(rx - 46, ry + 12, "1.254", "end mono xs b f-blue halo"))
    body.append(text(rx + 46, ry + 12, "2.254", "mono xs b f-green halo"))
    for sid, x, y in street:
        body.append(f'<use href="#{sid}-head" x="{x}" y="{y}" width="48" height="48"/>')
    for i, (x, y) in enumerate(school):
        body.append(f'<use href="#computer" x="{x}" y="{y}" width="44" height="40"/>')
        body.append(text(x + 54, y + 26, f"2.{i + 1}", "mono xs"))
    body.append(text(40, 24, "Our street: network 1", "slab b f-blue"))
    body.append(text(706, 24, "The school: network 2", "end slab b f-green"))
    body.append(text(250, 250, "Dave: “Who’s there?”", "hand f-orange"))
    svg = fig("".join(body), 720, 318, "A router joins two networks; broadcasts from one network stop at the router",
              "A router has one foot in each network, with an address on each. Frames and broadcasts stay on their own side.")
    (OUT / "ch11-router.svg").write_text(svg)


# ---------------------------------------------------------------- who vs where

def address():
    body = []
    # card address
    body.append(text(180, 28, "A card address says WHO", "mid slab b"))
    body.append('<rect x="50" y="48" width="260" height="62" rx="10" class="card"/>')
    body.append(text(180, 88, "0c:33:9a:41:07:e2", "mid mono lg b"))
    body.append(text(180, 138, "stamped in at the factory. Like a fingerprint,", "mid sm"))
    body.append(text(180, 158, "it tells you nothing about where Carol is.", "mid sm"))
    body.append('<line x1="360" y1="30" x2="360" y2="220" class="line s-line"/>')
    # network address
    body.append(text(540, 28, "A network address says WHERE", "mid slab b"))
    body.append('<rect x="440" y="48" width="200" height="62" rx="10" class="card"/>')
    body.append(text(500, 92, "1", "mid mono xl b f-blue"))
    body.append(text(540, 92, ".", "mid mono xl b"))
    body.append(text(580, 92, "3", "mid mono xl b f-orange"))
    body.append('<path d="M482,118 l0,8 l36,0 l0,-8" class="line s-blue" stroke-width="2"/>')
    body.append('<path d="M562,118 l0,8 l36,0 l0,-8" class="line s-orange" stroke-width="2"/>')
    body.append(text(500, 148, "network 1", "mid hand f-blue"))
    body.append(text(500, 166, "(our street)", "mid xs muted"))
    body.append(text(580, 148, "host 3", "mid hand f-orange"))
    body.append(text(580, 166, "(Carol)", "mid xs muted"))
    body.append(text(540, 200, "Like “house 3, Maple Street”.", "mid sm"))
    body.append(text(540, 220, "The first part is enough to get you close.", "mid sm"))
    svg = fig("".join(body), 720, 236, "A flat card address compared with a two-part network address",
              "Carol gets a second address. Her card address still works on her own network; the new one works everywhere.")
    (OUT / "ch11-address.svg").write_text(svg)


# ---------------------------------------------------------------- new frame, same packet

NODES = [("Alice", 52, "alice-head"), ("R1", 256, "router"), ("R4", 464, "router"), ("Otto", 668, "computer")]
FRAMES = [("c1:01", "0a:11", 64), ("c4:01", "c1:01", 63), ("40:02", "c4:01", 62)]


def hops():
    body = []
    y = 58
    for i in range(3):
        x1, x2 = NODES[i][1], NODES[i + 1][1]
        body.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" class="wire" stroke-width="5"/>')
    seg_labels = ["street (net 1)", "the R1–R4 cable", "Otto’s town (net 4)"]
    for i, lab in enumerate(seg_labels):
        body.append(text((NODES[i][1] + NODES[i + 1][1]) / 2, y + 30, lab, "mid xs muted"))
    for name, x, sprite in NODES:
        if sprite == "router":
            body.append(f'<use href="#router" x="{x - 33}" y="{y - 22}" width="66" height="44"/>')
        elif sprite == "computer":
            body.append(f'<use href="#computer" x="{x - 24}" y="{y - 22}" width="48" height="44"/>')
        else:
            body.append(f'<use href="#{sprite}" x="{x - 24}" y="{y - 26}" width="48" height="48"/>')
        body.append(text(x, y - 32, name, "mid slab b"))
    # moving packets
    for i in range(3):
        x1, x2 = NODES[i][1], NODES[i + 1][1]
        body.append(f'<g data-show="={i + 1}"><circle r="8" class="f-blue" stroke="var(--surface)" stroke-width="2">'
                    f'<animateMotion dur="1.2s" begin="indefinite" fill="freeze" path="M{x1 + 20},{y} L{x2 - 30},{y}"/></circle></g>')
    # envelopes
    for i, (to, frm, ttl) in enumerate(FRAMES):
        cx = (NODES[i][1] + NODES[i + 1][1]) / 2
        x0, w, top = cx - 97, 194, 112
        g = [f'<rect x="{x0}" y="{top}" width="{w}" height="146" rx="10" class="t-blue" stroke="var(--blue)" stroke-width="2"/>',
             text(x0 + 10, top + 20, "frame", "xs b f-blue"),
             text(x0 + 10, top + 40, f"to {to}", "mono xs b"),
             text(x0 + 10, top + 58, f"from {frm}", "mono xs"),
             f'<rect x="{x0 + 10}" y="{top + 70}" width="{w - 20}" height="66" rx="8" class="t-yellow" stroke="var(--yellow)" stroke-width="2"/>',
             text(x0 + 20, top + 88, "packet", "xs b"),
             text(x0 + 20, top + 106, "to 4.2 · from 1.1", "mono xs b"),
             text(x0 + 20, top + 126, f"hops left {ttl}", "mono xs" + (" b f-red" if i else ""))]
        body.append(f'<g data-show="{i + 1}">' + "".join(g) + "</g>")
        body.append(f'<g data-show="4"><rect x="{x0 + 7}" y="{top + 67}" width="{w - 14}" height="72" rx="10" class="f-none" '
                    f'stroke="var(--green)" stroke-width="3.5"/></g>')
    body.append(f'<g data-show="4">{text(360, 290, "The packet (green) makes the whole trip. Only its hop count changes.", "mid hand f-green")}'
                f'{text(360, 312, "The frame around it is thrown away and rebuilt at every router.", "mid hand f-blue")}</g>')
    steps = ["Alice’s packet is for 4.2, which isn’t on her network. So she puts it in a frame addressed to her <strong>gateway</strong>, R1, "
             "using R1’s card address.",
             "R1 opens the frame and looks at the packet’s destination: network 4. Its table says “via R4”. It takes one off the hop count, "
             "wraps the packet in a <em>new</em> frame addressed to R4’s card, and sends it down the cable.",
             "R4 is plugged right into network 4. It asks “who has 4.2?”, learns Otto’s card address, and wraps the packet in a new frame for him.",
             "Three frames, one packet. Card addresses only ever get a frame across one network. Network addresses get the packet across the whole town."]
    svg = fig("".join(body), 720, 324, "A packet crossing two routers keeps its addresses while the frame around it changes at every hop",
              "New frame, same packet.", steps)
    (OUT / "ch11-hops.svg").write_text(svg)


# ---------------------------------------------------------------- who has 1.254?

def whohas():
    seq = Seq([("Alice (1.1)", 110, "alice"), ("Bob (1.2)", 350, "bob"), ("R1 (1.254)", 590, None)], top=90, scale=34)
    seq.msg("Alice (1.1)", "Bob (1.2)", 0, 1, "", cls="orange", step="1")
    seq.msg("Alice (1.1)", "R1 (1.254)", 0, 1.5, "who has 1.254?", cls="orange", step="1", sub="to: everyone (broadcast)", label_at=0.76)
    seq.note("Bob (1.2)", 1.9, "not me: ignore it", step="2", side="right")
    seq.msg("R1 (1.254)", "Alice (1.1)", 2.5, 3.6, "1.254 is card c1:01", cls="green", step="2", sub="to: Alice only")
    seq.note("Alice (1.1)", 4.3, "write it down: 1.254 → c1:01", step="3", side="right")
    seq.msg("Alice (1.1)", "R1 (1.254)", 5.0, 6.0, "frame to c1:01", cls="blue", step="3")
    body, bottom = seq.render()
    body += '<use href="#router" x="560" y="10" width="60" height="40"/>'
    steps = ["Alice knows her gateway’s <em>network</em> address, 1.254, but a frame needs a <em>card</em> address. So she broadcasts a question to her whole network.",
             "Everyone hears it. Only the computer that has 1.254 answers, and it replies to Alice directly.",
             "Alice notes the answer in a small table, so she doesn’t have to ask again for a while, and sends her frame."]
    svg = fig(body, 720, bottom, "Alice broadcasts who has 1.254, the router replies with its card address",
              "Turning a network address into a card address.", steps)
    (OUT / "ch11-whohas.svg").write_text(svg)


# ---------------------------------------------------------------- a routing loop

def loop():
    body = []
    a, b = (220, 140), (500, 140)
    for (x, y), name in ((a, "R1"), (b, "R2")):
        body.append(f'<use href="#router" x="{x - 42}" y="{y - 28}" width="84" height="56"/>')
        body.append(text(x, y + 50, name, "mid slab b"))
    body.append(f'<path d="M{a[0] + 30},{a[1] - 30} Q360,30 {b[0] - 30},{b[1] - 30}" class="line s-muted" stroke-width="2.5" '
                'marker-end="url(#ah-muted)"/>')
    body.append(f'<path d="M{b[0] - 30},{b[1] + 30} Q360,250 {a[0] + 30},{a[1] + 30}" class="line s-muted" stroke-width="2.5" '
                'marker-end="url(#ah-muted)"/>')
    body.append(text(360, 42, "“network 4? that’s via R2”", "mid hand"))
    body.append(text(360, 250, "“network 4? that’s via R1”", "mid hand"))
    top = [(275, 70, 8), (360, 58 + 14, 7), (445, 70, 6)]
    bot = [(445, 210, 5), (360, 222 - 14, 4), (275, 210, 3)]
    for x, y, n in top + bot:
        body.append(f'<rect x="{x - 15}" y="{y - 11}" width="30" height="22" rx="5" class="t-yellow" stroke="var(--yellow)" stroke-width="2"/>')
        body.append(text(x, y + 5, str(n), "mid mono xs b"))
    body.append(text(80, 110, "…2, 1, 0!", "mid hand lg f-red"))
    body.append(text(80, 136, "dropped ✗", "mid hand f-red"))
    body.append(text(80, 160, "and Alice gets", "mid xs muted"))
    body.append(text(80, 176, "a note saying so", "mid xs muted"))
    body.append(text(640, 110, "Without a hop", "mid xs muted"))
    body.append(text(640, 126, "limit, it would", "mid xs muted"))
    body.append(text(640, 142, "circle forever.", "mid xs muted"))
    svg = fig("".join(body), 720, 270, "A packet bounces between two routers with bad tables until its hop count reaches zero",
              "Two routers that each think the other knows the way. The hop count guarantees the packet can’t circle forever.")
    (OUT / "ch11-loop.svg").write_text(svg)


# ---------------------------------------------------------------- traceroute

def trace():
    xs = {"Alice": 70, "R1": 260, "R4": 460, "Otto": 650}
    body = []
    for name, x in xs.items():
        body.append(text(x, 24, name, "mid slab b"))
        body.append(f'<line x1="{x}" y1="34" x2="{x}" y2="276" class="line s-muted" stroke-width="2" stroke-dasharray="2 5"/>')
    rows = [(1, "R1", "R1: “died here”"), (2, "R4", "R4: “died here”"), (3, "Otto", "Otto: “hello!”")]
    for i, (limit, stop, reply) in enumerate(rows):
        y = 64 + i * 80
        x1 = xs[stop]
        ok = stop == "Otto"
        body.append(f'<line x1="70" y1="{y}" x2="{x1 - 8}" y2="{y}" class="line s-blue" stroke-width="3" marker-end="url(#ah-blue)"/>')
        body.append(text(120, y - 8, f"hops left {limit}", "mono xs b f-blue halo"))
        if not ok:
            body.append(f'<path d="M{x1 - 8},{y - 8} l16,16 M{x1 + 8},{y - 8} l-16,16" class="line s-red" stroke-width="3.5"/>')
        body.append(f'<line x1="{x1 - 4}" y1="{y + 22}" x2="78" y2="{y + 22}" class="line s-{"green" if ok else "red"} dash" '
                    f'stroke-width="2" marker-end="url(#ah-{"green" if ok else "red"})"/>')
        body.append(text((70 + x1) / 2, y + 40, reply, f"mid hand {'f-green' if ok else 'f-red'} halo"))
    body.append(text(360, 300, "Each reply names one more router on the way. That’s the whole trick.", "mid hand"))
    svg = fig("".join(body), 720, 314, "Tracing a route by sending packets with hop limits of 1, 2 and 3",
              "Send a packet allowed 1 hop, then 2, then 3, and see who complains.")
    (OUT / "ch11-trace.svg").write_text(svg)


# ---------------------------------------------------------------- a real address

def realip():
    body = []
    octets = [192, 168, 1, 3]
    C, X0 = 19, 30
    for i, o in enumerate(octets):
        bits = format(o, "08b")
        for j, b in enumerate(bits):
            k = i * 8 + j
            x = X0 + k * C + i * 12
            net = k < 24
            body.append(f'<rect x="{x}" y="56" width="{C - 2}" height="26" rx="3" class="{"t-blue" if net else "t-orange"}" '
                        f'stroke="{"var(--blue)" if net else "var(--orange)"}" stroke-width="1.2"/>')
            body.append(text(x + (C - 2) / 2, 74, b, "mid mono xs b"))
        cx = X0 + i * (8 * C + 12) + 4 * C - 2
        body.append(text(cx, 44, str(o), "mid mono b " + ("f-blue" if i < 3 else "f-orange")))
    body.append(f'<path d="M{X0},92 l0,8 L{X0 + 24 * C + 24 - 2},100 l0,-8" class="line s-blue" stroke-width="2"/>')
    body.append(text(X0 + 12 * C + 12, 122, "network part: 192.168.1 (the first 24 bits)", "mid hand f-blue"))
    hx = X0 + 24 * C + 36
    body.append(f'<path d="M{hx},92 l0,8 L{hx + 8 * C - 2},100 l0,-8" class="line s-orange" stroke-width="2"/>')
    body.append(text(hx + 4 * C, 122, "host: 3", "mid hand f-orange"))
    body.append(text(360, 20, "192.168.1.3 is 32 bits", "mid slab b"))
    body.append(text(360, 152, "netmask 0xffffff00 = 24 ones, then 8 zeros = “/24”: the ones mark the network part", "mid sm muted"))
    svg = fig("".join(body), 720, 166, "The 32 bits of 192.168.1.3, split into a 24-bit network part and an 8-bit host part",
              "A real address is split into network and host, just like ours. Only the split point varies.")
    (OUT / "ch11-realip.svg").write_text(svg)


if __name__ == "__main__":
    router()
    address()
    hops()
    whohas()
    loop()
    trace()
    realip()
    print("wrote ch11 figures")
