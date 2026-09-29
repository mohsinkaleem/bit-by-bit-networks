#!/usr/bin/env python3
"""Chapter 33 lab: header compression for HTTP/2 (HPACK) and HTTP/3 (QPACK). h2client.py and quic.py import this.

    python3 hpack.py            compress the same request twice, and watch the second one shrink
    python3 hpack.py --test     check against the examples in RFC 7541

HTTP/2 sends the same headers (user-agent, accept, cookie…) on every request, so it compresses
them three ways: a static table of 61 common headers, a dynamic table of headers seen earlier on
this connection, and a Huffman code that gives common characters shorter bit patterns.
"""
import sys

STATIC = [   # RFC 7541 Appendix A: index 1 is the first
    (':authority', ''), (':method', 'GET'), (':method', 'POST'), (':path', '/'), (':path', '/index.html'),
    (':scheme', 'http'), (':scheme', 'https'), (':status', '200'), (':status', '204'), (':status', '206'),
    (':status', '304'), (':status', '400'), (':status', '404'), (':status', '500'), ('accept-charset', ''),
    ('accept-encoding', 'gzip, deflate'), ('accept-language', ''), ('accept-ranges', ''), ('accept', ''),
    ('access-control-allow-origin', ''), ('age', ''), ('allow', ''), ('authorization', ''), ('cache-control', ''),
    ('content-disposition', ''), ('content-encoding', ''), ('content-language', ''), ('content-length', ''),
    ('content-location', ''), ('content-range', ''), ('content-type', ''), ('cookie', ''), ('date', ''), ('etag', ''),
    ('expect', ''), ('expires', ''), ('from', ''), ('host', ''), ('if-match', ''), ('if-modified-since', ''),
    ('if-none-match', ''), ('if-range', ''), ('if-unmodified-since', ''), ('last-modified', ''), ('link', ''),
    ('location', ''), ('max-forwards', ''), ('proxy-authenticate', ''), ('proxy-authorization', ''), ('range', ''),
    ('referer', ''), ('refresh', ''), ('retry-after', ''), ('server', ''), ('set-cookie', ''),
    ('strict-transport-security', ''), ('transfer-encoding', ''), ('user-agent', ''), ('vary', ''), ('via', ''),
    ('www-authenticate', ''),
]

QPACK_STATIC = [   # RFC 9204 Appendix A: HTTP/3's static table, index 0 is the first
    (':authority', ''), (':path', '/'), ('age', '0'), ('content-disposition', ''), ('content-length', '0'),
    ('cookie', ''), ('date', ''), ('etag', ''), ('if-modified-since', ''), ('if-none-match', ''),
    ('last-modified', ''), ('link', ''), ('location', ''), ('referer', ''), ('set-cookie', ''), (':method', 'CONNECT'),
    (':method', 'DELETE'), (':method', 'GET'), (':method', 'HEAD'), (':method', 'OPTIONS'), (':method', 'POST'),
    (':method', 'PUT'), (':scheme', 'http'), (':scheme', 'https'), (':status', '103'), (':status', '200'),
    (':status', '304'), (':status', '404'), (':status', '503'), ('accept', '*/*'),
    ('accept', 'application/dns-message'), ('accept-encoding', 'gzip, deflate, br'), ('accept-ranges', 'bytes'),
    ('access-control-allow-headers', 'cache-control'), ('access-control-allow-headers', 'content-type'),
    ('access-control-allow-origin', '*'), ('cache-control', 'max-age=0'), ('cache-control', 'max-age=2592000'),
    ('cache-control', 'max-age=604800'), ('cache-control', 'no-cache'), ('cache-control', 'no-store'),
    ('cache-control', 'public, max-age=31536000'), ('content-encoding', 'br'), ('content-encoding', 'gzip'),
    ('content-type', 'application/dns-message'), ('content-type', 'application/javascript'),
    ('content-type', 'application/json'), ('content-type', 'application/x-www-form-urlencoded'),
    ('content-type', 'image/gif'), ('content-type', 'image/jpeg'), ('content-type', 'image/png'),
    ('content-type', 'text/css'), ('content-type', 'text/html; charset=utf-8'), ('content-type', 'text/plain'),
    ('content-type', 'text/plain;charset=utf-8'), ('range', 'bytes=0-'),
    ('strict-transport-security', 'max-age=31536000'),
    ('strict-transport-security', 'max-age=31536000; includesubdomains'),
    ('strict-transport-security', 'max-age=31536000; includesubdomains; preload'), ('vary', 'accept-encoding'),
    ('vary', 'origin'), ('x-content-type-options', 'nosniff'), ('x-xss-protection', '1; mode=block'),
    (':status', '100'), (':status', '204'), (':status', '206'), (':status', '302'), (':status', '400'),
    (':status', '403'), (':status', '421'), (':status', '425'), (':status', '500'), ('accept-language', ''),
    ('access-control-allow-credentials', 'FALSE'), ('access-control-allow-credentials', 'TRUE'),
    ('access-control-allow-headers', '*'), ('access-control-allow-methods', 'get'),
    ('access-control-allow-methods', 'get, post, options'), ('access-control-allow-methods', 'options'),
    ('access-control-expose-headers', 'content-length'), ('access-control-request-headers', 'content-type'),
    ('access-control-request-method', 'get'), ('access-control-request-method', 'post'), ('alt-svc', 'clear'),
    ('authorization', ''), ('content-security-policy', "script-src 'none'; object-src 'none'; base-uri 'none'"),
    ('early-data', '1'), ('expect-ct', ''), ('forwarded', ''), ('if-range', ''), ('origin', ''),
    ('purpose', 'prefetch'), ('server', ''), ('timing-allow-origin', '*'), ('upgrade-insecure-requests', '1'),
    ('user-agent', ''), ('x-forwarded-for', ''), ('x-frame-options', 'deny'), ('x-frame-options', 'sameorigin'),
]

# RFC 7541 Appendix B: the Huffman code for bytes 0-255 and end-of-string, as hex-code:length-in-bits
_HUFFMAN = """
1ff8:13 7fffd8:23 fffffe2:28 fffffe3:28 fffffe4:28 fffffe5:28 fffffe6:28 fffffe7:28 fffffe8:28 ffffea:24
3ffffffc:30 fffffe9:28 fffffea:28 3ffffffd:30 fffffeb:28 fffffec:28 fffffed:28 fffffee:28 fffffef:28 ffffff0:28
ffffff1:28 ffffff2:28 3ffffffe:30 ffffff3:28 ffffff4:28 ffffff5:28 ffffff6:28 ffffff7:28 ffffff8:28 ffffff9:28
ffffffa:28 ffffffb:28 14:6 3f8:10 3f9:10 ffa:12 1ff9:13 15:6 f8:8 7fa:11 3fa:10 3fb:10 f9:8 7fb:11 fa:8 16:6
17:6 18:6 0:5 1:5 2:5 19:6 1a:6 1b:6 1c:6 1d:6 1e:6 1f:6 5c:7 fb:8 7ffc:15 20:6 ffb:12 3fc:10 1ffa:13 21:6 5d:7
5e:7 5f:7 60:7 61:7 62:7 63:7 64:7 65:7 66:7 67:7 68:7 69:7 6a:7 6b:7 6c:7 6d:7 6e:7 6f:7 70:7 71:7 72:7 fc:8
73:7 fd:8 1ffb:13 7fff0:19 1ffc:13 3ffc:14 22:6 7ffd:15 3:5 23:6 4:5 24:6 5:5 25:6 26:6 27:6 6:5 74:7 75:7 28:6
29:6 2a:6 7:5 2b:6 76:7 2c:6 8:5 9:5 2d:6 77:7 78:7 79:7 7a:7 7b:7 7ffe:15 7fc:11 3ffd:14 1ffd:13 ffffffc:28
fffe6:20 3fffd2:22 fffe7:20 fffe8:20 3fffd3:22 3fffd4:22 3fffd5:22 7fffd9:23 3fffd6:22 7fffda:23 7fffdb:23
7fffdc:23 7fffdd:23 7fffde:23 ffffeb:24 7fffdf:23 ffffec:24 ffffed:24 3fffd7:22 7fffe0:23 ffffee:24 7fffe1:23
7fffe2:23 7fffe3:23 7fffe4:23 1fffdc:21 3fffd8:22 7fffe5:23 3fffd9:22 7fffe6:23 7fffe7:23 ffffef:24 3fffda:22
1fffdd:21 fffe9:20 3fffdb:22 3fffdc:22 7fffe8:23 7fffe9:23 1fffde:21 7fffea:23 3fffdd:22 3fffde:22 fffff0:24
1fffdf:21 3fffdf:22 7fffeb:23 7fffec:23 1fffe0:21 1fffe1:21 3fffe0:22 1fffe2:21 7fffed:23 3fffe1:22 7fffee:23
7fffef:23 fffea:20 3fffe2:22 3fffe3:22 3fffe4:22 7ffff0:23 3fffe5:22 3fffe6:22 7ffff1:23 3ffffe0:26 3ffffe1:26
fffeb:20 7fff1:19 3fffe7:22 7ffff2:23 3fffe8:22 1ffffec:25 3ffffe2:26 3ffffe3:26 3ffffe4:26 7ffffde:27
7ffffdf:27 3ffffe5:26 fffff1:24 1ffffed:25 7fff2:19 1fffe3:21 3ffffe6:26 7ffffe0:27 7ffffe1:27 3ffffe7:26
7ffffe2:27 fffff2:24 1fffe4:21 1fffe5:21 3ffffe8:26 3ffffe9:26 ffffffd:28 7ffffe3:27 7ffffe4:27 7ffffe5:27
fffec:20 fffff3:24 fffed:20 1fffe6:21 3fffe9:22 1fffe7:21 1fffe8:21 7ffff3:23 3fffea:22 3fffeb:22 1ffffee:25
1ffffef:25 fffff4:24 fffff5:24 3ffffea:26 7ffff4:23 3ffffeb:26 7ffffe6:27 3ffffec:26 3ffffed:26 7ffffe7:27
7ffffe8:27 7ffffe9:27 7ffffea:27 7ffffeb:27 ffffffe:28 7ffffec:27 7ffffed:27 7ffffee:27 7ffffef:27 7fffff0:27
3ffffee:26 3fffffff:30
"""


HUFFMAN = [(int(c, 16), int(n)) for c, n in (x.split(":") for x in _HUFFMAN.split())]   # [(code, length)] for 0..256
_DECODE = {(code, n): sym for sym, (code, n) in enumerate(HUFFMAN)}


# ---------------------------------------------------------------- numbers and strings

# --8<-- [start:ints]
def encode_int(value, prefix, flags=0):
    """An integer in the low `prefix` bits of the first byte, overflowing into more bytes, 7 bits at a time."""
    limit = (1 << prefix) - 1
    if value < limit:
        return bytes([flags | value])
    out, value = [flags | limit], value - limit
    while value >= 128:
        out.append(value % 128 + 128)
        value //= 128
    return bytes(out + [value])


def decode_int(data, i, prefix):
    limit = (1 << prefix) - 1
    value = data[i] & limit
    i += 1
    if value < limit:
        return value, i
    shift = 0
    while True:
        b = data[i]
        i += 1
        value += (b & 127) << shift
        shift += 7
        if not b & 128:
            return value, i
# --8<-- [end:ints]


# --8<-- [start:huffman]
def huffman_encode(data):
    bits, n = 0, 0
    for byte in data:
        code, length = HUFFMAN[byte]
        bits, n = (bits << length) | code, n + length
    pad = -n % 8                                      # pad the last byte with 1s (the start of end-of-string)
    return ((bits << pad) | ((1 << pad) - 1)).to_bytes((n + pad) // 8, "big")


def huffman_decode(data):
    out, code, n = bytearray(), 0, 0
    for byte in data:
        for k in range(7, -1, -1):
            code, n = (code << 1) | (byte >> k & 1), n + 1
            sym = _DECODE.get((code, n))
            if sym is not None:
                out.append(sym)
                code, n = 0, 0
    return bytes(out)
# --8<-- [end:huffman]


def encode_string(s, huffman=True, prefix=7, flags=0):
    raw = s.encode() if isinstance(s, str) else s
    packed = huffman_encode(raw)
    if huffman and len(packed) < len(raw):
        return encode_int(len(packed), prefix, flags | (1 << prefix)) + packed
    return encode_int(len(raw), prefix, flags) + raw


def decode_string(data, i, prefix=7):
    huff = data[i] >> prefix & 1
    n, i = decode_int(data, i, prefix)
    raw = data[i:i + n]
    return (huffman_decode(raw) if huff else raw).decode("latin-1"), i + n, bool(huff), n


# ---------------------------------------------------------------- HPACK: the tables

class Table:
    """The static table, then a dynamic table of recent headers (newest first, from index 62)."""
    def __init__(self, max_size=4096):
        self.dynamic, self.max_size = [], max_size

    def get(self, index):
        if index <= len(STATIC):
            return STATIC[index - 1]
        return self.dynamic[index - len(STATIC) - 1]

    def add(self, name, value):
        self.dynamic.insert(0, (name, value))
        while self.size() > self.max_size:
            self.dynamic.pop()

    def size(self):
        return sum(len(n) + len(v) + 32 for n, v in self.dynamic)     # the standard's way of counting

    def find(self, name, value):
        """(index of an exact match or None, index of a name match or None)"""
        both = name_only = None
        for i, entry in enumerate(STATIC + self.dynamic, 1):
            if entry == (name, value) and both is None:
                both = i
            if entry[0] == name and name_only is None:
                name_only = i
        return both, name_only


# --8<-- [start:decode]
def decode(block, table):
    """A header block → [(name, value, how it was sent, bytes it took)]."""
    out, i = [], 0
    while i < len(block):
        start, b = i, block[i]
        if b & 0x80:                                          # 1xxxxxxx: a whole header, by number
            index, i = decode_int(block, i, 7)
            name, value = table.get(index)
            how = f"index {index} ({'static' if index <= len(STATIC) else 'dynamic'} table)"
        elif b & 0xE0 == 0x20:                                # 001xxxxx: resize the dynamic table
            table.max_size, i = decode_int(block, i, 5)
            continue
        else:
            indexing = b & 0x40                               # 01xxxxxx: literal, and remember it
            index, i = decode_int(block, i, 6 if indexing else 4)
            if index:
                name = table.get(index)[0]
                how = f"name from index {index}, "
            else:
                name, i, h, _ = decode_string(block, i)
                how = "new name" + (" (Huffman)" if h else "") + ", "
            value, i, h, n = decode_string(block, i)
            how += f"value {'Huffman-coded' if h else 'as text'}"
            if indexing:
                table.add(name, value)
                how += "; added to the dynamic table"
            elif b & 0x10:
                how += "; never to be indexed"
        out.append((name, value, how, i - start))
    return out
# --8<-- [end:decode]


# --8<-- [start:encode]
def encode(headers, table, trace=None):
    """[(name, value)] → a header block, using the tables and remembering new headers."""
    out = bytearray()
    for name, value in headers:
        both, name_only = table.find(name, value)
        if both:
            piece = encode_int(both, 7, 0x80)                 # already in a table: one byte, usually
            how = f"index {both}"
        else:
            piece = (encode_int(name_only, 6, 0x40) if name_only
                     else b"\x40" + encode_string(name))      # a literal, to be remembered
            piece += encode_string(value)
            table.add(name, value)
            how = (f"name index {name_only}" if name_only else "new name") + ", value Huffman-coded, remembered"
        out += piece
        if trace is not None:
            trace.append((name, value, how, len(piece)))
    return bytes(out)
# --8<-- [end:encode]


# ---------------------------------------------------------------- QPACK (HTTP/3), static table only

def qpack_decode(block):
    """HTTP/3's field sections. We tell servers our dynamic table size is 0, so only the static table is used."""
    ric, i = decode_int(block, 0, 8)
    _, i = decode_int(block, i, 7)
    if ric:
        raise ValueError("this field section uses the dynamic table, which we didn't allow")
    out = []
    while i < len(block):
        start, b = i, block[i]
        if b & 0x80:                                          # 1Txxxxxx: indexed
            index, i = decode_int(block, i, 6)
            name, value = QPACK_STATIC[index]
            how = f"static index {index}"
        elif b & 0x40:                                        # 01NTxxxx: literal value, name from the table
            index, i = decode_int(block, i, 4)
            name = QPACK_STATIC[index][0]
            value, i, h, _ = decode_string(block, i)
            how = f"name from static index {index}, value {'Huffman-coded' if h else 'as text'}"
        elif b & 0x20:                                        # 001NHxxx: literal name and value
            name, i, h1, _ = decode_string(block, i, 3)
            value, i, h, _ = decode_string(block, i)
            how = f"new name, value {'Huffman-coded' if h else 'as text'}"
        else:
            raise ValueError("a dynamic table reference")
        out.append((name, value, how, i - start))
    return out


def qpack_encode(headers):
    out = bytearray(b"\x00\x00")                            # required insert count 0, base 0: no dynamic table
    for name, value in headers:
        exact = next((i for i, e in enumerate(QPACK_STATIC) if e == (name, value)), None)
        named = next((i for i, e in enumerate(QPACK_STATIC) if e[0] == name), None)
        if exact is not None:
            out += encode_int(exact, 6, 0xC0)
        elif named is not None:
            out += encode_int(named, 4, 0x50) + encode_string(value)
        else:
            out += encode_string(name, prefix=3, flags=0x20) + encode_string(value)
    return bytes(out)


# ---------------------------------------------------------------- try it

def demo():
    table = Table()
    request = [(":method", "GET"), (":scheme", "https"), (":authority", "en.wikipedia.org"), (":path", "/wiki/HTTP/2"),
               ("user-agent", "bitbybit-h2/1.0"), ("accept", "text/html")]
    plain = sum(len(n) + len(v) + 4 for n, v in request)      # as HTTP/1.1 would write them, "name: value\r\n"
    for n, path in enumerate(["/wiki/HTTP/2", "/wiki/HTTP/3"], 1):
        request[3] = (":path", path)
        trace = []
        block = encode(request, table, trace)
        print(f"request {n}: {len(block)} bytes of headers (about {plain} as HTTP/1.1 text)")
        width = max(len(f"{name}: {value}") for name, value, _, _ in trace)
        for name, value, how, size in trace:
            print(f"   {size:>3} bytes  {name + ': ' + value:<{width}}  {how}")
        print()
    print(f"the dynamic table now holds {len(table.dynamic)} headers ({table.size()} of {table.max_size} bytes)")


def test():
    # RFC 7541 C.4: requests with Huffman coding, decoded one after another with the same table
    table = Table()
    blocks = ["828684418cf1e3c2e5f23a6ba0ab90f4ff",
              "828684be5886a8eb10649cbf",
              "828785bf408825a849e95ba97d7f8925a849e95bb8e8b4bf"]
    expect = [[(":method", "GET"), (":scheme", "http"), (":path", "/"), (":authority", "www.example.com")],
              [(":method", "GET"), (":scheme", "http"), (":path", "/"), (":authority", "www.example.com"), ("cache-control", "no-cache")],
              [(":method", "GET"), (":scheme", "https"), (":path", "/index.html"), (":authority", "www.example.com"), ("custom-key", "custom-value")]]
    ok = all([(n, v) for n, v, _, _ in decode(bytes.fromhex(b), table)] == e for b, e in zip(blocks, expect))
    ok &= huffman_encode(b"www.example.com").hex() == "f1e3c2e5f23a6ba0ab90f4ff"
    ok &= encode_int(1337, 5) == bytes([31, 154, 10])
    print("RFC 7541 examples: all match" if ok else "MISMATCH")


if __name__ == "__main__":
    test() if "--test" in sys.argv else demo()
