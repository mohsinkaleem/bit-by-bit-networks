#!/usr/bin/env python3
"""Generate chapter 43 figures.  python3 src/figs/ch43.py"""
import sys
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent
sys.path.insert(0, str(OUT.parent.parent / "labs" / "ch43"))
import ndn  # noqa: E402


def box(x, y, w, h, cls="f-card", stroke="var(--line)", rx=8, dash=False, sw=1.6):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" class="{cls}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def line(x1, y1, x2, y2, cls="s-ink", w=2.2, arrow=False, dash=False):
    mk = f' marker-end="url(#ah-{"ink" if cls == "s-ink" else cls[2:]})"' if arrow else ""
    d = ' stroke-dasharray="5 4"' if dash else ""
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="{w}"{mk}{d}/>'


# ---------------------------------------------------------------- where vs what

def whatwhere():
    b = [box(10, 10, 340, 190, "f-card"), box(370, 10, 340, 190, "f-card"),
         text(180, 34, "IP: a letter to an address", "mid sm b"), text(540, 34, "NDN: a request for a thing", "mid sm b")]
    b.append(box(40, 50, 280, 70, "t-blue", "var(--blue)", 6))
    b.append(text(56, 72, "to:    172.66.157.237", "xs mono b"))
    b.append(text(56, 90, "from:  192.168.1.3", "xs mono"))
    b.append(text(56, 108, "“GET /garden/beans.jpg”", "xs mono muted"))
    b.append(text(180, 142, "The network only reads the address.", "mid xs"))
    b.append(text(180, 158, "What’s inside is the two ends’ business:", "mid xs"))
    b.append(text(180, 174, "every copy comes from that one machine.", "mid xs"))
    b.append(box(400, 50, 280, 70, "t-green", "var(--green)", 6))
    b.append(text(416, 72, "Interest:", "xs b"))
    b.append(text(416, 92, "/grandpa/garden/beans.jpg/seg=3", "xs mono b"))
    b.append(text(416, 110, "(no address at all, on either side)", "xs muted"))
    b.append(text(540, 142, "The network reads the name. Any router", "mid xs"))
    b.append(text(540, 158, "or cache holding that Data may answer:", "mid xs"))
    b.append(text(540, 174, "the Data carries its own signature.", "mid xs"))
    svg = fig("".join(b), 720, 210, "Left: an IP packet with destination and source addresses. Right: an NDN Interest carrying only a name for the content wanted",
              "The internet was designed for conversations between machines. Most of what it carries now is people asking for things.")
    (OUT / "ch43-whatwhere.svg").write_text(svg)


# ---------------------------------------------------------------- the two packets, byte by byte

def packets():
    interest = ndn.tlv(ndn.INTEREST, ndn.make_name("/ndn/edu/ucla/ping/31415") + ndn.tlv(ndn.NONCE, bytes.fromhex("5a1c9e02"))
                       + ndn.tlv(ndn.LIFETIME, (4000).to_bytes(2, "big")))
    rows = [("05 29", "Interest, 41 bytes follow", "t-green"),
            ("07 1d", "Name, 29 bytes:", "t-blue"),
            ("08 03 6e 64 6e", "   component “ndn”", "t-blue"),
            ("08 03 65 64 75", "   component “edu”", "t-blue"),
            ("08 04 75 63 6c 61", "   component “ucla”", "t-blue"),
            ("08 04 70 69 6e 67", "   component “ping”", "t-blue"),
            ("08 05 33 31 34 31 35", "   component “31415”", "t-blue"),
            ("0a 04 5a 1c 9e 02", "Nonce: 4 random bytes, to catch loops", "t-orange"),
            ("0c 02 0f a0", "InterestLifetime: 4,000 ms", "t-orange")]
    assert interest.hex(" ").startswith("05 29 07 1d")
    b = [text(20, 22, "an Interest, 43 bytes: every piece is Type, Length, Value", "xs b")]
    for i, (hexs, what, cls) in enumerate(rows):
        y = 32 + i * 26
        b.append(box(20, y, 220, 21, cls, "none", 4, sw=0))
        b.append(text(30, y + 15, hexs, "xs mono b"))
        b.append(text(250, y + 15, what, "xs"))
    x0 = 420
    b.append(text(x0, 22, "the Data that answers it", "xs b"))
    drows = [("06", "Data", "t-green"), ("07", "Name: the same /ndn/edu/ucla/ping/31415", "t-blue"),
             ("14", "MetaInfo: fresh for 1,000 ms", "t-orange"), ("15", "Content (a real one would hold the thing)", "t-yellow"),
             ("16", "SignatureInfo: type 0, a SHA-256 digest", "t-purple"), ("17", "SignatureValue: 32 bytes", "t-purple")]
    for i, (t, what, cls) in enumerate(drows):
        y = 32 + i * 30
        b.append(box(x0, y, 36, 24, cls, "none", 4, sw=0))
        b.append(text(x0 + 18, y + 16, t, "mid xs mono b"))
        b.append(text(x0 + 46, y + 16, what, "xs"))
    b.append(f'<path d="M{x0 - 8},{32 + 30} L{x0 - 14},{32 + 30} L{x0 - 14},{32 + 4 * 30 + 24} L{x0 - 8},{32 + 4 * 30 + 24}" class="line s-purple" stroke-width="1.6" fill="none"/>')
    b.append(text(x0, 32 + 6 * 30 + 16, "The signature covers the name and the content", "xs"))
    b.append(text(x0, 32 + 6 * 30 + 32, "together: a name can’t be moved to other data.", "xs"))
    svg = fig("".join(b), 720, 32 + 9 * 26 + 8, "The bytes of an NDN Interest: type 5, a name made of components, a nonce and a lifetime; and the fields of the Data packet that answers it",
              "NDN’s two packet types. There are no addresses anywhere: routers forward on the name, and the Data’s signature is what makes it trustworthy, wherever it came from.")
    (OUT / "ch43-packets.svg").write_text(svg)


# ---------------------------------------------------------------- inside a router: CS, PIT, FIB

def router():
    b = []
    # consumers, router, upstream
    for i, (y, label) in enumerate(((60, "Bob’s MacBook"), (150, "Alice’s phone"))):
        b.append(box(14, y - 18, 130, 36, "f-card", "var(--line)", 6))
        b.append(text(79, y + 5, label, "mid xs b"))
    b.append(box(240, 20, 240, 200, "f-surface", "var(--line)", 12))
    b.append(text(360, 40, "Grandpa’s Pi: an NDN router", "mid xs b"))
    tables = [("Content Store", "copies of Data it has passed on", 56, "t-yellow", "var(--yellow)"),
              ("Pending Interest Table", "who is waiting for what", 110, "t-orange", "var(--orange)"),
              ("Forwarding table (FIB)", "/ndn → the testbed · /grandpa → here", 164, "t-blue", "var(--blue)")]
    for name, what, y, cls, stroke in tables:
        b.append(box(256, y, 208, 44, cls, stroke, 6))
        b.append(text(360, y + 18, name, "mid xs b"))
        b.append(text(360, y + 34, what, "mid xs"))
    b.append(box(580, 90, 124, 50, "f-card", "var(--line)", 6))
    b.append(text(642, 110, "the testbed", "mid xs b"))
    b.append(text(642, 126, "(UCLA)", "mid xs muted"))
    # step 1: Interest from Bob; CS miss; PIT entry; FIB → forward
    b.append('<g data-show="=1">' + line(146, 60, 250, 70, "s-green", 2.5, arrow=True) + text(190, 52, "Interest", "mid xs b f-green")
             + text(470, 74, "✗ not in the store", "xs f-red")
             + text(470, 128, "+ Bob is waiting", "xs b f-orange") + text(470, 184, "longest match: /ndn", "xs")
             + line(466, 196, 578, 124, "s-green", 2.5, arrow=True) + "</g>")
    # step 2: Alice asks for the same thing: PIT aggregation
    b.append('<g data-show="=2">' + line(146, 150, 250, 132, "s-green", 2.5, arrow=True) + text(196, 160, "same Interest", "mid xs b f-green")
             + text(470, 128, "+ Alice too: 2 waiting", "xs b f-orange") + text(470, 144, "nothing more sent upstream", "xs") + "</g>")
    # step 3: Data comes back, follows the breadcrumbs, is cached
    b.append('<g data-show="=3">' + line(578, 116, 470, 132, "s-purple", 2.5, arrow=True) + text(528, 108, "Data", "mid xs b f-purple")
             + line(250, 126, 148, 64, "s-purple", 2.5, arrow=True) + line(250, 136, 148, 150, "s-purple", 2.5, arrow=True)
             + text(470, 74, "✓ keep a copy", "xs b f-green") + text(470, 144, "entry used up", "xs") + "</g>")
    # step 4: later, from the store
    b.append('<g data-show="=4">' + line(146, 60, 250, 70, "s-green", 2.5, arrow=True) + line(250, 76, 148, 66, "s-purple", 2.5, arrow=True)
             + text(470, 74, "✓ in the store: answered here", "xs b f-green") + text(470, 184, "the testbed never hears of it", "xs") + "</g>")
    steps = ["An Interest arrives. Is a copy already in the <strong>content store</strong>? No. So the router writes down, in the <strong>pending interest table</strong>, who asked, and looks up the name in its <strong>forwarding table</strong> by longest prefix match (Chapter 23), and sends the Interest on.",
             "Before an answer comes back, someone else asks for exactly the same name. The router doesn’t send a second Interest: it just adds them to the waiting list. That’s free multicast.",
             "The Data comes back. It has no destination address, so how does it find its way? By the breadcrumbs: every router on the way remembered who asked. The Data goes to everyone waiting, the entry is crossed off, and a copy is kept.",
             "Later, anyone else who asks gets the copy straight from the store. The more popular something is, the closer to people its copies end up."]
    svg = fig("".join(b), 720, 232, "An NDN router with a content store, pending interest table and forwarding table, handling Interests from two devices and Data from the testbed",
              "What this chapter’s <code>ndn.py router</code> does with every packet, and exactly what it did on Grandpa’s Pi.", steps)
    (OUT / "ch43-router.svg").write_text(svg)


if __name__ == "__main__":
    whatwhere()
    packets()
    router()
    print("wrote ch43 figures")
