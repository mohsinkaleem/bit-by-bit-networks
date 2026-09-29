#!/usr/bin/env python3
"""Chapter 34 lab: a forward proxy, like the ones companies and schools put between their users and the web.

    python3 proxy.py          then, in another window:
                              curl -x http://127.0.0.1:7140 http://info.cern.ch/
                              curl -x http://127.0.0.1:7140 https://example.org/
    python3 proxy.py --block example.com     refuse one site

For plain http:// the proxy sees (and could change) everything. For https:// the browser only
asks it to CONNECT: open a TCP connection to a host and port, and pass bytes blindly both ways.
The proxy sees the name, and how much went each way, and nothing else.
"""
import argparse
import select
import socket
import threading
import time

PORT = 7140


# --8<-- [start:connect]
def tunnel(client, host, port, log):
    """CONNECT: open a connection for the client, then copy bytes both ways until either side hangs up."""
    try:
        upstream = socket.create_connection((host, port), timeout=10)
    except OSError as e:
        client.sendall(f"HTTP/1.1 502 Bad Gateway\r\n\r\n{e}\r\n".encode())
        return log(f"CONNECT {host}:{port}  → failed: {e}")
    client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
    up = down = 0
    t0 = time.monotonic()
    socks = [client, upstream]
    while True:
        ready, _, _ = select.select(socks, [], [], 30)
        if not ready:
            break
        for s in ready:
            data = s.recv(65536)
            if not data:
                upstream.close()
                return log(f"CONNECT {host}:{port}  a tunnel: {up:,} bytes up, {down:,} down, {time.monotonic() - t0:.1f} s. "
                           f"First bytes up were {first[:3].hex()}…: a TLS hello. The rest is sealed.")
            if s is client:
                if up == 0:
                    first = data
                up += len(data)
                upstream.sendall(data)
            else:
                down += len(data)
                client.sendall(data)
# --8<-- [end:connect]


# --8<-- [start:plain]
def forward(client, request, log):
    """Plain HTTP: the request line has the whole URL in it. We read it, and could change anything."""
    head, _, rest = request.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    method, url, version = lines[0].split(" ")
    assert url.startswith("http://")
    hostport, _, path = url[7:].partition("/")
    host, _, port = hostport.partition(":")
    headers = [l for l in lines[1:] if not l.lower().startswith(("proxy-connection", "connection"))]
    upstream = socket.create_connection((host, int(port or 80)), timeout=10)
    upstream.sendall(f"{method} /{path} {version}\r\n".encode() + "\r\n".join(headers).encode()
                     + b"\r\nConnection: close\r\nVia: 1.1 bitbybit-proxy\r\n\r\n" + rest)
    total, status = 0, b""
    while True:
        data = upstream.recv(65536)
        if not data:
            break
        if not status:
            status = data.split(b"\r\n", 1)[0]
        total += len(data)
        client.sendall(data)
    ua = next((l.split(": ", 1)[1] for l in headers if l.lower().startswith("user-agent")), "?")
    log(f"{method} {url}  → {status.decode()}, {total:,} bytes. I can read all of it (user-agent: {ua})")
# --8<-- [end:plain]


def handle(client, blocked, log):
    with client:
        client.settimeout(10)
        request = b""
        while b"\r\n\r\n" not in request:
            data = client.recv(65536)
            if not data:
                return
            request += data
        method, target = request.split(b" ", 2)[:2]
        host = target.decode().split("//")[-1].split("/")[0].split(":")[0]
        if host in blocked:
            client.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 29\r\n\r\nBlocked by the garden proxy.\n")
            return log(f"{method.decode()} {target.decode()}  → 403: blocked")
        if method == b"CONNECT":
            h, _, p = target.decode().rpartition(":")
            tunnel(client, h, int(p), log)
        else:
            forward(client, request, log)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--block", nargs="*", default=[])
    a = ap.parse_args()
    lock = threading.Lock()

    def log(msg):
        with lock:
            print(time.strftime("%H:%M:%S ") + msg, flush=True)
    srv = socket.create_server(("127.0.0.1", PORT))
    print(f"forward proxy on 127.0.0.1:{PORT}. Try: curl -x http://127.0.0.1:{PORT} https://example.org/")
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client, set(a.block), log), daemon=True).start()


if __name__ == "__main__":
    main()
