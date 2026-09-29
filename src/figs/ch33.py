#!/usr/bin/env python3
"""Generate chapter 33 figures.  python3 src/figs/ch33.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent
STREAM_COL = {"1": ("t-blue", "var(--blue)"), "3": ("t-orange", "var(--orange)"), "5": ("t-green", "var(--green)")}


def box(x, y, w, h, label, cls, stroke, sub=None, lcls="mid xs b"):
    out = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="6" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>'
    out += text(x + w / 2, y + h / 2 + (0 if sub else 4), label, lcls)
    if sub:
        out += text(x + w / 2, y + h / 2 + 14, sub, "mid xs muted")
    return out


# ---------------------------------------------------------------- three stacks

def stacks():
    cols = [("HTTP/1.1", [("HTTP/1.1", "text headers", "t-green", "var(--green)"), ("TLS 1.3", "", "t-purple", "var(--purple)"),
                          ("TCP", "", "t-blue", "var(--blue)"), ("IP", "", "f-card", "var(--line)")]),
            ("HTTP/2", [("HTTP/2", "binary frames, streams", "t-green", "var(--green)"), ("TLS 1.3", "", "t-purple", "var(--purple)"),
                        ("TCP", "", "t-blue", "var(--blue)"), ("IP", "", "f-card", "var(--line)")]),
            ("HTTP/3", [("HTTP/3", "frames, no streams of its own", "t-green", "var(--green)"),
                        ("QUIC", "streams, reliability, congestion control, with TLS 1.3 inside", "t-orange", "var(--orange)"),
                        ("UDP", "", "t-blue", "var(--blue)"), ("IP", "", "f-card", "var(--line)")])]
    b = []
    for c, (title, layers) in enumerate(cols):
        x = 20 + c * 236
        b.append(text(x + 105, 22, title, "mid sm b"))
        y = 34
        for name, sub, cls, stroke in layers:
            h = 74 if name == "QUIC" else 44
            b.append(box(x, y, 210, h - 6, name, cls, stroke, sub or None, "mid sm b"))
            y += h
    b.append(text(20 + 2 * 236 + 105, 272, "QUIC is UDP’s datagrams with TCP’s", "mid xs"))
    b.append(text(20 + 2 * 236 + 105, 288, "and TLS’s jobs rebuilt on top, in one piece", "mid xs"))
    svg = fig("".join(b), 720, 300, "Three protocol stacks: HTTP/1.1 and HTTP/2 over TLS over TCP, and HTTP/3 over QUIC over UDP",
              "The same requests and responses, carried three ways. HTTP/2 changes only the top layer; HTTP/3 replaces TCP and TLS as well.")
    (OUT / "ch33-stacks.svg").write_text(svg)


# ---------------------------------------------------------------- an HTTP/2 frame

def frame():
    fields = [("length", "00 00 1f", "31 bytes of payload", 3, "t-yellow", "var(--yellow)"),
              ("type", "01", "1 = HEADERS", 1, "t-green", "var(--green)"),
              ("flags", "05", "END_STREAM + END_HEADERS", 1, "t-orange", "var(--orange)"),
              ("stream", "00 00 00 01", "stream 1", 4, "t-blue", "var(--blue)"),
              ("payload", "82 87 41 88 2f 91 d3 …", "the headers, compressed (HPACK)", 6, "f-card", "var(--line)")]
    b, x = [], 20
    for name, hexb, meaning, units, cls, stroke in fields:
        w = units * 44
        b.append(f'<rect x="{x}" y="36" width="{w}" height="40" rx="6" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(text(x + w / 2, 60, hexb, "mid mono sm b"))
        b.append(text(x + w / 2, 28, name, "mid xs b"))
        b.append(text(x + w / 2, 94, meaning, "mid xs"))
        x += w + 6
    b.append(text(20, 130, "Every HTTP/2 frame starts with these 9 bytes. The ten types include DATA (0) and HEADERS (1) for requests and", "xs"))
    b.append(text(20, 147, "responses, and SETTINGS, WINDOW_UPDATE, PING, RST_STREAM and GOAWAY for managing the connection. This is the", "xs"))
    b.append(text(20, 164, "request our lab sent to example.org: a whole GET, headers and all, in 40 bytes.", "xs"))
    svg = fig("".join(b), 720, 176, "An HTTP/2 frame header: 3-byte length, 1-byte type, 1-byte flags, 4-byte stream number, then the payload",
              "An HTTP/2 frame, from <code>h2client.py example.org</code>.")
    (OUT / "ch33-frame.svg").write_text(svg)


# ---------------------------------------------------------------- one connection, many streams (real order from Wikipedia)

def multiplex():
    real = "55555555555555553311553311553155311553135511335513551313131131311313311313311313311313311111111111"
    b = [text(20, 22, "HTTP/1.1: one request at a time on each connection, so browsers open up to six", "xs b")]
    for c, (sid, n) in enumerate([("1", 34), ("3", 24), ("5", 32)]):
        y = 34 + c * 22
        cls, stroke = STREAM_COL[sid]
        b.append(text(20, y + 14, f"connection {c + 1}", "xs muted"))
        b.append(f'<rect x="106" y="{y + 2}" width="{36}" height="16" rx="3" class="f-card" stroke="var(--line)"/>')
        b.append(text(124, y + 14, "hello", "mid xs muted"))
        for i in range(n):
            b.append(f'<rect x="{146 + i * 6}" y="{y + 2}" width="5" height="16" fill="{stroke}" fill-opacity="0.8"/>')
    b.append(text(20, 118, "HTTP/2: one connection; the frames of three responses, in the order they really arrived", "xs b"))
    b.append(f'<rect x="106" y="128" width="36" height="16" rx="3" class="f-card" stroke="var(--line)"/>')
    b.append(text(124, 140, "hello", "mid xs muted"))
    for i, sid in enumerate(real):
        cls, stroke = STREAM_COL[sid]
        b.append(f'<rect x="{146 + i * 5.6:.1f}" y="128" width="4.8" height="16" fill="{stroke}" fill-opacity="0.8"/>')
    for k, (sid, label) in enumerate([("1", "stream 1: /wiki/HTTP/2"), ("3", "stream 3: /wiki/HTTP/3"), ("5", "stream 5: /wiki/QUIC")]):
        cls, stroke = STREAM_COL[sid]
        b.append(f'<rect x="{146 + k * 180}" y="158" width="12" height="12" fill="{stroke}" fill-opacity="0.8"/>')
        b.append(text(164 + k * 180, 169, label, "xs"))
    svg = fig("".join(b), 720, 182, "HTTP/1.1 uses a separate connection per request in parallel; HTTP/2 interleaves the frames of several responses on one connection",
              "Three Wikipedia pages at once. With HTTP/1.1, each needs its own connection (and handshake). With HTTP/2, they share one: this is the real order of the DATA frames from <code>h2client.py en.wikipedia.org /wiki/HTTP/2 /wiki/HTTP/3 /wiki/QUIC</code>. The QUIC page was ready first; then the server let the three take turns.")
    (OUT / "ch33-multiplex.svg").write_text(svg)


# ---------------------------------------------------------------- handshakes compared, with real timings

def handshakes():
    b = []
    rows = [("TCP + TLS 1.3 (HTTP/1.1, HTTP/2)", [("TCP", 1, "t-blue", "var(--blue)"), ("TLS", 1, "t-purple", "var(--purple)"),
                                                ("request → response", 1, "t-green", "var(--green)")], "first byte ≈ 455 ms"),
            ("QUIC (HTTP/3)", [("QUIC + TLS", 1, "t-orange", "var(--orange)"), ("request → response", 1, "t-green", "var(--green)")], "first byte ≈ 350 ms"),
            ("QUIC, returning, with 0-RTT", [("hello + request → response", 1, "t-green", "var(--green)")], "one round trip in all")]
    unit = 150
    for r, (label, parts, result) in enumerate(rows):
        y = 34 + r * 58
        b.append(text(20, y - 6, label, "xs b"))
        x = 20
        for name, n, cls, stroke in parts:
            b.append(box(x, y, n * unit - 4, 30, name, cls, stroke))
            x += n * unit
        b.append(text(x + 10, y + 20, result, "sm b"))
    for k in range(4):
        b.append(f'<line x1="{20 + k * unit}" y1="16" x2="{20 + k * unit}" y2="196" class="grid" stroke-dasharray="3 4"/>')
        b.append(text(20 + k * unit, 210, f"{k} RTT", "mid xs muted"))
    svg = fig("".join(b), 720, 222, "Round trips before the first byte of the response: three with TCP and TLS, two with QUIC, one with QUIC 0-RTT",
              "Round trips before the answer starts. The timings are real: <code>curl</code> from Grandpa’s Pi to quic.nginx.org, 175 ms away, over HTTP/2 and HTTP/3.")
    (OUT / "ch33-handshakes.svg").write_text(svg)


# ---------------------------------------------------------------- what the network can see

def visible():
    b = [text(20, 22, "A TCP segment carrying TLS: what every router on the way can read (and change)", "xs b")]
    tcp = [("IP", 50, "f-card", "var(--line)"), ("ports", 60, "t-yellow", "var(--yellow)"), ("seq", 50, "t-yellow", "var(--yellow)"),
           ("ack", 50, "t-yellow", "var(--yellow)"), ("flags", 50, "t-yellow", "var(--yellow)"), ("window", 60, "t-yellow", "var(--yellow)"),
           ("TLS header", 80, "t-yellow", "var(--yellow)"), ("🔒 encrypted data", 270, "t-green", "var(--green)")]
    x = 20
    for name, w, cls, stroke in tcp:
        b.append(box(x, 32, w - 3, 30, name, cls, stroke))
        x += w
    b.append(text(20, 90, "A QUIC packet: almost everything is encrypted, even the packet number and the acknowledgements", "xs b"))
    quic = [("IP", 50, "f-card", "var(--line)"), ("UDP", 50, "f-card", "var(--line)"), ("flags", 44, "t-yellow", "var(--yellow)"),
            ("connection ID", 110, "t-yellow", "var(--yellow)"), ("🔒 #", 36, "t-green", "var(--green)"),
            ("🔒 frames: STREAM, ACK, … (and the rest of the flags)", 380, "t-green", "var(--green)")]
    x = 20
    for name, w, cls, stroke in quic:
        b.append(box(x, 100, w - 3, 30, name, cls, stroke))
        x += w
    b.append(text(20, 160, "Readable parts are yellow. A middlebox can’t read a QUIC connection’s packet numbers or acknowledgements, so it can’t", "xs"))
    b.append(text(20, 177, "meddle with them, or come to depend on them, and QUIC can keep changing without breaking. Only the connection ID", "xs"))
    b.append(text(20, 194, "stays visible, so that load balancers (Chapter 34) can send each packet to the right server.", "xs"))
    svg = fig("".join(b), 720, 206, "Comparison of visible header fields in a TCP segment carrying TLS and in a QUIC packet",
              "What the network sees.")
    (OUT / "ch33-visible.svg").write_text(svg)


# ---------------------------------------------------------------- connection migration

def migration():
    P, S = "Grandpa’s phone", "the server"
    seq = Seq([(P, 150, None), (S, 570, None)], top=40, scale=30, head=False)
    seq.msg(P, S, 0.3, 1.1, "from 192.168.1.23:51000", "navy", step="1", sub="on the garden Wi-Fi · connection ID 3f9a…")
    seq.msg(S, P, 1.5, 2.3, "video…", "green", step="1")
    seq.note(P, 3.1, "walks out of Wi-Fi range: mobile data, new address", step="2", cls="f-orange")
    seq.msg(P, S, 3.8, 4.6, "from 10.64.3.7:40122", "navy", step="3", sub="same connection ID 3f9a…")
    seq.msg(S, P, 5.1, 5.9, "PATH_CHALLENGE 8e21…", "purple", step="4")
    seq.msg(P, S, 6.3, 7.1, "PATH_RESPONSE 8e21…", "navy", step="4")
    seq.msg(S, P, 7.6, 8.4, "video continues", "green", step="5")
    body, bottom = seq.render(20)
    steps = ["A TCP connection is named by four numbers: both addresses and both ports (Chapter 12). A QUIC connection is named by its <strong>connection ID</strong> instead.",
             "Grandpa walks to the bottom of the garden, out of range of the Wi-Fi, and his phone switches to mobile data: a new IP address and port. Every TCP connection breaks, and must start again from a new handshake.",
             "His QUIC connection just carries on: the next packet comes from the new address, but carries the same connection ID (in real life, a fresh one from a list agreed earlier, so that Eve can’t link the two paths).",
             "The server checks that the new address is real before sending much to it: an 8-byte random challenge, which must come back.",
             "Nothing was lost, and no handshake repeated. This is called <strong>connection migration</strong>."]
    svg = fig(body, 720, bottom, "A QUIC connection surviving a change of address from Wi-Fi to mobile data, using the connection ID and a path challenge",
              "Changing networks without dropping the connection.", steps)
    (OUT / "ch33-migration.svg").write_text(svg)


if __name__ == "__main__":
    stacks()
    frame()
    multiplex()
    handshakes()
    visible()
    migration()
    print("wrote ch33 figures")
