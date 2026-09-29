#!/usr/bin/env python3
"""Chapter 33 lab: an HTTP/2 client from scratch (on top of Python's TLS).

    python3 h2client.py example.org                          one request, every frame explained
    python3 h2client.py example.org --hpack                  …and how each header was compressed
    python3 h2client.py en.wikipedia.org /wiki/HTTP/2 /wiki/HTTP/3 /wiki/QUIC
                                                             three requests at once, on one connection

HTTP/2 carries the same requests and responses as HTTP/1.1, but as binary frames, each tagged
with a stream number, so that many requests can share one connection at the same time.
"""
import argparse
import socket
import ssl
import struct
import time

import hpack

TYPES = {0: "DATA", 1: "HEADERS", 2: "PRIORITY", 3: "RST_STREAM", 4: "SETTINGS", 5: "PUSH_PROMISE", 6: "PING",
         7: "GOAWAY", 8: "WINDOW_UPDATE", 9: "CONTINUATION"}
SETTINGS = {1: "HEADER_TABLE_SIZE", 2: "ENABLE_PUSH", 3: "MAX_CONCURRENT_STREAMS", 4: "INITIAL_WINDOW_SIZE",
            5: "MAX_FRAME_SIZE", 6: "MAX_HEADER_LIST_SIZE", 8: "ENABLE_CONNECT_PROTOCOL", 9: "NO_RFC7540_PRIORITIES"}
END_STREAM, ACK, END_HEADERS = 0x1, 0x1, 0x4
PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"


# --8<-- [start:frame]
def frame(ftype, flags, stream, payload=b""):
    """Every HTTP/2 frame: a 9-byte header (length, type, flags, stream number), then the payload."""
    return struct.pack("!I", len(payload))[1:] + bytes([ftype, flags]) + struct.pack("!I", stream) + payload


def read_frame(sock):
    header = read_exactly(sock, 9)
    length = int.from_bytes(header[:3], "big")
    ftype, flags = header[3], header[4]
    stream = struct.unpack("!I", header[5:9])[0] & 0x7FFFFFFF    # the top bit is reserved
    return ftype, flags, stream, read_exactly(sock, length)
# --8<-- [end:frame]


def read_exactly(sock, n):
    data = b""
    while len(data) < n:
        more = sock.recv(n - len(data))
        if not more:
            raise ConnectionError("connection closed")
        data += more
    return data


def describe(ftype, flags, payload):
    if ftype == 4:
        if flags & ACK:
            return "ACK: “got your settings”"
        pairs = [struct.unpack("!HI", payload[i:i + 6]) for i in range(0, len(payload), 6)]
        return ", ".join(f"{SETTINGS.get(k, k)}={v}" for k, v in pairs) or "(none)"
    if ftype == 8:
        return f"+{struct.unpack('!I', payload)[0] & 0x7FFFFFFF:,} bytes may be sent"
    if ftype == 6:
        return ("ACK " if flags & ACK else "") + payload.hex()
    if ftype == 7:
        last, code = struct.unpack("!II", payload[:8])
        return f"last stream {last & 0x7FFFFFFF}, error {code} ({'NO_ERROR' if code == 0 else 'error'})"
    if ftype == 3:
        return f"error {struct.unpack('!I', payload)[0]}"
    names = [n for bit, n in ((END_STREAM, "END_STREAM"), (END_HEADERS, "END_HEADERS")) if flags & bit]
    return " ".join(names)


def run(host, paths, show_hpack=False):
    ctx = ssl.create_default_context()
    ctx.set_alpn_protocols(["h2"])                                   # "I'd like to speak HTTP/2 inside"
    sock = ctx.wrap_socket(socket.create_connection((host, 443), timeout=10), server_hostname=host)
    t0 = time.monotonic()
    ms = lambda: f"{(time.monotonic() - t0) * 1000:6.1f} ms"
    print(f"TLS connected to {host}; ALPN chose {sock.selected_alpn_protocol()!r}\n")
    if sock.selected_alpn_protocol() != "h2":
        raise SystemExit("this server doesn't speak HTTP/2")
    quiet = len(paths) > 1

    def send(ftype, flags, stream, payload=b"", note=None):
        sock.sendall(frame(ftype, flags, stream, payload))
        if not quiet or ftype == 1:
            print(f"{ms()} → {TYPES[ftype]:<14} stream {stream:<2} {len(payload):>5} bytes  {note or describe(ftype, flags, payload)}")

    # --8<-- [start:open]
    sock.sendall(PREFACE)                                          # proves we really mean HTTP/2
    print(f"{ms()} → (preface)        {len(PREFACE)} bytes: {PREFACE!r}")
    send(4, 0, 0, struct.pack("!HIHI", 2, 0, 4, 16 * 2 ** 20))       # SETTINGS: no server push; 16 MB windows
    send(8, 0, 0, struct.pack("!I", 16 * 2 ** 20 - 65535))           # WINDOW_UPDATE: the same for the connection
    encoder, decoder = hpack.Table(), hpack.Table()
    streams = {}
    for n, path in enumerate(paths):
        sid = 1 + 2 * n                                             # clients use odd stream numbers
        headers = [(":method", "GET"), (":scheme", "https"), (":authority", host), (":path", path),
                   ("user-agent", "bitbybit-h2/1.0"), ("accept", "*/*")]
        block = hpack.encode(headers, encoder)
        send(1, END_STREAM | END_HEADERS, sid, block, f"GET {path}  ({len(block)} bytes of compressed headers)")
        streams[sid] = {"path": path, "bytes": 0, "status": None, "done": False}
    # --8<-- [end:open]

    # --8<-- [start:loop]
    order = []                                                      # which stream each DATA frame belonged to
    while not all(s["done"] for s in streams.values()):
        ftype, flags, sid, payload = read_frame(sock)
        name = TYPES.get(ftype, f"type {ftype}")
        if ftype == 0:                                              # DATA
            streams[sid]["bytes"] += len(payload)
            order.append(sid)
            if not quiet:
                print(f"{ms()} ← DATA           stream {sid:<2} {len(payload):>5} bytes  {describe(ftype, flags, payload)}")
        elif ftype != 1:
            print(f"{ms()} ← {name:<14} stream {sid:<2} {len(payload):>5} bytes  {describe(ftype, flags, payload)}")
        if ftype == 1:                                              # HEADERS: decompress with the connection's table
            fields = hpack.decode(payload, decoder)
            status = dict((n, v) for n, v, _, _ in fields).get(":status")
            streams[sid]["status"] = status
            print(f"{ms()} ← HEADERS        stream {sid:<2} {len(payload):>5} bytes  :status {status}, {len(fields)} headers")
            if show_hpack:
                for n, v, how, size in fields:
                    print(f"          {size:>3} bytes  {(n + ': ' + v)[:48]:<48}  {how}")
        elif ftype == 4 and not flags & ACK:
            send(4, ACK, 0)                                         # acknowledge the server's settings
        elif ftype == 6 and not flags & ACK:
            send(6, ACK, 0, payload)                                # answer a PING
        elif ftype == 7:
            break
        if sid in streams and flags & END_STREAM and ftype in (0, 1):
            streams[sid]["done"] = True
    # --8<-- [end:loop]
    send(7, 0, 0, struct.pack("!II", 0, 0), "GOAWAY: we're finished, no error")
    sock.close()
    print()
    for sid, s in streams.items():
        print(f"stream {sid}: {s['path']}  →  {s['status']}, {s['bytes']:,} bytes")
    if quiet:
        print("\nthe DATA frames, in the order they arrived (each digit is the stream it belonged to):")
        line = "".join(str(sid % 10) if sid < 10 else "*" for sid in order)
        for i in range(0, len(line), 100):
            print("  " + line[i:i + 100])


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("host")
    p.add_argument("paths", nargs="*", default=["/"])
    p.add_argument("--hpack", action="store_true", help="show how each response header was compressed")
    a = p.parse_args()
    run(a.host, a.paths or ["/"], a.hpack)


if __name__ == "__main__":
    main()
