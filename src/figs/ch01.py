#!/usr/bin/env python3
"""Generate the repetitive chapter 1 figures.  python3 src/figs/ch01.py"""
from pathlib import Path

OUT = Path(__file__).parent
SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ␣.,?!~"


def halving(target="K"):
    idx = SYMBOLS.index(target)
    box, gap, top = 18, 0, 34
    center = 20 + 32 * box / 2
    rows, captions = [], []
    lo, hi = 0, 32
    bits = []
    for q in range(5):
        n = hi - lo
        x0 = center - n * box / 2
        y = top + q * 52
        mid = (lo + hi) // 2
        goes_right = idx >= mid
        bits.append("1" if goes_right else "0")
        parts = [f'<g data-show="{q + 1}">']
        for i in range(lo, hi):
            x = x0 + (i - lo) * box
            in_left = i < mid
            chosen = (not in_left) == goes_right
            fill = "t-red" if in_left else "t-green"
            op = "" if chosen else ' opacity="0.35"'
            hl = ' class="f-yellow"' if i == idx else f' class="{fill}"'
            parts.append(f'<rect x="{x + 1:.0f}" y="{y}" width="{box - 2}" height="26" rx="3"{hl}{op}/>')
            parts.append(f'<text x="{x + box / 2:.0f}" y="{y + 18}" class="mid mono sm b"{op}>{SYMBOLS[i]}</text>')
        split = x0 + (mid - lo) * box
        parts.append(f'<line x1="{split:.0f}" y1="{y - 5}" x2="{split:.0f}" y2="{y + 31}" class="line thick s-navy"/>')
        word = "right" if goes_right else "left"
        colour = "f-green" if goes_right else "f-red"
        parts.append(f'<text x="624" y="{y + 18}" class="hand lg">Q{q + 1}: {word} → '
                     f'<tspan class="{colour} b">{bits[-1]}</tspan></text>')
        if q < 4:
            nx0 = center - (n // 2) * box / 2
            src_x = (x0 + (mid - lo) * box / 2) if not goes_right else (split + (hi - mid) * box / 2)
            parts.append(f'<path d="M{src_x:.0f},{y + 29} L{center:.0f},{y + 47}" class="line thin s-muted" '
                         f'marker-end="url(#ah-muted)"/>')
        parts.append("</g>")
        rows.append("".join(parts))
        left_desc = f"{SYMBOLS[lo]}–{SYMBOLS[mid - 1]}" if mid - lo > 1 else SYMBOLS[lo]
        right_desc = f"{SYMBOLS[mid]}–{SYMBOLS[hi - 1]}" if hi - mid > 1 else SYMBOLS[mid]
        captions.append(
            f"<li><b>Question {q + 1}.</b> {n} symbols left. Cut them in half: {left_desc} on the left, "
            f"{right_desc} on the right. {target} is on the <b>{word}</b>, so the answer is "
            f"<b>{bits[-1]}</b>.</li>")
        if goes_right:
            lo = mid
        else:
            hi = mid
    y = top + 5 * 52 + 6
    code = "".join(bits)
    rows.append(f'<g data-show="6"><rect x="{center - 150:.0f}" y="{y - 6}" width="300" height="46" rx="10" class="f-navy"/>'
                f'<text x="{center:.0f}" y="{y + 24}" class="mid slab xl b on-night">{target}  =  {code}</text></g>')
    captions.append(f"<li>Only one symbol is left: <b>{target}</b>. Write the five answers down in order and you get "
                    f"<b>{code}</b>. Those five bits are all Bob needs to know Alice meant {target}.</li>")
    height = y + 52
    svg = (f'<figure class="fig stepper" data-widget="stepper">\n'
           f'<svg class="dia" viewBox="0 0 720 {height}" role="img" '
           f'aria-label="Finding the letter {target} by cutting the alphabet in half five times">'
           + "".join(rows) + "</svg>\n"
           f'<ol class="steps">' + "".join(captions) + "</ol>\n"
           f'<figcaption>Five yes/no answers are enough to pick one symbol out of 32.</figcaption>\n</figure>\n')
    (OUT / "ch01-halving.svg").write_text(svg)


def tree():
    """A 3-level binary tree: every path from the top is a 3-bit code."""
    parts = []
    levels = 3
    width, top, step = 720, 40, 62
    nodes = {(0, 0): (width / 2, top)}
    for level in range(1, levels + 1):
        count = 2 ** level
        for i in range(count):
            x = width * (i + 0.5) / count
            y = top + level * step
            nodes[(level, i)] = (x, y)
    for (level, i), (x, y) in nodes.items():
        if level == levels:
            continue
        for b in (0, 1):
            cx, cy = nodes[(level + 1, i * 2 + b)]
            colour = "s-green" if b else "s-red"
            parts.append(f'<line x1="{x:.0f}" y1="{y + 10}" x2="{cx:.0f}" y2="{cy - 12}" class="line {colour}" stroke-width="3"/>')
            lx, ly = (x + cx) / 2 + (10 if b else -10), (y + cy) / 2 + 2
            fill = "f-green" if b else "f-red"
            parts.append(f'<text x="{lx:.0f}" y="{ly:.0f}" class="mid mono b {fill}">{b}</text>')
    for (level, i), (x, y) in nodes.items():
        if level < levels:
            parts.append(f'<circle cx="{x:.0f}" cy="{y}" r="9" class="box"/>')
        else:
            code = format(i, "03b")
            parts.append(f'<rect x="{x - 34:.0f}" y="{y - 12}" width="68" height="44" rx="8" class="box"/>')
            parts.append(f'<text x="{x:.0f}" y="{y + 6}" class="mid mono lg b">{code}</text>')
            parts.append(f'<text x="{x:.0f}" y="{y + 25}" class="mid sm muted">= {i}</text>')
    parts.append(f'<text x="20" y="{top + 5}" class="hand lg">start here</text>')
    parts.append(f'<text x="20" y="{top + step + 4}" class="hand muted">1st bit</text>')
    parts.append(f'<text x="20" y="{top + 2 * step + 4}" class="hand muted">2nd bit</text>')
    height = top + levels * step + 44
    svg = (f'<figure class="fig"><svg class="dia" viewBox="0 0 720 {height}" role="img" '
           f'aria-label="A tree of left/right choices; three choices lead to eight different endings">'
           + "".join(parts) +
           '</svg><figcaption>Three two-way choices lead to 2 × 2 × 2 = 8 different endings. '
           'Every ending has its own 3-bit address.</figcaption></figure>\n')
    (OUT / "ch01-tree.svg").write_text(svg)


def flashes(text="HI BOB"):
    parts = []
    x = 18
    r = 8.5
    for ch in text:
        code = format(SYMBOLS.index("␣" if ch == " " else ch), "05b")
        gx = x
        for bit in code:
            colour = "f-green" if bit == "1" else "f-red"
            parts.append(f'<circle cx="{x + r:.1f}" cy="62" r="{r}" class="{colour}"/>')
            parts.append(f'<text x="{x + r:.1f}" y="92" class="mid mono sm">{bit}</text>')
            x += 2 * r + 4
        label = "␣" if ch == " " else ch
        mid = (gx + x - 4) / 2
        parts.append(f'<text x="{mid:.1f}" y="30" class="mid slab xl b">{label}</text>')
        parts.append(f'<path d="M{gx:.1f},40 L{gx:.1f},44 L{x - 4:.1f},44 L{x - 4:.1f},40" class="line thin s-muted"/>')
        x += 12
    width = x + 6
    svg = (f'<figure class="fig"><svg class="dia" viewBox="0 0 {width:.0f} 108" role="img" '
           f'aria-label="The message {text} as thirty green and red flashes">'
           + "".join(parts) +
           f'</svg><figcaption>“{text}” is 6 symbols × 5 bits = 30 flashes.</figcaption></figure>\n')
    (OUT / "ch01-hibob.svg").write_text(svg)


if __name__ == "__main__":
    halving()
    tree()
    flashes()
    print("wrote ch01 figures")
