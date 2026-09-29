#!/usr/bin/env python3
"""Generate chapter 13 figures.  python3 src/figs/ch13.py"""
import math
import random
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- stop and wait, with numbers

def stopwait():
    seq = Seq([("Alice", 170, "alice"), ("Otto", 550, None)], top=86, scale=30)
    seq.msg("Alice", "Otto", 0, 1, "#0", cls="blue", step="1")
    seq.msg("Otto", "Alice", 1.2, 2.2, "ACK 1", cls="green", step="1", sub="“I have everything before #1”")
    seq.msg("Alice", "Otto", 2.6, 3.6, "#1", cls="blue", step="2", lost=0.55)
    seq.timer("Alice", 2.6, 5.0, "no ACK… time’s up", step="2")
    seq.msg("Alice", "Otto", 5.2, 6.2, "#1 again", cls="blue", step="2")
    seq.msg("Otto", "Alice", 6.4, 7.4, "ACK 2", cls="green", step="2")
    seq.msg("Alice", "Otto", 7.8, 8.8, "#2", cls="blue", step="3")
    seq.msg("Otto", "Alice", 9.0, 10.0, "ACK 3", cls="green", step="3", lost=0.5)
    seq.timer("Alice", 7.8, 10.6, "time’s up", step="3")
    seq.msg("Alice", "Otto", 10.8, 11.8, "#2 again", cls="blue", step="4")
    seq.note("Otto", 12.0, "I already have #2! Keep one copy…", step="4", side="left")
    seq.msg("Otto", "Alice", 12.9, 13.9, "ACK 3", cls="green", step="4", sub="…but acknowledge it again")
    body, bottom = seq.render()
    body += '<use href="#computer" x="526" y="10" width="48" height="44"/>'
    steps = ["Every datagram carries a number, and every acknowledgment says which number Otto wants next.",
             "Datagram #1 is lost. Alice waits for its ACK, gives up, and sends it again. Exactly the plan from Chapter 3.",
             "This time the <em>acknowledgment</em> is lost. Alice can’t tell the difference, so she resends #2.",
             "In Chapter 3, this is where Bob printed a message twice. Now the number gives it away: Otto already has #2, so he throws the copy away and just repeats his ACK."]
    svg = fig(body, 720, bottom, "Stop-and-wait with sequence numbers, surviving a lost datagram and a lost acknowledgment",
              "Numbers turn “did you get that?” into something that always works.", steps)
    (OUT / "ch13-stopwait.svg").write_text(svg)


# ---------------------------------------------------------------- the pipe

def pipe():
    body = []

    def row(y, title, datas, acks, note):
        body.append(text(14, y - 30, title, "slab b"))
        body.append(f'<use href="#alice-head" x="10" y="{y - 22}" width="44" height="44"/>')
        body.append(f'<use href="#computer" x="668" y="{y - 20}" width="44" height="40"/>')
        body.append(f'<rect x="66" y="{y - 26}" width="592" height="52" rx="26" class="f-card" stroke="var(--line)" stroke-width="2"/>')
        body.append(f'<line x1="86" y1="{y}" x2="638" y2="{y}" class="line s-line dash" stroke-width="1.5"/>')
        for x in datas:
            body.append(f'<rect x="{x - 13}" y="{y - 22}" width="26" height="18" rx="3" class="f-blue"/>')
            body.append(f'<path d="M{x + 13},{y - 13} l8,0" class="line s-blue" stroke-width="2" marker-end="url(#ah-blue)"/>')
        for x in acks:
            body.append(f'<circle cx="{x}" cy="{y + 13}" r="7" class="f-green"/>')
            body.append(f'<path d="M{x - 8},{y + 13} l-8,0" class="line s-green" stroke-width="2" marker-end="url(#ah-green)"/>')
        body.append(text(360, y + 50, note, "mid hand"))
    row(70, "Stop-and-wait: one at a time", [250], [], "Nearly empty. At 40 ms a round trip, that’s 25 datagrams a second, however fast the wire.")
    row(200, "A window of 8: keep the pipe full", [150, 210, 270, 330, 390, 450, 510, 570], [180, 240, 300, 360, 420, 480, 540, 600],
        "8 datagrams on their way, acknowledgments streaming back: 8 times as much gets through.")
    svg = fig("".join(body), 720, 268, "Stop-and-wait leaves the path mostly empty; a window keeps it full of datagrams",
              "A network path is a pipe. Stop-and-wait uses a tiny part of it.")
    (OUT / "ch13-pipe.svg").write_text(svg)


# ---------------------------------------------------------------- the window

def window():
    body = []
    states = ["acked"] * 5 + ["sent"] * 5 + ["may"] * 3 + ["not"] * 7
    style = {"acked": ("t-green", "var(--green)", ""), "sent": ("t-yellow", "var(--yellow)", ""),
             "may": ("f-surface", "var(--ink)", ' stroke-dasharray="4 3"'), "not": ("f-card", "var(--line)", "")}
    W, X0, Y = 32, 40, 70
    for i, st in enumerate(states):
        cls, stroke, dash = style[st]
        x = X0 + i * W
        body.append(f'<rect x="{x}" y="{Y}" width="{W - 4}" height="36" rx="5" class="{cls}" stroke="{stroke}" stroke-width="2"{dash}/>')
        body.append(text(x + (W - 4) / 2, Y + 24, str(i), "mid mono sm b" + (" muted" if st == "not" else "")))
    wx0, wx1 = X0 + 5 * W - 4, X0 + 13 * W
    body.append(f'<rect x="{wx0}" y="{Y - 10}" width="{wx1 - wx0}" height="56" rx="10" class="f-none" stroke="var(--red)" stroke-width="3"/>')
    body.append(text((wx0 + wx1) / 2, Y - 18, "the window: 8 pieces", "mid hand b f-red"))
    body.append(f'<path d="M{wx1 - 24},{Y - 22} l44,0" class="line s-red" stroke-width="3" marker-end="url(#ah-red)"/>')
    body.append(text(wx1 + 30, Y - 17, "slides right as ACKs arrive", "hand f-red"))
    labels = [(0, 5, "acknowledged: done", "f-green"), (5, 10, "sent, waiting for ACK", "f-orange"),
              (10, 13, "may send now", "f-ink"), (13, 20, "must wait", "f-muted")]
    for a, b, lab, cls in labels:
        x1, x2 = X0 + a * W, X0 + b * W - 4
        body.append(f'<path d="M{x1},{Y + 46} l0,8 L{x2},{Y + 54} l0,-8" class="line" stroke-width="1.5"/>')
        body.append(text((x1 + x2) / 2, Y + 74, lab, f"mid xs b {cls}"))
    svg = fig("".join(body), 720, 160, "Sender's view of a sliding window over pieces 0 to 19",
              "Alice’s view of her report: at most 8 pieces may be unacknowledged at once.")
    (OUT / "ch13-window.svg").write_text(svg)


# ---------------------------------------------------------------- how long to wait?

def rtt():
    rng = random.Random(4)
    samples = []
    for i in range(60):
        base = 40 if i < 30 else 60                           # the route gets slower halfway through
        noise = rng.gauss(0, 3 if i < 30 else 7)
        spike = 25 if i in (12, 44) else 0
        samples.append(max(30, base + noise + spike))
    avg, wob, avgs, tos = samples[0], samples[0] / 2, [], []
    for r in samples:
        wob = 0.75 * wob + 0.25 * abs(r - avg)
        avg = 0.875 * avg + 0.125 * r
        avgs.append(avg)
        tos.append(avg + 4 * wob)
    X0, X1, Y0, Y1 = 70, 700, 20, 230

    def px(i):
        return X0 + i * (X1 - X0) / 59

    def py(ms):
        return Y1 - (ms - 20) / 100 * (Y1 - Y0)
    body = []
    for ms in (20, 40, 60, 80, 100, 120):
        body.append(f'<line x1="{X0}" y1="{py(ms):.1f}" x2="{X1}" y2="{py(ms):.1f}" class="grid"/>')
        body.append(text(X0 - 8, py(ms) + 4, f"{ms} ms", "end xs muted"))
    for i, r in enumerate(samples):
        body.append(f'<circle cx="{px(i):.1f}" cy="{py(r):.1f}" r="3.5" class="f-blue"/>')
    body.append('<path d="M' + " L".join(f"{px(i):.1f},{py(a):.1f}" for i, a in enumerate(avgs)) + '" class="line s-green" stroke-width="3"/>')
    body.append('<path d="M' + " L".join(f"{px(i):.1f},{py(t):.1f}" for i, t in enumerate(tos)) + '" class="line s-red" stroke-width="3" stroke-dasharray="8 5"/>')
    body.append(text(px(3), py(112), "timeout = average + 4 × wobble", "hand f-red halo"))
    body.append(text(px(20), py(avgs[20]) + 26, "running average", "hand f-green halo"))
    body.append(text(px(33), py(24), "the route gets slower here →", "xs muted halo"))
    body.append(text(385, 256, "each dot: how long one datagram took to be acknowledged", "mid xs"))
    svg = fig("".join(body), 720, 266, "Measured round-trip times with a smoothed average and a timeout that adapts to them",
              "Alice keeps a running average of the round trips, and how much they wobble, and waits a bit longer than that.")
    (OUT / "ch13-rtt.svg").write_text(svg)


# ---------------------------------------------------------------- congestion sawtooth

def sawtooth():
    X0, X1, Y0, Y1 = 70, 700, 30, 210
    body = [f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" class="line s-muted" stroke-width="1.5"/>',
            f'<line x1="{X0}" y1="{Y1}" x2="{X0}" y2="{Y0}" class="line s-muted" stroke-width="1.5"/>',
            text(X0 - 10, Y0 + 6, "window", "end xs muted"), text(X1, Y1 + 20, "time →", "end xs muted")]
    w, pts, losses = 1, [], []
    for t in range(64):
        pts.append((t, w))
        if w >= 20 or t in (40,):
            losses.append((t, w))
            w = max(1, w // 2)
        else:
            w = w * 2 if t < 4 else w + 1                  # start fast, then add one per round trip

    def px(t):
        return X0 + 8 + t * (X1 - X0 - 16) / 63

    def py(v):
        return Y1 - v * (Y1 - Y0) / 22
    body.append(f'<line x1="{X0}" y1="{py(20):.1f}" x2="{X1}" y2="{py(20):.1f}" class="line s-red" stroke-dasharray="6 5" stroke-width="1.5"/>')
    body.append(text(X1, py(20) - 6, "what the busiest link can carry", "end xs f-red"))
    body.append('<path d="M' + " L".join(f"{px(t):.1f},{py(v):.1f}" for t, v in pts) + '" class="line s-blue" stroke-width="3"/>')
    for t, v in losses:
        body.append(f'<circle cx="{px(t):.1f}" cy="{py(v):.1f}" r="6" class="f-red" stroke="var(--surface)" stroke-width="2"/>')
    (t1, v1), (t2, v2), (t3, v3) = losses[0], losses[1], losses[2]
    body.append(text(px(t1) + 10, py(v1 // 2) + 18, "loss! halve it", "hand f-red halo"))
    body.append(text((px(t2) + px(t3)) / 2 + 30, py(v2 // 2) + 40, "then add one each round trip", "mid hand f-blue halo"))
    body.append(text(px(3) + 10, py(3), "start fast", "hand muted halo"))
    svg = fig("".join(body), 720, 232, "A sender's window growing steadily and halving at each loss, forming a sawtooth",
              "Probing for the limit: grow slowly, back off sharply. Every sender on the internet does this.")
    (OUT / "ch13-sawtooth.svg").write_text(svg)


# ---------------------------------------------------------------- hello and goodbye

def handshake():
    seq = Seq([("Alice", 150, "alice"), ("Otto", 570, None)], top=86, scale=36)
    seq.msg("Alice", "Otto", 0, 1, "HELLO, I start at 1000", cls="blue", step="1", sub="SYN")
    seq.msg("Otto", "Alice", 1.3, 2.3, "HELLO, I start at 5000; next from you: 1001", cls="green", step="2", sub="SYN + ACK")
    seq.msg("Alice", "Otto", 2.6, 3.6, "next from you: 5001", cls="blue", step="3", sub="ACK")
    seq.note("Alice", 4.1, "connected! data flows both ways…", step="3", side="right")
    seq.msg("Alice", "Otto", 4.8, 5.8, "GOODBYE (I’m done sending)", cls="blue", step="4", sub="FIN")
    seq.msg("Otto", "Alice", 6.1, 7.1, "got it", cls="green", step="4", sub="ACK")
    seq.msg("Otto", "Alice", 7.4, 8.4, "GOODBYE from me too", cls="green", step="4", sub="FIN")
    seq.msg("Alice", "Otto", 8.7, 9.7, "got it", cls="blue", step="4", sub="ACK")
    body, bottom = seq.render()
    body += '<use href="#computer" x="546" y="10" width="48" height="44"/>'
    steps = ["Alice says hello, and picks a starting number for her datagrams. A random one, as we’ll see.",
             "Otto says hello back, picks his own starting number, and acknowledges Alice’s.",
             "Alice acknowledges Otto’s. Three messages, and now both sides know that the other is there, and what numbers to expect.",
             "Saying goodbye takes a message each way, because each side decides separately when it has finished sending."]
    svg = fig(body, 720, bottom, "A three-way handshake to start a connection and a goodbye in each direction to end it",
              "Hello, hello, and goodbye.", steps)
    (OUT / "ch13-handshake.svg").write_text(svg)


# ---------------------------------------------------------------- a stream of bytes

def stream():
    msg = "HELLO GRANDPA! LOVE, ALICE"
    writes = ["HELLO ", "GRANDPA! ", "LOVE, ALICE"]
    packets = ["HELLO GRAN", "DPA! LOVE,", " ALICE"]
    reads = ["HELL", "O GRANDPA! LO", "VE, ALICE"]
    C, X0 = 22, 124
    body = []

    def rowbits(y, groups, label, cls, stroke):
        body.append(text(X0 - 10, y + 22, label, "end sm b"))
        x = X0
        for g in groups:
            w = len(g) * C
            body.append(f'<rect x="{x}" y="{y}" width="{w - 4}" height="32" rx="6" class="{cls}" stroke="{stroke}" stroke-width="2"/>')
            for k, ch in enumerate(g):
                body.append(text(x + k * C + C / 2 - 2, y + 22, ch.replace(" ", "␣"), "mid mono sm b"))
            x += w
    for i in range(len(msg)):
        body.append(text(X0 + i * C + C / 2 - 2, 24, str(1000 + i)[-2:], "mid mono xs muted"))
    body.append(text(X0 - 10, 24, "byte #10…", "end xs muted"))
    rowbits(36, writes, "Alice writes", "t-blue", "var(--blue)")
    rowbits(100, packets, "on the wire", "t-yellow", "var(--yellow)")
    rowbits(164, reads, "Otto reads", "t-green", "var(--green)")
    body.append(text(360, 222, "Same bytes, same order, but the pieces don’t line up. It’s a stream, not a pile of messages.", "mid hand"))
    svg = fig("".join(body), 720, 236, "A byte stream: writes, packets and reads split the same bytes in different places",
              "Numbering bytes, not datagrams, turns the connection into one continuous stream.")
    (OUT / "ch13-stream.svg").write_text(svg)


if __name__ == "__main__":
    stopwait()
    pipe()
    window()
    rtt()
    sawtooth()
    handshake()
    stream()
    print("wrote ch13 figures")
