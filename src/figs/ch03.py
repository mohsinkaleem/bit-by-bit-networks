#!/usr/bin/env python3
"""Generate chapter 3 figures.  python3 src/figs/ch03.py"""
import random
from pathlib import Path

from svgkit import Seq, curve_path, fig, level_axes, text, wave_path

OUT = Path(__file__).parent


def car(x, y, colour, facing=1):
    body = (f'<rect x="{x - 17}" y="{y - 9}" width="34" height="16" rx="5" class="{colour}"/>'
            f'<rect x="{x - 8 + facing * 3}" y="{y - 15}" width="16" height="8" rx="3" class="{colour}" opacity="0.8"/>'
            f'<circle cx="{x - 9}" cy="{y + 8}" r="4" fill="#222"/><circle cx="{x + 9}" cy="{y + 8}" r="4" fill="#222"/>')
    return body


def light(x, y, on):
    return (f'<rect x="{x - 9}" y="{y - 26}" width="18" height="40" rx="4" fill="#333"/>'
            f'<circle cx="{x}" cy="{y - 16}" r="6" fill="{"#555" if on else "#e0566f"}"/>'
            f'<circle cx="{x}" cy="{y + 2}" r="6" fill="{"#45b872" if on else "#555"}"/>'
            f'<rect x="{x - 2}" y="{y + 14}" width="4" height="16" fill="#333"/>')


def roads():
    body = []
    rows = [(84, "Simplex: a one-way street. Only Alice can send."),
            (198, "Half duplex: a one-lane bridge. Both can send, but they take turns."),
            (312, "Full duplex: a two-lane road. Both send at the same time.")]
    for i, (y, title) in enumerate(rows):
        body.append(text(92, y - 44, title, "sm b"))
        body.append(f'<use href="#alice-head" x="24" y="{y - 26}" width="52" height="52"/>')
        body.append(f'<use href="#bob-head" x="644" y="{y - 26}" width="52" height="52"/>')
        if i < 2:
            body.append(f'<rect x="90" y="{y - 17}" width="540" height="34" rx="4" fill="#5b6168"/>')
        else:
            body.append(f'<rect x="90" y="{y - 24}" width="540" height="48" rx="4" fill="#5b6168"/>')
            body.append(f'<line x1="96" y1="{y}" x2="624" y2="{y}" stroke="#f2d16b" stroke-width="2.5" stroke-dasharray="14 10"/>')
        colours = ["f-green", "f-red", "f-green", "f-green", "f-red"]
        if i == 0:
            for k, c in enumerate(colours):
                body.append(car(170 + k * 95, y, c))
            body.append(f'<path d="M580,{y} l22,0" stroke="#fff" stroke-width="3" marker-end="url(#ah-ink)"/>')
        elif i == 1:
            body.append(light(108, y - 6, True))
            body.append(light(612, y - 6, False))
            for k, c in enumerate(colours[:3]):
                body.append(car(200 + k * 110, y, c))
            body.append(text(510, y + 5, "Bob waits…", "hand", fill="#fff"))
        else:
            for k, c in enumerate(colours):
                body.append(car(160 + k * 100, y - 11, c))
            for k, c in enumerate(["f-red", "f-green", "f-green", "f-red"]):
                body.append(car(210 + k * 110, y + 12, c, -1))
    svg = fig("".join(body), 720, 350, "Simplex, half duplex and full duplex drawn as roads",
              "Three ways to share a road, and three ways to share a wire.")
    (OUT / "ch03-roads.svg").write_text(svg)


def collision():
    rng = random.Random(3)
    x0, bw, amp = 110, 90, 26
    a_bits, b_bits = "101100", "011010"
    body = []
    rows = [(60, "What Alice sends", a_bits, "s-red"), (150, "What Bob sends, at the same moment", b_bits, "s-blue")]
    for y, title, bits, cls in rows:
        body.append(text(x0, y - amp - 10, title, "sm b"))
        body.append(level_axes(x0, x0 + 6 * bw, y, amp))
        body.append(f'<path d="{wave_path([1 if b == "1" else -1 for b in bits], x0, y, bw, amp)}" class="line thick {cls}"/>')
    y = 250
    body.append(text(x0, y - amp - 10, "What’s actually on the wire: a tug of war", "sm b"))
    body.append(level_axes(x0, x0 + 6 * bw, y, amp))
    values = []
    for i in range(6 * bw // 2):
        k = int(i * 2 / bw)
        a = 1 if a_bits[k] == "1" else -1
        b = 1 if b_bits[k] == "1" else -1
        values.append((a + b) / 2 * 0.8 + rng.gauss(0, 0.18))
    body.append(f'<path d="{curve_path(values, x0, y, 2, amp)}" class="line s-purple" stroke-width="2.4"/>')
    for k in range(6):
        a, b = a_bits[k], b_bits[k]
        x = x0 + (k + 0.5) * bw
        body.append(text(x, y + amp + 24, "?" if a != b else a, "mid mono b " + ("f-red" if a != b else "muted")))
    body.append(text(x0 - 8, y + amp + 24, "Bob reads:", "end xs muted"))
    svg = fig("".join(body), 720, 312, "When Alice and Bob drive the same wire at once the result is garbage",
              "Where they disagree, the voltages cancel out. Where they happen to agree, it looks fine, which is worse.")
    (OUT / "ch03-collision.svg").write_text(svg)


def boxes_row(tokens, x, y, h=30):
    """tokens: list of (label, kind). kind: data | ctrl | esc | word | bad."""
    out = []
    widths = []
    for label, kind in tokens:
        w = max(22, 11 * len(label) + 10) if kind != "data" else 22
        cls = {"data": "t-yellow", "ctrl": "t-red", "esc": "t-purple", "word": "t-yellow", "bad": "t-red"}[kind]
        stroke = {"ctrl": "var(--red)", "esc": "var(--purple)", "bad": "var(--red)"}.get(kind, "var(--line)")
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        out.append(text(x + w / 2, y + h / 2 + 5, label, "mid mono sm b"))
        widths.append((x, w))
        x += w + 3
    return "".join(out), widths


def over():
    body = []
    body.append(text(20, 30, "1. Using the word OVER to end a message", "sm b"))
    words = [("START", "word"), ("GAME", "word"), ("OVER", "bad"), ("LOL", "word"), ("OVER", "word")]
    row, w = boxes_row(words, 40, 44)
    body.append(row)
    x_end = w[2][0] + w[2][1]
    body.append(f'<path d="M{w[1][0]},{84} L{w[1][0]},{90} L{x_end},{90} L{x_end},{84}" class="line s-red"/>')
    body.append(text((w[1][0] + x_end) / 2, 110, "Bob: “the message is GAME”", "mid hand f-red"))
    body.append(text(w[3][0] + 60, 110, "…then “LOL” is gibberish", "hand f-red"))
    body.append(text(20, 156, "2. Using control codes that can’t appear in the text", "sm b"))
    toks = [("~S", "ctrl")] + [(c if c != " " else "␣", "data") for c in "GAME OVER LOL"] + [("~E", "ctrl")]
    row, w = boxes_row(toks, 40, 170)
    body.append(row)
    body.append(f'<path d="M{w[1][0]},210 L{w[1][0]},216 L{w[-2][0] + w[-2][1]},216 L{w[-2][0] + w[-2][1]},210" class="line s-green"/>')
    body.append(text((w[1][0] + w[-2][0] + w[-2][1]) / 2, 236, "one complete message", "mid hand f-green"))
    body.append(text(20, 282, "3. And when the text itself contains a ~, it’s escaped as ~~", "sm b"))
    toks = [("~S", "ctrl")] + [(c if c != " " else "␣", "data") for c in "SEE YOU "] + [("~~", "esc")] + \
           [(c if c != " " else "␣", "data") for c in " SOON"] + [("~E", "ctrl")]
    row, w = boxes_row(toks, 40, 296)
    body.append(row)
    esc = [p for p, (lab, k) in zip(w, toks) if k == "esc"][0]
    body.append(f'<path d="M{esc[0] + esc[1] / 2},338 l0,14" class="line s-purple" marker-start="url(#ah-purple)"/>')
    body.append(text(esc[0] + esc[1] / 2, 372, "means one real “~”", "mid hand f-purple"))
    svg = fig("".join(body), 720, 386, "Three ways of marking where a message ends",
              "Words can appear inside messages. Control codes can’t, as long as we escape them.")
    (OUT / "ch03-over.svg").write_text(svg)


def sequence():
    s = Seq([("Alice", 230, "alice"), ("Bob", 490, "bob")], top=86, scale=30)
    s.msg("Alice", "Bob", 0, 1, "~S HI BOB ~E", step="1")
    s.note("Bob", 1.1, "prints “HI BOB”", step="1", side="right")
    s.msg("Bob", "Alice", 1.5, 2.5, "~A", "green", step="1")
    s.note("Alice", 2.6, "delivered ✓", step="1", cls="f-green", side="left")
    s.msg("Alice", "Bob", 3.5, 4.5, "~S WANT TO PLAY? ~E", step="2", lost=0.55)
    s.timer("Alice", 3.5, 6.3, "waiting for ~A…", step="2")
    s.note("Alice", 6.8, "time’s up! send it again", step="3", cls="f-orange", side="left")
    s.msg("Alice", "Bob", 6.8, 7.8, "~S WANT TO PLAY? ~E", step="3")
    s.note("Bob", 7.9, "prints “WANT TO PLAY?”", step="3", side="right")
    s.msg("Bob", "Alice", 8.3, 9.3, "~A", "green", step="3")
    s.msg("Alice", "Bob", 10.3, 11.3, "~S MEET AT NOON ~E", step="4")
    s.note("Bob", 11.4, "prints “MEET AT NOON”", step="4", side="right")
    s.msg("Bob", "Alice", 11.8, 12.8, "~A", "green", step="4", lost=0.5)
    s.timer("Alice", 11.3, 14.1, "waiting for ~A…", step="4")
    s.note("Alice", 14.6, "time’s up! send it again", step="5", cls="f-orange", side="left")
    s.msg("Alice", "Bob", 14.6, 15.6, "~S MEET AT NOON ~E", step="5")
    s.note("Bob", 15.7, "prints it AGAIN?!", step="5", cls="f-red", side="right")
    s.msg("Bob", "Alice", 16.1, 17.1, "~A", "green", step="5")
    body, h = s.render()
    steps = [
        "The normal case. Alice sends a message, Bob prints it and replies <code>~A</code> (“got it”), and Alice knows it arrived.",
        "This time a burst of noise wrecks the message on its way. Bob never sees a complete message, so he never replies. Alice starts a timer.",
        "The timer runs out with no <code>~A</code>, so Alice assumes the message was lost and sends it again. This time it gets through.",
        "Now the <em>message</em> arrives fine, and Bob prints it, but his <code>~A</code> is the one that gets lost.",
        "Alice can’t tell the difference between a lost message and a lost <code>~A</code>, so she does the only thing she can: sends it again. And Bob, who has no way of knowing he’s seen it before, prints it twice.",
    ]
    svg = fig(body, 720, h, "Sequence diagram: a message, a lost message with a timeout and retry, and a lost acknowledgement causing a duplicate",
              "Time runs down the page. Each arrow is one message crossing the wire.", steps)
    (OUT / "ch03-sequence.svg").write_text(svg)


def states():
    def state(x, y, w, label, sub, cls):
        return (f'<rect x="{x}" y="{y}" width="{w}" height="54" rx="27" class="{cls}" stroke="var(--ink)" stroke-width="2"/>'
                + text(x + w / 2, y + 24, label, "mid slab b")
                + text(x + w / 2, y + 42, sub, "mid xs muted"))

    def arrow(d, label, lx, ly, cls="ink", anchor="mid"):
        return (f'<path d="{d}" class="line s-{cls if cls != "ink" else "ink"}" marker-end="url(#ah-{cls})"/>'
                + text(lx, ly, label, f"{anchor} hand halo"))

    body = [
        state(20, 150, 150, "IDLE", "nothing to send", "t-teal"),
        state(285, 40, 150, "SENDING", "~S … ~E", "t-yellow"),
        state(545, 150, 160, "WAITING", "for ~A, timer on", "t-blue"),
        state(285, 262, 150, "BACKOFF", "wait a random time", "t-red"),
        arrow("M110,148 C130,90 200,70 280,68", "have a message", 150, 88, anchor="mid"),
        arrow("M438,68 C520,70 590,90 612,146", "sent ~E", 562, 88),
        arrow("M543,184 L174,184", "got ~A: success!", 462, 176, "green"),
        arrow("M350,98 L350,258", "collision!", 342, 140, "red", anchor="end"),
        arrow("M630,206 C610,270 520,296 440,292", "timer ran out", 590, 280, "orange"),
        arrow("M372,258 L372,100", "line quiet again", 380, 236, "ink", anchor="start"),
        arrow("M282,300 C180,300 110,260 96,208", "too many tries: give up", 150, 330, "muted", anchor="mid"),
    ]
    body.append('<rect x="20" y="20" width="220" height="92" rx="10" class="card"/>')
    body.append(text(32, 44, "In every state:", "sm b"))
    body.append(text(32, 66, "if a message arrives,", "sm"))
    body.append(text(32, 86, "print it and send ~A", "sm"))
    body.append(text(32, 104, "(as soon as the line is quiet)", "xs muted"))
    svg = fig("".join(body), 720, 344, "State machine for the Chatterbox Protocol",
              "The whole protocol as a state machine: every Chatterbox is always in exactly one of these four states.")
    (OUT / "ch03-states.svg").write_text(svg)


if __name__ == "__main__":
    roads()
    collision()
    over()
    sequence()
    states()
    print("wrote ch03 figures")
