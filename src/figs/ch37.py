#!/usr/bin/env python3
"""Generate chapter 37 figures.  python3 src/figs/ch37.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


def box(x, y, w, h, label, cls="f-card", stroke="var(--line)", sub=None):
    out = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="8" class="{cls}" stroke="{stroke}" stroke-width="1.6"/>'
    out += text(x + w / 2, y + h / 2 + (-3 if sub else 4), label, "mid xs b")
    if sub:
        out += text(x + w / 2, y + h / 2 + 12, sub, "mid xs muted")
    return out


# ---------------------------------------------------------------- the map of the journey

def journey():
    stops = [(60, 70, "Bob’s laptop", "URL, HSTS, caches", "6, 30, 32", "t-blue", "var(--blue)"),
             (200, 70, "Wi-Fi", "radio, 802.11 frames", "17, 19", "t-teal", "var(--teal)"),
             (340, 70, "home router", "ARP, DHCP, DNS, NAT", "21, 22, 29", "t-orange", "var(--orange)"),
             (480, 70, "the ISP", "routing, PPPoE, MSS", "20, 23, 27", "t-purple", "var(--purple)"),
             (620, 70, "the internet", "BGP, anycast", "24, 34", "t-yellow", "var(--yellow)"),
             (620, 200, "CDN edge", "TCP or QUIC, TLS, HTTP/2 or 3, cache", "27, 32, 33, 34", "t-green", "var(--green)"),
             (400, 200, "origin server", "only on a cache miss", "30, 34", "f-card", "var(--line)")]
    b = []
    for i, (x, y, name, what, chs, cls, stroke) in enumerate(stops):
        g = box(x - 62, y - 30, 124, 60, name, cls, stroke, what)
        g += text(x, y + 46, f"ch. {chs}", "mid xs muted")
        b.append(f'<g data-show="{i + 1}">{g}</g>')
        if i:
            px, py = stops[i - 1][0], stops[i - 1][1]
            if py == y:
                d = f"M{px + 64 if x > px else px - 64},{y} L{x - 64 if x > px else x + 64},{y}"
            else:
                d = f"M{px},{py + 32} L{x},{y - 32}"
            b.append(f'<g data-show="{i + 1}"><path d="{d}" class="line s-muted" stroke-width="2.4" marker-end="url(#ah-muted)"/></g>')
    steps = ["Before anything touches the network: is <code>example.org</code> an address or a search? Is it on the HSTS list (Chapter 30), so it must be <code>https://</code>? Is the page, or at least its address, already cached?",
             "Every packet leaves as a radio frame (Chapters 17 and 19), after waiting its turn for the air.",
             "The first hop is the router the DHCP server named (Chapter 22). The laptop needs its MAC address (ARP, Chapter 21), usually already known. The router also answers the DNS question, from its cache or by asking further (Chapter 29), and rewrites every packet’s source address with NAT on its way out.",
             "The internet provider’s routers look up each destination in their tables, longest prefix first (Chapters 20 and 23). Here Bob’s own connection is PPPoE, which is why its packets top out at 1,492 bytes (Chapter 27).",
             "Across networks, BGP decides the path (Chapter 24). example.org is announced by Cloudflare from hundreds of places at once, so the nearest one wins: anycast (Chapter 34).",
             "The CDN’s edge server answers the TCP handshake (Chapter 27) or QUIC’s (Chapter 33), proves it’s example.org with TLS (Chapter 32), reads the HTTP/2 request (Chapter 33), and finds the page in its cache (Chapters 30 and 34).",
             "Only on a cache miss does anything travel on to the website’s own server. For example.org, this time, it didn’t."]
    svg = fig("".join(b), 720, 270, "The journey of a web request: laptop, Wi-Fi, home router, internet provider, the internet, a CDN edge, and the origin server",
              "The whole journey, and the chapters that explain each stop.", steps)
    (OUT / "ch37-journey.svg").write_text(svg)


# ---------------------------------------------------------------- the real capture, as a sequence

def timeline():
    P, R, S = "Grandpa’s Pi", "router", "example.org"
    seq = Seq([(P, 110, None), (R, 330, None), (S, 610, None)], top=40, scale=21, head=False)
    seq.msg(P, R, 0.2, 0.9, "ARP: who has 192.168.1.1?", "navy", step="1", sub="0.0 ms")
    seq.msg(R, P, 1.2, 1.9, "ARP: it’s me", "purple", step="1", sub="5.1 ms")
    seq.msg(P, R, 2.4, 3.1, "DNS: A? AAAA? example.org", "navy", step="2", sub="5.1 ms")
    seq.msg(R, P, 3.5, 4.2, "DNS: 172.66.157.237 …", "purple", step="2", sub="42.5 ms")
    seq.msg(P, S, 4.8, 5.8, "SYN", "navy", step="3", sub="42.7 ms", label_at=0.35)
    seq.msg(S, P, 6.1, 7.1, "SYN, ACK", "purple", step="3", sub="80.6 ms", label_at=0.65)
    seq.msg(P, S, 7.5, 8.5, "ACK + ClientHello (1,571 bytes)", "navy", step="4", sub="80.6 – 83.1 ms", label_at=0.4)
    seq.msg(S, P, 8.9, 9.9, "ServerHello, 🔒 certificate, signature, Finished", "purple", step="4", sub="124.9 – 127.9 ms", label_at=0.55)
    seq.msg(P, S, 10.3, 11.3, "🔒 Finished + 🔒 HTTP/2 GET /", "navy", step="5", sub="131.4 – 131.9 ms", label_at=0.4)
    seq.msg(S, P, 11.7, 12.7, "🔒 HEADERS 200 OK, DATA 713 bytes", "green", step="5", sub="171.0 – 174.6 ms", label_at=0.55)
    seq.msg(P, S, 13.1, 14.1, "🔒 GOAWAY, close_notify, FIN", "navy", step="6", sub="174.6 – 175.6 ms", label_at=0.4)
    seq.msg(S, P, 14.5, 15.5, "FIN, ACK", "purple", step="6", sub="211.7 ms", label_at=0.6)
    body, bottom = seq.render(20)
    steps = ["The Pi’s ARP cache was emptied first, so it has to ask for the router’s MAC address: 5 ms over Wi-Fi.",
             "Two DNS questions at once, for an IPv4 and an IPv6 address. The router had to ask upstream: 37 ms. (The Pi has no global IPv6, Chapter 25, so it will use IPv4.)",
             "The TCP handshake to the nearest Cloudflare site: 38 ms, one round trip.",
             "curl’s ClientHello is 1,571 bytes, too big for one TCP segment, because it carries a post-quantum key share as well as an X25519 one (Chapter 42). The server answers with everything at once, the certificate chain encrypted.",
             "One round trip after the ClientHello, the request goes out, in the same breath as the client’s Finished. Forty milliseconds later, the page comes back: 713 bytes, from the CDN’s cache.",
             "curl only wanted one page, so it says goodbye three ways: an HTTP/2 GOAWAY, a TLS close_notify, and a TCP FIN. 175 ms from the first packet to the page."]
    svg = fig(body, 720, bottom, "The real sequence of packets when the Pi fetched example.org: ARP, DNS, TCP handshake, TLS handshake, HTTP/2 request and response, and closing, with times",
              "Everything that happened when the Pi fetched <code>https://example.org/</code> with curl, from a real capture decrypted with its keys.", steps)
    (OUT / "ch37-timeline.svg").write_text(svg)


# ---------------------------------------------------------------- one packet, every layer

def onion():
    layers = [("Ethernet (Wi-Fi) header", 14, "t-teal", "var(--teal)", "19, 18"), ("IPv4 header", 20, "t-yellow", "var(--yellow)", "20"),
              ("TCP header", 32, "t-blue", "var(--blue)", "27"), ("TLS record header", 5, "t-purple", "var(--purple)", "32")]
    inner = [("HTTP/2 preface", 24, "the magic string"), ("SETTINGS", 27, "9 + 18"), ("WINDOW_UPDATE", 13, "9 + 4"),
             ("HEADERS", 37, "9 + 28: GET / and 5 more headers, 127 bytes as text, 28 compressed")]
    b = [text(20, 22, "Frame 23 of the capture: curl’s HTTP/2 request, 189 bytes on the wire", "xs b")]
    y = 34
    x0, x1 = 20, 700
    for i, (name, size, cls, stroke, ch) in enumerate(layers):
        top, bottom = y + i * 30, 290 - i * 8
        b.append(f'<rect x="{x0 + i * 16}" y="{top}" width="{x1 - x0 - i * 32}" height="{bottom - top}" rx="10" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(text(x0 + i * 16 + 12, top + 20, f"{name}: {size} bytes", "xs b"))
        b.append(text(x1 - i * 16 - 12, top + 20, f"ch. {ch}", "end xs muted"))
    y2 = y + 4 * 30 + 6
    b.append(f'<rect x="{x0 + 64}" y="{y2}" width="{x1 - x0 - 128}" height="90" rx="8" class="t-green" stroke="var(--green)" stroke-width="1.5" stroke-dasharray="6 3"/>')
    b.append(text(x0 + 76, y2 + 18, "🔒 encrypted (101 bytes of HTTP/2, + 1 byte of real type):  ch. 33", "xs b"))
    xx = x0 + 80
    for name, size, sub in inner:
        w = max(size * 4.2, 100)
        b.append(f'<rect x="{xx:g}" y="{y2 + 26}" width="{w:g}" height="36" rx="4" class="f-card" stroke="var(--line)"/>')
        b.append(text(xx + w / 2, y2 + 41, name, "mid xs b"))
        b.append(text(xx + w / 2, y2 + 55, f"{size} bytes", "mid xs muted"))
        xx += w + 4
    b.append(text(x0 + 80, y2 + 80, inner[-1][2], "xs muted"))
    b.append(f'<rect x="{xx:g}" y="{y2 + 26}" width="40" height="36" rx="4" class="t-purple" stroke="var(--purple)"/>')
    b.append(text(xx + 20, y2 + 41, "tag", "mid xs b"))
    b.append(text(xx + 20, y2 + 55, "16", "mid xs muted"))
    b.append(text(360, 308, "14 + 20 + 32 + 5 + 101 + 1 + 16 = 189. Everything outside the green box, a router can read.", "mid xs"))
    svg = fig("".join(b), 720, 318, "The nested layers of one real packet: Ethernet, IPv4, TCP, a TLS record, and inside it the encrypted HTTP/2 frames",
              "One packet, every layer: the request itself, from the same capture.")
    (OUT / "ch37-onion.svg").write_text(svg)


if __name__ == "__main__":
    journey()
    timeline()
    onion()
    print("wrote ch37 figures")
