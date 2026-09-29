#!/usr/bin/env python3
"""Generate chapter 28 figures.  python3 src/figs/ch28.py"""
import json
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- flow control: the receive window

def window():
    b = []
    slots = 12

    def buf(y, filled, label, step):
        out = [f'<g data-show="{step}">']
        out.append(text(470, y - 8, label, "mid xs b"))
        for i in range(slots):
            cls = "t-green" if i < filled else "f-surface"
            stroke = "var(--green)" if i < filled else "var(--line)"
            out.append(f'<rect x="{320 + i * 26}" y="{y}" width="22" height="26" rx="3" class="{cls}" stroke="{stroke}"/>')
        free = slots - filled
        out.append(f'<path d="M{320 + filled * 26},{y + 34} l0,6 l{free * 26 - 4},0 l0,-6" class="line s-purple" stroke-width="2"/>')
        out.append(text(320 + filled * 26 + (free * 26 - 4) / 2, y + 54, f"window: {free * 4} KB" if free else "window: 0!", "mid xs b", style="fill:var(--purple)"))
        out.append("</g>")
        return "".join(out)
    b.append('<use href="#computer" x="30" y="60" width="70" height="62"/>' + text(65, 140, "sender", "mid xs b"))
    b.append('<use href="#computer" x="620" y="60" width="70" height="62"/>' + text(655, 140, "receiver", "mid xs b"))
    b.append(buf(70, 3, "the receiver’s buffer: 48 KB, 12 KB waiting for the program", "=1"))
    b.append(buf(70, 9, "the program is busy: 36 KB waiting", "=2"))
    b.append(buf(70, 12, "full: the program still hasn’t read anything", "=3"))
    b.append(buf(70, 5, "the program reads 28 KB: room again", "=4"))
    b.append('<g data-show="=1"><path d="M110,90 L300,90" class="line s-blue" stroke-width="3" marker-end="url(#ah-blue)"/>' + text(200, 82, "data", "mid xs b halo") + "</g>")
    b.append('<g data-show="=2"><path d="M300,110 L110,110" class="line s-purple" stroke-width="2.5" marker-end="url(#ah-purple)"/>' + text(200, 126, "ACK, window 12 KB", "mid xs b halo", style="fill:var(--purple)") + "</g>")
    b.append('<g data-show="=3"><path d="M300,110 L110,110" class="line s-purple" stroke-width="2.5" marker-end="url(#ah-purple)"/>' + text(200, 126, "ACK, window 0: stop!", "mid xs b halo", style="fill:var(--purple)")
             + text(65, 170, "…waits, and now and then", "mid xs") + text(65, 184, "asks “room yet?”", "mid xs") + "</g>")
    b.append('<g data-show="=4"><path d="M300,110 L110,110" class="line s-purple" stroke-width="2.5" marker-end="url(#ah-purple)"/>' + text(200, 126, "window update: 28 KB", "mid xs b halo", style="fill:var(--purple)") + "</g>")
    steps = ["TCP delivers data into a buffer in the receiver’s kernel, where it waits until the program reads it (like UDP’s, in Chapter 26). Every acknowledgement carries the <strong>window</strong>: how much free space is left.",
             "If the program is slow to read, the buffer fills, and the window it advertises shrinks. The sender may never have more unacknowledged data out than the window allows.",
             "When the buffer is full, the receiver advertises a <strong>zero window</strong>, and the sender stops. It sends a tiny probe now and then, in case the window update that reopens it gets lost.",
             "When the program reads, space opens up, and the receiver sends a <strong>window update</strong>. Nothing is ever lost for lack of room: this is <strong>flow control</strong>, and it’s exactly what UDP’s flood in Chapter 26 didn’t have."]
    svg = fig("".join(b), 720, 196, "TCP flow control: the receiver's buffer filling up, its advertised window shrinking to zero, and a window update",
              "Flow control: the receiver says how much it can take.", steps)
    (OUT / "ch28-window.svg").write_text(svg)


# ---------------------------------------------------------------- bits in flight

def bdp():
    b = []
    b.append('<use href="#computer" x="14" y="44" width="60" height="54"/>')
    b.append('<use href="#server" x="656" y="40" width="40" height="62"/>')
    b.append('<rect x="84" y="56" width="560" height="30" rx="15" class="f-surface" stroke="var(--line)" stroke-width="2"/>')
    for i in range(36):
        x = 94 + i * 15.2
        b.append(f'<rect x="{x:g}" y="{62 if i % 2 else 64}" width="11" height="{18 if i % 2 else 14}" rx="2" class="t-blue" stroke="var(--blue)"/>')
    b.append('<path d="M640,96 C600,120 140,120 90,98" class="line s-green dash" stroke-width="2" marker-end="url(#ah-green)"/>')
    b.append(text(364, 132, "…and the acknowledgements take the same time to come back", "mid xs f-green b"))
    b.append(text(364, 40, "Bob’s upload: 135 Mbit/s × 12 ms round trip = 202,500 bytes in flight: about 146 full segments", "mid sm b"))
    rows = [("a home Wi-Fi link", "300 Mbit/s", "5 ms", "188 KB"), ("Bob’s upload to Cloudflare", "135 Mbit/s", "12 ms", "203 KB"),
            ("London to New York", "1 Gbit/s", "70 ms", "8.8 MB"), ("a data centre link", "100 Gbit/s", "0.1 ms", "1.3 MB")]
    y = 160
    b.append(text(40, y, "link", "xs b") + text(300, y, "speed", "xs b") + text(420, y, "round trip", "xs b") + text(560, y, "bytes in flight to fill it", "xs b"))
    for i, (a, s, r, f) in enumerate(rows):
        yy = y + 20 + i * 18
        b.append(text(40, yy, a, "xs") + text(300, yy, s, "mono xs") + text(420, yy, r, "mono xs") + text(560, yy, f, "mono xs b"))
    svg = fig("".join(b), 720, 244, "A network path drawn as a pipe full of packets: the bandwidth-delay product",
              "The <strong>bandwidth-delay product</strong>: how much data has to be on its way at once to keep a path busy. TCP’s window must be at least this big.")
    (OUT / "ch28-bdp.svg").write_text(svg)


# ---------------------------------------------------------------- the real congestion window

def cwnd_real():
    data = json.loads((OUT / "ch28-cwnd.json").read_text())
    samples = data["samples"]
    x0, x1, y0, h = 60, 700, 30, 190
    tmax = samples[-1][0]
    cmax = 7200                                               # KB
    b = []

    def X(t):
        return x0 + (x1 - x0) * t / tmax

    def Y(kb):
        return y0 + h - h * min(kb, cmax) / cmax
    for kb in (0, 1000, 2000, 3000, 4000, 5000, 6000, 7000):
        b.append(f'<line x1="{x0}" y1="{Y(kb):g}" x2="{x1}" y2="{Y(kb):g}" class="grid"/>')
        b.append(text(x0 - 6, Y(kb) + 4, f"{kb // 1000} MB" if kb else "0", "end xs muted"))
    for s in range(int(tmax) + 1):
        b.append(text(X(s), y0 + h + 16, f"{s} s", "mid xs muted"))
    pts = " ".join(f"{X(t):.1f},{Y(i['cwnd'] / 1024):.1f}" for t, i in samples)
    b.append(f'<polyline points="{pts}" class="line s-blue" stroke-width="2.2" fill="none"/>')
    # zoomed inset of the sawtooth
    zx0, zy0, zw, zh = 330, 50, 360, 110
    b.append(f'<rect x="{zx0}" y="{zy0}" width="{zw}" height="{zh}" rx="6" class="f-surface" stroke="var(--line)"/>')
    zs = [(t, i) for t, i in samples if t >= 1.1]
    zt0, zt1, zmax = 1.1, tmax, 300
    zpts = " ".join(f"{zx0 + zw * (t - zt0) / (zt1 - zt0):.1f},{zy0 + zh - 8 - (zh - 16) * min(i['cwnd'] / 1024, zmax) / zmax:.1f}" for t, i in zs)
    b.append(f'<polyline points="{zpts}" class="line s-blue" stroke-width="2" fill="none"/>')
    bdp_kb = 198                                              # 135 Mbit/s × 12 ms, in the lab’s KB (1024 bytes)
    yb = zy0 + zh - 8 - (zh - 16) * bdp_kb / zmax
    b.append(f'<line x1="{zx0}" y1="{yb:g}" x2="{zx0 + zw}" y2="{yb:g}" class="line s-green dash" stroke-width="1.5"/>')
    b.append(text(zx0 + zw - 6, yb - 4, "the path’s bandwidth × delay: 198 KB", "end xs b f-green"))
    b.append(text(zx0 + 8, zy0 + 16, "zoomed in, after 1.1 s (0 to 300 KB)", "xs b muted"))
    for t, kb, label in ((1.45, 157, "×0.71"), (3.13, 196, "×0.71"), (4.01, 172, "×0.70")):
        xx = zx0 + zw * (t - zt0) / (zt1 - zt0)
        yy = zy0 + zh - 8 - (zh - 16) * kb / zmax
        b.append(text(xx + 4, yy + 14, label, "xs b f-red"))
    b.append(f'<line x1="{X(1.1):g}" y1="{Y(250):g}" x2="{zx0}" y2="{zy0 + zh}" class="line s-muted" stroke-width="1" stroke-dasharray="2 3"/>')
    b.append(text(X(0.47), Y(6300), "← slow start: doubling", "xs b", style="fill:var(--blue)"))
    b.append(text(X(0.62), Y(2600) - 6, "losses", "xs b f-red"))
    b.append(text(X(0.55), Y(2600) + 8, "and timeouts", "xs b f-red"))
    b.append(text(x0, 20, "Congestion window of a real 5-second upload from Bob’s MacBook (labs/ch28/cwnd.py)", "sm b"))
    svg = fig("".join(b), 720, y0 + h + 28, "Chart of the congestion window during a real upload: slow start up to 7 MB, a collapse after losses, then a CUBIC sawtooth around the bandwidth-delay product",
              "Real congestion control. The window shoots up in slow start, far past what the path needs, until the queues overflow. Then, after a rough second of losses and timeouts, it settles into a sawtooth around the bandwidth-delay product, cut to 70% at every loss: CUBIC’s signature.")
    (OUT / "ch28-cwnd.svg").write_text(svg)


# ---------------------------------------------------------------- why AIMD is fair

def aimd():
    x0, y0, s = 60, 290, 240
    b = [f'<line x1="{x0}" y1="{y0}" x2="{x0 + s + 20}" y2="{y0}" class="line" stroke-width="1.5" marker-end="url(#ah-ink)"/>',
         f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 - s - 20}" class="line" stroke-width="1.5" marker-end="url(#ah-ink)"/>',
         text(x0 + s + 10, y0 + 18, "Alice’s speed", "end xs b"), text(x0 - 8, y0 - s - 24, "Bob’s speed", "xs b"),
         f'<line x1="{x0}" y1="{y0 - s}" x2="{x0 + s}" y2="{y0}" class="line s-orange" stroke-width="2"/>',
         text(x0 + s * 0.72, y0 - s * 0.28 - 10, "the link is full", "xs b f-orange", transform=f"rotate(-45 {x0 + s * 0.72} {y0 - s * 0.28 - 10})"),
         f'<line x1="{x0}" y1="{y0}" x2="{x0 + s}" y2="{y0 - s}" class="line s-green dash" stroke-width="2"/>',
         text(x0 + s * 0.86, y0 - s * 0.95, "fair: equal shares", "xs b f-green")]
    # trajectory: start at (0.1, 0.5) of s
    a, c = 0.1, 0.55
    pts = [(a, c)]
    for _ in range(8):
        while a + c < 1:
            a += 0.04
            c += 0.04
        pts.append((a, c))
        a, c = a / 2, c / 2
        pts.append((a, c))
    step_of = lambda i: "1" if i < 3 else "2" if i < 7 else "3"
    for i in range(len(pts) - 1):
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        cls = "s-blue" if i % 2 == 0 else "s-red"
        b.append(f'<g data-show="{step_of(i)}"><line x1="{x0 + xa * s:.1f}" y1="{y0 - ya * s:.1f}" x2="{x0 + xb * s:.1f}" y2="{y0 - yb * s:.1f}" class="line {cls}" stroke-width="2" marker-end="url(#ah-{"blue" if i % 2 == 0 else "red"})"/></g>')
    b.append(f'<circle cx="{x0 + 0.1 * s:.1f}" cy="{y0 - 0.55 * s:.1f}" r="5" class="f-ink"/>')
    b.append(text(x0 + 0.1 * s + 8, y0 - 0.55 * s - 6, "start: Bob has most", "xs"))
    b.append(text(430, 80, "blue: both add the same amount", "xs b", style="fill:var(--blue)"))
    b.append(text(430, 98, "(additive increase: moves at 45°)", "xs", style="fill:var(--blue)"))
    b.append(text(430, 130, "red: both halve (multiplicative", "xs b f-red"))
    b.append(text(430, 148, "decrease: moves towards 0)", "xs f-red"))
    b.append(text(430, 190, "Each round trip of the cycle, the gap", "xs"))
    b.append(text(430, 208, "between them halves, but the total", "xs"))
    b.append(text(430, 226, "keeps coming back to “full”.", "xs"))
    steps = ["Two connections share one link. Bob’s starts with most of it. Both add one segment per round trip (blue), so both speeds grow by the same amount, until together they overflow the link, and a packet is lost.",
             "Both halve their windows (red). Halving takes more from the bigger one: Bob loses more than Alice. Then both grow again by equal amounts.",
             "Round after round, the point zig-zags towards the green line, where they’re equal, while staying near the orange one, where the link is full. Nobody coordinates anything. That’s why TCP uses additive increase and multiplicative decrease, and not any other combination: it’s the one that converges to fair."]
    svg = fig("".join(b), 720, 308, "The Chiu-Jain diagram: two flows' speeds under additive increase and multiplicative decrease, zig-zagging towards the fair, full point",
              "Why AIMD shares fairly (after Chiu and Jain, 1989).", steps)
    (OUT / "ch28-aimd.svg").write_text(svg)


# ---------------------------------------------------------------- bufferbloat, measured

def bloat():
    res = [("idle", 10.3, 14.3), ("downloading", 26.9, 73.5), ("uploading", 10.8, 96.5)]
    b = [text(14, 22, "Pings from Bob’s MacBook to 1.1.1.1, every 100 ms (labs/ch28/bloat.py)", "sm b")]
    x0, sc = 150, 5.2
    for i, (name, med, worst) in enumerate(res):
        y = 44 + i * 44
        b.append(text(x0 - 10, y + 17, name, "end xs b"))
        b.append(f'<rect x="{x0}" y="{y}" width="{worst * sc:g}" height="24" rx="3" class="t-red" stroke="var(--red)"/>')
        b.append(f'<rect x="{x0}" y="{y}" width="{med * sc:g}" height="24" rx="3" class="t-blue" stroke="var(--blue)"/>')
        b.append(text(x0 + med * sc + 4 if worst * sc - med * sc > 60 else x0 + worst * sc + 6, y + 16, f"median {med} ms", "xs b", style="fill:var(--blue)"))
        b.append(text(x0 + worst * sc + 6, y + 16 if worst * sc - med * sc <= 60 else y + 16, "" if worst * sc - med * sc <= 60 else f"worst {worst} ms", "xs b f-red"))
    b.append(text(x0, 186, "The download ran at 116 Mbit/s, the upload at 130. Busy, the queue in front of the slowest link", "xs"))
    b.append(text(x0, 202, "fills up, and every other packet, like a game’s, waits behind it.", "xs"))
    svg = fig("".join(b), 720, 214, "Bar chart of real ping times while idle, downloading and uploading: medians of 10, 27 and 11 ms, worst cases of 14, 74 and 97 ms",
              "Bufferbloat on Bob’s network, measured. Blue: the typical ping. Red: the worst one.")
    (OUT / "ch28-bloat.svg").write_text(svg)


# ---------------------------------------------------------------- ECN

def ecn():
    b = []
    pos = {"a": 80, "r": 360, "b": 640}
    b.append('<use href="#computer" x="50" y="40" width="60" height="54"/>' + text(80, 110, "sender", "mid xs b"))
    b.append('<use href="#router" x="320" y="48" width="80" height="50"/>' + text(360, 110, "a busy router", "mid xs b"))
    b.append('<use href="#computer" x="610" y="40" width="60" height="54"/>' + text(640, 110, "receiver", "mid xs b"))
    for i in range(6):
        b.append(f'<rect x="{316 + i * 14}" y="120" width="10" height="16" rx="2" class="t-blue" stroke="var(--blue)"/>')
    b.append(text(360, 152, "queue getting long", "mid xs muted"))

    def pk(x, y, label, cls, step):
        return (f'<g data-show="{step}"><rect x="{x - 56}" y="{y}" width="112" height="24" rx="5" class="{cls}" stroke="var(--line)"/>'
                + text(x, y + 16, label, "mid mono xs b") + "</g>")
    b.append(pk(220, 170, "IP: ECT (“I can do ECN”)", "t-green", "=1"))
    b.append(pk(500, 170, "IP: CE (“congestion!”)", "t-orange", "=2"))
    b.append(pk(360, 206, "TCP ACK: ECE (“echo: congestion”)", "t-orange", "=3"))
    b.append(pk(220, 206, "TCP: CWR (“I’ve slowed down”)", "t-green", "=4"))
    b.append('<g data-show="=1"><path d="M110,60 L318,60" class="line s-green" stroke-width="2.5" marker-end="url(#ah-green)"/></g>')
    b.append('<g data-show="=2"><path d="M402,60 L608,60" class="line s-orange" stroke-width="2.5" marker-end="url(#ah-orange)"/></g>')
    b.append('<g data-show="=3"><path d="M608,86 L112,86" class="line s-orange" stroke-width="2.5" marker-end="url(#ah-orange)"/></g>')
    b.append('<g data-show="=4"><path d="M110,60 L318,60" class="line s-green" stroke-width="2.5" marker-end="url(#ah-green)"/></g>')
    steps = ["Both ends agreed, in the handshake, to use <strong>explicit congestion notification</strong>. The sender marks its packets “ECN-capable” with two spare bits in the IP header.",
             "A router whose queue is getting long doesn’t drop the packet. It changes the mark to “congestion experienced”, and forwards it.",
             "The receiver tells the sender, by setting the ECE flag in its acknowledgements.",
             "The sender slows down exactly as if a packet had been lost, and sets CWR to say so. The difference: nothing was lost, nothing had to be sent again, and nobody waited for a timeout."]
    svg = fig("".join(b), 720, 240, "Explicit congestion notification: a router marks a packet instead of dropping it, the receiver echoes the mark, and the sender slows down",
              "ECN: congestion signalled with a mark instead of a loss.", steps)
    (OUT / "ch28-ecn.svg").write_text(svg)


if __name__ == "__main__":
    window()
    bdp()
    cwnd_real()
    aimd()
    bloat()
    ecn()
    print("wrote ch28 figures")
