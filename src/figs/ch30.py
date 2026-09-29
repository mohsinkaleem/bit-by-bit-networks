#!/usr/bin/env python3
"""Generate chapter 30 figures.  python3 src/figs/ch30.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- one connection or many

def keepalive():
    b = [text(180, 22, "a new connection for each request", "mid sm b"), text(540, 22, "one connection, kept open", "mid sm b")]

    def lane(x0, items, y0=40):
        out = [f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 + 250}" class="line s-muted" stroke-width="1.5" stroke-dasharray="2 5"/>',
               f'<line x1="{x0 + 200}" y1="{y0}" x2="{x0 + 200}" y2="{y0 + 250}" class="line s-muted" stroke-width="1.5" stroke-dasharray="2 5"/>',
               text(x0, y0 - 4, "browser", "mid xs muted"), text(x0 + 200, y0 - 4, "server", "mid xs muted")]
        y = y0 + 8
        for kind, label in items:
            h = {"tcp": 14, "tls": 22, "req": 14}[kind]
            cls = {"tcp": "s-orange", "tls": "s-purple", "req": "s-green"}[kind]
            out.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + 200}" y2="{y + h / 2}" class="line {cls}" stroke-width="2"/>')
            out.append(f'<line x1="{x0 + 200}" y1="{y + h / 2}" x2="{x0}" y2="{y + h}" class="line {cls}" stroke-width="2"/>')
            out.append(text(x0 + 208 if x0 > 300 else x0 - 8, y + h / 2 + 4, label, "xs" + ("" if x0 > 300 else " end")))
            y += h + 3
        return "".join(out), y
    many = []
    for i in range(5):
        many += [("tcp", "TCP handshake" if i == 0 else ""), ("tls", "TLS handshake" if i == 0 else ""), ("req", f"request {i + 1}")]
    body, yend = lane(80, many)
    b.append(body)
    one = [("tcp", "TCP handshake"), ("tls", "TLS handshake")] + [("req", f"request {i + 1}") for i in range(5)]
    body2, yend2 = lane(440, one)
    b.append(body2)
    b.append(text(180, 312, "858 ms", "mid lg b f-red"))
    b.append(text(540, 312, "262 ms", "mid lg b f-green"))
    b.append(text(360, 334, "Real timings: five requests for https://example.org/ from Bob’s MacBook (labs/ch30/httpclient.py keepalive)", "mid xs muted"))
    svg = fig("".join(b), 720, 344, "Two timelines: five requests each needing their own TCP and TLS handshakes, versus five requests on one connection",
              "Every new HTTPS connection costs round trips before the first byte of the request: one for TCP (Chapter 27), and one or more for TLS (Chapter 32). Keeping it open saves them for every request after the first.")
    (OUT / "ch30-keepalive.svg").write_text(svg)


# ---------------------------------------------------------------- a chain of redirects

def redirects():
    hops = [("http://bbc.co.uk/", "301", "Location: https://bbc.co.uk/", "t-orange", "var(--orange)"),
            ("https://bbc.co.uk/", "301", "Location: https://www.bbc.co.uk/", "t-orange", "var(--orange)"),
            ("https://www.bbc.co.uk/", "200", "the page", "t-green", "var(--green)")]
    b = []
    for i, (url, code, what, cls, stroke) in enumerate(hops):
        x = 20 + i * 240
        b.append(f'<rect x="{x}" y="30" width="200" height="70" rx="10" class="{cls}" stroke="{stroke}" stroke-width="1.8"/>')
        b.append(text(x + 100, 52, url, "mid mono xs b"))
        b.append(text(x + 100, 72, code + (" Moved Permanently" if code == "301" else " OK"), "mid xs b"))
        b.append(text(x + 100, 90, what, "mid mono xs"))
        if i < 2:
            b.append(f'<path d="M{x + 204},65 L{x + 236},65" class="line" stroke-width="2.5" marker-end="url(#ah-ink)"/>')
    b.append(text(20, 130, "1. Plain http:// to https://, so everything after this is encrypted.", "xs"))
    b.append(text(20, 148, "2. The bare name to the www one: the BBC’s website lives at a single name.", "xs"))
    b.append(text(20, 166, "Both HTTPS answers also say Strict-Transport-Security: max-age=31536000; preload, which tells the browser:", "xs"))
    b.append(text(20, 184, "“for the next year, never even try http:// for this site”. Then step 1 never happens again.", "xs b"))
    svg = fig("".join(b), 720, 196, "A chain of two real redirects from http://bbc.co.uk/ to https://www.bbc.co.uk/",
              "A real chain of redirects, from <code>httpclient.py redirects http://bbc.co.uk/</code>.")
    (OUT / "ch30-redirects.svg").write_text(svg)


# ---------------------------------------------------------------- a cookie, taken apart

def cookie():
    parts = [("AEC=Aaa9EJpU_M6UK…", "the name and value: a random identifier", "t-yellow", "var(--yellow)"),
             ("expires=Sat, 27-Mar-2027", "keep it for six months (or: Max-Age=seconds)", "f-card", "var(--line)"),
             ("path=/; domain=.google.com", "send it back for every page on google.com and its subdomains", "f-card", "var(--line)"),
             ("Secure", "only ever send it over HTTPS", "t-green", "var(--green)"),
             ("HttpOnly", "the page’s JavaScript can’t read it, so a malicious script can’t steal it", "t-green", "var(--green)"),
             ("SameSite=lax", "don’t send it when another site sends you here with a form, or loads it in a frame", "t-green", "var(--green)")]
    b = [text(14, 22, "Set-Cookie:", "mono sm b")]
    y = 36
    for i, (p, meaning, cls, stroke) in enumerate(parts):
        w = 16 + 7.3 * len(p)
        b.append(f'<rect x="20" y="{y}" width="{w:g}" height="24" rx="5" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(text(28, y + 16, p, "mono xs b"))
        b.append(text(260, y + 16, meaning, "xs"))
        b.append(f'<line x1="{20 + w + 4:g}" y1="{y + 12}" x2="252" y2="{y + 12}" class="line s-line" stroke-width="1"/>')
        y += 32
    svg = fig("".join(b), 720, y + 6, "A real Set-Cookie header from google.com with each attribute explained",
              "One of the cookies <code>www.google.com</code> set on a first visit (its value shortened). The green attributes are all about security.")
    (OUT / "ch30-cookie.svg").write_text(svg)


if __name__ == "__main__":
    keepalive()
    redirects()
    cookie()
    print("wrote ch30 figures")
