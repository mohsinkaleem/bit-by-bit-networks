#!/usr/bin/env python3
"""Generate chapter 42 figures.  python3 src/figs/ch42.py"""
import math
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def box(x, y, w, h, cls="f-card", stroke="var(--line)", rx=8, dash=False, sw=1.6):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" class="{cls}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def line(x1, y1, x2, y2, cls="s-ink", w=2.2, arrow=False, dash=False):
    mk = f' marker-end="url(#ah-{"ink" if cls == "s-ink" else cls[2:]})"' if arrow else ""
    d = ' stroke-dasharray="5 4"' if dash else ""
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="{w}"{mk}{d}/>'


# ---------------------------------------------------------------- harvest now, decrypt later

def harvest():
    b = ['<path d="M40,110 L690,110" class="line s-muted" stroke-width="3" marker-end="url(#ah-muted)"/>']
    for x, yr in ((70, "2026"), (300, "…"), (560, "the year a big quantum computer works")):
        b.append(text(x, 132, yr, "mid xs b muted" if yr != "…" else "mid sm muted"))
    b.append('<g data-show="1">' + box(20, 30, 200, 56, "t-blue", "var(--blue)")
             + text(120, 52, "Bob’s HTTPS connection", "mid xs b") + text(120, 70, "X25519 key exchange, then AES", "mid xs")
             + f'<use href="#eve-head" x="236" y="36" width="44" height="44"/>'
             + text(300, 54, "Eve records every byte,", "xs") + text(300, 70, "and keeps it", "xs")
             + box(430, 40, 60, 40, "f-surface", "var(--line)", 6) + text(460, 65, "4 TB", "mid xs b") + "</g>")
    b.append('<g data-show="2">' + box(470, 150, 240, 64, "t-red", "var(--red)")
             + text(590, 172, "Shor’s algorithm finds", "mid xs b") + text(590, 188, "X25519’s secret key from the", "mid xs")
             + text(590, 204, "public keys she recorded", "mid xs") + line(460, 80, 540, 148, "s-red", 2, arrow=True) + "</g>")
    b.append('<g data-show="3">' + box(150, 160, 250, 54, "t-red", "var(--red)")
             + text(275, 182, "…and so the AES key, and so", "mid xs b") + text(275, 198, "everything Bob said, years ago", "mid xs")
             + line(468, 186, 404, 186, "s-red", 2, arrow=True) + "</g>")
    b.append('<g data-show="4">' + box(20, 232, 690, 44, "t-green", "var(--green)")
             + text(365, 250, "Unless the key exchange was already post-quantum: then there’s nothing in the recording", "mid xs b")
             + text(365, 266, "that a quantum computer can turn into the key. The protection has to be in place before the recording is made.", "mid xs") + "</g>")
    steps = ["Today: Eve can’t read Bob’s encrypted traffic (Chapter 31). But disks are cheap, so she records it anyway.",
             "One day, perhaps, a large quantum computer works. It can solve the maths problem behind X25519 (and RSA, and every elliptic curve): from the public keys in the recording, it finds a private one.",
             "With it, Eve redoes the key exchange, runs the same key schedule as Chapter 32, and decrypts the whole conversation. Years late, but for some secrets that doesn’t matter.",
             "That’s why the switch has to happen long before anyone has such a computer."]
    svg = fig("".join(b), 720, 286, "A timeline: Eve records encrypted traffic today and decrypts it once a quantum computer exists, unless a post-quantum key exchange was used",
              "“Harvest now, decrypt later”. The danger for today’s secrets isn’t today’s computers.", steps)
    (OUT / "ch42-harvest.svg").write_text(svg)


# ---------------------------------------------------------------- what a quantum computer breaks

def breaks():
    rows = [("X25519, ECDH", "agreeing on keys (Ch. 31, 32)", "safe", "broken (Shor)", "t-red"),
            ("RSA", "keys and signatures", "safe", "broken (Shor)", "t-red"),
            ("ECDSA, Ed25519", "signatures, certificates", "safe", "broken (Shor)", "t-red"),
            ("AES-128", "encrypting the data", "safe", "weaker (Grover)", "t-yellow"),
            ("AES-256, ChaCha20", "encrypting the data", "safe", "safe", "t-green"),
            ("SHA-256", "hashes, key schedules", "safe", "safe", "t-green"),
            ("ML-KEM, ML-DSA, SLH-DSA", "the new standards", "safe", "safe, as far as anyone knows", "t-green")]
    b = [text(20, 22, "", "xs b"), text(250, 22, "used for", "xs b"), text(450, 22, "against today’s computers", "mid xs b"),
         text(620, 22, "against a quantum computer", "mid xs b")]
    for i, (name, use, now, q, cls) in enumerate(rows):
        y = 34 + i * 32
        b.append(box(14, y, 692, 26, "f-surface" if i % 2 else "f-card", "var(--line)", 4, sw=0.8))
        b.append(text(24, y + 17, name, "xs b"))
        b.append(text(250, y + 17, use, "xs"))
        b.append(text(450, y + 17, now, "mid xs"))
        b.append(box(540, y + 3, 160, 20, cls, "none", 4, sw=0))
        b.append(text(620, y + 17, q, "mid xs b"))
    svg = fig("".join(b), 720, 34 + len(rows) * 32 + 6, "A table: key exchange and signature algorithms like X25519, RSA and ECDSA are broken by a quantum computer; AES-128 is weakened; AES-256, ChaCha20 and SHA-256 stay safe; the new ML-KEM, ML-DSA and SLH-DSA are designed to stay safe",
              "What a large quantum computer would break. Shor’s algorithm destroys the maths behind almost every public-key method in use; Grover’s only speeds up guessing, which bigger keys fix.")
    (OUT / "ch42-breaks.svg").write_text(svg)


# ---------------------------------------------------------------- lattices: good and bad bases

def lattice():
    ox, oy, sc = 60, 270, 26
    g1, g2 = (3, 1), (1, 2)                     # a short, nearly square basis
    b1, b2 = (7, 4), (11, 7)                    # the same lattice: 2·g1 + g2 and 3·g1 + 2·g2 (long and thin)
    target = (4.4, 4.3)

    def P(x, y):
        return ox + x * sc, oy - y * sc
    b = ['<clipPath id="lat42"><rect x="10" y="10" width="380" height="290" rx="8"/></clipPath>',
         box(10, 10, 380, 290, "f-card", "var(--line)", 8), '<g clip-path="url(#lat42)">']
    for i in range(-12, 13):
        for j in range(-12, 13):
            x, y = i * g1[0] + j * g2[0], i * g1[1] + j * g2[1]
            px, py = P(x, y)
            if 10 < px < 390 and 10 < py < 300:
                b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" class="f-ink"/>')
    tx, ty = P(*target)
    b.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="6" class="f-red"/>')
    b.append(text(tx - 10, ty + 22, "a point with noise added", "end xs b f-red"))
    near = min(((i * g1[0] + j * g2[0], i * g1[1] + j * g2[1]) for i in range(-5, 6) for j in range(-5, 6)),
               key=lambda p: (p[0] - target[0]) ** 2 + (p[1] - target[1]) ** 2)
    nx, ny = P(*near)
    b.append('<g data-show="1">')
    for v, cls in ((g1, "s-green"), (g2, "s-green")):
        b.append(line(ox, oy, *P(*v), cls, 3, arrow=True))
    b.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="9" fill="none" class="line s-green" stroke-width="2.5"/>')
    b.append("</g>")
    b.append('<g data-show="2">')
    for v in (b1, b2):
        b.append(line(ox, oy, *P(*v), "s-orange", 3, arrow=True))
    b.append("</g></g>")
    b.append(text(420, 40, "A lattice: a grid of points, made by adding", "xs"))
    b.append(text(420, 56, "whole multiples of two arrows (a basis).", "xs"))
    b.append('<g data-show="1">' + text(420, 92, "With short, nearly square arrows (green),", "xs b f-green")
             + text(420, 108, "finding the lattice point nearest to the red", "xs")
             + text(420, 124, "one is easy: round to the nearest corner.", "xs") + "</g>")
    b.append('<g data-show="2">' + text(420, 160, "The orange arrows make exactly the same", "xs b f-orange")
             + text(420, 176, "grid. But from them, rounding points you", "xs")
             + text(420, 192, "to the wrong place, far away.", "xs")
             + text(420, 226, "Now imagine 768 dimensions instead of 2.", "xs b")
             + text(420, 242, "The public key is like the orange arrows;", "xs")
             + text(420, 258, "the private key, the green ones. Nobody", "xs")
             + text(420, 274, "knows a fast way, even with a quantum", "xs")
             + text(420, 290, "computer, to get from one to the other.", "xs") + "</g>")
    steps = ["The same grid of points can be made from different pairs of arrows. With a good pair, it’s easy to find the grid point closest to any spot.",
             "With a bad pair, it’s very hard. Lattice cryptography gives everyone the bad arrows, and keeps the good ones secret."]
    svg = fig("".join(b), 720, 310, "A two-dimensional lattice of points with a short basis and a long skewed basis, and a target point to be matched to its nearest lattice point",
              "The hard problem underneath ML-KEM and ML-DSA, in two dimensions instead of hundreds.", steps)
    (OUT / "ch42-lattice.svg").write_text(svg)


# ---------------------------------------------------------------- the hybrid key share in TLS

def hybrid():
    scale = 0.33                                                     # pixels per byte
    b = [text(20, 22, "the key share in each hello, to scale", "xs b")]
    rows = [("Chapter 32’s ClientHello", "191 bytes in all", [(32, "X25519", "t-blue", "var(--blue)")]),
            ("our ClientHello now", "1,375 bytes in all", [(1184, "ML-KEM-768 encapsulation key", "t-purple", "var(--purple)"), (32, "X25519", "t-blue", "var(--blue)")]),
            ("the server’s reply", "1,210 bytes in all", [(1088, "ML-KEM-768 ciphertext", "t-purple", "var(--purple)"), (32, "X25519", "t-blue", "var(--blue)")]),
            ("the shared secret", "→ into the key schedule", [(32, "ML-KEM", "t-purple", "var(--purple)"), (32, "X25519", "t-blue", "var(--blue)")])]
    for i, (name, sub, parts) in enumerate(rows):
        y = 40 + i * 50
        b.append(text(20, y + 12, name, "xs b"))
        b.append(text(20, y + 26, sub, "xs muted"))
        x = 190
        for n, label, cls, stroke in parts:
            w = max(n * scale, 14)
            b.append(box(x, y, w, 26, cls, stroke, 3, sw=1.2))
            if w > 120:
                b.append(text(x + w / 2, y + 17, f"{label}: {n:,} bytes", "mid xs"))
            x += w
        b.append(text(x + 8, y + 17, "32 + 32 bytes" if i == 3 else ("+ " if len(parts) > 1 else "") + "X25519: 32 bytes", "xs"))
    svg = fig("".join(b), 720, 240, "Bars to scale: a classical key share of 32 bytes, the hybrid client share of 1,216 bytes, the server's 1,120 bytes, and a 64-byte combined secret",
              "X25519MLKEM768 in the handshake. Each side sends both kinds of key share, glued together, and the secret is both results, one after the other. Break X25519 and you still face ML-KEM, and the other way round.")
    (OUT / "ch42-hybrid.svg").write_text(svg)


# ---------------------------------------------------------------- signature and key sizes (openssl, measured)

def sizes():
    rows = [("Ed25519", 32, 64), ("ECDSA P-256", 65, 71), ("RSA-2048", 270, 256),
            ("ML-DSA-44", 1312, 2420), ("ML-DSA-65", 1952, 3309), ("ML-DSA-87", 2592, 4627),
            ("SLH-DSA-SHA2-128s", 32, 7856), ("SLH-DSA-SHA2-128f", 32, 17088)]
    sc = 430 / 17088
    b = [text(20, 22, "bytes, as OpenSSL 3.6 makes them", "xs b"),
         '<rect x="440" y="12" width="12" height="12" class="t-orange"/>', text(458, 22, "public key", "xs"),
         '<rect x="540" y="12" width="12" height="12" class="t-purple"/>', text(558, 22, "one signature", "xs")]
    for i, (name, pk, sig) in enumerate(rows):
        y = 36 + i * 32
        b.append(text(20, y + 18, name, "xs b"))
        x = 170
        wp, ws = max(pk * sc, 2), max(sig * sc, 2)
        b.append(f'<rect x="{x}" y="{y + 4}" width="{wp:.1f}" height="10" class="t-orange" stroke="var(--orange)" stroke-width="0.8"/>')
        b.append(f'<rect x="{x}" y="{y + 16}" width="{ws:.1f}" height="10" class="t-purple" stroke="var(--purple)" stroke-width="0.8"/>')
        b.append(text(x + max(wp, ws) + 8, y + 20, f"{pk:,} + {sig:,}", "xs mono"))
    b.append(text(20, 36 + len(rows) * 32 + 14, "A TLS handshake carries two or three certificates, each with a public key and a signature, plus one more signature (Chapter 32).", "xs"))
    svg = fig("".join(b), 720, 36 + len(rows) * 32 + 26, "Bar chart of public key and signature sizes: Ed25519 32 and 64 bytes, ECDSA 65 and 71, RSA 270 and 256, ML-DSA-65 1,952 and 3,309, SLH-DSA-128f 32 and 17,088",
              "Post-quantum signatures are big. The first three rows are today’s; the rest are NIST’s new standards.")
    (OUT / "ch42-sizes.svg").write_text(svg)


if __name__ == "__main__":
    harvest()
    breaks()
    lattice()
    hybrid()
    sizes()
    print("wrote ch42 figures")
