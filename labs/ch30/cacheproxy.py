#!/usr/bin/env python3
"""Chapter 30 lab: a caching web proxy, like the ones inside every content delivery network.

    python3 cacheproxy.py                       listen on 127.0.0.1:7130
    curl -x http://127.0.0.1:7130 -sI http://info.cern.ch/     (in another window, a few times)

It only handles plain http:// (an https:// connection is encrypted end to end: Chapter 32).
Every response gets an X-Cache header saying what the proxy did: MISS (fetched it), HIT (answered
from its memory), or REVALIDATED (asked the server "has it changed?" and was told no).
"""
import email.utils
import socketserver
import time
import urllib.parse

from httpclient import Connection

CACHE = {}          # url -> dict(status, headers, body, stored, fresh_for)


# --8<-- [start:fresh]
def freshness(headers, now):
    """How many seconds a response may be reused without asking the server again."""
    cc = {d.strip().split("=")[0].lower(): (d.split("=")[1] if "=" in d else True)
          for d in headers.get("cache-control", "").split(",") if d.strip()}
    if "no-store" in cc or "private" in cc:
        return None                               # mustn't be kept at all (by a shared cache)
    if "no-cache" in cc:
        return 0                                  # may be kept, but must be checked every time
    if "s-maxage" in cc:
        return int(cc["s-maxage"])                # "shared caches, use this one"
    if "max-age" in cc:
        return int(cc["max-age"])
    if "expires" in headers:
        return email.utils.parsedate_to_datetime(headers["expires"]).timestamp() - now
    if "last-modified" in headers:                # no instructions: guess 10% of its age, at most a day
        age = now - email.utils.parsedate_to_datetime(headers["last-modified"]).timestamp()
        return min(age / 10, 86400)
    return 0
# --8<-- [end:fresh]


def fetch(url, extra=None):
    u = urllib.parse.urlsplit(url)
    c = Connection(u.hostname, u.port or 80, False)
    code, status, head, body = c.request("GET", u.hostname, (u.path or "/") + (f"?{u.query}" if u.query else ""),
                                         dict(extra or {}, **{"Accept-Encoding": "identity"}))
    c.close()
    return code, status, head, body


# --8<-- [start:handle]
def handle(url):
    now = time.time()
    entry = CACHE.get(url)
    if entry and now - entry["stored"] < entry["fresh_for"]:
        return entry, "HIT", int(now - entry["stored"])
    if entry:                                     # stale: ask the server whether our copy is still good
        ask = {}
        if "etag" in entry["headers"]:
            ask["If-None-Match"] = entry["headers"]["etag"]
        if "last-modified" in entry["headers"]:
            ask["If-Modified-Since"] = entry["headers"]["last-modified"]
        if ask:
            code, status, head, body = fetch(url, ask)
            if code == 304:
                entry["stored"], entry["fresh_for"] = now, freshness(dict(entry["headers"], **head), now) or 0
                return entry, "REVALIDATED", 0
    code, status, head, body = fetch(url)
    entry = dict(status=status, headers=head, body=body, stored=now, fresh_for=freshness(head, now))
    if code == 200 and entry["fresh_for"] is not None:
        CACHE[url] = entry
    return entry, "MISS", 0
# --8<-- [end:handle]


class Proxy(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline().decode("latin-1").strip()
        while self.rfile.readline().strip():      # skip the client's headers
            pass
        try:
            method, url, _ = line.split()
            if method not in ("GET", "HEAD") or not url.startswith("http://"):
                raise ValueError
        except ValueError:
            self.wfile.write(b"HTTP/1.1 501 Not Implemented\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            return
        entry, what, age = handle(url)
        skip = {"connection", "transfer-encoding", "content-length", "keep-alive", "age", "x-cache"}
        head = "".join(f"{k}: {v}\r\n" for k, v in entry["headers"].items() if k not in skip)
        body = entry["body"] if method == "GET" else b""
        self.wfile.write((f"{entry['status']}\r\n{head}Age: {age}\r\nX-Cache: {what}\r\n"
                          f"Content-Length: {len(entry['body'])}\r\nConnection: close\r\n\r\n").encode("latin-1") + body)
        fresh = entry["fresh_for"]
        print(f"{time.strftime('%H:%M:%S')}  {what:<11} {url}   (fresh for {fresh:.0f} s)" if fresh is not None else
              f"{time.strftime('%H:%M:%S')}  {what:<11} {url}   (not cacheable)", flush=True)


def main():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("127.0.0.1", 7130), Proxy) as server:
        print("caching proxy on 127.0.0.1:7130. Try: curl -x http://127.0.0.1:7130 -sI http://info.cern.ch/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print()


if __name__ == "__main__":
    main()
