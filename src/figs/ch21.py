#!/usr/bin/env python3
"""Generate chapter 21 figures.  python3 src/figs/ch21.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent

REQUEST = bytes.fromhex("0001080006040001" "2ccf675e10c2" "c0a80104" "000000000000" "c0a80101")
REPLY = bytes.fromhex("0001080006040002" "14c35e400b32" "c0a80101" "2ccf675e10c2" "c0a80104")
TIME_EXCEEDED = bytes.fromhex("45c00070adae0000400148c9c0a80101c0a80104" "0b00f4ff00000000"
                              "45000054ad8d40000101086ec0a80104010101010800d62e3ae90001")


# ---------------------------------------------------------------- an ARP message

def arp():
    fields = [("hardware", 0, 2, "1 = Ethernet"), ("protocol", 2, 4, "0800 = IPv4"), ("sizes", 4, 6, "6 and 4 bytes"),
              ("operation", 6, 8, None), ("sender MAC", 8, 14, None), ("sender IP", 14, 18, None),
              ("target MAC", 18, 24, None), ("target IP", 24, 28, None)]
    b = []
    widths = {"hardware": 54, "protocol": 58, "sizes": 50, "operation": 76, "sender MAC": 126, "sender IP": 94,
              "target MAC": 126, "target IP": 94}
    for r, (title, msg, sub) in enumerate((("“Who has 192.168.1.1? Tell 192.168.1.4.”", REQUEST, "broadcast, to ff:ff:ff:ff:ff:ff"),
                                          ("“192.168.1.1 is at 14:c3:5e:40:0b:32.”", REPLY, "straight back to the Pi"))):
        y = 30 + r * 120
        b.append(text(14, y, title, "sm b"))
        b.append(text(706, y, sub, "end xs muted"))
        x = 14
        for name, a, c, note in fields:
            w = widths[name]
            chunk = msg[a:c]
            if name.endswith("IP"):
                value = ".".join(map(str, chunk))
            elif name.endswith("MAC"):
                value = ":".join(f"{v:02x}" for v in chunk)
            elif name == "operation":
                value = "1: ask" if chunk[1] == 1 else "2: answer"
            else:
                value = chunk.hex()
            cls = "t-blue" if "MAC" in name else "t-yellow" if "IP" in name else "t-purple" if name == "operation" else "f-card"
            highlight = (name == "target MAC" and r == 0) or (name == "operation")
            b.append(f'<rect x="{x}" y="{y + 10}" width="{w - 3}" height="44" rx="5" class="{cls}" stroke="{"var(--orange)" if highlight else "var(--line)"}" stroke-width="{2 if highlight else 1.2}"/>')
            b.append(text(x + (w - 3) / 2, y + 26, name, "mid xs b"))
            b.append(text(x + (w - 3) / 2, y + 44, value, "mid mono xs"))
            x += w
    b.append(text(14 + 54 + 58 + 50 + 76 + 126 + 94 + 63, 102, "all zeros: “that’s what I’m asking!”", "mid xs f-orange b"))
    svg = fig("".join(b), 720, 264, "An ARP request and its reply, field by field, from the Pi's real capture",
              "A real “who has?” and its answer: 28 bytes each, inside an Ethernet frame of type 0806.")
    (OUT / "ch21-arp.svg").write_text(svg)


# ---------------------------------------------------------------- an ICMP error, quoting the original

def icmperror():
    b = [text(14, 22, "What the router sent back when the Pi’s ping ran out of hops (packet 22 of Chapter 16’s capture)", "sm b")]
    layers = [("IP header, from the router", "192.168.1.1 → 192.168.1.4, protocol 1 (ICMP)", 0, 20, "t-yellow", "var(--yellow)"),
              ("ICMP: type 11, code 0", "“time exceeded in transit”, then 4 unused bytes", 20, 28, "t-red", "var(--red)"),
              ("…the Pi’s own IP header, quoted", "192.168.1.4 → 1.1.1.1, ttl 1, protocol 1", 28, 48, "t-yellow", "var(--yellow)"),
              ("…and the start of what was inside", "ICMP echo request, id 15081, seq 1", 48, 56, "t-green", "var(--green)")]
    for n, (name, words, a, c, cls, stroke) in enumerate(layers):
        indent = 0 if n < 2 else 24
        y = 40 + n * 58
        b.append(f'<rect x="{14 + indent}" y="{y}" width="{692 - indent}" height="50" rx="8" class="{cls}" stroke="{stroke}" stroke-width="2"/>')
        b.append(text(26 + indent, y + 20, name, "sm b"))
        b.append(text(26 + indent, y + 38, words, "xs"))
        hexs = TIME_EXCEEDED[a:c].hex(" ")
        b.append(text(700, y + 20, hexs[:47], "end mono xs"))
        if len(hexs) > 47:
            b.append(text(700, y + 38, hexs[48:], "end mono xs"))
    b.append(f'<path d="M24,{40 + 2 * 58} L24,{40 + 4 * 58 - 8}" class="line s-muted" stroke-width="2"/>')
    b.append(text(360, 290, "The quote lets the Pi work out exactly which of its packets died, and which program sent it.", "mid hand"))
    svg = fig("".join(b), 720, 304, "An ICMP time exceeded message: the router's IP header, the ICMP header, then a quote of the original packet's IP header and first bytes",
              "An ICMP error always quotes the start of the packet that caused it.")
    (OUT / "ch21-icmperror.svg").write_text(svg)


# ---------------------------------------------------------------- how traceroute works

def traceroute():
    xs = [70, 210, 350, 490, 640]
    names = ["Bob’s laptop", "home router", "provider", "…", "1.1.1.1"]
    y = 110
    b = [f'<line x1="{xs[0]}" y1="{y}" x2="{xs[-1]}" y2="{y}" class="wire" stroke-width="4"/>']
    b.append(f'<use href="#computer" x="{xs[0] - 30}" y="{y - 28}" width="60" height="54"/>')
    for x in xs[1:4]:
        b.append(f'<use href="#router" x="{x - 30}" y="{y - 20}" width="60" height="40"/>')
    b.append(f'<use href="#server" x="{xs[4] - 16}" y="{y - 28}" width="32" height="54"/>')
    for x, n in zip(xs, names):
        b.append(text(x, y + 46, n, "mid xs b"))
    for step, hop in ((1, 1), (2, 2), (3, 4)):
        g = [f'<g data-show="={step}">']
        end = xs[hop]
        if hop < 4:
            g.append(f'<path d="M{xs[0] + 34},{y - 36} L{end - 10},{y - 36}" class="line s-blue" stroke-width="3" marker-end="url(#ah-blue)"/>')
            g.append(text((xs[0] + end) / 2, y - 46, f"ping with hop limit {step}", "mid xs b"))
            g.append(f'<path d="M{end - 8},{y - 24} l14,14 M{end + 6},{y - 24} l-14,14" class="line s-red" stroke-width="3"/>')
            g.append(f'<path d="M{end - 10},{y + 62} L{xs[0] + 34},{y + 62}" class="line s-red" stroke-width="3" marker-end="url(#ah-red)"/>')
            g.append(text((xs[0] + end) / 2, y + 82, f"“time exceeded”, from router {step}’s own address", "mid xs b f-red"))
        else:
            g.append(f'<path d="M{xs[0] + 34},{y - 36} L{end - 22},{y - 36}" class="line s-blue" stroke-width="3" marker-end="url(#ah-blue)"/>')
            g.append(text((xs[0] + end) / 2, y - 46, "ping with hop limit 4", "mid xs b"))
            g.append(f'<path d="M{end - 22},{y + 62} L{xs[0] + 34},{y + 62}" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/>')
            g.append(text((xs[0] + end) / 2, y + 82, "“echo reply”: we’ve arrived", "mid xs b f-green"))
        g.append("</g>")
        b.append("".join(g))
    steps = ["Send a ping with a hop limit of 1. The first router takes 1 off, gets 0, throws the ping away, and sends back “time exceeded”, from its own address. Now we know who the first router is, and how long the round trip to it takes.",
             "Send another with a hop limit of 2. It gets one router further, and the second router complains. Every step reveals one more router.",
             "Keep going until the destination itself answers with an echo reply. Each line of traceroute’s output is one of these steps, usually tried three times."]
    svg = fig("".join(b), 720, 212, "Traceroute sending pings with increasing hop limits; each router in turn sends back time exceeded, until the destination replies",
              "How traceroute finds the routers: by making each one complain in turn.", steps)
    (OUT / "ch21-traceroute.svg").write_text(svg)


if __name__ == "__main__":
    arp()
    icmperror()
    traceroute()
    print("wrote ch21 figures")
