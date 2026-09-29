#!/usr/bin/env python3
"""Generate chapter 25 figures.  python3 src/figs/ch25.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- the parts of an address

def anatomy():
    groups = ["2001", "0db8", "04c1", "0012", "3b57", "d9be", "3b78", "a7e8"]
    x0, gw = 40, 80
    b = [text(360, 22, "One computer’s address at the university (in the range set aside for examples)", "mid sm b")]
    parts = [(0, 3, "global routing prefix: 48 bits", "who: the university’s block, from its provider", "t-blue", "var(--blue)"),
             (3, 4, "subnet: 16 bits", "which network inside it", "t-yellow", "var(--yellow)"),
             (4, 8, "interface ID: 64 bits", "which computer on that network", "t-green", "var(--green)")]
    for a, c, name, sub, cls, stroke in parts:
        x1, x2 = x0 + a * gw, x0 + c * gw - 6
        b.append(f'<rect x="{x1}" y="40" width="{x2 - x1}" height="36" rx="6" class="{cls}" stroke="{stroke}" stroke-width="1.8"/>')
        for g in range(a, c):
            b.append(text(x0 + g * gw + (gw - 6) / 2, 64, groups[g], "mid mono b"))
            if g < 7:
                b.append(text(x0 + (g + 1) * gw - 3, 64, ":", "mid mono b muted"))
        b.append(f'<path d="M{x1},86 L{x1},92 L{x2},92 L{x2},86" class="line" stroke="{stroke}" stroke-width="2"/>')
        b.append(text((x1 + x2) / 2, 110, name, "mid xs b"))
        b.append(text((x1 + x2) / 2, 125, sub, "mid xs muted"))
    b.append(text(360, 158, "The first 64 bits say which network (routers only look at these); the last 64 say which computer.", "mid xs"))
    b.append(text(360, 176, "A home usually gets a /56 from its provider: 256 networks of 18,446,744,073,709,551,616 addresses each.", "mid xs"))
    svg = fig("".join(b), 720, 190, "An IPv6 address split into a 48-bit global routing prefix, a 16-bit subnet ID and a 64-bit interface ID",
              "The three parts of a typical IPv6 address.")
    (OUT / "ch25-anatomy.svg").write_text(svg)


# ---------------------------------------------------------------- writing it shorter

def compress():
    full = ["2001", "0db8", "0000", "0000", "0000", "ff00", "0042", "8329"]
    step2 = ["2001", "db8", "0", "0", "0", "ff00", "42", "8329"]
    b = []

    def row(y, groups, step, hl=None, colon_mode=False):
        out = [f'<g data-show="{step}">']
        x = 40
        for i, g in enumerate(groups):
            w = 18 + 11 * len(g)
            cls = "t-red" if hl and i in hl else "f-card"
            stroke = "var(--red)" if hl and i in hl else "var(--line)"
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="5" class="{cls}" stroke="{stroke}"/>')
            out.append(text(x + w / 2, y + 20, g, "mid mono b"))
            x += w
            if i < len(groups) - 1:
                out.append(text(x + 6, y + 20, ":", "mid mono b muted"))
                x += 12
        out.append("</g>")
        return "".join(out), x
    r, _ = row(30, full, "=1", hl={1, 2, 3, 4, 6})
    b.append(r)
    r, _ = row(30, step2, "=2", hl={2, 3, 4})
    b.append(r)
    b.append('<g data-show="=3"><text x="40" y="52" class="mono xl b">2001:db8::ff00:42:8329</text></g>')
    b.append('<g data-show="=1">' + text(40, 96, "8 groups of 4 hex digits: 32 digits, 128 bits. Long.", "sm") + "</g>")
    b.append('<g data-show="=2">' + text(40, 96, "Rule 1: leave out the zeros at the start of each group. A group of 0000 becomes 0.", "sm") + "</g>")
    b.append('<g data-show="=3">' + text(40, 96, "Rule 2: replace one run of all-zero groups with ::. The reader can work out how many are missing.", "sm") + "</g>")
    steps = ["An IPv6 address written out in full: eight groups of 16 bits, each written as four hex digits, separated by colons.",
             "Leading zeros in a group can go, just as you’d write 7 rather than 0007.",
             "And one run of zero groups can become <code>::</code>. Only one, though: in <code>2001::1::5</code> there’d be no way to tell how many zeros each <code>::</code> stood for. <code>::1</code> is the loopback address (Chapter 20’s 127.0.0.1), and <code>::</code> alone is all zeros."]
    svg = fig("".join(b), 720, 112, "Compressing an IPv6 address: removing leading zeros, then replacing a run of zero groups with a double colon",
              "Two rules make IPv6 addresses shorter to write.", steps)
    (OUT / "ch25-compress.svg").write_text(svg)


# ---------------------------------------------------------------- a card address inside an IPv6 address

def eui64():
    mac = ["14", "c3", "5e", "40", "0b", "32"]
    b = [text(14, 24, "Bob’s router’s card address", "sm b")]

    def cells(y, vals, step, cls_for, x0=40, w=46):
        out = [f'<g data-show="{step}">']
        for i, v in enumerate(vals):
            cls, stroke = cls_for(i, v)
            out.append(f'<rect x="{x0 + i * w}" y="{y}" width="{w - 6}" height="30" rx="5" class="{cls}" stroke="{stroke}"/>')
            out.append(text(x0 + i * w + (w - 6) / 2, y + 20, v, "mid mono b"))
        out.append("</g>")
        return "".join(out)
    b.append(cells(36, mac, "1", lambda i, v: ("f-card", "var(--line)")))
    b.append(cells(96, ["14", "c3", "5e", "ff", "fe", "40", "0b", "32"], "2",
                   lambda i, v: ("t-yellow", "var(--yellow)") if i in (3, 4) else ("f-card", "var(--line)")))
    b.append('<g data-show="2">' + text(430, 116, "← split it in half, and put ff:fe in the middle", "xs b f-orange") + "</g>")
    b.append(cells(156, ["16", "c3", "5e", "ff", "fe", "40", "0b", "32"], "3",
                   lambda i, v: ("t-red", "var(--red)") if i == 0 else ("t-yellow", "var(--yellow)") if i in (3, 4) else ("f-card", "var(--line)")))
    b.append('<g data-show="3">' + text(430, 170, "← flip one bit: 14 = 0001 0100 becomes", "xs b f-red")
             + text(430, 184, "16 = 0001 0110 (Chapter 18’s “chosen by software” bit)", "xs b f-red") + "</g>")
    b.append('<g data-show="4"><text x="40" y="240" class="mono lg b">fe80::<tspan class="f-green">16c3:5eff:fe40:b32</tspan></text>'
             + text(430, 236, "← the router’s real link-local address", "xs b f-green") + "</g>")
    steps = ["An Ethernet or Wi-Fi card address is 48 bits (Chapter 18). But the interface part of an IPv6 address is 64.",
             "The old recipe, called <strong>EUI-64</strong>, stretches it: cut it in half, and put the two bytes ff and fe in the middle.",
             "Then flip the bit that says whether the address was chosen by software. (It’s flipped so that simple, hand-typed interface IDs like ::1 count as “chosen by software”.)",
             "Stick fe80:: on the front, and that’s the link-local address Bob’s router really has. Look for ff:fe in the middle of an address: it usually means there’s a card address inside. This chapter’s lab finds them."]
    svg = fig("".join(b), 720, 256, "Building an EUI-64 interface ID from the router's MAC address 14:c3:5e:40:0b:32: insert ff:fe and flip the universal/local bit",
              "How a card address becomes the second half of an IPv6 address.", steps)
    (OUT / "ch25-eui64.svg").write_text(svg)


# ---------------------------------------------------------------- neighbour discovery, from real messages

def nd():
    devs = [("Bob’s MacBook", 100, "fe80::1c2b:3a4d:5e6f:7081", "#computer"),
            ("Mum’s phone", 360, "fe80::1c9a:4bff:fe27:d163", "#computer"),
            ("the router", 620, "fe80::16c3:5eff:fe40:b32", "#router")]
    b = ['<line x1="40" y1="150" x2="690" y2="150" class="wire" stroke-width="5"/>']
    for name, x, addr, sprite in devs:
        h = 40 if sprite == "#router" else 48
        b.append(f'<line x1="{x}" y1="126" x2="{x}" y2="150" class="wire" stroke-width="3"/>')
        b.append(f'<use href="{sprite}" x="{x - 28}" y="{80 if sprite == "#router" else 76}" width="56" height="{h}"/>')
        b.append(text(x, 176, name, "mid xs b"))
        b.append(text(x, 190, addr, "mid mono xs"))
    b.append('<g data-show="1"><rect x="14" y="4" width="316" height="50" rx="6" class="t-orange" stroke="var(--orange)"/>'
             + text(172, 24, "“who has fe80::16c3:5eff:fe40:b32?”", "mid xs b")
             + text(172, 42, "to ff02::1:ff40:b32, in a frame to 33:33:ff:40:0b:32", "mid xs") + "</g>")
    for name, x, addr, sprite in devs[1:]:
        hears = sprite == "#router"
        b.append(f'<g data-show="=1"><path d="M120,130 C{(120 + x) / 2},104 {(120 + x) / 2},104 {x - 10},{126 if hears else 130}" class="line {"s-orange" if hears else "s-muted dash"}" stroke-width="{3 if hears else 1.5}"{" marker-end=\"url(#ah-orange)\"" if hears else ""}/></g>')
        if not hears:
            b.append(f'<g data-show="=1">' + text(x, 214, "not in that group: its card ignores the frame", "mid xs muted") + "</g>")
    b.append('<g data-show="2"><rect x="420" y="4" width="286" height="50" rx="6" class="t-green" stroke="var(--green)"/>'
             + text(563, 24, "“that’s me (a router, answering you)”", "mid xs b")
             + text(563, 42, "straight back to Bob’s MacBook", "mid xs") + "</g>")
    b.append('<g data-show="2"><path d="M606,126 C480,70 250,70 126,120" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/></g>')
    steps = ["Bob’s MacBook wants the router’s card address. IPv6 has no broadcast, so instead of shouting at everyone (Chapter 21’s ARP), it sends an ICMPv6 <strong>neighbour solicitation</strong> to a “solicited-node” multicast group, made from the last 24 bits of the address it’s looking for. Only a device whose address ends that way has joined that group, so the other cards throw the frame away without even bothering the computer.",
             "The router sends back a <strong>neighbour advertisement</strong> with its card address, and the flags “I’m a router” and “this is an answer”. Both messages are real, from Bob’s network, and this chapter’s lab can show you yours. (The phone’s address has been changed.)"]
    svg = fig("".join(b), 720, 226, "A neighbour solicitation sent to a solicited-node multicast group that only the router has joined, and the router's neighbour advertisement in reply",
              "Neighbour discovery: ARP’s job, done with ICMPv6 and multicast.", steps)
    (OUT / "ch25-nd.svg").write_text(svg)


# ---------------------------------------------------------------- SLAAC

def slaac():
    seq = Seq([("Alice’s laptop (at university)", 150, None), ("the building’s router", 570, None)], top=40, scale=30, head=False)
    L, R = "Alice’s laptop (at university)", "the building’s router"
    seq.note(L, 0.3, "1. makes fe80::… for itself, checks nobody has it", step="1")
    seq.msg(L, R, 1.1, 1.6, "router solicitation: “any routers here?”", "navy", step="2", sub="to ff02::2, all routers")
    seq.msg(R, L, 2.8, 3.3, "router advertisement", "purple", step="3", sub="prefix 2001:db8:4c1:12::/64, and “use me as your router”")
    seq.note(L, 4.4, "2001:db8:4c1:12: + an interface ID of its own choosing", step="4")
    seq.msg(L, R, 5.3, 5.8, "neighbour solicitation: “who has 2001:db8:4c1:12:3b57:…?”", "navy", step="5", sub="from ::, “I don’t have an address yet”")
    seq.note(L, 6.9, "…silence: nobody else has it. It’s mine.", step="5", cls="f-green")
    body, bottom = seq.render(20)
    steps = ["Every IPv6 interface gives itself a link-local address (fe80:: and an interface ID) the moment it comes up, and checks that nobody else is using it. It can already talk to everything on its own network.",
             "Then it asks for routers, with a <strong>router solicitation</strong> to ff02::2, the group every router joins.",
             "The router answers with a <strong>router advertisement</strong>: the network’s prefix, a flag saying “make your own addresses from this”, and how long to use it as the default router. Routers also send these every few minutes, unasked.",
             "The laptop sticks an interface ID of its own onto the prefix. There’s no DHCP server keeping a list: this is <strong>stateless address autoconfiguration</strong>, SLAAC.",
             "Before using it, it checks nobody else has it: “duplicate address detection”, a neighbour solicitation sent from the unspecified address ::. If nobody answers within a second, the address is its own, and it’s online."]
    svg = fig(body, 720, bottom, "Stateless address autoconfiguration: link-local address, router solicitation, router advertisement with a prefix, and duplicate address detection",
              "How a computer gets an IPv6 address with no DHCP server at all.", steps)
    (OUT / "ch25-slaac.svg").write_text(svg)


# ---------------------------------------------------------------- the headers side by side

def header():
    b = []
    v4 = [[("ver", 4), ("hlen", 4, "x"), ("type of service", 8, "r"), ("total length", 16, "r")],
          [("identification", 16, "x"), ("flags", 3, "x"), ("fragment offset", 13, "x")],
          [("TTL", 8, "r"), ("protocol", 8, "r"), ("header checksum", 16, "x")],
          [("source address (32 bits)", 32)], [("destination address (32 bits)", 32)], [("options (maybe)", 32, "x")]]
    v6 = [[("ver", 4), ("traffic class", 8, "r"), ("flow label", 20, "n")],
          [("payload length", 16, "r"), ("next header", 8, "r"), ("hop limit", 8, "r")],
          [("source address", 32)], [("(128 bits)", 32)], [("", 32)], [("", 32)],
          [("destination address", 32)], [("(128 bits)", 32)], [("", 32)], [("", 32)]]

    def draw(rows, x0, title, width=300):
        out = [text(x0 + width / 2, 20, title, "mid sm b")]
        for r, row in enumerate(rows):
            x = x0
            for field in row:
                name, bits = field[0], field[1]
                mark = field[2] if len(field) > 2 else ""
                w = width * bits / 32
                cls = {"x": "t-red", "r": "t-yellow", "n": "t-green"}.get(mark, "f-card")
                stroke = {"x": "var(--red)", "r": "var(--yellow)", "n": "var(--green)"}.get(mark, "var(--line)")
                y = 30 + r * 22
                top_join = name == "" or name.startswith("(")
                out.append(f'<rect x="{x:g}" y="{y}" width="{w:g}" height="22" class="{cls}" stroke="{stroke}"/>')
                if name:
                    out.append(text(x + w / 2, y + 15, name, "mid xs" + (" muted" if name.startswith("(") else "")))
                if mark == "x":
                    out.append(f'<line x1="{x + 3:g}" y1="{y + 11}" x2="{x + w - 3:g}" y2="{y + 11}" class="line s-red" stroke-width="1.5"/>')
                x += w
        return "".join(out)
    b.append(draw(v4, 20, "IPv4: 20 bytes, or more"))
    b.append(draw(v6, 400, "IPv6: always exactly 40 bytes"))
    legend = [("t-red", "var(--red)", "gone in IPv6"), ("t-yellow", "var(--yellow)", "kept (most renamed)"), ("t-green", "var(--green)", "new")]
    for i, (cls, stroke, label) in enumerate(legend):
        b.append(f'<rect x="{20 + i * 120}" y="200" width="16" height="14" class="{cls}" stroke="{stroke}"/>')
        b.append(text(42 + i * 120, 211, label, "xs"))
    svg = fig("".join(b), 720, 262, "The IPv4 header beside the IPv6 header, showing which fields were removed, renamed, or added",
              "IPv6 threw out everything routers had to work at. No checksum to recompute at every hop, no fragments to cut, no options to parse, and a fixed size.")
    (OUT / "ch25-header.svg").write_text(svg)


# ---------------------------------------------------------------- NAT64

def nat64():
    b = []
    phone, dns, nat, cern = (80, 120), (300, 40), (420, 150), (640, 150)
    b.append(f'<use href="#computer" x="{phone[0] - 30}" y="{phone[1] - 26}" width="60" height="52"/>')
    b.append(text(phone[0], phone[1] + 42, "Alice’s phone", "mid xs b"))
    b.append(text(phone[0], phone[1] + 56, "IPv6 only", "mid xs muted"))
    b.append(f'<use href="#server" x="{dns[0] - 16}" y="{dns[1] - 26}" width="32" height="50"/>')
    b.append(text(dns[0] + 26, dns[1] - 4, "the provider’s", "xs b"))
    b.append(text(dns[0] + 26, dns[1] + 10, "name server (DNS64)", "xs b"))
    b.append(f'<use href="#router" x="{nat[0] - 36}" y="{nat[1] - 20}" width="72" height="42"/>')
    b.append(text(nat[0], nat[1] + 38, "NAT64", "mid xs b"))
    b.append(f'<use href="#server" x="{cern[0] - 16}" y="{cern[1] - 26}" width="32" height="50"/>')
    b.append(text(cern[0], cern[1] + 40, "a server with only IPv4", "mid xs b"))
    b.append(text(cern[0], cern[1] + 54, "203.0.113.80", "mid mono xs"))
    b.append('<g data-show="1"><path d="M112,100 C170,50 220,40 276,40" class="line s-blue" stroke-width="2.5" marker-end="url(#ah-blue)"/>'
             + text(150, 42, "AAAA for oldsite.example?", "mid xs b halo", style="fill:var(--blue)") + "</g>")
    b.append('<g data-show="2"><path d="M300,70 C280,110 200,120 120,120" class="line s-green" stroke-width="2.5" marker-end="url(#ah-green)"/>'
             + text(250, 132, "“64:ff9b::cb00:7150”", "mid mono xs b f-green halo")
             + text(470, 40, "It only has an IPv4 address, 203.0.113.80,", "xs") + text(470, 54, "so the name server makes up an IPv6 one:", "xs")
             + text(470, 68, "64:ff9b:: + cb00:7150 (203.0.113.80 in hex)", "mono xs b") + "</g>")
    b.append('<g data-show="3"><line x1="118" y1="150" x2="378" y2="150" class="line s-purple" stroke-width="3" marker-end="url(#ah-purple)"/>'
             + text(248, 170, "IPv6 packet to 64:ff9b::cb00:7150", "mid xs b halo", style="fill:var(--purple)")
             + '<line x1="462" y1="150" x2="616" y2="150" class="line s-orange" stroke-width="3" marker-end="url(#ah-orange)"/>'
             + text(540, 132, "IPv4 packet to 203.0.113.80", "mid xs b halo f-orange") + "</g>")
    steps = ["Many mobile networks now give phones only IPv6. When Alice’s phone looks up a website that only has an IPv4 address, it asks for an IPv6 address (an AAAA record, Chapter 29), as usual.",
             "The provider’s name server finds no AAAA record, so it <em>makes one up</em>: the IPv4 address, written in hex, on the end of a special prefix, 64:ff9b::/96. This is <strong>DNS64</strong>.",
             "Packets to that prefix are routed to a <strong>NAT64</strong> translator, which rewrites them as IPv4 packets from one of its own IPv4 addresses, like Chapter 22’s NAT, and translates the answers back. The phone never knew."]
    svg = fig("".join(b), 720, 220, "An IPv6-only phone reaching an IPv4-only server through DNS64, which synthesizes an address, and a NAT64 translator",
              "DNS64 and NAT64: how an IPv6-only phone reaches the IPv4 internet.", steps)
    (OUT / "ch25-nat64.svg").write_text(svg)


if __name__ == "__main__":
    anatomy()
    compress()
    eui64()
    nd()
    slaac()
    header()
    nat64()
    print("wrote ch25 figures")
