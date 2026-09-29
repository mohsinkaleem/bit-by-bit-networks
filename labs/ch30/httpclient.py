#!/usr/bin/env python3
"""Chapter 30 lab: an HTTP/1.1 client from scratch, with the features real browsers rely on.

    python3 httpclient.py get http://info.cern.ch/            one request, every header shown
    python3 httpclient.py keepalive https://example.org/      5 requests: new connection each time, or one?
    python3 httpclient.py cache http://info.cern.ch/          ask twice; the second time, "only if it changed"
    python3 httpclient.py redirects http://bbc.co.uk/         follow Location headers to the end
    python3 httpclient.py range http://info.cern.ch/ 0-99     just part of the file
    python3 httpclient.py gzip https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol

Only the standard library: socket for the connection, ssl for https, gzip for compression.
"""
import gzip
import socket
import ssl
import sys
import time
import urllib.parse


class Connection:
    """One TCP (and maybe TLS) connection, which can carry many requests, one after another."""

    def __init__(self, host, port, tls):
        t = time.perf_counter()
        raw = socket.create_connection((host, port), timeout=10)
        self.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host) if tls else raw
        self.setup_ms = (time.perf_counter() - t) * 1000
        self.buf = b""

    def readline(self):
        while b"\r\n" not in self.buf:
            more = self.sock.recv(65536)
            if not more:
                raise ConnectionError("connection closed")
            self.buf += more
        line, self.buf = self.buf.split(b"\r\n", 1)
        return line.decode("latin-1")

    def read(self, n):
        while len(self.buf) < n:
            more = self.sock.recv(65536)
            if not more:
                raise ConnectionError("connection closed")
            self.buf += more
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    # --8<-- [start:request]
    def request(self, method, host, path, headers=None):
        lines = [f"{method} {path} HTTP/1.1", f"Host: {host}", "User-Agent: bitbybit-lab/1.0 (a networking book)"]
        lines += [f"{k}: {v}" for k, v in (headers or {}).items()]
        self.sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        status = self.readline()                                   # e.g. "HTTP/1.1 200 OK"
        head = {}
        while (line := self.readline()):                           # headers, until an empty line
            name, _, value = line.partition(":")
            head[name.strip().lower()] = head.get(name.strip().lower(), "") + value.strip()
        code = int(status.split()[1])
        # where does the body end? That's the question a kept-open connection must answer.
        if method == "HEAD" or code in (204, 304):
            body = b""
        elif head.get("transfer-encoding", "").lower() == "chunked":
            body = self.read_chunked()                             # Chapter 7's chunks
        elif "content-length" in head:
            body = self.read(int(head["content-length"]))
        else:
            body = self.read_until_closed()                        # the old way: the server hangs up
        if head.get("content-encoding") == "gzip":
            body = gzip.decompress(body)
        return code, status, head, body
    # --8<-- [end:request]

    def read_chunked(self):
        body = b""
        while True:
            size = int(self.readline().split(";")[0], 16)
            if size == 0:
                while self.readline():                             # optional trailer headers
                    pass
                return body
            body += self.read(size)
            self.readline()

    def read_until_closed(self):
        body = self.buf
        while (more := self.sock.recv(65536)):
            body += more
        self.buf = b""
        return body

    def close(self):
        self.sock.close()


def parts(url):
    u = urllib.parse.urlsplit(url)
    tls = u.scheme == "https"
    return u.hostname, u.port or (443 if tls else 80), tls, (u.path or "/") + (f"?{u.query}" if u.query else "")


def get(url, headers=None, verbose=True):
    host, port, tls, path = parts(url)
    c = Connection(host, port, tls)
    code, status, head, body = c.request("GET", host, path, headers)
    c.close()
    if verbose:
        print(f"> GET {path} HTTP/1.1\n> Host: {host}")
        for k, v in (headers or {}).items():
            print(f"> {k}: {v}")
        print(f"< {status}")
        for k, v in head.items():
            print(f"< {k}: {v}")
        print(f"({len(body)} bytes of body)")
    return code, head, body


# --8<-- [start:keepalive]
def keepalive(url, n=5):
    host, port, tls, path = parts(url)
    t = time.perf_counter()
    for i in range(n):                                             # a new connection for every request
        c = Connection(host, port, tls)
        c.request("GET", host, path, {"Connection": "close"})
        c.close()
    fresh = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    c = Connection(host, port, tls)                                # one connection, kept open
    for i in range(n):
        c.request("GET", host, path)
    c.close()
    reused = (time.perf_counter() - t) * 1000
    print(f"{n} requests, a new connection each time: {fresh:6.0f} ms")
    print(f"{n} requests, one connection kept open:  {reused:6.0f} ms   (setting it up took {c.setup_ms:.0f} ms)")
# --8<-- [end:keepalive]


def cache(url):
    code, head, body = get(url, verbose=False)
    print(f"first request:  {code}, {len(body)} bytes; ETag {head.get('etag')}, Last-Modified {head.get('last-modified')}")
    ask = {}
    if "etag" in head:
        ask["If-None-Match"] = head["etag"]
    if "last-modified" in head:
        ask["If-Modified-Since"] = head["last-modified"]
    code, head2, body2 = get(url, ask, verbose=False)
    print(f"asking again with {', '.join(ask)}:")
    print(f"second request: {code}, {len(body2)} bytes" + ("  → “not modified”: use the copy you have" if code == 304 else ""))


def redirects(url, limit=10):
    for _ in range(limit):
        code, head, _ = get(url, verbose=False)
        hsts = f"   (and: Strict-Transport-Security: {head['strict-transport-security']})" if "strict-transport-security" in head else ""
        print(f"{code}  {url}" + hsts)
        if code not in (301, 302, 303, 307, 308):
            return
        url = urllib.parse.urljoin(url, head["location"])


def byte_range(url, spec):
    code, head, body = get(url, {"Range": f"bytes={spec}"}, verbose=False)
    print(f"{code}, Content-Range: {head.get('content-range')}, got {len(body)} bytes:")
    print(body.decode("utf-8", "replace"))


def compare_gzip(url):
    host, port, tls, path = parts(url)
    for enc in ("identity", "gzip"):
        c = Connection(host, port, tls)
        c.sock.sendall(f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: bitbybit-lab/1.0 (a networking book)\r\n"
                       f"Accept-Encoding: {enc}\r\nConnection: close\r\n\r\n".encode())
        raw = c.read_until_closed()
        c.close()
        head, _, body = raw.partition(b"\r\n\r\n")
        encoding = next((l.split(b":", 1)[1].strip().decode() for l in head.split(b"\r\n") if l.lower().startswith(b"content-encoding")), "none")
        status = head.split(b"\r\n")[0].decode()
        print(f"Accept-Encoding: {enc:<9} → {status}, Content-Encoding: {encoding:<5} {len(raw):>9,} bytes on the wire")


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] in ("get", "keepalive", "cache", "redirects", "gzip"):
        {"get": get, "keepalive": keepalive, "cache": cache, "redirects": redirects, "gzip": compare_gzip}[a[0]](a[1])
    elif len(a) == 3 and a[0] == "range":
        byte_range(a[1], a[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
