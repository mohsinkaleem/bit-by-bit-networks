#!/usr/bin/env python3
"""Generate chapter 22 figures.  python3 src/figs/ch22.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- DORA

def dora():
    seq = Seq([("Alice’s laptop", 150, None), ("the router’s DHCP server", 570, None)], top=40, scale=30, head=False)
    msgs = [("Alice’s laptop", "the router’s DHCP server", 0.4, "DISCOVER: “I need an address”", "1", "from 0.0.0.0, to everyone (255.255.255.255)"),
            ("the router’s DHCP server", "Alice’s laptop", 2.0, "OFFER: “how about 192.168.1.7?”", "2", "plus mask, router, name server, 24 hours"),
            ("Alice’s laptop", "the router’s DHCP server", 3.6, "REQUEST: “yes please, 192.168.1.7”", "3", "still broadcast: other servers learn they lost"),
            ("the router’s DHCP server", "Alice’s laptop", 5.2, "ACK: “it’s yours for 24 hours”", "4", None),
            ("Alice’s laptop", "the router’s DHCP server", 7.4, "REQUEST: “can I keep it?”", "5", "12 hours later: straight to the server"),
            ("the router’s DHCP server", "Alice’s laptop", 9.0, "ACK: “another 24 hours”", "5", None)]
    for a, c, t, label, step, sub in msgs:
        seq.msg(a, c, t, t + 0.5, label, "navy" if a.startswith("Alice") else "purple", step=step, sub=sub)
    seq.note("Alice’s laptop", 6.4, "…12 hours pass…", step="5")
    body, bottom = seq.render(24)
    steps = ["<strong>Discover.</strong> Alice’s laptop has no address, and doesn’t know who to ask, so it sends from 0.0.0.0 to the broadcast address 255.255.255.255, UDP port 67.",
             "<strong>Offer.</strong> Any DHCP server that hears it offers an address from its pool, with everything else the laptop needs: the netmask, the router, the name server, and how long it can keep them.",
             "<strong>Request.</strong> The laptop accepts one offer, and says so to everyone, so that any other server that made an offer knows it wasn’t chosen.",
             "<strong>Acknowledge.</strong> The server confirms. The laptop checks that nobody else is using the address (the ARP probe from Chapter 21), and it’s online.",
             "The address is only <strong>leased</strong>. Half-way through, the laptop asks the same server, directly this time, to renew it. If that server is gone, it tries anyone at 87.5%, and when the lease runs out it must stop using the address."]
    svg = fig(body, 720, bottom, "The four DHCP messages, discover, offer, request and acknowledge, followed by a renewal half-way through the lease",
              "Discover, offer, request, acknowledge: DORA.", steps)
    (OUT / "ch22-dora.svg").write_text(svg)


# ---------------------------------------------------------------- NAT, step by step

def nat():
    lx, nx, rx = 120, 360, 600
    b = [f'<rect x="8" y="8" width="250" height="216" rx="10" class="t-green" style="opacity:0.6"/>',
         text(20, 28, "inside: private addresses", "xs b f-green"),
         text(706, 28, "outside: the internet", "end xs b", style="fill:var(--blue)")]
    b.append(f'<use href="#computer" x="{lx - 70}" y="60" width="56" height="50"/>')
    b.append(text(lx - 42, 124, "Bob’s laptop", "mid xs b"))
    b.append(text(lx - 42, 138, "192.168.1.3", "mid mono xs"))
    b.append(f'<use href="#router" x="{nx - 40}" y="66" width="80" height="52"/>')
    b.append(text(nx, 136, "home router", "mid xs b"))
    b.append(text(nx, 150, "outside: 203.0.113.77", "mid mono xs"))
    b.append(f'<use href="#server" x="{rx + 40}" y="58" width="36" height="58"/>')
    b.append(text(rx + 58, 130, "info.cern.ch", "mid xs b"))
    b.append(text(rx + 58, 144, "188.184.67.127", "mid mono xs"))
    b.append(f'<line x1="{lx - 10}" y1="90" x2="{nx - 42}" y2="90" class="wire" stroke-width="3"/>')
    b.append(f'<line x1="{nx + 42}" y1="90" x2="{rx + 36}" y2="90" class="line s-muted dash" stroke-width="2"/>')

    def env(x, y, src, dst, cls, stroke, step):
        return (f'<g data-show="{step}"><rect x="{x}" y="{y}" width="200" height="40" rx="6" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>'
                + text(x + 10, y + 16, "from " + src, "mono xs") + text(x + 10, y + 32, "to " + dst, "mono xs") + "</g>")
    b.append(env(20, 166, "192.168.1.3:52000", "188.184.67.127:80", "f-surface", "var(--green)", "=1"))
    b.append(f'<g data-show="=1"><path d="M222,186 L300,186" class="line s-green" stroke-width="2.5" marker-end="url(#ah-green)"/></g>')
    b.append(env(470, 166, "203.0.113.77:52000", "188.184.67.127:80", "f-surface", "var(--blue)", "=2"))
    b.append(f'<g data-show="=2"><path d="M420,186 L466,186" class="line s-blue" stroke-width="2.5" marker-end="url(#ah-blue)"/>'
             + text(nx, 186, "rewrite the “from”", "mid hand f-orange") + "</g>")
    b.append(f'<g data-show="2-4"><rect x="260" y="236" width="200" height="46" rx="6" class="t-yellow" stroke="var(--yellow)" stroke-width="1.5"/>'
             + text(360, 254, "NAT table", "mid xs b") + text(360, 272, ":52000 ↔ 192.168.1.3:52000", "mid mono xs") + "</g>")
    b.append(env(470, 166, "188.184.67.127:80", "203.0.113.77:52000", "f-surface", "var(--blue)", "=3"))
    b.append(f'<g data-show="=3"><path d="M466,186 L420,186" class="line s-blue" stroke-width="2.5" marker-end="url(#ah-blue)"/>'
             + text(nx, 186, "look it up…", "mid hand f-orange") + "</g>")
    b.append(env(20, 166, "188.184.67.127:80", "192.168.1.3:52000", "f-surface", "var(--green)", "=3"))
    b.append(f'<g data-show="=3"><path d="M300,186 L222,186" class="line s-green" stroke-width="2.5" marker-end="url(#ah-green)"/></g>')
    b.append(env(470, 166, "198.51.100.66:4444", "203.0.113.77:22", "t-red", "var(--red)", "=4"))
    b.append(f'<g data-show="=4"><path d="M466,186 L420,186" class="line s-red" stroke-width="2.5" marker-end="url(#ah-red)"/>'
             + text(nx - 40, 190, "✗ no entry: dropped", "mid hand f-red") + "</g>")
    steps = ["Bob’s laptop sends a packet to CERN, from its private address. That address means nothing on the internet: millions of homes use 192.168.1.3.",
             "On the way out, the router swaps the private source for its own public address, and notes what it did in its table. (It also fixes the IP and TCP checksums, since the addresses are part of what they check.)",
             "CERN’s answer comes back to the router’s public address. The router looks up port 52000 in its table, swaps the destination back to 192.168.1.3:52000, and sends it on. Neither the laptop nor CERN ever knows.",
             "A packet that isn’t an answer to anything finds no entry in the table, and the router has no idea which device it might be for. It’s thrown away. That’s why NAT works as a basic firewall, and why you can’t easily run a server at home."]
    svg = fig("".join(b), 720, 292, "A home router rewriting the source address of an outgoing packet, recording it in its NAT table, translating the reply back, and dropping an unsolicited packet",
              "Network address translation: one public address shared by a whole house.", steps)
    (OUT / "ch22-nat.svg").write_text(svg)


# ---------------------------------------------------------------- NAT inside NAT

def cgnat():
    boxes = [(14, 150, "Bob’s house", "192.168.1.0/24", "t-green", "var(--green)"),
             (200, 160, "home router", "outside: 100.72.14.9", "t-yellow", "var(--yellow)"),
             (396, 150, "provider’s big NAT", "outside: 203.0.113.77", "t-orange", "var(--orange)"),
             (582, 124, "the internet", "", "t-blue", "var(--blue)")]
    b = []
    for x, w, name, sub, cls, stroke in boxes:
        b.append(f'<rect x="{x}" y="40" width="{w}" height="70" rx="10" class="{cls}" stroke="{stroke}" stroke-width="2"/>')
        b.append(text(x + w / 2, 70, name, "mid sm b"))
        if sub:
            b.append(text(x + w / 2, 90, sub, "mid mono xs"))
    for x in (166, 362, 548):
        b.append(f'<path d="M{x},75 L{x + 30},75" class="line" stroke-width="2.5" marker-end="url(#ah-ink)"/>')
    b.append(text(360, 140, "With carrier-grade NAT, the home router’s “outside” address is private too (100.64.0.0/10),", "mid xs"))
    b.append(text(360, 156, "and hundreds of homes share each of the provider’s public addresses.", "mid xs"))
    svg = fig("".join(b), 720, 170, "Double NAT: a home router's NAT behind an internet provider's carrier-grade NAT",
              "NAT inside NAT. Many mobile networks, and some home internet providers, work like this.")
    (OUT / "ch22-cgnat.svg").write_text(svg)


# ---------------------------------------------------------------- hole punching

def punch():
    b = []
    cols = {"bob": 70, "nat_b": 220, "stun": 360, "nat_a": 500, "alice": 650}
    labels = {"bob": ("Bob", "192.168.1.3"), "nat_b": ("Bob’s router", "203.0.113.77"), "stun": ("STUN server", "192.0.2.1"),
              "nat_a": ("university NAT", "198.51.100.9"), "alice": ("Alice", "10.23.147.8")}
    for k, x in cols.items():
        sprite = "#computer" if k in ("bob", "alice") else "#server" if k == "stun" else "#router"
        w, hgt = (50, 45) if sprite == "#computer" else (30, 48) if sprite == "#server" else (60, 40)
        b.append(f'<use href="{sprite}" x="{x - w / 2}" y="{40 - hgt / 2}" width="{w}" height="{hgt}"/>')
        b.append(text(x, 80, labels[k][0], "mid xs b"))
        b.append(text(x, 94, labels[k][1], "mid mono xs"))
        b.append(f'<line x1="{x}" y1="102" x2="{x}" y2="262" class="line s-muted" stroke-width="1.5" stroke-dasharray="2 5"/>')

    def arrow(a, c, y, label, cls, step, lost=False):
        x1, x2 = cols[a], cols[c]
        end = x2 - (8 if x2 > x1 else -8)
        head = "" if lost else f' marker-end="url(#ah-{cls})"'
        out = f'<g data-show="{step}"><line x1="{x1}" y1="{y}" x2="{end}" y2="{y}" class="line s-{cls}" stroke-width="2.5"{head}/>'
        if lost:
            out += f'<path d="M{end - 7},{y - 7} l14,14 M{end + 7},{y - 7} l-14,14" class="line s-red" stroke-width="3"/>'
        return out + text((x1 + x2) / 2, y - 7, label, "mid xs b halo") + "</g>"
    b.append(arrow("bob", "stun", 122, "what do I look like?", "blue", "1"))
    b.append(arrow("alice", "stun", 142, "what do I look like?", "purple", "1"))
    b.append(arrow("stun", "bob", 172, "Alice is 198.51.100.9:41000", "green", "2"))
    b.append(arrow("stun", "alice", 192, "Bob is 203.0.113.77:50000", "green", "2"))
    b.append(arrow("alice", "nat_b", 222, "hello Bob", "purple", "3", lost=True))
    b.append(arrow("bob", "alice", 248, "hello Alice: gets through!", "blue", "4"))
    steps = ["Alice, at university, and Bob, at home, want to play a game directly, with no server in the middle. Both are behind NATs. First, each asks a STUN server what its address and port look like from outside.",
             "The game’s server passes each one’s outside address to the other.",
             "Alice sends a packet to Bob’s outside address. Bob’s router has no entry for her, so it drops it. But her own NAT now has an entry saying “Alice is talking to 203.0.113.77:50000”.",
             "Bob sends to Alice’s outside address. It passes his router (creating an entry for her), and arrives at her NAT, which sees an answer to her packet, and lets it in. Both holes are open. This is <strong>hole punching</strong>, and it’s how most video calls connect."]
    svg = fig("".join(b), 720, 272, "Two computers behind two NATs learn their outside addresses from a STUN server and punch holes by sending to each other",
              "Getting through two NATs at once.", steps)
    (OUT / "ch22-punch.svg").write_text(svg)


# ---------------------------------------------------------------- names without a name server

def mdns():
    b = [f'<rect x="140" y="30" width="440" height="190" rx="14" class="f-card" stroke="var(--line)" stroke-width="1.5"/>',
         text(360, 50, "Bob’s home network", "mid sm b")]
    spots = [("Bob’s laptop", 220, 100, "#computer"), ("Grandpa’s Pi", 500, 100, "#computer"), ("the printer", 220, 180, "#computer"),
             ("the TV", 500, 180, "#computer")]
    for name, x, y, sprite in spots:
        b.append(f'<use href="{sprite}" x="{x - 24}" y="{y - 22}" width="48" height="43"/>')
        b.append(text(x, y + 34, name, "mid xs b"))
    b.append(f'<g data-show="1"><circle cx="220" cy="100" r="60" class="f-none s-orange" stroke-width="2" stroke-dasharray="5 4"/>'
             f'<circle cx="220" cy="100" r="110" class="f-none s-orange" stroke-width="1.5" stroke-dasharray="5 4" style="opacity:0.6"/>'
             + text(40, 96, "to 224.0.0.251:", "xs b f-orange") + text(40, 110, "“who is", "xs b f-orange")
             + text(40, 124, "raspberrypi.local?”", "xs b f-orange") + "</g>")
    b.append(f'<g data-show="2"><path d="M470,108 C400,140 300,140 250,110" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/>'
             + text(600, 96, "“that’s me:", "xs b f-green") + text(600, 110, "192.168.1.4”", "xs b f-green") + "</g>")
    steps = ["Bob types <code>ssh raspberrypi.local</code>. Names ending in <code>.local</code> aren’t looked up in DNS: his laptop sends the question to the multicast address 224.0.0.251, UDP port 5353, which every device on the network listens to.",
             "The Pi recognizes its own name and answers. No name server was involved, and nobody had to configure anything."]
    svg = fig("".join(b), 720, 234, "A laptop multicasting a question for raspberrypi.local to every device on the network, and the Pi answering",
              "Multicast DNS: ask everyone, and let the right one answer.", steps)
    (OUT / "ch22-mdns.svg").write_text(svg)


if __name__ == "__main__":
    dora()
    nat()
    cgnat()
    punch()
    mdns()
    print("wrote ch22 figures")
