#!/usr/bin/env python3
"""Generate chapter 19 figures.  python3 src/figs/ch19.py"""
import math
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- listen, count down, talk, ACK

def csmaca():
    x0, us = 120, 1.25                      # left edge of the timeline, pixels per microsecond
    rows = {"laptop": 70, "phone": 140, "router": 210}
    b = []
    for name, y in rows.items():
        b.append(text(x0 - 12, y + 5, {"laptop": "Bob’s laptop", "phone": "Mum’s phone", "router": "the router"}[name], "end sm b"))
        b.append(f'<line x1="{x0}" y1="{y}" x2="706" y2="{y}" class="grid"/>')

    def block(t0, t1, y, label, cls, stroke, step):
        x, w = x0 + t0 * us, (t1 - t0) * us
        return (f'<g data-show="{step}"><rect x="{x:.1f}" y="{y - 14}" width="{w:.1f}" height="28" rx="4" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>'
                + text(x + w / 2, y + 5, label, "mid xs b") + "</g>")

    def slots(t0, n, y, step, start, frozen_at=None):
        out = [f'<g data-show="{step}">']
        for k in range(n):
            x = x0 + (t0 + 9 * k) * us
            out.append(f'<rect x="{x:.1f}" y="{y - 9}" width="{9 * us - 2:.1f}" height="18" rx="2" class="t-yellow" stroke="var(--yellow)"/>')
            out.append(text(x + 9 * us / 2 - 1, y + 4, str(start - k), "mid xs b"))
        out.append("</g>")
        return "".join(out)
    # step 1: someone else is talking
    b.append(f'<g data-show="1"><rect x="{x0}" y="46" width="{80 * us:.1f}" height="186" rx="4" class="f-line" style="opacity:0.6"/>'
             + text(x0 + 40 * us, 34, "someone else", "mid xs b muted") + text(x0 + 40 * us, 144, "busy", "mid sm b muted") + "</g>")
    # step 2: wait, then count down
    b.append(block(80, 114, 70, "wait", "f-none", "var(--muted)", "2"))
    b.append(block(80, 114, 140, "wait", "f-none", "var(--muted)", "2"))
    b.append(slots(114, 3, 70, "2", 3))
    b.append(slots(114, 3, 140, "2", 5))
    b.append(f'<g data-show="=2">{text(x0 + 150 * us, 108, "each picks a random number, and counts down while it’s quiet", "hand")}</g>')
    # step 3: laptop reaches zero and sends; phone freezes at 2
    b.append(block(141, 241, 70, "DATA", "t-blue", "var(--blue)", "3"))
    b.append(f'<g data-show="3-4">{text(x0 + 124 * us, 170, "the phone hears the laptop, and freezes at 2", "hand f-orange")}</g>')
    # step 4: ACK
    b.append(block(257, 301, 210, "ACK", "t-green", "var(--green)", "4"))
    b.append(f'<g data-show="4">{text(x0 + 257 * us, 250, "16 µs after the data", "mid xs muted")}</g>')
    # step 5: phone carries on from 2
    b.append(block(301, 335, 140, "wait", "f-none", "var(--muted)", "5"))
    b.append(slots(335, 2, 140, "5", 2))
    b.append(block(353, 453, 140, "DATA", "t-purple", "var(--purple)", "5"))
    b.append(f'<g data-show="5">{text(x0 + 403 * us, 108, "then its turn comes", "mid hand f-purple")}</g>')
    b.append(text(706, 262, "time →", "end xs muted"))
    steps = ["Someone else is using the channel. Bob’s laptop and his mum’s phone both have a frame to send, so they listen, and wait.",
             "The channel goes quiet. Each waits a moment longer, then picks a random number of 9-microsecond slots: 3 for the laptop, 5 for the phone. They count down, one slot at a time, while the channel stays quiet.",
             "The laptop reaches zero first and sends. The phone hears it, and freezes its count at 2 instead of starting again.",
             "Radio can’t tell a sender whether its frame collided, so the receiver has to say so: the router sends back an ACK, just 16 microseconds after the frame ends. No ACK means “try again”.",
             "The channel is quiet again. The phone waits, carries on counting from 2, and sends. If two stations had reached zero together, neither would get an ACK, and both would pick a new number from a range twice as big."]
    svg = fig("".join(b), 720, 272, "Two Wi-Fi stations waiting for a busy channel, counting down random backoff slots; one sends and is acknowledged, then the other",
              "Collision avoidance: wait, count down, talk, and wait for the ACK.", steps)
    (OUT / "ch19-csmaca.svg").write_text(svg)


# ---------------------------------------------------------------- the hidden station

def hidden():
    b = []
    ax, apx, cx, y = 150, 360, 570, 160
    b.append('<clipPath id="ch19-hidden-clip"><rect x="0" y="0" width="720" height="290" rx="8"/></clipPath>')
    b.append(f'<g data-show="1" clip-path="url(#ch19-hidden-clip)"><circle cx="{ax}" cy="{y}" r="250" class="f-none s-blue" stroke-width="2" stroke-dasharray="6 5" style="fill:var(--tint-blue);fill-opacity:0.35"/>'
             f'<circle cx="{cx}" cy="{y}" r="250" class="f-none s-purple" stroke-width="2" stroke-dasharray="6 5" style="fill:var(--tint-purple);fill-opacity:0.35"/></g>')
    b.append(f'<use href="#router" x="{apx - 36}" y="{y - 24}" width="72" height="48"/>')
    b.append(text(apx, y + 44, "the access point", "mid xs b"))
    b.append(f'<use href="#computer" x="{ax - 30}" y="{y - 27}" width="60" height="54"/>')
    b.append(text(ax, y + 44, "Alice’s laptop", "mid xs b"))
    b.append(f'<use href="#computer" x="{cx - 30}" y="{y - 27}" width="60" height="54"/>')
    b.append(text(cx, y + 44, "Carol’s laptop", "mid xs b"))
    # step 1: both send, crash at the AP
    b.append(f'<g data-show="=1"><path d="M{ax + 34},{y - 6} L{apx - 44},{y - 6}" class="line s-blue" stroke-width="4" marker-end="url(#ah-blue)"/>'
             f'<path d="M{cx - 34},{y - 6} L{apx + 44},{y - 6}" class="line s-purple" stroke-width="4" marker-end="url(#ah-purple)"/>'
             + text(apx, y - 40, "✗ both at once: noise", "mid hand f-red")
             + text(ax, 36, "Alice can’t hear Carol…", "mid hand")
             + text(cx, 36, "…and Carol can’t hear Alice", "mid hand") + "</g>")
    # step 2: RTS / CTS
    b.append(f'<g data-show="=2"><path d="M{ax + 34},{y - 6} L{apx - 44},{y - 6}" class="line s-blue" stroke-width="3" marker-end="url(#ah-blue)"/>'
             + text((ax + apx) / 2, y - 16, "RTS: may I?", "mid xs b")
             + f'<path d="M{apx - 20},{y + 60} Q{(ax + apx) / 2},{y + 96} {ax + 20},{y + 60}" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/>'
             + f'<path d="M{apx + 20},{y + 60} Q{(cx + apx) / 2},{y + 96} {cx - 20},{y + 60}" class="line s-green" stroke-width="3" marker-end="url(#ah-green)"/>'
             + text(apx, y + 104, "CTS: “Alice may send, for 300 µs”: everyone hears it", "mid xs b f-green")
             + text(cx, 36, "Carol stays quiet for 300 µs", "mid hand f-green") + "</g>")
    steps = ["Alice and Carol are at opposite ends of the house. Both can reach the access point, but they’re too far apart to hear each other, so each thinks the channel is free, and they send at the same time. At the access point, the two frames arrive on top of each other, and neither can be read. This is the <strong>hidden station</strong> problem.",
             "The fix: before sending a long frame, Alice sends a tiny <strong>RTS</strong> (“request to send”). The access point answers with a <strong>CTS</strong> (“clear to send”), which says how long Alice will be. Carol can’t hear Alice, but she can hear the access point, so she keeps quiet until Alice is done."]
    svg = fig("".join(b), 720, 290, "Two laptops out of range of each other both reach the access point; their frames collide there, and RTS/CTS lets the access point reserve the channel",
              "Stations that can’t hear each other, and the “may I?” that fixes it.", steps)
    (OUT / "ch19-hidden.svg").write_text(svg)


# ---------------------------------------------------------------- three addresses

def addresses():
    b = []
    lap, ap, rt = 70, 360, 650
    b.append(f'<use href="#computer" x="{lap - 34}" y="40" width="68" height="60"/>')
    b.append(text(lap, 118, "Bob’s laptop", "mid sm b"))
    b.append(text(lap, 134, "e2:5f:b1:3c:77:0a", "mid mono xs"))
    b.append(f'<use href="#router" x="{ap - 38}" y="48" width="76" height="50"/>')
    b.append(text(ap, 118, "access point", "mid sm b"))
    b.append(text(ap, 134, "14:c3:5e:40:0b:38", "mid mono xs"))
    b.append(f'<use href="#router" x="{rt - 38}" y="48" width="76" height="50"/>')
    b.append(text(rt, 118, "router", "mid sm b"))
    b.append(text(rt, 134, "14:c3:5e:40:0b:32", "mid mono xs"))
    for r in (14, 26, 38):
        b.append(f'<path d="M{lap + 44},{70 - r * 0.8} q{r * 0.6},{r * 0.8} 0,{r * 1.6}" class="line s-purple" stroke-width="2" style="opacity:0.6"/>')
    b.append(f'<line x1="{ap + 40}" y1="73" x2="{rt - 40}" y2="73" class="wire" stroke-width="4"/>')
    # the wi-fi frame
    wf = [("receiver", "14:c3:…:0b:38", "the access point"), ("transmitter", "e2:5f:…:77:0a", "the laptop"),
          ("destination", "14:c3:…:0b:32", "the router")]
    b.append(text(20, 170, "In the air: a Wi-Fi frame, “to the network” bit set", "sm b f-purple"))
    x = 20
    for name, val, who in wf:
        b.append(f'<rect x="{x}" y="180" width="100" height="46" rx="5" class="t-purple" stroke="var(--purple)" stroke-width="1.5"/>')
        b.append(text(x + 50, 198, name, "mid xs b"))
        b.append(text(x + 50, 216, val, "mid mono xs"))
        b.append(text(x + 50, 242, who, "mid xs muted"))
        x += 104
    b.append(f'<rect x="{x}" y="180" width="60" height="46" rx="5" class="t-yellow" stroke="var(--yellow)" stroke-width="1.5"/>')
    b.append(text(x + 30, 208, "data 🔒", "mid xs b"))
    # the ethernet frame
    b.append(text(430, 170, "On the cable: an Ethernet frame", "sm b f-blue"))
    x = 430
    for name, val, who in (("to", "14:c3:…:0b:32", "the router"), ("from", "e2:5f:…:77:0a", "the laptop")):
        b.append(f'<rect x="{x}" y="180" width="100" height="46" rx="5" class="t-blue" stroke="var(--blue)" stroke-width="1.5"/>')
        b.append(text(x + 50, 198, name, "mid xs b"))
        b.append(text(x + 50, 216, val, "mid mono xs"))
        b.append(text(x + 50, 242, who, "mid xs muted"))
        x += 104
    b.append(f'<rect x="{x}" y="180" width="60" height="46" rx="5" class="t-yellow" stroke="var(--yellow)" stroke-width="1.5"/>')
    b.append(text(x + 30, 208, "data", "mid xs b"))
    b.append(f'<path d="M398,203 L424,203" class="line s-ink" stroke-width="2.5" marker-end="url(#ah-ink)"/>')
    b.append(text(376, 268, "the access point decrypts it, and rewrites the envelope", "mid hand"))
    svg = fig("".join(b), 720, 282, "A Wi-Fi frame from the laptop has three addresses: the access point receiving it, the laptop sending it, and the router it's really for. The access point turns it into an Ethernet frame with two.",
              "In the air, a frame needs three addresses: the next hop, the sender, and where it’s really going.")
    (OUT / "ch19-addresses.svg").write_text(svg)


# ---------------------------------------------------------------- crowded channels

SCAN_24 = [(1, -79), (1, -48), (3, -72), (6, -66), (6, -62), (6, -33), (9, -76), (11, -61), (11, -29)]
SCAN_5 = [(36, -24, 80), (40, -84, 80), (40, -84, 80), (40, -83, 80), (44, -77, 80), (52, -90, 80), (52, -89, 80),
          (149, -38, 80), (157, -67, 80)]


def channels():
    b = [text(14, 22, "2.4 GHz: what Grandpa Otto’s Pi could hear, one evening", "sm b")]
    x0, x1, f0, f1, base = 60, 700, 2400, 2484, 170
    px = lambda f: x0 + (f - f0) / (f1 - f0) * (x1 - x0)
    height = lambda dbm: (dbm + 95) * 1.7
    b.append(f'<line x1="{x0}" y1="{base}" x2="{x1}" y2="{base}" class="line" stroke-width="1.5"/>')
    for ch in range(1, 14):
        f = 2407 + 5 * ch
        b.append(f'<line x1="{px(f):.1f}" y1="{base}" x2="{px(f):.1f}" y2="{base + 5}" class="line" stroke-width="1"/>')
        b.append(text(px(f), base + 18, str(ch), "mid xs" + (" b" if ch in (1, 6, 11) else " muted")))
    b.append(text(x0 - 8, base + 18, "channel", "end xs muted"))
    for ch, dbm in SCAN_24:
        f = 2407 + 5 * ch
        hgt = height(dbm)
        bad = ch not in (1, 6, 11)
        colour = "var(--red)" if bad else "var(--blue)"
        d = f"M{px(f - 11):.1f},{base} C{px(f - 8):.1f},{base - hgt:.1f} {px(f + 8):.1f},{base - hgt:.1f} {px(f + 11):.1f},{base}"
        b.append(f'<path d="{d}" style="fill:{colour};fill-opacity:0.18;stroke:{colour}" stroke-width="1.8"/>')
    b.append(text(px(2422), base - height(-72) - 24, "channel 3 overlaps", "mid xs b f-red"))
    b.append(text(px(2422), base - height(-72) - 11, "both 1 and 6", "mid xs b f-red"))
    b.append(text(px(2452), base - height(-76) - 11, "9 hits 6 and 11", "mid xs b f-red"))
    b.append(text(x1, 44, "each hump: one network, as tall as it is loud", "end xs muted"))
    # 5 GHz
    y5 = 240
    b.append(text(14, y5, "5 GHz: much more room, in wider blocks", "sm b"))
    g0, g1 = 5170, 5835
    qx = lambda f: x0 + (f - g0) / (g1 - g0) * (x1 - x0)
    blocks = [(36, 48, "36–48"), (52, 64, "52–64"), (100, 112, "100–112"), (116, 128, "116–128"), (132, 144, "132–144"), (149, 161, "149–161")]
    for lo, hi, label in blocks:
        fa, fb = 5000 + 5 * lo - 10, 5000 + 5 * hi + 10
        count = sum(1 for ch, _, _ in SCAN_5 if lo <= ch <= hi)
        ours = lo == 149
        cls = "t-green" if ours else "t-blue" if count else "f-card"
        stroke = "var(--green)" if ours else "var(--blue)" if count else "var(--line)"
        b.append(f'<rect x="{qx(fa):.1f}" y="{y5 + 14}" width="{qx(fb) - qx(fa) - 3:.1f}" height="40" rx="4" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(text((qx(fa) + qx(fb)) / 2, y5 + 32, label, "mid xs b"))
        note = "ours + 1 more" if ours else (f"{count} network" + ("s" if count > 1 else "")) if count else "empty"
        b.append(text((qx(fa) + qx(fb)) / 2, y5 + 47, note, "mid xs" + ("" if count else " muted")))
    b.append(text(x0, y5 + 72, "Each block is four 20 MHz channels joined into one 80 MHz channel. Blocks 52–144 must also share with weather radar.", "xs muted"))
    svg = fig("".join(b), 720, 330, "Real Wi-Fi networks heard by the Pi on 2.4 GHz channels 1, 3, 6, 9 and 11, with overlapping ones marked, and 5 GHz blocks of 80 MHz channels",
              "Only channels 1, 6 and 11 don’t overlap on 2.4 GHz. Networks on 3 or 9 get interference from both sides, and cause it too.")
    (OUT / "ch19-channels.svg").write_text(svg)


# ---------------------------------------------------------------- joining a network

def join():
    seq = Seq([("laptop", 150, None), ("access point", 570, None)], top=40, scale=34, head=False)
    msgs = [
        ("access point", "laptop", "beacon: “HomeWiFi is here, WPA2”", "1", "ten times a second, to everyone", 0),
        ("laptop", "access point", "probe request: “anyone here?”", "2", None, 1.3),
        ("access point", "laptop", "probe response", "2", None, 0.9),
        ("laptop", "access point", "authentication (open)", "3", None, 1.2),
        ("access point", "laptop", "authentication: OK", "3", None, 0.9),
        ("laptop", "access point", "association request", "4", None, 1.2),
        ("access point", "laptop", "association response: “you’re number 3”", "4", None, 0.9),
        ("access point", "laptop", "key message 1: a random number", "5", None, 1.2),
        ("laptop", "access point", "key message 2: my random number, and a proof", "5", None, 1.05),
        ("access point", "laptop", "key message 3: my proof, and the group key", "5", None, 1.05),
        ("laptop", "access point", "key message 4: done", "5", None, 1.05),
        ("laptop", "access point", "DHCP: “can I have an IP address?”", "6", "Chapter 22", 1.2),
    ]
    steps, t = [], 0.3
    for a, c, label, step, sub, gap in msgs:
        t += gap
        steps.append((a, c, t, t + 0.4, label, step, sub))
    for a, c, t0, t1, label, step, sub in steps:
        seq.msg(a, c, t0, t1, label, "navy" if a == "laptop" else "purple", step=step, sub=sub)
    body, bottom = seq.render(20)
    captions = ["The access point sends a <strong>beacon</strong> about ten times a second, announcing its network’s name, its channel, and what it supports. A laptop can find networks just by listening.",
                "Or it can shout: a <strong>probe request</strong> asks “is anyone here?” (or “is HomeWiFi here?”), and access points answer. This is how your phone finds networks faster than beacons alone would let it.",
                "“Authentication”, but not really: it’s a leftover from the original 1997 standard, and for a home network it always says yes.",
                "<strong>Association</strong>: the laptop asks to join, and the access point gives it a number. From now on, the access point will pass its frames on.",
                "The <strong>four-way handshake</strong>. The password is never sent. Instead, both sides mix it with two random numbers to make a fresh key for this laptop alone, and each proves it got the same answer. The frames are EAPOL, EtherType 0x888E, from Chapter 18’s table.",
                "Now the laptop’s frames are encrypted, and it can ask for an address (Chapter 22). All of this takes a few tens of milliseconds."]
    svg = fig(body, 720, bottom, "Joining a Wi-Fi network: beacon, probe, authentication, association, the four-way key handshake, then DHCP",
              "Joining a Wi-Fi network, frame by frame.", captions)
    (OUT / "ch19-join.svg").write_text(svg)


# ---------------------------------------------------------------- where 702 Mb/s comes from

def ofdm():
    b = [text(14, 22, "One 80 MHz channel, split into 256 narrow subcarriers (242 shown to scale)", "sm b")]
    x0, x1, base = 30, 690, 110
    n = 242
    w = (x1 - x0) / n
    for i in range(n):
        x = x0 + i * w
        pilot = i % 30 == 7
        colour = "var(--orange)" if pilot else "var(--blue)"
        hgt = 60
        b.append(f'<path d="M{x - w:.2f},{base} Q{x + w / 2:.2f},{base - 2 * hgt} {x + 2 * w:.2f},{base}" '
                 f'style="fill:none;stroke:{colour};stroke-opacity:0.5" stroke-width="0.7"/>')
    b.append(f'<line x1="{x0}" y1="{base}" x2="{x1}" y2="{base}" class="line" stroke-width="1.5"/>')
    b.append(text(x0, base + 16, "5,735 MHz", "xs muted"))
    b.append(text(x1, base + 16, "5,815 MHz", "end xs muted"))
    b.append(text(360, base + 16, "blue: 234 carry data · orange: 8 “pilots” for keeping in tune", "mid xs"))
    parts = [("234", "subcarriers", 86), ("× 8", "bits each (256-QAM)", 124), ("× ¾", "kept after error correction", 158),
             ("× 2", "antennas, two streams", 132), ("÷ 4 µs", "per symbol", 84), ("= 702", "Mb/s", 70)]
    x = 22
    for big, small, wdt in parts:
        b.append(text(x + wdt / 2, 170, big, "mid lg b" + (" f-green" if big.startswith("=") else "")))
        b.append(text(x + wdt / 2, 190, small, "mid xs muted"))
        x += wdt + 4
    svg = fig("".join(b), 720, 206, "An 80 MHz Wi-Fi channel divided into hundreds of narrow subcarriers, and the arithmetic that gives the laptop's 702 megabits per second",
              "Chapter 17’s rule again: symbols per second × bits per symbol × lanes. Here the lanes are subcarriers and antennas.")
    (OUT / "ch19-ofdm.svg").write_text(svg)


if __name__ == "__main__":
    csmaca()
    hidden()
    addresses()
    channels()
    join()
    ofdm()
    print("wrote ch19 figures")
