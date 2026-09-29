#!/usr/bin/env python3
"""Generate chapter 2 waveform figures.  python3 src/figs/ch02.py"""
import random
from pathlib import Path

from svgkit import curve_path, fig, level_axes, text, wave_path

OUT = Path(__file__).parent


def bit_labels(bits, x0, bw, y):
    return "".join(text(x0 + (i + 0.5) * bw, y, b, "mid mono b " + ("f-green" if b == "1" else "f-red"))
                   for i, b in enumerate(bits))


def bit_grid(n, x0, bw, y1, y2):
    return "".join(f'<line x1="{x0 + i * bw:g}" y1="{y1}" x2="{x0 + i * bw:g}" y2="{y2}" class="grid" stroke-dasharray="3 4"/>'
                   for i in range(n + 1))


def rz_nrz():
    bits, x0, bw, amp = "11010", 110, 110, 30
    body = [bit_grid(5, x0, bw, 34, 240), bit_labels(bits, x0, bw, 24)]
    for y_mid, title, halves in (
        (95, "Flashlight style: pulse, then rest  (“return to zero”)", True),
        (205, "Metronome style: hold the level for one whole tick  (“non-return to zero”)", False),
    ):
        levels = []
        for b in bits:
            lv = 1 if b == "1" else -1
            levels += [lv, 0] if halves else [lv, lv]
        body.append(text(x0, y_mid - amp - 16, title, "sm b"))
        body.append(level_axes(x0, x0 + 5 * bw, y_mid, amp))
        body.append(f'<path d="{wave_path(levels, x0, y_mid, bw / 2, amp)}" class="line thick s-navy"/>')
    body.append(text(x0 + 2.5 * bw, 266, "the two 1s at the start blur together in the bottom row: timing has to tell them apart",
                     "mid hand muted"))
    svg = fig("".join(body), 720, 278, "The bits 11010 drawn two ways: as pulses with rests, and as held levels",
              "Two ways to draw 1 1 0 1 0 on a wire.")
    (OUT / "ch02-rz-nrz.svg").write_text(svg)


def sampling():
    bits, x0, bw, y_mid, amp = "0011101000", 90, 58, 112, 40
    body = [bit_grid(10, x0, bw, 44, 176)]
    for i, (lab, lo) in enumerate((("H", 0), ("I", 5))):
        xa, xb = x0 + lo * bw + 4, x0 + (lo + 5) * bw - 4
        body.append(f'<path d="M{xa},34 L{xa},28 L{xb},28 L{xb},34" class="line thin s-muted"/>')
        body.append(text((xa + xb) / 2, 22, lab, "mid slab lg b"))
    body.append(level_axes(x0, x0 + 10 * bw, y_mid, amp))
    levels = [1 if b == "1" else -1 for b in bits]
    body.append(f'<path d="{wave_path(levels, x0, y_mid, bw, amp)}" class="line thick s-navy"/>')
    for i, b in enumerate(bits):
        x = x0 + (i + 0.5) * bw
        y = y_mid - (amp if b == "1" else -amp)
        body.append(f'<line x1="{x:g}" y1="52" x2="{x:g}" y2="192" class="line thin s-teal dot-line"/>')
        body.append(f'<circle cx="{x:g}" cy="{y}" r="5" class="f-teal" stroke="var(--surface)" stroke-width="2"/>')
        body.append(f'<path d="M{x - 6:g},200 L{x + 6:g},200 L{x:g},192 Z" class="f-teal"/>')
        body.append(text(x, 222, b, "mid mono b " + ("f-green" if b == "1" else "f-red")))
    body.append(text(x0 - 8, 204, "Bob’s", "end xs muted"))
    body.append(text(x0 - 8, 216, "clock", "end xs muted"))
    svg = fig("".join(body), 720, 236, "Bob samples the voltage in the middle of every bit-time",
              "Bob’s clock ticks once per bit, halfway through each one. He reads 0011101000, which is “HI”.")
    (OUT / "ch02-sampling.svg").write_text(svg)


def drift():
    bits = "001110100000001"
    n, x0, bw, y_mid, amp, slow = len(bits), 60, 40, 100, 35, 1.07
    body = [bit_grid(n, x0, bw, 50, 150)]
    body.append(level_axes(x0, x0 + n * bw, y_mid, amp, ("", "", "")))
    levels = [1 if b == "1" else -1 for b in bits]
    body.append(f'<path d="{wave_path(levels, x0, y_mid, bw, amp)}" class="line thick s-navy"/>')
    body.append(text(x0, 34, "Alice’s bit slots (her clock)", "sm b"))
    for i in range(n):
        body.append(text(x0 + (i + 0.5) * bw, 50, str(i + 1), "mid xs muted"))
    for i in range(n):
        pos = (i + 0.5) * slow
        x = x0 + pos * bw
        if pos >= n:
            break
        slot = int(pos)
        ok = slot == i
        cls = "f-teal" if ok else "f-red"
        body.append(f'<line x1="{x:.1f}" y1="60" x2="{x:.1f}" y2="170" class="line thin {"s-teal" if ok else "s-red"} dot-line"/>')
        body.append(f'<path d="M{x - 6:.1f},178 L{x + 6:.1f},178 L{x:.1f},170 Z" class="{cls}"/>')
        body.append(text(x, 194, str(i + 1), f"mid xs b {cls}"))
    body.append(text(x0, 222, "Bob’s ticks (his clock runs 7% slow): each tick lands a little later than the last",
                     "hand muted"))
    svg = fig("".join(body), 720, 236,
              "Bob's slow clock samples drift later and later until they land in the wrong bit slot",
              "By tick 8, Bob’s sample has slipped into Alice’s bit 9, and from then on every sample is one slot behind.")
    (OUT / "ch02-drift.svg").write_text(svg)


def letters():
    x0, bw, y_mid, amp = 40, 40, 112, 35
    slots = [("idle", 0)]
    for code in ("00111", "01000"):
        slots.append(("start", 1))
        slots += [("data", 1 if b == "1" else -1) for b in code]
        slots.append(("rest", 0))
    slots.append(("idle", 0))
    body = []
    x = x0
    groups = []
    for kind, lv in slots:
        if groups and groups[-1][0] == kind and kind == "data":
            groups[-1][2] += 1
        else:
            groups.append([kind, x, 1])
        x += bw
    tint = {"start": "t-yellow", "data": "t-teal", "rest": "t-purple", "idle": None}
    names = {"start": "start", "rest": "rest"}
    data_labels = iter(["H = 00111", "I = 01000"])
    for kind, gx, count in groups:
        if tint[kind]:
            body.append(f'<rect x="{gx}" y="56" width="{count * bw}" height="112" class="{tint[kind]}"/>')
        label = next(data_labels) if kind == "data" else names.get(kind)
        if label:
            body.append(text(gx + count * bw / 2, 48, label, "mid sm b"))
        if kind == "start":
            body.append(f'<path d="M{gx},172 L{gx},186" class="line s-red" marker-end="url(#ah-red)" transform="rotate(180 {gx} 179)"/>')
            body.append(text(gx, 204, "Bob restarts his clock", "mid hand f-red"))
    body.append(level_axes(x0, x0 + len(slots) * bw, y_mid, amp, ("", "", "")))
    levels = [lv for _, lv in slots]
    body.append(f'<path d="{wave_path(levels, x0, y_mid, bw, amp)}" class="line thick s-navy"/>')
    svg = fig("".join(body), 720, 216,
              "The letters H and I each sent with a start pulse before and a rest after",
              "Every letter brings its own “get ready” pulse, so Bob’s clock only has to stay accurate for six bits.")
    (OUT / "ch02-letters.svg").write_text(svg)


def manchester():
    bits, x0, bw, amp = "10110", 110, 110, 30
    body = [bit_grid(5, x0, bw, 34, 250), bit_labels(bits, x0, bw, 24)]
    rows = ((95, "Plain (metronome style): 1 1 in a row is one long flat stretch", False),
            (210, "Manchester: every bit flips in the middle.  up = 1, down = 0", True))
    for y_mid, title, man in rows:
        levels = []
        for b in bits:
            if man:
                levels += [-1, 1] if b == "1" else [1, -1]
            else:
                lv = 1 if b == "1" else -1
                levels += [lv, lv]
        body.append(text(x0, y_mid - amp - 16, title, "sm b"))
        body.append(level_axes(x0, x0 + 5 * bw, y_mid, amp))
        body.append(f'<path d="{wave_path(levels, x0, y_mid, bw / 2, amp)}" class="line thick s-navy"/>')
        if man:
            for i, b in enumerate(bits):
                x = x0 + (i + 0.5) * bw + 12
                if b == "1":
                    body.append(f'<path d="M{x},{y_mid + 18} L{x},{y_mid - 18}" class="line s-green" marker-end="url(#ah-green)"/>')
                else:
                    body.append(f'<path d="M{x},{y_mid - 18} L{x},{y_mid + 18}" class="line s-red" marker-end="url(#ah-red)"/>')
    svg = fig("".join(body), 720, 262, "The bits 10110 in plain encoding and in Manchester encoding",
              "Manchester encoding hides a clock tick inside every bit.")
    (OUT / "ch02-manchester.svg").write_text(svg)


def noise():
    rng = random.Random(4)
    bits, x0, bw, y_mid, amp = "0011101000", 76, 54, 118, 10  # amp = px per volt
    body = []
    top, bot = y_mid - 7 * amp, y_mid + 7 * amp
    body.append(f'<rect x="{x0}" y="{top}" width="{10 * bw}" height="{5 * amp}" class="t-green"/>')
    body.append(f'<rect x="{x0}" y="{y_mid - 2 * amp}" width="{10 * bw}" height="{4 * amp}" class="t-yellow"/>')
    body.append(f'<rect x="{x0}" y="{y_mid + 2 * amp}" width="{10 * bw}" height="{5 * amp}" class="t-red"/>')
    body.append(text(x0 + 10 * bw + 8, top + 30, "reads as 1", "hand f-green"))
    body.append(text(x0 + 10 * bw + 8, y_mid + 5, "can’t tell", "hand"))
    body.append(text(x0 + 10 * bw + 8, bot - 20, "reads as 0", "hand f-red"))
    for v, lab in ((5, "+5 V"), (2, "+2 V"), (0, "0 V"), (-2, "−2 V"), (-5, "−5 V")):
        y = y_mid - v * amp
        body.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + 10 * bw}" y2="{y}" class="grid" stroke-dasharray="{"0" if abs(v) == 2 else "4 4"}"/>')
        body.append(text(x0 - 8, y + 4, lab, "end xs muted"))
    dx = 2
    values = []
    steps = int(bw / dx)
    for i, b in enumerate(bits):
        base = 5 if b == "1" else -5
        for k in range(steps):
            v = base + rng.gauss(0, 0.7)
            if i == 6 and 9 <= k <= 20:
                v -= 4.2 * (1 - abs(k - 14.5) / 6)  # a burst of interference
            values.append(v)
    body.append(f'<path d="{curve_path(values, x0, y_mid, dx, amp)}" class="line s-navy" stroke-width="1.6"/>')
    for i, b in enumerate(bits):
        k = int((i + 0.5) * steps)
        v = values[k]
        x = x0 + k * dx
        ok = (v > 2 and b == "1") or (v < -2 and b == "0")
        cls = "f-teal" if ok else "f-red"
        body.append(f'<circle cx="{x}" cy="{y_mid - v * amp:.1f}" r="6" class="{cls}" stroke="var(--surface)" stroke-width="2"/>')
        body.append(text(x, bot + 22, "?" if not ok else b, f"mid mono b {cls}"))
    body.append(text(x0 - 8, bot + 22, "Bob:", "end xs muted"))
    svg = fig("".join(body), 720, bot + 34, "A noisy signal with thresholds; one sample falls into the can't-tell zone",
              "Noise wiggles the voltage. Bob only trusts readings well away from zero, and a burst of interference just cost him a bit.")
    (OUT / "ch02-noise.svg").write_text(svg)


def smear():
    rng = random.Random(11)
    x0, width = 70, 620
    body = []
    rows = ((100, 124, "10110", "Slow bits: the edges get rounded, but every bit still reaches its level"),
            (238, 24.8, "".join(rng.choice("01") for _ in range(25)), "Fast bits through the same wire: they smear into each other"))
    tau = 16.0
    for y_mid, bw, bits, title in rows:
        amp = 32
        body.append(text(x0, y_mid - amp - 18, title, "sm b"))
        body.append(level_axes(x0, x0 + width, y_mid, amp, ("+5", "0", "−5")))
        levels = [1 if b == "1" else -1 for b in bits]
        body.append(f'<path d="{wave_path(levels, x0, y_mid, bw, amp)}" class="line s-muted" stroke-width="1.5" stroke-dasharray="5 4"/>')
        v, out = -1.0, []
        dx = 1.0
        n = int(len(bits) * bw / dx)
        for s in range(n + 1):
            idx = min(int(s * dx / bw), len(bits) - 1)
            target = levels[idx]
            v += (target - v) * (dx / tau)
            out.append(v)
        body.append(f'<path d="{curve_path(out, x0, y_mid, dx, amp)}" class="line thick s-red"/>')
    body.append(f'<path d="M{x0 + 330},300 l24,0" class="line s-muted" stroke-dasharray="5 4"/>')
    body.append(text(x0 + 360, 304, "what Alice sends", "xs muted"))
    body.append(f'<path d="M{x0 + 470},300 l24,0" class="line thick s-red"/>')
    body.append(text(x0 + 500, 304, "what Bob sees", "xs muted"))
    svg = fig("".join(body), 720, 316, "The same wire rounds off slow bits slightly but smears fast bits together",
              "A long wire can’t change its voltage instantly. Push bits too fast and they blur together.")
    (OUT / "ch02-smear.svg").write_text(svg)


if __name__ == "__main__":
    rz_nrz()
    sampling()
    drift()
    letters()
    manchester()
    noise()
    smear()
    print("wrote ch02 figures")
