#!/usr/bin/env python3
"""Generate chapter 10 figures.  python3 src/figs/ch10.py"""
import math
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- hogging

def hog():
    body = []

    def track(y, label):
        body.append(text(14, y - 12, label, "slab b"))
        body.append(f'<rect x="150" y="{y}" width="556" height="34" rx="4" class="f-card" stroke="var(--line)"/>')
        body.append(text(140, y + 22, "link to Carol", "end xs muted"))

    def bracket(x0, x1, y, label, cls):
        body.append(f'<path d="M{x0},{y} l0,8 L{x1},{y + 8} l0,-8" class="line s-{cls}" stroke-width="2"/>')
        body.append(text((x0 + x1) / 2 if x1 - x0 > 120 else x0, y + 28, label,
                         ("mid " if x1 - x0 > 120 else "") + f"hand f-{cls}"))

    def press(x, y):
        body.append(f'<line x1="{x}" y1="{y - 34}" x2="{x}" y2="{y - 4}" class="line s-blue" stroke-width="2" marker-end="url(#ah-blue)"/>')
        body.append(text(x + 6, y - 24, "Alice presses send", "hand f-blue"))

    # one giant message
    track(46, "One giant message")
    body.append('<rect x="152" y="48" width="512" height="30" rx="3" class="f-orange"/>')
    body.append(text(408, 68, "Bob’s video, all two hours of it", "mid sm b", fill="#fff"))
    body.append('<rect x="666" y="48" width="36" height="30" rx="3" class="f-blue"/>')
    body.append(text(684, 68, "HI", "mid xs b", fill="#fff"))
    press(190, 46)
    bracket(190, 666, 86, "…and waits for the entire video", "red")

    # packets
    y = 196
    track(y, "In packets")
    x = 152
    kinds = ["o", "o", "a", "o", "d", "o", "o", "o", "o", "d", "o", "o", "o", "o", "o", "o", "o", "o", "o", "o"]
    for k in kinds:
        cls, w = {"o": ("f-orange", 22), "a": ("f-blue", 22), "d": ("f-green", 22)}[k]
        body.append(f'<rect x="{x}" y="{y + 2}" width="{w}" height="30" rx="3" class="{cls}"/>')
        if k == "a":
            body.append(text(x + w / 2, y + 22, "HI", "mid xs b", fill="#fff"))
        x += w + 4
    body.append(text(x + 4, y + 22, "…", "sm b"))
    press(190, y)
    bracket(190, 230, y + 40, "…and waits a moment", "green")
    body.append(text(706, y + 68, "(green: Dave’s messages get a turn too)", "end xs muted"))
    svg = fig("".join(body), 720, 280, "A single huge message hogs the link; chopped into packets, others' messages slip in between",
              "Chopped into small pieces, one big message can share the link with everyone else’s.")
    (OUT / "ch10-hog.svg").write_text(svg)


# ---------------------------------------------------------------- chop and reassemble

PW, PG, PX = 80, 8, 96        # piece width, gap, first x


def piece(x, y, n, extra="", zap=False, rot=0):
    g = [f'<g transform="rotate({rot} {x + PW / 2} {y + 20})">' if rot else "<g>",
         f'<rect x="{x}" y="{y}" width="{PW}" height="40" rx="5" class="t-orange" stroke="var(--orange)" stroke-width="2"/>',
         f'<rect x="{x}" y="{y}" width="30" height="40" rx="5" class="t-blue" stroke="var(--blue)" stroke-width="2"/>',
         text(x + 15, y + 25, f"{n}/6", "mid mono xs b"),
         f'<rect x="{x + PW - 12}" y="{y}" width="12" height="40" rx="3" class="t-red" stroke="var(--red)" stroke-width="2"/>']
    for i in range(3):                                            # film-strip frames
        g.append(f'<rect x="{x + 34 + i * 11}" y="{y + 10}" width="8" height="20" rx="1" class="f-orange" opacity="0.55"/>')
    if zap:
        g.append(f'<path d="M{x + 30},{y - 14} l14,22 l-10,4 l16,28" class="line s-red" stroke-width="4" fill="none"/>')
    g.append("</g>")
    return f'<g{extra}>' + "".join(g) + "</g>"


def chop():
    body = [f'<use href="#bob-head" x="14" y="14" width="56" height="56"/>',
            f'<use href="#carol-head" x="14" y="222" width="56" height="56"/>',
            text(42, 84, "Bob", "mid sm b"), text(42, 292, "Carol", "mid sm b")]
    xs = [PX + i * (PW + PG) for i in range(6)]
    # row 1: Bob's video
    body.append(text(PX, 18, "Bob’s video, chopped into numbered pieces", "sm muted"))
    body.append(f'<g data-show="=1"><rect x="{PX}" y="30" width="{6 * PW + 5 * PG}" height="40" rx="5" class="t-orange" '
                f'stroke="var(--orange)" stroke-width="2"/>{text(PX + 262, 55, "✂ ✂ ✂ …", "mid lg f-orange")}</g>')
    for i, x in enumerate(xs):
        body.append(piece(x, 30, i + 1, ' data-show="2"'))
    # row 2: the wire
    body.append(f'<g data-show="2">{text(PX, 116, "On the wire, in whatever order they happen to arrive", "sm muted")}</g>')
    jumble = [3, 1, 5, 4, 2, 6]
    rots = [-4, 3, -2, 5, -3, 2]
    for slot, (n, r) in enumerate(zip(jumble, rots)):
        body.append(piece(xs[slot], 132, n, ' data-show="=2"', zap=(n == 4), rot=r))
    body.append(f'<g data-show="=2">{text(xs[3] + 60, 124, "noise!", "hand f-red b")}</g>')
    # row 3: Carol's shelf
    body.append(text(PX, 216, "Carol’s shelf, with a numbered slot for each piece", "sm muted"))
    for i, x in enumerate(xs):
        body.append(f'<rect x="{x}" y="228" width="{PW}" height="40" rx="5" class="f-none" stroke="var(--muted)" '
                    f'stroke-width="1.5" stroke-dasharray="5 4"/>')
        body.append(text(x + PW / 2, 286, f"slot {i + 1}", "mid xs muted"))
        if i != 3:
            body.append(piece(x, 228, i + 1, ' data-show="3"'))
    body.append(piece(xs[3], 228, 4, ' data-show="4"'))
    # the bin
    bx = PX + 6 * (PW + PG) + 10
    body.append(f'<g data-show="=3">'
                f'<path d="M{bx},{232} l8,40 l40,0 l8,-40 z" class="t-red" stroke="var(--red)" stroke-width="2"/>'
                f'<text x="{bx + 28}" y="{262}" class="mid lg">🗑️</text>'
                f'{text(bx + 28, 222, "piece 4 fails", "mid xs b f-red")}{text(bx + 28, 292, "its check", "mid xs b f-red")}</g>')
    body.append(f'<g data-show="4"><rect x="{PX}" y="128" width="170" height="50" rx="10" class="card"/>'
                f'{text(PX + 85, 150, "“Bob, please resend", "mid hand")}{text(PX + 85, 170, "piece 4!”", "mid hand")}'
                f'<path d="M{PX + 20},180 L62,222" class="line s-muted" stroke-width="2"/></g>')
    body.append(piece(xs[3], 132, 4, ' data-show="=4"'))
    body.append(f'<g data-show="=4"><path d="M{xs[3] + PW / 2},{176} L{xs[3] + PW / 2},{222}" class="line s-green" stroke-width="2.5" '
                f'marker-end="url(#ah-green)"/>{text(xs[3] + PW + 10, 158, "second try: OK ✓", "hand f-green")}</g>')
    body.append(f'<g data-show="4">{text(PX + 262, 318, "All six pieces, in order: Carol has the whole video ✓", "mid hand lg f-green")}</g>')
    steps = ["Bob has one enormous message: the video of the school play.",
             "He chops it into pieces, and gives each one a little label: its number, and how many pieces there are in all. "
             "Each piece also gets its own check at the end (red). They set off down the wire, and noise hits piece 4.",
             "Carol checks each piece as it arrives. The good ones go on her shelf in their numbered slots, no matter what order they "
             "arrived in. Piece 4 fails its check, so she throws it away.",
             "She asks Bob for just the missing piece. He sends piece 4 again, and the video is complete. One damaged bit cost one small "
             "piece, not the whole two hours."]
    svg = fig("".join(body), 720, 330, "A video is chopped into six numbered pieces, one is damaged in transit and resent",
              "Chopping, checking, and filing by number.", steps)
    (OUT / "ch10-chop.svg").write_text(svg)


# ---------------------------------------------------------------- a piece inside a frame

def layout():
    body = []
    top = [("to", 70, "t-blue"), ("from", 70, "t-blue"), ("type", 70, "t-green"), ("data", 390, "t-yellow"), ("check", 86, "t-red")]
    x = 14
    for name, w, cls in top:
        body.append(f'<rect x="{x}" y="36" width="{w}" height="46" rx="6" class="{cls}" stroke="var(--line)"/>')
        body.append(text(x + w / 2, 64, name, "mid slab b"))
        if name == "data":
            dx0, dx1 = x, x + w
        if name == "check":
            body.append(text(x + w / 2, 28, "CRC-32", "mid mono xs b f-red"))
        x += w + 2
    body.append(text(14, 22, "A frame (Chapter 8)", "sm muted"))
    body.append(f'<path d="M{dx0},84 L14,140 M{dx1},84 L706,140" class="line s-muted dash" stroke-width="1.5"/>')
    inner = [("piece #", "which piece", "4", 110, "t-blue"), ("of", "how many", "4", 110, "t-blue"),
             ("length", "data bytes", "4", 110, "t-blue"), ("data", "a slice of the video", "up to 1,488", 358, "t-yellow")]
    x = 14
    for name, sub, size, w, cls in inner:
        body.append(f'<rect x="{x}" y="142" width="{w}" height="58" rx="6" class="{cls}" stroke="var(--line)"/>')
        body.append(text(x + w / 2, 166, name, "mid slab b"))
        body.append(text(x + w / 2, 188, sub, "mid xs"))
        body.append(text(x + w / 2, 218, f"{size} bytes", "mid xs muted"))
        x += w + 2
    body.append(f'<path d="M14,228 L14,236 L344,236 L344,228" class="line s-blue" stroke-width="2"/>')
    body.append(text(180, 256, "the packet’s own little header", "mid hand f-blue"))
    svg = fig("".join(body), 720, 268, "A packet rides in the data part of a frame: piece number, total, length, then a slice of data",
              "Each piece (from now on, a <strong>packet</strong>) rides inside an ordinary frame. The frame’s check at the very end covers every bit of it.")
    (OUT / "ch10-layout.svg").write_text(svg)


# ---------------------------------------------------------------- parity

def parity():
    rows = [("As sent", "01001000", set(), "two 1s, plus parity 0: even ✓", "f-ink"),
            ("One bit flipped", "01011000", {3}, "three 1s: odd! Something broke. Caught ✓", "f-green"),
            ("Two bits flipped", "01011010", {3, 6}, "four 1s: even. Looks fine… Missed ✗", "f-red")]
    body = [text(214, 22, "“H” = 72", "mid xs muted"), text(340, 22, "parity", "mid xs muted")]
    C = 30
    for r, (label, bits, flipped, verdict, vcls) in enumerate(rows):
        y = 34 + r * 62
        body.append(text(14, y + 21, label, "hand"))
        for i, b in enumerate(bits):
            x = 154 + i * C
            cls = "t-red" if i in flipped else "f-card"
            body.append(f'<rect x="{x}" y="{y}" width="{C - 3}" height="{C}" rx="4" class="{cls}" stroke="var(--line)"/>')
            body.append(text(x + (C - 3) / 2, y + 21, b, "mid mono b" + (" f-red" if i in flipped else "")))
        body.append(f'<rect x="{154 + 8 * C + 12}" y="{y}" width="{C - 3}" height="{C}" rx="4" class="t-teal" stroke="var(--teal)" stroke-width="2"/>')
        body.append(text(154 + 8 * C + 12 + (C - 3) / 2, y + 21, "0", "mid mono b"))
        body.append(text(440, y + 21, verdict, f"sm b {vcls}"))
    svg = fig("".join(body), 720, 216, "A parity bit catches one flipped bit but misses two",
              "A parity bit makes the number of 1s even. One flip makes it odd, and gets caught. Two flips cancel out.")
    (OUT / "ch10-parity.svg").write_text(svg)


# ---------------------------------------------------------------- CRC long division

def crc_division():
    msg, div = "11010110", "1011"
    work = [int(c) for c in msg + "000"]
    steps_rows = []                                   # (position, bits after XOR)
    for i in range(len(msg)):
        if work[i]:
            for j, d in enumerate(div):
                work[i + j] ^= int(d)
            steps_rows.append((i, list(work)))
    remainder = "".join(map(str, work[-3:]))
    C, X0, Y0, RH = 26, 60, 44, 21
    body = [text(X0, 26, "message", "xs muted"), text(X0 + 8 * C, 26, "+ 3 zeros", "xs muted")]

    def row(y, bits, start=0, cls="", dim_before=None, show=None):
        out = []
        for k, b in enumerate(bits):
            x = X0 + (start + k) * C
            c = cls
            if dim_before is not None and start + k < dim_before:
                c = "f-muted"
            out.append(text(x + C / 2, y, str(b), f"mid mono b {c}"))
        g = "".join(out)
        return f'<g data-show="{show}">{g}</g>' if show else g

    body.append(row(Y0 + 12, work and [int(c) for c in msg + "000"], cls=""))
    # show zeros muted
    y = Y0 + 12
    # group division steps into stepper steps
    groups = [steps_rows[:1], steps_rows[1:3], steps_rows[3:]]
    step_of = {}
    for gi, grp in enumerate(groups):
        for s in grp:
            step_of[s[0]] = gi + 2
    for n, (pos, after) in enumerate(steps_rows):
        st = step_of[pos]
        y += RH
        body.append(row(y, [int(c) for c in div], start=pos, cls="f-orange", show=str(st)))
        body.append(f'<g data-show="{st}"><text x="{X0 - 12}" y="{y}" class="end mono b f-orange">⊕</text>'
                    f'<line x1="{X0 + pos * C}" y1="{y + 6}" x2="{X0 + (pos + 4) * C}" y2="{y + 6}" class="line s-ink" stroke-width="1.5"/></g>')
        y += RH
        nxt = steps_rows[n + 1][0] if n + 1 < len(steps_rows) else len(msg)
        body.append(row(y, after, dim_before=nxt, show=str(st)))
    last_y = y
    rx = X0 + len(msg) * C
    body.append(f'<g data-show="5"><rect x="{rx - 3}" y="{last_y - 19}" width="{3 * C + 6}" height="27" rx="6" class="f-none" '
                f'stroke="var(--red)" stroke-width="3"/>'
                f'{text(rx + 3 * C + 14, last_y, "remainder = " + remainder, "hand lg f-red")}</g>')
    body.append(f'<g data-show="5">{text(X0, last_y + 44, "Send:", "sm b")}'
                f'{text(X0 + 50, last_y + 44, msg, "mono b")}{text(X0 + 50 + 8 * 10.5, last_y + 44, remainder, "mono b f-red")}'
                f'{text(X0 + 50 + 11 * 10.5 + 16, last_y + 44, "(the message, then its 3-bit check)", "sm muted")}</g>')
    # explainer on the right
    ex = 430
    notes = [(2, ["Line the divisor up under", "the first 1 and XOR:", "1⊕1 = 0, 1⊕0 = 1, 0⊕0 = 0.", "No carrying, no borrowing."]),
             (3, ["Skip ahead to the next 1", "and do it again. The 1s at", "the front always cancel out,", "so the number keeps shrinking."]),
             (4, ["Keep going until the divisor", "would hang off the end."])]
    for st, lines in notes:
        body.append(f'<g data-show="={st}"><rect x="{ex - 14}" y="40" width="290" height="{len(lines) * 24 + 20}" rx="10" class="card"/>'
                    + "".join(text(ex, 64 + i * 24, l, "hand") for i, l in enumerate(lines)) + "</g>")
    body.append(f'<g data-show="=1"><rect x="{ex - 14}" y="40" width="290" height="108" rx="10" class="card"/>'
                + text(ex, 64, "Message: 11010110", "hand") + text(ex, 88, "Agreed divisor: 1011", "hand")
                + text(ex, 112, "Tack on 3 zeros (one fewer", "hand") + text(ex, 132, "than the divisor’s length).", "hand") + "</g>")
    steps = ["Alice and Bob agree on a divisor in advance, here <code>1011</code>. Alice writes her message and adds three 0s to the end.",
             "Long division, school style, except that “subtract” means XOR, bit by bit, with no borrowing. Put the divisor under the first 1.",
             "Bring the divisor under the next leading 1, and XOR again. Whatever was in front has become zeros (greyed out).",
             "Carry on until you run out of room.",
             f"What’s left over is the <strong>remainder</strong>, <code>{remainder}</code>. Alice sends it right after the message. "
             "Bob divides what he receives by the same divisor. If he doesn’t get the same remainder, something changed on the way."]
    height = last_y + 64
    svg = fig("".join(body), 720, height, "Binary long division using XOR produces a 3-bit remainder, the CRC",
              "A tiny CRC with a 4-bit divisor. CRC-32 is exactly the same process with a 33-bit divisor.", steps)
    (OUT / "ch10-crc.svg").write_text(svg)
    return remainder


# ---------------------------------------------------------------- how big should a packet be?

def sizes():
    BER, HDR = 1e-6, 16
    X0, X1, Y0, Y1 = 90, 690, 40, 250          # plot box: Y0 top (cost 2.0), Y1 bottom (cost 1.0)
    lo, hi = math.log10(16), math.log10(256000)

    def px(s):
        return X0 + (math.log10(s) - lo) / (hi - lo) * (X1 - X0)

    def py(cost):
        return Y1 - (min(cost, 2.05) - 1) / 1.0 * (Y1 - Y0)

    def header(s):
        return 1 + HDR / s

    def resend(s):
        return 1 / (1 - BER) ** ((s + HDR) * 8)

    def total(s):
        return header(s) * resend(s)
    body = []
    for c in (1.0, 1.25, 1.5, 1.75, 2.0):
        y = py(c)
        body.append(f'<line x1="{X0}" y1="{y:.1f}" x2="{X1}" y2="{y:.1f}" class="grid"/>')
        body.append(text(X0 - 8, y + 4, f"{c:.2f}×", "end xs muted"))
    for s in (16, 100, 1000, 10000, 100000):
        x = px(s)
        body.append(f'<line x1="{x:.1f}" y1="{Y1}" x2="{x:.1f}" y2="{Y1 + 5}" class="line s-muted"/>')
        body.append(text(x, Y1 + 20, f"{s:,}", "mid xs muted"))
    body.append(text((X0 + X1) / 2, Y1 + 42, "bytes of data per packet (each step is 10× bigger)", "mid sm"))
    body.append(text(20, (Y0 + Y1) / 2 - 14, "bits sent,", "sm", transform=f"rotate(-90 32 {(Y0 + Y1) / 2})"))
    body.append(text(36, (Y0 + Y1) / 2 + 6, "per bit of video", "xs muted", transform=f"rotate(-90 32 {(Y0 + Y1) / 2})"))
    samples = [10 ** (lo + (hi - lo) * i / 300) for i in range(301)]
    for fn, cls, width, dash in ((total, "s-ink", 7, None), (header, "s-blue", 3, "7 5"), (resend, "s-orange", 3, "7 5")):
        pts = " L".join(f"{px(s):.1f},{py(fn(s)):.1f}" for s in samples)
        extra = f' stroke-dasharray="{dash}"' if dash else ' opacity="0.35"'
        body.append(f'<path d="M{pts}" class="line {cls}" fill="none" stroke-width="{width}"{extra} '
                    f'clip-path="url(#sizes-clip)"/>')
    body.insert(0, f'<defs><clipPath id="sizes-clip"><rect x="{X0}" y="{Y0 - 6}" width="{X1 - X0}" height="{Y1 - Y0 + 8}"/></clipPath></defs>')
    best = min(samples, key=total)
    bx, by = px(best), py(total(best))
    body.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="7" class="f-green" stroke="var(--surface)" stroke-width="2"/>')
    body.append(text(bx, by - 40, f"best: about {round(best, -2):,.0f} bytes", "mid hand b f-green halo"))
    body.append(text(bx, by - 20, f"(costs {total(best):.2f}×)", "mid xs f-green halo"))
    body.append(text(px(40), py(header(40)) + 30, "headers eat", "hand f-blue halo"))
    body.append(text(px(40), py(header(40)) + 50, "tiny packets", "hand f-blue halo"))
    body.append(text(px(60000) + 16, py(resend(60000)) + 44, "resends eat", "hand f-orange halo"))
    body.append(text(px(60000) + 16, py(resend(60000)) + 64, "huge packets", "hand f-orange halo"))
    body.append(text((X0 + X1) / 2, Y0 + 4, "a line that flips one bit in a million", "mid xs muted halo"))
    body.append(f'<line x1="{X1 - 150}" y1="{Y0 + 30}" x2="{X1 - 120}" y2="{Y0 + 30}" class="line s-ink" stroke-width="7" opacity="0.35"/>')
    body.append(text(X1 - 112, Y0 + 34, "total cost", "xs"))
    svg = fig("".join(body), 720, 306, "Total cost of sending a file versus packet size; the minimum is around 1,400 bytes",
              "Small packets waste bits on headers, big packets waste bits on resends. The best size sits in between.")
    (OUT / "ch10-sizes.svg").write_text(svg)
    return best


# ---------------------------------------------------------------- circuits vs packets

def circuits():
    body = []

    def panel(ox, title, reserved):
        a, e1, e2, b = (ox + 50, 80), (ox + 136, 80), (ox + 230, 150), (ox + 300, 150)
        side1, side2 = (ox + 100, 196), (ox + 190, 206)
        body.append(text(ox + 175, 22, title, "mid slab b"))
        path = f"M{a[0]},{a[1]} L{e1[0]},{e1[1]} L{e2[0]},{e2[1]} L{b[0]},{b[1]}"
        body.append(f'<path d="{path}" class="wire" stroke-width="5" fill="none"/>')
        body.append(f'<path d="M{e1[0]},{e1[1]} L{side1[0]},{side1[1]} M{e2[0]},{e2[1]} L{side2[0]},{side2[1]}" class="wire" stroke-width="3"/>')
        if reserved:
            body.append(f'<path d="{path}" class="line s-purple" stroke-width="9" fill="none" opacity="0.45"/>')
        for (x, y), label, dy in ((e1, "exchange" if reserved else "switch", -24), (e2, "exchange" if reserved else "switch", 32)):
            body.append(f'<rect x="{x - 26}" y="{y - 16}" width="52" height="32" rx="6" class="card"/>')
            body.append(text(x + (14 if dy > 0 else 0), y + dy, label, "mid xs muted halo"))
        body.append(f'<use href="#alice-head" x="{a[0] - 44}" y="{a[1] - 22}" width="44" height="44"/>')
        body.append(f'<use href="#bob-head" x="{b[0]}" y="{b[1] - 22}" width="44" height="44"/>')
        body.append(f'<use href="#carol-head" x="{side1[0] - 22}" y="{side1[1] - 4}" width="40" height="40"/>')
        body.append(f'<use href="#dave-head" x="{side2[0] - 16}" y="{side2[1] - 4}" width="40" height="40"/>')
        return a, e1, e2, b, side1, side2

    def blob(x, y, cls, w=16):
        body.append(f'<rect x="{x - w / 2}" y="{y - 7}" width="{w}" height="14" rx="3" class="{cls}"/>')

    # circuit switching: one reserved path, mostly silent; Carol and Dave get a busy signal
    a, e1, e2, b, s1, s2 = panel(0, "Circuit switching (the phone network)", True)
    blob(78, 80, "f-purple", 10)
    body.append(text(94, 64, "“hello?”", "mid hand xs f-purple halo"))
    body.append(text(268, 136, "(silence)", "mid hand xs muted halo"))
    body.append(text(s1[0] - 30, s1[1] + 20, "busy!", "end hand f-red b"))
    body.append(text(s2[0] + 30, s2[1] + 18, "busy!", "hand f-red b"))
    body.append(text(175, 262, "The whole path is reserved for the call, even", "mid sm"))
    body.append(text(175, 282, "during silences. Everyone else has to wait.", "mid sm"))
    body.append('<line x1="358" y1="30" x2="358" y2="286" class="line s-line"/>')
    # packet switching: everyone's packets share the links
    a, e1, e2, b, s1, s2 = panel(366, "Packet switching", False)
    for x, y, cls in ((440, 80, "f-purple"), (462, 80, "f-purple"), (546, 102, "f-purple"), (566, 116, "f-orange"),
                      (586, 130, "f-green"), (626, 150, "f-orange"), (646, 150, "f-purple")):
        blob(x, y, cls)
    blob(483, 158, "f-orange")
    blob(578, 184, "f-green")
    body.append(text(541, 262, "Everyone’s packets share every link,", "mid sm"))
    body.append(text(541, 282, "and nobody reserves anything.", "mid sm"))
    svg = fig("".join(body), 720, 296, "Circuit switching reserves a whole path per call; packet switching shares links between everyone's packets",
              "Two ways to share a network. Purple is Alice’s call (or packets); orange is Carol’s and green is Dave’s.")
    (OUT / "ch10-circuits.svg").write_text(svg)


if __name__ == "__main__":
    hog()
    chop()
    layout()
    parity()
    r = crc_division()
    b = sizes()
    circuits()
    print(f"wrote ch10 figures (crc remainder {r}, best packet size {b:.0f})")
