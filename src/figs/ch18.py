#!/usr/bin/env python3
"""Generate chapter 18 figures.  python3 src/figs/ch18.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def field(x, y, w, h, name, size, cls, stroke, sub=None):
    out = [f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="5" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>',
           text(x + w / 2, y + h / 2 - 2, name, "mid sm b"),
           text(x + w / 2, y + h / 2 + 14, size, "mid xs muted")]
    if sub:
        out.append(text(x + w / 2, y + h + 16, sub, "mid mono xs"))
    return "".join(out)


# ---------------------------------------------------------------- a frame, as it really is

def frame():
    parts = [("preamble", "7 bytes", 62, "f-card", "var(--muted)", "1010…"), ("start", "1", 40, "f-card", "var(--muted)", "…1011"),
             ("to", "6", 72, "t-blue", "var(--blue)", "14:c3:5e…"), ("from", "6", 72, "t-blue", "var(--blue)", "2c:cf:67…"),
             ("type", "2", 50, "t-blue", "var(--blue)", "0800"), ("data", "46 to 1,500 bytes", 250, "t-yellow", "var(--yellow)", "an IP packet"),
             ("check", "4", 50, "t-red", "var(--red)", "CRC-32"), ("gap", "12", 44, "f-none", "var(--muted)", "silence")]
    b, x, xs = [], 14, {}
    for name, size, w, cls, stroke, sub in parts:
        b.append(field(x, 40, w, 50, name, size, cls, stroke, sub))
        xs[name] = (x, x + w)
        x += w + 4
    # brackets
    def bracket(a, c, y, label, cls="s-ink", tcls="mid xs b"):
        return (f'<path d="M{a},{y - 8} L{a},{y} L{c},{y} L{c},{y - 8}" class="line {cls}" stroke-width="2"/>'
                + text((a + c) / 2, y + 16, label, tcls))
    b.append(bracket(xs["to"][0], xs["check"][1], 128, "the frame: 64 to 1,518 bytes. The check covers all of it."))
    b.append(bracket(xs["to"][0], xs["data"][1], 168, "what tcpdump shows you", "s-teal", "mid xs b f-teal"))
    b.append(bracket(xs["preamble"][0], xs["start"][1], 128, "clock sync", "s-muted", "mid xs muted"))
    b.append(text(14, 26, "One Ethernet frame on the cable, in the order it’s sent", "sm b"))
    b.append(text(360, 206, "The card adds the preamble, the check and the gap, and strips them off again on arrival.", "mid hand"))
    svg = fig("".join(b), 720, 220, "The parts of an Ethernet frame on the wire: preamble, start byte, destination, source, type, data, check and gap",
              "A real Ethernet frame. Chapter 3 invented start markers, Chapter 8 the addresses and Chapter 10 the check: it’s all here.")
    (OUT / "ch18-frame.svg").write_text(svg)


# ---------------------------------------------------------------- the bits of a MAC address

def mac():
    b = [text(14, 24, "Two card addresses, taken apart", "sm b")]
    rows = [("2c:cf:67:5e:10:c2", "Grandpa Otto’s Pi", 0x2C), ("e2:5f:b1:3c:77:0a", "Bob’s laptop, on the home Wi-Fi", 0xE2)]
    for n, (addr, who, first) in enumerate(rows):
        y = 48 + n * 150
        bytes_ = addr.split(":")
        b.append(text(14, y + 22, who, "sm b"))
        for i, byte in enumerate(bytes_):
            x = 230 + i * 70
            cls = "t-blue" if i < 3 else "t-green"
            b.append(f'<rect x="{x}" y="{y}" width="62" height="34" rx="5" class="{cls}" stroke="var(--line)" stroke-width="1.5"/>')
            b.append(text(x + 31, y + 23, byte, "mid mono b"))
        b.append(f'<path d="M230,{y + 42} L230,{y + 48} L432,{y + 48} L432,{y + 42}" class="line s-blue" stroke-width="2"/>')
        b.append(f'<path d="M440,{y + 42} L440,{y + 48} L642,{y + 48} L642,{y + 42}" class="line s-green" stroke-width="2"/>')
        maker = "made by: Raspberry Pi" if n == 0 else "made by: nobody!"
        b.append(text(331, y + 64, maker, "mid xs b", style="fill:var(--blue)"))
        b.append(text(541, y + 64, "which card: a serial number" if n == 0 else "random, chosen by the laptop", "mid xs b", style="fill:var(--green)"))
        # the first byte, bit by bit
        bits = f"{first:08b}"
        for k, bit in enumerate(bits):
            x = 14 + k * 24
            special = k >= 6
            cls = "t-orange" if special else "f-card"
            b.append(f'<rect x="{x}" y="{y + 48}" width="22" height="26" rx="3" class="{cls}" stroke="var(--line)"/>')
            b.append(text(x + 11, y + 66, bit, "mid mono sm b"))
        b.append(f'<path d="M244,{y + 36} C220,{y + 44} 210,{y + 46} 200,{y + 52}" class="line s-muted" stroke-width="1.5" marker-end="url(#ah-muted)"/>')
        local = "1 = chosen by software" if first & 2 else "0 = set at the factory"
        group = "1 = a group" if first & 1 else "0 = one card"
        b.append(text(170, y + 92, local, "end xs b f-orange"))
        b.append(text(206, y + 106, group, "end xs b f-orange"))
        b.append(f'<path d="M170,{y + 74} L170,{y + 80}" class="line s-orange" stroke-width="2"/>')
        b.append(f'<path d="M194,{y + 74} L194,{y + 96}" class="line s-orange" stroke-width="2"/>')
    svg = fig("".join(b), 720, 340, "The Pi's factory MAC address with a manufacturer prefix, and the laptop's randomly chosen private address with the 'locally administered' bit set",
              "The first half says who made the card. Two bits of the very first byte say whether it’s a real factory address, and whether it’s a group.")
    (OUT / "ch18-mac.svg").write_text(svg)


# ---------------------------------------------------------------- inside the home router

def homerouter():
    b = [f'<rect x="200" y="30" width="330" height="250" rx="16" class="f-card" stroke="var(--ink)" stroke-width="2"/>',
         text(365, 52, "the “router” on the shelf", "mid slab b")]
    b.append(f'<rect x="222" y="66" width="130" height="60" rx="8" class="t-yellow" stroke="var(--yellow)" stroke-width="2"/>')
    b.append(text(287, 92, "router", "mid sm b"))
    b.append(text(287, 108, "(Chapters 20–22)", "mid xs muted"))
    b.append(f'<rect x="222" y="160" width="130" height="100" rx="8" class="t-teal" stroke="var(--teal-ink)" stroke-width="2"/>')
    b.append(text(287, 186, "4-port switch", "mid sm b"))
    for i in range(4):
        b.append(f'<rect x="{234 + i * 28}" y="206" width="22" height="16" rx="2" class="f-surface" stroke="var(--ink)" stroke-width="1.5"/>')
    b.append(text(287, 244, "(this chapter)", "mid xs muted"))
    b.append(f'<rect x="386" y="160" width="130" height="100" rx="8" class="t-purple" stroke="var(--purple)" stroke-width="2"/>')
    b.append(text(451, 186, "Wi-Fi access", "mid sm b"))
    b.append(text(451, 202, "point", "mid sm b"))
    b.append(text(451, 244, "(Chapter 19)", "mid xs muted"))
    b.append('<line x1="287" y1="126" x2="287" y2="160" class="line" stroke-width="3"/>')
    b.append('<line x1="352" y1="210" x2="386" y2="210" class="line" stroke-width="3"/>')
    b.append(text(369, 202, "bridge", "mid xs muted"))
    b.append(f'<rect x="386" y="70" width="130" height="52" rx="8" class="f-surface" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="4 3"/>')
    b.append(text(451, 92, "also: DHCP, NAT,", "mid xs"))
    b.append(text(451, 107, "a firewall (Ch. 22)", "mid xs"))
    # outside
    b.append('<line x1="222" y1="96" x2="120" y2="96" class="wire" stroke-width="4"/>')
    b.append(f'<use href="#cloud" x="10" y="56" width="120" height="72"/>')
    b.append(text(70, 142, "the internet", "mid xs b"))
    b.append(text(166, 88, "fiber / DSL", "mid xs muted"))
    wired = [("Bob’s gaming PC", 234, 330), ("the TV", 290, 330)]
    for name, px, lx in wired:
        b.append(f'<path d="M{px + 11},222 L{px + 11},{300}" class="wire" stroke-width="3"/>')
    b.append(f'<use href="#computer" x="200" y="296" width="60" height="54"/>')
    b.append(text(230, 362, "Bob’s gaming PC", "mid xs b"))
    b.append(f'<use href="#computer" x="272" y="296" width="60" height="54"/>')
    b.append(text(302, 362, "the TV", "mid xs b"))
    for name, x, y in (("Bob’s laptop", 640, 110), ("Grandpa’s Pi", 640, 200), ("the doorbell", 640, 290)):
        b.append(f'<use href="#computer" x="{x - 28}" y="{y - 26}" width="56" height="50"/>')
        b.append(text(x, y + 38, name, "mid xs b"))
        b.append(f'<path d="M520,210 Q560,{(210 + y) / 2} {x - 32},{y}" class="line s-purple dot-line" stroke-width="2.5"/>')
    svg = fig("".join(b), 720, 372, "Inside a home router: a router, a four-port switch and a Wi-Fi access point, bridged together into one network",
              "One box, three jobs. Everything plugged into the switch or joined to the Wi-Fi is on the same Ethernet network.")
    (OUT / "ch18-homerouter.svg").write_text(svg)


# ---------------------------------------------------------------- the VLAN tag

def tag():
    b = [text(14, 24, "An ordinary frame, and the same frame with an 802.1Q tag", "sm b")]
    y1, y2 = 40, 116
    plain = [("to", "6", 90, "t-blue", "var(--blue)"), ("from", "6", 90, "t-blue", "var(--blue)"), ("type", "0800", 70, "t-blue", "var(--blue)"),
             ("data", "", 300, "t-yellow", "var(--yellow)"), ("check", "", 60, "t-red", "var(--red)")]
    x = 14
    for name, size, w, cls, stroke in plain:
        b.append(field(x, y1, w, 44, name, size, cls, stroke))
        x += w + 4
    tagged = [("to", "6", 90, "t-blue", "var(--blue)"), ("from", "6", 90, "t-blue", "var(--blue)"),
              ("tag", "8100 · VLAN 20", 120, "t-orange", "var(--orange)"), ("type", "0800", 70, "t-blue", "var(--blue)"),
              ("data", "", 230, "t-yellow", "var(--yellow)"), ("check", "new!", 60, "t-red", "var(--red)")]
    x = 14
    for name, size, w, cls, stroke in tagged:
        b.append(field(x, y2, w, 44, name, size, cls, stroke))
        if name == "tag":
            tx = x
        x += w + 4
    # zoom into the tag
    zy = 206
    bits = [("TPID: 0x8100", "16 bits", 256, "“a tag follows”"), ("PCP", "3", 60, "priority 0–7"), ("DEI", "1", 40, ""),
            ("VID: 000000010100", "12 bits = 20", 300, "the VLAN number: 1 to 4094")]
    x = 30
    b.append(f'<path d="M{tx},{y2 + 44} L30,{zy} M{tx + 120},{y2 + 44} L{30 + 256 + 60 + 40 + 300 + 12},{zy}" class="line s-orange" stroke-width="1.2" style="opacity:0.7"/>')
    for name, size, w, note in bits:
        b.append(field(x, zy, w, 44, name, size, "t-orange", "var(--orange)"))
        if note:
            b.append(text(x + w / 2, zy + 62, note, "mid xs"))
        x += w + 4
    svg = fig("".join(b), 720, 284, "An 802.1Q VLAN tag of four bytes inserted between the source address and the type field, and its bit fields",
              "A VLAN tag: four bytes squeezed in after the addresses. Old equipment sees type 8100, doesn’t understand it, and leaves the frame alone.")
    (OUT / "ch18-tag.svg").write_text(svg)


if __name__ == "__main__":
    frame()
    mac()
    homerouter()
    tag()
    print("wrote ch18 figures")
