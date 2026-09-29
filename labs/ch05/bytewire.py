#!/usr/bin/env python3
"""Chapter 5 lab, part 3: sending ANY bytes, by saying how many are coming.

    python3 bytewire.py serve shared            share every file in the folder "shared" (port 7005)
    python3 bytewire.py fetch volcano.png       (in another terminal) fetch it into downloads/

The request is one line of text. The reply is a few header lines, a blank line,
and then exactly Length bytes of body, which can be anything at all.

    GET volcano.png                 OK
                                    Type: image/png
                                    Length: 1234
                                    (blank line)
                                    ...1234 bytes...
"""
import hashlib
import mimetypes
import os
import socket
import sys

PORT = 7005


# --8<-- [start:read]
def read_exactly(sock, n):
    """Keep reading until we have exactly n bytes (a socket may hand us less each time)."""
    data = b""
    while len(data) < n:
        more = sock.recv(n - len(data))
        if not more:
            raise ConnectionError(f"connection closed after {len(data)} of {n} bytes")
        data += more
    return data


def read_headers(sock):
    """Read up to the blank line. Returns (status line, {name: value})."""
    raw = b""
    while not raw.endswith(b"\n\n"):
        byte = sock.recv(1)
        if not byte:
            raise ConnectionError("connection closed in the middle of the headers")
        raw += byte
    lines = raw.decode().strip("\n").split("\n")
    headers = {}
    for line in lines[1:]:
        name, _, value = line.partition(": ")
        headers[name.lower()] = value
    return lines[0], headers
# --8<-- [end:read]


# --8<-- [start:serve]
def serve(folder):
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", PORT))
    listener.listen()
    print(f"sharing {folder}/ on port {PORT}. Ctrl+C to stop.")
    while True:
        conn, _ = listener.accept()
        with conn:
            request = b""
            while not request.endswith(b"\n"):
                request += conn.recv(1)
            command, _, name = request.decode().strip().partition(" ")
            path = os.path.join(folder, os.path.basename(name))
            if command != "GET" or not os.path.isfile(path):
                conn.sendall(b"NOT FOUND\nLength: 0\n\n")
                print(f"GET {name} -> NOT FOUND")
                continue
            with open(path, "rb") as f:
                body = f.read()
            kind = mimetypes.guess_type(path)[0] or "application/octet-stream"
            header = f"OK\nType: {kind}\nLength: {len(body)}\n\n".encode()
            conn.sendall(header + body)
            print(f"GET {name} -> OK, {kind}, {len(body)} bytes")
# --8<-- [end:serve]


def fetch(name):
    with socket.create_connection(("127.0.0.1", PORT)) as sock:
        sock.sendall(f"GET {name}\n".encode())
        status, headers = read_headers(sock)
        body = read_exactly(sock, int(headers.get("length", "0")))
    print(status)
    for k, v in headers.items():
        print(f"  {k}: {v}")
    if status != "OK":
        return
    os.makedirs("downloads", exist_ok=True)
    out = os.path.join("downloads", os.path.basename(name))
    with open(out, "wb") as f:
        f.write(body)
    print(f"saved {out}  sha256={hashlib.sha256(body).hexdigest()[:16]}…")
    if headers.get("type", "").startswith("text/"):
        print("-" * 40)
        print(body.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    if sys.argv[1:2] == ["serve"] and len(sys.argv) > 2:
        serve(sys.argv[2])
    elif sys.argv[1:2] == ["fetch"] and len(sys.argv) > 2:
        fetch(sys.argv[2])
    else:
        print(__doc__)
