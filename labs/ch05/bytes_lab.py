#!/usr/bin/env python3
"""Chapter 5 lab, part 1: looking at bytes.

    python3 bytes_lab.py inspect "Hé 👋"      every character, its number, and its UTF-8 bytes
    python3 bytes_lab.py hexdump FILE          a mini hexdump (like `xxd`)
    python3 bytes_lab.py endian 1000           a number as 2 and 4 bytes, both byte orders
    python3 bytes_lab.py ascii                 the printable ASCII table
"""
import struct
import sys


# --8<-- [start:inspect]
def inspect(text):
    print(f"{'char':>6}  {'code point':>10}  {'UTF-8 bytes (hex)':<18}  bits")
    for ch in text:
        data = ch.encode("utf-8")                     # str -> bytes
        hexes = " ".join(f"{b:02X}" for b in data)
        bits = " ".join(f"{b:08b}" for b in data)
        shown = repr(ch)[1:-1] if not ch.isprintable() or ch == " " else ch
        print(f"{shown:>6}  {'U+%04X' % ord(ch):>10}  {hexes:<18}  {bits}")
    total = text.encode("utf-8")
    print(f"\n{len(text)} characters became {len(total)} bytes: {total.hex(' ').upper()}")
# --8<-- [end:inspect]


# --8<-- [start:hexdump]
def hexdump(path, limit=512):
    with open(path, "rb") as f:
        data = f.read(limit)
    for offset in range(0, len(data), 16):
        chunk = data[offset:offset + 16]
        hexes = " ".join(f"{b:02x}" for b in chunk)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{offset:08x}  {hexes:<47}  {text}")
# --8<-- [end:hexdump]


def endian(n):
    for fmt, size in (("H", 2), ("I", 4)):
        if n >= 2 ** (8 * size):
            continue
        big = struct.pack(">" + fmt, n)
        little = struct.pack("<" + fmt, n)
        print(f"{n} in {size} bytes:  big-endian (network order) {big.hex(' ').upper():<12}   "
              f"little-endian {little.hex(' ').upper()}")


def ascii_table():
    for row in range(16):
        cells = []
        for col in range(2, 8):
            code = col * 16 + row
            ch = chr(code) if code != 127 else "DEL"
            cells.append(f"{code:3} {code:02X} {ch:<3}")
        print("   ".join(cells))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["inspect"] and len(args) > 1:
        inspect(" ".join(args[1:]))
    elif args[:1] == ["hexdump"] and len(args) > 1:
        hexdump(args[1])
    elif args[:1] == ["endian"] and len(args) > 1:
        endian(int(args[1], 0))
    elif args[:1] == ["ascii"]:
        ascii_table()
    else:
        print(__doc__)
