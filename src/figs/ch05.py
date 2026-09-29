#!/usr/bin/env python3
"""Generate chapter 5 figures.  python3 src/figs/ch05.py"""
from html import escape
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent

CONTROL = ("NUL SOH STX ETX EOT ENQ ACK BEL BS HT LF VT FF CR SO SI "
           "DLE DC1 DC2 DC3 DC4 NAK SYN ETB CAN EM SUB ESC FS GS RS US").split()
FAMOUS = {2: "start of text", 3: "end of text", 6: "acknowledge", 7: "ring the bell!", 10: "line feed",
          13: "carriage return", 21: "negative ack", 27: "escape"}


def hexfig():
    body = []
    body.append(text(40, 34, "the letter", "hand lg"))
    body.append(text(40, 78, "H", "slab b", style="font-size:48px"))
    body.append(f'<path d="M84,64 L128,64" class="line" marker-end="url(#ah-ink)"/>')
    body.append(text(106, 54, "72", "mid mono sm muted"))
    bits = "01001000"
    for i, b in enumerate(bits):
        x = 140 + i * 36 + (14 if i >= 4 else 0)
        cls = "t-green" if b == "1" else "t-red"
        body.append(f'<rect x="{x}" y="42" width="32" height="40" rx="5" class="{cls}" stroke="var(--line)"/>')
        body.append(text(x + 16, 69, b, "mid mono lg b"))
    body.append(f'<path d="M142,92 L142,100 L282,100 L282,92" class="line s-muted"/>')
    body.append(f'<path d="M300,92 L300,100 L440,100 L440,92" class="line s-muted"/>')
    body.append(text(212, 130, "0100 = 4", "mid mono b"))
    body.append(text(370, 130, "1000 = 8", "mid mono b"))
    body.append(f'<path d="M458,64 L500,64" class="line" marker-end="url(#ah-ink)"/>')
    body.append(f'<rect x="508" y="36" width="120" height="56" rx="10" class="t-yellow" stroke="var(--yellow)" stroke-width="2"/>')
    body.append(text(568, 74, "0x48", "mid mono xl b"))
    body.append(text(568, 112, "“hex 48”", "mid hand"))
    body.append(text(40, 170, "The 16 hex digits, and the 4 bits each one stands for:", "sm b"))
    for d in range(16):
        x = 40 + d * 40
        body.append(f'<rect x="{x}" y="182" width="36" height="52" rx="5" class="card"/>')
        body.append(text(x + 18, 204, format(d, "X"), "mid mono lg b"))
        body.append(text(x + 18, 224, format(d, "04b"), "mid mono xs muted"))
    svg = fig("".join(body), 720, 246, "A byte split into two 4-bit halves, each written as one hexadecimal digit",
              "Split a byte in half and each half is one hex digit. Two hex digits = one byte, always.")
    (OUT / "ch05-hex.svg").write_text(svg)


def ascii_chart():
    x0, y0, cw, ch = 44, 58, 83, 23
    body = [text(x0 + 4 * cw, 18, "the first hex digit →", "mid hand muted"),
            text(18, y0 + 8 * ch, "second digit ↓", "mid hand muted", transform=f"rotate(-90 18 {y0 + 8 * ch})")]
    for col in range(8):
        body.append(text(x0 + col * cw + cw / 2, y0 - 10, f"{col}_", "mid mono b"))
    for row in range(16):
        body.append(text(x0 - 8, y0 + row * ch + 16, f"_{row:X}", "end mono xs b"))
        for col in range(8):
            code = col * 16 + row
            if code < 32 or code == 127:
                label, cls = (CONTROL[code] if code < 32 else "DEL"), "t-purple"
            elif chr(code).isdigit():
                label, cls = chr(code), "t-green"
            elif chr(code).isupper():
                label, cls = chr(code), "t-blue"
            elif chr(code).islower():
                label, cls = chr(code), "t-teal"
            else:
                label, cls = ("SP" if code == 32 else chr(code)), "t-yellow"
            x, y = x0 + col * cw, y0 + row * ch
            stroke = 'stroke="var(--red)" stroke-width="2"' if code in FAMOUS else 'stroke="var(--surface)"'
            body.append(f'<rect x="{x}" y="{y}" width="{cw - 2}" height="{ch - 2}" rx="3" class="{cls}" {stroke}/>')
            size = "sm" if len(label) > 1 else ""
            body.append(text(x + 8, y + 16, escape(label), f"mono b {size}"))
            body.append(text(x + cw - 8, y + 15, f"{code:02X}", "end mono xs muted"))
    ly = y0 + 16 * ch + 26
    legend = [("t-purple", "control codes"), ("t-yellow", "space + punctuation"), ("t-green", "digits"),
              ("t-blue", "uppercase"), ("t-teal", "lowercase")]
    x = x0
    for cls, lab in legend:
        body.append(f'<rect x="{x}" y="{ly - 12}" width="16" height="16" rx="3" class="{cls}"/>')
        body.append(text(x + 22, ly + 1, lab, "sm"))
        x += 34 + len(lab) * 7.2
    body.append(f'<rect x="{x0}" y="{ly + 12}" width="16" height="16" rx="3" class="f-none" stroke="var(--red)" stroke-width="2"/>')
    body.append(text(x0 + 22, ly + 25, "control codes we’ve already met in spirit: STX/ETX (~S/~E), ACK/NAK (~A/~N), LF/CR (~L), ESC (~)", "sm"))
    svg = fig("".join(body), 720, ly + 40, "The ASCII table: 128 codes arranged by their two hex digits",
              "ASCII. “A” is 41, “a” is 61, “0” is 30. Every character your keyboard can type is somewhere in here.")
    (OUT / "ch05-ascii.svg").write_text(svg)


def token_row(tokens, x, y, h=34):
    out = []
    for label, cls in tokens:
        w = max(34, 9.5 * len(label) + 14)
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" class="{cls}" stroke="var(--line)"/>')
        out.append(text(x + w / 2, y + h / 2 + 5, escape(label), "mid mono sm b"))
        x += w + 3
    return "".join(out), x


def framing():
    body = [text(20, 30, "Marker style (Chapter 3): look at every byte for the end marker, escape any ~ inside", "sm b")]
    row, end = token_row([("~S", "t-red"), ("89", "t-yellow"), ("50", "t-yellow"), ("4E", "t-yellow"), ("~~", "t-purple"),
                          ("47", "t-yellow"), ("0D", "t-yellow"), ("…", "t-yellow"), ("~E", "t-red")], 40, 44)
    body.append(row)
    body.append(text(end + 8, 66, "“~” is 7E, so any 7E byte in the picture has to be doubled", "hand muted"))
    body.append(text(20, 130, "Length style: say how many bytes are coming, then simply count them", "sm b"))
    row, end = token_row([("Length: 944", "t-blue"), ("89", "t-yellow"), ("50", "t-yellow"), ("4E", "t-yellow"), ("7E", "t-yellow"),
                          ("47", "t-yellow"), ("0D", "t-yellow"), ("… 944 bytes in all …", "t-yellow")], 40, 144)
    body.append(row)
    body.append(f'<path d="M160,190 C300,214 500,214 {end - 6},190" class="line s-green" marker-end="url(#ah-green)"/>')
    body.append(text(400, 226, "no escaping, no scanning: after 944 bytes, the message is over", "mid hand f-green"))
    svg = fig("".join(body), 720, 240, "Two ways to find the end of a message: an end marker, or a length up front",
              "An end marker means inspecting every byte. A length up front means you can just count.")
    (OUT / "ch05-framing.svg").write_text(svg)


def endian():
    def egg(cx, cy, crack_top):
        y = cy - 34 if crack_top else cy + 30
        crack = f'M{cx - 14},{y} l7,{6 if crack_top else -6} l7,-{6 if crack_top else -6} l7,{6 if crack_top else -6} l7,-{6 if crack_top else -6}'
        return (f'<path d="M{cx},{cy - 44} C{cx + 30},{cy - 44} {cx + 34},{cy + 10} {cx + 30},{cy + 22} '
                f'C{cx + 24},{cy + 42} {cx - 24},{cy + 42} {cx - 30},{cy + 22} C{cx - 34},{cy + 10} {cx - 30},{cy - 44} {cx},{cy - 44} Z" '
                f'fill="#fff8e6" stroke="#8c6d3f" stroke-width="2"/>'
                f'<path d="{crack}" fill="none" stroke="#8c6d3f" stroke-width="2"/>')
    body = [text(360, 28, "The number 1000 is 0x03E8 in hex: too big for one byte, so it takes two.", "mid sm b")]
    rows = [(96, "Big-endian", "biggest part first, like we write 1,000", ["03", "E8"], True),
            (196, "Little-endian", "smallest part first", ["E8", "03"], False)]
    for y, name, sub, order, big in rows:
        body.append(egg(70, y, not big))
        body.append(text(130, y - 8, name, "slab b lg"))
        body.append(text(130, y + 16, sub, "sm muted"))
        for i, b in enumerate(order):
            x = 440 + i * 90
            body.append(f'<rect x="{x}" y="{y - 30}" width="80" height="54" rx="8" class="{"t-blue" if b == "03" else "t-yellow"}" stroke="var(--line)"/>')
            body.append(text(x + 40, y + 6, b, "mid mono xl b"))
            body.append(text(x + 40, y + 42, f"byte {i + 1}", "mid xs muted"))
        if big:
            body.append(text(640, y + 6, "← the internet’s order", "hand f-green"))
    svg = fig("".join(body), 720, 250, "Big-endian and little-endian byte orders for the number 1000",
              "Same number, two byte orders. Both sides must agree, and on the network, big-endian wins.")
    (OUT / "ch05-endian.svg").write_text(svg)


def rgb():
    colours = [((255, 0, 0), "red"), ((0, 200, 0), "green"), ((0, 0, 255), "blue"), ((255, 217, 102), "volcano sky"),
               ((32, 32, 32), "volcano"), ((0, 53, 84), "this book’s header")]
    body = []
    for i, ((r, g, b), name) in enumerate(colours):
        x = 20 + i * 116
        body.append(f'<rect x="{x}" y="16" width="104" height="64" rx="8" fill="#{r:02x}{g:02x}{b:02x}" stroke="var(--line)"/>')
        body.append(text(x + 52, 102, f"{r:02X} {g:02X} {b:02X}", "mid mono b"))
        body.append(text(x + 52, 122, name, "mid hand"))
    svg = fig("".join(body), 720, 136, "Six colours and the three bytes that describe each",
              "Every colour is three bytes: how much red, how much green, how much blue (00 = none, FF = all).")
    (OUT / "ch05-rgb.svg").write_text(svg)


if __name__ == "__main__":
    hexfig()
    ascii_chart()
    framing()
    endian()
    rgb()
    print("wrote ch05 figures")
