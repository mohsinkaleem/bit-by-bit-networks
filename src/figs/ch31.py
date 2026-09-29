#!/usr/bin/env python3
"""Generate chapter 31 figures.  python3 src/figs/ch31.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- XOR, the heart of a stream cipher

def xor():
    msg = "HI"
    mbits = "".join(format(ord(c), "08b") for c in msg)
    kbits = "1011001001110101"
    cbits = "".join(str(int(a) ^ int(b)) for a, b in zip(mbits, kbits))
    rows = [("message “HI”", mbits, "t-blue", "var(--blue)"), ("key (random)", kbits, "t-orange", "var(--orange)"),
            ("encrypted", cbits, "t-green", "var(--green)"), ("encrypted", cbits, "t-green", "var(--green)"),
            ("the same key", kbits, "t-orange", "var(--orange)"), ("message again", mbits, "t-blue", "var(--blue)")]
    b = []
    x0, w = 170, 30
    for r, (label, bits, cls, stroke) in enumerate(rows):
        y = 20 + r * 36 + (24 if r >= 3 else 0)
        b.append(text(x0 - 12, y + 19, label, "end xs b"))
        for i, bit in enumerate(bits):
            b.append(f'<rect x="{x0 + i * w + (i // 8) * 10}" y="{y}" width="{w - 4}" height="28" rx="4" class="{cls}" stroke="{stroke}"/>')
            b.append(text(x0 + i * w + (i // 8) * 10 + (w - 4) / 2, y + 19, bit, "mid mono sm b"))
        if r in (1, 4):
            b.append(text(x0 - 150, y + 19, "XOR", "xs b f-orange"))
        if r in (2, 5):
            b.append(f'<line x1="{x0}" y1="{y - 4}" x2="{x0 + 16 * w + 10}" y2="{y - 4}" class="line" stroke-width="1.5"/>')
    b.append(text(x0 + 8 * w + 5, 138, "…sent. Bob XORs with the same key, and gets the message back:", "mid xs muted"))
    svg = fig("".join(b), 720, 290, "A message XORed with a random key gives the ciphertext; XORing the ciphertext with the same key gives the message back",
              "XOR: 1 where the bits differ, 0 where they match. Doing it twice with the same key undoes it.")
    (OUT / "ch31-xor.svg").write_text(svg)


# ---------------------------------------------------------------- Diffie-Hellman, with paint

def paint():
    def pot(x, y, colour, label, step, sub=None):
        out = (f'<g data-show="{step}"><path d="M{x - 26},{y - 16} L{x + 26},{y - 16} L{x + 20},{y + 22} L{x - 20},{y + 22} Z" fill="{colour}" stroke="var(--ink)" stroke-width="1.5"/>'
               + text(x, y + 40, label, "mid xs b"))
        if sub:
            out += text(x, y + 54, sub, "mid xs muted")
        return out + "</g>"
    yellow, red, blue = "#f2c94c", "#d9534f", "#4a7fd6"
    orange, green = "#e8894a", "#8fb56b"            # yellow+red, yellow+blue
    brown = "#8a6a3a"
    b = [f'<rect x="240" y="8" width="240" height="250" rx="10" class="t-red" opacity="0.45"/>',
         text(360, 28, "in public: Eve sees all of it", "mid xs b f-red"),
         text(110, 28, "Alice", "mid sm b"), text(610, 28, "Bob", "mid sm b")]
    b.append(pot(360, 72, yellow, "a common colour", "1", "agreed in public"))
    b.append(pot(110, 72, red, "her secret colour", "2", "never shared"))
    b.append(pot(610, 72, blue, "his secret colour", "2", "never shared"))
    b.append(pot(300, 170, orange, "Alice’s mix", "3", "yellow + red"))
    b.append(pot(420, 170, green, "Bob’s mix", "3", "yellow + blue"))
    b.append('<g data-show="3"><path d="M140,90 C200,140 240,160 270,168" class="line s-muted" stroke-width="1.5" marker-end="url(#ah-muted)"/>'
             '<path d="M580,90 C520,140 480,160 450,168" class="line s-muted" stroke-width="1.5" marker-end="url(#ah-muted)"/></g>')
    b.append(pot(110, 200, brown, "the shared secret", "4", "Bob’s mix + her red"))
    b.append(pot(610, 200, brown, "the shared secret", "4", "Alice’s mix + his blue"))
    b.append('<g data-show="4"><path d="M392,178 C300,230 200,220 140,206" class="line s-green" stroke-width="2" marker-end="url(#ah-green)"/>'
             '<path d="M328,178 C420,230 520,220 580,206" class="line s-blue" stroke-width="2" marker-end="url(#ah-blue)"/></g>')
    steps = ["Alice and Bob agree, in public, on a common starting colour. Eve hears it.",
             "Each secretly picks a colour of their own, and never tells anyone.",
             "Each mixes their secret colour into the common one, and sends the mix across, in public. Eve sees both mixes, but unmixing paint is hopeless: she can’t get the secret colours back out.",
             "Each adds their own secret colour to the <em>other’s</em> mix. Both end up with the same colour, common + red + blue, which never crossed the room. Eve has common + red, and common + blue, and no way to combine them into common + red + blue."]
    svg = fig("".join(b), 720, 268, "The paint-mixing picture of Diffie-Hellman: a public colour, two secret colours, two public mixes, and the same final mixture on both sides",
              "Diffie–Hellman key exchange, with paint instead of numbers.", steps)
    (OUT / "ch31-paint.svg").write_text(svg)


# ---------------------------------------------------------------- AEAD: encrypt, and tag

def aead():
    b = []

    def box(x, y, w, label, sub, cls, stroke, step=None):
        g = f'<rect x="{x}" y="{y}" width="{w}" height="44" rx="8" class="{cls}" stroke="{stroke}" stroke-width="1.6"/>' + text(x + w / 2, y + 19, label, "mid xs b") + text(x + w / 2, y + 34, sub, "mid xs muted")
        return f'<g data-show="{step}">{g}</g>' if step else g
    b.append(box(20, 30, 180, "the message", "Meet me at the old oak…", "t-blue", "var(--blue)"))
    b.append(box(20, 96, 180, "key + nonce", "32 secret bytes + 12 unique ones", "t-orange", "var(--orange)"))
    b.append(box(270, 60, 160, "ChaCha20-Poly1305", "seal()", "f-card", "var(--line)"))
    b.append('<path d="M200,52 L266,76" class="line" stroke-width="2" marker-end="url(#ah-ink)"/><path d="M200,118 L266,94" class="line" stroke-width="2" marker-end="url(#ah-ink)"/>')
    b.append('<path d="M430,82 L494,82" class="line" stroke-width="2" marker-end="url(#ah-ink)"/>')
    b.append(box(500, 40, 200, "ciphertext", "7cc4567d99cf183e… (same length)", "t-green", "var(--green)"))
    b.append(box(500, 96, 200, "tag", "4a97433ca1dd21ad…", "t-purple", "var(--purple)"))
    b.append('<g data-show="2">' + text(360, 170, "Eve flips one bit of the ciphertext. When Bob opens it:", "mid xs b f-red")
             + box(210, 184, 300, "open() refuses", "“authentication failed”: nothing is decrypted at all", "t-red", "var(--red)") + "</g>")
    steps = ["An <strong>authenticated cipher</strong> does two jobs at once. The ciphertext hides the message. The 16-byte tag proves that the ciphertext, and any unencrypted header sent with it, is exactly what the sender sealed. The nonce must never be reused with the same key, or the one-time pad’s weakness comes back.",
             "Encryption alone doesn’t stop tampering: with a stream cipher, flipping a bit of the ciphertext flips the same bit of the message, and Eve could change “10 pounds” into “90 pounds” without knowing the key. The tag makes any change detectable. (These are real bytes from this chapter’s lab.)"]
    svg = fig("".join(b), 720, 240, "Authenticated encryption: a message, key and nonce go into ChaCha20-Poly1305, producing ciphertext and a tag; tampering makes decryption fail",
              "Authenticated encryption: secrecy and a seal, in one step.", steps)
    (OUT / "ch31-aead.svg").write_text(svg)


# ---------------------------------------------------------------- a real certificate chain

def chain():
    certs = [("example.org", "Cloudflare TLS Issuing ECC CA 3", "valid 26 Sep to 25 Dec 2026", "ECDSA P-256", "the website"),
             ("Cloudflare TLS Issuing ECC CA 3", "SSL.com TLS Transit ECC CA R2", "valid until 2035", "ECDSA P-256", "an intermediate"),
             ("SSL.com TLS Transit ECC CA R2", "SSL.com TLS ECC Root CA 2022", "valid until 2037", "ECDSA P-384", "another intermediate"),
             ("SSL.com TLS ECC Root CA 2022", "AAA Certificate Services", "this copy cross-signed by an older root", "ECDSA P-384", "a root: trusted in advance")]
    b = []
    for i, (subject, issuer, valid, key, role) in enumerate(certs):
        y = 14 + i * 72
        cls = "t-green" if i == 3 else "f-card"
        b.append(f'<rect x="150" y="{y}" width="420" height="56" rx="8" class="{cls}" stroke="var(--line)" stroke-width="1.6"/>')
        b.append(text(162, y + 20, subject, "sm b"))
        b.append(text(162, y + 38, f"public key: {key} · {valid}", "xs muted"))
        b.append(text(560, y + 20, role, "end xs b"))
        b.append(text(140, y + 32, f"#{i}", "end xs muted"))
        if i < 3:
            b.append(f'<path d="M600,{y + 46} C650,{y + 60} 650,{y + 72} 600,{y + 86}" class="line s-orange" stroke-width="2" marker-end="url(#ah-orange)"/>')
            b.append(text(650, y + 70, "signed by ↓", "xs b f-orange"))
    svg = fig("".join(b), 720, 306, "The real certificate chain for example.org: the site's certificate, two intermediates, and a root",
              "The certificates example.org really sends, checked from the bottom up: each one is signed by the next, ending at a root the computer already trusts (from <code>openssl s_client -showcerts</code>). The root is sent as a copy signed by an even older root, so that devices too old to know the 2022 one still trust the chain (Chapter 32).")
    (OUT / "ch31-chain.svg").write_text(svg)


if __name__ == "__main__":
    xor()
    paint()
    aead()
    chain()
    print("wrote ch31 figures")
