#!/usr/bin/env python3
"""Chapter 6 lab: a web server for the Tangled Text Protocol (TTP)...
and, it turns out, for real web browsers too.

    python3 webserver.py          serve every folder in sites/ on port 7006

Each folder in sites/ is one computer's documents (sites/bob, sites/carol, sites/alice).
A TTP request's Host header says which computer's documents you want.

It also understands real HTTP. Open http://localhost:7006/ in Safari or Chrome and see.
"""
import mimetypes
import os
import re
import socket
import threading

PORT = 7006
SITES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sites")
MOVED = {("bob", "/homework.mu"): "/school/homework.mu"}
REASONS = {200: "OK", 301: "Moved Permanently", 400: "Bad Request", 404: "Not Found"}
mimetypes.add_type("text/markup", ".mu")


def read_head(conn):
    """Read bytes up to the blank line that ends the headers."""
    raw = b""
    while b"\n\n" not in raw.replace(b"\r\n", b"\n"):
        more = conn.recv(1024)
        if not more:
            break
        raw += more
    return raw.decode("utf-8", errors="replace").replace("\r\n", "\n")


# --8<-- [start:handle]
def handle(conn):
    head = read_head(conn)
    lines = head.split("\n")
    try:
        method, path, version = lines[0].split(" ")
    except ValueError:
        return send(conn, "TTP/1", 400, {}, b"bad request line\n")
    headers = {}
    for line in lines[1:]:
        if ": " in line:
            name, value = line.split(": ", 1)
            headers[name.lower()] = value
    real_browser = version.startswith("HTTP/")
    if real_browser:
        host, path = http_route(path)       # see the bottom of this file
    else:
        host = headers.get("host", "bob")

    status, extra, body = find(host, path)
    kind = extra.pop("Type", "text/plain")
    if real_browser and kind == "text/markup":
        body, kind = markup_to_html(body.decode(), host), "text/html; charset=utf-8"
    if real_browser and "Location" in extra:
        extra["Location"] = f"/{host}{extra['Location']}"
    print(f"{'HTTP' if real_browser else 'TTP '} {host:>6} {method} {path:<22} -> {status} {REASONS[status]}",
          flush=True)
    send(conn, "HTTP/1.0" if real_browser else "TTP/1", status, dict(extra, Type=kind), body)


def find(host, path):
    """Work out the reply for one path on one computer: (status, headers, body)."""
    if (host, path) in MOVED:
        return 301, {"Location": MOVED[(host, path)]}, b"moved\n"
    root = os.path.realpath(os.path.join(SITES, host))
    full = os.path.realpath(os.path.join(root, path.lstrip("/")))
    if not full.startswith(root) or not os.path.isdir(root):       # no escaping the site folder
        return 404, {}, b"no such page\n"
    if os.path.isdir(full):
        full = os.path.join(full, "index.mu")
    if not os.path.isfile(full):
        return 404, {}, f"There is no {path} on {host}'s computer.\n".encode()
    with open(full, "rb") as f:
        body = f.read()
    return 200, {"Type": mimetypes.guess_type(full)[0] or "application/octet-stream"}, body


def send(conn, version, status, headers, body):
    if version.startswith("HTTP"):
        names = {"Type": "Content-Type", "Length": "Content-Length"}
        lines = [f"{version} {status} {REASONS[status]}"]
        lines += [f"{names.get(k, k)}: {v}" for k, v in headers.items()]
        lines += [f"Content-Length: {len(body)}", "Connection: close"]
        head = "\r\n".join(lines) + "\r\n\r\n"     # real HTTP ends lines with CR LF
    else:
        lines = [f"{version} {status} {REASONS[status]}"]
        lines += [f"{k}: {v}" for k, v in headers.items()]
        lines += [f"Length: {len(body)}"]
        head = "\n".join(lines) + "\n\n"
    conn.sendall(head.encode() + body)
# --8<-- [end:handle]


# ------------------------------------------------------------------ the real-browser bits
# A real browser always talks to "localhost", so it can't use Host to pick bob or carol.
# Instead we put the computer's name first in the path: /carol/bees.mu

def http_route(path):
    parts = path.split("/", 2)
    if len(parts) > 1 and parts[1] in os.listdir(SITES):
        return parts[1], "/" + (parts[2] if len(parts) > 2 else "")
    return "bob", path if path != "/" else "/index.mu"


def markup_to_html(text, host):
    def url(u):
        if u.startswith("ttp://"):
            return "/" + u[len("ttp://"):]
        if u.startswith("/"):
            return f"/{host}{u}"
        return u
    title = re.search(r"<title>(.*?)</title>", text)
    text = re.sub(r"<title>.*?</title>\n?", "", text)
    text = re.sub(r"<h>(.*?)</h>", r"<h1>\1</h1>", text)
    text = re.sub(r'<link to="(.*?)">(.*?)</link>', lambda m: f'<a href="{url(m[1])}">{m[2]}</a>', text)
    text = re.sub(r'<image src="(.*?)">', lambda m: f'<img src="{url(m[1])}" style="max-width:100%">', text)
    text = text.replace("\n", "<br>\n")
    return (f"<!doctype html><title>{title[1] if title else host}</title>"
            f"<body style='font:18px Georgia;max-width:680px;margin:40px auto;line-height:1.5'>"
            f"<p style='background:#003554;color:#8ab9b5;padding:8px 12px;border-radius:6px'>"
            f"Served by your own webserver.py, from sites/{host}/</p>{text}</body>").encode()


def main():
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", PORT))
    listener.listen()
    print(f"serving {', '.join(sorted(os.listdir(SITES)))} on port {PORT}. Ctrl+C to stop.", flush=True)
    while True:
        conn, _ = listener.accept()
        threading.Thread(target=lambda c=conn: (handle(c), c.close()), daemon=True).start()


if __name__ == "__main__":
    main()
