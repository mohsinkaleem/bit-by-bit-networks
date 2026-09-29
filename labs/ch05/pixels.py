#!/usr/bin/env python3
"""Chapter 5 lab, part 2: turning a drawing into bytes, and bytes into a real PNG file.

    python3 pixels.py                  draw the built-in volcano, write volcano.png
    python3 pixels.py drawing.txt      draw your own ("#" = dark pixel, anything else = light)
    open volcano.png                   (macOS) view it

The PNG format is a nice preview of later chapters: a file is a list of "chunks",
and every chunk says its LENGTH up front and ends with a CRC checksum (Chapter 10).
"""
import struct
import sys
import zlib

VOLCANO = """
................................
..............#..#..............
.............#.##.#.............
..............####..............
...............##...............
..............####..............
.............######.............
............########............
...........##########...........
..........############..........
.........##############.........
........################........
.......##################.......
......####################......
.....######################.....
################################
"""

# --8<-- [start:bytes]
def rows_to_bytes(rows):
    """Pack each row of pixels into bytes, 8 pixels per byte, 1 = dark."""
    out = []
    for row in rows:
        bits = "".join("1" if ch == "#" else "0" for ch in row)
        bits = bits.ljust((len(bits) + 7) // 8 * 8, "0")        # pad to a multiple of 8
        out.append(bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)))
    return out
# --8<-- [end:bytes]


# --8<-- [start:png]
def chunk(kind, data):
    """A PNG chunk: 4-byte length, 4-byte type, the data, then a CRC of type + data."""
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data)))


def write_png(path, rows, scale=12):
    height, width = len(rows), len(rows[0])
    raw = b""
    for row in rows:
        line = b"".join((b"\x20\x20\x20" if ch == "#" else b"\xff\xd9\x66") * scale for ch in row)
        raw += (b"\x00" + line) * scale                 # each scanline starts with a filter byte
    header = struct.pack(">IIBBBBB", width * scale, height * scale, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = (b"\x89PNG\r\n\x1a\n"                            # the "magic number" every PNG starts with
           + chunk(b"IHDR", header)
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)
# --8<-- [end:png]


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            text = f.read()
        out = sys.argv[1].rsplit(".", 1)[0] + ".png"
    else:
        text, out = VOLCANO, "volcano.png"
    rows = [line for line in text.strip("\n").splitlines()]
    width = max(len(r) for r in rows)
    rows = [r.ljust(width, ".") for r in rows]

    packed = rows_to_bytes(rows)
    print(f"{width} x {len(rows)} pixels, 1 bit each = {sum(len(p) for p in packed)} bytes:\n")
    for row, data in zip(rows, packed):
        drawn = row.replace("#", "█").replace(".", "·")
        print(f"  {drawn}   {data.hex(' ').upper()}")
    size = write_png(out, rows)
    print(f"\nwrote {out} ({size} bytes). On a Mac: open {out}")


if __name__ == "__main__":
    main()
