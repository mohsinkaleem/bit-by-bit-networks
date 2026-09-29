#!/usr/bin/env python3
"""Generate chapter 12 figures.  python3 src/figs/ch12.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


def envelope(x, y, label, cls="t-yellow", stroke="var(--yellow)", w=150):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="40" rx="5" class="{cls}" stroke="{stroke}" stroke-width="2"/>'
            f'<path d="M{x},{y} L{x + w / 2},{y + 20} L{x + w},{y}" class="line" style="stroke:{stroke}" stroke-width="1.5"/>'
            + text(x + w / 2, y + 34, label, "mid mono xs b"))


# ---------------------------------------------------------------- numbered mailboxes

def mailboxes():
    body = [f'<rect x="300" y="26" width="406" height="262" rx="16" class="f-card" stroke="var(--ink)" stroke-width="2"/>',
            text(503, 50, "Otto’s computer, 4.2", "mid slab b"),
            f'<rect x="318" y="66" width="104" height="206" rx="10" class="t-teal" stroke="var(--teal)" stroke-width="2"/>',
            text(370, 162, "operating", "mid sm b"), text(370, 180, "system", "mid sm b"),
            text(370, 202, "(the mailroom)", "mid xs muted")]
    progs = [("chat", 7, 88, "t-blue", "var(--blue)"), ("chess", 64, 152, "t-green", "var(--green)"), ("clock", 123, 216, "t-purple", "var(--purple)")]
    for name, port, y, cls, stroke in progs:
        body.append(f'<rect x="530" y="{y}" width="160" height="46" rx="8" class="{cls}" stroke="{stroke}" stroke-width="2"/>')
        body.append(text(610, y + 29, name, "mid slab b"))
        body.append(f'<rect x="470" y="{y + 7}" width="50" height="32" rx="6" class="f-surface" stroke="var(--ink)" stroke-width="2"/>')
        body.append(text(495, y + 29, str(port), "mid mono b"))
        body.append(f'<line x1="422" y1="{y + 23}" x2="466" y2="{y + 23}" class="line" stroke-width="2.5" marker-end="url(#ah-ink)"/>')
    body.append(text(495, 276, "ports", "mid hand"))
    incoming = [("to port 64", 70, "var(--green)"), ("to port 7", 130, "var(--blue)"), ("to port 123", 190, "var(--purple)")]
    for label, y, colour in incoming:
        body.append(envelope(40, y, label))
        body.append(f'<line x1="196" y1="{y + 20}" x2="312" y2="{y + 30}" class="line" style="stroke:{colour}" stroke-width="2.5" '
                    f'marker-end="url(#ah-muted)"/>')
    body.append(envelope(40, 250, "to port 99", "t-red", "var(--red)"))
    body.append(f'<line x1="196" y1="266" x2="312" y2="256" class="line s-red" stroke-width="2.5" marker-end="url(#ah-red)"/>')
    body.append(f'<path d="M318,250 C260,300 210,300 196,284" class="line s-red dash" stroke-width="2" marker-end="url(#ah-red)"/>')
    body.append(text(250, 312, "“nobody home at port 99”", "mid hand f-red"))
    body.append(text(118, 52, "Arriving packets", "mid sm muted"))
    svg = fig("".join(body), 720, 322, "Packets arriving at Otto's computer are sorted into numbered ports, one per program",
              "Every program gets a numbered mailbox. The operating system reads the number and delivers to the right one.")
    (OUT / "ch12-mailboxes.svg").write_text(svg)


# ---------------------------------------------------------------- the datagram header

def layout():
    parts = [("to port", "64", "2", 110, "t-green"), ("from port", "51234", "2", 110, "t-green"),
             ("length", "10", "2", 110, "t-green"), ("check", "a CRC-like sum", "2", 110, "t-red"), ("data", "“e4”", "any", 234, "t-yellow")]
    body, x = [], 14
    for name, val, size, w, cls in parts:
        body.append(f'<rect x="{x}" y="30" width="{w}" height="62" rx="6" class="{cls}" stroke="var(--line)"/>')
        body.append(text(x + w / 2, 54, name, "mid slab b"))
        body.append(text(x + w / 2, 78, val, "mid mono xs"))
        body.append(text(x + w / 2, 112, f"{size} bytes", "mid xs muted"))
        x += w + 2
    body.append('<path d="M14,124 L14,132 L458,132 L458,124" class="line s-green" stroke-width="2"/>')
    body.append(text(236, 152, "the whole header: just 8 bytes", "mid hand f-green"))
    svg = fig("".join(body), 720, 164, "Datagram header: destination port, source port, length and check, then the data",
              "A datagram: four small numbers, then the message.")
    (OUT / "ch12-layout.svg").write_text(svg)


# ---------------------------------------------------------------- nesting dolls

def nesting():
    layers = [("frame", "to c4:01 · from c1:01", 14, 706, 24, 196, "t-blue", "var(--blue)", "switches and cards read this"),
              ("packet", "to 4.2 · from 1.1 · hops left 62", 34, 646, 56, 182, "t-yellow", "var(--yellow)", "routers read this"),
              ("datagram", "to port 64 · from port 51234", 54, 626, 88, 168, "t-green", "var(--green)", "the operating system reads this"),
              ("data", "e4", 74, 606, 120, 154, "t-purple", "var(--purple)", "the chess program reads this")]
    body = []
    for name, header, x0, x1, y0, y1, cls, stroke, reader in layers:
        body.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="10" class="{cls}" stroke="{stroke}" stroke-width="2"/>')
        body.append(text(x0 + 12, y0 + 21, name, "sm b"))
        body.append(text(x0 + 96, y0 + 21, header, "mono xs"))
        body.append(text(min(x1 - 12, 640), y0 + 21, reader, "end hand xs muted"))
    body.append(f'<rect x="650" y="30" width="50" height="160" rx="6" class="t-red" stroke="var(--red)" stroke-width="1.5"/>')
    body.append(text(675, 116, "check", "mid xs b", transform="rotate(-90 675 112)"))
    svg = fig("".join(body), 720, 208, "Four nested envelopes: frame, packet, datagram, data, each read by a different part of the system",
              "Envelopes inside envelopes. Each layer only reads its own.")
    (OUT / "ch12-nesting.svg").write_text(svg)


# ---------------------------------------------------------------- four numbers per conversation

def games():
    body = [f'<rect x="470" y="30" width="236" height="250" rx="14" class="f-card" stroke="var(--ink)" stroke-width="2"/>',
            text(588, 54, "Otto 4.2, chess on port 64", "mid sm b")]
    players = [("alice", "Alice", "1.1", 51234, 60, "var(--blue)"), ("alice", "Alice’s 2nd window", "1.1", 51240, 150, "var(--purple)"),
               ("bob", "Bob", "1.2", 50999, 240, "var(--green)")]
    for i, (sid, name, addr, port, y, colour) in enumerate(players):
        body.append(f'<use href="#{sid}-head" x="14" y="{y - 24}" width="48" height="48"/>')
        body.append(text(72, y - 4, name, "sm b"))
        body.append(text(72, y + 16, f"{addr} port {port}", "mono xs"))
        gy = 74 + i * 68
        body.append(f'<line x1="240" y1="{y}" x2="486" y2="{gy + 22}" class="line" style="stroke:{colour}" stroke-width="3"/>')
        body.append(f'<rect x="486" y="{gy}" width="204" height="48" rx="8" class="f-surface" stroke="{colour}" stroke-width="2.5"/>')
        body.append(text(498, gy + 20, f"game #{i + 1}", "sm b"))
        body.append(text(498, gy + 38, f"with {addr}:{port}", "mono xs"))
        for k in range(4):
            for j in range(4):
                if (k + j) % 2:
                    body.append(f'<rect x="{652 + k * 7}" y="{gy + 10 + j * 7}" width="7" height="7" class="f-ink" opacity="0.7"/>')
        body.append(f'<rect x="652" y="{gy + 10}" width="28" height="28" class="f-none" stroke="var(--ink)" stroke-width="1"/>')
    body.append(text(360, 306, "Otto’s address and port are the same for all three. The other end’s address and port tell the games apart.", "mid sm"))
    svg = fig("".join(body), 720, 318, "Three chess games on Otto's port 64, told apart by the other player's address and port",
              "Four numbers name a conversation: both addresses and both ports.")
    (OUT / "ch12-games.svg").write_text(svg)


# ---------------------------------------------------------------- fire and forget

def forget():
    seq = Seq([("Alice", 150, "alice"), ("Otto", 570, None)], top=86, scale=32)
    seq.msg("Alice", "Otto", 0, 1, "#1", cls="blue", step="1")
    seq.note("Otto", 1.1, "got #1", step="1", side="right")
    seq.msg("Alice", "Otto", 1.2, 2.2, "#2", cls="blue", step="2", lost=0.55)
    seq.note("Alice", 2.2, "(she has no idea)", step="2", cls="muted")
    seq.msg("Alice", "Otto", 2.6, 5.0, "#3", cls="blue", step="3", label_at=0.35, sub="the long way round")
    seq.msg("Alice", "Otto", 3.2, 4.2, "#4", cls="blue", step="3", label_at=0.7)
    seq.note("Otto", 4.3, "got #4", step="3", side="right")
    seq.note("Otto", 5.1, "got #3 (late!)", step="3", side="right")
    seq.msg("Alice", "Otto", 5.6, 6.6, "#5", cls="blue", step="4")
    seq.msg("Alice", "Otto", 5.6, 7.5, "#5 again", cls="orange", step="4", label_at=0.72)
    seq.note("Otto", 6.7, "got #5", step="4", side="right")
    seq.note("Otto", 7.6, "got #5 twice?!", step="4", side="right", cls="f-red")
    body, bottom = seq.render()
    body += '<use href="#computer" x="546" y="10" width="48" height="44"/>'
    steps = ["Alice sends five datagrams to Otto. The first one arrives, as most do.",
             "Number 2 is lost: noise, a full mailbox, a broken cable. Nobody tells Alice. Nobody tells Otto either: he doesn’t know it was ever sent.",
             "Numbers 3 and 4 take different routes across town (Chapter 11), and 4 overtakes 3.",
             "And very occasionally, a datagram arrives twice, perhaps because some piece of equipment sent it again. The network makes no promises at all."]
    svg = fig(body, 720, bottom, "Datagrams can be lost, reordered or duplicated without either end being told",
              "Fire and forget: what the network is allowed to do to your datagrams.", steps)
    (OUT / "ch12-forget.svg").write_text(svg)


if __name__ == "__main__":
    mailboxes()
    layout()
    nesting()
    games()
    forget()
    print("wrote ch12 figures")
