#!/usr/bin/env python3
"""Generate chapter 27 figures.  python3 src/figs/ch27.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent



# ---------------------------------------------------------------- the header, with the real SYN in it

def header():
    rows = [
        [("source port", 16, "58798", "t-yellow"), ("destination port", 16, "443 (HTTPS)", "t-yellow")],
        [("sequence number", 32, "1912436191: where this segment’s bytes start", "t-blue")],
        [("acknowledgement number", 32, "0: “the next byte I expect from you” (none yet)", "t-green")],
        [("offset", 4, "10", "f-card"), ("", 4, "", "f-card"), ("flags", 8, "SYN", "t-red"), ("window", 16, "64240 bytes", "t-purple")],
        [("checksum", 16, "0x9510", "f-card"), ("urgent pointer", 16, "0 (never used)", "f-card")],
        [("options", 32, "MSS 1460 · SACK permitted · timestamps · window scale 10", "t-orange")],
    ]
    x0, w, rh = 60, 600, 40
    b = [text(x0, 16, "0", "xs muted"), text(x0 + w / 2, 16, "16", "mid xs muted"), text(x0 + w, 16, "31 bits", "end xs muted")]
    for r, row in enumerate(rows):
        x = x0
        y = 24 + r * rh
        for name, bits, value, cls in row:
            bw = w * bits / 32
            stroke = {"t-yellow": "var(--yellow)", "t-blue": "var(--blue)", "t-green": "var(--green)", "t-red": "var(--red)",
                      "t-purple": "var(--purple)", "t-orange": "var(--orange)"}.get(cls, "var(--line)")
            b.append(f'<rect x="{x:g}" y="{y}" width="{bw:g}" height="{rh - 2}" class="{cls}" stroke="{stroke}" stroke-width="1.3"/>')
            if name:
                b.append(text(x + bw / 2, y + 15, name, "mid xs b"))
                b.append(text(x + bw / 2, y + 31, value, "mid xs mono"))
            x += bw
    b.append(text(x0 - 8, 24 + 5 * rh + 24, "20 more", "end xs muted"))
    b.append(text(x0 - 8, 24 + 5 * rh + 36, "bytes", "end xs muted"))
    b.append(text(360, 24 + 6 * rh + 22, "“offset 10” means the header is 10 × 4 = 40 bytes long: 20 fixed, and 20 bytes of options.", "mid xs"))
    b.append(text(360, 24 + 6 * rh + 38, "The flags are one bit each: SYN, ACK, FIN, RST, PSH, URG, and two for congestion (ECE, CWR, Chapter 28).", "mid xs"))
    svg = fig("".join(b), 720, 24 + 6 * rh + 48, "The TCP header, filled in with the values from the Pi's real SYN segment",
              "The TCP header, with the real SYN that opened Grandpa Otto’s connection to example.org. Compare UDP’s 8 bytes in Chapter 26.")
    (OUT / "ch27-header.svg").write_text(svg)


# ---------------------------------------------------------------- the real handshake

def handshake():
    P, S = "Grandpa Otto’s Pi", "example.org (Cloudflare)"
    seq = Seq([(P, 150, None), (S, 570, None)], top=40, scale=34, head=False)
    seq.msg(P, S, 0.3, 1.3, "SYN  seq 1912436191", "navy", step="1", sub="mss 1460 · sackOK · timestamps · wscale 10")
    seq.msg(S, P, 2.3, 3.3, "SYN, ACK  seq 3510948663  ack 1912436192", "purple", step="2", sub="mss 1400 · sackOK · timestamps · wscale 13")
    seq.msg(P, S, 4.3, 5.3, "ACK  ack 3510948664", "navy", step="3", sub="30.2 ms after the SYN: one round trip")
    seq.note(P, 6.3, "established: from now on, count from 0", step="4", cls="f-green")
    body, bottom = seq.render(20)
    steps = ["The Pi sends a segment with the SYN flag (“synchronize”) and no data. Its sequence number is its <strong>initial sequence number</strong>, picked at random. The options say what it can do: take segments of up to 1,460 bytes, understand selective acknowledgements and timestamps, and multiply its window by 2<sup>10</sup>.",
             "The server answers with SYN and ACK together. It acknowledges the Pi’s SYN by expecting byte 1912436192 next (a SYN counts as one byte, even though it carries none), and picks its own random starting number, and its own options.",
             "The Pi acknowledges the server’s SYN. Three segments, one and a half round trips, and both sides know the other’s starting number. The Pi can send data straight after this ACK, and does, 3 ms later.",
             "Because the real numbers are huge and random, tools like tcpdump, Wireshark and this chapter’s lab usually show them <em>relative</em> to the starting number: the first byte of data is byte 1."]
    svg = fig(body, 720, bottom, "The real three-way handshake between the Pi and example.org's server, with sequence numbers and options",
              "The three-way handshake, from the real capture (Chapter 13 invented it; here are the numbers).", steps)
    (OUT / "ch27-handshake.svg").write_text(svg)


# ---------------------------------------------------------------- why 1388 and 1440?

def mss():
    b = []

    def packet(y, label, parts, total):
        out = [text(14, y + 20, label, "xs b")]
        x = 190
        scale = 500 / 1500
        for name, size, cls, stroke in parts:
            w = size * scale
            out.append(f'<rect x="{x:g}" y="{y}" width="{w:g}" height="30" class="{cls}" stroke="{stroke}" stroke-width="1.2"/>')
            if w > 40:
                out.append(text(x + w / 2, y + 19, f"{name} {size}", "mid xs b"))
            elif name:
                out.append(text(x + w / 2, y + 19, str(size), "mid xs b"))
            x += w
        out.append(text(x + 6, y + 19, f"= {total}", "xs b"))
        return "".join(out)
    hdr = [("IP", 20, "t-yellow", "var(--yellow)"), ("TCP", 20, "t-blue", "var(--blue)"), ("", 12, "t-orange", "var(--orange)")]
    b.append(packet(20, "Pi → server: 1388 bytes", hdr + [("data", 1388, "t-green", "var(--green)")], 1440))
    b.append(packet(66, "server → Pi: 1440 bytes", hdr + [("data", 1440, "t-green", "var(--green)")], 1492))
    b.append('<g data-show="1">' + text(190, 122, "The server said “MSS 1400” in its SYN-ACK. Every segment also carries 12 bytes of", "xs")
             + text(190, 138, "timestamps (orange), which count against it: 1400 − 12 = 1388 bytes of data.", "xs") + "</g>")
    b.append('<g data-show="2">' + text(190, 160, "The Pi said “MSS 1460” (1500 − 40). But on the way out, Bob’s router rewrote it to 1452,", "xs")
             + text(190, 176, "because its internet connection only carries 1,492-byte packets (Chapter 22’s MSS clamping).", "xs")
             + text(190, 192, "So the server sends 1452 − 12 = 1440 bytes of data: packets of exactly 1,492 bytes.", "xs b") + "</g>")
    steps = ["Each side tells the other, in its SYN, the biggest <strong>segment</strong> it can take: its maximum segment size, or MSS, which counts only the data, not the headers. Cloudflare’s servers say 1,400, which leaves room for tunnels along the way. The Pi’s segments are 1,388 bytes.",
             "The capture was taken on the Pi, so it shows the SYN as the Pi sent it. What the server received was different, and the proof is the size of the server’s segments: exactly what fits in Bob’s internet connection. Mystery from Chapter 16, solved from the other side."]
    svg = fig("".join(b), 720, 204, "Why the Pi's segments carry 1388 bytes of data and the server's 1440: MSS values, the timestamp option, and MSS clamping",
              "Why the segments are the sizes they are.", steps)
    (OUT / "ch27-mss.svg").write_text(svg)


# ---------------------------------------------------------------- a real loss, repaired with SACK

def sack():
    P, S = "the Pi", "the server"
    seq = Seq([(P, 150, None), (S, 570, None)], top=40, scale=30, head=False)
    seq.msg(S, P, 0.3, 1.0, "5626:5657", "purple", step="1", sub="31 bytes")
    seq.msg(S, P, 1.4, 2.1, "5657:5828", "purple", step="1", lost=0.55)
    seq.msg(S, P, 2.5, 3.2, "5828:6418", "purple", step="2", sub="210.7 ms: arrives with a gap before it")
    seq.msg(P, S, 3.8, 4.5, "ACK 5657, SACK 5828-6418", "navy", step="3", sub="“I still need 5657, but I have 5828 to 6418”")
    seq.msg(S, P, 5.6, 6.3, "5657:5828 again", "orange", step="4", sub="300.8 ms: just the missing piece")
    seq.msg(P, S, 6.9, 7.6, "ACK 6418", "green", step="5", sub="“I have everything up to 6418”")
    body, bottom = seq.render(20)
    steps = ["The server sends three segments of the web page. The middle one, bytes 5657 to 5828, is lost somewhere on the way.",
             "The next one arrives with a gap in front of it. The Pi can’t hand its bytes to the program yet (TCP delivers a stream in order), so it keeps them, and waits.",
             "The Pi’s acknowledgement still says 5657, the first byte it’s missing, as Chapter 13’s cumulative ACKs did. But it adds a <strong>SACK</strong> block, a selective acknowledgement: “and I also have 5828 to 6418”.",
             "So the server knows exactly what’s missing, and resends only that: 171 bytes, instead of everything after the gap (Chapter 13’s “go back N”).",
             "The hole is filled. The Pi hands all of it to the browser, and acknowledges everything up to 6418 in one go. The whole repair took 90 milliseconds."]
    svg = fig(body, 720, bottom, "A real lost segment, a SACK block reporting the data received after the gap, and the retransmission of just the missing piece",
              "A real loss, repaired with a selective acknowledgement.", steps)
    (OUT / "ch27-sack.svg").write_text(svg)


# ---------------------------------------------------------------- lost, or just slow? A tail loss probe

def tlp():
    P, S = "the Pi", "the server"
    seq = Seq([(P, 150, None), (S, 570, None)], top=40, scale=30, head=False)
    seq.msg(P, S, 0.3, 1.3, "1:1389", "navy", step="1", sub="33.5 ms: the first part of a TLS hello (Chapter 32)")
    seq.msg(P, S, 1.6, 2.6, "1389:1572", "navy", step="1", sub="the rest: the last thing the Pi has to send")
    seq.timer(P, 1.6, 4.4, "no ACK for 65 ms", step="2")
    seq.msg(P, S, 4.4, 5.4, "1389:1572 again", "orange", step="2", sub="98.3 ms: a “tail loss probe”")
    seq.msg(S, P, 4.9, 5.9, "ACK 1572", "purple", step="3", sub="113.2 ms: it had everything all along")
    seq.msg(S, P, 7.0, 8.0, "ACK 1572, D-SACK 1389-1572", "purple", step="4", sub="189.0 ms: “by the way, I got those bytes twice”")
    body, bottom = seq.render(20)
    steps = ["The Pi sends the two segments of a TLS hello, and then has nothing more to send until the server answers.",
             "Normally, a lost segment is noticed when later segments arrive and the receiver sends duplicate ACKs. But when the lost one is the <em>last</em>, nothing follows it, so nothing reveals the loss, and the sender would have to wait for its full timeout (at least 200 ms on Linux, often much more). So Linux uses a <strong>tail loss probe</strong>: after about two round trips of silence, it resends the last segment, to provoke an acknowledgement.",
             "Here, nothing had been lost: the server’s acknowledgement was just slow, and crossed the probe on the way.",
             "The server’s next acknowledgement carries a <strong>D-SACK</strong> (“duplicate SACK”): a SACK block for bytes <em>before</em> the acknowledgement number, which means “these arrived twice”. Now the Pi knows its resend was unnecessary, and that the network didn’t really lose anything. That matters for the next chapter: TCP slows down when it thinks it’s lost data, and a D-SACK lets it undo that."]
    svg = fig(body, 720, bottom, "A real tail loss probe: the Pi resends its last segment after 65 ms of silence, and the server later reports the duplicate with a D-SACK",
              "Lost, or just slow? Three unnecessary resends in this capture, and how TCP found out.", steps)
    (OUT / "ch27-tlp.svg").write_text(svg)


# ---------------------------------------------------------------- the states

def states():
    b = []
    nodes = {"CLOSED": (100, 40), "LISTEN": (560, 40), "SYN_SENT": (100, 120), "SYN_RCVD": (560, 120),
             "ESTABLISHED": (330, 200), "FIN_WAIT_1": (100, 280), "CLOSE_WAIT": (560, 280), "FIN_WAIT_2": (100, 350),
             "LAST_ACK": (560, 350), "TIME_WAIT": (100, 420), "CLOSED ": (560, 420)}
    edges = [("CLOSED", "SYN_SENT", "connect(): send SYN", "l"), ("LISTEN", "SYN_RCVD", "SYN in: send SYN,ACK", "r"),
             ("SYN_SENT", "ESTABLISHED", "SYN,ACK in: send ACK", "l"), ("SYN_RCVD", "ESTABLISHED", "ACK in", "r"),
             ("ESTABLISHED", "FIN_WAIT_1", "close(): send FIN", "l"), ("ESTABLISHED", "CLOSE_WAIT", "FIN in: send ACK", "r"),
             ("FIN_WAIT_1", "FIN_WAIT_2", "ACK in", "l"), ("CLOSE_WAIT", "LAST_ACK", "close(): send FIN", "r"),
             ("FIN_WAIT_2", "TIME_WAIT", "FIN in: send ACK", "l"), ("LAST_ACK", "CLOSED ", "ACK in", "r")]
    for a, c, label, side in edges:
        (x1, y1), (x2, y2) = nodes[a], nodes[c]
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** 0.5
        sx, sy = x1 + dx / L * 22, y1 + dy / L * 18
        ex, ey = x2 - dx / L * 26, y2 - dy / L * 20
        b.append(f'<line x1="{sx:g}" y1="{sy:g}" x2="{ex:g}" y2="{ey:g}" class="line s-muted" stroke-width="2" marker-end="url(#ah-muted)"/>')
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        anchor = "start" if side == "l" and dx == 0 else "end" if side == "r" and dx == 0 else "middle"
        off = 10 if anchor == "start" else -10 if anchor == "end" else 0
        b.append(f'<text x="{mx + off:g}" y="{my + 4:g}" class="xs halo" text-anchor="{anchor}">{label}</text>')
    for name, (x, y) in nodes.items():
        n = name.strip()
        cls = "t-green" if n == "ESTABLISHED" else "t-orange" if n == "TIME_WAIT" else "f-surface"
        w = 12 + 8.4 * len(n)
        b.append(f'<rect x="{x - w / 2:g}" y="{y - 14}" width="{w:g}" height="28" rx="14" class="{cls}" stroke="var(--line)" stroke-width="1.5"/>')
        b.append(text(x, y + 5, n, "mid mono xs b"))
    b.append(text(100, 452, "…waits 2 × the maximum segment lifetime (60 s on Linux), then CLOSED", "mid xs muted"))
    b.append(text(330, 20, "the client (it connects, and here it closes first)", "end xs b", style="fill:var(--blue)"))
    b.append(text(420, 20, "the server", "xs b", style="fill:var(--purple)"))
    svg = fig("".join(b), 720, 464, "The TCP state machine: opening states on both sides, ESTABLISHED, and the closing states including TIME_WAIT",
              "The states a TCP connection goes through, and what moves it from one to the next. <code>netstat</code> and <code>ss</code> show these names.")
    (OUT / "ch27-states.svg").write_text(svg)


if __name__ == "__main__":
    header()
    handshake()
    mss()
    sack()
    tlp()
    states()
    print("wrote ch27 figures")
