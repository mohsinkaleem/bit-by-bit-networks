#!/usr/bin/env python3
"""Chapter 7 lab: a web server that writes its pages on the spot.

    python3 dynserver.py        then open http://localhost:7007/ (or use curl)

It speaks real HTTP (Chapter 6 showed that our TTP was HTTP in disguise), built
directly on a socket so you can see every step. Pages:

    /                     a menu
    /time                 the current time: different on every request
    /dice?sides=20&n=3    roll some dice, using query parameters
    /weather?unit=F       Bob's (imaginary) backyard thermometer
    /hello                remembers you, using a cookie
    /guestbook            read it (GET) or sign it (POST)
    /countdown            sent in chunks, before the server knows how long it will be
    /echo                 shows exactly what your browser sent
"""
import html
import json
import os
import random
import socket
import threading
import time
import urllib.parse
from datetime import datetime

PORT = 7007
HERE = os.path.dirname(os.path.abspath(__file__))
GUESTBOOK = os.path.join(HERE, "guestbook.json")
ESCAPE_GUESTBOOK = True          # set to False to see why escaping matters (see the lab)
REASONS = {200: "OK", 303: "See Other", 400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed"}

visits = {}                      # visitor number -> how many times we've seen them
lock = threading.Lock()


# ------------------------------------------------------------------ reading a request

class Request:
    pass


# --8<-- [start:parse]
def read_request(conn):
    raw = b""
    while b"\r\n\r\n" not in raw:
        more = conn.recv(4096)
        if not more:
            return None
        raw += more
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    req = Request()
    req.method, target, req.version = lines[0].split(" ", 2)
    req.headers = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        req.headers[name.strip().lower()] = value.strip()
    length = int(req.headers.get("content-length", 0))
    while len(body) < length:                          # the body may still be arriving
        body += conn.recv(4096)
    req.body = body
    url = urllib.parse.urlsplit(target)                # "/dice?sides=20&n=3"
    req.path = url.path                                # "/dice"
    req.query = dict(urllib.parse.parse_qsl(url.query))   # {"sides": "20", "n": "3"}
    req.cookies = dict(
        c.strip().split("=", 1) for c in req.headers.get("cookie", "").split(";") if "=" in c)
    return req
# --8<-- [end:parse]


# ------------------------------------------------------------------ pages

ROUTES = {}


def route(path):
    def register(fn):
        ROUTES[path] = fn
        return fn
    return register


def page(title, body):
    return f"""<!doctype html><meta charset="utf-8"><title>{title}</title>
<body style="font:18px Georgia;max-width:680px;margin:32px auto;line-height:1.5;padding:0 16px">
<p style="background:#003554;color:#8ab9b5;padding:8px 12px;border-radius:6px">
<a href="/" style="color:#fff">dynserver.py</a> · page written at {datetime.now():%H:%M:%S}</p>
<h1>{title}</h1>{body}</body>""".encode()


@route("/")
def menu(req):
    links = "".join(f'<li><a href="{p}">{p}</a></li>' for p in
                    ["/time", "/dice?sides=20&n=3", "/weather?unit=F", "/hello", "/guestbook", "/countdown", "/echo"])
    return 200, {}, page("Pages that write themselves", f"<ul>{links}</ul>")


# --8<-- [start:dynamic]
@route("/time")
def the_time(req):
    return 200, {}, page("What time is it?", f"<p>It is <b>{datetime.now():%H:%M:%S}</b>. Reload me!</p>")


@route("/dice")
def dice(req):
    try:
        sides = int(req.query.get("sides", "6"))
        n = int(req.query.get("n", "1"))
    except ValueError:
        return 400, {}, page("Bad dice", "<p>sides and n must be whole numbers</p>")
    if not (2 <= sides <= 1000 and 1 <= n <= 20):       # never trust what's in a URL
        return 400, {}, page("Bad dice", "<p>try 2–1000 sides and 1–20 dice</p>")
    rolls = [random.randint(1, sides) for _ in range(n)]
    return 200, {}, page(f"{n} × d{sides}", f"<p style='font-size:40px'>{' '.join(map(str, rolls))}</p>")
# --8<-- [end:dynamic]


@route("/weather")
def weather(req):
    celsius = 17 + 3 * random.random()
    if req.query.get("unit", "C").upper() == "F":
        reading = f"{celsius * 9 / 5 + 32:.1f} °F"
    else:
        reading = f"{celsius:.1f} °C"
    return 200, {}, page("Bob’s backyard", f"<p>The thermometer says <b>{reading}</b>. "
                                           f"Try <a href='?unit=C'>?unit=C</a> or <a href='?unit=F'>?unit=F</a>.</p>")


# --8<-- [start:cookie]
@route("/hello")
def hello(req):
    extra = {}
    with lock:
        visitor = req.cookies.get("visitor")
        if visitor not in visits:                       # a stranger: hand out a new ticket
            visitor = str(len(visits) + 1)
            visits[visitor] = 0
            extra["Set-Cookie"] = f"visitor={visitor}; Path=/; Max-Age=86400"
        visits[visitor] += 1
        count = visits[visitor]
    if count == 1:
        msg = f"Hello, stranger! I’ll call you <b>visitor #{visitor}</b>. Reload the page."
    else:
        msg = f"Welcome back, <b>visitor #{visitor}</b>. This is visit number <b>{count}</b>."
    return 200, extra, page("Hello!", f"<p>{msg}</p>")
# --8<-- [end:cookie]


# --8<-- [start:guestbook]
@route("/guestbook")
def guestbook(req):
    entries = json.load(open(GUESTBOOK)) if os.path.exists(GUESTBOOK) else []
    if req.method == "POST":
        form = dict(urllib.parse.parse_qsl(req.body.decode()))       # "name=Alice&message=Hi+Carol!"
        name, message = form.get("name", "").strip()[:40], form.get("message", "").strip()[:500]
        if name and message:
            entries.append({"name": name, "message": message, "when": f"{datetime.now():%d %b %H:%M}"})
            json.dump(entries, open(GUESTBOOK, "w"), indent=1)
        return 303, {"Location": "/guestbook"}, b""                 # "now go and GET the guestbook"
    if req.method != "GET":
        return 405, {}, page("Nope", "<p>only GET and POST here</p>")
    show = html.escape if ESCAPE_GUESTBOOK else (lambda s: s)
    items = "".join(f"<li><b>{show(e['name'])}</b> ({e['when']}): {show(e['message'])}</li>" for e in entries)
    form = ("<form method='post' action='/guestbook'><p><input name='name' placeholder='your name'> "
            "<input name='message' placeholder='your message' size='30'> <button>Sign</button></p></form>")
    return 200, {}, page("Carol’s guestbook", form + f"<ul>{items or '<li>(nobody yet)</li>'}</ul>")
# --8<-- [end:guestbook]


@route("/countdown")
def countdown(req):
    def chunks():                                       # a generator: the page is made as we go
        yield b"<!doctype html><meta charset='utf-8'><body style='font:24px Georgia;margin:40px'>"
        for n in range(5, 0, -1):
            yield f"<p>{n}…</p>".encode()
            time.sleep(1)
        yield "<p>🚀 liftoff! (this page arrived in chunks)</p>".encode()
    return 200, {}, chunks()


@route("/echo")
def echo(req):
    head = f"{req.method} {req.path} {req.version}\n" + "\n".join(f"{k}: {v}" for k, v in req.headers.items())
    body = html.escape(req.body.decode(errors="replace"))
    return 200, {}, page("What your browser sent", f"<pre style='white-space:pre-wrap'>{html.escape(head)}\n\n{body}</pre>")


# ------------------------------------------------------------------ sending a response

# --8<-- [start:send]
def send(conn, status, headers, body):
    lines = [f"HTTP/1.1 {status} {REASONS[status]}", "Connection: close"]
    if "Location" not in headers:
        lines.append("Content-Type: text/html; charset=utf-8")
    lines += [f"{k}: {v}" for k, v in headers.items()]
    if isinstance(body, bytes):
        lines.append(f"Content-Length: {len(body)}")
        conn.sendall(("\r\n".join(lines) + "\r\n\r\n").encode() + body)
        return
    # we don't know the length yet: send it in chunks, each with its own length (in hex)
    lines.append("Transfer-Encoding: chunked")
    conn.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
    for piece in body:
        conn.sendall(f"{len(piece):x}\r\n".encode() + piece + b"\r\n")
    conn.sendall(b"0\r\n\r\n")                           # a zero-length chunk means "the end"
# --8<-- [end:send]


def handle(conn):
    with conn:
        req = read_request(conn)
        if req is None:
            return
        fn = ROUTES.get(req.path)
        status, headers, body = fn(req) if fn else (404, {}, page("Not found", "<p>no such page</p>"))
        who = f"visitor #{req.cookies['visitor']}" if "visitor" in req.cookies else ""
        print(f"{req.method:4} {req.path:<11} {'?' + urllib.parse.urlencode(req.query) if req.query else '':<18} "
              f"-> {status} {who}", flush=True)
        send(conn, status, headers, body)


def main():
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", PORT))
    listener.listen()
    print(f"open http://localhost:{PORT}/  (Ctrl+C to stop)", flush=True)
    while True:
        conn, _ = listener.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    main()
