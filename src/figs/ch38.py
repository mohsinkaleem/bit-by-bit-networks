#!/usr/bin/env python3
"""Generate chapter 38 figures.  python3 src/figs/ch38.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- the method: bottom up

def method():
    rows = [("the web page, or the app", "curl -v https://example.org/ · openssl s_client", "30, 32, 33", "t-green", "var(--green)"),
            ("the port", "nc -vz example.org 443 · ss -tn", "26, 27", "t-blue", "var(--blue)"),
            ("names", "dig example.org · dig @1.1.1.1 · dig +tcp", "29", "t-purple", "var(--purple)"),
            ("the internet, by address", "ping 1.1.1.1 · traceroute · mtr · tracepath", "21, 23, 24", "t-orange", "var(--orange)"),
            ("the router", "ping 192.168.1.1 · arp -a / ip neigh", "21, 22", "t-yellow", "var(--yellow)"),
            ("an address, and a route", "ifconfig / ip addr · route get / ip route", "20, 22", "t-teal", "var(--teal)"),
            ("the link itself", "is it connected? Wi-Fi signal · cable light", "17, 18, 19", "f-card", "var(--line)")]
    b = []
    n = len(rows)
    for i, (what, tools, chs, cls, stroke) in enumerate(rows):
        y = 16 + i * 40
        b.append(f'<rect x="60" y="{y}" width="600" height="34" rx="7" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(text(74, y + 22, what, "sm b"))
        b.append(text(290, y + 22, tools, "xs mono"))
        b.append(text(650, y + 22, f"ch. {chs}", "end xs muted"))
        b.append(text(40, y + 22, str(n - i), "mid sm b muted"))
    b.append(f'<path d="M30,{16 + n * 40 - 10} L30,26" class="line s-orange" stroke-width="3" marker-end="url(#ah-orange)"/>')
    b.append(text(360, 16 + n * 40 + 16, "Start at the bottom, and stop at the first thing that fails: everything above it will fail too.", "mid xs b"))
    svg = fig("".join(b), 720, 16 + n * 40 + 28, "The troubleshooting ladder: from the link, through addresses, the router, the internet, names and ports, up to the application, with a tool for each",
              "The detective’s ladder. Each rung depends on the ones below it, so a failure low down makes everything above look broken too.")
    (OUT / "ch38-method.svg").write_text(svg)


# ---------------------------------------------------------------- the example.com case

def dnstrace():
    hops = ["192.168.1.1", "(silent)", "203.0.113.9", "(silent)", "142.250.172.12", "192.178.121.31", "142.251.55.41", "8.8.8.8"]
    org = ["exp", "sil", "exp", "sil", "exp", "exp", "exp", "ans"]
    com = ["exp", "sil", "sil", "sil", "sil", "sil", "sil", "sil"]
    b = [text(20, 22, "A DNS question, sent with a time-to-live of 1, 2, 3…, from Grandpa’s Pi to 8.8.8.8", "xs b")]
    x0, w = 150, 70
    for i, h in enumerate(hops):
        x = x0 + i * w
        b.append(text(x + w / 2, 44, f"hop {i + 1}", "mid xs b"))
        b.append(text(x + w / 2, 58 + (i % 2) * 14, h, "mid xs mono muted" if "(" in h else "mid xs mono"))
    for r, (label, row) in enumerate((("example.org", org), ("example.com", com))):
        y = 90 + r * 56
        b.append(text(20, y + 24, label, "sm b"))
        for i, v in enumerate(row):
            x = x0 + i * w + 8
            cls, stroke, t = {"exp": ("t-green", "var(--green)", "expired"), "ans": ("t-blue", "var(--blue)", "ANSWER"),
                              "sil": ("f-surface", "var(--line)", "…")}[v]
            b.append(f'<rect x="{x}" y="{y}" width="{w - 16}" height="40" rx="6" class="{cls}" stroke="{stroke}" stroke-width="1.4"/>')
            b.append(text(x + (w - 16) / 2, y + 25, t, "mid xs b"))
    b.append('<path d="M158,206 L158,212 L290,212 L290,206" class="line s-red" stroke-width="2"/>')
    b.append(text(224, 228, "it dies somewhere in here", "mid xs b f-red"))
    b.append(text(20, 252, "Hop 2 never answers anyone (plenty of routers don’t), but hop 3 does, for example.org. For example.com, nothing ever", "xs"))
    b.append(text(20, 268, "comes back from hop 3 or beyond: the question never gets there. So it’s dropped by the home router, or by the internet", "xs"))
    b.append(text(20, 284, "provider’s first box: that’s where to look next.", "xs"))
    svg = fig("".join(b), 720, 296, "A traceroute of DNS questions: for example.org the question reaches Google's server; for example.com it vanishes after the first hop",
              "A real mystery from Bob’s home network, narrowed down with <code>dnstrace.py</code>. (The provider’s router address is replaced with a documentation address.)")
    (OUT / "ch38-dnstrace.svg").write_text(svg)


# ---------------------------------------------------------------- the path MTU black hole

def blackhole():
    nodes = [(70, "patient", "10.38.0.2"), (240, "r1", ""), (480, "r2", ""), (650, "server", "10.38.2.2")]
    b = []
    for x, name, ip in nodes:
        b.append(f'<rect x="{x - 50}" y="30" width="100" height="44" rx="8" class="f-card" stroke="var(--line)" stroke-width="1.6"/>')
        b.append(text(x, 50, name, "mid sm b"))
        if ip:
            b.append(text(x, 66, ip, "mid xs mono muted"))
    b.append('<path d="M120,52 L190,52" class="line s-ink" stroke-width="3"/>')
    b.append(text(155, 44, "1500", "mid xs muted"))
    b.append('<path d="M290,52 L430,52" class="line s-orange" stroke-width="7"/>')
    b.append(text(360, 42, "only 1,400-byte packets fit", "mid xs b f-orange"))
    b.append('<path d="M530,52 L600,52" class="line s-ink" stroke-width="3"/>')
    b.append(text(565, 44, "1500", "mid xs muted"))
    b.append('<g data-show="1">' + '<path d="M600,98 L100,98" class="line s-green" stroke-width="2" marker-end="url(#ah-green)"/>'
             + text(360, 92, "small packets: the request, ACKs, small.txt (6 bytes)", "mid xs b f-green") + "</g>")
    b.append('<g data-show="2-3">' + '<path d="M600,134 L500,134" class="line s-blue" stroke-width="4" marker-end="url(#ah-blue)"/>'
             + text(640, 128, "1,500 bytes, DF", "mid xs b f-blue") + '<path d="M470,124 l20,20 M490,124 l-20,20" class="line s-red" stroke-width="3"/>' + "</g>")
    b.append('<g data-show="=2">' + '<path d="M480,160 L600,160" class="line s-purple" stroke-width="2" marker-end="url(#ah-purple)"/>'
             + text(540, 178, "ICMP: too big, use 1400", "mid xs b f-purple") + text(360, 210, "The server resends in 1,400-byte packets, and everything works.", "mid sm b f-green") + "</g>")
    b.append('<g data-show="=3">' + '<path d="M480,160 L530,160" class="line s-purple dash" stroke-width="2"/>'
             + '<path d="M530,152 l14,14 M544,152 l-14,14" class="line s-red" stroke-width="3"/>'
             + text(560, 178, "ICMP dropped by a firewall", "mid xs b f-red")
             + text(360, 210, "The server never hears why. It resends the same big packet, again and again: 0 bytes arrive.", "mid sm b f-red") + "</g>")
    steps = ["Small packets cross the narrow link without trouble. The connection opens, the request goes out, and a tiny file comes back.",
             "A big packet with Don’t Fragment set (TCP always sets it) doesn’t fit. The router drops it, and sends back an ICMP “fragmentation needed” message, with the size that would fit. The sender shrinks its packets: that’s <strong>path MTU discovery</strong>.",
             "But if a firewall on the way throws away ICMP (“it’s just ping, isn’t it?”), the sender never finds out. It waits, resends the same packet, and waits again. Small things work; big things hang for ever. That’s a <strong>black hole</strong>."]
    svg = fig("".join(b), 720, 226, "A path MTU black hole: a narrow link in the middle, big packets dropped, and the ICMP message that would explain it dropped too",
              "The path MTU black hole, as <code>breakit.sh blackhole</code> builds it.", steps)
    (OUT / "ch38-blackhole.svg").write_text(svg)


if __name__ == "__main__":
    method()
    dnstrace()
    blackhole()
    print("wrote ch38 figures")
