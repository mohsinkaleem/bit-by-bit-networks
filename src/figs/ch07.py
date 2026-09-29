#!/usr/bin/env python3
"""Generate chapter 7 figures.  python3 src/figs/ch07.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


def static_dynamic():
    body = []
    for y, title, middle, note in ((20, "A static page", "read a file", "same answer every time"),
                                   (160, "A dynamic page", "run a program", "a fresh answer every time")):
        body.append(text(20, y + 16, title, "slab b"))
        body.append(f'<rect x="20" y="{y + 30}" width="150" height="70" rx="10" class="t-red" stroke="var(--line)"/>')
        body.append(text(95, y + 60, "request", "mid b"))
        body.append(text(95, y + 80, "GET /time", "mid mono sm"))
        body.append(f'<path d="M174,{y + 65} L236,{y + 65}" class="line" marker-end="url(#ah-ink)"/>')
        body.append(f'<rect x="240" y="{y + 30}" width="220" height="70" rx="10" class="t-teal" stroke="var(--line)"/>')
        body.append(text(350, y + 60, "server", "mid b"))
        body.append(text(350, y + 80, middle, "mid sm"))
        if "file" in middle:
            body.append(f'<use href="#disk" x="330" y="{y + 102}" width="40" height="40"/>')
        else:
            body.append(f'<g transform="translate(330,{y + 104})"><rect width="40" height="34" rx="4" fill="#1d2b45"/>'
                        f'<text x="20" y="22" class="mid mono xs" fill="#7dffa8">f(x)</text></g>')
        body.append(f'<path d="M464,{y + 65} L526,{y + 65}" class="line" marker-end="url(#ah-ink)"/>')
        body.append(f'<rect x="530" y="{y + 30}" width="170" height="70" rx="10" class="t-yellow" stroke="var(--line)"/>')
        body.append(text(615, y + 60, "document", "mid b"))
        body.append(text(615, y + 80, note, "mid hand"))
    svg = fig("".join(body), 720, 300, "A static page is read from disk; a dynamic page is produced by running a program",
              "From the browser’s side the two look identical. Only the server knows the difference.")
    (OUT / "ch07-static-dynamic.svg").write_text(svg)


def query():
    parts = [("/dice", "t-yellow", "path"), ("?", "f-none", ""), ("sides=20", "t-green", "a parameter"),
             ("&", "f-none", ""), ("n=3", "t-green", "another")]
    body = []
    x = 110
    for label, cls, name in parts:
        w = 13 * len(label) + 18
        body.append(f'<rect x="{x}" y="30" width="{w}" height="40" rx="6" class="{cls}" stroke="var(--line)"/>')
        body.append(text(x + w / 2, 57, label.replace("&", "&amp;"), "mid mono xl b"))
        if name:
            body.append(f'<path d="M{x + w / 2},72 l0,14" class="line thin s-muted"/>')
            body.append(text(x + w / 2, 104, name, "mid hand"))
        x += w + 3
    body.append(text(520, 57, "→  { sides: 20, n: 3 }", "mono b"))
    svg = fig("".join(body), 720, 120, "A path followed by a question mark and two name=value parameters",
              "After the ?, name=value pairs, separated by &amp;.")
    (OUT / "ch07-query.svg").write_text(svg)


def cookies():
    s = Seq([("Alice’s browser", 170, "alice"), ("Bob’s server", 470, "bob")], top=86, scale=30)
    s.msg("Alice’s browser", "Bob’s server", 0, 1, "GET /hello", step="1")
    s.note("Bob’s server", 1.2, "never seen you: you’re #7", step="1", side="right")
    s.msg("Bob’s server", "Alice’s browser", 1.6, 2.6, "200 OK  Set-Cookie: visitor=7", "green", step="1")
    s.note("Alice’s browser", 2.9, "remembers visitor=7 for bob", step="2", side="right")
    s.msg("Alice’s browser", "Bob’s server", 3.6, 4.6, "GET /hello  Cookie: visitor=7", step="2")
    s.note("Bob’s server", 4.8, "#7! visit number 2", step="2", side="right")
    s.msg("Bob’s server", "Alice’s browser", 5.2, 6.2, "200 OK “Welcome back!”", "green", step="2")
    s.msg("Alice’s browser", "Bob’s server", 7.2, 8.2, "GET /weather  Cookie: visitor=7", step="3")
    s.note("Alice’s browser", 8.6, "…the ticket goes along with every request to bob", step="3", side="right")
    body, h = s.render()
    steps = ["Alice’s first visit. The server has never seen her, so it picks a new number and sends it back in a <code>Set-Cookie</code> header.",
             "Her browser stores the cookie and, from then on, sends it back in a <code>Cookie</code> header. Now the server can tell her apart from everyone else.",
             "It goes along with <em>every</em> request to Bob’s server, not just to that page, until it expires."]
    svg = fig(body, 720, h, "Sequence diagram: a server hands out a cookie and the browser returns it on later requests",
              "A cookie is a ticket the server hands you, and you show it every time you come back.", steps)
    (OUT / "ch07-cookies.svg").write_text(svg)


def post_redirect():
    s = Seq([("Alice’s browser", 190, "alice"), ("Carol’s guestbook", 530, "carol")], top=86, scale=30)
    s.msg("Alice’s browser", "Carol’s guestbook", 0, 1, "POST /guestbook", sub="name=Alice&amp;message=Hi")
    s.note("Carol’s guestbook", 1.25, "adds the entry", side="right")
    s.msg("Carol’s guestbook", "Alice’s browser", 1.6, 2.6, "303 See Other → /guestbook", "orange")
    s.msg("Alice’s browser", "Carol’s guestbook", 3.2, 4.2, "GET /guestbook")
    s.msg("Carol’s guestbook", "Alice’s browser", 4.5, 5.5, "200 OK (the updated page)", "green")
    s.note("Alice’s browser", 6.1, "if Alice reloads now, it re-sends the GET, not the POST", side="right", cls="f-green")
    body, h = s.render()
    svg = fig(body, 720, h, "Post, then redirect, then get",
              "Post, redirect, get: reloading the page can’t sign the guestbook twice.")
    (OUT / "ch07-prg.svg").write_text(svg)


def chunked():
    toks = [("51", "t-blue"), ("81 bytes of page…", "t-yellow"), ("b", "t-blue"), ("<p>5…</p>", "t-yellow"),
            ("b", "t-blue"), ("<p>4…</p>", "t-yellow"), ("…", "f-none"), ("0", "t-red")]
    body = []
    x = 20
    for label, cls in toks:
        w = 11 * len(label) + 20
        body.append(f'<rect x="{x}" y="30" width="{w}" height="40" rx="6" class="{cls}" stroke="var(--line)"/>')
        body.append(text(x + w / 2, 56, label.replace("<", "&lt;").replace(">", "&gt;"), "mid mono b"))
        x += w + 4
    body.append(text(40, 100, "each chunk starts with its own length (in hex)…", "hand f-blue"))
    body.append(text(700, 100, "…and a length of 0 means “that’s all”", "end hand f-red"))
    svg = fig("".join(body), 720, 116, "A body sent as chunks, each prefixed with its length, ending with a zero-length chunk",
              "Chunked sending: length-first framing, one piece at a time.")
    (OUT / "ch07-chunked.svg").write_text(svg)


if __name__ == "__main__":
    static_dynamic()
    query()
    cookies()
    post_redirect()
    chunked()
    print("wrote ch07 figures")
